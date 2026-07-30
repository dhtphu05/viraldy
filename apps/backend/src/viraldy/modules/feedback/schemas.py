from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from viraldy.modules.feedback.contracts import (
    FeedbackJsonValue,
    FeedbackSubjectType,
    FeedbackType,
    FieldFeedbackV1,
)


class CreateFeedbackRequest(FieldFeedbackV1):
    pass


class FeedbackResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    subject_type: FeedbackSubjectType
    subject_id: UUID
    subject_version: int | None
    field_path: str
    feedback_type: FeedbackType
    ai_value_json: FeedbackJsonValue = None
    user_value_json: FeedbackJsonValue = None
    comment: str | None
    model_run_id: UUID | None
    created_by_user_id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class ListFeedbackQuery(BaseModel):
    subject_type: FeedbackSubjectType | None = None
    subject_id: UUID | None = None
    limit: int = Field(default=100, ge=1, le=500)
