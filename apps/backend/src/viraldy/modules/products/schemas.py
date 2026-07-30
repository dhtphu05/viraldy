from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field

from viraldy.modules.products.contracts import ProductContextV1


class CreateProductRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    market: str | None = None
    external_source: str | None = None
    external_id: str | None = None
    metadata_json: dict[str, object] = Field(default_factory=dict)
    product_context: ProductContextV1 | None = None


class UpdateProductRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    status: str | None = None
    market: str | None = None
    metadata_json: dict[str, object] | None = None
    product_context: ProductContextV1 | None = None


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
    product_context: ProductContextV1
    context_schema_version: str
    product_context_version: int

    model_config = {"from_attributes": True}


class ProductSummary(BaseModel):
    id: UUID
    workspace_id: UUID
    name: str
    status: str
    context_schema_version: str | None = None
    product_context_version: int = 1

    model_config = {"from_attributes": True}
