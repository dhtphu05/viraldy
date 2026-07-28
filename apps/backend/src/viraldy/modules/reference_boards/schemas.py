from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CreateReferenceBoardRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    product_id: UUID | None = None
    board_type: str = "creative_research"


class UpdateReferenceBoardRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    product_id: UUID | None = None
    board_type: str | None = None
    status: str | None = None


class ReferenceBoardResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    product_id: UUID | None
    name: str
    description: str | None
    board_type: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
