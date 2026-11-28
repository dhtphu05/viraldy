from __future__ import annotations

import json
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from viraldy.api.dependencies.auth import CurrentUserDep, DbSession, require_workspace_permission
from viraldy.api.dependencies.request import get_request_id
from viraldy.api.responses.envelope import Envelope, success
from viraldy.platform.auth.policy import Permission
from viraldy.platform.config.settings import Settings, get_settings
from viraldy.platform.storage.s3 import S3StorageAdapter
from viraldy.shared.errors.base import AppError

from .engine.schemas import RenderSmartRemakeInput
from .repair_media import RepairMediaStore
from .repair_repository import RepairRepository
from .repair_schemas import (
    AcceptSceneVersion,
    PublishTimelineRequest,
    RepairSceneRequest,
    SaveTimelineRequest,
)
from .repair_service import RepairService
from .service import (
    compile_request,
    feature_enabled,
    health_payload,
    render_request,
    require_kie_renderer,
)

router = APIRouter(prefix="/workspaces/{workspace_id}/smart-remake", tags=["smart-remake"])
SettingsDep = Annotated[Settings, Depends(get_settings)]


@router.get("/health", response_model=Envelope)
async def smart_remake_health(
    workspace_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.WORKSPACE_READ, current_user, db)
    return success(health_payload(settings), request_id)


@router.post("/compile", response_model=Envelope)
async def compile_smart_remake_route(
    workspace_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    mode: str = Form("smart_remake"),
    target_duration: str = Form(..., alias="targetDuration"),
    aspect_ratio: str = Form("9:16", alias="aspectRatio"),
    language: str | None = Form(None),
    prompt: str | None = Form(None),
    description: str | None = Form(None),
    product_url: str | None = Form(None, alias="productUrl"),
    product_title: str | None = Form(None, alias="productTitle"),
    product_description: str | None = Form(None, alias="productDescription"),
    reference_video: UploadFile | None = File(None, alias="referenceVideo"),  # noqa: B008
    product_image: UploadFile | None = File(None, alias="productImage"),  # noqa: B008
    request_id: str = Depends(get_request_id),
    timeline_mode: Annotated[str | None, Form(alias="timelineMode")] = None,
    analysis_scope: Annotated[
        Literal["excerpt", "full_source"], Form(alias="analysisScope")
    ] = "excerpt",
    reference_start_frame: Annotated[int, Form(alias="referenceStartFrame", ge=0)] = 0,
    source_cut_frames: Annotated[str | None, Form(alias="sourceCutFrames")] = None,
    project_id: Annotated[UUID | None, Form(alias="projectId")] = None,
    render_group_breaks: Annotated[str | None, Form(alias="renderGroupBreaks")] = None,
    expected_revision: Annotated[int | None, Form(alias="expectedRevision", ge=1)] = None,
    idempotency_key: Annotated[str | None, Form(alias="idempotencyKey", max_length=200)] = None,
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.ANALYSIS_RUN, current_user, db)
    if settings.ai_mode.strip().lower() not in {"fixture", "mock"} and timeline_mode != "reference":
        raise AppError(
            "SMART_REMAKE_INTAKE_REQUIRED", "Use an owned reference intake before analysis.", 409
        )
    values: dict[str, Any] = dict(
        settings=settings,
        mode=mode,
        target_duration=target_duration,
        aspect_ratio=aspect_ratio,
        language=language,
        prompt=prompt,
        description=description,
        product_url=product_url,
        product_title=product_title,
        product_description=product_description,
        reference_video=reference_video,
        product_image=product_image,
    )
    if timeline_mode is not None:
        if timeline_mode != "reference":
            raise AppError("SMART_REMAKE_TIMELINE_INVALID", "Timeline mode is not supported.")
        from .timeline_compile import compile_timeline_request

        if analysis_scope not in {"excerpt", "full_source"}:
            raise AppError("SMART_REMAKE_TIMELINE_INVALID", "Analysis scope is not supported.")
        if analysis_scope == "full_source":
            values["analysis_scope"] = analysis_scope

        if project_id is not None:
            values["project_id"] = project_id
        if expected_revision is not None:
            values["expected_revision"] = expected_revision
        if idempotency_key is not None:
            values["idempotency_key"] = idempotency_key
        if getattr(current_user, "id", None) is not None:
            values["actor_id"] = current_user.id
        if render_group_breaks is not None:
            values["render_group_breaks"] = _parse_render_group_breaks(render_group_breaks)
        result = await compile_timeline_request(
            session=db,
            workspace_id=workspace_id,
            reference_start_frame=reference_start_frame,
            source_cut_frames=_parse_source_cut_frames(source_cut_frames),
            **values,
        )
    else:
        result = await compile_request(**values)
    return success(result, request_id)


def _parse_source_cut_frames(value: str | None) -> list[int] | None:
    if value is None:
        return None
    try:
        cuts = json.loads(value)
    except json.JSONDecodeError as exc:
        raise AppError(
            "SMART_REMAKE_TIMELINE_INVALID", "Source cuts must be a JSON array."
        ) from exc
    if not isinstance(cuts, list) or any(type(frame) is not int for frame in cuts):
        raise AppError("SMART_REMAKE_TIMELINE_INVALID", "Source cuts must contain integer frames.")
    return cuts


def _parse_render_group_breaks(value: str) -> list[int]:
    breaks = _parse_source_cut_frames(value)
    if (
        breaks is None
        or any(boundary < 1 for boundary in breaks)
        or breaks != sorted(set(breaks))
    ):
        raise AppError(
            "SMART_REMAKE_TIMELINE_INVALID",
            "Group boundaries must be increasing positive scene positions.",
        )
    return breaks


@router.post("/render", response_model=Envelope)
async def render_smart_remake_route(
    workspace_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    compile_result: str = Form(..., alias="compileResult"),
    product_image: UploadFile | None = File(None, alias="productImage"),  # noqa: B008
    product_url: str | None = Form(None, alias="productUrl"),
    provider: str = Form("fixture"),
    project_name: str = Form("Smart Remake", alias="projectName"),
    audio_required: bool = Form(False, alias="audioRequired"),
    idempotency_key: str | None = Form(None, alias="idempotencyKey", min_length=1, max_length=200),
    request_id: str = Depends(get_request_id),
    project_id: Annotated[UUID | None, Form(alias="projectId")] = None,
    expected_revision: Annotated[int | None, Form(alias="expectedRevision", ge=1)] = None,
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.ANALYSIS_RUN, current_user, db)
    try:
        parsed = json.loads(compile_result)
    except json.JSONDecodeError as exc:
        raise AppError(
            "INVALID_SMART_REMAKE_COMPILE_RESULT", "compileResult must be valid JSON."
        ) from exc
    if not isinstance(parsed, dict):
        raise AppError("INVALID_SMART_REMAKE_COMPILE_RESULT", "compileResult must be an object.")
    render_key = (idempotency_key or "").strip()
    if provider == "kie" and not render_key:
        raise AppError("SMART_REMAKE_IDEMPOTENCY_KEY_REQUIRED", "A render request key is required.")
    if parsed.get("schemaVersion") == 2:
        result = await _render_timeline(
            db, settings, workspace_id, project_id, expected_revision, render_key,
            parsed, provider, project_name, audio_required,
            actor_id=getattr(current_user, "id", None),
        )
        return success(result, request_id)
    if settings.ai_mode.strip().lower() not in {"fixture", "mock"}:
        raise AppError(
            "SMART_REMAKE_INTAKE_REQUIRED", "Live rendering requires an owned P0 timeline.", 409
        )
    if project_id is not None or expected_revision is not None:
        raise AppError("SMART_REMAKE_TIMELINE_INVALID", "A saved timeline plan is required.")
    repair = (
        _repair_service(db, settings, workspace_id) if provider not in {"fixture", "kie"} else None
    )

    async def submit_kie(input_data: RenderSmartRemakeInput) -> dict[str, Any]:
        from .kie_workflow import enqueue_kie_render

        return await enqueue_kie_render(db, settings, workspace_id, input_data, render_key)

    try:
        result = await render_request(
            settings=settings,
            compile_result=parsed,
            product_image=product_image,
            provider=provider,
            project_name=project_name,
            audio_required=audio_required,
            product_url=product_url,
            prepare_render=repair.begin_render if repair else None,
            submit_render=submit_kie if provider == "kie" else None,
        )
    except AppError as exc:
        recovery_id = await repair.recoverable_project_id() if repair else None
        if recovery_id:
            exc.details = {**exc.details, "repairProjectId": recovery_id}
        raise
    except Exception as exc:
        recovery_id = await repair.recoverable_project_id() if repair else None
        details: dict[str, object] = {"repairProjectId": recovery_id} if recovery_id else {}
        raise AppError(
            "SMART_REMAKE_RENDER_INTERRUPTED",
            "The render could not finish. Retained scenes can be reviewed before retrying.",
            503,
            details,
        ) from exc
    if repair and repair.render_project_id:
        result["repairProject"] = await repair.get(repair.render_project_id)
    return success(result, request_id)


async def _render_timeline(
    db: AsyncSession,
    settings: Settings,
    workspace_id: UUID,
    project_id: UUID | None,
    expected_revision: int | None,
    render_key: str,
    compiled: dict[str, Any],
    provider: str,
    project_name: str,
    audio_required: bool,
    *,
    actor_id: UUID | None = None,
) -> dict[str, Any]:
    if (
        project_id is None
        or type(expected_revision) is not int
        or expected_revision < 1
        or str(project_id) != compiled.get("projectId")
    ):
        raise AppError(
            "SMART_REMAKE_TIMELINE_INVALID", "A saved project and revision are required."
        )
    if not feature_enabled(settings):
        raise AppError("SMART_REMAKE_DISABLED", "Smart Remake is disabled.", 503)
    if provider != "kie":
        raise AppError(
            "SMART_REMAKE_TIMELINE_PROVIDER_REQUIRED", "Reference timelines require KIE.", 409
        )
    require_kie_renderer(settings)
    from .timeline_service import enqueue_timeline_render

    return await enqueue_timeline_render(
        db, settings, workspace_id, project_id, expected_revision, render_key,
        prompt_drafts=_timeline_prompt_drafts(compiled),
        project_name=project_name,
        audio_required=audio_required,
        actor_id=actor_id,
    )


def _timeline_prompt_drafts(compiled: dict[str, Any]) -> list[dict[str, str]]:
    scene_map = compiled.get("sceneMap")
    scenes = scene_map.get("scenes") if isinstance(scene_map, dict) else None
    if not isinstance(scenes, list) or not scenes:
        raise AppError("SMART_REMAKE_TIMELINE_INVALID", "The saved timeline needs scene prompts.")
    fields = ("prompt", "imagePrompt", "videoPrompt")
    drafts = []
    for scene in scenes:
        if not isinstance(scene, dict) or any(
            not isinstance(scene.get(field), str) or not 1 <= len(scene[field].strip()) <= 12000
            for field in fields
        ):
            raise AppError("SMART_REMAKE_TIMELINE_INVALID", "Every scene needs valid prompts.")
        drafts.append({field: scene[field] for field in fields})
    return drafts


def _repair_service(db: AsyncSession, settings: Settings, workspace_id: UUID) -> RepairService:
    try:
        return RepairService(
            RepairRepository(db),
            RepairMediaStore(S3StorageAdapter(settings)),
            workspace_id,
            settings=settings,
        )
    except Exception as exc:
        raise AppError(
            "SMART_REMAKE_RETENTION_UNAVAILABLE", "Scene repair storage is unavailable.", 503
        ) from exc


@router.patch("/projects/{project_id}/timeline", response_model=Envelope)
async def save_smart_remake_timeline(
    workspace_id: UUID,
    project_id: UUID,
    payload: SaveTimelineRequest,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.ANALYSIS_RUN, current_user, db)
    if not feature_enabled(settings):
        raise AppError("SMART_REMAKE_DISABLED", "Smart Remake is disabled.", 503)
    from .timeline_service import save_timeline

    result = await save_timeline(_repair_service(db, settings, workspace_id), project_id, payload)
    return success(result, request_id)


@router.post("/projects/{project_id}/publish", response_model=Envelope)
async def publish_smart_remake_timeline(
    workspace_id: UUID,
    project_id: UUID,
    payload: PublishTimelineRequest,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.ANALYSIS_RUN, current_user, db)
    if not feature_enabled(settings):
        raise AppError("SMART_REMAKE_DISABLED", "Smart Remake is disabled.", 503)
    from .timeline_service import enqueue_publish

    result = await enqueue_publish(
        db, settings, workspace_id, project_id, payload, actor_id=getattr(current_user, "id", None)
    )
    return success(result, request_id)


@router.get("/projects/{project_id}", response_model=Envelope)
async def get_smart_remake_project(
    workspace_id: UUID,
    project_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.WORKSPACE_READ, current_user, db)
    return success(await _repair_service(db, settings, workspace_id).get(project_id), request_id)


@router.post("/projects/{project_id}/scenes/{scene_id}/repairs", response_model=Envelope)
async def repair_smart_remake_scene(
    workspace_id: UUID,
    project_id: UUID,
    scene_id: UUID,
    payload: RepairSceneRequest,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.ANALYSIS_RUN, current_user, db)
    if not feature_enabled(settings):
        raise AppError("SMART_REMAKE_DISABLED", "Smart Remake is disabled.", 503)
    repair = _repair_service(db, settings, workspace_id)
    row = await repair.repository.project(workspace_id, project_id)
    if row.state_json["provider"] == "kie":
        require_kie_renderer(settings)
        from .kie_workflow import enqueue_kie_repair

        result = await enqueue_kie_repair(
            db, settings, workspace_id, project_id, scene_id, payload,
            actor_id=getattr(current_user, "id", None),
        )
    else:
        result = await repair.repair(project_id, scene_id, payload)
    return success(result, request_id)


@router.post("/projects/{project_id}/accept", response_model=Envelope)
async def accept_smart_remake_scene(
    workspace_id: UUID,
    project_id: UUID,
    payload: AcceptSceneVersion,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.ANALYSIS_RUN, current_user, db)
    result = await _repair_service(db, settings, workspace_id).accept(project_id, payload)
    return success(result, request_id)


@router.post(
    "/projects/{project_id}/scenes/{scene_id}/versions/{version_id}/checks", response_model=Envelope
)
async def check_smart_remake_scene(
    workspace_id: UUID,
    project_id: UUID,
    scene_id: UUID,
    version_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.ANALYSIS_RUN, current_user, db)
    result = await _repair_service(db, settings, workspace_id).check(
        project_id, scene_id, version_id
    )
    return success(result, request_id)


# Keep lifecycle declarations under the same workspace authentication boundary.
from .asset_intake_router import router as asset_intake_router  # noqa: E402
from .asset_upload_router import router as asset_upload_router  # noqa: E402
from .intake_router import router as intake_router  # noqa: E402
from .lifecycle_router import router as lifecycle_router  # noqa: E402
from .preflight_router import router as preflight_router  # noqa: E402
from .project_library import router as project_library_router  # noqa: E402
from .repair_receipts import router as repair_receipts_router  # noqa: E402

router.include_router(asset_intake_router)
router.include_router(asset_upload_router)
router.include_router(intake_router)
router.include_router(lifecycle_router)
router.include_router(preflight_router)
router.include_router(project_library_router)
router.include_router(repair_receipts_router)
