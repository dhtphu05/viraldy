from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from viraldy.modules.workspaces.repository import WorkspaceRepository
from viraldy.modules.workspaces.schemas import CreateWorkspaceRequest, WorkspaceResponse
from viraldy.shared.errors.base import NotFoundError


class WorkspaceService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repository = WorkspaceRepository(session)

    async def create_workspace(
        self, data: CreateWorkspaceRequest, user_id: UUID
    ) -> WorkspaceResponse:
        workspace = await self._repository.create(data.name, data.slug, user_id)
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
