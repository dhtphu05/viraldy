from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from viraldy.modules.workspaces.models import WorkspaceMemberModel, WorkspaceModel


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

    async def list_for_user(self, user_id: UUID) -> list[WorkspaceModel]:
        result = await self._session.execute(
            select(WorkspaceModel)
            .join(WorkspaceMemberModel, WorkspaceMemberModel.workspace_id == WorkspaceModel.id)
            .where(WorkspaceMemberModel.user_id == user_id)
            .order_by(WorkspaceModel.created_at.desc())
        )
        return list(result.scalars())

    async def get_for_user(self, workspace_id: UUID, user_id: UUID) -> WorkspaceModel | None:
        result = await self._session.execute(
            select(WorkspaceModel)
            .join(WorkspaceMemberModel, WorkspaceMemberModel.workspace_id == WorkspaceModel.id)
            .where(WorkspaceModel.id == workspace_id, WorkspaceMemberModel.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_member_role(self, workspace_id: UUID, user_id: UUID) -> str | None:
        result = await self._session.execute(
            select(WorkspaceMemberModel.role).where(
                WorkspaceMemberModel.workspace_id == workspace_id,
                WorkspaceMemberModel.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()
