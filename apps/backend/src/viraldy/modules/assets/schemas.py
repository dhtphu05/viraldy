from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CreateUploadSessionRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=512)
    declared_mime_type: str
    declared_size_bytes: int = Field(gt=0)
    asset_type: str
    product_id: UUID | None = None


class UploadSessionResponse(BaseModel):
    asset_id: UUID
    asset_version_id: UUID
    upload_url: str
    upload_method: str
    required_headers: dict[str, str]
    expires_at: datetime


class AssetResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    product_id: UUID | None
    asset_type: str
    status: str
    current_version_id: UUID | None
    metadata_json: dict[str, object]

    model_config = {"from_attributes": True}
