"""Only scoped Smart Remake uploads can create and complete R2 sessions."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from pydantic import ValidationError

from viraldy.modules.smart_remake.asset_uploads import (
    SmartRemakeUploadRequest,
    complete_upload,
    create_upload_session,
)
from viraldy.platform.storage.keys import asset_source_key
from viraldy.platform.storage.ports import ObjectMetadata, PresignedUpload
from viraldy.shared.errors.base import AppError


@pytest.fixture
def upload():
    workspace, actor, asset_id, version_id = uuid4(), uuid4(), uuid4(), uuid4()
    version = SimpleNamespace(
        id=version_id,
        asset_id=asset_id,
        version_number=1,
        storage_key=f"{asset_source_key(workspace, asset_id, version_id)}/__r2__/{version_id.hex}",
        size_bytes=100,
        declared_mime_type="video/mp4",
        detected_mime_type=None,
    )
    asset = SimpleNamespace(
        id=asset_id,
        workspace_id=workspace,
        library_scope="WORKSPACE",
        created_by_user_id=actor,
        deleted_at=None,
        metadata_json={"smartRemakeUploadRole": "reference_video"},
    )
    assets = SimpleNamespace(
        create_pending_upload=AsyncMock(return_value=(asset, version)),
        get=AsyncMock(return_value=asset),
        get_current_version=AsyncMock(return_value=version),
    )
    signed = PresignedUpload(
        "https://r2.example.test/signed-put",
        "PUT",
        {"Content-Type": "video/mp4"},
        datetime.now(UTC) + timedelta(minutes=10),
    )
    storage = SimpleNamespace(
        create_presigned_upload=Mock(return_value=signed),
        get_object_metadata=Mock(return_value=ObjectMetadata(100, "video/mp4")),
    )
    return SimpleNamespace(
        workspace=workspace,
        actor=actor,
        asset=asset,
        version=version,
        assets=assets,
        storage=storage,
        settings=SimpleNamespace(r2_configured=True),
        db=SimpleNamespace(commit=AsyncMock()),
        service=SimpleNamespace(
            complete_upload=AsyncMock(return_value=SimpleNamespace(id=asset_id))
        ),
        request=SmartRemakeUploadRequest(
            filename="source.mp4",
            declared_mime_type="video/mp4",
            declared_size_bytes=100,
            role="reference_video",
        ),
    )


async def begin(upload):
    return await create_upload_session(
        upload.db,
        upload.assets,
        upload.storage,
        upload.settings,
        upload.workspace,
        upload.actor,
        upload.request,
    )


async def finish(upload):
    return await complete_upload(
        upload.assets,
        upload.storage,
        upload.service,
        upload.settings,
        upload.workspace,
        upload.asset.id,
        upload.actor,
    )


async def test_session_persists_server_owned_r2_key_and_role(upload):
    response = await begin(upload)
    arguments = upload.assets.create_pending_upload.await_args.kwargs
    owned_prefix = asset_source_key(
        upload.workspace, arguments["asset_id"], arguments["version_id"]
    )
    assert arguments["storage_key"] == f"{owned_prefix}/__r2__/{arguments['version_id'].hex}"
    assert arguments["workspace_id"] == upload.workspace
    assert arguments["created_by_user_id"] == upload.actor
    assert arguments["asset_type"] == "reference"
    assert upload.asset.metadata_json["smartRemakeUploadRole"] == "reference_video"
    assert (
        upload.asset.metadata_json["smartRemakeUploadExpiresAt"] == response.expires_at.isoformat()
    )
    assert upload.storage.create_presigned_upload.call_args.kwargs == {"content_length": 100}
    assert response.upload_url == "https://r2.example.test/signed-put"
    assert response.asset_version_id == arguments["version_id"]
    upload.db.commit.assert_awaited_once()


@pytest.mark.parametrize("role", ["product_image", "character_image"])
async def test_image_sessions_use_product_asset_type(upload, role):
    upload.request = SmartRemakeUploadRequest(
        filename="image.png", declared_mime_type="image/png", declared_size_bytes=100, role=role
    )
    await begin(upload)
    assert upload.assets.create_pending_upload.await_args.kwargs["asset_type"] == "product_media"
    assert upload.asset.metadata_json["smartRemakeUploadRole"] == role


@pytest.mark.parametrize("operation", [begin, finish])
async def test_r2_must_be_configured_before_database_or_storage_access(upload, operation):
    upload.settings.r2_configured = False
    with pytest.raises(AppError) as error:
        await operation(upload)
    assert error.value.code == "SMART_REMAKE_R2_NOT_CONFIGURED"
    upload.assets.create_pending_upload.assert_not_awaited()
    upload.assets.get.assert_not_awaited()
    upload.storage.create_presigned_upload.assert_not_called()


@pytest.mark.parametrize("case", ["mime", "size"])
async def test_session_rejects_wrong_role_or_oversize_before_persisting(upload, monkeypatch, case):
    if case == "mime":
        upload.request.declared_mime_type = "image/png"
    else:
        monkeypatch.setenv("SMART_REMAKE_MAX_REFERENCE_VIDEO_BYTES", "99")
    with pytest.raises(AppError):
        await begin(upload)
    upload.assets.create_pending_upload.assert_not_awaited()


async def test_complete_delegates_only_after_owned_r2_upload_validation(upload):
    assert (await finish(upload)).id == upload.asset.id
    upload.storage.get_object_metadata.assert_called_once_with(upload.version.storage_key)
    upload.service.complete_upload.assert_awaited_once_with(
        upload.workspace, upload.asset.id, upload.actor
    )


@pytest.mark.parametrize(
    "case",
    ["missing", "foreign", "market", "unowned", "deleted", "origin", "legacy_key", "foreign_key"],
)
async def test_complete_never_reads_unowned_or_non_smart_remake_objects(upload, case):
    if case == "missing":
        upload.assets.get.return_value = None
    elif case == "foreign":
        upload.asset.workspace_id = uuid4()
    elif case == "market":
        upload.asset.library_scope = "MARKET"
    elif case == "unowned":
        upload.asset.created_by_user_id = None
    elif case == "deleted":
        upload.asset.deleted_at = datetime.now(UTC)
    elif case == "origin":
        upload.asset.metadata_json = {}
    elif case == "legacy_key":
        upload.version.storage_key = asset_source_key(
            upload.workspace, upload.asset.id, upload.version.id
        )
    else:
        upload.version.storage_key = (
            f"{asset_source_key(uuid4(), upload.asset.id, upload.version.id)}/__r2__/foreign"
        )
    with pytest.raises(AppError) as error:
        await finish(upload)
    assert error.value.status_code == 404
    upload.storage.get_object_metadata.assert_not_called()
    upload.service.complete_upload.assert_not_awaited()


@pytest.mark.parametrize("case", ["object_mime", "object_size", "version_size"])
async def test_complete_rechecks_role_type_and_size_before_upload_completion(
    upload, monkeypatch, case
):
    if case == "object_mime":
        upload.storage.get_object_metadata.return_value = ObjectMetadata(100, "image/png")
    elif case == "object_size":
        upload.storage.get_object_metadata.return_value = ObjectMetadata(101, "video/mp4")
    else:
        monkeypatch.setenv("SMART_REMAKE_MAX_REFERENCE_VIDEO_BYTES", "99")
    with pytest.raises(AppError):
        await finish(upload)
    upload.service.complete_upload.assert_not_awaited()


def test_session_wire_rejects_storage_keys_and_invalid_roles(upload):
    for update in ({"storage_key": "r2/foreign"}, {"role": "other"}):
        with pytest.raises(ValidationError):
            SmartRemakeUploadRequest.model_validate({**upload.request.model_dump(), **update})
