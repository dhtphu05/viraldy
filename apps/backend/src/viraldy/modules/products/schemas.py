from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class CreateProductRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    market: str | None = None
    external_source: str | None = None
    external_id: str | None = None
    metadata_json: dict[str, object] = Field(default_factory=dict)


class UpdateProductRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    status: str | None = None
    market: str | None = None
    metadata_json: dict[str, object] | None = None


class ProductResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    name: str
    description: str | None
    status: str
    market: str | None
    external_source: str | None
    external_id: str | None
    metadata_json: dict[str, object]

    model_config = {"from_attributes": True}


class ProductSummary(BaseModel):
    id: UUID
    workspace_id: UUID
    name: str
    status: str

    model_config = {"from_attributes": True}
