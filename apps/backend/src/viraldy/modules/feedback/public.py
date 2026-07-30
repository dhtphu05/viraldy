from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from viraldy.modules.feedback.contracts import (
    FeedbackJsonValue,
    FeedbackSubjectType,
    FeedbackType,
    FieldFeedbackV1,
)
from viraldy.modules.feedback.models import FeedbackItemModel
from viraldy.modules.feedback.repository import FeedbackRepository
from viraldy.modules.feedback.schemas import FeedbackResponse
from viraldy.modules.product_events.public import ProductEventPublisher, ProductEventType


class FeedbackWriter:
    def __init__(self, session: AsyncSession) -> None:
        self._repository = FeedbackRepository(session)
        self._events = ProductEventPublisher(session)

    async def record(
        self,
        *,
        workspace_id: UUID,
        created_by_user_id: UUID,
        feedback: FieldFeedbackV1,
    ) -> FeedbackItemModel:
        item = await self._repository.create(
            workspace_id=workspace_id,
            created_by_user_id=created_by_user_id,
            feedback=feedback,
        )
        await self._record_correction_event(workspace_id, created_by_user_id, feedback)
        return item

    async def _record_correction_event(
        self,
        workspace_id: UUID,
        user_id: UUID,
        feedback: FieldFeedbackV1,
    ) -> None:
        event_type = _correction_event_for_subject(feedback.subject_type)
        if event_type is None:
            return
        await self._events.record(
            event_type=event_type,
            workspace_id=workspace_id,
            actor_user_id=user_id,
            subject_type=feedback.subject_type,
            subject_id=feedback.subject_id,
            payload_json={
                "subject_version": feedback.subject_version,
                "field_path": feedback.field_path,
                "feedback_type": feedback.feedback_type,
            },
        )


def _correction_event_for_subject(
    subject_type: FeedbackSubjectType,
) -> ProductEventType | None:
    if subject_type == "creative_dna":
        return "creative_dna_corrected"
    if subject_type == "pattern_kit":
        return "pattern_kit_corrected"
    return None


__all__ = [
    "FeedbackJsonValue",
    "FeedbackResponse",
    "FeedbackType",
    "FeedbackWriter",
    "FieldFeedbackV1",
]
