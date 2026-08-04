from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import cast
from uuid import UUID, uuid4

import pytest

from viraldy.modules.assets.service import AssetService
from viraldy.platform.storage.ports import StoragePort
from viraldy.shared.errors.base import NotFoundError


class _PlaybackRepository:
    def __init__(self, version: object | None) -> None:
        self.version = version

    async def get_version_in_workspace(
        self,
        workspace_id: UUID,
        asset_id: UUID,
        version_id: UUID,
    ) -> object | None:
        _ = (workspace_id, asset_id, version_id)
        return self.version


class _PlaybackStorage:
    def create_presigned_download(self, key: str) -> str:
        assert key == "private/workspace/revision.mp4"
        return "https://video.example.test/presigned"


def _service(version: object | None) -> AssetService:
    service = cast(AssetService, AssetService.__new__(AssetService))
    service._repository = _PlaybackRepository(version)  # type: ignore[assignment]
    service._storage = cast(StoragePort, _PlaybackStorage())
    service._settings = SimpleNamespace(s3_presigned_expiry_seconds=900)  # type: ignore[assignment]
    return service


async def test_historical_asset_version_playback_returns_only_presigned_access() -> None:
    asset_id = uuid4()
    version_id = uuid4()
    version = SimpleNamespace(
        id=version_id,
        asset_id=asset_id,
        storage_key="private/workspace/revision.mp4",
        validation_status="uploaded",
    )

    before = datetime.now(UTC)
    response = await _service(version).get_version_playback(uuid4(), asset_id, version_id)

    assert response.asset_id == asset_id
    assert response.asset_version_id == version_id
    assert response.video_url == "https://video.example.test/presigned"
    assert response.expires_at > before
    assert "storage_key" not in response.model_dump()


async def test_historical_asset_version_playback_is_workspace_scoped() -> None:
    with pytest.raises(NotFoundError) as error:
        await _service(None).get_version_playback(uuid4(), uuid4(), uuid4())

    assert error.value.code == "ASSET_VERSION_NOT_FOUND"
