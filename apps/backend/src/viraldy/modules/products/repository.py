from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from viraldy.modules.products.models import ProductModel
from viraldy.platform.clock.utc import utc_now


class ProductRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        workspace_id: UUID,
        name: str,
        description: str | None,
        market: str | None,
        external_source: str | None,
        external_id: str | None,
        metadata_json: dict[str, object],
        created_by_user_id: UUID,
    ) -> ProductModel:
        product = ProductModel(
            workspace_id=workspace_id,
            name=name,
            description=description,
            status="active",
            market=market,
            external_source=external_source,
            external_id=external_id,
            metadata_json=metadata_json,
            created_by_user_id=created_by_user_id,
        )
        self._session.add(product)
        await self._session.flush()
        return product

    async def list_products(self, workspace_id: UUID) -> list[ProductModel]:
        result = await self._session.execute(
            select(ProductModel)
            .where(ProductModel.workspace_id == workspace_id, ProductModel.deleted_at.is_(None))
            .order_by(ProductModel.created_at.desc())
        )
        return list(result.scalars())

    async def get_product(self, workspace_id: UUID, product_id: UUID) -> ProductModel | None:
        result = await self._session.execute(
            select(ProductModel).where(
                ProductModel.workspace_id == workspace_id,
                ProductModel.id == product_id,
                ProductModel.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def update_product(
        self,
        workspace_id: UUID,
        product_id: UUID,
        values: dict[str, object],
    ) -> ProductModel | None:
        product = await self.get_product(workspace_id, product_id)
        if product is None:
            return None

        for field, value in values.items():
            setattr(product, field, value)
        await self._session.flush()
        return product

    async def archive_product(self, workspace_id: UUID, product_id: UUID) -> bool:
        product = await self.get_product(workspace_id, product_id)
        if product is None:
            return False

        product.deleted_at = utc_now()
        await self._session.flush()
        return True

    async def exists_in_workspace(self, workspace_id: UUID, product_id: UUID) -> bool:
        result = await self._session.execute(
            select(ProductModel.id).where(
                ProductModel.workspace_id == workspace_id,
                ProductModel.id == product_id,
                ProductModel.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none() is not None
