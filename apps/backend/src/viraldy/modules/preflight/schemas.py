from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, field_validator

from viraldy.modules.campaign_packs.requirements import CompiledRequirementsSnapshotV2
from viraldy.modules.jobs.public import JobResponse
from viraldy.modules.preflight.contracts import BriefAlignmentResultV2
from viraldy.modules.products.contracts import ProductContextV1
from viraldy.modules.tiktok_scorer.contracts import BlockerV2, DimensionScoreV2, FixV2, StrengthV2


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
    dimension_scores_json: dict[str, DimensionScoreV2]
    brief_alignment_json: BriefAlignmentResultV2
    strengths_json: list[StrengthV2]
    blockers_json: list[BlockerV2]
    fixes_json: list[FixV2]
    revision_message: str
    evidence_ids_json: list[UUID]
    product_snapshot_json: ProductContextV1 | None
    product_context_schema_version: str | None
    requirements_snapshot_json: CompiledRequirementsSnapshotV2 | None
    analysis_mode: str
    rubric_version: str
    rule_version: str
    model_version: str | None
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("brief_alignment_json", mode="before")
    @classmethod
    def coerce_pending_alignment(cls, value: object) -> object:
        if value == {}:
            return {
                "score": 0,
                "confidence": "low",
                "requirements": [],
                "coverage": {
                    "total": 0,
                    "satisfied": 0,
                    "partial": 0,
                    "missing": 0,
                    "violated": 0,
                    "unknown": 0,
                    "not_applicable": 0,
                },
                "blockers": [],
                "fixes": [],
            }
        return value


class CreatePreflightRunResponse(BaseModel):
    preflight_run: PreflightRunResponse
    job: JobResponse
