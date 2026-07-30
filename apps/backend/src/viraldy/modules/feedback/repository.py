from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from viraldy.modules.feedback.contracts import FeedbackSubjectType, FieldFeedbackV1
from viraldy.modules.feedback.models import FeedbackItemModel


class FeedbackRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        workspace_id: UUID,
        created_by_user_id: UUID,
        feedback: FieldFeedbackV1,
    ) -> FeedbackItemModel:
        item = FeedbackItemModel(
            workspace_id=workspace_id,
            subject_type=feedback.subject_type,
            subject_id=feedback.subject_id,
            subject_version=feedback.subject_version,
            field_path=feedback.field_path,
            feedback_type=feedback.feedback_type,
            ai_value_json=feedback.ai_value_json,
            user_value_json=feedback.user_value_json,
            comment=feedback.comment,
            model_run_id=feedback.model_run_id,
            created_by_user_id=created_by_user_id,
        )
        self._session.add(item)
        await self._session.flush()
        return item

    async def list_for_workspace(
        self,
        *,
        workspace_id: UUID,
        subject_type: FeedbackSubjectType | None = None,
        subject_id: UUID | None = None,
        limit: int = 100,
    ) -> list[FeedbackItemModel]:
        statement = select(FeedbackItemModel).where(FeedbackItemModel.workspace_id == workspace_id)
        if subject_type is not None:
            statement = statement.where(FeedbackItemModel.subject_type == subject_type)
        if subject_id is not None:
            statement = statement.where(FeedbackItemModel.subject_id == subject_id)
        result = await self._session.execute(
            statement.order_by(FeedbackItemModel.created_at.desc()).limit(limit)
        )
        return list(result.scalars())
