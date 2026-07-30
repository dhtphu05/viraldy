from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from viraldy.modules.creative_domain.schema_versions import PATTERN_KIT_SCHEMA_VERSION

PatternKitKindV1 = Literal[
    "single_asset_abstraction",
    "multi_asset_cluster",
    "workspace_learned_pattern",
    "category_playbook",
]
PatternKitScopeV1 = Literal["workspace_private", "product_specific"]
PatternKitStatusV1 = Literal["candidate", "reviewed", "validated", "deprecated", "archived"]
PatternExtractionModeV1 = Literal["deterministic_fixture", "ai_assisted", "human"]
PatternConfidenceV1 = Literal["low", "medium", "high"]
SourceType = Literal["vision", "asr", "ocr", "derived", "human_correction", "performance"]


class PatternKitContractBase(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PatternEvidenceRefV1(PatternKitContractBase):
    creative_dna_version_id: UUID
    asset_version_id: UUID
    evidence_id: UUID
    feature_path: str = Field(min_length=1, max_length=500)
    source_type: SourceType
    start_ms: int | None = Field(default=None, ge=0)
    end_ms: int | None = Field(default=None, ge=0)
    observation_summary: str = Field(min_length=1, max_length=500)
    confidence: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def validate_time_range(self) -> PatternEvidenceRefV1:
        if self.start_ms is not None and self.end_ms is not None and self.end_ms < self.start_ms:
            raise ValueError("end_ms must be greater than or equal to start_ms")
        return self


class PatternSequenceBeatV1(PatternKitContractBase):
    beat_id: str = Field(min_length=1, max_length=80)
    order: int = Field(ge=1)
    beat_type: Literal[
        "hook",
        "problem",
        "product_reveal",
        "demo",
        "proof",
        "offer",
        "cta",
        "reaction",
        "transition",
        "other",
    ]
    purpose: str = Field(min_length=1, max_length=500)
    recommended_start_ms_min: int | None = Field(default=None, ge=0)
    recommended_start_ms_max: int | None = Field(default=None, ge=0)
    recommended_duration_ms_min: int | None = Field(default=None, ge=0)
    recommended_duration_ms_max: int | None = Field(default=None, ge=0)
    requiredness: Literal["required", "recommended", "optional"]
    evidence_refs: list[PatternEvidenceRefV1] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def validate_ranges(self) -> PatternSequenceBeatV1:
        if (
            self.recommended_start_ms_min is not None
            and self.recommended_start_ms_max is not None
            and self.recommended_start_ms_max < self.recommended_start_ms_min
        ):
            raise ValueError("recommended start range is invalid")
        if (
            self.recommended_duration_ms_min is not None
            and self.recommended_duration_ms_max is not None
            and self.recommended_duration_ms_max < self.recommended_duration_ms_min
        ):
            raise ValueError("recommended duration range is invalid")
        return self


class OpeningPatternV1(PatternKitContractBase):
    primary_hook_types: list[str] = Field(default_factory=list)
    hook_mechanism: str
    opening_visual_pattern: str
    first_three_second_structure: str
    face_presence_preference: str
    product_presence_preference: str
    pattern_interrupt_strategy: str
    evidence_refs: list[PatternEvidenceRefV1] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    uncertainties: list[str] = Field(default_factory=list)


class ProductRevealPatternV1(PatternKitContractBase):
    first_appearance_window_ms: tuple[int | None, int | None]
    preferred_shot_types: list[str] = Field(default_factory=list)
    close_up_expectation: str
    usage_visibility_expectation: str
    screen_time_guidance: str
    reveal_role: str
    product_match_requirement: str
    evidence_refs: list[PatternEvidenceRefV1] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    uncertainties: list[str] = Field(default_factory=list)


class NarrativePatternV1(PatternKitContractBase):
    structures: list[str] = Field(default_factory=list)
    angle_family: str
    buyer_pain_pattern: str
    desired_outcome_pattern: str
    emotional_drivers: list[str] = Field(default_factory=list)
    awareness_stage: str
    narrative_progression: list[str] = Field(default_factory=list)
    evidence_refs: list[PatternEvidenceRefV1] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    uncertainties: list[str] = Field(default_factory=list)


class DemoPatternV1(PatternKitContractBase):
    demo_types: list[str] = Field(default_factory=list)
    mechanism_pattern: str
    required_steps: list[str] = Field(default_factory=list)
    before_state_expectation: str
    after_state_expectation: str
    result_visibility_expectation: str
    continuity_expectation: str
    demo_failure_modes: list[str] = Field(default_factory=list)
    evidence_refs: list[PatternEvidenceRefV1] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    uncertainties: list[str] = Field(default_factory=list)


class ProofPatternV1(PatternKitContractBase):
    proof_types: list[str] = Field(default_factory=list)
    proof_mechanism: str
    verifiability_requirement: str
    proof_timing_guidance: str
    proof_strength_conditions: list[str] = Field(default_factory=list)
    unsupported_proof_risks: list[str] = Field(default_factory=list)
    evidence_refs: list[PatternEvidenceRefV1] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    uncertainties: list[str] = Field(default_factory=list)


class CreatorPatternV1(PatternKitContractBase):
    creator_personas: list[str] = Field(default_factory=list)
    delivery_styles: list[str] = Field(default_factory=list)
    face_presence_preference: str
    speaking_preference: str
    emotion_range: list[str] = Field(default_factory=list)
    pacing_preference: str
    authenticity_cues: list[str] = Field(default_factory=list)
    sales_language_intensity: str
    creator_constraints: list[str] = Field(default_factory=list)
    evidence_refs: list[PatternEvidenceRefV1] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    uncertainties: list[str] = Field(default_factory=list)


class EditingPatternV1(PatternKitContractBase):
    pacing: str
    cut_density: str
    first_three_second_cut_guidance: str
    caption_density: str
    transition_types: list[str] = Field(default_factory=list)
    pattern_interrupt_guidance: list[str] = Field(default_factory=list)
    dead_air_tolerance: str
    visual_safe_zone_guidance: list[str] = Field(default_factory=list)
    evidence_refs: list[PatternEvidenceRefV1] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    uncertainties: list[str] = Field(default_factory=list)


class OfferPatternV1(PatternKitContractBase):
    offer_required: bool
    offer_types: list[str] = Field(default_factory=list)
    offer_positioning_pattern: str
    offer_timing_guidance: str
    urgency_policy: str
    price_display_policy: str
    commerce_constraints: list[str] = Field(default_factory=list)
    evidence_refs: list[PatternEvidenceRefV1] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    uncertainties: list[str] = Field(default_factory=list)


class CtaPatternV1(PatternKitContractBase):
    cta_required: bool
    cta_types: list[str] = Field(default_factory=list)
    modalities: list[str] = Field(default_factory=list)
    product_tag_expectation: str
    cta_timing_guidance: str
    cta_language_pattern: str
    cta_failure_modes: list[str] = Field(default_factory=list)
    evidence_refs: list[PatternEvidenceRefV1] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    uncertainties: list[str] = Field(default_factory=list)


class PodApplicabilityV1(PatternKitContractBase):
    recipient_types: list[str] = Field(default_factory=list)
    occasions: list[str] = Field(default_factory=list)
    personalization_requirements: list[str] = Field(default_factory=list)
    identity_cues: list[str] = Field(default_factory=list)
    emotional_payoff_patterns: list[str] = Field(default_factory=list)
    mockup_accuracy_risks: list[str] = Field(default_factory=list)


class DropshippingApplicabilityV1(PatternKitContractBase):
    visual_demo_required: bool
    trust_mechanisms: list[str] = Field(default_factory=list)
    shipping_promise_constraints: list[str] = Field(default_factory=list)
    quality_proof_requirements: list[str] = Field(default_factory=list)
    margin_or_offer_constraints: list[str] = Field(default_factory=list)
    claim_risks: list[str] = Field(default_factory=list)


class PatternApplicabilityV1(PatternKitContractBase):
    suitable_categories: list[str] = Field(default_factory=list)
    unsuitable_categories: list[str] = Field(default_factory=list)
    required_product_traits: list[str] = Field(default_factory=list)
    preferred_product_traits: list[str] = Field(default_factory=list)
    buyer_contexts: list[str] = Field(default_factory=list)
    markets: list[str] = Field(default_factory=list)
    platforms: list[str] = Field(default_factory=list)
    objectives: list[str] = Field(default_factory=list)
    fulfillment_constraints: list[str] = Field(default_factory=list)
    compliance_sensitivities: list[str] = Field(default_factory=list)
    pod_context: PodApplicabilityV1 | None = None
    dropshipping_context: DropshippingApplicabilityV1 | None = None


class PatternAdaptationInstructionV1(PatternKitContractBase):
    element_path: str = Field(min_length=1, max_length=500)
    instruction_type: Literal["keep", "change", "avoid"]
    instruction: str = Field(min_length=1, max_length=1000)
    rationale: str = Field(min_length=1, max_length=1000)
    evidence_refs: list[PatternEvidenceRefV1] = Field(default_factory=list)
    severity: Literal["hard", "high", "medium", "low"]


class PatternMetricSummaryV1(PatternKitContractBase):
    metric_name: str
    sample_size: int = Field(ge=0)
    median: float | None = None
    mean: float | None = None
    p25: float | None = None
    p75: float | None = None
    unit: str | None = None
    source: str


class PatternPerformanceSummaryV1(PatternKitContractBase):
    evidence_status: Literal["none", "directional", "supported"]
    asset_count: int = Field(ge=0)
    campaign_count: int = Field(ge=0)
    date_range_start: date | None = None
    date_range_end: date | None = None
    metrics: list[PatternMetricSummaryV1] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)
    confidence: PatternConfidenceV1

    @model_validator(mode="after")
    def validate_no_metrics_without_evidence(self) -> PatternPerformanceSummaryV1:
        if self.evidence_status == "none" and self.metrics:
            raise ValueError("metrics require directional or supported performance evidence")
        return self


class PatternKitSourceV1(PatternKitContractBase):
    creative_dna_version_ids: list[UUID]
    source_asset_count: int = Field(ge=0)
    source_category_count: int = Field(ge=0)
    extraction_mode: PatternExtractionModeV1


class PatternKitProvenanceV1(PatternKitContractBase):
    taxonomy_version: str
    model_run_id: UUID | None = None
    prompt_version: str


class PatternKitV1(PatternKitContractBase):
    schema_version: Literal["pattern_kit_v1"] = PATTERN_KIT_SCHEMA_VERSION
    id: UUID
    workspace_id: UUID
    version: int = Field(ge=1)
    name: str = Field(min_length=3, max_length=160)
    summary: str = Field(min_length=1, max_length=1000)
    kind: PatternKitKindV1
    scope: PatternKitScopeV1
    status: PatternKitStatusV1
    source: PatternKitSourceV1
    sequence: list[PatternSequenceBeatV1]
    opening: OpeningPatternV1
    product_reveal: ProductRevealPatternV1
    narrative: NarrativePatternV1
    demo: DemoPatternV1
    proof: ProofPatternV1
    creator: CreatorPatternV1
    editing: EditingPatternV1
    offer: OfferPatternV1
    cta: CtaPatternV1
    applicability: PatternApplicabilityV1
    adaptation_instructions: list[PatternAdaptationInstructionV1] = Field(default_factory=list)
    performance_summary: PatternPerformanceSummaryV1
    overall_confidence: PatternConfidenceV1
    uncertainties: list[str] = Field(default_factory=list)
    created_by: UUID
    created_at: datetime
    provenance: PatternKitProvenanceV1

    @model_validator(mode="after")
    def validate_sequence(self) -> PatternKitV1:
        beat_ids = [beat.beat_id for beat in self.sequence]
        if len(beat_ids) != len(set(beat_ids)):
            raise ValueError("duplicate beat_id values are invalid")
        orders = [beat.order for beat in self.sequence]
        if orders != list(range(1, len(orders) + 1)):
            raise ValueError("sequence order must start at 1 and be contiguous")
        for beat in self.sequence:
            if beat.requiredness == "required" and not beat.evidence_refs:
                raise ValueError("required sequence beats require evidence")
        return self
