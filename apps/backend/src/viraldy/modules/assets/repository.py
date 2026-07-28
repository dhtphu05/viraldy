from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from viraldy.modules.assets.models import AssetModel, AssetVersionModel


class AssetRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_pending_upload(
        self,
        workspace_id: UUID,
        product_id: UUID | None,
        asset_type: str,
        filename: str,
        declared_mime_type: str,
        declared_size_bytes: int,
        storage_key: str,
        created_by_user_id: UUID,
        asset_id: UUID,
        version_id: UUID,
    ) -> tuple[AssetModel, AssetVersionModel]:
        asset = AssetModel(
            id=asset_id,
            workspace_id=workspace_id,
            product_id=product_id,
            asset_type=asset_type,
            status="pending_upload",
            current_version_id=version_id,
            created_by_user_id=created_by_user_id,
            metadata_json={},
        )
        version = AssetVersionModel(
            id=version_id,
            asset_id=asset_id,
            version_number=1,
            storage_key=storage_key,
            original_filename=filename,
            declared_mime_type=declared_mime_type,
            size_bytes=declared_size_bytes,
            metadata_json={},
            validation_status="pending",
        )
        self._session.add_all([asset, version])
        await self._session.flush()
        return asset, version

    async def list_assets(self, workspace_id: UUID) -> list[AssetModel]:
        result = await self._session.execute(
            select(AssetModel)
            .where(AssetModel.workspace_id == workspace_id, AssetModel.deleted_at.is_(None))
            .order_by(AssetModel.created_at.desc())
        )
        return list(result.scalars())

    async def get(self, workspace_id: UUID, asset_id: UUID) -> AssetModel | None:
        result = await self._session.execute(
            select(AssetModel).where(
                AssetModel.workspace_id == workspace_id,
                AssetModel.id == asset_id,
                AssetModel.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_current_version(self, asset_id: UUID) -> AssetVersionModel | None:
        result = await self._session.execute(
            select(AssetVersionModel)
            .join(AssetModel, AssetModel.current_version_id == AssetVersionModel.id)
            .where(AssetModel.id == asset_id)
        )
        return result.scalar_one_or_none()

    async def mark_uploaded(
        self,
        workspace_id: UUID,
        asset_id: UUID,
        size_bytes: int,
        detected_mime_type: str | None,
        checksum_sha256: str | None,
    ) -> tuple[AssetModel, AssetVersionModel] | None:
        result = await self._session.execute(
            select(AssetModel, AssetVersionModel)
            .join(AssetVersionModel, AssetModel.current_version_id == AssetVersionModel.id)
            .where(
                AssetModel.workspace_id == workspace_id,
                AssetModel.id == asset_id,
                AssetModel.deleted_at.is_(None),
            )
        )
        row = result.one_or_none()
        if row is None:
            return None

        asset, version = row
        asset.status = "uploaded"
        version.detected_mime_type = detected_mime_type
        version.checksum_sha256 = checksum_sha256
        version.validation_status = "uploaded"
        version.size_bytes = size_bytes
        await self._session.flush()
        return asset, version
