from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from viraldy.modules.campaign_packs.contracts import CampaignPackBriefV1


class CreateCampaignPackRequest(BaseModel):
    adaptation_run_id: UUID
    concept_id: str = Field(min_length=1)


class CreateCampaignPackVersionRequest(BaseModel):
    brief: CampaignPackBriefV1
    change_note: str | None = None


class UpdateCampaignPackRequest(BaseModel):
    status: Literal["draft", "ready", "sent", "archived"] | None = None


class CampaignPackVersionResponse(BaseModel):
    id: UUID
    campaign_pack_id: UUID
    version_number: int
    brief_json: dict[str, object]
    brief_schema_version: str
    product_snapshot_json: dict[str, object] | None = None
    compiled_requirements_json: dict[str, object]
    requirements_schema_version: str | None = None
    change_note: str | None
    source_adaptation_run_id: UUID | None = None
    source_model_run_id: UUID | None = None
    source_prompt_version: str | None = None
    source_schema_version: str | None = None
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
