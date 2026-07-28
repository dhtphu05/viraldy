from __future__ import annotations

from typing import Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from viraldy.modules.products.repository import ProductRepository
from viraldy.modules.products.schemas import ProductSummary


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
