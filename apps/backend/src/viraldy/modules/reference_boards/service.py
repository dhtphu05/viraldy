from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from viraldy.modules.products.public import ProductLookupPort
from viraldy.modules.reference_boards.repository import ReferenceBoardRepository
from viraldy.modules.reference_boards.schemas import (
    CreateReferenceBoardRequest,
    ReferenceBoardResponse,
    UpdateReferenceBoardRequest,
)
from viraldy.shared.errors.base import NotFoundError


class ReferenceBoardService:
    def __init__(self, session: AsyncSession, product_lookup: ProductLookupPort) -> None:
        self._session = session
        self._repository = ReferenceBoardRepository(session)
        self._product_lookup = product_lookup

    async def create(
        self,
        workspace_id: UUID,
        user_id: UUID,
        data: CreateReferenceBoardRequest,
    ) -> ReferenceBoardResponse:
        if data.product_id and not await self._product_lookup.exists_in_workspace(
            workspace_id, data.product_id
        ):
            raise NotFoundError("PRODUCT_NOT_FOUND", "Product was not found.")
        board = await self._repository.create(
            workspace_id, user_id, data.name, data.description, data.product_id, data.board_type
        )
        await self._session.commit()
        return ReferenceBoardResponse.model_validate(board)

    async def list(
        self, workspace_id: UUID, product_id: UUID | None = None
    ) -> list[ReferenceBoardResponse]:
        boards = await self._repository.list(workspace_id, product_id)
        return [ReferenceBoardResponse.model_validate(board) for board in boards]

    async def get(self, workspace_id: UUID, board_id: UUID) -> ReferenceBoardResponse:
        board = await self._repository.get(workspace_id, board_id)
        if board is None:
            raise NotFoundError("REFERENCE_BOARD_NOT_FOUND", "Reference board was not found.")
        return ReferenceBoardResponse.model_validate(board)

    async def update(
        self,
        workspace_id: UUID,
        board_id: UUID,
        data: UpdateReferenceBoardRequest,
    ) -> ReferenceBoardResponse:
        values = data.model_dump(exclude_unset=True)
        product_id = values.get("product_id")
        if product_id and not await self._product_lookup.exists_in_workspace(
            workspace_id, product_id
        ):
            raise NotFoundError("PRODUCT_NOT_FOUND", "Product was not found.")
        board = await self._repository.update(workspace_id, board_id, values)
        if board is None:
            raise NotFoundError("REFERENCE_BOARD_NOT_FOUND", "Reference board was not found.")
        await self._session.commit()
        return ReferenceBoardResponse.model_validate(board)

    async def delete(self, workspace_id: UUID, board_id: UUID) -> None:
        if not await self._repository.archive(workspace_id, board_id):
            raise NotFoundError("REFERENCE_BOARD_NOT_FOUND", "Reference board was not found.")
        await self._session.commit()
