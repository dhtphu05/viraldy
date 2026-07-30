from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from viraldy.modules.creative_domain.schema_versions import PREFLIGHT_SCHEMA_VERSION
from viraldy.modules.tiktok_scorer.contracts import BlockerV2, FixV2


class PreflightContractBase(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RequirementEvaluationV2(PreflightContractBase):
    requirement_id: str
    status: Literal["satisfied", "partial", "missing", "violated", "unknown", "not_applicable"]
    score: int = Field(ge=0, le=100)
    confidence: Literal["low", "medium", "high"]
    reason: str
    evidence_ids: list[UUID] = Field(default_factory=list)
    expected: dict[str, object] = Field(default_factory=dict)
    observed: dict[str, object] = Field(default_factory=dict)


class BriefAlignmentResultV2(PreflightContractBase):
    schema_version: Literal["ugc_preflight_v2"] = PREFLIGHT_SCHEMA_VERSION
    score: int = Field(ge=0, le=100)
    confidence: Literal["low", "medium", "high"]
    requirements: list[RequirementEvaluationV2] = Field(default_factory=list)
    coverage: dict[str, object] = Field(default_factory=dict)
    blockers: list[BlockerV2] = Field(default_factory=list)
    fixes: list[FixV2] = Field(default_factory=list)
