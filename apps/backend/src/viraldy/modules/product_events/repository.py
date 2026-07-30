from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from viraldy.modules.product_events.contracts import ProductEventType
from viraldy.modules.product_events.models import ProductEventModel


class ProductEventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

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
        event = ProductEventModel(
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
            event_type=event_type,
            subject_type=subject_type,
            subject_id=subject_id,
            payload_json=payload_json or {},
        )
        self._session.add(event)
        await self._session.flush()
        return event

    async def list_for_workspace(
        self,
        *,
        workspace_id: UUID,
        event_type: ProductEventType | None = None,
        subject_type: str | None = None,
        limit: int = 100,
    ) -> list[ProductEventModel]:
        statement = select(ProductEventModel).where(ProductEventModel.workspace_id == workspace_id)
        if event_type is not None:
            statement = statement.where(ProductEventModel.event_type == event_type)
        if subject_type is not None:
            statement = statement.where(ProductEventModel.subject_type == subject_type)
        result = await self._session.execute(
            statement.order_by(ProductEventModel.created_at.desc()).limit(limit)
        )
        return list(result.scalars())


class SyncProductEventRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def record(
        self,
        *,
        event_type: ProductEventType,
        workspace_id: UUID | None,
        actor_user_id: UUID | None,
        subject_type: str | None = None,
        subject_id: UUID | None = None,
        payload_json: dict[str, object] | None = None,
    ) -> ProductEventModel:
        event = ProductEventModel(
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
            event_type=event_type,
            subject_type=subject_type,
            subject_id=subject_id,
            payload_json=payload_json or {},
        )
        self._session.add(event)
        self._session.flush()
        return event
