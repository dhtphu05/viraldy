from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from viraldy.modules.creative_domain.schema_versions import RECOMMENDATION_SCHEMA_VERSION


class RecommendationContractBase(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RecommendationEvidenceV2(RecommendationContractBase):
    evidence_ids: list[UUID] = Field(default_factory=list)
    blockers: list[dict[str, object]] = Field(default_factory=list)
    fixes: list[dict[str, object]] = Field(default_factory=list)


class RecommendationPayloadV2(RecommendationContractBase):
    schema_version: Literal["recommendation_v2"] = RECOMMENDATION_SCHEMA_VERSION
    subject_type: str
    subject_id: UUID
    recommendation_type: str
    action: str
    confidence: str
    reasoning: str
    evidence: RecommendationEvidenceV2
    assumptions: list[object] = Field(default_factory=list)
    rule_version: str | None = None
    source_run_id: UUID | None = None
