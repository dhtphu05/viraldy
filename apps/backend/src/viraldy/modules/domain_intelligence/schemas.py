from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

RecommendationGroup = Literal["fix_first", "improve", "confirm"]
RecommendationTaskKind = Literal[
    "video_edit_required",
    "publish_ops_required",
    "seller_input_required",
    "keep",
    "do_not_change",
]
RecommendationPriority = Literal[
    "fix_before_publish",
    "confirm_before_publish",
    "optional_improvement",
    "keep",
]
ReviewFixType = Literal[
    "edit_existing_footage",
    "add_overlay",
    "replace_copy",
    "reshoot_scene",
    "confirm_seller_input",
    "request_better_media",
]
OwnerRole = Literal["seller", "creator", "editor"]
ReviewNextAction = Literal[
    "use_as_is",
    "revise",
    "reshoot_scene",
    "confirm_information",
    "request_better_media",
]
Confidence = Literal["high", "medium", "low"]
UnknownState = Literal[
    "unknown",
    "insufficient_evidence",
    "seller_confirmation_required",
    "expert_review_required",
    "policy_conflict",
    "rights_incomplete",
    "economics_insufficient",
    "supplier_data_stale",
    "publish_check_required",
]
CommerceDomain = Literal[
    "generic",
    "tiktok_shop_us",
    "pod_personalization",
    "dropshipping",
]
IntendedUse = Literal[
    "organic",
    "affiliate",
    "paid_candidate",
    "spark_candidate",
    "unknown",
]
MaterialConnection = Literal["yes", "no", "unknown"]
EvidenceSource = Literal["video", "transcript", "ocr", "seller_input", "brief", "policy"]


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class UGCReviewContext(StrictBaseModel):
    market: str = Field(default="US", min_length=1, max_length=100)
    platform: str = Field(default="tiktok_shop", min_length=1, max_length=100)
    commerce_domain: CommerceDomain = "generic"
    intended_use: IntendedUse = "unknown"
    product_name: str | None = Field(default=None, max_length=255)
    product_category: str | None = Field(default=None, max_length=160)
    exact_variant_or_sku: str | None = Field(default=None, max_length=255)
    product_description: str | None = Field(default=None, max_length=10_000)
    current_offer: str | None = Field(default=None, max_length=2_000)
    verified_shipping_language: str | None = Field(default=None, max_length=2_000)
    approved_personalization: str | None = Field(default=None, max_length=2_000)
    physical_sample_available: bool | None = None
    creator_brief: str | None = Field(default=None, max_length=30_000)
    material_connection: MaterialConnection = "unknown"
    seller_notes: str | None = Field(default=None, max_length=10_000)


class ReviewEvidence(StrictBaseModel):
    id: str = Field(min_length=1, max_length=160)
    source: EvidenceSource
    observed: str = Field(min_length=1)
    start_ms: int | None = Field(default=None, ge=0)
    end_ms: int | None = Field(default=None, ge=0)
    confidence: Confidence

    @model_validator(mode="after")
    def validate_range(self) -> ReviewEvidence:
        if self.start_ms is not None and self.end_ms is not None and self.end_ms < self.start_ms:
            raise ValueError("end_ms must be greater than or equal to start_ms")
        return self


class ReviewTimeRange(StrictBaseModel):
    start_ms: int = Field(ge=0)
    end_ms: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_range(self) -> ReviewTimeRange:
        if self.end_ms is not None and self.end_ms < self.start_ms:
            raise ValueError("end_ms must be greater than or equal to start_ms")
        return self


class UGCRecommendation(StrictBaseModel):
    id: str = Field(min_length=1, max_length=160)
    rule_code: str | None = Field(default=None, max_length=100)
    mistake_code: str | None = Field(default=None, max_length=100)
    group: RecommendationGroup
    title: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    why_it_matters: str = Field(min_length=1)
    owner: OwnerRole
    fix_type: ReviewFixType | None = None
    instructions: list[str] = Field(default_factory=list)
    strengths_to_preserve: list[str] = Field(default_factory=list)
    completion_criteria: list[str] = Field(default_factory=list)
    evidence: list[ReviewEvidence] = Field(default_factory=list)
    confidence: Confidence
    affected_use: str | None = None
    unknown_state: UnknownState | None = None
    task_kind: RecommendationTaskKind = "video_edit_required"
    priority: RecommendationPriority = "optional_improvement"
    time_range: ReviewTimeRange | None = None
    exact_action: str | None = Field(default=None, min_length=1)
    exact_copy: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)


class UGCReviewResult(StrictBaseModel):
    review_id: str = Field(min_length=1)
    status: Literal["completed"] = "completed"
    headline: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    recommended_next_action: ReviewNextAction
    overall_confidence: Confidence
    strengths_to_keep: list[str] = Field(min_length=1)
    fix_first: list[UGCRecommendation] = Field(default_factory=list)
    improvements: list[UGCRecommendation] = Field(default_factory=list)
    confirmations: list[UGCRecommendation] = Field(default_factory=list)
    creator_revision_message: str = Field(min_length=1)
    policy_pack_version: str = Field(min_length=1)
    analysis_provenance: dict[str, object] = Field(default_factory=dict)
    created_at: str = Field(min_length=1)


class UGCRevisionComparison(StrictBaseModel):
    parent_review_id: str
    revision_review_id: str
    summary: str
    resolved: list[dict[str, object]] = Field(default_factory=list)
    still_open: list[dict[str, object]] = Field(default_factory=list)
    new_findings: list[dict[str, object]] = Field(default_factory=list)
    strengths_preserved: list[str] = Field(default_factory=list)


class NormalizedEvidence(StrictBaseModel):
    id: str = Field(min_length=1, max_length=160)
    kind: str = Field(min_length=1, max_length=100)
    source: EvidenceSource
    observed: str = Field(min_length=1)
    start_ms: int | None = Field(default=None, ge=0)
    end_ms: int | None = Field(default=None, ge=0)
    confidence: Confidence
    value: dict[str, object] = Field(default_factory=dict)


class NormalizedEvidenceBundle(StrictBaseModel):
    items: list[NormalizedEvidence] = Field(default_factory=list)
    coverage: dict[str, bool] = Field(default_factory=dict)
    missing_required: list[str] = Field(default_factory=list)
    unknowns: list[UnknownState] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)
    pipeline_version: str | None = None


class DomainRule(StrictBaseModel):
    code: str = Field(min_length=1, max_length=100)
    domain: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1)
    rule_type: str = Field(min_length=1, max_length=100)
    severity: str = Field(min_length=1, max_length=100)
    enabled_for_mvp: bool = False
    applicability: list[object] = Field(default_factory=list)
    required_conditions: list[object] = Field(default_factory=list)
    implementation: dict[str, object] = Field(default_factory=dict)
    source_ids: list[str] = Field(default_factory=list)
    raw_payload: dict[str, object] = Field(default_factory=dict)


class PolicyPackCounts(StrictBaseModel):
    policies: int = Field(ge=0)
    patterns: int = Field(ge=0)
    mistakes: int = Field(ge=0)
    uncertainties: int = Field(ge=0)
    sources: int = Field(ge=0)


class PolicyPackStatus(StrictBaseModel):
    pack_name: str
    version: str
    content_hash: str = Field(min_length=64, max_length=64)
    status: str
    counts: PolicyPackCounts
    active_rule_codes: list[str] = Field(default_factory=list)


class EvaluationCandidate(StrictBaseModel):
    rule_code: str | None = None
    mistake_code: str | None = None
    group: RecommendationGroup
    title: str
    reason: str
    why_it_matters: str
    owner: OwnerRole
    fix_type: ReviewFixType | None = None
    instructions: list[str] = Field(default_factory=list)
    strengths_to_preserve: list[str] = Field(default_factory=list)
    completion_criteria: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    confidence: Confidence
    affected_use: str | None = None
    unknown_state: UnknownState | None = None
    task_kind: RecommendationTaskKind | None = None
    priority: RecommendationPriority | None = None
    time_range: ReviewTimeRange | None = None
    exact_action: str | None = Field(default=None, min_length=1)
    exact_copy: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)


class ImportSummary(StrictBaseModel):
    pack_name: str
    version: str
    content_hash: str
    counts: PolicyPackCounts
    inserted: int = 0
    updated: int = 0
    skipped: int = 0
    dry_run: bool = False
