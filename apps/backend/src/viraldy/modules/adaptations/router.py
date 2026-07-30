from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from viraldy.api.dependencies.auth import CurrentUserDep, DbSession, require_workspace_permission
from viraldy.api.dependencies.request import get_request_id
from viraldy.api.responses.envelope import Envelope, success
from viraldy.modules.adaptations.schemas import CreateAdaptationRequest
from viraldy.modules.adaptations.service import AdaptationService
from viraldy.platform.auth.policy import Permission
from viraldy.platform.config.settings import Settings, get_settings

router = APIRouter(prefix="/workspaces/{workspace_id}/adaptations", tags=["adaptations"])
SettingsDep = Annotated[Settings, Depends(get_settings)]


@router.post("", status_code=status.HTTP_201_CREATED, response_model=Envelope)
async def create_adaptation(
    workspace_id: UUID,
    payload: CreateAdaptationRequest,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(
        workspace_id, Permission.VIRAL_KIT_WRITE, current_user, db
    )
    run = await AdaptationService(db, settings).create(workspace_id, current_user.id, payload)
    return success(run.model_dump(mode="json"), request_id)


@router.get("/{adaptation_id}", response_model=Envelope)
async def get_adaptation(
    workspace_id: UUID,
    adaptation_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.WORKSPACE_READ, current_user, db)
    run = await AdaptationService(db, settings).get(workspace_id, adaptation_id)
    return success(run.model_dump(mode="json"), request_id)
