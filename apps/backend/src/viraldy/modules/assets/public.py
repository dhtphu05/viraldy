from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from viraldy.modules.assets.models import AssetModel, AssetVersionModel
from viraldy.modules.assets.repository import AssetRepository
from viraldy.modules.assets.service import AssetService

__all__ = [
    "AssetModel",
    "AssetRepository",
    "AssetService",
    "AssetVersionModel",
    "AssetVersionReference",
    "AssetQueries",
    "AssetVersionSnapshot",
    "SyncAssetQueries",
]


@dataclass(frozen=True, slots=True)
class AssetVersionSnapshot:
    asset_id: UUID
    asset_version_id: UUID
    workspace_id: UUID
    product_id: UUID | None
    storage_key: str
    original_filename: str
    declared_mime_type: str
    detected_mime_type: str | None
    size_bytes: int
    checksum_sha256: str | None
    metadata_json: dict[str, object]


@dataclass(frozen=True, slots=True)
class AssetVersionReference:
    asset_id: UUID
    asset_version_id: UUID
    workspace_id: UUID
    product_id: UUID | None
    original_filename: str
    checksum_sha256: str | None
    validation_status: str


class AssetQueries:
    def __init__(self, session: AsyncSession) -> None:
        self._repository = AssetRepository(session)

    async def get_version_reference(
        self,
        workspace_id: UUID,
        asset_version_id: UUID,
    ) -> AssetVersionReference | None:
        result = await self._repository.get_version_by_id_in_workspace(
            workspace_id,
            asset_version_id,
        )
        if result is None:
            return None
        asset, version = result
        return AssetVersionReference(
            asset_id=asset.id,
            asset_version_id=version.id,
            workspace_id=asset.workspace_id,
            product_id=asset.product_id,
            original_filename=version.original_filename,
            checksum_sha256=version.checksum_sha256,
            validation_status=version.validation_status,
        )


class SyncAssetQueries:
    def __init__(self, session: Session) -> None:
        self._session = session

    def load_asset_version(
        self,
        asset_id: UUID,
        version_id: UUID,
    ) -> AssetVersionSnapshot | None:
        result = self._session.execute(
            select(AssetModel, AssetVersionModel).where(
                AssetModel.id == asset_id,
                AssetVersionModel.id == version_id,
                AssetVersionModel.asset_id == AssetModel.id,
            )
        )
        row = result.one_or_none()
        if row is None:
            return None

        asset, version = row
        return AssetVersionSnapshot(
            asset_id=asset.id,
            asset_version_id=version.id,
            workspace_id=asset.workspace_id,
            product_id=asset.product_id,
            storage_key=version.storage_key,
            original_filename=version.original_filename,
            declared_mime_type=version.declared_mime_type,
            detected_mime_type=version.detected_mime_type,
            size_bytes=version.size_bytes,
            checksum_sha256=version.checksum_sha256,
            metadata_json=version.metadata_json,
        )

    def get_current_version_for_asset(
        self, workspace_id: UUID, asset_id: UUID
    ) -> AssetVersionSnapshot | None:
        result = self._session.execute(
            select(AssetModel, AssetVersionModel).where(
                AssetModel.workspace_id == workspace_id,
                AssetModel.id == asset_id,
                AssetModel.current_version_id == AssetVersionModel.id,
                AssetVersionModel.asset_id == AssetModel.id,
            )
        )
        row = result.one_or_none()
        if row is None:
            return None
        asset, version = row
        return AssetVersionSnapshot(
            asset_id=asset.id,
            asset_version_id=version.id,
            workspace_id=asset.workspace_id,
            product_id=asset.product_id,
            storage_key=version.storage_key,
            original_filename=version.original_filename,
            declared_mime_type=version.declared_mime_type,
            detected_mime_type=version.detected_mime_type,
            size_bytes=version.size_bytes,
            checksum_sha256=version.checksum_sha256,
            metadata_json=version.metadata_json,
        )
