from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from viraldy.modules.creative_domain.schema_versions import MEDIA_OBSERVATION_SCHEMA_VERSION


class MediaObservationBase(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TimeRangeV1(MediaObservationBase):
    start_ms: int = Field(ge=0)
    end_ms: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_order(self) -> TimeRangeV1:
        if self.end_ms < self.start_ms:
            raise ValueError("end_ms must be greater than or equal to start_ms")
        return self


class ObservationRefV1(MediaObservationBase):
    observation_id: str = Field(min_length=1, max_length=120)
    confidence: float = Field(ge=0, le=1)
    frame_storage_keys: list[str] = Field(default_factory=list)


class HookObservationV1(ObservationRefV1):
    time_range: TimeRangeV1
    hook_type: Literal[
        "problem_first",
        "result_first",
        "curiosity",
        "question",
        "contrarian",
        "testimonial",
        "offer_first",
        "product_first",
        "pattern_interrupt",
        "story_open",
        "unknown",
    ] = "unknown"
    spoken_text: str | None = None
    overlay_text: str | None = None
    visual_description: str = "unknown"
    buyer_pain: str | None = None
    clarity: Literal["clear", "partial", "unclear", "unknown"] = "unknown"
    face_present: bool | None = None
    product_present: bool | None = None


class ProductAppearanceV1(ObservationRefV1):
    time_range: TimeRangeV1
    visibility: Literal["clear", "partial", "obstructed", "uncertain"] = "uncertain"
    shot_type: Literal[
        "hero",
        "close_up",
        "medium",
        "wide",
        "in_use",
        "packaging",
        "result_only",
        "unknown",
    ] = "unknown"
    usage_visible: bool = False
    product_match_confidence: float | None = Field(default=None, ge=0, le=1)


class ProductVisibilitySummaryV1(MediaObservationBase):
    first_appearance_ms: int | None = Field(default=None, ge=0)
    total_visible_ms: int | None = Field(default=None, ge=0)
    screen_time_ratio: float | None = Field(default=None, ge=0, le=1)
    clear_close_up_present: bool = False
    usage_present: bool = False


class DemoStepV1(ObservationRefV1):
    step_index: int = Field(ge=0)
    time_range: TimeRangeV1
    action: str = Field(min_length=1)
    product_visible: bool = False
    mechanism_visible: bool = False
    result_visible: bool = False


class DemoObservationV1(MediaObservationBase):
    detected: bool = False
    demo_type: Literal[
        "before_after",
        "tutorial",
        "installation",
        "usage",
        "comparison",
        "unboxing",
        "result_reveal",
        "none",
        "unknown",
    ] = "unknown"
    steps: list[DemoStepV1] = Field(default_factory=list)
    before_state_visible: bool = False
    after_state_visible: bool = False
    mechanism_clarity: Literal["clear", "partial", "unclear", "unknown"] = "unknown"
    continuity: Literal["continuous", "edited_but_clear", "fragmented", "unknown"] = "unknown"
    confidence: float = Field(default=0, ge=0, le=1)

    @model_validator(mode="after")
    def validate_demo_state(self) -> DemoObservationV1:
        if not self.detected and self.steps:
            raise ValueError("demo.detected=false requires an empty steps list")
        if not self.detected and self.demo_type not in {"none", "unknown"}:
            raise ValueError("demo.detected=false cannot carry a positive demo_type")
        return self


class ProofMomentV1(ObservationRefV1):
    time_range: TimeRangeV1
    proof_type: Literal[
        "visual_result",
        "before_after",
        "demonstration",
        "testimonial",
        "rating",
        "review",
        "comment_social_proof",
        "measurement",
        "comparison",
        "authority",
        "none",
        "unknown",
    ] = "unknown"
    description: str = "unknown"
    verifiability: Literal[
        "observable",
        "partially_observable",
        "not_observable",
        "unknown",
    ] = "unknown"


class CtaObservationV1(ObservationRefV1):
    time_range: TimeRangeV1
    modality: Literal["spoken", "overlay", "visual", "mixed"] = "mixed"
    cta_type: Literal[
        "product_tag",
        "shop_now",
        "link_in_shop",
        "learn_more",
        "comment",
        "follow",
        "generic",
        "unknown",
    ] = "unknown"
    text: str | None = None
    product_tag_visible: bool = False


class OfferObservationV1(ObservationRefV1):
    time_range: TimeRangeV1
    offer_type: Literal[
        "price",
        "discount",
        "bundle",
        "free_shipping",
        "limited_time",
        "value_statement",
        "none",
        "unknown",
    ] = "unknown"
    text: str | None = None
    price_text: str | None = None


class CreatorObservationV1(MediaObservationBase):
    face_present: bool | None = None
    speaking_present: bool | None = None
    delivery_style: Literal[
        "authentic_review",
        "testimonial",
        "tutorial",
        "demonstration",
        "storytelling",
        "sales_pitch",
        "voiceover",
        "faceless_demo",
        "unknown",
    ] = "unknown"
    creator_persona: str | None = None
    emotion: Literal[
        "neutral",
        "excited",
        "surprised",
        "frustrated",
        "relieved",
        "confident",
        "unknown",
    ] = "unknown"
    pacing: Literal["slow", "moderate", "fast", "mixed", "unknown"] = "unknown"
    sales_language_intensity: Literal["low", "medium", "high", "unknown"] = "unknown"
    authenticity_cues: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0, ge=0, le=1)


class EditingObservationV1(MediaObservationBase):
    cut_count: int | None = Field(default=None, ge=0)
    average_shot_duration_ms: int | None = Field(default=None, ge=0)
    first_three_second_cut_count: int | None = Field(default=None, ge=0)
    pattern_interrupts: list[TimeRangeV1] = Field(default_factory=list)
    dead_air_ranges: list[TimeRangeV1] = Field(default_factory=list)
    caption_density: Literal["none", "low", "medium", "high", "unknown"] = "unknown"
    visual_pacing: Literal["slow", "moderate", "fast", "mixed", "unknown"] = "unknown"
    transition_types: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0, ge=0, le=1)


class ClaimCandidateV1(ObservationRefV1):
    time_range: TimeRangeV1 | None = None
    text: str = Field(min_length=1)
    source: Literal["spoken", "overlay", "caption", "visual_inference"] = "spoken"
    category: Literal[
        "performance",
        "health",
        "safety",
        "financial",
        "shipping",
        "scarcity",
        "superlative",
        "guarantee",
        "comparison",
        "other",
        "unknown",
    ] = "unknown"
    risk: Literal["none", "low", "medium", "high", "critical", "unknown"] = "unknown"
    qualification_present: bool = False


class PlatformObservationV1(MediaObservationBase):
    aspect_ratio: str | None = None
    vertical: bool | None = None
    native_signals: list[str] = Field(default_factory=list)
    shop_signals: list[str] = Field(default_factory=list)
    caption_style: list[str] = Field(default_factory=list)
    visual_safe_zone_risk: bool | None = None
    confidence: float = Field(default=0, ge=0, le=1)


class MediaObservationBundleV1(MediaObservationBase):
    schema_version: Literal["media_observation_v1"] = MEDIA_OBSERVATION_SCHEMA_VERSION
    duration_ms: int = Field(ge=0)
    hooks: list[HookObservationV1] = Field(default_factory=list)
    product_appearances: list[ProductAppearanceV1] = Field(default_factory=list)
    product_visibility: ProductVisibilitySummaryV1 = Field(
        default_factory=ProductVisibilitySummaryV1
    )
    demo: DemoObservationV1 = Field(default_factory=DemoObservationV1)
    proof_moments: list[ProofMomentV1] = Field(default_factory=list)
    ctas: list[CtaObservationV1] = Field(default_factory=list)
    offers: list[OfferObservationV1] = Field(default_factory=list)
    creator: CreatorObservationV1 = Field(default_factory=CreatorObservationV1)
    editing: EditingObservationV1 = Field(default_factory=EditingObservationV1)
    claims: list[ClaimCandidateV1] = Field(default_factory=list)
    platform: PlatformObservationV1 = Field(default_factory=PlatformObservationV1)
    uncertainties: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_bundle(self) -> MediaObservationBundleV1:
        self._validate_ranges_within_duration()
        self._validate_unique_observation_ids()
        self._validate_product_visibility_summary()
        return self

    def _validate_ranges_within_duration(self) -> None:
        for time_range in _all_time_ranges(self):
            if time_range.end_ms > self.duration_ms:
                raise ValueError("observation time ranges must be within media duration")

    def _validate_unique_observation_ids(self) -> None:
        ids = _all_observation_ids(self)
        if len(ids) != len(set(ids)):
            raise ValueError("observation IDs must be unique within a bundle")

    def _validate_product_visibility_summary(self) -> None:
        starts = [item.time_range.start_ms for item in self.product_appearances]
        first = self.product_visibility.first_appearance_ms
        if first is None:
            if starts:
                raise ValueError("product first appearance is required when appearances exist")
            return
        if not starts:
            raise ValueError("product first appearance requires at least one appearance")
        if first != min(starts):
            raise ValueError("product first appearance must match the earliest appearance")
        if first > self.duration_ms:
            raise ValueError("product first appearance must be within media duration")


def media_observation_bundle_to_json(bundle: MediaObservationBundleV1) -> dict[str, object]:
    return bundle.model_dump(mode="json")


def _all_time_ranges(bundle: MediaObservationBundleV1) -> list[TimeRangeV1]:
    ranges: list[TimeRangeV1] = []
    ranges.extend(item.time_range for item in bundle.hooks)
    ranges.extend(item.time_range for item in bundle.product_appearances)
    ranges.extend(item.time_range for item in bundle.demo.steps)
    ranges.extend(item.time_range for item in bundle.proof_moments)
    ranges.extend(item.time_range for item in bundle.ctas)
    ranges.extend(item.time_range for item in bundle.offers)
    ranges.extend(item.time_range for item in bundle.claims if item.time_range is not None)
    ranges.extend(bundle.editing.pattern_interrupts)
    ranges.extend(bundle.editing.dead_air_ranges)
    return ranges


def _all_observation_ids(bundle: MediaObservationBundleV1) -> list[str]:
    ids: list[str] = []
    ids.extend(item.observation_id for item in bundle.hooks)
    ids.extend(item.observation_id for item in bundle.product_appearances)
    ids.extend(item.observation_id for item in bundle.demo.steps)
    ids.extend(item.observation_id for item in bundle.proof_moments)
    ids.extend(item.observation_id for item in bundle.ctas)
    ids.extend(item.observation_id for item in bundle.offers)
    ids.extend(item.observation_id for item in bundle.claims)
    return ids
