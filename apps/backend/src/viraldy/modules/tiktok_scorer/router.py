from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, status

from viraldy.api.dependencies.auth import CurrentUserDep, DbSession, require_workspace_permission
from viraldy.api.dependencies.request import get_request_id
from viraldy.api.responses.envelope import Envelope, success
from viraldy.modules.tiktok_scorer.schemas import CreateTikTokScoreRequest
from viraldy.modules.tiktok_scorer.service import TikTokScoreService
from viraldy.platform.auth.policy import Permission
from viraldy.platform.config.settings import Settings, get_settings

router = APIRouter(prefix="/workspaces/{workspace_id}/tiktok-scores", tags=["tiktok-scores"])
SettingsDep = Annotated[Settings, Depends(get_settings)]


@router.post("", status_code=status.HTTP_202_ACCEPTED, response_model=Envelope)
async def create_score(
    workspace_id: UUID,
    payload: CreateTikTokScoreRequest,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(
        workspace_id, Permission.ANALYSIS_RUN, current_user, db
    )
    result = await TikTokScoreService(db, settings).create(workspace_id, payload, idempotency_key)
    return success(result.model_dump(mode="json"), request_id)


@router.get("/{score_run_id}", response_model=Envelope)
async def get_score(
    workspace_id: UUID,
    score_run_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.WORKSPACE_READ, current_user, db)
    run = await TikTokScoreService(db, settings).get(workspace_id, score_run_id)
    return success(run.model_dump(mode="json"), request_id)
