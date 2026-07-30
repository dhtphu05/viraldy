from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from viraldy.modules.feedback.public import FeedbackJsonValue, FeedbackType
from viraldy.modules.pattern_kits.contracts import (
    PatternExtractionModeV1,
    PatternKitKindV1,
    PatternKitScopeV1,
    PatternKitStatusV1,
    PatternKitV1,
)


class CreatePatternKitRequest(BaseModel):
    name: str = Field(min_length=3, max_length=160)
    kind: PatternKitKindV1
    scope: PatternKitScopeV1 = "workspace_private"
    source_creative_dna_version_ids: list[UUID] = Field(min_length=1)
    primary_category: str = Field(min_length=1, max_length=100)
    target_platforms: list[str] = Field(min_length=1)
    target_markets: list[str] = Field(min_length=1)
    objectives: list[str] = Field(min_length=1)
    extraction_mode: PatternExtractionModeV1 = "ai_assisted"
    review_notes: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_sources(self) -> CreatePatternKitRequest:
        if len(self.source_creative_dna_version_ids) != len(
            set(self.source_creative_dna_version_ids)
        ):
            raise ValueError("source_creative_dna_version_ids cannot contain duplicates")
        if self.kind == "multi_asset_cluster" and len(self.source_creative_dna_version_ids) < 2:
            raise ValueError("multi_asset_cluster requires at least two Creative DNA versions")
        return self


class CreatePatternKitVersionRequest(BaseModel):
    change_reason: str = Field(min_length=1, max_length=1000)
    pattern: PatternKitV1 | None = None


class PatternKitActionRequest(BaseModel):
    action: Literal["reviewed", "validated", "deprecated", "archived", "restored"]
    reason: str | None = Field(default=None, max_length=2000)


class CreatePatternKitFeedbackRequest(BaseModel):
    subject_version: int | None = Field(default=None, ge=1)
    field_path: str = Field(min_length=1, max_length=500)
    feedback_type: FeedbackType
    ai_value_json: FeedbackJsonValue = None
    user_value_json: FeedbackJsonValue = None
    comment: str | None = Field(default=None, max_length=2000)
    model_run_id: UUID | None = None


class PatternKitSummaryResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    name: str
    kind: PatternKitKindV1
    scope: PatternKitScopeV1
    status: PatternKitStatusV1
    primary_category: str | None
    target_platforms_json: list[object]
    target_markets_json: list[object]
    objectives_json: list[object]
    latest_version: int
    created_by_user_id: UUID
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None

    model_config = {"from_attributes": True}


class PatternKitVersionResponse(BaseModel):
    id: UUID
    pattern_kit_id: UUID
    workspace_id: UUID
    version: int
    parent_version: int | None
    change_reason: str | None
    schema_version: str
    pattern: PatternKitV1
    overall_confidence: str
    model_run_id: UUID | None
    created_by_user_id: UUID
    created_at: datetime


class PatternKitDetailResponse(BaseModel):
    kit: PatternKitSummaryResponse
    latest_version: PatternKitVersionResponse


class PatternKitActionResponse(BaseModel):
    id: UUID
    pattern_kit_id: UUID
    version: int
    action: str
    created_at: datetime

    model_config = {"from_attributes": True}
