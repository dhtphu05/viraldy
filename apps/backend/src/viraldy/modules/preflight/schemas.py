from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from viraldy.modules.jobs.public import JobResponse


class CreatePreflightRunRequest(BaseModel):
    ugc_asset_id: UUID
    campaign_pack_version_id: UUID


class PreflightRunResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    ugc_asset_version_id: UUID
    campaign_pack_version_id: UUID
    structural_score_run_id: UUID | None
    status: str
    schema_version: str
    structural_score: float
    brief_alignment_score: float
    preflight_score: float
    confidence: str
    action_label: str
    dimension_scores_json: dict[str, object]
    brief_alignment_json: dict[str, object]
    strengths_json: list[object]
    blockers_json: list[object]
    fixes_json: list[object]
    revision_message: str
    evidence_ids_json: list[object]
    product_snapshot_json: dict[str, object] | None
    product_context_schema_version: str | None
    requirements_snapshot_json: dict[str, object] | None
    analysis_mode: str
    rubric_version: str
    rule_version: str
    model_version: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CreatePreflightRunResponse(BaseModel):
    preflight_run: PreflightRunResponse
    job: JobResponse
