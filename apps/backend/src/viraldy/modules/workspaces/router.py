from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from viraldy.api.dependencies.auth import CurrentUserDep, DbSession, require_workspace_permission
from viraldy.api.dependencies.request import get_request_id
from viraldy.api.responses.envelope import Envelope, success
from viraldy.modules.workspaces.schemas import (
    AddWorkspaceMemberRequest,
    CreateWorkspaceRequest,
    UpdateWorkspaceMemberRequest,
    UpdateWorkspaceRequest,
)
from viraldy.modules.workspaces.service import WorkspaceService
from viraldy.platform.auth.policy import Permission

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
    await require_workspace_permission(workspace_id, Permission.WORKSPACE_READ, current_user, db)
    workspace = await WorkspaceService(db).get(workspace_id)
    return success(workspace.model_dump(mode="json"), request_id)


@router.patch("/{workspace_id}", response_model=Envelope)
async def update_workspace(
    workspace_id: UUID,
    payload: UpdateWorkspaceRequest,
    current_user: CurrentUserDep,
    db: DbSession,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.WORKSPACE_MANAGE, current_user, db)
    workspace = await WorkspaceService(db).update_workspace(workspace_id, payload)
    return success(workspace.model_dump(mode="json"), request_id)


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workspace(
    workspace_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
) -> Response:
    await require_workspace_permission(workspace_id, Permission.WORKSPACE_MANAGE, current_user, db)
    await WorkspaceService(db).delete_workspace(workspace_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{workspace_id}/members", response_model=Envelope)
async def list_workspace_members(
    workspace_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.MEMBERS_READ, current_user, db)
    members = await WorkspaceService(db).list_members(workspace_id)
    return success([member.model_dump(mode="json") for member in members], request_id)


@router.post(
    "/{workspace_id}/members",
    status_code=status.HTTP_201_CREATED,
    response_model=Envelope,
)
async def add_workspace_member(
    workspace_id: UUID,
    payload: AddWorkspaceMemberRequest,
    current_user: CurrentUserDep,
    db: DbSession,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.MEMBERS_MANAGE, current_user, db)
    member = await WorkspaceService(db).add_member(workspace_id, payload)
    return success(member.model_dump(mode="json"), request_id)


@router.patch("/{workspace_id}/members/{member_id}", response_model=Envelope)
async def update_workspace_member(
    workspace_id: UUID,
    member_id: UUID,
    payload: UpdateWorkspaceMemberRequest,
    current_user: CurrentUserDep,
    db: DbSession,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.MEMBERS_MANAGE, current_user, db)
    member = await WorkspaceService(db).update_member(
        workspace_id,
        member_id,
        current_user.id,
        payload,
    )
    return success(member.model_dump(mode="json"), request_id)


@router.delete("/{workspace_id}/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_workspace_member(
    workspace_id: UUID,
    member_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
) -> Response:
    await require_workspace_permission(workspace_id, Permission.MEMBERS_MANAGE, current_user, db)
    await WorkspaceService(db).remove_member(workspace_id, member_id, current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
