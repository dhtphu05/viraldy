from __future__ import annotations

from datetime import UTC, datetime
from typing import cast
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from viraldy.modules.product_events.models import ProductEventModel
from viraldy.modules.product_events.service import ProductEventService


class FakeSession:
    pass


class FakeProductEventRepository:
    def __init__(self, session: FakeSession) -> None:
        self.session = session
        self.list_args: dict[str, object] | None = None
        self.event = ProductEventModel(
            id=uuid4(),
            workspace_id=uuid4(),
            actor_user_id=uuid4(),
            event_type="product_created",
            subject_type="product",
            subject_id=uuid4(),
            payload_json={"source": "unit"},
            created_at=datetime.now(UTC),
        )

    async def list_for_workspace(self, **kwargs: object) -> list[ProductEventModel]:
        self.list_args = kwargs
        self.event.workspace_id = cast(UUID, kwargs["workspace_id"])
        return [self.event]


@pytest.mark.asyncio
async def test_product_event_service_lists_exportable_events(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import viraldy.modules.product_events.service as service_module

    session = FakeSession()
    repository = FakeProductEventRepository(session)
    monkeypatch.setattr(service_module, "ProductEventRepository", lambda _: repository)
    workspace_id = uuid4()

    events = await ProductEventService(cast(AsyncSession, session)).list_events(
        workspace_id=workspace_id,
        event_type="product_created",
        subject_type="product",
        limit=50,
    )

    assert len(events) == 1
    assert events[0].workspace_id == workspace_id
    assert repository.list_args == {
        "workspace_id": workspace_id,
        "event_type": "product_created",
        "subject_type": "product",
        "limit": 50,
    }
