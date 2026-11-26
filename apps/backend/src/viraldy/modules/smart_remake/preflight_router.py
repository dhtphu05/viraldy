"""Workspace-authorized, side-effect-free action confirmation preflight."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends

from viraldy.api.dependencies.auth import CurrentUserDep, DbSession
from viraldy.api.dependencies.request import get_request_id
from viraldy.api.responses.envelope import Envelope, success

from .intake_router import SettingsDep, authorize
from .preflight_contracts import PreflightRequest
from .preflight_service import preflight_action

router = APIRouter()


@router.post("/preflight", response_model=Envelope)
async def preflight_smart_remake_action(
    workspace_id: UUID,
    payload: PreflightRequest,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await authorize(workspace_id, current_user, db, settings)
    result = await preflight_action(db, settings, workspace_id, payload)
    data = result.model_dump(mode="json", exclude_none=True)
    data["budget"] = result.budget.model_dump(mode="json") if result.budget else None
    return success(data, request_id)
