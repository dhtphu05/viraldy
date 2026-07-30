from __future__ import annotations

from typing import Protocol
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from viraldy.modules.creative_domain.schema_versions import PRODUCT_CONTEXT_SCHEMA_VERSION
from viraldy.modules.products.contracts import (
    ProductContextV1,
    build_minimal_product_context,
    product_context_to_json,
    validate_product_context,
)
from viraldy.modules.products.models import ProductModel
from viraldy.modules.products.repository import ProductRepository
from viraldy.modules.products.schemas import ProductSummary


class ProductContextSnapshot(BaseModel):
    product_id: UUID
    workspace_id: UUID
    context_schema_version: str
    product_context_version: int
    product_context: ProductContextV1


class ProductLookupPort(Protocol):
    async def exists_in_workspace(self, workspace_id: UUID, product_id: UUID) -> bool:
        raise NotImplementedError


class ProductQueries:
    def __init__(self, session: AsyncSession) -> None:
        self._repository = ProductRepository(session)

    async def exists_in_workspace(self, workspace_id: UUID, product_id: UUID) -> bool:
        return await self._repository.exists_in_workspace(workspace_id, product_id)

    async def get_product_summary(
        self,
        workspace_id: UUID,
        product_id: UUID,
    ) -> ProductSummary | None:
        product = await self._repository.get_product(workspace_id, product_id)
        if product is None:
            return None
        return ProductSummary.model_validate(product)

    async def get_product_context_snapshot(
        self,
        workspace_id: UUID,
        product_id: UUID,
    ) -> ProductContextSnapshot | None:
        product = await self._repository.get_product(workspace_id, product_id)
        if product is None:
            return None
        return get_product_context_snapshot(product)


class SyncProductQueries:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_product_context_snapshot(
        self,
        workspace_id: UUID,
        product_id: UUID,
    ) -> ProductContextSnapshot | None:
        product = self._session.execute(
            select(ProductModel).where(
                ProductModel.workspace_id == workspace_id,
                ProductModel.id == product_id,
                ProductModel.deleted_at.is_(None),
            )
        ).scalar_one_or_none()
        if product is None:
            return None
        return get_product_context_snapshot(product)


def get_product_context_snapshot(product: ProductModel) -> ProductContextSnapshot:
    context = _context_from_product(product)
    return ProductContextSnapshot(
        product_id=product.id,
        workspace_id=product.workspace_id,
        context_schema_version=product.context_schema_version or PRODUCT_CONTEXT_SCHEMA_VERSION,
        product_context_version=int(getattr(product, "product_context_version", 1) or 1),
        product_context=context,
    )


def _context_from_product(product: ProductModel) -> ProductContextV1:
    if product.product_context_json:
        return validate_product_context(product.product_context_json)
    return build_minimal_product_context(
        name=product.name,
        description=product.description,
        market=product.market,
        metadata_json=product.metadata_json,
    )


__all__ = [
    "ProductContextSnapshot",
    "ProductLookupPort",
    "ProductQueries",
    "SyncProductQueries",
    "build_minimal_product_context",
    "get_product_context_snapshot",
    "product_context_to_json",
    "validate_product_context",
]
