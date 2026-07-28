from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from viraldy.modules.workspaces.repository import WorkspaceRepository


async def get_workspace_member_role(
    session: AsyncSession,
    workspace_id: UUID,
    user_id: UUID,
) -> str | None:
    return await WorkspaceRepository(session).get_member_role(workspace_id, user_id)
