from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from viraldy.modules.product_events.contracts import ProductEventType
from viraldy.modules.product_events.repository import ProductEventRepository
from viraldy.modules.product_events.schemas import ProductEventResponse


class ProductEventService:
    def __init__(self, session: AsyncSession) -> None:
        self._repository = ProductEventRepository(session)

    async def list_events(
        self,
        *,
        workspace_id: UUID,
        event_type: ProductEventType | None = None,
        subject_type: str | None = None,
        limit: int = 100,
    ) -> list[ProductEventResponse]:
        events = await self._repository.list_for_workspace(
            workspace_id=workspace_id,
            event_type=event_type,
            subject_type=subject_type,
            limit=limit,
        )
        return [ProductEventResponse.model_validate(event) for event in events]
