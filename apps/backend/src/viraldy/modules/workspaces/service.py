from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from viraldy.modules.identity.public import IdentityQueries, UserSummary
from viraldy.modules.product_events.public import ProductEventPublisher
from viraldy.modules.workspaces.models import WorkspaceMemberModel
from viraldy.modules.workspaces.repository import WorkspaceRepository
from viraldy.modules.workspaces.schemas import (
    AddWorkspaceMemberRequest,
    CreateWorkspaceRequest,
    UpdateWorkspaceMemberRequest,
    UpdateWorkspaceRequest,
    WorkspaceMemberResponse,
    WorkspaceResponse,
)
from viraldy.platform.auth.policy import WorkspaceRole, normalize_workspace_role
from viraldy.shared.errors.base import AppError, ForbiddenError, NotFoundError


class WorkspaceService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repository = WorkspaceRepository(session)
        self._identity = IdentityQueries(session)

    async def create_workspace(
        self, data: CreateWorkspaceRequest, user_id: UUID
    ) -> WorkspaceResponse:
        workspace = await self._repository.create(data.name, data.slug, user_id)
        await ProductEventPublisher(self._session).record(
            event_type="workspace_created",
            workspace_id=workspace.id,
            actor_user_id=user_id,
            subject_type="workspace",
            subject_id=workspace.id,
            payload_json={"name": data.name, "slug": data.slug},
        )
        await self._session.commit()
        return WorkspaceResponse.model_validate(workspace)

    async def list_for_user(self, user_id: UUID) -> list[WorkspaceResponse]:
        workspaces = await self._repository.list_for_user(user_id)
        return [WorkspaceResponse.model_validate(workspace) for workspace in workspaces]

    async def get_for_user(self, workspace_id: UUID, user_id: UUID) -> WorkspaceResponse:
        workspace = await self._repository.get_for_user(workspace_id, user_id)
        if workspace is None:
            raise NotFoundError("WORKSPACE_NOT_FOUND", "Workspace was not found.")
        return WorkspaceResponse.model_validate(workspace)

    async def get(self, workspace_id: UUID) -> WorkspaceResponse:
        workspace = await self._repository.get(workspace_id)
        if workspace is None:
            raise NotFoundError("WORKSPACE_NOT_FOUND", "Workspace was not found.")
        return WorkspaceResponse.model_validate(workspace)

    async def update_workspace(
        self,
        workspace_id: UUID,
        data: UpdateWorkspaceRequest,
    ) -> WorkspaceResponse:
        workspace = await self._repository.get(workspace_id)
        if workspace is None:
            raise NotFoundError("WORKSPACE_NOT_FOUND", "Workspace was not found.")
        updated = await self._repository.update_workspace(
            workspace,
            name=data.name,
            slug=data.slug,
            status=data.status,
        )
        await self._session.commit()
        await self._session.refresh(updated)
        return WorkspaceResponse.model_validate(updated)

    async def delete_workspace(self, workspace_id: UUID) -> None:
        workspace = await self._repository.get(workspace_id)
        if workspace is None:
            raise NotFoundError("WORKSPACE_NOT_FOUND", "Workspace was not found.")
        await self._repository.soft_delete_workspace(workspace)
        await self._session.commit()

    async def list_members(self, workspace_id: UUID) -> list[WorkspaceMemberResponse]:
        members = await self._repository.list_members(workspace_id)
        users = await self._identity.list_by_ids([member.user_id for member in members])
        users_by_id = {user.id: user for user in users}
        return [
            _member_response(member, users_by_id.get(member.user_id))
            for member in members
            if users_by_id.get(member.user_id) is not None
        ]

    async def add_member(
        self,
        workspace_id: UUID,
        data: AddWorkspaceMemberRequest,
    ) -> WorkspaceMemberResponse:
        user = await self._identity.get_by_email(str(data.email))
        if user is None:
            raise NotFoundError("USER_NOT_FOUND", "User with that email was not found.")
        if user.status != "active":
            raise ForbiddenError("USER_NOT_ACTIVE", "User is not active.")
        member = await self._repository.add_member(workspace_id, user.id, data.role.value)
        await self._session.commit()
        await self._session.refresh(member)
        return _member_response(member, user)

    async def update_member(
        self,
        workspace_id: UUID,
        member_id: UUID,
        actor_user_id: UUID,
        data: UpdateWorkspaceMemberRequest,
    ) -> WorkspaceMemberResponse:
        member = await self._repository.get_member(workspace_id, member_id)
        if member is None:
            raise NotFoundError("WORKSPACE_MEMBER_NOT_FOUND", "Workspace member was not found.")
        await self._guard_last_owner_self_change(
            workspace_id,
            member,
            actor_user_id,
            next_role=data.role,
        )
        updated = await self._repository.update_member_role(member, data.role.value)
        await self._session.commit()
        await self._session.refresh(updated)
        users = await self._identity.list_by_ids([updated.user_id])
        return _member_response(updated, users[0] if users else None)

    async def remove_member(
        self,
        workspace_id: UUID,
        member_id: UUID,
        actor_user_id: UUID,
    ) -> None:
        member = await self._repository.get_member(workspace_id, member_id)
        if member is None:
            raise NotFoundError("WORKSPACE_MEMBER_NOT_FOUND", "Workspace member was not found.")
        await self._guard_last_owner_self_change(
            workspace_id,
            member,
            actor_user_id,
            next_role=None,
        )
        await self._repository.remove_member(workspace_id, member_id)
        await self._session.commit()

    async def _guard_last_owner_self_change(
        self,
        workspace_id: UUID,
        member: WorkspaceMemberModel,
        actor_user_id: UUID,
        next_role: WorkspaceRole | None,
    ) -> None:
        if member.user_id != actor_user_id or member.role != WorkspaceRole.OWNER.value:
            return
        if next_role is WorkspaceRole.OWNER:
            return
        owner_count = await self._repository.count_owners(workspace_id)
        if owner_count <= 1:
            raise AppError(
                "WORKSPACE_LAST_OWNER_REQUIRED",
                "The only workspace owner cannot remove or demote themself.",
                status_code=409,
            )


def _member_response(
    member: WorkspaceMemberModel,
    user: UserSummary | None,
) -> WorkspaceMemberResponse:
    if user is None:
        raise NotFoundError(
            "WORKSPACE_MEMBER_USER_NOT_FOUND",
            "Workspace member user was not found.",
        )
    return WorkspaceMemberResponse(
        workspace_id=member.workspace_id,
        user_id=member.user_id,
        email=user.email,
        display_name=user.display_name,
        role=normalize_workspace_role(member.role),
        created_at=member.created_at,
    )
