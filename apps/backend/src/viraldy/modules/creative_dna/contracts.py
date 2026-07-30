from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from viraldy.modules.creative_domain.schema_versions import CREATIVE_DNA_SCHEMA_VERSION

ObservedStatusV1 = Literal["observed", "inferred", "unknown", "not_present"]
ConfidenceLabelV1 = Literal["low", "medium", "high"]


class CreativeDnaContractBase(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ObservedValueV1(CreativeDnaContractBase):
    value: Any
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


class ObservedObjectListV1(ObservedValueV1):
    value: list[dict[str, object]] | None


class OpeningDnaV1(CreativeDnaContractBase):
    primary_hook_type: ObservedStringV1
    hook_text: ObservedStringV1
    opening_visual: ObservedStringV1
    buyer_pain: ObservedStringV1
    face_present: ObservedBoolV1
    product_present: ObservedBoolV1
    first_three_second_structure: ObservedStringV1
    pattern_interrupts: ObservedObjectListV1


class ProductDnaV1(CreativeDnaContractBase):
    first_appearance_ms: ObservedIntV1
    total_visible_ms: ObservedIntV1
    screen_time_ratio: ObservedFloatV1
    close_up_present: ObservedBoolV1
    hero_shot_present: ObservedBoolV1
    usage_present: ObservedBoolV1
    product_match: ObservedFloatV1
    appearance_sequence: ObservedObjectListV1


class NarrativeDnaV1(CreativeDnaContractBase):
    structure: ObservedValueV1
    angle: ObservedValueV1
    buyer_pain: ObservedValueV1
    desired_outcome: ObservedValueV1
    emotional_drivers: ObservedValueV1
    awareness_stage: ObservedValueV1


class DemoDnaV1(CreativeDnaContractBase):
    detected: ObservedBoolV1
    demo_type: ObservedValueV1
    mechanism_clarity: ObservedValueV1
    before_state_visible: ObservedValueV1
    after_state_visible: ObservedValueV1
    result_clarity: ObservedValueV1
    steps: ObservedValueV1


class ProofDnaV1(CreativeDnaContractBase):
    proof_types: ObservedValueV1
    strongest_proof: ObservedValueV1
    verifiability: ObservedValueV1
    proof_strength_label: ObservedValueV1


class CreatorDnaV1(CreativeDnaContractBase):
    face_present: ObservedBoolV1
    delivery_style: ObservedValueV1
    creator_persona: ObservedValueV1
    emotion: ObservedValueV1
    pacing: ObservedValueV1
    authenticity_cues: ObservedValueV1
    sales_language_intensity: ObservedValueV1


class EditingDnaV1(CreativeDnaContractBase):
    cut_count: ObservedIntV1
    average_shot_duration_ms: ObservedIntV1
    first_three_second_cut_count: ObservedIntV1
    pacing: ObservedValueV1
    caption_density: ObservedValueV1
    pattern_interrupts: ObservedObjectListV1
    dead_air_ranges: ObservedObjectListV1
    dead_air_present: ObservedBoolV1
    transition_types: ObservedValueV1


class OfferDnaV1(CreativeDnaContractBase):
    present: ObservedBoolV1
    offer_types: ObservedValueV1
    price_text: ObservedValueV1
    discount_text: ObservedValueV1
    urgency_present: ObservedBoolV1


class CtaDnaV1(CreativeDnaContractBase):
    present: ObservedBoolV1
    cta_types: ObservedValueV1
    first_appearance_ms: ObservedIntV1
    spoken_text: ObservedStringV1
    overlay_text: ObservedStringV1
    product_tag_visible: ObservedBoolV1


class PlatformDnaV1(CreativeDnaContractBase):
    vertical: ObservedValueV1
    native_signals: ObservedValueV1
    shop_signals: ObservedValueV1
    safe_zone_risk: ObservedValueV1
    format: ObservedValueV1


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
    completeness: dict[str, bool]
    overall_confidence: ConfidenceLabelV1
