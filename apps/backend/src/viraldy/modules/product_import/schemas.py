from __future__ import annotations

from pydantic import BaseModel, Field

from viraldy.modules.products.schemas import CreateProductRequest


class ProductCrawlRequest(BaseModel):
    url: str = Field(min_length=8, max_length=2048)


class ProductImportPreview(BaseModel):
    source_url: str
    crawl: dict[str, object]
    product_draft: CreateProductRequest
