from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from viraldy.modules.creative_domain.schema_versions import VIRAL_KIT_SCHEMA_VERSION
from viraldy.modules.pattern_kits.contracts import PatternEvidenceRefV1
from viraldy.modules.products.contracts import ProductContextV1

ViralKitStatusV1 = Literal[
    "draft",
    "generating",
    "ready_for_review",
    "concept_selected",
    "production_ready",
    "testing",
    "completed",
    "archived",
    "failed",
]
ViralKitObjectiveV1 = Literal[
    "tiktok_shop_affiliate_test",
    "tiktok_shop_organic_test",
    "small_paid_test",
    "spark_candidate",
    "ugc_paid_asset",
    "pod_gift_campaign",
    "dropshipping_demo_test",
    "creative_refresh",
]
ViralKitPlatformV1 = Literal["tiktok_shop", "tiktok_organic", "tiktok_paid"]
ViralKitConfidenceV1 = Literal["low", "medium", "high"]
PatternApplicabilityStatusV1 = Literal["matched", "partial", "override", "rejected"]
AdaptationDecisionTypeV1 = Literal["keep", "change", "avoid"]
DecisionSeverityV1 = Literal["hard", "high", "medium", "low"]
DiversityAxisV1 = Literal[
    "buyer_persona",
    "buyer_pain",
    "awareness_stage",
    "hook_mechanism",
    "creator_persona",
    "delivery_style",
    "narrative_structure",
    "demo_mechanism",
    "proof_mechanism",
    "offer_framing",
    "cta_strategy",
]
ConceptActionV1 = Literal["selected", "rejected", "restored", "campaign_pack_created"]


class ViralKitContractBase(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CreatorConstraintsV1(ViralKitContractBase):
    allowed_personas: list[str] = Field(default_factory=list)
    disallowed_personas: list[str] = Field(default_factory=list)
    delivery_style_preferences: list[str] = Field(default_factory=list)


class ProductionConstraintsV1(ViralKitContractBase):
    max_duration_ms: int | None = Field(default=None, ge=1000)
    required_aspect_ratio: Literal["9:16", "1:1", "16:9"] = "9:16"
    raw_footage_required: bool = False
    concept_preview_requested: bool = False


class CommercialConstraintsV1(ViralKitContractBase):
    offer_required: bool = False
    product_tag_required: bool = False
    shipping_claim_policy: Literal[
        "use_product_context_only",
        "no_shipping_claims",
        "seller_confirmed_only",
    ] = "use_product_context_only"


class GovernanceConstraintsV1(ViralKitContractBase):
    prohibited_claims: list[str] = Field(default_factory=list)
    required_disclosures: list[str] = Field(default_factory=list)
    prohibited_content: list[str] = Field(default_factory=list)
    rights_notes: list[str] = Field(default_factory=list)


class ViralKitConstraintsV1(ViralKitContractBase):
    creator: CreatorConstraintsV1 = Field(default_factory=CreatorConstraintsV1)
    production: ProductionConstraintsV1 = Field(default_factory=ProductionConstraintsV1)
    commercial: CommercialConstraintsV1 = Field(default_factory=CommercialConstraintsV1)
    governance: GovernanceConstraintsV1 = Field(default_factory=GovernanceConstraintsV1)


class ViralKitProductSnapshotV1(ViralKitContractBase):
    product_id: UUID
    product_context_schema_version: str
    product_context_version: int = Field(ge=1)
    snapshot_json: ProductContextV1
    captured_at: datetime


class BuyerContextV1(ViralKitContractBase):
    persona_id: str | None = None
    persona_label: str
    pain_points: list[str] = Field(default_factory=list)
    desired_outcomes: list[str] = Field(default_factory=list)
    awareness_stage: str = "unknown"


class ViralKitPatternMatchV1(ViralKitContractBase):
    pattern_kit_version_id: UUID
    match_score: float = Field(ge=0, le=1)
    applicability_status: PatternApplicabilityStatusV1
    matched_product_traits: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    selection_reason: str = Field(min_length=1, max_length=1000)
    evidence_summary: list[str] = Field(default_factory=list)


class AdaptationDecisionV1(ViralKitContractBase):
    element_path: str = Field(min_length=1, max_length=500)
    decision: AdaptationDecisionTypeV1
    source_pattern_kit_version_ids: list[UUID] = Field(default_factory=list)
    product_context_paths: list[str] = Field(default_factory=list)
    rationale: str = Field(min_length=1, max_length=1000)
    severity: DecisionSeverityV1
    evidence_refs: list[PatternEvidenceRefV1] = Field(default_factory=list)


class ViralKitAdaptationPlanV1(ViralKitContractBase):
    keep: list[AdaptationDecisionV1] = Field(default_factory=list)
    change: list[AdaptationDecisionV1] = Field(default_factory=list)
    avoid: list[AdaptationDecisionV1] = Field(default_factory=list)


class ViralKitHookV1(ViralKitContractBase):
    hook_type: str = Field(min_length=1, max_length=120)
    spoken_text: str | None = Field(default=None, max_length=240)
    overlay_text: str | None = Field(default=None, max_length=160)
    opening_visual: str = Field(min_length=1, max_length=500)
    target_time_ms: int = Field(ge=0)
    product_present: bool
    buyer_pain: str = Field(min_length=1, max_length=500)


class ViralKitRequirementDraftV1(ViralKitContractBase):
    id: str = Field(min_length=1, max_length=120)
    requirement_type: str = Field(min_length=1, max_length=100)
    instruction: str = Field(min_length=1, max_length=500)
    required: bool
    severity: DecisionSeverityV1
    expected_before_ms: int | None = Field(default=None, ge=0)
    matcher_hint: str = Field(min_length=1, max_length=120)


class ViralKitRiskV1(ViralKitContractBase):
    code: str = Field(min_length=1, max_length=120)
    severity: DecisionSeverityV1
    message: str = Field(min_length=1, max_length=500)
    source: str = Field(min_length=1, max_length=120)
    mitigation: str = Field(min_length=1, max_length=500)


class ViralKitConceptV1(ViralKitContractBase):
    id: str = Field(min_length=1, max_length=120)
    name: str = Field(min_length=1, max_length=160)
    strategic_axis: str = Field(min_length=1, max_length=160)
    diversity_axes: list[DiversityAxisV1] = Field(min_length=1)
    buyer_persona_id: str
    buyer_persona_label: str
    buyer_pain: str
    desired_outcome: str
    awareness_stage: str | None = None
    creative_angle: str
    hook: ViralKitHookV1
    opening_visual: str
    narrative_structure: str
    creator_persona: str
    delivery_style: str
    demo_mechanism: str
    proof_mechanism: str
    offer_framing: str | None = None
    cta_strategy: str
    must_show: list[ViralKitRequirementDraftV1]
    overlays: list[str] = Field(default_factory=list)
    spoken_lines: list[str] = Field(default_factory=list)
    claims_to_avoid: list[str] = Field(default_factory=list)
    required_disclosures: list[str] = Field(default_factory=list)
    test_hypothesis: str
    expected_learning: str
    feasibility: Literal["high", "medium", "low"]
    risks: list[ViralKitRiskV1] = Field(default_factory=list)
    source_pattern_kit_version_ids: list[UUID] = Field(min_length=1)
    evidence_refs: list[PatternEvidenceRefV1] = Field(default_factory=list)
    confidence: ViralKitConfidenceV1

    @model_validator(mode="after")
    def validate_buyer_creator_separation(self) -> ViralKitConceptV1:
        buyer = self.buyer_persona_label.strip().lower()
        creator = self.creator_persona.strip().lower()
        if buyer and buyer == creator:
            raise ValueError("buyer persona must remain separate from creator persona")
        return self


class ViralKitTestCellV1(ViralKitContractBase):
    concept_id: str
    hypothesis: str
    changed_axes: list[DiversityAxisV1]
    held_constant: list[str] = Field(default_factory=list)
    minimum_execution_requirements: list[str] = Field(default_factory=list)
    metrics_to_observe: list[str] = Field(default_factory=list)


class ViralKitDecisionCriterionV1(ViralKitContractBase):
    criterion: str
    signal_type: Literal["structural", "behavioral", "commercial"]
    comparison: str
    caveat: str


class ViralKitTestMatrixV1(ViralKitContractBase):
    primary_hypothesis: str
    concepts: list[ViralKitTestCellV1]
    controlled_variables: list[str] = Field(default_factory=list)
    intentionally_changed_variables: list[str] = Field(default_factory=list)
    recommended_test_order: list[str] = Field(default_factory=list)
    decision_criteria: list[ViralKitDecisionCriterionV1] = Field(default_factory=list)


class ViralKitCampaignPackLinkV1(ViralKitContractBase):
    concept_id: str
    campaign_pack_id: UUID
    campaign_pack_version_id: UUID
    compiled_requirements_schema_version: str
    created_at: datetime


class ViralKitPreflightRequirementLinkV1(ViralKitContractBase):
    concept_id: str
    expected_requirement_classes: list[str] = Field(default_factory=list)


class GenerationSceneV1(ViralKitContractBase):
    scene_id: str
    order: int = Field(ge=1)
    start_ms: int | None = Field(default=None, ge=0)
    end_ms: int | None = Field(default=None, ge=0)
    purpose: str
    visual_prompt: str
    camera_direction: str
    product_visibility: str
    creator_direction: str
    overlay_text: str | None = None
    spoken_direction: str | None = None
    reference_asset_ids: list[UUID] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_timing(self) -> GenerationSceneV1:
        if self.start_ms is not None and self.end_ms is not None and self.end_ms < self.start_ms:
            raise ValueError("scene end_ms must be greater than or equal to start_ms")
        return self


class GenerationBriefV1(ViralKitContractBase):
    concept_id: str
    purpose: Literal["storyboard_preview", "concept_video_preview"]
    aspect_ratio: Literal["9:16", "1:1", "16:9"]
    duration_ms: int | None = Field(default=None, ge=1000)
    product_asset_ids: list[UUID] = Field(default_factory=list)
    reference_asset_ids: list[UUID] = Field(default_factory=list)
    scenes: list[GenerationSceneV1]
    consistency_constraints: list[str] = Field(default_factory=list)
    negative_constraints: list[str] = Field(default_factory=list)
    overlay_instructions: list[str] = Field(default_factory=list)
    audio_direction: str | None = None
    claim_guardrails: list[str] = Field(default_factory=list)
    rights_confirmation_required: bool


class ViralKitProvenanceV1(ViralKitContractBase):
    pattern_kit_version_ids: list[UUID]
    adaptation_schema_version: str
    model_run_id: UUID | None = None
    prompt_version: str


class ViralKitV1(ViralKitContractBase):
    schema_version: Literal["viral_kit_v1"] = VIRAL_KIT_SCHEMA_VERSION
    id: UUID
    workspace_id: UUID
    version: int = Field(ge=1)
    status: ViralKitStatusV1
    name: str = Field(min_length=1, max_length=200)
    product: ViralKitProductSnapshotV1
    objective: ViralKitObjectiveV1
    platform: ViralKitPlatformV1
    target_market: str = Field(min_length=1, max_length=100)
    buyer_context: BuyerContextV1
    constraints: ViralKitConstraintsV1
    pattern_matches: list[ViralKitPatternMatchV1]
    adaptation_plan: ViralKitAdaptationPlanV1
    concepts: list[ViralKitConceptV1]
    test_matrix: ViralKitTestMatrixV1
    selected_concept_id: str | None = None
    campaign_pack_links: list[ViralKitCampaignPackLinkV1] = Field(default_factory=list)
    preflight_requirement_links: list[ViralKitPreflightRequirementLinkV1] = Field(
        default_factory=list
    )
    generation_briefs: list[GenerationBriefV1] = Field(default_factory=list)
    risks: list[ViralKitRiskV1] = Field(default_factory=list)
    overall_confidence: ViralKitConfidenceV1
    uncertainties: list[str] = Field(default_factory=list)
    provenance: ViralKitProvenanceV1
    created_by: UUID
    created_at: datetime

    @model_validator(mode="after")
    def validate_concepts(self) -> ViralKitV1:
        if len(self.concepts) != 3:
            raise ValueError("ViralKitV1 requires exactly three concepts")
        concept_ids = [concept.id for concept in self.concepts]
        if len(concept_ids) != len(set(concept_ids)):
            raise ValueError("ViralKit concept IDs must be unique")
        if self.selected_concept_id is not None and self.selected_concept_id not in concept_ids:
            raise ValueError("selected_concept_id must reference an existing concept")
        for left_index, left in enumerate(self.concepts):
            for right in self.concepts[left_index + 1 :]:
                if _concept_difference_count(left, right) < 2:
                    raise ValueError("ViralKit concepts must differ on at least two axes")
        if not any(
            "hook_mechanism" in concept.diversity_axes for concept in self.concepts
        ):
            raise ValueError("at least one concept must test a different hook mechanism")
        if not any(
            {"demo_mechanism", "proof_mechanism", "narrative_structure"}.intersection(
                concept.diversity_axes
            )
            for concept in self.concepts
        ):
            raise ValueError(
                "at least one concept must vary demo, proof, or narrative mechanism"
            )
        return self


def _concept_difference_count(left: ViralKitConceptV1, right: ViralKitConceptV1) -> int:
    comparisons = [
        left.buyer_persona_id != right.buyer_persona_id,
        left.buyer_pain != right.buyer_pain,
        left.awareness_stage != right.awareness_stage,
        left.hook.hook_type != right.hook.hook_type,
        left.creator_persona != right.creator_persona,
        left.delivery_style != right.delivery_style,
        left.narrative_structure != right.narrative_structure,
        left.demo_mechanism != right.demo_mechanism,
        left.proof_mechanism != right.proof_mechanism,
        left.offer_framing != right.offer_framing,
        left.cta_strategy != right.cta_strategy,
    ]
    return sum(1 for item in comparisons if item)
