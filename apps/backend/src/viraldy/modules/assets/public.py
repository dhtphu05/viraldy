from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from viraldy.modules.assets.models import AssetModel, AssetVersionModel
from viraldy.modules.assets.repository import AssetRepository

__all__ = [
    "AssetModel",
    "AssetRepository",
    "AssetVersionModel",
    "AssetVersionSnapshot",
    "SyncAssetQueries",
]


@dataclass(frozen=True, slots=True)
class AssetVersionSnapshot:
    asset_id: UUID
    asset_version_id: UUID
    workspace_id: UUID
    storage_key: str
    original_filename: str
    declared_mime_type: str
    detected_mime_type: str | None
    size_bytes: int
    checksum_sha256: str | None
    metadata_json: dict[str, object]


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
            storage_key=version.storage_key,
            original_filename=version.original_filename,
            declared_mime_type=version.declared_mime_type,
            detected_mime_type=version.detected_mime_type,
            size_bytes=version.size_bytes,
            checksum_sha256=version.checksum_sha256,
            metadata_json=version.metadata_json,
        )
