from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from viraldy.modules.creative_domain.schema_versions import CREATIVE_DNA_SCHEMA_VERSION

ObservedStatusV1 = Literal["observed", "inferred", "unknown", "not_present"]
ConfidenceLabelV1 = Literal["low", "medium", "high"]


class CreativeDnaContractBase(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ObservedValueV1(CreativeDnaContractBase):
    confidence: float = Field(ge=0, le=1)
    evidence_ids: list[UUID] = Field(default_factory=list)
    status: ObservedStatusV1


class ObservedStringV1(ObservedValueV1):
    value: str | None


class ObservedBoolV1(ObservedValueV1):
    value: bool | None


class ObservedIntV1(ObservedValueV1):
    value: int | None


class ObservedFloatV1(ObservedValueV1):
    value: float | None


class ObservedStringListV1(ObservedValueV1):
    value: list[str] | None


class TimeRangeValueV1(CreativeDnaContractBase):
    start_ms: int | None
    end_ms: int | None


class ProductAppearanceValueV1(TimeRangeValueV1):
    visibility: str | None
    shot_type: str | None


class DemoStepValueV1(TimeRangeValueV1):
    step_index: int | None
    action: str | None


class ObservedTimeRangeListV1(ObservedValueV1):
    value: list[TimeRangeValueV1] | None


class ObservedProductAppearanceListV1(ObservedValueV1):
    value: list[ProductAppearanceValueV1] | None


class ObservedDemoStepListV1(ObservedValueV1):
    value: list[DemoStepValueV1] | None


class OpeningDnaV1(CreativeDnaContractBase):
    primary_hook_type: ObservedStringV1
    hook_text: ObservedStringV1
    opening_visual: ObservedStringV1
    buyer_pain: ObservedStringV1
    face_present: ObservedBoolV1
    product_present: ObservedBoolV1
    first_three_second_structure: ObservedStringV1
    pattern_interrupts: ObservedTimeRangeListV1


class ProductDnaV1(CreativeDnaContractBase):
    first_appearance_ms: ObservedIntV1
    total_visible_ms: ObservedIntV1
    screen_time_ratio: ObservedFloatV1
    close_up_present: ObservedBoolV1
    hero_shot_present: ObservedBoolV1
    usage_present: ObservedBoolV1
    product_match: ObservedFloatV1
    appearance_sequence: ObservedProductAppearanceListV1


class NarrativeDnaV1(CreativeDnaContractBase):
    structure: ObservedStringV1
    angle: ObservedStringV1
    buyer_pain: ObservedStringV1
    desired_outcome: ObservedStringV1
    emotional_drivers: ObservedStringListV1
    awareness_stage: ObservedStringV1


class DemoDnaV1(CreativeDnaContractBase):
    detected: ObservedBoolV1
    demo_type: ObservedStringV1
    mechanism_clarity: ObservedStringV1
    before_state_visible: ObservedBoolV1
    after_state_visible: ObservedBoolV1
    result_clarity: ObservedStringV1
    steps: ObservedDemoStepListV1


class ProofDnaV1(CreativeDnaContractBase):
    proof_types: ObservedStringListV1
    strongest_proof: ObservedStringV1
    verifiability: ObservedStringV1
    proof_strength_label: ObservedStringV1


class CreatorDnaV1(CreativeDnaContractBase):
    face_present: ObservedBoolV1
    delivery_style: ObservedStringV1
    creator_persona: ObservedStringV1
    emotion: ObservedStringV1
    pacing: ObservedStringV1
    authenticity_cues: ObservedStringListV1
    sales_language_intensity: ObservedStringV1


class EditingDnaV1(CreativeDnaContractBase):
    cut_count: ObservedIntV1
    average_shot_duration_ms: ObservedIntV1
    first_three_second_cut_count: ObservedIntV1
    pacing: ObservedStringV1
    caption_density: ObservedStringV1
    pattern_interrupts: ObservedTimeRangeListV1
    dead_air_ranges: ObservedTimeRangeListV1
    dead_air_present: ObservedBoolV1
    transition_types: ObservedStringListV1


class OfferDnaV1(CreativeDnaContractBase):
    present: ObservedBoolV1
    offer_types: ObservedStringListV1
    price_text: ObservedStringV1
    discount_text: ObservedStringV1
    urgency_present: ObservedBoolV1


class CtaDnaV1(CreativeDnaContractBase):
    present: ObservedBoolV1
    cta_types: ObservedStringListV1
    first_appearance_ms: ObservedIntV1
    spoken_text: ObservedStringV1
    overlay_text: ObservedStringV1
    product_tag_visible: ObservedBoolV1


class PlatformDnaV1(CreativeDnaContractBase):
    vertical: ObservedBoolV1
    native_signals: ObservedStringListV1
    shop_signals: ObservedStringListV1
    safe_zone_risk: ObservedBoolV1
    format: ObservedStringV1


class ClaimDnaV1(CreativeDnaContractBase):
    text: str
    risk: str
    category: str
    qualification_present: bool
    evidence_ids: list[UUID]


class RiskDnaV1(CreativeDnaContractBase):
    code: str
    severity: Literal["low", "medium", "high", "critical"]
    message: str
    evidence_ids: list[UUID]


class ReusableMechanismV1(CreativeDnaContractBase):
    mechanism_type: str
    description: str
    evidence_ids: list[UUID]


class CreativeDnaCompletenessV1(CreativeDnaContractBase):
    opening: bool
    product: bool
    demo: bool
    proof: bool
    cta: bool
    creator: bool
    editing: bool
    platform: bool


class CreativeDnaV1(CreativeDnaContractBase):
    schema_version: Literal["creative_dna_v1"] = CREATIVE_DNA_SCHEMA_VERSION
    opening: OpeningDnaV1
    product: ProductDnaV1
    narrative: NarrativeDnaV1
    demo: DemoDnaV1
    proof: ProofDnaV1
    creator: CreatorDnaV1
    editing: EditingDnaV1
    offer: OfferDnaV1
    cta: CtaDnaV1
    platform: PlatformDnaV1
    claims: list[ClaimDnaV1] = Field(default_factory=list)
    risks: list[RiskDnaV1] = Field(default_factory=list)
    reusable_mechanisms: list[ReusableMechanismV1] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    completeness: CreativeDnaCompletenessV1
    overall_confidence: ConfidenceLabelV1
