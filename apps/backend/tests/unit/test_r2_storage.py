from __future__ import annotations

import io
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from urllib.parse import parse_qs, urlsplit

import pytest
from botocore.exceptions import ClientError
from pydantic import SecretStr, ValidationError

from viraldy.modules.smart_remake.repair_media import RepairMediaStore
from viraldy.platform.config.settings import AuthMode, Settings
from viraldy.platform.storage.s3 import S3StorageAdapter
from viraldy.shared.errors.base import AppError


def settings(**overrides):
    return SimpleNamespace(
        s3_endpoint_url="http://localhost:19000",
        s3_region="us-east-1",
        s3_bucket="legacy",
        s3_access_key_id=SecretStr("test-access"),
        s3_secret_access_key=SecretStr("test-secret"),
        s3_force_path_style=True,
        s3_presigned_expiry_seconds=300,
        r2_configured=True,
        r2_account_id="a" * 32,
        r2_access_key_id=SecretStr("r2-test-access"),
        r2_secret_access_key=SecretStr("r2-test-secret"),
        r2_bucket="smart-remake-private",
        **overrides,
    )


def test_upload_and_download_use_r2_sigv4_without_public_bucket():
    adapter = S3StorageAdapter(settings())
    key = "workspaces/owned/assets/video/source/__r2__/object"
    upload = adapter.create_presigned_upload(key, "video/mp4")
    parsed = urlsplit(upload.url)
    query = parse_qs(parsed.query)
    assert parsed.hostname == f"{'a' * 32}.r2.cloudflarestorage.com"
    assert parsed.path == f"/smart-remake-private/{key}"
    assert query["X-Amz-Algorithm"] == ["AWS4-HMAC-SHA256"]
    assert "/auto/s3/aws4_request" in query["X-Amz-Credential"][0]
    assert query["X-Amz-Expires"] == ["300"]
    assert "content-type" in query["X-Amz-SignedHeaders"][0]
    assert upload.required_headers == {"Content-Type": "video/mp4"}
    download = parse_qs(
        urlsplit(adapter.create_presigned_download(key, filename='video"\r\n.mp4')).query
    )
    assert download["response-content-disposition"] == ['attachment; filename="video___.mp4"']
    assert "response-content-disposition" not in parse_qs(
        urlsplit(adapter.create_presigned_download(key)).query
    )


def test_legacy_keys_still_use_original_storage_with_sigv4():
    adapter = S3StorageAdapter(settings())
    url = urlsplit(adapter.create_presigned_download("workspaces/legacy/video"))
    assert url.hostname == "localhost"
    assert url.path == "/legacy/workspaces/legacy/video"
    assert parse_qs(url.query)["X-Amz-Algorithm"] == ["AWS4-HMAC-SHA256"]


def test_smart_remake_upload_signature_binds_declared_content_length():
    adapter = S3StorageAdapter(settings())
    upload = adapter.create_presigned_upload(
        "workspaces/owned/input/__r2__/video", "video/mp4", content_length=2268
    )
    query = parse_qs(urlsplit(upload.url).query)
    assert "content-length" in query["X-Amz-SignedHeaders"][0]
    # The browser sets Content-Length from the File body; JS must not set it.
    assert upload.required_headers == {"Content-Type": "video/mp4"}


def test_r2_keys_fail_closed_when_private_r2_configuration_is_missing():
    config = settings()
    config.r2_configured = False
    adapter = S3StorageAdapter(config)
    with pytest.raises(AppError, match="R2"):
        adapter.create_presigned_download("workspaces/owned/video/__r2__/object")


async def test_smart_remake_new_media_is_prefixed_but_existing_keys_remain_readable(tmp_path):
    class Storage:
        smart_remake_r2_enabled = True

        def __init__(self):
            self.objects = {"workspaces/old/input": b"legacy"}

        def upload_file(self, source, key, mime):
            self.objects[key] = Path(source).read_bytes()

        def download_object(self, key, target):
            Path(target).write_bytes(self.objects[key])

    storage = Storage()
    media = RepairMediaStore(storage)
    key = await media.put("workspaces/owned/smart-remake/project", b"new", "video/mp4")
    assert key.startswith("workspaces/owned/smart-remake/project/__r2__/")
    assert await media.read(key) == b"new"
    assert await media.read("workspaces/old/input") == b"legacy"


def test_r2_settings_accept_legacy_account_id_and_do_not_require_public_url(monkeypatch):
    for key in (
        "R2_ACCOUNT_ID",
        "ACCOUNT_ID",
        "R2_ACCESS_KEY_ID",
        "R2_SECRET_ACCESS_KEY",
        "R2_BUCKET",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("ACCOUNT_ID", "a" * 32)
    config = Settings(
        _env_file=None,
        auth_mode=AuthMode.LOCAL_TEST,
        r2_access_key_id="access",
        r2_secret_access_key=SecretStr("test-secret"),
        r2_bucket="private",
    )
    assert config.r2_configured is True
    assert config.r2_account_id == "a" * 32
    assert Settings(_env_file=None, auth_mode=AuthMode.LOCAL_TEST).r2_configured is False


@pytest.mark.parametrize("ttl", [0, 604801])
def test_presigned_expiry_must_be_supported_by_r2(ttl):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, auth_mode=AuthMode.LOCAL_TEST, s3_presigned_expiry_seconds=ttl)


def test_bounded_r2_reads_limit_stream_and_close_body():
    adapter = S3StorageAdapter(settings())
    body = io.BytesIO(b"0123456789")
    client = Mock()
    client.get_object.return_value = {"Body": body}
    adapter._r2_client = client
    key = "workspaces/owned/input/__r2__/video"
    assert adapter.read_object_bytes(key, 5) == b"012345"
    assert body.closed
    client.get_object.assert_called_once_with(
        Bucket="smart-remake-private", Key=key, Range="bytes=0-5"
    )
    assert adapter._client is None


def test_r2_metadata_transfer_and_delete_use_the_configured_private_bucket():
    adapter = S3StorageAdapter(settings())
    client = Mock()
    adapter._r2_client = client
    key = "workspaces/owned/input/__r2__/video"
    client.head_object.return_value = {"ContentLength": 4, "ContentType": "video/mp4"}
    assert adapter.object_exists(key)
    assert adapter.get_object_metadata(key).size_bytes == 4
    adapter.download_object(key, "target")
    client.download_file.assert_called_once_with("smart-remake-private", key, "target")
    adapter.upload_file("source", key, "video/mp4")
    client.upload_file.assert_called_once_with(
        "source", "smart-remake-private", key, ExtraArgs={"ContentType": "video/mp4"}
    )
    adapter.delete_object(key)
    client.delete_object.assert_called_once_with(Bucket="smart-remake-private", Key=key)
    client.head_object.side_effect = ClientError(
        {"ResponseMetadata": {"HTTPStatusCode": 404}}, "HeadObject"
    )
    assert adapter.object_exists(key) is False
    client.head_object.side_effect = ClientError(
        {"ResponseMetadata": {"HTTPStatusCode": 403}}, "HeadObject"
    )
    with pytest.raises(ClientError):
        adapter.object_exists(key)


def test_workspace_inventory_lists_both_stores_without_unrelated_r2_objects():
    adapter = S3StorageAdapter(settings())
    adapter._client, adapter._r2_client = Mock(), Mock()
    now = datetime.now(UTC)
    legacy = "workspaces/owned/legacy"
    private = "workspaces/owned/project/__r2__/video"
    adapter._client.get_paginator.return_value.paginate.return_value = [
        {"Contents": [{"Key": legacy, "LastModified": now, "Size": 4}]}
    ]
    adapter._r2_client.get_paginator.return_value.paginate.return_value = [
        {
            "Contents": [
                {"Key": private, "LastModified": now, "Size": 8},
                {"Key": "workspaces/owned/unrelated-public", "LastModified": now, "Size": 1},
            ]
        }
    ]
    assert {item.key for item in adapter.list_objects("workspaces/owned/")} == {legacy, private}
