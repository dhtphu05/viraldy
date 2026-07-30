from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

ProductEventType = Literal[
    "user_signed_up",
    "workspace_created",
    "product_created",
    "reference_uploaded",
    "reference_analyzed",
    "creative_dna_viewed",
    "creative_dna_corrected",
    "pattern_kit_created",
    "pattern_kit_version_created",
    "pattern_kit_reviewed",
    "pattern_kit_validated",
    "pattern_kit_corrected",
    "viral_kit_created",
    "viral_kit_version_created",
    "concept_selected",
    "concept_rejected",
    "campaign_pack_created",
    "campaign_pack_exported",
    "ugc_uploaded",
    "preflight_viewed",
    "recommendation_accepted",
    "recommendation_rejected",
    "recommendation_applied",
    "revision_uploaded",
]


class ProductEventContractBase(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProductEventPayloadV1(ProductEventContractBase):
    event_type: ProductEventType
    subject_type: str | None = Field(default=None, max_length=100)
    subject_id: UUID | None = None
    payload_json: dict[str, object] = Field(default_factory=dict)
