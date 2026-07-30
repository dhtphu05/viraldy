from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

FeedbackSubjectType = Literal[
    "creative_dna",
    "pattern_kit",
    "viral_kit",
    "tiktok_score",
    "preflight",
    "recommendation",
]
FeedbackType = Literal[
    "correct",
    "incorrect",
    "partial",
    "missing",
    "false_positive",
    "false_negative",
    "not_useful",
]
FeedbackJsonValue = dict[str, object] | list[object] | str | int | float | bool | None


class FeedbackContractBase(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FieldFeedbackV1(FeedbackContractBase):
    subject_type: FeedbackSubjectType
    subject_id: UUID
    subject_version: int | None = Field(default=None, ge=1)
    field_path: str = Field(min_length=1, max_length=500)
    feedback_type: FeedbackType
    ai_value_json: FeedbackJsonValue = None
    user_value_json: FeedbackJsonValue = None
    comment: str | None = Field(default=None, max_length=2000)
    model_run_id: UUID | None = None
