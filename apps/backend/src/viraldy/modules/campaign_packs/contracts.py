from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from viraldy.modules.creative_domain.schema_versions import CAMPAIGN_PACK_SCHEMA_VERSION
from viraldy.modules.products.contracts import ProductContextV1


class CampaignPackContractBase(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CampaignObjectiveV1(CampaignPackContractBase):
    objective_type: str
    primary_action: str
    channel: Literal["tiktok_shop", "tiktok_organic", "tiktok_paid", "unknown"] = "unknown"


class CampaignAudienceV1(CampaignPackContractBase):
    persona_id: str | None = None
    persona_label: str
    pain_points: list[str] = Field(default_factory=list)
    desired_outcomes: list[str] = Field(default_factory=list)
    objections: list[str] = Field(default_factory=list)
    awareness_stage: str = "unknown"


class CampaignAngleV1(CampaignPackContractBase):
    name: str
    promise: str
    mechanism: str
    emotional_driver: str
    differentiation: str | None = None


class CreatorDirectionV1(CampaignPackContractBase):
    persona: str
    delivery_style: str
    tone: list[str] = Field(default_factory=list)
    avoid_tones: list[str] = Field(default_factory=list)
    authenticity_notes: list[str] = Field(default_factory=list)


class HookOptionV1(CampaignPackContractBase):
    id: str
    spoken_text: str | None = None
    overlay_text: str | None = None
    opening_visual: str
    hook_type: str
    target_time_ms: int = Field(ge=0)
    mandatory: bool = False


class ScriptBeatV1(CampaignPackContractBase):
    id: str
    sequence: int
    beat_type: str
    instruction: str
    expected_start_ms: int | None = Field(default=None, ge=0)
    expected_end_ms: int | None = Field(default=None, ge=0)
    required: bool = False


class StoryboardSceneV1(CampaignPackContractBase):
    id: str
    sequence: int
    instruction: str
    shot_type: str
    product_visibility_required: bool = False
    overlay_text: str | None = None
    spoken_direction: str | None = None
    required: bool = False


class MustShowRequirementV1(CampaignPackContractBase):
    id: str
    requirement_type: Literal[
        "product",
        "demo",
        "proof",
        "offer",
        "cta",
        "overlay",
        "creator",
        "scene",
        "claim",
    ]
    description: str
    severity: Literal["hard", "high", "medium", "low"]
    expected_before_ms: int | None = Field(default=None, ge=0)
    source_path: str


class CtaDirectionV1(CampaignPackContractBase):
    spoken: str | None = None
    overlay: str | None = None
    cta_type: str
    product_tag_required: bool = False
    required_before_ms: int | None = Field(default=None, ge=0)


class ClaimGuardrailsV1(CampaignPackContractBase):
    allowed: list[str] = Field(default_factory=list)
    allowed_with_qualification: list[str] = Field(default_factory=list)
    prohibited: list[str] = Field(default_factory=list)
    required_disclosures: list[str] = Field(default_factory=list)


class RightsNoteV1(CampaignPackContractBase):
    raw_footage_requested: bool = False
    editing_permission_requested: bool = False
    spark_authorization_requested: bool = False
    note: str


class CampaignPackBriefV1(CampaignPackContractBase):
    schema_version: Literal["campaign_pack_brief_v1"] = CAMPAIGN_PACK_SCHEMA_VERSION
    product_snapshot: ProductContextV1
    objective: CampaignObjectiveV1
    audience: CampaignAudienceV1
    angle: CampaignAngleV1
    creator_direction: CreatorDirectionV1
    hooks: list[HookOptionV1]
    script_beats: list[ScriptBeatV1]
    storyboard: list[StoryboardSceneV1]
    must_show: list[MustShowRequirementV1]
    talking_points: list[str] = Field(default_factory=list)
    text_overlays: list[str] = Field(default_factory=list)
    proof_direction: list[str] = Field(default_factory=list)
    offer_direction: list[str] = Field(default_factory=list)
    cta: CtaDirectionV1
    claim_guardrails: ClaimGuardrailsV1
    do: list[str] = Field(default_factory=list)
    dont: list[str] = Field(default_factory=list)
    rights_note: RightsNoteV1
    revision_checklist: list[str] = Field(default_factory=list)
    source_adaptation_run_id: UUID | None = None
    source_viral_kit_id: UUID | None = None
    source_viral_kit_version: int | None = Field(default=None, ge=1)
    source_pattern_kit_version_ids: list[UUID] = Field(default_factory=list)
    source_concept_id: str
