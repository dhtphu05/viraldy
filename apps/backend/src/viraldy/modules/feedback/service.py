from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from viraldy.modules.feedback.contracts import FeedbackSubjectType
from viraldy.modules.feedback.repository import FeedbackRepository
from viraldy.modules.feedback.schemas import CreateFeedbackRequest, FeedbackResponse
from viraldy.modules.product_events.public import ProductEventPublisher, ProductEventType


class FeedbackService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repository = FeedbackRepository(session)
        self._events = ProductEventPublisher(session)

    async def create_feedback(
        self,
        *,
        workspace_id: UUID,
        user_id: UUID,
        data: CreateFeedbackRequest,
    ) -> FeedbackResponse:
        feedback = await self._repository.create(
            workspace_id=workspace_id,
            created_by_user_id=user_id,
            feedback=data,
        )
        await self._record_correction_event(workspace_id, user_id, data)
        await self._session.commit()
        await self._session.refresh(feedback)
        return FeedbackResponse.model_validate(feedback)

    async def list_feedback(
        self,
        *,
        workspace_id: UUID,
        subject_type: FeedbackSubjectType | None = None,
        subject_id: UUID | None = None,
        limit: int = 100,
    ) -> list[FeedbackResponse]:
        items = await self._repository.list_for_workspace(
            workspace_id=workspace_id,
            subject_type=subject_type,
            subject_id=subject_id,
            limit=limit,
        )
        return [FeedbackResponse.model_validate(item) for item in items]

    async def _record_correction_event(
        self,
        workspace_id: UUID,
        user_id: UUID,
        data: CreateFeedbackRequest,
    ) -> None:
        event_type = _correction_event_for_subject(data.subject_type)
        if event_type is None:
            return
        await self._events.record(
            event_type=event_type,
            workspace_id=workspace_id,
            actor_user_id=user_id,
            subject_type=data.subject_type,
            subject_id=data.subject_id,
            payload_json={
                "subject_version": data.subject_version,
                "field_path": data.field_path,
                "feedback_type": data.feedback_type,
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
