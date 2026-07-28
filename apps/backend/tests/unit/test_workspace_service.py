from __future__ import annotations

from typing import cast
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from viraldy.modules.workspaces.models import WorkspaceModel
from viraldy.modules.workspaces.schemas import CreateWorkspaceRequest
from viraldy.modules.workspaces.service import WorkspaceService


class FakeSession:
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1


class FakeWorkspaceRepository:
    def __init__(self, session: FakeSession) -> None:
        self.session = session
        self.created_by_user_id: UUID | None = None

    async def create(
        self,
        name: str,
        slug: str,
        created_by_user_id: UUID,
    ) -> WorkspaceModel:
        self.created_by_user_id = created_by_user_id
        return WorkspaceModel(
            id=uuid4(),
            name=name,
            slug=slug,
            status="active",
            created_by_user_id=created_by_user_id,
        )


@pytest.mark.asyncio
async def test_workspace_service_creates_owner_workspace(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import viraldy.modules.workspaces.service as service_module

    session = FakeSession()
    repository = FakeWorkspaceRepository(session)
    monkeypatch.setattr(service_module, "WorkspaceRepository", lambda _: repository)
    user_id = uuid4()

    workspace = await WorkspaceService(cast(AsyncSession, session)).create_workspace(
        CreateWorkspaceRequest(name="Viraldy Team", slug="viraldy-team"),
        user_id,
    )

    assert workspace.name == "Viraldy Team"
    assert workspace.slug == "viraldy-team"
    assert repository.created_by_user_id == user_id
    assert session.commits == 1
