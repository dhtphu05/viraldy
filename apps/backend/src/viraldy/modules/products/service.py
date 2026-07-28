from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from viraldy.modules.products.repository import ProductRepository
from viraldy.modules.products.schemas import (
    CreateProductRequest,
    ProductResponse,
    ProductSummary,
    UpdateProductRequest,
)
from viraldy.shared.errors.base import NotFoundError


class ProductService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repository = ProductRepository(session)

    async def create_product(
        self,
        workspace_id: UUID,
        user_id: UUID,
        data: CreateProductRequest,
    ) -> ProductResponse:
        product = await self._repository.create(
            workspace_id=workspace_id,
            name=data.name,
            description=data.description,
            market=data.market,
            external_source=data.external_source,
            external_id=data.external_id,
            metadata_json=data.metadata_json,
            created_by_user_id=user_id,
        )
        await self._session.commit()
        return ProductResponse.model_validate(product)

    async def list_products(self, workspace_id: UUID) -> list[ProductResponse]:
        products = await self._repository.list_products(workspace_id)
        return [ProductResponse.model_validate(product) for product in products]

    async def get_product(self, workspace_id: UUID, product_id: UUID) -> ProductResponse:
        product = await self._repository.get_product(workspace_id, product_id)
        if product is None:
            raise NotFoundError("PRODUCT_NOT_FOUND", "Product was not found.")
        return ProductResponse.model_validate(product)

    async def update_product(
        self,
        workspace_id: UUID,
        product_id: UUID,
        data: UpdateProductRequest,
    ) -> ProductResponse:
        values = data.model_dump(exclude_unset=True, exclude_none=True)
        product = await self._repository.update_product(workspace_id, product_id, values)
        if product is None:
            raise NotFoundError("PRODUCT_NOT_FOUND", "Product was not found.")

        await self._session.commit()
        return ProductResponse.model_validate(product)

    async def delete_product(self, workspace_id: UUID, product_id: UUID) -> None:
        deleted = await self._repository.archive_product(workspace_id, product_id)
        if not deleted:
            raise NotFoundError("PRODUCT_NOT_FOUND", "Product was not found.")

        await self._session.commit()

    async def get_product_summary(
        self,
        workspace_id: UUID,
        product_id: UUID,
    ) -> ProductSummary | None:
        product = await self._repository.get_product(workspace_id, product_id)
        if product is None:
            return None

        return ProductSummary.model_validate(product)
