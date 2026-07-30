from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from viraldy.api.dependencies.auth import CurrentUserDep, DbSession, require_workspace_permission
from viraldy.api.dependencies.request import get_request_id
from viraldy.api.responses.envelope import Envelope, success
from viraldy.modules.ai_gateway.schemas import AiModelRunStatus
from viraldy.modules.ai_gateway.service import AiModelRunService
from viraldy.platform.auth.policy import Permission

router = APIRouter(prefix="/workspaces/{workspace_id}/model-runs", tags=["model-runs"])


@router.get("", response_model=Envelope)
async def list_model_runs(
    workspace_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    subject_type: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    subject_id: UUID | None = None,
    operation: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    status: AiModelRunStatus | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.DATA_EXPORT, current_user, db)
    runs = await AiModelRunService(db).list_runs(
        workspace_id=workspace_id,
        subject_type=subject_type,
        subject_id=subject_id,
        operation=operation,
        status=status,
        limit=limit,
    )
    return success([run.model_dump(mode="json") for run in runs], request_id)


@router.get("/{model_run_id}", response_model=Envelope)
async def get_model_run(
    workspace_id: UUID,
    model_run_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.DATA_EXPORT, current_user, db)
    run = await AiModelRunService(db).get_run(workspace_id, model_run_id)
    return success(run.model_dump(mode="json"), request_id)
