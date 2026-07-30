from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from viraldy.modules.product_events.contracts import ProductEventType
from viraldy.modules.product_events.models import ProductEventModel
from viraldy.modules.product_events.repository import ProductEventRepository


class ProductEventPublisher:
    def __init__(self, session: AsyncSession) -> None:
        self._repository = ProductEventRepository(session)

    async def record(
        self,
        *,
        event_type: ProductEventType,
        workspace_id: UUID | None,
        actor_user_id: UUID | None,
        subject_type: str | None = None,
        subject_id: UUID | None = None,
        payload_json: dict[str, object] | None = None,
    ) -> ProductEventModel:
        return await self._repository.record(
            event_type=event_type,
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
            subject_type=subject_type,
            subject_id=subject_id,
            payload_json=payload_json,
        )


__all__ = ["ProductEventPublisher", "ProductEventType"]
