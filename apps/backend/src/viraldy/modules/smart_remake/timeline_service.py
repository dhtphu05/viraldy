"""Owned Timeline v2 drafts, explicit review, and provider-free publishing."""

from __future__ import annotations

import copy
import hashlib
from collections.abc import Callable
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from viraldy.modules.jobs.registry import JobType
from viraldy.modules.jobs.service import JobService
from viraldy.platform.config.settings import Settings
from viraldy.shared.errors.base import AppError

from .assembly_snapshots import (
    assembly_expectations,
    assembly_manifest,
    content_hash,
    record_assembly,
)
from .generation_expectations import (
    build_generation_expectations,
    expectations_hash,
    require_generation_expectations,
)
from .project_intake import assert_input_binding
from .project_policy import assert_project_policy, constraints_hash, policy_hash
from .repair_schemas import PublishTimelineRequest, SaveTimelineRequest
from .repair_service import RepairService, _new_version, _request_hash, _revision, _scene, _version
from .timeline_manifest import validate_timeline_structure
from .timeline_media import (
    compose_timeline,
    probe_timeline_media,
    validate_selection_media,
    validate_trim,
)
from .timeline_planner import build_render_groups
from .timeline_retention import (
    _finish_retention,
    _invalidate_current,
    _release_reads,
    _remember_media,
)
from .timeline_schemas import RenderPlan


def _validate_group_plan(plan: dict[str, Any], used_ids: set[str]) -> None:
    RenderPlan.model_validate(plan)
    if "groups" not in plan:
        if plan.get("groupingPolicy") == "fixed_provider_windows" or any(
            plan.get(key)
            for key in (
                "videoModel", "videoResolution", "imageModel", "imageQuality",
                "imageComplexity", "imageSize",
            )
        ):
            raise ValueError("Provider configuration requires saved render groups.")
        return
    if (
        plan.get("videoModel") not in {"veo3_lite", "wan/3-0-video"}
        or plan.get("imageModel") not in {"gpt-image-2.6-sunburst", "gpt-image-2.6-flare"}
        or plan.get("imageQuality") not in {"low", "medium", "high", "xhigh", "max"}
        or plan.get("imageSize") != "720x1280"
    ):
        raise ValueError("The grouped provider configuration is incomplete.")
    if plan["videoModel"] == "veo3_lite" and (plan.get("videoResolution") or "720P") != "720P":
        raise ValueError("The saved Veo contract requires 720P resolution.")
    if (plan["imageModel"] == "gpt-image-2.6-sunburst" or "imageComplexity" in plan) and plan.get(
        "imageComplexity"
    ) not in {"low", "medium", "high"}:
        raise ValueError("The saved image complexity is invalid.")
    try:
        build_render_groups(
            plan["units"], render_group_breaks=plan.get("renderGroupBreaks", [])
        )
    except AppError as exc:
        raise ValueError("Invalid saved group boundaries.") from exc
    groups = plan["groups"]
    if not isinstance(groups, list) or not groups:
        raise ValueError("Saved groups do not cover the planned scenes.")
    fixed = plan.get("groupingPolicy") == "fixed_provider_windows"
    if fixed:
        total_frames = sum(unit["targetDurationFrames"] for unit in plan["units"])
        if (
            plan.get("renderGroupBreaks")
            or total_frames not in (192, 384)
            or len(groups) != total_frames // 192
            or any(group["targetDurationFrames"] != 192 for group in groups)
        ):
            raise ValueError(
                "A fixed provider plan needs exactly one complete eight-second window per call."
            )
    boundaries, cursor = [], 0
    for group in groups[:-1]:
        cursor += len(group["renderUnitIds"])
        boundaries.append(cursor)
    if not set(plan.get("renderGroupBreaks") or []) <= set(boundaries):
        raise ValueError("Saved groups must retain every explicit group boundary.")
    try:
        expected = build_render_groups(plan["units"], render_group_breaks=boundaries)
    except AppError as exc:
        raise ValueError("Invalid frozen provider group boundaries.") from exc
    if len(groups) != len(expected):
        raise ValueError("Saved groups do not cover the planned scenes.")
    for group, packed in zip(groups, expected, strict=True):
        if not group["id"] or group["id"] in used_ids:
            raise ValueError("Render group IDs must be independent and unique.")
        used_ids.add(group["id"])
        if {key: value for key, value in group.items() if key != "id"} != {
            key: value for key, value in packed.items() if key != "id"
        }:
            raise ValueError("Saved group timing must match contiguous whole scenes.")


def validate_manifest(row: Any) -> None:
    """Timing comes exclusively from the saved compiler manifest."""

    state, context = row.state_json, row.context_json
    try:
        ids = validate_timeline_structure(state, context)
        _validate_group_plan(state["renderPlan"], ids)
    except (KeyError, TypeError, ValueError) as exc:
        raise AppError(
            "SMART_REMAKE_TIMELINE_INVALID",
            "The saved timeline must preserve the source scenes and their assigned "
            "output ranges within the eight-second provider clips.",
        ) from exc


def _ready(timeline: dict[str, Any]) -> None:
    if any(not item.get("versionId") or not item.get("reviewed") for item in timeline["items"]):
        raise AppError(
            "SMART_REMAKE_TIMELINE_UNREVIEWED",
            "Choose and confirm a clip range for every scene before assembling.",
        )


def _assert_in_use(row: Any) -> None:
    if row.context_json.get("p0", {}).get("deletion", {}).get("status") not in (
        None,
        "cancelled",
    ):
        raise AppError(
            "SMART_REMAKE_USE_STOPPED", "This project's assets are no longer in use.", 403
        )


def _compose_policy(row: Any, frozen: dict[str, Any] | None = None) -> None:
    _assert_in_use(row)
    if not row.context_json.get("p0"):
        return
    assert_project_policy(row, purpose="export")
    if frozen is not None and (
        not frozen.get("actorId")
        or frozen.get("constraintsHash") != constraints_hash(row.context_json)
        or frozen.get("policyHash") != policy_hash(row.context_json)
    ):
        raise AppError(
            "SMART_REMAKE_COMPOSE_POLICY_CHANGED",
            "The saved requirements or rights changed. Assemble a new preview.",
            409,
        )
    if frozen is not None and frozen.get("expectationsHash"):
        current = assembly_expectations(
            row.state_json["draftTimeline"], row.state_json, row.context_json
        )
        if expectations_hash(current) != frozen["expectationsHash"]:
            raise AppError(
                "SMART_REMAKE_COMPOSE_POLICY_CHANGED",
                "The selected scene expectations changed. Assemble a new preview.",
                409,
            )


async def save_timeline(
    service: RepairService, project_id: UUID, request: SaveTimelineRequest
) -> dict[str, Any]:
    payload = request.model_dump(mode="json", exclude={"idempotencyKey"})
    row, operation, created = await service.repository.start(
        service.workspace_id,
        project_id,
        request.idempotencyKey,
        _request_hash("timeline", project_id, payload),
    )
    if not created:
        return await service._operation_result(project_id, operation)
    try:
        _assert_in_use(row)
        validate_manifest(row)
        _revision(row.state_json, request.expectedRevision)
        state = copy.deepcopy(row.state_json)
        updates = {str(item.renderUnitId): item for item in request.items}
        if len(updates) != len(request.items):
            raise AppError(
                "SMART_REMAKE_TRIM_INVALID", "A scene can appear only once in an update."
            )
        planned = {item["renderUnitId"] for item in state["draftTimeline"]["items"]}
        if not set(updates) <= planned:
            raise AppError(
                "SMART_REMAKE_SCENE_NOT_FOUND", "This scene is not in the saved timeline."
            )
        for item in state["draftTimeline"]["items"]:
            update = updates.get(item["renderUnitId"])
            if update is None:
                continue
            selected = {
                **item,
                "versionId": str(update.versionId),
                "inFrame": update.inFrame,
                "outFrame": update.outFrame,
                "reviewed": update.reviewed,
            }
            version = _version(_scene(state, item["renderUnitId"]), update.versionId)
            validate_trim(selected, version.get("frameCount", 192))
            # A trim save selects retained media, not an unaccepted repair candidate.
            if _scene(state, item["renderUnitId"])["activeVersionId"] != str(update.versionId):
                raise AppError(
                    "SMART_REMAKE_CANDIDATE_NOT_ACCEPTED",
                    "Accept this candidate before selecting its range.",
                )
            await validate_selection_media(service, state, selected)
            item.update(selected)
        row = await service.repository.project(service.workspace_id, project_id, lock=True)
        _revision(row.state_json, request.expectedRevision)
        _assert_in_use(row)
        if state["draftTimeline"] != row.state_json["draftTimeline"]:
            _invalidate_current(row, state, "timeline_changed")
        state["revision"] += 1
        await service.repository.complete(row, state, operation, {"kind": "timeline"})
        return await service._operation_result(project_id, operation)
    except Exception as exc:
        await service.repository.finish(
            operation,
            "failed",
            {
                "kind": "timeline",
                "errorCode": getattr(exc, "code", "SMART_REMAKE_TIMELINE_SAVE_FAILED"),
            },
        )
        raise


async def _queue(
    session: AsyncSession, service: RepairService, row: Any, operation: Any, job_type: str
) -> Any:
    from .kie_workflow import _dispatch
    from .runtime_limits import kie_job_runtime_input

    job = await JobService(session).request_mvp_job(
        service.workspace_id,
        "smart_remake_project",
        row.id,
        job_type,
        {
            "project_id": str(row.id),
            "operation_id": str(operation.id),
            "request_hash": operation.request_hash,
            **(
                kie_job_runtime_input(row.state_json, row.context_json, operation.result_json)
                if job_type == JobType.SMART_REMAKE_KIE
                else {}
            ),
        },
        f"timeline:{operation.id}",
    )
    # Concurrent idempotent inserts roll back the losing transaction and expire
    # ORM attributes. Reload before the atomic job-id merge accesses this row.
    await service.repository.refresh(operation)
    await service.repository.attach_processing_job(operation, job.id)
    await _dispatch(session, job.id)
    return job


async def enqueue_publish(
    session: AsyncSession,
    settings: Settings,
    workspace_id: UUID,
    project_id: UUID,
    request: PublishTimelineRequest,
    *,
    actor_id: UUID | None = None,
) -> dict[str, Any]:
    from .kie_workflow import _service

    service = _service(session, settings, workspace_id)
    row, operation, created = await service.repository.start(
        workspace_id,
        project_id,
        request.idempotencyKey,
        _request_hash(
            "publish",
            project_id,
            {
                **request.model_dump(exclude={"idempotencyKey"}),
                "actorId": str(actor_id) if actor_id else None,
            },
        ),
    )
    if created:
        try:
            _compose_policy(row)
            if row.context_json.get("p0") and actor_id is None:
                raise AppError(
                    "SMART_REMAKE_ACTOR_REQUIRED", "An authenticated actor is required.", 403
                )
            validate_manifest(row)
            _revision(row.state_json, request.expectedRevision)
            timeline = copy.deepcopy(row.state_json["draftTimeline"])
            _ready(timeline)
            manifest = []
            for item in timeline["items"]:
                await validate_selection_media(service, row.state_json, item)
                version = _version(_scene(row.state_json, item["renderUnitId"]), item["versionId"])
                manifest.append(
                    {
                        "versionId": version["id"],
                        "storageKey": version["storageKey"],
                        "mediaHash": version["mediaHash"],
                    }
                )
            row = await service.repository.project(workspace_id, project_id, lock=True)
            _revision(row.state_json, request.expectedRevision)
            _compose_policy(row)
            expectations = (
                assembly_expectations(timeline, row.state_json, row.context_json)
                if row.context_json.get("p0")
                else None
            )
            await service.repository.finish(
                operation,
                "running",
                {
                    "kind": "compose",
                    "actorId": str(actor_id) if actor_id else None,
                    "constraintsHash": constraints_hash(row.context_json),
                    "policyHash": policy_hash(row.context_json),
                    "expectedRevision": request.expectedRevision,
                    "timeline": timeline,
                    "mediaManifest": manifest,
                    **(
                        {
                            "generationExpectations": expectations,
                            "expectationsHash": expectations_hash(expectations),
                        }
                        if expectations is not None
                        else {}
                    ),
                },
            )
        except Exception as exc:
            await service.repository.finish(
                operation,
                "failed",
                {
                    "kind": "compose",
                    "errorCode": getattr(exc, "code", "SMART_REMAKE_PUBLISH_INVALID"),
                },
            )
            raise
    if operation.status == "running":
        _compose_policy(row, operation.result_json)
        await _queue(session, service, row, operation, JobType.SMART_REMAKE_COMPOSE.value)
    return await service._operation_result(project_id, operation)


async def enqueue_timeline_render(
    session: AsyncSession,
    settings: Settings,
    workspace_id: UUID,
    project_id: UUID,
    expected_revision: int,
    idempotency_key: str,
    *,
    prompt_drafts: list[dict[str, Any]] | None = None,
    project_name: str | None = None,
    audio_required: bool | None = None,
    actor_id: UUID | None = None,
) -> dict[str, Any]:
    from .kie_workflow import _fingerprint, _key, _render_response, _service
    from .service import require_kie_renderer

    require_kie_renderer(settings)
    service = _service(session, settings, workspace_id)
    row, operation, created = await service.repository.start(
        workspace_id,
        project_id,
        _key(idempotency_key),
        _request_hash(
            "render",
            project_id,
            {
                "revision": expected_revision,
                "prompts": prompt_drafts,
                "projectName": project_name,
                "audioRequired": audio_required,
                "actorId": str(actor_id) if actor_id else None,
            },
        ),
    )
    if created:
        try:
            _assert_in_use(row)
            if settings.ai_mode.strip().lower() not in {"fixture", "mock"} or row.context_json.get(
                "p0"
            ):
                assert_project_policy(row, purpose="generation")
                await assert_input_binding(row, service.media)
            validate_manifest(row)
            if row.context_json["renderPlan"].get("groupingPolicy") != "fixed_provider_windows":
                raise AppError(
                    "SMART_REMAKE_PROVIDER_PLAN_UPDATE_REQUIRED",
                    "Update the script to use one provider call for eight seconds "
                    "or two for sixteen.",
                    409,
                )
            _revision(row.state_json, expected_revision)
            require_generation_expectations(row.context_json)
            if row.context_json["renderPlan"].get("imageModel"):
                from .service import require_openai_images

                require_openai_images(settings)
            if any(scene["versions"] for scene in row.state_json["scenes"]):
                raise AppError(
                    "SMART_REMAKE_RENDER_ALREADY_STARTED",
                    "Use scene repair for clips that have already been generated.",
                )
            context, state = copy.deepcopy(row.context_json), copy.deepcopy(row.state_json)
            for name in ("source", "product"):
                expected_hash = context.get(f"{name}MediaHash")
                if (
                    expected_hash
                    and hashlib.sha256(await service.media.read(context[f"{name}Key"])).hexdigest()
                    != expected_hash
                ):
                    raise AppError("SMART_REMAKE_MEDIA_CHANGED", "The saved input media changed.")
            row = await service.repository.project(workspace_id, project_id, lock=True)
            _revision(row.state_json, expected_revision)
            _assert_in_use(row)
            if settings.ai_mode.strip().lower() not in {"fixture", "mock"} or row.context_json.get(
                "p0"
            ):
                assert_project_policy(row, purpose="generation")
            context, state = copy.deepcopy(row.context_json), copy.deepcopy(row.state_json)
            if prompt_drafts is not None:
                from .scene_prompt_drafts import apply_scene_prompt_drafts

                context, state = apply_scene_prompt_drafts(context, state, prompt_drafts)
            if project_name is not None:
                context["projectName"] = project_name[:200]
            if audio_required is not None:
                context["audioRequired"] = audio_required
            expectations = build_generation_expectations(context)
            context.update(
                generationExpectations=expectations,
                expectationsHash=expectations_hash(expectations),
                expectationsStale=False,
            )
            state["status"] = "incomplete"
            _invalidate_current(row, state, "render_started")
            context = {**context, "p0": row.context_json["p0"]} if "p0" in context else context
            if context.get("p0"):
                context["p0"]["constraintsHash"] = constraints_hash(context)
            state["revision"] += 1
            row.context_json, row.state_json, row.revision = context, state, state["revision"]
            frozen_plan = copy.deepcopy(context["renderPlan"])
            await service.repository.finish(
                operation,
                "running",
                {
                    "kind": "render",
                    "actorId": str(actor_id) if actor_id else None,
                    "tasks": {},
                    "renderPlan": frozen_plan,
                    "renderPlanHash": _fingerprint(frozen_plan),
                    "generationExpectations": expectations,
                    "expectationsHash": expectations_hash(expectations),
                },
            )
        except Exception as exc:
            await service.repository.finish(
                operation,
                "failed",
                {
                    "kind": "render",
                    "errorCode": getattr(exc, "code", "SMART_REMAKE_RENDER_INVALID"),
                },
            )
            raise
    if operation.status != "running":
        return await service._operation_result(project_id, operation)
    _assert_in_use(row)
    if settings.ai_mode.strip().lower() not in {"fixture", "mock"} or row.context_json.get("p0"):
        assert_project_policy(row, purpose="generation")
    job = await _queue(session, service, row, operation, JobType.SMART_REMAKE_KIE.value)
    return await _render_response(service, project_id, job.id)


async def retain_timeline_clip(
    service: RepairService, row: Any, index: int, data: bytes, metadata: dict[str, Any]
) -> None:
    before = copy.deepcopy(row.state_json)
    await _release_reads(service)
    key = await service.media.put(
        f"workspaces/{service.workspace_id}/smart-remake/{row.id}", data, "video/mp4"
    )
    version = await run_in_threadpool(
        _new_version,
        data,
        key,
        before["scenes"][index],
        None,
        metadata,
        source="generated",
        audio_required=row.context_json["audioRequired"],
    )
    info = await run_in_threadpool(probe_timeline_media, data)
    version.update(rawDurationFrames=192, frameCount=info["frameCount"])
    state = copy.deepcopy(before)
    scene, item = state["scenes"][index], state["draftTimeline"]["items"][index]
    scene["versions"] = [*scene["versions"], version]
    if version["technicalCheck"]["status"] == "passed":
        scene["activeVersionId"] = version["id"]
        item.update(
            versionId=version["id"],
            inFrame=0,
            outFrame=item["targetDurationFrames"],
            reviewed=False,
        )
    await _finish_retention(service, row.id, before, state, key, metadata)


async def retain_timeline_group_clip(
    service: RepairService,
    row: Any,
    group: dict[str, Any],
    data: bytes,
    metadata: dict[str, Any],
) -> None:
    """Retain one media object and commit every logical scene binding together."""
    current = await service.repository.project(service.workspace_id, row.id)
    validate_manifest(current)
    saved = next(
        (
            value
            for value in current.state_json["renderPlan"].get("groups", [])
            if value["id"] == group["id"]
        ),
        None,
    )
    task_id = metadata.get("providerRequestId")
    if saved != group or not isinstance(task_id, str) or not task_id:
        raise AppError("SMART_REMAKE_TIMELINE_INVALID", "Invalid retained render group binding.")
    if metadata.get("renderGroupId", group["id"]) != group["id"]:
        raise AppError("SMART_REMAKE_TIMELINE_INVALID", "The provider group binding changed.")
    state = copy.deepcopy(current.state_json)
    members = [_scene(state, unit_id) for unit_id in group["renderUnitIds"]]
    existing = [
        next(
            (
                version
                for version in scene["versions"]
                if version.get("providerMetadata", {}).get("providerRequestId") == task_id
                and version.get("providerMetadata", {}).get("renderGroupId") == group["id"]
            ),
            None,
        )
        for scene in members
    ]
    media_hash = hashlib.sha256(data).hexdigest()
    retained = [version for version in existing if version is not None]
    if (
        any(version["mediaHash"] != media_hash for version in retained)
        or len({version["storageKey"] for version in retained}) > 1
    ):
        raise AppError("SMART_REMAKE_MEDIA_CHANGED", "The retained group media changed.")
    if all(existing):
        await _release_reads(service)
        return
    before = copy.deepcopy(current.state_json)
    await _release_reads(service)
    key = (
        retained[0]["storageKey"]
        if retained
        else await service.media.put(
            f"workspaces/{service.workspace_id}/smart-remake/{row.id}", data, "video/mp4"
        )
    )
    info = await run_in_threadpool(probe_timeline_media, data)
    items = {item["renderUnitId"]: item for item in state["draftTimeline"]["items"]}
    for scene, segment, previous in zip(members, group["segments"], existing, strict=True):
        if previous is not None:
            continue
        bounds = {
            "renderGroupId": group["id"],
            "suggestedInFrame": segment["inFrame"],
            "suggestedOutFrame": segment["outFrame"],
        }
        version = await run_in_threadpool(
            _new_version,
            data,
            key,
            scene,
            None,
            {**metadata, **bounds},
            source="generated",
            audio_required=current.context_json["audioRequired"],
        )
        version.update(rawDurationFrames=192, frameCount=info["frameCount"], **bounds)
        item = items[scene["id"]]
        selection = {**item, "inFrame": segment["inFrame"], "outFrame": segment["outFrame"]}
        if segment["outFrame"] > info["frameCount"]:
            check = version["technicalCheck"]
            version["technicalCheck"] = {
                **check,
                "status": "failed",
                "findings": [
                    *check.get("findings", []),
                    "The planned scene range exceeds the clip.",
                ],
            }
        scene["versions"] = [*scene["versions"], version]
        if version["technicalCheck"]["status"] == "passed":
            validate_trim(selection, info["frameCount"])
            scene["activeVersionId"] = version["id"]
            item.update(
                versionId=version["id"],
                inFrame=segment["inFrame"],
                outFrame=segment["outFrame"],
                reviewed=False,
            )
    await _finish_retention(service, row.id, before, state, key, metadata)


async def accept_timeline_version(
    service: RepairService,
    row: Any,
    state: dict[str, Any],
    operation: Any,
    scene: dict[str, Any],
    version: dict[str, Any],
) -> None:
    _assert_in_use(row)
    item = next(
        item for item in state["draftTimeline"]["items"] if item["renderUnitId"] == scene["id"]
    )
    metadata = version.get("providerMetadata") or {}
    start = version.get("suggestedInFrame", metadata.get("suggestedInFrame", 0))
    end = version.get(
        "suggestedOutFrame", metadata.get("suggestedOutFrame", start + item["targetDurationFrames"])
    )
    selection = {**item, "inFrame": start, "outFrame": end}
    validate_trim(selection, version.get("frameCount", 192))
    item.update(versionId=version["id"], inFrame=start, outFrame=end, reviewed=False)
    _invalidate_current(row, state, "scene_version_accepted")
    state["revision"] += 1
    version["usedByRevision"] = state["revision"]
    await service.repository.complete(row, state, operation, {"kind": "accept"})


class TimelineWorkflow:
    def __init__(self, service: RepairService, *, ensure_active: Callable[[], None] = lambda: None):
        self.service, self.ensure_active = service, ensure_active

    async def execute(self, project_id: UUID, operation_id: UUID) -> dict[str, Any]:
        repo, service = self.service.repository, self.service
        async with repo.execution_guard(operation_id) as acquired:
            if not acquired:
                raise RuntimeError("Another worker is assembling this timeline.")
            row = await repo.project(service.workspace_id, project_id)
            operation = await repo.operation(service.workspace_id, project_id, operation_id)
            if operation.status != "running":
                return {"status": operation.status, "project_id": str(project_id)}
            try:
                _compose_policy(row, operation.result_json)
                if operation.result_json.get("kind") != "compose":
                    raise AppError("SMART_REMAKE_JOB_BINDING_INVALID", "Invalid compose operation.")
                validate_manifest(row)
                _revision(row.state_json, operation.result_json["expectedRevision"])
                timeline = copy.deepcopy(operation.result_json["timeline"])
                if timeline != row.state_json["draftTimeline"]:
                    raise AppError(
                        "SMART_REMAKE_REVISION_CONFLICT", "The reviewed timeline changed."
                    )
                _ready(timeline)
                manifest = operation.result_json.get("mediaManifest", [])
                if len(manifest) != len(timeline["items"]):
                    raise AppError(
                        "SMART_REMAKE_MEDIA_CHANGED", "The frozen clip manifest is incomplete."
                    )
                for item, frozen in zip(timeline["items"], manifest, strict=True):
                    version = _version(
                        _scene(row.state_json, item["renderUnitId"]), item["versionId"]
                    )
                    if frozen != {
                        "versionId": version["id"],
                        "storageKey": version["storageKey"],
                        "mediaHash": version["mediaHash"],
                    }:
                        raise AppError("SMART_REMAKE_MEDIA_CHANGED", "The retained clip changed.")
                self.ensure_active()
                await _release_reads(service)
                output, check = await compose_timeline(service, row, timeline)
                self.ensure_active()
                current = await repo.project(service.workspace_id, project_id)
                _compose_policy(current, operation.result_json)
                await _release_reads(service)
                key = await service.media.put(
                    f"workspaces/{service.workspace_id}/smart-remake/{row.id}", output, "video/mp4"
                )
                current = await repo.project(service.workspace_id, project_id, lock=True)
                _remember_media(current, key)
                _compose_policy(current, operation.result_json)
                _revision(current.state_json, operation.result_json["expectedRevision"])
                state = copy.deepcopy(current.state_json)
                state.update(
                    publishedTimeline=timeline,
                    finalStorageKey=key,
                    assemblyCheck=check,
                    status="ready",
                    revision=state["revision"] + 1,
                )
                if current.context_json.get("p0"):
                    context = copy.deepcopy(current.context_json)
                    context["p0"]["phase"], state["phase"] = "rendered", "rendered"
                    context["p0"] = record_assembly(
                        context["p0"],
                        project_id=str(project_id),
                        timeline=timeline,
                        state=state,
                        storage_key=key,
                        media_hash=hashlib.sha256(output).hexdigest(),
                        technical_check=check,
                        constraints_hash=constraints_hash(context),
                        context_hash=content_hash(
                            {
                                "constraintsHash": constraints_hash(context),
                                "manifestHash": content_hash(assembly_manifest(timeline, state)),
                                "policyHash": policy_hash(context),
                            }
                        ),
                        revision=state["revision"],
                        actor_id=operation.result_json["actorId"],
                        operation_id=str(operation.id),
                        context=context,
                    )
                    current.context_json = context
                self.ensure_active()
                await repo.complete(current, state, operation, operation.result_json)
                return {"status": "completed", "project_id": str(project_id)}
            except Exception as exc:
                if getattr(exc, "code", "") not in {
                    "JOB_ATTEMPT_SUPERSEDED",
                    "JOB_ATTEMPT_NOT_CLAIMED",
                }:
                    await repo.finish(
                        operation,
                        "failed",
                        {
                            **operation.result_json,
                            "errorCode": getattr(exc, "code", "SMART_REMAKE_COMPOSE_FAILED"),
                        },
                    )
                raise


async def reconcile_compose_project(service: RepairService, operation: Any) -> None:
    from .kie_workflow import _dispatch

    if operation.result_json.get("processingJobId"):
        try:
            await _dispatch(
                service.repository.session, UUID(operation.result_json["processingJobId"])
            )
        except AppError:
            return
