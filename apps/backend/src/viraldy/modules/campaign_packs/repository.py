from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from viraldy.modules.campaign_packs.models import CampaignPackModel, CampaignPackVersionModel


class CampaignPackRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        workspace_id: UUID,
        user_id: UUID,
        product_id: UUID,
        adaptation_run_id: UUID,
        brief_json: dict[str, object],
    ) -> tuple[CampaignPackModel, CampaignPackVersionModel]:
        pack = CampaignPackModel(
            workspace_id=workspace_id,
            product_id=product_id,
            adaptation_run_id=adaptation_run_id,
            created_by_user_id=user_id,
        )
        self._session.add(pack)
        await self._session.flush()
        version = CampaignPackVersionModel(
            campaign_pack_id=pack.id,
            version_number=1,
            brief_json=brief_json,
            change_note="Initial generated brief",
            created_by_user_id=user_id,
        )
        self._session.add(version)
        await self._session.flush()
        pack.current_version_id = version.id
        await self._session.flush()
        return pack, version

    async def list(self, workspace_id: UUID) -> list[CampaignPackModel]:
        result = await self._session.execute(
            select(CampaignPackModel)
            .where(
                CampaignPackModel.workspace_id == workspace_id,
                CampaignPackModel.deleted_at.is_(None),
            )
            .order_by(CampaignPackModel.created_at.desc())
        )
        return list(result.scalars())

    async def get(self, workspace_id: UUID, pack_id: UUID) -> CampaignPackModel | None:
        result = await self._session.execute(
            select(CampaignPackModel).where(
                CampaignPackModel.workspace_id == workspace_id,
                CampaignPackModel.id == pack_id,
                CampaignPackModel.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_version(self, version_id: UUID) -> CampaignPackVersionModel | None:
        return await self._session.get(CampaignPackVersionModel, version_id)

    async def get_version_in_workspace(
        self, workspace_id: UUID, version_id: UUID
    ) -> CampaignPackVersionModel | None:
        result = await self._session.execute(
            select(CampaignPackVersionModel)
            .join(
                CampaignPackModel, CampaignPackVersionModel.campaign_pack_id == CampaignPackModel.id
            )
            .where(
                CampaignPackVersionModel.id == version_id,
                CampaignPackModel.workspace_id == workspace_id,
                CampaignPackModel.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def list_versions(self, pack_id: UUID) -> list[CampaignPackVersionModel]:
        result = await self._session.execute(
            select(CampaignPackVersionModel)
            .where(CampaignPackVersionModel.campaign_pack_id == pack_id)
            .order_by(CampaignPackVersionModel.version_number.desc())
        )
        return list(result.scalars())

    async def create_version(
        self,
        pack: CampaignPackModel,
        user_id: UUID,
        brief_json: dict[str, object],
        change_note: str | None,
    ) -> CampaignPackVersionModel:
        next_version = (
            await self._session.scalar(
                select(func.max(CampaignPackVersionModel.version_number)).where(
                    CampaignPackVersionModel.campaign_pack_id == pack.id
                )
            )
            or 0
        ) + 1
        version = CampaignPackVersionModel(
            campaign_pack_id=pack.id,
            version_number=next_version,
            brief_json=brief_json,
            change_note=change_note,
            created_by_user_id=user_id,
        )
        self._session.add(version)
        await self._session.flush()
        pack.current_version_id = version.id
        await self._session.flush()
        return version


class SyncCampaignPackRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_version_with_pack(
        self, workspace_id: UUID, version_id: UUID
    ) -> tuple[CampaignPackVersionModel, CampaignPackModel] | None:
        row = self._session.execute(
            select(CampaignPackVersionModel, CampaignPackModel).where(
                CampaignPackVersionModel.id == version_id,
                CampaignPackVersionModel.campaign_pack_id == CampaignPackModel.id,
                CampaignPackModel.workspace_id == workspace_id,
                CampaignPackModel.deleted_at.is_(None),
            )
        ).one_or_none()
        return row
