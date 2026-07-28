from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from viraldy.modules.jobs.public import JobResponse


class CreateReferenceRequest(BaseModel):
    board_id: UUID
    asset_id: UUID
    product_id: UUID | None = None
    source_platform: str | None = None
    source_url: str | None = None
    title: str = Field(min_length=1, max_length=255)
    notes: str | None = None


class ReferenceResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    board_id: UUID
    product_id: UUID | None
    asset_id: UUID
    source_platform: str | None
    source_url: str | None
    title: str
    notes: str | None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AnalyzeReferenceResponse(BaseModel):
    reference: ReferenceResponse
    job: JobResponse
