from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CreateAdaptationRequest(BaseModel):
    product_id: UUID
    creative_dna_version_id: UUID
    objective: str = Field(default="tiktok_shop_affiliate_test", min_length=1, max_length=255)
    target_market: str = Field(default="US", min_length=1, max_length=100)
    target_buyer: dict[str, object] = Field(default_factory=dict)
    constraints: dict[str, object] = Field(default_factory=dict)


class AdaptationRunResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    product_id: UUID
    creative_dna_version_id: UUID
    objective: str
    target_market: str
    target_buyer_json: dict[str, object]
    constraints_json: dict[str, object]
    result_json: dict[str, object]
    status: str
    schema_version: str
    product_snapshot_json: dict[str, object] | None = None
    product_context_schema_version: str | None = None
    analysis_mode: str
    primary_model_run_id: UUID | None = None
    model_version: str | None
    prompt_version: str
    created_at: datetime

    model_config = {"from_attributes": True}
