from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from viraldy.modules.reference_boards.models import ReferenceBoardModel
from viraldy.platform.clock.utc import utc_now


class ReferenceBoardRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        workspace_id: UUID,
        user_id: UUID,
        name: str,
        description: str | None,
        product_id: UUID | None,
        board_type: str,
    ) -> ReferenceBoardModel:
        board = ReferenceBoardModel(
            workspace_id=workspace_id,
            product_id=product_id,
            name=name,
            description=description,
            board_type=board_type,
            created_by_user_id=user_id,
        )
        self._session.add(board)
        await self._session.flush()
        return board

    async def list(
        self, workspace_id: UUID, product_id: UUID | None = None
    ) -> list[ReferenceBoardModel]:
        stmt = select(ReferenceBoardModel).where(
            ReferenceBoardModel.workspace_id == workspace_id,
            ReferenceBoardModel.deleted_at.is_(None),
        )
        if product_id is not None:
            stmt = stmt.where(ReferenceBoardModel.product_id == product_id)
        result = await self._session.execute(stmt.order_by(ReferenceBoardModel.created_at.desc()))
        return list(result.scalars())

    async def get(self, workspace_id: UUID, board_id: UUID) -> ReferenceBoardModel | None:
        result = await self._session.execute(
            select(ReferenceBoardModel).where(
                ReferenceBoardModel.workspace_id == workspace_id,
                ReferenceBoardModel.id == board_id,
                ReferenceBoardModel.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def update(
        self,
        workspace_id: UUID,
        board_id: UUID,
        values: dict[str, object],
    ) -> ReferenceBoardModel | None:
        board = await self.get(workspace_id, board_id)
        if board is None:
            return None
        for key, value in values.items():
            setattr(board, key, value)
        await self._session.flush()
        return board

    async def archive(self, workspace_id: UUID, board_id: UUID) -> bool:
        board = await self.get(workspace_id, board_id)
        if board is None:
            return False
        board.deleted_at = utc_now()
        board.status = "archived"
        await self._session.flush()
        return True


class SyncReferenceBoardQueries:
    def __init__(self, session: Session) -> None:
        self._session = session

    def exists(self, workspace_id: UUID, board_id: UUID) -> bool:
        return (
            self._session.execute(
                select(ReferenceBoardModel.id).where(
                    ReferenceBoardModel.workspace_id == workspace_id,
                    ReferenceBoardModel.id == board_id,
                    ReferenceBoardModel.deleted_at.is_(None),
                )
            ).scalar_one_or_none()
            is not None
        )
