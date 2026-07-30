from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from viraldy.api.dependencies.auth import (
    CurrentUserDep,
    DbSession,
    require_workspace_permission,
)
from viraldy.api.dependencies.request import get_request_id
from viraldy.api.responses.envelope import Envelope, success
from viraldy.modules.products.schemas import CreateProductRequest, UpdateProductRequest
from viraldy.modules.products.service import ProductService
from viraldy.platform.auth.policy import Permission

router = APIRouter(prefix="/workspaces/{workspace_id}/products", tags=["products"])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=Envelope)
async def create_product(
    workspace_id: UUID,
    payload: CreateProductRequest,
    current_user: CurrentUserDep,
    db: DbSession,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(
        workspace_id, Permission.PRODUCT_WRITE, current_user, db
    )
    product = await ProductService(db).create_product(workspace_id, current_user.id, payload)
    return success(product.model_dump(mode="json"), request_id)


@router.get("", response_model=Envelope)
async def list_products(
    workspace_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.PRODUCT_READ, current_user, db)
    products = await ProductService(db).list_products(workspace_id)
    return success([product.model_dump(mode="json") for product in products], request_id)


@router.get("/{product_id}", response_model=Envelope)
async def get_product(
    workspace_id: UUID,
    product_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.PRODUCT_READ, current_user, db)
    product = await ProductService(db).get_product(workspace_id, product_id)
    return success(product.model_dump(mode="json"), request_id)


@router.patch("/{product_id}", response_model=Envelope)
async def update_product(
    workspace_id: UUID,
    product_id: UUID,
    payload: UpdateProductRequest,
    current_user: CurrentUserDep,
    db: DbSession,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(
        workspace_id, Permission.PRODUCT_WRITE, current_user, db
    )
    product = await ProductService(db).update_product(workspace_id, product_id, payload)
    return success(product.model_dump(mode="json"), request_id)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    workspace_id: UUID,
    product_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
) -> Response:
    await require_workspace_permission(
        workspace_id, Permission.DATA_DELETE, current_user, db
    )
    await ProductService(db).delete_product(workspace_id, product_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
