from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from viraldy.modules.product_events.public import ProductEventPublisher
from viraldy.modules.products.contracts import (
    ProductContextV1,
    build_minimal_product_context,
    product_context_to_json,
    validate_product_context,
)
from viraldy.modules.products.models import ProductModel
from viraldy.modules.products.repository import ProductRepository
from viraldy.modules.products.schemas import (
    CreateProductRequest,
    ProductResponse,
    ProductSummary,
    UpdateProductRequest,
)
from viraldy.shared.errors.base import AppError, NotFoundError


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
        product_context = _context_for_create(data)
        product = await self._repository.create(
            workspace_id=workspace_id,
            name=product_context.identity.name,
            description=data.description,
            market=product_context.identity.market,
            external_source=data.external_source,
            external_id=data.external_id,
            metadata_json=data.metadata_json,
            product_context_json=product_context_to_json(product_context),
            context_schema_version=product_context.schema_version,
            created_by_user_id=user_id,
        )
        await ProductEventPublisher(self._session).record(
            event_type="product_created",
            workspace_id=workspace_id,
            actor_user_id=user_id,
            subject_type="product",
            subject_id=product.id,
            payload_json={
                "name": product.name,
                "context_schema_version": product.context_schema_version,
            },
        )
        await self._session.commit()
        return _response_from_product(product)

    async def list_products(self, workspace_id: UUID) -> list[ProductResponse]:
        products = await self._repository.list_products(workspace_id)
        return [_response_from_product(product) for product in products]

    async def get_product(self, workspace_id: UUID, product_id: UUID) -> ProductResponse:
        product = await self._repository.get_product(workspace_id, product_id)
        if product is None:
            raise NotFoundError("PRODUCT_NOT_FOUND", "Product was not found.")
        return _response_from_product(product)

    async def update_product(
        self,
        workspace_id: UUID,
        product_id: UUID,
        data: UpdateProductRequest,
    ) -> ProductResponse:
        product = await self._repository.get_product(workspace_id, product_id)
        if product is None:
            raise NotFoundError("PRODUCT_NOT_FOUND", "Product was not found.")

        values = data.model_dump(exclude={"product_context"}, exclude_unset=True, exclude_none=True)
        if data.product_context is not None:
            _validate_projection(data.product_context, data.name, data.market)
            values["name"] = data.product_context.identity.name
            values["market"] = data.product_context.identity.market
            values["product_context_json"] = product_context_to_json(data.product_context)
            values["context_schema_version"] = data.product_context.schema_version
        elif "name" in values or "market" in values:
            current = _context_from_product(product)
            identity = current.identity.model_copy(
                update={
                    "name": str(values.get("name", current.identity.name)),
                    "market": str(values.get("market", current.identity.market)),
                }
            )
            updated_context = current.model_copy(update={"identity": identity})
            values["product_context_json"] = product_context_to_json(updated_context)
            values["context_schema_version"] = updated_context.schema_version

        product = await self._repository.update_product(workspace_id, product_id, values)
        if product is None:
            raise NotFoundError("PRODUCT_NOT_FOUND", "Product was not found.")

        await self._session.commit()
        return _response_from_product(product)

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


def _context_for_create(data: CreateProductRequest) -> ProductContextV1:
    if data.product_context is None:
        return build_minimal_product_context(
            name=data.name,
            description=data.description,
            market=data.market,
            metadata_json=data.metadata_json,
        )
    _validate_projection(data.product_context, data.name, data.market)
    return data.product_context


def _validate_projection(
    context: ProductContextV1, name: str | None, market: str | None
) -> None:
    if name is not None and context.identity.name != name:
        raise AppError(
            "PRODUCT_CONTEXT_INVALID",
            "Product context identity.name must match the product name projection.",
        )
    if market is not None and context.identity.market != market:
        raise AppError(
            "PRODUCT_CONTEXT_INVALID",
            "Product context identity.market must match the product market projection.",
        )


def _response_from_product(product: ProductModel) -> ProductResponse:
    context = _context_from_product(product)
    return ProductResponse(
        id=product.id,
        workspace_id=product.workspace_id,
        name=product.name,
        description=product.description,
        status=product.status,
        market=product.market,
        external_source=product.external_source,
        external_id=product.external_id,
        metadata_json=product.metadata_json,
        product_context=context,
        context_schema_version=product.context_schema_version or context.schema_version,
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
