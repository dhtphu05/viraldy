from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from viraldy.modules.workspaces.models import WorkspaceMemberModel, WorkspaceModel
from viraldy.shared.errors.base import ConflictError


class WorkspaceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, name: str, slug: str, created_by_user_id: UUID) -> WorkspaceModel:
        workspace = WorkspaceModel(
            name=name,
            slug=slug,
            status="active",
            created_by_user_id=created_by_user_id,
        )
        self._session.add(workspace)
        await self._session.flush()
        self._session.add(
            WorkspaceMemberModel(
                workspace_id=workspace.id,
                user_id=created_by_user_id,
                role="owner",
            )
        )
        await self._session.flush()
        return workspace

    async def get(self, workspace_id: UUID) -> WorkspaceModel | None:
        result = await self._session.execute(
            select(WorkspaceModel).where(
                WorkspaceModel.id == workspace_id,
                WorkspaceModel.status != "deleted",
            )
        )
        return result.scalar_one_or_none()

    async def list_for_user(self, user_id: UUID) -> list[WorkspaceModel]:
        result = await self._session.execute(
            select(WorkspaceModel)
            .join(WorkspaceMemberModel, WorkspaceMemberModel.workspace_id == WorkspaceModel.id)
            .where(WorkspaceMemberModel.user_id == user_id, WorkspaceModel.status != "deleted")
            .order_by(WorkspaceModel.created_at.desc())
        )
        return list(result.scalars())

    async def get_for_user(self, workspace_id: UUID, user_id: UUID) -> WorkspaceModel | None:
        result = await self._session.execute(
            select(WorkspaceModel)
            .join(WorkspaceMemberModel, WorkspaceMemberModel.workspace_id == WorkspaceModel.id)
            .where(
                WorkspaceModel.id == workspace_id,
                WorkspaceModel.status != "deleted",
                WorkspaceMemberModel.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_member_role(self, workspace_id: UUID, user_id: UUID) -> str | None:
        result = await self._session.execute(
            select(WorkspaceMemberModel.role)
            .join(WorkspaceModel, WorkspaceModel.id == WorkspaceMemberModel.workspace_id)
            .where(
                WorkspaceMemberModel.workspace_id == workspace_id,
                WorkspaceMemberModel.user_id == user_id,
                WorkspaceModel.status != "deleted",
            )
        )
        return result.scalar_one_or_none()

    async def update_workspace(
        self,
        workspace: WorkspaceModel,
        *,
        name: str | None = None,
        slug: str | None = None,
        status: str | None = None,
    ) -> WorkspaceModel:
        if name is not None:
            workspace.name = name
        if slug is not None:
            workspace.slug = slug
        if status is not None:
            workspace.status = status
        try:
            await self._session.flush()
        except IntegrityError as exc:
            raise ConflictError("WORKSPACE_CONFLICT", "Workspace slug is already in use.") from exc
        return workspace

    async def soft_delete_workspace(self, workspace: WorkspaceModel) -> None:
        workspace.status = "deleted"
        await self._session.flush()

    async def list_members(self, workspace_id: UUID) -> list[WorkspaceMemberModel]:
        result = await self._session.execute(
            select(WorkspaceMemberModel)
            .where(WorkspaceMemberModel.workspace_id == workspace_id)
            .order_by(WorkspaceMemberModel.created_at.asc(), WorkspaceMemberModel.user_id.asc())
        )
        return list(result.scalars())

    async def get_member(
        self, workspace_id: UUID, user_id: UUID
    ) -> WorkspaceMemberModel | None:
        result = await self._session.execute(
            select(WorkspaceMemberModel).where(
                WorkspaceMemberModel.workspace_id == workspace_id,
                WorkspaceMemberModel.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def add_member(
        self,
        workspace_id: UUID,
        user_id: UUID,
        role: str,
    ) -> WorkspaceMemberModel:
        member = WorkspaceMemberModel(workspace_id=workspace_id, user_id=user_id, role=role)
        self._session.add(member)
        try:
            await self._session.flush()
        except IntegrityError as exc:
            raise ConflictError("WORKSPACE_MEMBER_EXISTS", "User is already a member.") from exc
        return member

    async def update_member_role(
        self,
        member: WorkspaceMemberModel,
        role: str,
    ) -> WorkspaceMemberModel:
        member.role = role
        await self._session.flush()
        return member

    async def remove_member(self, workspace_id: UUID, user_id: UUID) -> None:
        await self._session.execute(
            delete(WorkspaceMemberModel).where(
                WorkspaceMemberModel.workspace_id == workspace_id,
                WorkspaceMemberModel.user_id == user_id,
            )
        )
        await self._session.flush()

    async def count_owners(self, workspace_id: UUID) -> int:
        result = await self._session.execute(
            select(func.count()).select_from(WorkspaceMemberModel).where(
                WorkspaceMemberModel.workspace_id == workspace_id,
                WorkspaceMemberModel.role == "owner",
            )
        )
        return int(result.scalar_one())
