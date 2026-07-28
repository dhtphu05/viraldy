from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status

from viraldy.api.dependencies.auth import CurrentUserDep, DbSession
from viraldy.api.dependencies.request import get_request_id
from viraldy.api.responses.envelope import Envelope, success
from viraldy.modules.workspaces.schemas import CreateWorkspaceRequest
from viraldy.modules.workspaces.service import WorkspaceService

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.get("", response_model=Envelope)
async def list_workspaces(
    current_user: CurrentUserDep,
    db: DbSession,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    workspaces = await WorkspaceService(db).list_for_user(current_user.id)
    return success([workspace.model_dump(mode="json") for workspace in workspaces], request_id)


@router.post("", status_code=status.HTTP_201_CREATED, response_model=Envelope)
async def create_workspace(
    payload: CreateWorkspaceRequest,
    current_user: CurrentUserDep,
    db: DbSession,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    workspace = await WorkspaceService(db).create_workspace(payload, current_user.id)
    return success(workspace.model_dump(mode="json"), request_id)


@router.get("/{workspace_id}", response_model=Envelope)
async def get_workspace(
    workspace_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    workspace = await WorkspaceService(db).get_for_user(workspace_id, current_user.id)
    return success(workspace.model_dump(mode="json"), request_id)
