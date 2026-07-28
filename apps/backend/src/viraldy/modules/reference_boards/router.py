from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from viraldy.api.dependencies.auth import CurrentUserDep, DbSession, require_workspace_permission
from viraldy.api.dependencies.request import get_request_id
from viraldy.api.responses.envelope import Envelope, success
from viraldy.modules.products.public import ProductQueries
from viraldy.modules.reference_boards.schemas import (
    CreateReferenceBoardRequest,
    UpdateReferenceBoardRequest,
)
from viraldy.modules.reference_boards.service import ReferenceBoardService
from viraldy.platform.auth.policy import Permission

router = APIRouter(prefix="/workspaces/{workspace_id}/reference-boards", tags=["reference-boards"])


def _service(db: DbSession) -> ReferenceBoardService:
    return ReferenceBoardService(db, ProductQueries(db))


@router.post("", status_code=status.HTTP_201_CREATED, response_model=Envelope)
async def create_board(
    workspace_id: UUID,
    payload: CreateReferenceBoardRequest,
    current_user: CurrentUserDep,
    db: DbSession,
    request_id: Annotated[str, Depends(get_request_id)],
) -> Envelope:
    await require_workspace_permission(
        workspace_id, Permission.CREATE_UPDATE_BUSINESS_RESOURCES, current_user, db
    )
    board = await _service(db).create(workspace_id, current_user.id, payload)
    return success(board.model_dump(mode="json"), request_id)


@router.get("", response_model=Envelope)
async def list_boards(
    workspace_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    product_id: UUID | None = None,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.READ, current_user, db)
    boards = await _service(db).list(workspace_id, product_id)
    return success([board.model_dump(mode="json") for board in boards], request_id)


@router.get("/{board_id}", response_model=Envelope)
async def get_board(
    workspace_id: UUID,
    board_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.READ, current_user, db)
    board = await _service(db).get(workspace_id, board_id)
    return success(board.model_dump(mode="json"), request_id)


@router.patch("/{board_id}", response_model=Envelope)
async def update_board(
    workspace_id: UUID,
    board_id: UUID,
    payload: UpdateReferenceBoardRequest,
    current_user: CurrentUserDep,
    db: DbSession,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(
        workspace_id, Permission.CREATE_UPDATE_BUSINESS_RESOURCES, current_user, db
    )
    board = await _service(db).update(workspace_id, board_id, payload)
    return success(board.model_dump(mode="json"), request_id)


@router.delete("/{board_id}", response_model=Envelope)
async def delete_board(
    workspace_id: UUID,
    board_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(
        workspace_id, Permission.CREATE_UPDATE_BUSINESS_RESOURCES, current_user, db
    )
    await _service(db).delete(workspace_id, board_id)
    return success({"deleted": True}, request_id)
