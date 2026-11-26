from __future__ import annotations

import hashlib
from typing import cast
from unittest.mock import Mock
from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy.orm import Session

from viraldy.modules.assets.models import AssetVersionModel
from viraldy.modules.jobs.models import ProcessingJobModel
from viraldy.modules.jobs.repository import WorkerJobRepository
from viraldy.platform.config.settings import Settings
from viraldy.shared.errors.base import AppError
from viraldy.worker.tasks import process_asset as worker


@pytest.fixture
def import_context(monkeypatch: pytest.MonkeyPatch) -> tuple[ProcessingJobModel, Mock, Mock]:
    asset_id, version_id = uuid4(), uuid4()
    job = ProcessingJobModel(
        workspace_id=uuid4(),
        input_json={
            "asset_id": str(asset_id),
            "asset_version_id": str(version_id),
            "source_record_id": str(uuid4()),
            "source_url": "https://v77.tiktokcdn.com/video.mp4",
            "media_type": "video",
        },
    )
    session = Mock(spec=Session)
    session.get.return_value = AssetVersionModel(
        id=version_id, asset_id=asset_id, storage_key="market/video.mp4"
    )
    monkeypatch.setattr(
        worker,
        "get_settings",
        lambda: Settings(
            _env_file=None, ai_mode="fixture", tiktok_commercial_media_persistence_allowed=True
        ),
    )
    assets = Mock()
    monkeypatch.setattr(worker, "SyncAssetRepository", Mock(return_value=assets))
    sources = Mock()
    sources.get_source_record.return_value = None
    monkeypatch.setattr(worker, "SyncTikTokCommercialRepository", Mock(return_value=sources))
    monkeypatch.setattr(worker, "S3StorageAdapter", Mock())
    return job, session, assets


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/private",
        "https://127.0.0.1/private",
        "https://tiktokcdn.com.attacker.example/video.mp4",
        "http://v77.tiktokcdn.com/video.mp4",
    ],
)
def test_media_import_rejects_untrusted_hosts_before_network(
    import_context: tuple[ProcessingJobModel, Mock, Mock],
    monkeypatch: pytest.MonkeyPatch,
    url: str,
) -> None:
    job, session, _ = import_context
    job.input_json = {**job.input_json, "source_url": url}
    stream = Mock(side_effect=AssertionError("Unexpected outbound HTTP"))
    monkeypatch.setattr(worker.httpx, "stream", stream)

    with pytest.raises(AppError) as error:
        worker._import_tiktok_media(job, Mock(spec=WorkerJobRepository), cast(Session, session))

    assert error.value.code == "TIKTOK_MEDIA_HOST_NOT_ALLOWED"
    stream.assert_not_called()


@pytest.mark.parametrize("missing", [True, False])
def test_media_import_rejects_missing_or_mismatched_version_before_network(
    import_context: tuple[ProcessingJobModel, Mock, Mock],
    monkeypatch: pytest.MonkeyPatch,
    missing: bool,
) -> None:
    job, session, _ = import_context
    session.get.return_value = (
        None if missing else AssetVersionModel(asset_id=uuid4(), storage_key="other/video.mp4")
    )
    stream = Mock(side_effect=AssertionError("Unexpected outbound HTTP"))
    monkeypatch.setattr(worker.httpx, "stream", stream)

    with pytest.raises(AppError) as error:
        worker._import_tiktok_media(job, Mock(spec=WorkerJobRepository), cast(Session, session))

    assert error.value.code == "ASSET_NOT_FOUND"
    stream.assert_not_called()


@pytest.mark.parametrize("redirect", [False, True])
def test_media_import_downloads_only_the_validated_provider_url(
    import_context: tuple[ProcessingJobModel, Mock, Mock],
    monkeypatch: pytest.MonkeyPatch,
    redirect: bool,
) -> None:
    job, session, assets = import_context
    hosts: list[str] = []

    def respond(request: httpx.Request) -> httpx.Response:
        hosts.append(request.url.host)
        if redirect and request.url.host == "v77.tiktokcdn.com":
            return httpx.Response(302, headers={"location": "http://127.0.0.1/private"})
        return httpx.Response(200, content=b"video", headers={"content-type": "video/mp4"})

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        monkeypatch.setattr(worker.httpx, "stream", client.stream)
        if redirect:
            with pytest.raises(AppError) as error:
                worker._import_tiktok_media(
                    job, Mock(spec=WorkerJobRepository), cast(Session, session)
                )
            assert error.value.code == "TIKTOK_MEDIA_DOWNLOAD_FAILED"
            assets.complete_remote_import.assert_not_called()
        else:
            output = worker._import_tiktok_media(
                job, Mock(spec=WorkerJobRepository), cast(Session, session)
            )
            assert output["size_bytes"] == len(b"video")
            assert assets.complete_remote_import.call_args.kwargs["checksum_sha256"] == (
                hashlib.sha256(b"video").hexdigest()
            )
            session.get.assert_called_once_with(
                AssetVersionModel, UUID(str(job.input_json["asset_version_id"]))
            )

    assert hosts == ["v77.tiktokcdn.com"]
