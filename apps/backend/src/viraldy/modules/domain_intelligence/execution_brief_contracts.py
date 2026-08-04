from __future__ import annotations

from typing import Literal

from pydantic import Field

from viraldy.modules.domain_intelligence.schemas import StrictBaseModel


class UGCExecutionBriefRecommendationPatchV1(StrictBaseModel):
    recommendation_id: str = Field(min_length=1, max_length=160)
    title: str | None = Field(default=None, min_length=1)
    reason: str | None = Field(default=None, min_length=1)
    exact_action: str | None = Field(default=None, min_length=1)
    exact_copy: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)


class UGCExecutionBriefSynthesisV1(StrictBaseModel):
    schema_version: Literal["ugc_execution_brief_synthesis_v1"] = (
        "ugc_execution_brief_synthesis_v1"
    )
    recommendation_patches: list[UGCExecutionBriefRecommendationPatchV1] = Field(
        default_factory=list
    )
    creator_revision_message: str | None = Field(default=None, min_length=1)


__all__ = [
    "UGCExecutionBriefRecommendationPatchV1",
    "UGCExecutionBriefSynthesisV1",
]
