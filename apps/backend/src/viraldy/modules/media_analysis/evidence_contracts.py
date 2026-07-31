from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from viraldy.modules.creative_domain.schema_versions import EVIDENCE_SCHEMA_VERSION


class EvidenceValueBaseV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["evidence_v1"] = EVIDENCE_SCHEMA_VERSION
    observation_id: str | None = None


class TranscriptSegmentEvidenceValueV1(EvidenceValueBaseV1):
    evidence_type: Literal["transcript_segment"] = "transcript_segment"
    text: str
    start_ms: int = Field(ge=0)
    end_ms: int = Field(ge=0)


class OnScreenTextEvidenceValueV1(EvidenceValueBaseV1):
    evidence_type: Literal["on_screen_text"] = "on_screen_text"
    text: str
    text_role: str | None = None
    start_ms: int = Field(ge=0)
    end_ms: int = Field(ge=0)
    frame_storage_key: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)


class HookSignalEvidenceValueV1(EvidenceValueBaseV1):
    evidence_type: Literal["hook_signal"] = "hook_signal"
    hook_type: str
    spoken_text: str | None = None
    overlay_text: str | None = None
    visual_description: str
    buyer_pain: str | None = None
    clarity: str
    confidence: float = Field(ge=0, le=1)
    start_ms: int = Field(ge=0)
    end_ms: int = Field(ge=0)
    frame_storage_keys: list[str] = Field(default_factory=list)


class ProductAppearanceEvidenceValueV1(EvidenceValueBaseV1):
    evidence_type: Literal["product_appearance"] = "product_appearance"
    visibility: str
    shot_type: str
    usage_visible: bool
    product_match_confidence: float | None = Field(default=None, ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    start_ms: int = Field(ge=0)
    end_ms: int = Field(ge=0)
    frame_storage_keys: list[str] = Field(default_factory=list)


class ProductVisibilitySummaryEvidenceValueV1(EvidenceValueBaseV1):
    evidence_type: Literal["product_visibility_summary"] = "product_visibility_summary"
    first_appearance_ms: int | None = Field(default=None, ge=0)
    total_visible_ms: int | None = Field(default=None, ge=0)
    screen_time_ratio: float | None = Field(default=None, ge=0, le=1)
    clear_close_up_present: bool
    usage_present: bool


class DemoStepEvidenceValueV1(EvidenceValueBaseV1):
    evidence_type: Literal["demo_step"] = "demo_step"
    step_index: int = Field(ge=0)
    action: str
    product_visible: bool
    mechanism_visible: bool
    result_visible: bool
    confidence: float = Field(ge=0, le=1)
    start_ms: int = Field(ge=0)
    end_ms: int = Field(ge=0)
    frame_storage_keys: list[str] = Field(default_factory=list)


class DemoSummaryEvidenceValueV1(EvidenceValueBaseV1):
    evidence_type: Literal["demo_summary"] = "demo_summary"
    detected: bool
    demo_type: str
    before_state_visible: bool
    after_state_visible: bool
    mechanism_clarity: str
    continuity: str
    confidence: float = Field(ge=0, le=1)


class ProofSignalEvidenceValueV1(EvidenceValueBaseV1):
    evidence_type: Literal["proof_signal"] = "proof_signal"
    proof_type: str
    description: str
    verifiability: str
    confidence: float = Field(ge=0, le=1)
    start_ms: int = Field(ge=0)
    end_ms: int = Field(ge=0)
    frame_storage_keys: list[str] = Field(default_factory=list)


class CtaSignalEvidenceValueV1(EvidenceValueBaseV1):
    evidence_type: Literal["cta_signal"] = "cta_signal"
    modality: str
    cta_type: str
    text: str | None = None
    spoken_text: str | None = None
    overlay_text: str | None = None
    product_tag_visible: bool
    confidence: float = Field(ge=0, le=1)
    start_ms: int = Field(ge=0)
    end_ms: int = Field(ge=0)
    frame_storage_keys: list[str] = Field(default_factory=list)


class OfferSignalEvidenceValueV1(EvidenceValueBaseV1):
    evidence_type: Literal["offer_signal"] = "offer_signal"
    offer_type: str
    text: str | None = None
    price_text: str | None = None
    discount_text: str | None = None
    urgency_present: bool = False
    confidence: float = Field(ge=0, le=1)
    start_ms: int = Field(ge=0)
    end_ms: int = Field(ge=0)
    frame_storage_keys: list[str] = Field(default_factory=list)


class CreatorSignalEvidenceValueV1(EvidenceValueBaseV1):
    evidence_type: Literal["creator_signal"] = "creator_signal"
    face_present: bool | None = None
    speaking_present: bool | None = None
    delivery_style: str
    creator_persona: str | None = None
    emotion: str
    pacing: str
    sales_language_intensity: str
    authenticity_cues: list[str]
    confidence: float = Field(ge=0, le=1)


class EditingSignalEvidenceValueV1(EvidenceValueBaseV1):
    evidence_type: Literal["editing_signal"] = "editing_signal"
    cut_count: int | None = Field(default=None, ge=0)
    average_shot_duration_ms: int | None = Field(default=None, ge=0)
    first_three_second_cut_count: int | None = Field(default=None, ge=0)
    pattern_interrupts: list[dict[str, int]] = Field(default_factory=list)
    dead_air_ranges: list[dict[str, int]] = Field(default_factory=list)
    caption_density: str
    visual_pacing: str
    transition_types: list[str]
    confidence: float = Field(ge=0, le=1)


class ClaimSignalEvidenceValueV1(EvidenceValueBaseV1):
    evidence_type: Literal["claim_signal"] = "claim_signal"
    text: str
    source: str
    category: str
    risk: str
    qualification_present: bool
    confidence: float = Field(ge=0, le=1)
    start_ms: int | None = Field(default=None, ge=0)
    end_ms: int | None = Field(default=None, ge=0)
    frame_storage_keys: list[str] = Field(default_factory=list)


class PlatformSignalEvidenceValueV1(EvidenceValueBaseV1):
    evidence_type: Literal["platform_signal"] = "platform_signal"
    aspect_ratio: str | None = None
    vertical: bool | None = None
    native_signals: list[str]
    shop_signals: list[str]
    caption_style: list[str]
    visual_safe_zone_risk: bool | None = None
    confidence: float = Field(ge=0, le=1)


EvidenceValueV1 = Annotated[
    TranscriptSegmentEvidenceValueV1
    | OnScreenTextEvidenceValueV1
    | HookSignalEvidenceValueV1
    | ProductAppearanceEvidenceValueV1
    | ProductVisibilitySummaryEvidenceValueV1
    | DemoStepEvidenceValueV1
    | DemoSummaryEvidenceValueV1
    | ProofSignalEvidenceValueV1
    | CtaSignalEvidenceValueV1
    | OfferSignalEvidenceValueV1
    | CreatorSignalEvidenceValueV1
    | EditingSignalEvidenceValueV1
    | ClaimSignalEvidenceValueV1
    | PlatformSignalEvidenceValueV1,
    Field(discriminator="evidence_type"),
]

EVIDENCE_VALUE_ADAPTER: TypeAdapter[EvidenceValueV1] = TypeAdapter(EvidenceValueV1)


def validate_evidence_value_v1(value: dict[str, object]) -> EvidenceValueV1:
    return EVIDENCE_VALUE_ADAPTER.validate_python(value)
