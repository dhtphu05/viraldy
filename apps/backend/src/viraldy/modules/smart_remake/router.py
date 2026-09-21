from __future__ import annotations

import json
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile

from viraldy.api.dependencies.auth import CurrentUserDep, DbSession, require_workspace_permission
from viraldy.api.dependencies.request import get_request_id
from viraldy.api.responses.envelope import Envelope, success
from viraldy.platform.auth.policy import Permission
from viraldy.platform.config.settings import Settings, get_settings
from viraldy.shared.errors.base import AppError

from .service import compile_request, health_payload, render_request

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
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.ANALYSIS_RUN, current_user, db)
    result = await compile_request(
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
    return success(result, request_id)


@router.post("/render", response_model=Envelope)
async def render_smart_remake_route(
    workspace_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    compile_result: str = Form(..., alias="compileResult"),
    product_image: UploadFile = File(..., alias="productImage"),  # noqa: B008
    provider: str = Form("fixture"),
    project_name: str = Form("Smart Remake", alias="projectName"),
    audio_required: bool = Form(False, alias="audioRequired"),
    request_id: str = Depends(get_request_id),
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
    result = await render_request(
        settings=settings,
        compile_result=parsed,
        product_image=product_image,
        provider=provider,
        project_name=project_name,
        audio_required=audio_required,
    )
    return success(result, request_id)
