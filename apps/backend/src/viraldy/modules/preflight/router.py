from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, status

from viraldy.api.dependencies.auth import CurrentUserDep, DbSession, require_workspace_permission
from viraldy.api.dependencies.request import get_request_id
from viraldy.api.responses.envelope import Envelope, success
from viraldy.modules.preflight.schemas import CreatePreflightRunRequest
from viraldy.modules.preflight.service import PreflightService
from viraldy.modules.presentations.public import (
    GeneratePresentationRequestV1,
    PreflightPresentationService,
)
from viraldy.platform.auth.policy import Permission
from viraldy.platform.config.settings import Settings, get_settings

router = APIRouter(prefix="/workspaces/{workspace_id}/preflight-runs", tags=["preflight"])
SettingsDep = Annotated[Settings, Depends(get_settings)]


@router.post("", status_code=status.HTTP_202_ACCEPTED, response_model=Envelope)
async def create_preflight(
    workspace_id: UUID,
    payload: CreatePreflightRunRequest,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.PREFLIGHT_RUN, current_user, db)
    result = await PreflightService(db, settings).create(workspace_id, payload, idempotency_key)
    return success(result.model_dump(mode="json"), request_id)


@router.get("/{preflight_run_id}", response_model=Envelope)
async def get_preflight(
    workspace_id: UUID,
    preflight_run_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.WORKSPACE_READ, current_user, db)
    run = await PreflightService(db, settings).get(workspace_id, preflight_run_id, current_user.id)
    return success(run.model_dump(mode="json"), request_id)


@router.post("/{preflight_run_id}/presentation", response_model=Envelope)
async def generate_preflight_presentation(
    workspace_id: UUID,
    preflight_run_id: UUID,
    payload: GeneratePresentationRequestV1,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(
        workspace_id,
        Permission.PREFLIGHT_RUN,
        current_user,
        db,
    )
    result = await PreflightPresentationService(db, settings).generate(
        workspace_id=workspace_id,
        preflight_run_id=preflight_run_id,
        actor_user_id=current_user.id,
        request=payload,
    )
    return success(result.model_dump(mode="json"), request_id)
