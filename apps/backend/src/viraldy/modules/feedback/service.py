from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from viraldy.modules.feedback.contracts import FeedbackSubjectType
from viraldy.modules.feedback.public import FeedbackWriter
from viraldy.modules.feedback.repository import FeedbackRepository
from viraldy.modules.feedback.schemas import CreateFeedbackRequest, FeedbackResponse


class FeedbackService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repository = FeedbackRepository(session)
        self._writer = FeedbackWriter(session)

    async def create_feedback(
        self,
        *,
        workspace_id: UUID,
        user_id: UUID,
        data: CreateFeedbackRequest,
    ) -> FeedbackResponse:
        feedback = await self._writer.record(
            workspace_id=workspace_id,
            created_by_user_id=user_id,
            feedback=data,
        )
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
