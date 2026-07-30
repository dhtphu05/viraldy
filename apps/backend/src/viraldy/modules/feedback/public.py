from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from viraldy.modules.feedback.contracts import FieldFeedbackV1
from viraldy.modules.feedback.models import FeedbackItemModel
from viraldy.modules.feedback.repository import FeedbackRepository


class FeedbackWriter:
    def __init__(self, session: AsyncSession) -> None:
        self._repository = FeedbackRepository(session)

    async def record(
        self,
        *,
        workspace_id: UUID,
        created_by_user_id: UUID,
        feedback: FieldFeedbackV1,
    ) -> FeedbackItemModel:
        return await self._repository.create(
            workspace_id=workspace_id,
            created_by_user_id=created_by_user_id,
            feedback=feedback,
        )


__all__ = ["FeedbackWriter", "FieldFeedbackV1"]
