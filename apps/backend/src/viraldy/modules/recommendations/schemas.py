from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class RecommendationResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    subject_type: str
    subject_id: UUID
    recommendation_type: str
    action: str
    confidence: str
    reasoning: str
    evidence_json: dict[str, object]
    assumptions_json: list[object]
    model_version: str | None
    rule_version: str | None
    source_run_id: UUID | None

    model_config = {"from_attributes": True}


class RecordRecommendationActionRequest(BaseModel):
    action_type: str
    metadata_json: dict[str, object] = Field(default_factory=dict)


class RecommendationActionResponse(BaseModel):
    id: UUID
