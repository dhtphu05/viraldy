from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from viraldy.modules.jobs.public import JobResponse

TikTokScoreMode = Literal["quick", "product_aware", "usage_aware"]
TikTokIntendedUse = Literal[
    "tiktok_organic",
    "tiktok_shop_affiliate",
    "ugc_paid_candidate",
    "spark_candidate",
]
ProfileSelectionMode = Literal[
    "user_selected",
    "model_suggested",
    "model_suggested_user_confirmed",
    "inherited",
    "user_overridden",
]
FixActionEventType = Literal[
    "viewed",
    "accepted",
    "rejected",
    "sent_to_creator",
    "sent_to_editor",
    "marked_completed",
    "verified_after_revision",
]
TikTokScorerEventType = Literal[
    "tiktok_scorer_opened",
    "tiktok_score_started",
    "tiktok_score_completed",
    "tiktok_score_failed",
    "tiktok_finding_viewed",
    "tiktok_evidence_opened",
    "tiktok_fix_accepted",
    "tiktok_fix_rejected",
    "tiktok_fix_sent_to_creator",
    "tiktok_fix_sent_to_editor",
    "tiktok_fix_marked_completed",
    "tiktok_revision_uploaded",
    "tiktok_comparison_viewed",
    "tiktok_action_verified_after_revision",
]


class ApiContractBase(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CreateTikTokScoreRequest(ApiContractBase):
    asset_version_id: UUID | None = None
    asset_id: UUID | None = None
    product_id: UUID | None = None
    score_mode: TikTokScoreMode = "quick"
    score_profile: str = Field(default="general_tiktok_v1", min_length=1, max_length=100)
    intended_use: TikTokIntendedUse = "tiktok_organic"
    creative_direction_context_id: UUID | None = None
    idempotency_key: str | None = Field(default=None, min_length=1, max_length=255)
    profile_selection_mode: ProfileSelectionMode = "user_selected"
    profile_selection_confidence: float | None = Field(default=None, ge=0, le=1)
    alternative_profiles: list[str] = Field(default_factory=list)
    profile_evidence_ids: list[UUID] = Field(default_factory=list)
    target_query: str | None = Field(default=None, max_length=500)
    target_buyer_question: str | None = Field(default=None, max_length=500)
    selected_search_topic: str | None = Field(default=None, max_length=500)
    content_gap_topic: str | None = Field(default=None, max_length=500)
    objective: str = Field(default="generic_structure", min_length=1, max_length=200)

    @model_validator(mode="after")
    def validate_asset_and_product(self) -> CreateTikTokScoreRequest:
        if self.asset_version_id is None and self.asset_id is None:
            raise ValueError("asset_version_id or legacy asset_id is required")
        if self.score_mode == "product_aware" and self.product_id is None:
            raise ValueError("product_id is required for Product-Aware Score")
        return self


class CreateTikTokScoreRevisionRequest(ApiContractBase):
    asset_version_id: UUID
    score_profile: str | None = Field(default=None, min_length=1, max_length=100)
    profile_override_reason: str | None = Field(default=None, min_length=1, max_length=1000)
    accepted_fix_action_ids: list[UUID] = Field(default_factory=list)
    idempotency_key: str | None = Field(default=None, min_length=1, max_length=255)


class RecordTikTokFixActionRequest(ApiContractBase):
    event_type: FixActionEventType
    details_json: dict[str, object] = Field(default_factory=dict)
    idempotency_key: str | None = Field(default=None, min_length=1, max_length=255)


class RecordTikTokScorerEventRequest(ApiContractBase):
    event_type: TikTokScorerEventType
    asset_version_id: UUID | None = None
    fix_action_id: UUID | None = None
    finding_id: UUID | None = None
    evidence_id: UUID | None = None
    comparison_id: UUID | None = None
    score_mode: TikTokScoreMode | None = None
    score_profile: str | None = Field(default=None, min_length=1, max_length=100)
    intended_use: TikTokIntendedUse | None = None


class RecordTikTokScorerOpenedRequest(ApiContractBase):
    event_type: Literal["tiktok_scorer_opened"] = "tiktok_scorer_opened"
    score_mode: TikTokScoreMode | None = None
    score_profile: str | None = Field(default=None, min_length=1, max_length=100)
    intended_use: TikTokIntendedUse | None = None


class TikTokScoreRunResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    asset_id: UUID | None
    asset_version_id: UUID
    product_id: UUID | None
    parent_score_run_id: UUID | None
    creative_dna_version_id: UUID | None
    processing_job_id: UUID | None
    status: str
    current_stage: str
    schema_version: str
    score_mode: str
    intended_use: str
    score_profile: str
    score_profile_version: int
    profile_selection_mode: str
    profile_selection_confidence: float | None
    alternative_profiles_json: list[object]
    profile_evidence_ids_json: list[object]
    profile_override_reason: str | None
    product_context_snapshot_json: dict[str, object] | None
    product_context_snapshot_hash: str | None
    product_context_schema_version: str | None
    product_context_version: int | None
    policy_pack_versions_json: dict[str, object]
    rule_versions_json: dict[str, object]
    prompt_versions_json: dict[str, object]
    model_provider_versions_json: dict[str, object]
    media_checksum_sha256: str | None
    creative_direction_context_id: UUID | None
    creative_direction_context_snapshot_json: dict[str, object] | None
    creative_direction_context_version: int | None
    creative_direction_lookup_error: str | None
    structural_score: float | None
    confidence: str
    confidence_json: dict[str, object]
    action_label: str
    creative_structure_decision: str
    paid_use_rights_status: str
    final_paid_readiness: str
    dimension_scores_json: dict[str, object]
    strengths_json: list[object]
    blockers_json: list[object]
    fixes_json: list[object]
    evidence_ids_json: list[UUID]
    scene_inventory_json: dict[str, object] | None
    auxiliary_signals_json: dict[str, object] | None
    creative_upgrades_json: list[object]
    result_json: dict[str, object] | None
    analysis_mode: str
    rubric_version: str
    rule_version: str
    model_version: str | None
    latency_ms: int | None
    token_usage_json: dict[str, object]
    cost_estimate: float | None
    failure_code: str | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class TikTokScoreDimensionResponse(BaseModel):
    id: UUID
    code: str
    label: str
    score: int | None
    applicability: str
    evidence_status: str
    confidence: str
    reason: str
    positive_signals_json: list[object]
    missing_signals_json: list[object]
    uncertainty_json: list[object]
    evidence_ids_json: list[object]
    contributing_rule_codes_json: list[object]
    result_json: dict[str, object]

    model_config = ConfigDict(from_attributes=True)


class TikTokScoreFindingResponse(BaseModel):
    id: UUID
    code: str
    rule_code: str
    rule_class: str
    source_dimension: str
    severity: str
    priority: str
    applicability: str
    evidence_status: str
    title: str
    reason: str
    expected_json: dict[str, object]
    observed_json: dict[str, object]
    target_time_range_ms_json: list[object] | None
    evidence_ids_json: list[object]
    uncertainty_json: list[object]
    requires_seller_truth: bool
    can_be_resolved_by_edit: bool | None
    requires_physical_reshoot: bool | None
    finding_json: dict[str, object]

    model_config = ConfigDict(from_attributes=True)


class TikTokFixActionResponse(BaseModel):
    id: UUID
    score_run_id: UUID
    finding_id: UUID | None
    code: str
    recommendation_class: str
    basis: str
    priority: str
    severity: str
    source_dimension: str
    owner_role: str
    fix_type: str
    title: str
    why_it_matters: str
    expected_json: dict[str, object]
    observed_json: dict[str, object]
    evidence_ids_json: list[object]
    target_time_range_ms_json: list[object] | None
    video_operations_json: list[object]
    instructions_json: list[object]
    strengths_to_preserve_json: list[object]
    required_inputs_json: list[object]
    estimated_effort: str
    reshoot_required: bool
    completion_criteria_json: list[object]
    verification_method: str
    current_action_state: str
    action_json: dict[str, object]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TikTokFixActionEventResponse(BaseModel):
    id: UUID
    score_run_id: UUID
    fix_action_id: UUID
    actor_user_id: UUID | None
    event_type: str
    details_json: dict[str, object]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TikTokScoreComparisonResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    before_score_run_id: UUID
    after_score_run_id: UUID
    status: str
    accepted_fix_action_ids_json: list[object]
    resolved_blockers_json: list[object]
    unresolved_blockers_json: list[object]
    new_regressions_json: list[object]
    dimension_changes_json: list[object]
    evidence_before_after_json: list[object]
    strengths_preserved_json: list[object]
    actions_verified_json: list[object]
    final_next_action: str | None
    comparison_json: dict[str, object]
    failure_code: str | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    before_asset_version_id: UUID | None = None
    after_asset_version_id: UUID | None = None
    before_asset_filename: str | None = None
    after_asset_filename: str | None = None
    before_product_name: str | None = None
    after_product_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


class TikTokScoreProfileResponse(BaseModel):
    id: UUID
    code: str
    label: str
    description: str
    profile_version: int
    weights_json: dict[str, object]
    thresholds_json: dict[str, object]
    configuration_json: dict[str, object]
    is_system: bool

    model_config = ConfigDict(from_attributes=True)


class TikTokEvidencePreviewResponse(BaseModel):
    id: UUID
    evidence_type: str
    source: str
    start_ms: int | None
    end_ms: int | None
    value_summary_json: dict[str, object]
    confidence: float | None
    frame_available: bool


class TikTokScoreDetailResponse(BaseModel):
    score_run: TikTokScoreRunResponse
    job: JobResponse | None
    dimensions: list[TikTokScoreDimensionResponse]
    findings: list[TikTokScoreFindingResponse]
    fix_actions: list[TikTokFixActionResponse]
    evidence: list[TikTokEvidencePreviewResponse]
    asset_filename: str
    asset_name: str
    product_name: str | None
    revision_count: int
    comparison_ids: list[UUID]


class TikTokScoreListItemResponse(TikTokScoreRunResponse):
    asset_filename: str
    asset_name: str
    product_name: str | None
    revision_count: int
    last_updated_at: datetime


class TikTokScoreListResponse(BaseModel):
    items: list[TikTokScoreListItemResponse]
    total: int
    limit: int
    offset: int


class TikTokFixActionListResponse(BaseModel):
    score_run_id: UUID
    items: list[TikTokFixActionResponse]


class TikTokScoreProfileListResponse(BaseModel):
    items: list[TikTokScoreProfileResponse]


class RecordTikTokFixActionResponse(BaseModel):
    fix_action: TikTokFixActionResponse
    event: TikTokFixActionEventResponse


class RecordTikTokScorerEventResponse(BaseModel):
    recorded: bool
    event_id: UUID | None = None


class CreateTikTokScoreResponse(BaseModel):
    score_run: TikTokScoreRunResponse
    job: JobResponse
    run_id: UUID
    job_id: UUID
    status: str
    current_stage: str | None


class CreateTikTokScoreRevisionResponse(BaseModel):
    score_run: TikTokScoreRunResponse
    job: JobResponse
    comparison: TikTokScoreComparisonResponse
    run_id: UUID
    job_id: UUID
    comparison_id: UUID
    status: str
    current_stage: str | None
