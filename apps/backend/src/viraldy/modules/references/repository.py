from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from viraldy.modules.references.models import ReferenceModel


class ReferenceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        workspace_id: UUID,
        user_id: UUID,
        board_id: UUID,
        asset_id: UUID,
        product_id: UUID | None,
        source_platform: str | None,
        source_url: str | None,
        title: str,
        notes: str | None,
    ) -> ReferenceModel:
        reference = ReferenceModel(
            workspace_id=workspace_id,
            board_id=board_id,
            product_id=product_id,
            asset_id=asset_id,
            source_platform=source_platform,
            source_url=source_url,
            title=title,
            notes=notes,
            created_by_user_id=user_id,
        )
        self._session.add(reference)
        await self._session.flush()
        return reference

    async def list(self, workspace_id: UUID) -> list[ReferenceModel]:
        result = await self._session.execute(
            select(ReferenceModel)
            .where(ReferenceModel.workspace_id == workspace_id, ReferenceModel.deleted_at.is_(None))
            .order_by(ReferenceModel.created_at.desc())
        )
        return list(result.scalars())

    async def get(self, workspace_id: UUID, reference_id: UUID) -> ReferenceModel | None:
        result = await self._session.execute(
            select(ReferenceModel).where(
                ReferenceModel.workspace_id == workspace_id,
                ReferenceModel.id == reference_id,
                ReferenceModel.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def set_status(self, reference: ReferenceModel, status: str) -> None:
        reference.status = status
        await self._session.flush()


class SyncReferenceRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, workspace_id: UUID, reference_id: UUID) -> ReferenceModel | None:
        return self._session.execute(
            select(ReferenceModel).where(
                ReferenceModel.workspace_id == workspace_id,
                ReferenceModel.id == reference_id,
                ReferenceModel.deleted_at.is_(None),
            )
        ).scalar_one_or_none()
