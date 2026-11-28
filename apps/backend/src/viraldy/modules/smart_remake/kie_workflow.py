"""Durable KIE operations. A committed submission intent is never posted twice."""

from __future__ import annotations

import asyncio
import copy
import hashlib
import json
from collections.abc import Callable
from time import monotonic
from typing import Any, Literal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from viraldy.modules.jobs.dispatcher import CeleryJobDispatcher
from viraldy.modules.jobs.models import ProcessingJobModel
from viraldy.modules.jobs.public import get_existing_idempotent_job
from viraldy.modules.jobs.registry import JobType
from viraldy.modules.jobs.service import JobService
from viraldy.platform.config.settings import Settings
from viraldy.platform.storage.s3 import S3StorageAdapter
from viraldy.shared.errors.base import AppError, ConflictError

from .engine.config import get_kie_poll_interval_seconds, get_kie_poll_timeout_seconds
from .engine.errors import SmartRemakeError
from .engine.kie_client import KieClient
from .engine.prompt_sanitizer import (
    validate_sanitized_compiler_prompts,
)
from .engine.schemas import RenderSmartRemakeInput, UploadedMedia
from .engine.wan_video_adapter import WAN_VIDEO_MODEL
from .engine.window_continuity import WINDOW_CONTINUITY_VERSION, build_window_context
from .generation_budget import (
    character_reference,
    generation_execution_receipt,
    mark_generation_submitted,
    recover_generation_task,
    require_generation_policy,
    reserve_generation_attempt,
    settle_generation_attempt,
)
from .generation_expectations import (
    build_generation_expectations,
    expectations_hash,
    expectations_scene,
    require_generation_expectations,
    validate_generation_expectations,
)
from .provider_errors import sanitize_provider_error
from .provider_group_request import conditioned_group_request
from .repair_media import RepairMediaStore
from .repair_repository import RepairRepository
from .repair_schemas import RepairSceneRequest
from .repair_service import RepairService, _new_version, _request_hash, _revision, _scene, _version
from .runtime_limits import kie_job_runtime_input

JOB_TYPE = JobType.SMART_REMAKE_KIE.value


def _fingerprint(value: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def _key(value: str) -> str:
    if not value or not value.strip() or len(value) > 200:
        raise AppError(
            "SMART_REMAKE_IDEMPOTENCY_KEY_REQUIRED", "A valid idempotency key is required."
        )
    return value.strip()


def _service(session: AsyncSession, settings: Settings, workspace_id: UUID) -> RepairService:
    return RepairService(
        RepairRepository(session),
        RepairMediaStore(S3StorageAdapter(settings)),
        workspace_id,
        settings=settings,
    )


async def _dispatch(session: AsyncSession, job_id: UUID) -> None:
    job = await session.get(ProcessingJobModel, job_id)
    if job is not None and job.status == "queued" and not job.task_id:
        # Separate creation from dispatch: the operation is committed before delivery.
        try:
            await JobService(session, CeleryJobDispatcher())._dispatch_created_job(job)
        except Exception as exc:
            raise AppError(
                "SMART_REMAKE_QUEUE_UNAVAILABLE",
                "The request was saved but could not reach the worker. Retry with the same key.",
                503,
                {"repairProjectId": str(job.subject_id), "processingJobId": str(job.id)},
            ) from exc


async def _render_response(
    service: RepairService, project_id: UUID, job_id: UUID
) -> dict[str, Any]:
    project = await service.get(project_id)
    return {
        "success": True,
        "mode": "smart_remake",
        "provider": "kie",
        "projectId": str(project_id),
        "repairProjectId": str(project_id),
        "processingJobId": str(job_id),
        "repairProject": project,
        "finalVideoUrl": project.get("finalVideoUrl", ""),
        "targetDuration": project["targetDuration"],
        "sceneCount": len(project["scenes"]),
        "renderSubmitted": True,
        "status": "completed" if project["status"] == "ready" else "submitted",
        "warnings": [],
    }


async def enqueue_kie_render(
    session: AsyncSession,
    settings: Settings,
    workspace_id: UUID,
    input_data: RenderSmartRemakeInput,
    idempotency_key: str,
) -> dict[str, Any]:
    from .service import require_kie_renderer

    require_kie_renderer(settings)
    key = _key(idempotency_key)
    request_hash = _fingerprint(
        {
            **input_data.model_dump(exclude={"productImage"}),
            "productHash": hashlib.sha256(input_data.productImage.bytes).hexdigest(),
            "productMimeType": input_data.productImage.mime_type,
        }
    )
    service = _service(session, settings, workspace_id)
    existing = await get_existing_idempotent_job(session, workspace_id, JOB_TYPE, key)
    if existing:
        if existing.input_json.get("request_hash") != request_hash:
            raise ConflictError(
                "SMART_REMAKE_IDEMPOTENCY_CONFLICT", "This key belongs to another render."
            )
        await _dispatch(session, existing.id)
        return await _render_response(service, existing.subject_id, existing.id)
    await service.begin_render(input_data)
    project_id = service.render_project_id
    assert project_id is not None
    row, operation, _ = await service.repository.start(
        workspace_id, project_id, "initial", request_hash
    )
    await service.repository.finish(operation, "running", {"kind": "render", "tasks": {}})
    job = await JobService(session).request_mvp_job(
        workspace_id,
        "smart_remake_project",
        project_id,
        JOB_TYPE,
        {
            "project_id": str(project_id),
            "operation_id": str(operation.id),
            "request_hash": request_hash,
            **kie_job_runtime_input(row.state_json, row.context_json, operation.result_json),
        },
        key,
    )
    if job.subject_id != project_id:
        # Concurrent callers may have prepared storage, but only the winning job runs.
        await session.delete(row)
        await session.commit()
        if job.input_json.get("request_hash") != request_hash:
            raise ConflictError(
                "SMART_REMAKE_IDEMPOTENCY_CONFLICT", "This key belongs to another render."
            )
    winning = await service.repository.running(job.subject_id)
    if winning:
        await service.repository.attach_processing_job(winning, job.id)
    await _dispatch(session, job.id)
    return await _render_response(service, job.subject_id, job.id)


async def enqueue_kie_repair(
    session: AsyncSession,
    settings: Settings,
    workspace_id: UUID,
    project_id: UUID,
    scene_id: UUID,
    request: RepairSceneRequest,
    *,
    actor_id: UUID | None = None,
) -> dict[str, Any]:
    from .service import require_kie_renderer

    require_kie_renderer(settings)
    service = _service(session, settings, workspace_id)
    payload = request.model_dump(mode="json", exclude={"idempotencyKey"})
    actor = {"actorId": str(actor_id)} if actor_id is not None else {}
    request_hash = _request_hash("regenerate", scene_id, {**payload, **actor})
    row, operation, created = await service.repository.start(
        workspace_id, project_id, request.idempotencyKey, request_hash
    )
    if not created and operation.status != "running":
        return await service._operation_result(project_id, operation)
    if created:
        try:
            plan = row.context_json.get("renderPlan") or {}
            if plan.get("imageModel"):
                from .service import require_openai_images

                require_openai_images(settings)
            _revision(row.state_json, request.expectedRevision)
            scene = _scene(row.state_json, scene_id)
            base_id = str(request.baseVersionId) if request.baseVersionId else None
            if scene["activeVersionId"] != base_id:
                raise ConflictError(
                    "SMART_REMAKE_BASE_VERSION_CONFLICT", "The active scene version changed."
                )
            if not base_id:
                raise AppError(
                    "SMART_REMAKE_BASE_VERSION_REQUIRED",
                    "Cảnh chưa có video để sửa. Hãy tạo video trước.", 409,
                )
            _version(scene, base_id)
            if request.repairIntent is not None:
                from .repair_intent import NORMALIZER_VERSION, repair_base_scene

                compiled = repair_base_scene(row, scene)
                directions = {
                    "repairBaseScene": compiled,
                    "repairNormalization": {"version": NORMALIZER_VERSION, "phase": "prepared"},
                }
            else:
                compiled = copy.deepcopy(row.context_json["sceneMap"]["scenes"][scene["index"]])
                for field in ("prompt", "imagePrompt", "videoPrompt"):
                    original = f"original{field[0].upper()}{field[1:]}"
                    compiled[original] = compiled.get(original, compiled[field])
                compiled.update(
                    {field: payload[field] for field in ("prompt", "imagePrompt", "videoPrompt")}
                )
                compiled["promptEdited"] = True
                compiled.pop("sourceFrame", None)
                compiled.pop("sourceFrames", None)
                validate_sanitized_compiler_prompts(
                    prompt=compiled["prompt"],
                    image_prompt=compiled["imagePrompt"],
                    video_prompt=compiled["videoPrompt"],
                    analysis=row.context_json["referenceAnalysis"] or {},
                    product_lock=row.context_json["productLock"],
                    timeline=compiled.get("shotPlan") or {},
                )
                directions = {"compiledScene": compiled}
            await service.repository.finish(
                operation,
                "running",
                {
                    "kind": "repair",
                    **actor,
                    "sceneId": str(scene_id),
                    "sceneIndex": scene["index"],
                    "request": payload,
                    **directions,
                    "tasks": {},
                    **(
                        {"renderPlan": copy.deepcopy(plan), "renderPlanHash": _fingerprint(plan)}
                        if plan.get("groups") or plan.get("imageModel")
                        else {}
                    ),
                },
            )
        except Exception as exc:
            await service.repository.finish(
                operation,
                "failed",
                {"kind": "repair", **actor,
                 "sceneId": str(scene_id), "request": payload,
                 "needsReconciliation": False,
                 "errorCode": getattr(exc, "code", "SMART_REMAKE_REPAIR_INVALID")},
            )
            raise
    job = await JobService(session).request_mvp_job(
        workspace_id,
        "smart_remake_project",
        project_id,
        JOB_TYPE,
        {
            "project_id": str(project_id),
            "operation_id": str(operation.id),
            "request_hash": request_hash,
            **kie_job_runtime_input(row.state_json, row.context_json, operation.result_json),
        },
        f"repair:{operation.id}",
    )
    await service.repository.attach_processing_job(operation, job.id)
    await _dispatch(session, job.id)
    return await service._operation_result(project_id, operation)


class KieWorkflow:
    def __init__(
        self,
        repair: RepairService,
        *,
        client: Any = None,
        image_client: Any = None,
        ensure_active: Callable[[], None] = lambda: None,
        poll_timeout_seconds: float | None = None,
    ) -> None:
        self.repair = repair
        self.client = client or KieClient()
        self.image_client = image_client
        self.ensure_active = ensure_active
        self.poll_timeout_seconds = poll_timeout_seconds

    async def _save(
        self, operation: Any, result: dict[str, Any], *, status: str = "running"
    ) -> None:
        self.ensure_active()
        await self.repair.repository.finish(operation, status, result)

    async def _freeze_plan(self, row: Any, operation: Any) -> dict[str, Any]:
        current = row.context_json.get("renderPlan") or {}
        saved = operation.result_json.get("renderPlan")
        tasks = operation.result_json.get("tasks", {}).values()
        # Upgrades never turn an existing paid intent into replacement work.
        if any(task.get("taskId") or task.get("status") == "submitting" for task in tasks):
            return dict(saved or current)
        if not operation.result_json.get("generationExpectations"):
            images = operation.result_json.get("images", {}).values()
            if any(image.get("status") == "submitting" for image in images):
                raise AppError(
                    "OPENAI_IMAGE_SUBMISSION_UNRESOLVED",
                    "The existing image request requires reconciliation, not a replacement.", 409,
                )
        require_generation_expectations(row.context_json)
        scenes = None
        if operation.result_json.get("compiledScene"):
            scenes = copy.deepcopy(row.context_json["sceneMap"]["scenes"])
            scenes[operation.result_json["sceneIndex"]] = operation.result_json["compiledScene"]
        snapshot = build_generation_expectations(row.context_json, scenes=scenes)
        frozen = operation.result_json.get("generationExpectations")
        if frozen is not None:
            validate_generation_expectations(frozen, operation.result_json.get("expectationsHash"))
            if expectations_hash(snapshot) != operation.result_json.get("expectationsHash"):
                raise ConflictError(
                    "SMART_REMAKE_EXPECTATIONS_CHANGED",
                    "The saved generation requirements changed.",
                )
        if saved is not None:
            expected = operation.result_json.get("renderPlanHash")
            if expected != _fingerprint(saved) or expected != _fingerprint(current):
                raise ConflictError(
                    "SMART_REMAKE_RENDER_PLAN_CHANGED", "The saved render plan changed."
                )
        fresh_policy: dict[str, str] = {}
        if (
            not operation.result_json.get("images") and not operation.result_json.get("tasks")
            and not operation.result_json.get("windowContinuityVersion")
            and current.get("videoModel") == WAN_VIDEO_MODEL
            and len(current.get("groups") or []) == 2
            and all(group.get("rawDurationFrames") == 144 for group in current["groups"])
        ):
            fresh_policy = {"windowContinuityVersion": WINDOW_CONTINUITY_VERSION}
        if frozen is None or current.get("groups") or current.get("imageModel"):
            await self._save(
                operation,
                {
                    **operation.result_json,
                    "renderPlan": copy.deepcopy(current),
                    "renderPlanHash": _fingerprint(current),
                    "generationExpectations": snapshot,
                    "expectationsHash": expectations_hash(snapshot),
                    **fresh_policy,
                },
            )
        return dict(current)

    async def _request(
        self, row: Any, operation: Any, index: int, group: dict[str, Any] | None
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        await require_generation_policy(self.repair, row)
        require_generation_expectations(row.context_json)
        if not operation.result_json.get("expectationsHash"):
            raise AppError(
                "SMART_REMAKE_EXPECTATIONS_REQUIRED",
                "The operation must retain its generation requirements before creating video.", 409,
            )
        snapshot = validate_generation_expectations(
            operation.result_json.get("generationExpectations"),
            operation.result_json.get("expectationsHash"),
        )
        if operation.result_json.get("referencePreparation") != "direct":
            await self._save(operation, {**operation.result_json, "referencePreparation": "direct"})
        snapshot_hash = expectations_hash(snapshot)
        override_scenes = None
        if operation.result_json.get("compiledScene"):
            override_scenes = copy.deepcopy(row.context_json["sceneMap"]["scenes"])
            override_scenes[operation.result_json["sceneIndex"]] = (
                operation.result_json["compiledScene"]
            )
        if snapshot_hash != expectations_hash(build_generation_expectations(
            row.context_json, scenes=override_scenes,
        )):
            raise ConflictError(
                "SMART_REMAKE_EXPECTATIONS_CHANGED", "The saved generation requirements changed."
            )
        character = await character_reference(self.repair, row)
        plan = operation.result_json.get("renderPlan") or row.context_json.get("renderPlan") or {}
        current_plan = row.context_json.get("renderPlan") or {}
        if (
            plan.get("videoModel"), plan.get("videoResolution") or "720P",
            plan.get("audioRequired"),
            [(group["rawDurationFrames"], group["targetDurationFrames"])
             for group in plan.get("groups") or []],
        ) != (
            current_plan.get("videoModel"), current_plan.get("videoResolution") or "720P",
            current_plan.get("audioRequired"),
            [(group["rawDurationFrames"], group["targetDurationFrames"])
             for group in current_plan.get("groups") or []],
        ):
            raise ConflictError(
                "SMART_REMAKE_RENDER_PLAN_CHANGED",
                "Reconcile submitted tasks before changing the saved video settings or duration.",
            )
        if not plan.get("imageModel"):
            raise AppError(
                "SMART_REMAKE_CONDITIONING_REQUIRED",
                "Update the script to prepare composed opening and final images before video.",
                409,
            )
        compiled = row.context_json["sceneMap"]["scenes"]
        indices = [index]
        if group is not None:
            units = {unit["id"]: unit for unit in plan["units"]}
            indices = [units[unit_id]["sceneIndex"] for unit_id in group["renderUnitIds"]]
        scenes = []
        for position in indices:
            unit_id = plan["units"][position]["id"]
            scene = expectations_scene(snapshot, unit_id)
            scenes.append({
                **{key: compiled[position][key] for key in (
                    "targetDurationFrames", "rawDurationFrames",
                ) if key in compiled[position]},
                **copy.deepcopy(scene),
            })
        segments = (
            group["segments"]
            if group is not None
            else [
                {
                    "renderUnitId": plan["units"][index]["id"],
                    "inFrame": 0,
                    "outFrame": plan["units"][index]["targetDurationFrames"],
                }
            ]
        )
        # Validate the combined prompt before paid image edits. These public
        # literal placeholders are never fetched, uploaded or sent to KIE.
        window_context = (
            build_window_context(plan, group, snapshot)
            if group is not None and operation.result_json.get("windowContinuityVersion")
            == WINDOW_CONTINUITY_VERSION else None
        )
        request = await asyncio.to_thread(
            conditioned_group_request, context=row.context_json, plan=plan, snapshot=snapshot,
            scenes=scenes, segments=segments, has_character_reference=bool(character),
            duration_seconds=(group or plan["units"][index]).get("rawDurationFrames", 192) // 24,
            window_context=window_context,
        )
        references: list[dict[str, Any]] = []
        from .image_workflow import prepare_scene_image

        if self.image_client is None:
            from .engine.openai_images import OpenAIImageClient

            if self.repair.settings is None:
                raise AppError(
                    "OPENAI_IMAGES_NOT_CONFIGURED", "OpenAI image settings are required.", 503
                )
            self.image_client = OpenAIImageClient(self.repair.settings)
        bookends: list[tuple[int, Literal["opening", "ending"]]] = [
            (0, "opening"), (len(indices) - 1, "ending"),
        ]
        for offset, frame_role in bookends:
            references.append(
                await prepare_scene_image(
                    repair=self.repair,
                    row=row,
                    operation=operation,
                    index=indices[offset],
                    compiled_scene=scenes[offset],
                    frame_role=frame_role,
                    image_client=self.image_client,
                    save=self._save,
                    ensure_active=self.ensure_active,
                )
            )
        product_data = await self.repair.media.read(row.context_json["productKey"])
        product_hash = row.context_json.get("productMediaHash")
        if product_hash is not None and hashlib.sha256(product_data).hexdigest() != product_hash:
            raise AppError(
                "SMART_REMAKE_INPUT_CHANGED", "The retained product reference changed.", 409
            )
        upload_media = []
        for reference in references:
            data = await self.repair.media.read(reference["storageKey"])
            if row.context_json.get("p0") and (
                hashlib.sha256(data).hexdigest() != reference["mediaHash"]
            ):
                raise AppError(
                    "SMART_REMAKE_INPUT_CHANGED", "The checked conditioning image changed.", 409
                )
            upload_media.append(UploadedMedia(
                bytes=data, mime_type=reference["mimeType"], file_name="scene-reference",
            ))
        # Upload these exact verified buffers; never reread storage after this check.
        urls = []
        for media in upload_media:
            await require_generation_policy(self.repair, row)
            urls.append(await self.client.upload_file(media))
        image_fields = (
            {"first_frame_url": urls[0], "last_frame_url": urls[1]}
            if request["model"] == WAN_VIDEO_MODEL else {"image_urls": urls}
        )
        request = {**request, "input": {**request["input"], **image_fields}}
        return request, references

    async def _task(
        self,
        row: Any,
        operation: Any,
        index: int,
        *,
        reconcile_only: bool,
        group: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        await require_generation_policy(self.repair, row)
        tasks = operation.result_json.get("tasks", {})
        key = f"group:{group['id']}" if group is not None else str(index)
        task = tasks.get(key, {})
        if not task.get("taskId") and task.get("attemptId"):
            known_id = await recover_generation_task(self.repair, row, task["attemptId"])
            if known_id:
                task = {**task, "taskId": known_id, "status": "submitted"}
                await self._save(operation, {
                    **operation.result_json, "tasks": {**tasks, key: task},
                    "needsReconciliation": False,
                })
        if not task.get("taskId"):
            if task.get("status") == "submitting":
                await self._save(
                    operation,
                    {
                        **operation.result_json,
                        "needsReconciliation": True,
                        "errorCode": "SMART_REMAKE_SUBMISSION_UNRESOLVED",
                    },
                )
                raise AppError(
                    "SMART_REMAKE_SUBMISSION_UNRESOLVED",
                    "KIE may have accepted this request. No new paid request was submitted.",
                    409,
                )
            if reconcile_only:
                return None
            request, references = await self._request(row, operation, index, group)
            api_contract = getattr(self.client, "api_contract", None)
            wire_binding = {"apiContract": api_contract} if isinstance(api_contract, str) else {}
            request_hash = _fingerprint({
                "model": request["model"],
                "input": {name: value for name, value in request["input"].items()
                          if name not in {"image_urls", "first_frame_url", "last_frame_url"}},
                "productHash": row.context_json.get("productMediaHash"),
                "characterHash": row.context_json.get("characterMediaHash"),
                "imageHashes": [reference["mediaHash"] for reference in references],
                "expectationsHash": operation.result_json["expectationsHash"],
                **wire_binding,
            })
            attempt, created = await reserve_generation_attempt(
                self.repair, row, operation, slot=f"video:{key}", request_hash=request_hash,
                stage="video", provider="kie", model=request["model"],
                profile={"model": request["input"].get("model", request["model"]), **{
                    name: request["input"][name] for name in (
                        "duration", "aspect_ratio", "resolution"
                    ) if name in request["input"]
                }} | wire_binding,
            )
            if not created and not attempt.provider_task_id:
                raise AppError(
                    "SMART_REMAKE_SUBMISSION_UNRESOLVED",
                    "The existing paid intent requires reconciliation; no request was repeated.",
                    409,
                )
            snapshot = {
                "model": request["model"],
                "input": {name: copy.deepcopy(value) for name, value in request["input"].items()
                          if name not in {"image_urls", "first_frame_url", "last_frame_url"}},
            } if created else task.get("videoRequest")
            task = {
                **({"attemptId": str(attempt.id)} if attempt else {}),
                **({"taskId": attempt.provider_task_id} if not created else {}),
                "status": "submitting",
                "requestHash": request_hash,
                "model": request["input"].get("model", request["model"]),
                "requestModel": request["model"],
                **({"videoRequest": snapshot} if snapshot else {}),
                **wire_binding,
                "imageReferences": references,
                "generationExpectations": copy.deepcopy(
                    operation.result_json["generationExpectations"]
                ),
                "expectationsHash": operation.result_json["expectationsHash"],
                **({"renderGroupId": group["id"], "group": copy.deepcopy(group)} if group else {}),
            }
            await self._save(
                operation,
                {
                    **operation.result_json,
                    "tasks": {**operation.result_json.get("tasks", {}), key: task},
                },
            )
            self.ensure_active()
            if created:
                try:
                    await mark_generation_submitted(self.repair, row, task.get("attemptId"))
                except AppError as exc:
                    await self._save(operation, {
                        **operation.result_json,
                        "tasks": {**operation.result_json.get("tasks", {}), key: {
                            **task, "status": "preflight_rejected", "errorCode": exc.code,
                        }},
                        "needsReconciliation": False,
                        "errorCode": exc.code,
                    }, status="failed")
                    raise
            try:
                submitted = (
                    await self.client.create_task(
                        model=request["model"], input_data=request["input"]
                    )
                    if created else {"task_id": attempt.provider_task_id}
                )
                task_id = submitted["task_id"]
            except Exception as exc:
                code = getattr(exc, "code", "")
                execution = generation_execution_receipt(
                    self.client, attempt_id=task.get("attemptId"), request_hash=request_hash,
                    provider="kie", model=request["model"], operation="kie.tasks.create",
                )
                details = getattr(exc, "details", None) or {}
                if isinstance(details, dict) and isinstance(details.get("providerError"), dict):
                    details = details["providerError"]
                provider_error = sanitize_provider_error(
                    details, secrets=(getattr(self.client, "api_key", ""),),
                )
                if code in {
                    "KIE_AUTH_FAILED",
                    "KIE_CREDITS_EXHAUSTED",
                    "KIE_RATE_LIMITED",
                    "KIE_VALIDATION_FAILED",
                    "KIE_TASK_CREATE_FAILED",
                }:
                    await settle_generation_attempt(
                        self.repair, row, task.get("attemptId"), status="failed",
                        receipt={"errorCode": code, **provider_error, **execution},
                    )
                    await self._save(
                        operation,
                        {
                            **operation.result_json,
                            "needsReconciliation": False,
                            "errorCode": code,
                            "providerError": provider_error,
                            "tasks": {**operation.result_json.get("tasks", {}), key: {
                                **task, "status": "rejected", "errorCode": code,
                                "providerError": provider_error,
                            }},
                        },
                        status="failed",
                    )
                    raise AppError(code, "KIE rejected this scene request.") from exc
                await settle_generation_attempt(
                    self.repair, row, task.get("attemptId"), status="unknown",
                    receipt={"errorCode": "SMART_REMAKE_SUBMISSION_UNRESOLVED",
                             **provider_error, **execution},
                )
                await self._save(
                    operation,
                    {
                        **operation.result_json,
                        "needsReconciliation": True,
                        "errorCode": "SMART_REMAKE_SUBMISSION_UNRESOLVED",
                        "providerError": provider_error,
                        "tasks": {**operation.result_json.get("tasks", {}), key: {
                            **task, "providerError": provider_error,
                            "errorCode": "SMART_REMAKE_SUBMISSION_UNRESOLVED",
                        }},
                    },
                )
                raise AppError(
                    "SMART_REMAKE_SUBMISSION_UNRESOLVED",
                    "KIE may have accepted this request. Reconcile it before trying again.",
                    409,
                ) from exc
            await mark_generation_submitted(
                self.repair, row, task.get("attemptId"), task_id=task_id,
                execution_evidence=generation_execution_receipt(
                    self.client, attempt_id=task.get("attemptId"), request_hash=request_hash,
                    provider="kie", model=request["model"], operation="kie.tasks.create",
                    task_id=task_id,
                ).get("executionEvidence") if created else None,
            )
            task = {**task, "status": "submitted", "taskId": task_id}
            await self._save(
                operation,
                {
                    **operation.result_json,
                    "tasks": {**operation.result_json["tasks"], key: task},
                },
            )
        deadline = monotonic() + (
            self.poll_timeout_seconds
            if self.poll_timeout_seconds is not None
            else get_kie_poll_timeout_seconds()
        )
        while True:
            self.ensure_active()
            try:
                if task.get("requestModel") == WAN_VIDEO_MODEL:
                    status = await self.client.get_task(task["taskId"], model=WAN_VIDEO_MODEL)
                else:
                    status = await self.client.get_task(task["taskId"])
            except SmartRemakeError as exc:
                provider_error = sanitize_provider_error(
                    exc.details, secrets=(getattr(self.client, "api_key", ""),),
                )
                await self._save(operation, {
                    **operation.result_json, "providerError": provider_error,
                    "providerTaskId": task["taskId"],
                    "tasks": {**operation.result_json.get("tasks", {}), key: {
                        **task, "providerError": provider_error, "errorCode": exc.code,
                    }},
                })
                raise
            # Remote JSON and injected fake clients cannot supply execution proof.
            receipt = {
                name: value for name, value in status.get("receipt", {}).items()
                if name not in {"executionEvidence", "terminalExecutionEvidence"}
            }
            if status["status"] in {"completed", "failed"}:
                terminal_proof = generation_execution_receipt(
                    self.client, attempt_id=task.get("attemptId"),
                    request_hash=str(task.get("requestHash") or ""), provider="kie",
                    model=task.get("requestModel") or "veo-3-1",
                    operation="kie.tasks.get", task_id=task["taskId"],
                ).get("executionEvidence")
                if terminal_proof is not None:
                    receipt["terminalExecutionEvidence"] = terminal_proof
            if status["status"] == "failed":
                provider_error = sanitize_provider_error(
                    status.get("providerError", {
                        "providerCode": status.get("error_code", status.get("failCode")),
                        "providerMessage": status.get("error_message"),
                    }),
                    secrets=(getattr(self.client, "api_key", ""),),
                )
                await settle_generation_attempt(
                    self.repair, row, task.get("attemptId"), status="failed",
                    receipt={
                        "providerTaskId": task["taskId"], "errorCode": "KIE_TASK_FAILED",
                        **receipt, **provider_error,
                    },
                    usage=status.get("usage"),
                )
                await self._save(
                    operation,
                    {
                        **operation.result_json, "errorCode": "KIE_TASK_FAILED",
                        "needsReconciliation": False, "providerError": provider_error,
                        "providerTaskId": task["taskId"],
                        "tasks": {**operation.result_json.get("tasks", {}), key: {
                            **task, "status": "failed", "errorCode": "KIE_TASK_FAILED",
                            "providerError": provider_error,
                        }},
                    },
                    status="failed",
                )
                raise AppError(
                    "KIE_TASK_FAILED",
                    "KIE could not generate this scene. The active version was preserved.",
                )
            if status["status"] == "completed":
                await settle_generation_attempt(
                    self.repair, row, task.get("attemptId"), status="completed",
                    receipt={"providerTaskId": task["taskId"], **receipt},
                    usage=status.get("usage"),
                )
                return {**task, "url": status.get("output", {}).get("video_url")}
            if reconcile_only:
                return None
            if monotonic() >= deadline:
                raise TimeoutError("KIE task is still processing")
            await asyncio.sleep(get_kie_poll_interval_seconds())

    async def _retain(self, row: Any, operation: Any, index: int, task: dict[str, Any]) -> None:
        row = await self.repair.repository.project(self.repair.workspace_id, row.id, lock=True)
        scene = row.state_json["scenes"][index]
        existing = next(
            (
                version
                for version in scene["versions"]
                if version.get("providerMetadata", {}).get("providerRequestId") == task["taskId"]
            ),
            None,
        )
        if existing:
            return
        if not task.get("url"):
            raise RuntimeError("KIE returned no video output")
        data = await self.client.download_file(task["url"])
        self.ensure_active()
        metadata = {
            "provider": "kie",
            "providerRequestId": task["taskId"],
            "sourceOperationId": str(operation.id),
            **{
                field: task[field]
                for field in (
                    "model", "requestHash", "imageReferences", "generationExpectations",
                    "expectationsHash",
                )
                if field in task
            },
        }
        if operation.result_json["kind"] == "render":
            if row.state_json.get("schemaVersion") == 2:
                from .timeline_service import retain_timeline_clip

                await retain_timeline_clip(self.repair, row, index, data, metadata)
                return
            self.repair.render_project_id = row.id
            await self.repair.capture_render_output(index, data, metadata)
            return
        from starlette.concurrency import run_in_threadpool

        key = await self.repair.media.put(
            f"workspaces/{self.repair.workspace_id}/smart-remake/{row.id}", data, "video/mp4"
        )
        request = operation.result_json["request"]
        prompts = (
            operation.result_json["compiledScene"] if request.get("repairIntent") else request
        )
        if request.get("repairIntent"):
            metadata.update(
                repairIntent=copy.deepcopy(request["repairIntent"]),
                repairNormalizerVersion=operation.result_json["repairNormalization"]["version"],
            )
        version = await run_in_threadpool(
            _new_version,
            data,
            key,
            prompts,
            request.get("baseVersionId"),
            metadata,
            source="regenerated",
            audio_required=bool(
                (operation.result_json.get("renderPlan")
                 or row.context_json.get("renderPlan") or {})
                .get("audioRequired", row.context_json["audioRequired"])
            ),
            expected_duration=(
                (operation.result_json.get("renderPlan") or row.context_json["renderPlan"])
                ["units"][index].get("rawDurationFrames", 192) // 24
                if row.state_json.get("schemaVersion") == 2 else 8
            ),
        )
        if row.state_json.get("schemaVersion") == 2:
            from .timeline_media import probe_timeline_media

            info = await run_in_threadpool(probe_timeline_media, data)
            plan = operation.result_json.get("renderPlan") or row.context_json["renderPlan"]
            target_frames = next(
                unit["targetDurationFrames"] for unit in plan["units"] if unit["id"] == scene["id"]
            )
            version.update(
                rawDurationFrames=next(
                    unit["rawDurationFrames"] for unit in plan["units"]
                    if unit["id"] == scene["id"]
                ),
                frameCount=info["frameCount"],
                suggestedInFrame=0,
                suggestedOutFrame=target_frames,
            )
            metadata.update(suggestedInFrame=0, suggestedOutFrame=target_frames)
        state = copy.deepcopy(row.state_json)
        state["scenes"][index]["versions"] = [*state["scenes"][index]["versions"], version]
        self.ensure_active()
        await self.repair.repository.complete(
            row,
            state,
            operation,
            {
                **operation.result_json,
                "needsReconciliation": False,
                "candidateVersionId": version["id"],
            },
        )

    async def _retain_group(self, row: Any, group: dict[str, Any], task: dict[str, Any]) -> None:
        from .timeline_service import retain_timeline_group_clip

        row = await self.repair.repository.project(self.repair.workspace_id, row.id, lock=True)
        members = [
            scene for scene in row.state_json["scenes"] if scene["id"] in group["renderUnitIds"]
        ]
        if len(members) == len(group["renderUnitIds"]) and all(
            any(
                version.get("providerMetadata", {}).get("providerRequestId") == task["taskId"]
                and version.get("providerMetadata", {}).get("renderGroupId") == group["id"]
                for version in scene["versions"]
            )
            for scene in members
        ):
            return
        if not task.get("url"):
            raise RuntimeError("KIE returned no video output")
        data = await self.client.download_file(task["url"])
        self.ensure_active()
        metadata = {
            "provider": "kie",
            "providerRequestId": task["taskId"],
            "renderGroupId": group["id"],
            **{
                field: task[field]
                for field in (
                    "model", "requestHash", "imageReferences", "generationExpectations",
                    "expectationsHash",
                )
                if field in task
            },
        }
        await retain_timeline_group_clip(self.repair, row, group, data, metadata)

    async def execute(
        self, project_id: UUID, operation_id: UUID, *, reconcile_only: bool = False
    ) -> dict[str, Any]:
        async with self.repair.repository.execution_guard(operation_id) as acquired:
            if not acquired:
                if reconcile_only:
                    return {"project_id": str(project_id), "status": "running"}
                raise RuntimeError("Another executor is reconciling this KIE operation.")
            return await self._execute(project_id, operation_id, reconcile_only=reconcile_only)

    async def _execute(
        self, project_id: UUID, operation_id: UUID, *, reconcile_only: bool
    ) -> dict[str, Any]:
        row = await self.repair.repository.project(self.repair.workspace_id, project_id)
        operation = await self.repair.repository.operation(
            self.repair.workspace_id, project_id, operation_id
        )
        if operation.status != "running":
            return {
                "project_id": str(project_id),
                "operation_id": str(operation_id),
                "status": operation.status,
            }
        indices = (
            [operation.result_json["sceneIndex"]]
            if operation.result_json["kind"] == "repair"
            else range(len(row.state_json["scenes"]))
        )
        current_key = ""
        try:
            if operation.result_json.get("request", {}).get("repairIntent") and not any(
                task.get("taskId") or task.get("status") == "submitting"
                for task in operation.result_json.get("tasks", {}).values()
            ):
                from .repair_intent_workflow import resolve_repair_intent

                resolved = await resolve_repair_intent(
                    self.repair, row, operation, save=self._save, reconcile_only=reconcile_only
                )
                if not resolved:
                    return {"project_id": str(project_id), "status": "running"}
            plan = await self._freeze_plan(row, operation)
            groups = plan.get("groups") if operation.result_json["kind"] == "render" else None
            work = (
                [(0, group) for group in groups] if groups else [(index, None) for index in indices]
            )
            for index, group in work:
                current_key = f"group:{group['id']}" if group is not None else str(index)
                task = await self._task(
                    row, operation, index, reconcile_only=reconcile_only, group=group
                )
                if task is None:
                    return {"project_id": str(project_id), "status": "running"}
                if group is not None:
                    await self._retain_group(row, group, task)
                else:
                    await self._retain(row, operation, index, task)
            if operation.result_json["kind"] == "render":
                row = await self.repair.repository.project(self.repair.workspace_id, project_id)
                if row.state_json.get("schemaVersion") == 2:
                    # Retained raw clips are only suggestions. Seller confirms
                    # fixed-duration ranges before the separate compose job.
                    await self._save(
                        operation,
                        {**operation.result_json, "needsReconciliation": False},
                        status="completed",
                    )
                    return {
                        "project_id": str(project_id),
                        "operation_id": str(operation_id),
                        "status": "completed",
                    }
                if row.state_json.get("status") != "ready":
                    data, _ = await self.repair._compose(row, row.state_json)
                    self.ensure_active()
                    self.repair.render_project_id = project_id
                    await self.repair.capture_render_output(-1, data, {"provider": "kie"})
                await self._save(
                    operation,
                    {**operation.result_json, "needsReconciliation": False},
                    status="completed",
                )
            return {
                "project_id": str(project_id),
                "operation_id": str(operation_id),
                "status": "completed",
            }
        except AppError as exc:
            # Budget/policy rejection can roll back and expire both ORM rows.
            # Load the committed receipt explicitly before reading its fields.
            operation = await self.repair.repository.operation(
                self.repair.workspace_id, project_id, operation_id
            )
            if exc.code in {
                "OPENAI_IMAGE_SUBMISSION_UNRESOLVED",
                "SMART_REMAKE_MODEL_ATTEMPT_UNCERTAIN",
                "SMART_REMAKE_ATTEMPT_RECONCILIATION_REQUIRED",
            }:
                await self._save(
                    operation,
                    {
                        **operation.result_json,
                        "needsReconciliation": True,
                        "errorCode": exc.code,
                    },
                )
            if (
                exc.code
                not in {
                    "SMART_REMAKE_SUBMISSION_UNRESOLVED",
                    "OPENAI_IMAGE_SUBMISSION_UNRESOLVED",
                    "SMART_REMAKE_MODEL_ATTEMPT_UNCERTAIN",
                    "SMART_REMAKE_ATTEMPT_RECONCILIATION_REQUIRED",
                    "JOB_ATTEMPT_SUPERSEDED",
                    "JOB_ATTEMPT_NOT_CLAIMED",
                }
                and operation.status == "running"
            ):
                await self._save(
                    operation,
                    {
                        **operation.result_json,
                        "needsReconciliation": False,
                        "errorCode": exc.code,
                    },
                    status="failed",
                )
            raise
        except Exception as exc:
            self.ensure_active()
            operation = await self.repair.repository.operation(
                self.repair.workspace_id, project_id, operation_id
            )
            current_task = operation.result_json.get("tasks", {}).get(current_key, {})
            if not current_task.get("taskId") and current_task.get("status") != "submitting":
                code = getattr(exc, "code", "KIE_PREPARATION_FAILED")
                await self._save(
                    operation,
                    {
                        **operation.result_json,
                        "needsReconciliation": False,
                        "errorCode": code,
                    },
                    status="failed",
                )
                raise AppError(
                    code, "The scene could not be prepared. No generation was submitted.", 503
                ) from exc
            await self._save(
                operation,
                {
                    **operation.result_json,
                    "needsReconciliation": True,
                    "errorCode": "KIE_OUTPUT_PENDING",
                },
            )
            raise RuntimeError(
                "KIE output retrieval can be retried without a new generation."
            ) from exc


async def reconcile_kie_project(service: RepairService, row: Any, operation: Any) -> None:
    """A manual refresh only retrieves recorded tasks; it never creates paid work."""
    try:
        if service.settings is not None:
            from .service import require_kie_renderer

            require_kie_renderer(service.settings)
        job_id = operation.result_json.get("processingJobId")
        if job_id:
            await _dispatch(service.repository.session, UUID(job_id))
        if not operation.result_json.get("needsReconciliation"):
            return
        await KieWorkflow(service).execute(row.id, operation.id, reconcile_only=True)
    except (AppError, RuntimeError):
        # Persisted safe error and pending status remain visible to the seller.
        return
