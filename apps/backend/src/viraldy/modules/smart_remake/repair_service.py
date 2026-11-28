from __future__ import annotations

import copy
import hashlib
import json
import tempfile
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any, cast
from uuid import UUID, uuid4

from starlette.concurrency import run_in_threadpool

from viraldy.platform.config.settings import Settings
from viraldy.shared.errors.base import AppError, ConflictError, NotFoundError

from .engine.audio_assets import AUDIO_ASSET_DIR, mux_reference_music
from .engine.concat import _fetch_scene_video_bytes, concat_video_urls
from .engine.errors import SmartRemakeError
from .engine.flowkit_client import FlowKitClient
from .engine.media_probe import probe_media_bytes
from .engine.prompt_edits import scene_edit_directions
from .engine.prompt_sanitizer import validate_sanitized_compiler_prompts
from .engine.render_orchestrator import _text_overlays, render_smart_remake
from .engine.schemas import RenderSmartRemakeInput, UploadedMedia
from .engine.unifically_adapter import extract_task_output_url
from .engine.unifically_client import UnificallyClient
from .models import SmartRemakeOperationModel, SmartRemakeProjectModel
from .repair_media import RepairMediaStore, now_iso, technical_check, with_silent_audio
from .repair_repository import RepairRepository
from .repair_schemas import AcceptSceneVersion, RepairSceneRequest


def _scene(state: dict[str, Any], scene_id: UUID | str) -> dict[str, Any]:
    for scene in state["scenes"]:
        if scene["id"] == str(scene_id):
            return cast(dict[str, Any], scene)
    raise NotFoundError("SMART_REMAKE_SCENE_NOT_FOUND", "Scene was not found in this project.")


def _version(scene: dict[str, Any], version_id: UUID | str) -> dict[str, Any]:
    for version in scene["versions"]:
        if version["id"] == str(version_id):
            return cast(dict[str, Any], version)
    raise NotFoundError("SMART_REMAKE_VERSION_NOT_FOUND", "Version was not found in this scene.")


def _revision(state: dict[str, Any], expected: int) -> None:
    if state["revision"] != expected:
        raise ConflictError(
            "SMART_REMAKE_REVISION_CONFLICT",
            "The project changed. Refresh before applying this operation.",
        )


def _request_hash(action: str, scene_id: UUID | str, payload: dict[str, Any]) -> str:
    value = {"action": action, "sceneId": str(scene_id), **payload}
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def _new_version(
    data: bytes,
    key: str,
    prompts: dict[str, Any],
    parent: str | None,
    metadata: dict[str, Any],
    *,
    source: str,
    audio_required: bool,
    expected_duration: int = 8,
) -> dict[str, Any]:
    return {
        "id": str(uuid4()),
        "parentVersionId": parent,
        "storageKey": key,
        "mediaHash": hashlib.sha256(data).hexdigest(),
        "prompt": prompts["prompt"],
        "imagePrompt": prompts["imagePrompt"],
        "videoPrompt": prompts["videoPrompt"],
        "source": source,
        "createdAt": now_iso(),
        "usedByRevision": None,
        "providerMetadata": copy.deepcopy(metadata),
        **{
            field: copy.deepcopy(metadata[field])
            for field in ("generationExpectations", "expectationsHash")
            if field in metadata
        },
        "technicalCheck": technical_check(
            data, expected_duration=expected_duration, audio_required=audio_required,
        ),
    }


def _ambiguous_provider_failure(exc: Exception, *, submitted: bool = False) -> bool:
    code = getattr(exc, "code", "")
    if submitted and code not in {
        "UNIFICALLY_TASK_FAILED",
        "FLOWKIT_IMAGE_GENERATION_FAILED",
        "FLOWKIT_VIDEO_GENERATION_FAILED",
        "UNIFICALLY_VALIDATION_FAILED",
        "UNIFICALLY_PAYLOAD_INVALID",
        "COMPILER_OUTPUT_INVALID",
        "INVALID_FLOWKIT_SCENE_PAYLOAD",
    }:
        # Once a task exists, retry retrieval/persistence of that output rather
        # than opening another paid generation because a download or store failed.
        return True
    details = getattr(exc, "details", None)
    status = details.get("status") if isinstance(details, dict) else None
    return (
        "POLL_TIMEOUT" in code
        or code
        in {
            "UNIFICALLY_UNAVAILABLE",
            "UNIFICALLY_TASK_STATUS_FAILED",
            "UNIFICALLY_OUTPUT_DOWNLOAD_FAILED",
            "FLOWKIT_UNAVAILABLE",
            "FLOWKIT_INVALID_BATCH_STATUS",
            "SMART_REMAKE_SCENE_PENDING",
        }
        or (isinstance(status, int) and status >= 500)
    )


async def _reconciled_media(task: dict[str, Any]) -> bytes | None:
    ids = task.get("requestIds") or []
    if not ids:
        return None
    if task["provider"] == "flowkit":
        flowkit = FlowKitClient()
        statuses = [await flowkit.get_request_status(task_id) for task_id in ids]
        if any(
            str(item.get("status")).lower() in {"failed", "error", "cancelled"} for item in statuses
        ):
            raise SmartRemakeError(
                "The existing FlowKit request failed.", "FLOWKIT_VIDEO_GENERATION_FAILED"
            )
        if task.get("stage") != "video" or not task.get("videoId"):
            return None
        if not all(
            str(item.get("status")).lower() in {"completed", "succeeded", "success", "done"}
            for item in statuses
        ):
            return None
        records = await flowkit.list_scenes(task["videoId"])
        record = next(
            (item for item in records if item.get("id") in task.get("sceneIds", [])), None
        )
        url = record.get("vertical_video_url") if record else None
        return await _fetch_scene_video_bytes(url, 0) if isinstance(url, str) and url else None
    client = UnificallyClient()
    status = await client.get_task(ids[-1])
    if status.get("status") == "failed":
        raise SmartRemakeError("The existing Unifically request failed.", "UNIFICALLY_TASK_FAILED")
    url = extract_task_output_url(status, "video_url")
    if status.get("status") != "completed" or not url:
        return None
    return await client.download_file(url)


def _scene_description(scene: dict[str, Any], scene_map: Any) -> str | None:
    existing = scene.get("description")
    if isinstance(existing, str) and existing.strip():
        return existing.strip()
    if not isinstance(scene_map, dict) or not isinstance(scene_map.get("scenes"), list):
        return None
    compiled_scenes = [item for item in scene_map["scenes"] if isinstance(item, dict)]
    matching = [item for item in compiled_scenes if item.get("id") == scene["id"]]
    if not matching and type(scene.get("index")) is int:
        matching = [
            item for item in compiled_scenes
            if not item.get("id")
            and type(item.get("displayOrder")) is int
            and item["displayOrder"] == scene["index"]
        ]
    if len(matching) != 1:
        return None
    compiled = matching[0]
    description = compiled.get("description")
    if isinstance(description, str) and description.strip():
        return description.strip()
    shot_plan = compiled.get("shotPlan")
    if not isinstance(shot_plan, dict) or not isinstance(shot_plan.get("shots"), list):
        return None
    actions = []
    for shot in shot_plan["shots"]:
        if not isinstance(shot, dict):
            continue
        action = shot.get("physicalAction")
        if not isinstance(action, str) or not action.strip():
            action = shot.get("action")
        if isinstance(action, str) and action.strip():
            actions.append(action.strip())
    return " ".join(actions) or None


class RepairService:
    """Awaited provider operations with persisted candidates and explicit activation.

    A running operation is never resubmitted automatically. After a process failure,
    operators must reconcile the provider before retrying a paid request.
    """

    def __init__(
        self,
        repository: RepairRepository,
        media: RepairMediaStore,
        workspace_id: UUID,
        *,
        settings: Settings | None = None,
    ) -> None:
        self.repository = repository
        self.media = media
        self.workspace_id = workspace_id
        self.settings = settings
        self.render_project_id: UUID | None = None

    async def present(self, row: SmartRemakeProjectModel) -> dict[str, Any]:
        state = copy.deepcopy(row.state_json)
        final_key = state.pop("finalStorageKey", None)
        p0 = row.context_json.get("p0")
        unavailable = p0 and p0.get("status") in {"suspended", "deleted"}
        if final_key and not unavailable:
            state["finalVideoUrl"] = await self.media.url(final_key)
            if not p0 and getattr(self.settings, "ai_mode", "fixture").strip().lower() in {
                "fixture", "mock"
            }:
                state["downloadUrl"] = await self.media.download_url(
                    final_key, f"smart-remake-{row.id}.mp4"
                )
        if p0:
            from .project_presentation import project_policy_fields

            state.pop("downloadUrl", None)
            state.update(project_policy_fields(row.context_json))
            from .project_preview import public_project_preview

            preview = public_project_preview(row)
            if preview is not None:
                state["preview"] = preview
            if getattr(self.repository, "session", None) is not None:
                from .budget_ledger import budget_summary

                state["budget"] = await budget_summary(
                    self.repository.session, self.workspace_id, row.id
                )
        if unavailable:
            from .project_presentation import without_storage_keys

            def stopped(value: Any) -> Any:
                if isinstance(value, dict):
                    return {key: stopped(item) for key, item in value.items()
                            if not key.lower().endswith("url")}
                if isinstance(value, list):
                    return [stopped(item) for item in value]
                return value

            return cast(dict[str, Any], stopped(without_storage_keys(state)))
        state["productImageUrl"] = await self.media.url(row.context_json["productKey"])
        additional = (row.context_json.get("p0") or {}).get("additionalProductReferences") or []
        if additional:
            state["additionalProductImageUrls"] = [
                await self.media.url(asset["storageKey"]) for asset in additional
            ]
        if row.context_json.get("characterKey"):
            state["characterImageUrl"] = await self.media.url(row.context_json["characterKey"])
        if state.get("schemaVersion") == 2:
            state["sourceVideoUrl"] = await self.media.url(row.context_json["sourceKey"])
            thumbnail_keys = row.context_json.get("sourceThumbnailKeys", {})
            for source_scene in state.get("sourceSceneMap", {}).get("scenes", []):
                thumbnail_key = thumbnail_keys.get(source_scene["id"])
                if thumbnail_key:
                    source_scene["thumbnailUrl"] = await self.media.url(thumbnail_key)
        for scene in state["scenes"]:
            description = _scene_description(scene, row.context_json.get("sceneMap"))
            if description:
                scene["description"] = description
            for version in scene["versions"]:
                key = version.pop("storageKey")
                version["videoUrl"] = await self.media.url(key)
        if p0:
            from .inspection_presentation import (
                current_report_ids,
                evidence_previews,
                inspection_clock_fields,
            )
            from .project_presentation import without_storage_keys

            state["inspectionSummary"]["currentReportIds"] = current_report_ids(
                row, self.workspace_id
            )
            previews = await evidence_previews(row, self.media, self.workspace_id)
            state.update(inspection_clock_fields(row, self.workspace_id, previews))
            state = without_storage_keys(state)
        return state

    async def get(self, project_id: UUID) -> dict[str, Any]:
        from .provider_errors import public_provider_error_fields

        row = await self.repository.project(self.workspace_id, project_id)
        operation = await self.repository.running(project_id)
        p0 = getattr(row, "context_json", {}).get("p0") or {}
        stopped = p0.get("status") in {"suspended", "deleted"} or (
            (p0.get("deletion") or {}).get("status") not in {None, "cancelled"}
        )
        if operation and stopped:
            pass
        elif operation and operation.result_json.get("kind") == "compose":
            from .timeline_service import reconcile_compose_project

            await reconcile_compose_project(self, operation)
        elif operation and (
            not operation.result_json
            or operation.result_json.get("kind") in {"compile", "inspection"}
        ):
            # These operations own their dispatch and model receipt. A read must
            # never reinterpret them as a video submission or run AI inline.
            # An empty receipt has no recorded work to reconcile yet either.
            pass
        elif operation and row.state_json.get("provider") == "kie":
            from .kie_workflow import reconcile_kie_project

            await reconcile_kie_project(self, row, operation)
            row = await self.repository.project(self.workspace_id, project_id)
        elif operation and operation.result_json.get("providerTasks"):
            await self._reconcile(row, operation)
            row = await self.repository.project(self.workspace_id, project_id)
        state = await self.present(row)
        generation_attempts = None
        latest = None
        if operation and operation.status == "running":
            state["pendingOperation"] = {
                "id": str(operation.id),
                "kind": operation.result_json.get("kind"),
                "status": "running",
                "needsReconciliation": bool(operation.result_json.get("needsReconciliation")),
                "errorCode": operation.result_json.get("errorCode"),
                **public_provider_error_fields(operation.result_json),
            }
        elif row.state_json.get("provider") == "kie" or row.context_json.get("p0") is not None:
            latest = await self.repository.latest_operation(project_id)
            if latest:
                state["lastOperation"] = {
                    "id": str(latest.id),
                    "kind": latest.result_json.get("kind"),
                    "status": latest.status,
                    "errorCode": latest.result_json.get("errorCode"),
                    "needsReconciliation": bool(latest.result_json.get("needsReconciliation")),
                    **public_provider_error_fields(latest.result_json),
                }
        if not stopped and not operation and latest and (
            latest.status == "failed" and latest.result_json.get("kind") == "render"
        ):
            from sqlalchemy import select

            from .budget_models import SmartRemakeAttemptModel
            from .generation_recovery import initial_render_recovery

            attempts = list(await self.repository.session.scalars(
                select(SmartRemakeAttemptModel).where(
                    SmartRemakeAttemptModel.project_id == row.id,
                    SmartRemakeAttemptModel.workspace_id == self.workspace_id,
                )
            ))
            generation_attempts = attempts
            recovery = initial_render_recovery(row, latest, attempts)
            if recovery is not None:
                state["generationRecovery"] = recovery
        if not stopped:
            from .analysis_progress import public_analysis_progress

            progress_operation = operation or latest
            render_operation = progress_operation
            if (
                progress_operation
                and progress_operation.result_json.get("kind")
                in {"timeline", "compose", "accept", "approval", "export", "inspection", "repair"}
                and callable(getattr(self.repository, "latest_render_operation", None))
            ):
                render_operation = await self.repository.latest_render_operation(project_id)
            if render_operation and render_operation.result_json.get("kind") == "render":
                from .generation_progress import present_generation_progress

                if generation_attempts is None and getattr(
                    getattr(self.repository, "session", None), "scalars", None
                ) is not None:
                    from sqlalchemy import select

                    from .budget_models import SmartRemakeAttemptModel

                    generation_attempts = list(await self.repository.session.scalars(
                        select(SmartRemakeAttemptModel).where(
                            SmartRemakeAttemptModel.project_id == row.id,
                            SmartRemakeAttemptModel.workspace_id == self.workspace_id,
                        )
                    ))
                generation = await present_generation_progress(
                    row, render_operation, workspace_id=self.workspace_id,
                    attempts=generation_attempts, media=self.media,
                )
                if generation is not None:
                    state["generationProgress"] = generation
            retry_disposition = None
            if (
                not operation and latest and latest.status == "failed"
                and latest.result_json.get("kind") == "compile"
                and getattr(self.repository, "session", None) is not None
            ):
                from sqlalchemy import select

                from .budget_models import SmartRemakeAttemptModel
                from .generation_recovery import analysis_retry_disposition

                attempts = list(await self.repository.session.scalars(
                    select(SmartRemakeAttemptModel).where(
                        SmartRemakeAttemptModel.project_id == row.id,
                        SmartRemakeAttemptModel.workspace_id == self.workspace_id,
                    )
                ))
                retry_disposition = analysis_retry_disposition(
                    row, latest, attempts, workspace_id=self.workspace_id,
                )
            progress = public_analysis_progress(
                progress_operation, retry_disposition=retry_disposition,
            ) if progress_operation else None
            if progress is not None:
                state["analysisProgress"] = progress
        return state

    async def _reconcile(
        self, row: SmartRemakeProjectModel, operation: SmartRemakeOperationModel
    ) -> None:
        tasks = operation.result_json.get("providerTasks") or []
        if not tasks:
            return
        last = tasks[-1]
        ids = last.get("requestIds") or []
        if not ids:
            return
        try:
            data = await _reconciled_media(last)
            if data is None:
                return
            request = operation.result_json.get("request")
            scene_id = operation.result_json.get("sceneId")
            if not request or not scene_id:
                return
            try:
                key = await self.media.put(
                    f"workspaces/{self.workspace_id}/smart-remake/{row.id}", data, "video/mp4"
                )
            except Exception:
                # Keep the persisted task unresolved; a later refresh retries
                # the same completed output without submitting provider work.
                return
            version = await run_in_threadpool(
                _new_version,
                data,
                key,
                request,
                request.get("baseVersionId"),
                {"providerRequestId": ids[-1]},
                source="regenerated",
                audio_required=row.context_json["audioRequired"],
            )
            current = await self.repository.project(self.workspace_id, row.id, lock=True)
            active = await self.repository.running(row.id)
            if not active or active.id != operation.id:
                return
            state = copy.deepcopy(current.state_json)
            scene = _scene(state, scene_id)
            scene["versions"] = [*scene["versions"], version]
            await self.repository.complete(
                current,
                state,
                operation,
                {
                    **operation.result_json,
                    "needsReconciliation": False,
                    "candidateVersionId": version["id"],
                },
            )
        except SmartRemakeError as exc:
            if exc.code in {"UNIFICALLY_TASK_FAILED", "FLOWKIT_VIDEO_GENERATION_FAILED"}:
                await self.repository.finish(
                    operation,
                    "failed",
                    {
                        **operation.result_json,
                        "errorCode": exc.code,
                    },
                )

    async def recoverable_project_id(self) -> str | None:
        if self.render_project_id is None:
            return None
        row = await self.repository.project(self.workspace_id, self.render_project_id)
        return str(row.id) if any(scene["versions"] for scene in row.state_json["scenes"]) else None

    async def begin_render(
        self, input_data: RenderSmartRemakeInput
    ) -> Callable[[int, bytes, dict[str, Any]], Awaitable[None]]:
        project_id = uuid4()
        prefix = f"workspaces/{self.workspace_id}/smart-remake/{project_id}"
        # Preflight private storage before any provider job is submitted.
        try:
            product_key = await self.media.put(
                prefix, input_data.productImage.bytes, input_data.productImage.mime_type
            )
        except Exception as exc:
            raise AppError(
                "SMART_REMAKE_RETENTION_UNAVAILABLE",
                "Scene repair storage is unavailable. No video job was submitted.",
                503,
            ) from exc
        reference = copy.deepcopy(input_data.referenceAnalysis)
        context = {
            "sceneMap": copy.deepcopy(input_data.sceneMap),
            "productLock": input_data.productLock,
            "referenceAnalysis": reference,
            "productKey": product_key,
            "productMimeType": input_data.productImage.mime_type,
            "audioRequired": input_data.audioRequired,
            "projectName": input_data.projectName,
            "textOverlays": _text_overlays(input_data.sceneMap["scenes"]),
        }
        audio_plan = (reference or {}).get("audioPlan") or {}
        music = audio_plan.get("referenceMusic") or {}
        asset_id = music.get("assetId")
        if isinstance(asset_id, str) and Path(asset_id).name == asset_id:
            music_path = AUDIO_ASSET_DIR / f"{asset_id}.m4a"
            if music_path.is_file():
                context["musicKey"] = await self.media.put(
                    prefix, music_path.read_bytes(), "audio/mp4"
                )
        scenes = []
        for index, compiled in enumerate(input_data.sceneMap["scenes"]):
            scenes.append(
                {
                    "id": str(uuid4()),
                    "index": index,
                    "startSecond": index * 8,
                    "durationSeconds": 8,
                    "activeVersionId": None,
                    "versions": [],
                    **{key: compiled[key] for key in ("prompt", "imagePrompt", "videoPrompt")},
                }
            )
        state = {
            "id": str(project_id),
            "revision": 1,
            "status": "incomplete",
            "finalVideoUrl": "",
            "targetDuration": input_data.sceneMap["targetDuration"],
            "provider": input_data.provider,
            "scenes": scenes,
        }
        await self.repository.create(
            SmartRemakeProjectModel(
                id=project_id,
                workspace_id=self.workspace_id,
                revision=1,
                state_json=state,
                context_json=context,
            )
        )
        self.render_project_id = project_id
        return self.capture_render_output

    async def capture_render_output(
        self, index: int, data: bytes, metadata: dict[str, Any]
    ) -> None:
        project_id = self.render_project_id
        assert project_id is not None
        prefix = f"workspaces/{self.workspace_id}/smart-remake/{project_id}"
        key = await self.media.put(prefix, data, "video/mp4")
        row = await self.repository.project(self.workspace_id, project_id, lock=True)
        state = copy.deepcopy(row.state_json)
        if index == -1:
            check = await run_in_threadpool(
                technical_check,
                data,
                expected_duration=state["targetDuration"],
                audio_required=row.context_json["audioRequired"],
            )
            state["assemblyCheck"] = check
            if check["status"] != "passed" or any(
                not scene["activeVersionId"] for scene in state["scenes"]
            ):
                await self.repository.save(row, state)
                raise AppError(
                    "SMART_REMAKE_TECHNICAL_CHECK_FAILED",
                    "The rendered video has technical issues. "
                    "Review retained scenes before regenerating.",
                )
            state["finalStorageKey"] = key
            state["status"] = "ready"
        else:
            scene = state["scenes"][index]
            version = await run_in_threadpool(
                _new_version,
                data,
                key,
                scene,
                None,
                metadata,
                source="generated",
                audio_required=row.context_json["audioRequired"],
            )
            passed = version["technicalCheck"]["status"] == "passed"
            version["usedByRevision"] = 1 if passed else None
            scene["versions"] = [*scene["versions"], version]
            scene["activeVersionId"] = version["id"] if passed else None
        await self.repository.save(row, state)

    async def _operation_result(
        self, project_id: UUID, operation: SmartRemakeOperationModel
    ) -> dict[str, Any]:
        from .provider_errors import public_provider_error_fields
        from .provider_group_repair import group_repair_public_fields

        project = await self.get(project_id)
        group_fields = {}
        if operation.result_json.get("repairGroup"):
            row = await self.repository.project(self.workspace_id, project_id)
            group_fields = group_repair_public_fields(row.state_json, operation)

        return {
            "project": project,
            "operationId": str(operation.id),
            "status": operation.status,
            **public_provider_error_fields(operation.result_json),
            **{
                key: value
                for key, value in operation.result_json.items()
                if key
                in {
                    "candidateVersionId",
                    "errorCode",
                    "needsReconciliation",
                }
            },
            **group_fields,
        }

    async def repair(
        self, project_id: UUID, scene_id: UUID, request: RepairSceneRequest
    ) -> dict[str, Any]:
        payload = request.model_dump(mode="json", exclude={"idempotencyKey"})
        row, operation, created = await self.repository.start(
            self.workspace_id,
            project_id,
            request.idempotencyKey,
            _request_hash("regenerate", scene_id, payload),
        )
        if not created:
            return await self._operation_result(project_id, operation)
        try:
            _revision(row.state_json, request.expectedRevision)
            scene = _scene(row.state_json, scene_id)
            base_id = str(request.baseVersionId) if request.baseVersionId else None
            if scene["activeVersionId"] != base_id:
                raise ConflictError(
                    "SMART_REMAKE_BASE_VERSION_CONFLICT", "The active scene version changed."
                )
            if base_id:
                _version(scene, base_id)
            context = row.context_json
            await self.repository.finish(
                operation,
                "running",
                {
                    "kind": "repair",
                    "sceneId": str(scene_id),
                    "sceneIndex": scene["index"],
                    "request": payload,
                },
            )
            if request.repairIntent is not None:
                from .generation_expectations import (
                    build_generation_expectations,
                    expectations_hash,
                )
                from .repair_intent import (
                    NORMALIZER_VERSION,
                    apply_repair_result,
                    fixture_repair_result,
                    repair_base_scene,
                )

                async def save_normalization(op: Any, result: dict[str, Any]) -> None:
                    await self.repository.finish(op, "running", result)

                compiled = repair_base_scene(row, scene)
                await save_normalization(operation, {
                    **operation.result_json, "repairBaseScene": compiled,
                    "repairNormalization": {"version": NORMALIZER_VERSION, "phase": "prepared"},
                })
                if self.settings and self.settings.ai_mode.strip().lower() in {"fixture", "mock"}:
                    result = fixture_repair_result(compiled, request.repairIntent)
                    compiled = apply_repair_result(compiled, result, context)
                    await save_normalization(operation, {
                        **operation.result_json, "compiledScene": compiled,
                        "repairNormalization": {
                            "version": NORMALIZER_VERSION, "phase": "resolved",
                            "result": result, "reason": result["reason"], "fixture": True,
                        },
                    })
                else:
                    from .repair_intent_workflow import resolve_repair_intent

                    await resolve_repair_intent(self, row, operation, save=save_normalization)
                    compiled = operation.result_json["compiledScene"]
                scenes = copy.deepcopy(context["sceneMap"]["scenes"])
                scenes[scene["index"]] = compiled
                snapshot = build_generation_expectations(context, scenes=scenes)
                await save_normalization(operation, {
                    **operation.result_json, "generationExpectations": snapshot,
                    "expectationsHash": expectations_hash(snapshot),
                })
            else:
                compiled = copy.deepcopy(context["sceneMap"]["scenes"][scene["index"]])
                for field in ("prompt", "imagePrompt", "videoPrompt"):
                    original_field = f"original{field[0].upper()}{field[1:]}"
                    # Retain legacy prompt-diff behavior for existing callers.
                    compiled[original_field] = compiled.get(original_field, compiled[field])
                compiled.update({key: payload[key] for key in (
                    "prompt", "imagePrompt", "videoPrompt"
                )})
                compiled["promptEdited"] = True
            if row.state_json["provider"] == "unifically":
                scene_edit_directions(compiled)
            validate_sanitized_compiler_prompts(
                prompt=compiled["prompt"],
                image_prompt=compiled["imagePrompt"],
                video_prompt=compiled["videoPrompt"],
                analysis=context["referenceAnalysis"] or {},
                product_lock=context["productLock"],
                timeline=compiled.get("shotPlan") or {},
            )
            # Source frames stay analysis-only; the raw product is the identity reference.
            compiled.pop("sourceFrame", None)
            compiled.pop("sourceFrames", None)
            reference = copy.deepcopy(context["referenceAnalysis"])
            music = ((reference or {}).get("audioPlan") or {}).get("referenceMusic")
            if isinstance(music, dict):
                music.pop("assetId", None)
            product_bytes = await self.media.read(context["productKey"])
            captured = []

            async def capture(index: int, data: bytes, metadata: dict[str, Any]) -> None:
                if index == 0:
                    captured.append((data, metadata))

            async def record_task(metadata: dict[str, Any]) -> None:
                await self.repository.finish(
                    operation,
                    "running",
                    {
                        **operation.result_json,
                        "providerTasks": [
                            *operation.result_json.get("providerTasks", []),
                            metadata,
                        ],
                    },
                )

            result = await render_smart_remake(
                RenderSmartRemakeInput(
                    productLock=context["productLock"],
                    sceneMap={
                        **context["sceneMap"],
                        "targetDuration": 8,
                        "sceneCount": 1,
                        "scenes": [compiled],
                    },
                    referenceAnalysis=reference,
                    productImage=UploadedMedia(
                        bytes=product_bytes,
                        mime_type=context["productMimeType"],
                        file_name="product-reference",
                    ),
                    projectName=context["projectName"],
                    provider=row.state_json["provider"],
                    audioRequired=context["audioRequired"],
                ),
                on_scene_output=capture,
                on_task_submitted=record_task,
            )
            if result.get("status") != "completed" or len(captured) != 1:
                raise AppError(
                    "SMART_REMAKE_SCENE_PENDING",
                    "The provider has not returned a completed scene.",
                    409,
                )
            data, metadata = captured[0]
            if request.repairIntent is not None:
                metadata = {
                    **metadata, "sourceOperationId": str(operation.id),
                    "repairIntent": payload["repairIntent"],
                    "repairNormalizerVersion": NORMALIZER_VERSION,
                    "generationExpectations": operation.result_json["generationExpectations"],
                    "expectationsHash": operation.result_json["expectationsHash"],
                }
            key = await self.media.put(
                f"workspaces/{self.workspace_id}/smart-remake/{project_id}", data, "video/mp4"
            )
            version = await run_in_threadpool(
                _new_version,
                data,
                key,
                compiled if request.repairIntent is not None else payload,
                base_id,
                metadata,
                source="regenerated",
                audio_required=context["audioRequired"],
            )
            row = await self.repository.project(self.workspace_id, project_id, lock=True)
            active = await self.repository.running(project_id)
            if not active or active.id != operation.id:
                await self.repository.refresh(operation)
                await self.repository.finish(operation, operation.status, operation.result_json)
                return await self._operation_result(project_id, operation)
            state = copy.deepcopy(row.state_json)
            updated = _scene(state, scene_id)
            updated["versions"] = [*updated["versions"], version]
            await self.repository.complete(
                row,
                state,
                operation,
                {**operation.result_json, "candidateVersionId": version["id"]},
            )
            return await self._operation_result(project_id, operation)
        except Exception as exc:
            await self.repository.refresh(operation)
            if operation.status == "completed":
                return await self._operation_result(project_id, operation)
            if getattr(exc, "code", "") in {
                "SMART_REMAKE_MODEL_ATTEMPT_UNCERTAIN",
                "SMART_REMAKE_ATTEMPT_RECONCILIATION_REQUIRED",
            } or _ambiguous_provider_failure(
                exc, submitted=bool(operation.result_json.get("providerTasks"))
            ):
                await self.repository.finish(
                    operation,
                    "running",
                    {
                        **operation.result_json,
                        "needsReconciliation": True,
                        "errorCode": getattr(exc, "code", "SMART_REMAKE_PROVIDER_UNRESOLVED"),
                    },
                )
                raise AppError(
                    "SMART_REMAKE_OPERATION_UNRESOLVED",
                    "The provider may still be processing this scene. No new job was submitted; "
                    "refresh and reconcile the existing request before retrying.",
                    409,
                    {"operationStatus": "running", "operationId": str(operation.id)},
                ) from exc
            await self.repository.finish(
                operation,
                "failed",
                {
                    **operation.result_json,
                    "errorCode": getattr(exc, "code", "SMART_REMAKE_REPAIR_FAILED"),
                },
            )
            details: dict[str, object] = {
                "operationStatus": "failed",
                "operationId": str(operation.id),
            }
            if isinstance(exc, AppError):
                exc.details = {**exc.details, **details}
                raise
            if isinstance(exc, SmartRemakeError):
                raise AppError(exc.code, str(exc), details=details) from exc
            raise AppError(
                "SMART_REMAKE_REPAIR_FAILED",
                "Scene repair could not finish. The active video was preserved.",
                503,
                details,
            ) from exc

    async def _compose(
        self, row: SmartRemakeProjectModel, state: dict[str, Any]
    ) -> tuple[bytes, dict[str, Any]]:
        had_native_audio = False
        with tempfile.TemporaryDirectory(prefix="smart-remake-assembly-") as tmp:
            paths = []
            for scene in state["scenes"]:
                if not scene["activeVersionId"]:
                    raise ConflictError(
                        "SMART_REMAKE_SCENE_MISSING",
                        "Generate every missing scene before assembling the video.",
                    )
                version = _version(scene, scene["activeVersionId"])
                if version["technicalCheck"]["status"] != "passed":
                    raise ConflictError(
                        "SMART_REMAKE_TECHNICAL_CHECK_FAILED",
                        "A scene has not passed technical checks.",
                    )
                path = Path(tmp) / f"{scene['index']}.mp4"
                data = await self.media.read(version["storageKey"])
                if hashlib.sha256(data).hexdigest() != version["mediaHash"]:
                    raise ConflictError(
                        "SMART_REMAKE_MEDIA_CHANGED",
                        "Stored scene media no longer matches this version.",
                    )
                probe = await run_in_threadpool(probe_media_bytes, data)
                has_audio = bool(probe.get("hasAudio"))
                had_native_audio = had_native_audio or has_audio
                if not has_audio:
                    data = await run_in_threadpool(with_silent_audio, data)
                path.write_bytes(data)
                paths.append(str(path))
            output = await concat_video_urls(
                video_urls=paths,
                title=row.context_json["projectName"],
                text_overlays=row.context_json.get("textOverlays", []),
            )
        music_key = row.context_json.get("musicKey")
        if music_key:
            asset_id = uuid4().hex
            AUDIO_ASSET_DIR.mkdir(parents=True, exist_ok=True)
            music_path = AUDIO_ASSET_DIR / f"{asset_id}.m4a"
            music_path.write_bytes(await self.media.read(music_key))
            try:
                output = await run_in_threadpool(
                    mux_reference_music, output, asset_id, had_native_audio
                )
            finally:
                music_path.unlink(missing_ok=True)
        check = await run_in_threadpool(
            technical_check,
            output,
            expected_duration=state["targetDuration"],
            audio_required=row.context_json["audioRequired"],
        )
        return output, check

    async def accept(self, project_id: UUID, request: AcceptSceneVersion) -> dict[str, Any]:
        payload = request.model_dump(mode="json", exclude={"idempotencyKey"})
        row, operation, created = await self.repository.start(
            self.workspace_id,
            project_id,
            request.idempotencyKey,
            _request_hash("accept", request.sceneId, payload),
        )
        if not created:
            if operation.result_json.get("repairScope") == "provider_group":
                from .project_preview import queue_automatic_preview

                await queue_automatic_preview(self, row, operation)
            return await self._operation_result(project_id, operation)
        try:
            _revision(row.state_json, request.expectedRevision)
            state = copy.deepcopy(row.state_json)
            scene = _scene(state, request.sceneId)
            version = _version(scene, request.versionId)
            if (
                version.get("usedByRevision") is None
                and version["parentVersionId"] != scene["activeVersionId"]
            ):
                raise ConflictError(
                    "SMART_REMAKE_CANDIDATE_STALE",
                    "This candidate was created from an older scene version. "
                    "Generate a new candidate from the active version.",
                )
            if version["technicalCheck"]["status"] != "passed":
                raise ConflictError(
                    "SMART_REMAKE_TECHNICAL_CHECK_FAILED",
                    "This version has not passed technical checks.",
                )
            scene["activeVersionId"] = version["id"]
            if state.get("schemaVersion") == 2:
                from .timeline_service import accept_timeline_version

                await accept_timeline_version(self, row, state, operation, scene, version)
                return await self._operation_result(project_id, operation)
            output, check = await self._compose(row, state)
            if check["status"] != "passed":
                raise ConflictError(
                    "SMART_REMAKE_ASSEMBLY_CHECK_FAILED",
                    "The assembled video failed technical checks.",
                )
            key = await self.media.put(
                f"workspaces/{self.workspace_id}/smart-remake/{project_id}", output, "video/mp4"
            )
            current = await self.repository.project(self.workspace_id, project_id, lock=True)
            _revision(current.state_json, request.expectedRevision)
            state["revision"] += 1
            version["usedByRevision"] = state["revision"]
            state["status"] = "ready"
            state["finalStorageKey"] = key
            state["assemblyCheck"] = check
            await self.repository.complete(current, state, operation, {})
            return await self._operation_result(project_id, operation)
        except Exception as exc:
            await self.repository.finish(
                operation,
                "failed",
                {"errorCode": getattr(exc, "code", "SMART_REMAKE_ACCEPT_FAILED")},
            )
            details: dict[str, object] = {
                "operationStatus": "failed",
                "operationId": str(operation.id),
            }
            if isinstance(exc, AppError):
                exc.details = {**exc.details, **details}
                raise
            if isinstance(exc, SmartRemakeError):
                raise AppError(exc.code, str(exc), details=details) from exc
            raise AppError(
                "SMART_REMAKE_ACCEPT_FAILED",
                "The video could not be assembled. The active video was preserved.",
                503,
                details,
            ) from exc

    async def check(self, project_id: UUID, scene_id: UUID, version_id: UUID) -> dict[str, Any]:
        row = await self.repository.project(self.workspace_id, project_id)
        version = _version(_scene(row.state_json, scene_id), version_id)
        data = await self.media.read(version["storageKey"])
        check = await run_in_threadpool(
            technical_check,
            data,
            expected_duration=(
                version.get("rawDurationFrames", 192) // 24
                if row.state_json.get("schemaVersion") == 2 else 8
            ),
            audio_required=bool((row.context_json.get("renderPlan") or {}).get(
                "audioRequired", row.context_json["audioRequired"],
            )),
        )
        if check["mediaHash"] != version["mediaHash"]:
            check = {
                **check,
                "status": "failed",
                "findings": [
                    *check["findings"],
                    "Stored media changed after this version was created.",
                ],
            }
        row = await self.repository.project(self.workspace_id, project_id, lock=True)
        state = copy.deepcopy(row.state_json)
        version = _version(_scene(state, scene_id), version_id)
        version["technicalCheck"] = check
        await self.repository.save(row, state)
        return {"project": await self.present(row), "technicalCheck": check}
