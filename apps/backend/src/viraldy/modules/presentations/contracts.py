from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

SellerLocale = Literal["en-US", "vi-VN"]
CreatorLocale = Literal["en-US"]


class PresentationContractBase(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PresentationBlockerV1(PresentationContractBase):
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)


class PresentationFixV1(PresentationContractBase):
    code: str = Field(min_length=1)
    instruction: str = Field(min_length=1)
    required_text: str | None = None
    target_start_ms: int | None = Field(default=None, ge=0)
    target_end_ms: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_target_range(self) -> PresentationFixV1:
        if (
            self.target_start_ms is not None
            and self.target_end_ms is not None
            and self.target_end_ms < self.target_start_ms
        ):
            raise ValueError("target_end_ms must be greater than or equal to target_start_ms")
        return self


class SellerDecisionInputV1(PresentationContractBase):
    product_name: str = Field(min_length=1)
    objective: str | None = None
    action_label: Literal[
        "revise",
        "ready_for_organic",
        "small_paid_test",
        "reject_or_reshoot",
    ]
    final_score: int = Field(ge=0, le=100)
    structural_score: int = Field(ge=0, le=100)
    brief_alignment_score: int = Field(ge=0, le=100)
    confidence: Literal["low", "medium", "high"]
    strengths: list[str] = Field(default_factory=list)
    blockers: list[PresentationBlockerV1] = Field(default_factory=list)
    fixes: list[PresentationFixV1] = Field(default_factory=list)
    next_action: str = Field(min_length=1)
    locale: SellerLocale = "en-US"


class SellerDecisionSummaryV1(PresentationContractBase):
    schema_version: Literal["seller_decision_summary_v1"] = (
        "seller_decision_summary_v1"
    )
    headline: str = Field(min_length=1)
    one_sentence_decision: str = Field(min_length=1)
    why_this_matters: str = Field(min_length=1)
    strengths_to_keep: list[str] = Field(default_factory=list)
    blockers_to_fix: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(min_length=1)
    confidence_explanation: str = Field(min_length=1)
    commercial_guardrail: str = Field(min_length=1)
    locale: SellerLocale


class GeneratePresentationRequestV1(PresentationContractBase):
    seller_locale: SellerLocale = "en-US"
    force_regenerate: bool = False


class CreatorRevisionInputV2(PresentationContractBase):
    product_name: str = Field(min_length=1)
    strengths_to_preserve: list[str] = Field(min_length=1, max_length=5)
    required_changes: list[PresentationFixV1] = Field(min_length=1)
    allowed_blocker_codes: list[str] = Field(min_length=1)
    resubmission_request: str = Field(min_length=1)
    locale: CreatorLocale = "en-US"

    @model_validator(mode="after")
    def validate_referenced_blockers(self) -> CreatorRevisionInputV2:
        allowed = set(self.allowed_blocker_codes)
        referenced = {change.code for change in self.required_changes}
        if not referenced.issubset(allowed):
            raise ValueError("required_changes may reference only supplied blocker codes")
        return self


class CreatorRevisionMessageV2(PresentationContractBase):
    schema_version: Literal["creator_revision_message_v2"] = (
        "creator_revision_message_v2"
    )
    message: str = Field(min_length=1)
    strengths_to_preserve: list[str] = Field(min_length=1)
    required_changes: list[PresentationFixV1] = Field(min_length=1)
    referenced_blocker_codes: list[str] = Field(min_length=1)
    resubmission_request: str = Field(min_length=1)
    locale: CreatorLocale = "en-US"


class PreflightPresentationBundleV1(PresentationContractBase):
    preflight_run_id: UUID
    seller_summary: SellerDecisionSummaryV1
    creator_revision: CreatorRevisionMessageV2 | None = None
    sources: dict[
        str,
        Literal[
            "openai",
            "mock",
            "deterministic",
            "deterministic_fallback",
        ],
    ]
    model_run_ids: list[UUID] = Field(default_factory=list)
