from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CreateCampaignPackRequest(BaseModel):
    adaptation_run_id: UUID
    concept_id: str = Field(min_length=1)


class CreateCampaignPackVersionRequest(BaseModel):
    brief_json: dict[str, object]
    change_note: str | None = None


class UpdateCampaignPackRequest(BaseModel):
    status: str | None = None


class CampaignPackVersionResponse(BaseModel):
    id: UUID
    campaign_pack_id: UUID
    version_number: int
    brief_json: dict[str, object]
    change_note: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CampaignPackResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    product_id: UUID
    adaptation_run_id: UUID
    status: str
    current_version_id: UUID | None
    created_at: datetime
    updated_at: datetime
    current_version: CampaignPackVersionResponse | None = None

    model_config = {"from_attributes": True}
