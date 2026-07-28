from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from viraldy.modules.assets.models import AssetModel, AssetVersionModel


@dataclass(frozen=True, slots=True)
class AssetVersionSnapshot:
    asset_id: UUID
    asset_version_id: UUID
    workspace_id: UUID
    storage_key: str
    size_bytes: int


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
            size_bytes=version.size_bytes,
        )
