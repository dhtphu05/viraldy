from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
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
            current_version_id=None,
            created_by_user_id=created_by_user_id,
            metadata_json={},
        )
        self._session.add(asset)
        await self._session.flush()

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
        self._session.add(version)
        await self._session.flush()

        asset.current_version_id = version_id
        await self._session.flush()
        return asset, version

    async def list_assets(self, workspace_id: UUID) -> list[AssetModel]:
        result = await self._session.execute(
            select(AssetModel)
            .where(AssetModel.workspace_id == workspace_id, AssetModel.deleted_at.is_(None))
            .order_by(AssetModel.created_at.desc())
        )
        return list(result.scalars())

    async def create_pending_revision(
        self,
        *,
        workspace_id: UUID,
        asset_id: UUID,
        version_id: UUID,
        filename: str,
        declared_mime_type: str,
        declared_size_bytes: int,
        storage_key: str,
    ) -> AssetVersionModel | None:
        asset = await self._session.scalar(
            select(AssetModel)
            .where(
                AssetModel.workspace_id == workspace_id,
                AssetModel.id == asset_id,
                AssetModel.deleted_at.is_(None),
                AssetModel.status == "uploaded",
            )
            .with_for_update()
        )
        if asset is None:
            return None
        next_version = (
            int(
                await self._session.scalar(
                    select(func.coalesce(func.max(AssetVersionModel.version_number), 0)).where(
                        AssetVersionModel.asset_id == asset_id
                    )
                )
                or 0
            )
            + 1
        )
        version = AssetVersionModel(
            id=version_id,
            asset_id=asset_id,
            version_number=next_version,
            storage_key=storage_key,
            original_filename=filename,
            declared_mime_type=declared_mime_type,
            size_bytes=declared_size_bytes,
            metadata_json={},
            validation_status="pending",
        )
        self._session.add(version)
        await self._session.flush()
        return version

    async def get(self, workspace_id: UUID, asset_id: UUID) -> AssetModel | None:
        result = await self._session.execute(
            select(AssetModel).where(
                AssetModel.workspace_id == workspace_id,
                AssetModel.id == asset_id,
                AssetModel.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def list_versions(
        self,
        workspace_id: UUID,
        asset_id: UUID,
    ) -> list[tuple[AssetVersionModel, bool]]:
        result = await self._session.execute(
            select(AssetVersionModel, AssetModel.current_version_id == AssetVersionModel.id)
            .join(AssetModel, AssetModel.id == AssetVersionModel.asset_id)
            .where(
                AssetModel.workspace_id == workspace_id,
                AssetModel.id == asset_id,
                AssetModel.deleted_at.is_(None),
            )
            .order_by(AssetVersionModel.version_number.desc())
        )
        return [(version, bool(is_current)) for version, is_current in result]

    async def get_version_in_workspace(
        self,
        workspace_id: UUID,
        asset_id: UUID,
        version_id: UUID,
    ) -> AssetVersionModel | None:
        result = await self._session.execute(
            select(AssetVersionModel)
            .join(AssetModel, AssetModel.id == AssetVersionModel.asset_id)
            .where(
                AssetModel.workspace_id == workspace_id,
                AssetModel.id == asset_id,
                AssetModel.deleted_at.is_(None),
                AssetVersionModel.id == version_id,
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

    async def get_current_version_in_workspace(
        self, workspace_id: UUID, asset_id: UUID
    ) -> AssetVersionModel | None:
        result = await self._session.execute(
            select(AssetVersionModel)
            .join(AssetModel, AssetModel.current_version_id == AssetVersionModel.id)
            .where(
                AssetModel.workspace_id == workspace_id,
                AssetModel.id == asset_id,
                AssetModel.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def mark_uploaded(
        self,
        workspace_id: UUID,
        asset_id: UUID,
        size_bytes: int,
        detected_mime_type: str | None,
        checksum_sha256: str | None,
    ) -> tuple[AssetModel, AssetVersionModel, bool] | None:
        asset = await self._session.scalar(
            select(AssetModel)
            .where(
                AssetModel.workspace_id == workspace_id,
                AssetModel.id == asset_id,
                AssetModel.deleted_at.is_(None),
            )
            .with_for_update()
        )
        if asset is None or asset.current_version_id is None:
            return None
        version = await self._session.get(AssetVersionModel, asset.current_version_id)
        if version is None:
            return None
        newly_completed = version.validation_status != "uploaded"
        asset.status = "uploaded"
        version.detected_mime_type = detected_mime_type
        version.checksum_sha256 = checksum_sha256
        version.validation_status = "uploaded"
        version.size_bytes = size_bytes
        await self._session.flush()
        return asset, version, newly_completed

    async def mark_revision_uploaded(
        self,
        *,
        workspace_id: UUID,
        asset_id: UUID,
        version_id: UUID,
        size_bytes: int,
        detected_mime_type: str | None,
        checksum_sha256: str | None,
    ) -> tuple[AssetModel, AssetVersionModel, bool, bool] | None:
        asset = await self._session.scalar(
            select(AssetModel)
            .where(
                AssetModel.workspace_id == workspace_id,
                AssetModel.id == asset_id,
                AssetModel.deleted_at.is_(None),
            )
            .with_for_update()
        )
        if asset is None:
            return None
        version = await self._session.scalar(
            select(AssetVersionModel).where(
                AssetVersionModel.id == version_id,
                AssetVersionModel.asset_id == asset_id,
            )
        )
        if version is None:
            return None
        if version.version_number <= 1:
            return None

        newly_completed = version.validation_status != "uploaded"
        version.detected_mime_type = detected_mime_type
        version.checksum_sha256 = checksum_sha256
        version.validation_status = "uploaded"
        version.size_bytes = size_bytes

        current_version_number = await self._session.scalar(
            select(AssetVersionModel.version_number).where(
                AssetVersionModel.id == asset.current_version_id
            )
        )
        should_become_current = (
            current_version_number is None or version.version_number > current_version_number
        )
        if should_become_current:
            asset.current_version_id = version.id
            asset.status = "uploaded"
        is_current = asset.current_version_id == version.id
        await self._session.flush()
        return asset, version, is_current, newly_completed
