from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from viraldy.modules.jobs.public import JobResponse
from viraldy.modules.tiktok_scorer.contracts import (
    BlockerV2,
    DimensionScoreV2,
    FixV2,
    StrengthV2,
)


class CreateTikTokScoreRequest(BaseModel):
    asset_id: UUID
    product_id: UUID | None = None
    objective: str = "generic_structure"


class TikTokScoreRunResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    asset_version_id: UUID
    creative_dna_version_id: UUID | None
    status: str
    schema_version: str
    structural_score: float
    confidence: str
    action_label: str
    dimension_scores_json: dict[str, DimensionScoreV2]
    strengths_json: list[StrengthV2]
    blockers_json: list[BlockerV2]
    fixes_json: list[FixV2]
    evidence_ids_json: list[UUID]
    analysis_mode: str
    rubric_version: str
    rule_version: str
    model_version: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CreateTikTokScoreResponse(BaseModel):
    score_run: TikTokScoreRunResponse
    job: JobResponse
