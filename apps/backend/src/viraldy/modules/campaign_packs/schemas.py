from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from viraldy.modules.campaign_packs.contracts import CampaignPackBriefV1
from viraldy.modules.campaign_packs.requirements import CompiledRequirementsSnapshotV2
from viraldy.modules.products.contracts import ProductContextV1

CampaignPackExportFormat = Literal["json", "text"]


class CreateCampaignPackRequest(BaseModel):
    adaptation_run_id: UUID
    concept_id: str = Field(min_length=1)


class CreateCampaignPackVersionRequest(BaseModel):
    brief: CampaignPackBriefV1
    change_note: str | None = None


class UpdateCampaignPackRequest(BaseModel):
    status: Literal["draft", "ready", "sent", "archived"] | None = None


class ExportCampaignPackRequest(BaseModel):
    format: CampaignPackExportFormat


class CampaignPackExportResponse(BaseModel):
    campaign_pack_id: UUID
    campaign_pack_version_id: UUID
    version_number: int = Field(ge=1)
    format: CampaignPackExportFormat
    filename: str
    content_type: str
    content: str


class CampaignPackVersionResponse(BaseModel):
    id: UUID
    campaign_pack_id: UUID
    version_number: int
    brief_json: CampaignPackBriefV1
    brief_schema_version: str
    product_snapshot_json: ProductContextV1 | None = None
    compiled_requirements_json: CompiledRequirementsSnapshotV2
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
    adaptation_run_id: UUID | None
    status: str
    current_version_id: UUID | None
    created_at: datetime
    updated_at: datetime
    current_version: CampaignPackVersionResponse | None = None

    model_config = {"from_attributes": True}
