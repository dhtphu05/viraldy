from __future__ import annotations

from typing import cast
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from viraldy.modules.identity.public import UserSummary
from viraldy.modules.workspaces.models import WorkspaceMemberModel, WorkspaceModel
from viraldy.modules.workspaces.schemas import (
    AddWorkspaceMemberRequest,
    CreateWorkspaceRequest,
    UpdateWorkspaceMemberRequest,
)
from viraldy.modules.workspaces.service import WorkspaceService
from viraldy.platform.clock.utc import utc_now
from viraldy.shared.errors.base import AppError


class FakeSession:
    def __init__(self) -> None:
        self.commits = 0
        self.refreshed: list[object] = []

    async def commit(self) -> None:
        self.commits += 1

    async def refresh(self, item: object) -> None:
        self.refreshed.append(item)


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


class FakeIdentityQueries:
    def __init__(self, user: UserSummary | None = None) -> None:
        self.user = user

    async def get_by_email(self, email: str) -> UserSummary | None:
        return self.user if self.user and self.user.email == email else None

    async def list_by_ids(self, user_ids: list[UUID]) -> list[UserSummary]:
        if self.user and self.user.id in user_ids:
            return [self.user]
        return []


class FakeProductEventPublisher:
    def __init__(self, session: FakeSession) -> None:
        self.session = session
        self.records: list[dict[str, object]] = []

    async def record(self, **kwargs: object) -> None:
        self.records.append(kwargs)


class FakeMemberRepository:
    def __init__(self, member: WorkspaceMemberModel | None = None, owner_count: int = 1) -> None:
        self.member = member
        self.owner_count = owner_count
        self.added_role: str | None = None

    async def add_member(
        self,
        workspace_id: UUID,
        user_id: UUID,
        role: str,
    ) -> WorkspaceMemberModel:
        self.added_role = role
        return WorkspaceMemberModel(
            workspace_id=workspace_id,
            user_id=user_id,
            role=role,
            created_at=utc_now(),
        )

    async def get_member(
        self,
        workspace_id: UUID,
        user_id: UUID,
    ) -> WorkspaceMemberModel | None:
        return self.member

    async def count_owners(self, workspace_id: UUID) -> int:
        return self.owner_count


@pytest.mark.asyncio
async def test_workspace_service_creates_owner_workspace(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import viraldy.modules.workspaces.service as service_module

    session = FakeSession()
    repository = FakeWorkspaceRepository(session)
    event_publisher = FakeProductEventPublisher(session)
    monkeypatch.setattr(service_module, "WorkspaceRepository", lambda _: repository)
    monkeypatch.setattr(service_module, "ProductEventPublisher", lambda _: event_publisher)
    user_id = uuid4()

    workspace = await WorkspaceService(cast(AsyncSession, session)).create_workspace(
        CreateWorkspaceRequest(name="Viraldy Team", slug="viraldy-team"),
        user_id,
    )

    assert workspace.name == "Viraldy Team"
    assert workspace.slug == "viraldy-team"
    assert repository.created_by_user_id == user_id
    assert event_publisher.records == [
        {
            "event_type": "workspace_created",
            "workspace_id": workspace.id,
            "actor_user_id": user_id,
            "subject_type": "workspace",
            "subject_id": workspace.id,
            "payload_json": {"name": "Viraldy Team", "slug": "viraldy-team"},
        }
    ]
    assert session.commits == 1


@pytest.mark.asyncio
async def test_workspace_service_adds_active_member_by_email(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import viraldy.modules.workspaces.service as service_module

    session = FakeSession()
    user = UserSummary(
        id=uuid4(),
        email="member@example.com",
        display_name="Member",
        status="active",
    )
    repository = FakeMemberRepository()
    monkeypatch.setattr(service_module, "WorkspaceRepository", lambda _: repository)
    monkeypatch.setattr(service_module, "IdentityQueries", lambda _: FakeIdentityQueries(user))
    workspace_id = uuid4()

    member = await WorkspaceService(cast(AsyncSession, session)).add_member(
        workspace_id,
        AddWorkspaceMemberRequest(email="member@example.com", role="member"),
    )

    assert member.workspace_id == workspace_id
    assert member.user_id == user.id
    assert member.role == "member"
    assert repository.added_role == "member"
    assert session.commits == 1


@pytest.mark.asyncio
async def test_workspace_service_rejects_last_owner_self_demotion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import viraldy.modules.workspaces.service as service_module

    session = FakeSession()
    actor_id = uuid4()
    workspace_id = uuid4()
    repository = FakeMemberRepository(
        WorkspaceMemberModel(
            workspace_id=workspace_id,
            user_id=actor_id,
            role="owner",
            created_at=utc_now(),
        ),
        owner_count=1,
    )
    monkeypatch.setattr(service_module, "WorkspaceRepository", lambda _: repository)
    monkeypatch.setattr(service_module, "IdentityQueries", lambda _: FakeIdentityQueries())

    with pytest.raises(AppError, match="WORKSPACE_LAST_OWNER_REQUIRED"):
        await WorkspaceService(cast(AsyncSession, session)).update_member(
            workspace_id,
            actor_id,
            actor_id,
            UpdateWorkspaceMemberRequest(role="admin"),
        )
