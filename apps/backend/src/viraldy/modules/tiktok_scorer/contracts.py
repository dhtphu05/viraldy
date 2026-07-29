from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from viraldy.modules.creative_domain.schema_versions import (
    TIKTOK_RUBRIC_VERSION,
    TIKTOK_RULE_VERSION,
    TIKTOK_SCORE_SCHEMA_VERSION,
)


class TikTokScoreContractBase(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ScoreSignalV2(TikTokScoreContractBase):
    code: str
    value: str | int | float | bool | None
    contribution: float
    confidence: float = Field(ge=0, le=1)
    evidence_ids: list[UUID] = Field(default_factory=list)


class DimensionScoreV2(TikTokScoreContractBase):
    dimension: str
    score: int = Field(ge=0, le=100)
    confidence: Literal["low", "medium", "high"]
    reason: str
    signals: list[ScoreSignalV2] = Field(default_factory=list)
    evidence_ids: list[UUID] = Field(default_factory=list)
    missing_signals: list[str] = Field(default_factory=list)


class BlockerV2(TikTokScoreContractBase):
    code: str
    severity: Literal["hard", "high", "medium"]
    message: str
    evidence_ids: list[UUID] = Field(default_factory=list)
    remediation_code: str | None = None


class FixV2(TikTokScoreContractBase):
    code: str
    priority: int
    instruction: str
    why: str
    expected_impact_dimensions: list[str] = Field(default_factory=list)
    evidence_ids: list[UUID] = Field(default_factory=list)


class StrengthV2(TikTokScoreContractBase):
    code: str
    message: str
    dimensions: list[str]
    evidence_ids: list[UUID] = Field(default_factory=list)


class TikTokScoreResultV2(TikTokScoreContractBase):
    schema_version: Literal["tiktok_score_v2"] = TIKTOK_SCORE_SCHEMA_VERSION
    structural_score: int = Field(ge=0, le=100)
    confidence: Literal["low", "medium", "high"]
    action: Literal[
        "reject_or_reshoot",
        "revise",
        "organic_ready_or_small_test",
        "approve_structure",
    ]
    dimensions: dict[str, DimensionScoreV2]
    strengths: list[StrengthV2] = Field(default_factory=list)
    blockers: list[BlockerV2] = Field(default_factory=list)
    fixes: list[FixV2] = Field(default_factory=list)
    evidence_ids: list[UUID] = Field(default_factory=list)
    rubric_version: Literal["tiktok_structure_rubric_v2"] = TIKTOK_RUBRIC_VERSION
    rule_version: Literal["tiktok_structure_rules_v2"] = TIKTOK_RULE_VERSION
    disclaimer: str
    summary: str
