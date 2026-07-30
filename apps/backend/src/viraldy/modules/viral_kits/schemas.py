from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from viraldy.modules.campaign_packs.schemas import CampaignPackResponse
from viraldy.modules.feedback.public import FeedbackJsonValue, FeedbackType
from viraldy.modules.viral_kits.contracts import (
    CommercialConstraintsV1,
    ConceptActionV1,
    CreatorConstraintsV1,
    ProductionConstraintsV1,
    ViralKitObjectiveV1,
    ViralKitPlatformV1,
    ViralKitStatusV1,
    ViralKitV1,
)


class CreateViralKitRequest(BaseModel):
    product_id: UUID
    expected_product_context_version: int = Field(ge=1)
    pattern_kit_version_ids: list[UUID] = Field(min_length=1)
    objective: ViralKitObjectiveV1
    platform: ViralKitPlatformV1
    target_market: str = Field(min_length=1, max_length=100)
    buyer_persona_id: str | None = Field(default=None, max_length=120)
    creator_constraints: CreatorConstraintsV1 = Field(default_factory=CreatorConstraintsV1)
    production_constraints: ProductionConstraintsV1 = Field(
        default_factory=ProductionConstraintsV1
    )
    commercial_constraints: CommercialConstraintsV1 = Field(
        default_factory=CommercialConstraintsV1
    )
    concept_count: int = Field(default=3)
    notes: str | None = Field(default=None, max_length=2000)
    applicability_override_reason: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_request(self) -> CreateViralKitRequest:
        if len(self.pattern_kit_version_ids) != len(set(self.pattern_kit_version_ids)):
            raise ValueError("pattern_kit_version_ids cannot contain duplicates")
        if self.concept_count != 3:
            raise ValueError("ViralKit V1 requires exactly three concepts")
        if self.commercial_constraints.product_tag_required and self.platform != "tiktok_shop":
            raise ValueError("product_tag_required is only valid for tiktok_shop")
        return self


class CreateViralKitVersionRequest(BaseModel):
    change_reason: str = Field(min_length=1, max_length=1000)
    viral_kit: ViralKitV1 | None = None


class ViralKitConceptActionRequest(BaseModel):
    concept_id: str = Field(min_length=1, max_length=120)
    action: ConceptActionV1
    reason: str | None = Field(default=None, max_length=2000)


class CreateViralKitCampaignPackRequest(BaseModel):
    rights_note: str | None = Field(default=None, max_length=1000)


class CreateViralKitFeedbackRequest(BaseModel):
    subject_version: int | None = Field(default=None, ge=1)
    field_path: str = Field(min_length=1, max_length=500)
    feedback_type: FeedbackType
    ai_value_json: FeedbackJsonValue = None
    user_value_json: FeedbackJsonValue = None
    comment: str | None = Field(default=None, max_length=2000)
    model_run_id: UUID | None = None


class ViralKitSummaryResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    product_id: UUID
    name: str
    objective: ViralKitObjectiveV1
    platform: ViralKitPlatformV1
    target_market: str
    status: ViralKitStatusV1
    latest_version: int
    selected_concept_id: str | None
    created_by_user_id: UUID
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None

    model_config = {"from_attributes": True}


class ViralKitVersionResponse(BaseModel):
    id: UUID
    viral_kit_id: UUID
    workspace_id: UUID
    version: int
    parent_version: int | None
    change_reason: str | None
    schema_version: str
    product_context_version: int
    product_snapshot_json: dict[str, object]
    viral_kit: ViralKitV1
    model_run_id: UUID | None
    created_by_user_id: UUID
    created_at: datetime


class ViralKitDetailResponse(BaseModel):
    kit: ViralKitSummaryResponse
    latest_version: ViralKitVersionResponse


class ViralKitConceptActionResponse(BaseModel):
    id: UUID
    viral_kit_id: UUID
    viral_kit_version: int
    concept_id: str
    action: ConceptActionV1
    reason: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ViralKitCampaignPackResponse(BaseModel):
    concept_id: str
    campaign_pack_id: UUID
    campaign_pack_version_id: UUID
    compiled_requirements_schema_version: str
    campaign_pack: CampaignPackResponse
