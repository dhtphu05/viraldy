from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from viraldy.modules.jobs.public import JobResponse


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
    dimension_scores_json: dict[str, object]
    strengths_json: list[object]
    blockers_json: list[object]
    fixes_json: list[object]
    evidence_ids_json: list[object]
    analysis_mode: str
    rubric_version: str
    rule_version: str
    model_version: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CreateTikTokScoreResponse(BaseModel):
    score_run: TikTokScoreRunResponse
    job: JobResponse
