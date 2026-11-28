"""Direct-upload intake preserves ownership, media limits and canonical replay."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from pydantic import ValidationError

from tests.unit.test_smart_remake_rights import (
    MemoryRepository,
    image_upload,
    intake_payload,
    source_upload,
)
from viraldy.modules.smart_remake.asset_intake import (
    SmartRemakeAssetIntakeRequest,
    create_intake_from_assets,
)
from viraldy.modules.smart_remake.project_intake import create_intake
from viraldy.modules.smart_remake.repair_media import RepairMediaStore
from viraldy.platform.storage.ports import ObjectMetadata
from viraldy.shared.errors.base import AppError


class AssetStorage:
    def __init__(self):
        self.objects = {}
        self.metadata = {}
        self.reads = []
        self.downloads = []
        self.bounded_reads = []

    def get_object_metadata(self, key):
        self.reads.append(key)
        return self.metadata[key]

    def download_object(self, key, destination):
        raise AssertionError("Intake must use a bounded object read.")

    def read_object_bytes(self, key, maximum_bytes):
        self.downloads.append(key)
        self.bounded_reads.append((key, maximum_bytes))
        return self.objects[key][: maximum_bytes + 1]

    def upload_file(self, source, key, content_type):
        self.objects[key] = Path(source).read_bytes()
        self.metadata[key] = ObjectMetadata(len(self.objects[key]), content_type)

    def delete_object(self, key):
        self.objects.pop(key, None)


@pytest.fixture
def assets():
    workspace, actor = uuid4(), uuid4()
    storage = AssetStorage()
    rows = {}
    ids = {}
    for role, upload in (("source", source_upload()), ("product", image_upload())):
        asset_id, version_id = uuid4(), uuid4()
        ids[role] = version_id
        key = f"workspaces/{workspace}/assets/{asset_id}/{version_id}"
        asset = SimpleNamespace(
            id=asset_id,
            workspace_id=workspace,
            library_scope="WORKSPACE",
            created_by_user_id=actor,
            deleted_at=None,
            status="uploaded",
        )
        version = SimpleNamespace(
            id=version_id,
            asset_id=asset_id,
            storage_key=key,
            validation_status="uploaded",
            size_bytes=len(upload.bytes),
            declared_mime_type=upload.mime_type,
            detected_mime_type=upload.mime_type,
            original_filename=f"{role}.media",
            checksum_sha256=None,
        )
        rows[version_id] = asset, version
        storage.objects[key] = upload.bytes
        storage.metadata[key] = ObjectMetadata(len(upload.bytes), upload.mime_type)
    repository = SimpleNamespace(
        get_version_by_id_in_workspace=AsyncMock(side_effect=lambda ws, vid: rows.get(vid))
    )
    return SimpleNamespace(
        workspace=workspace,
        actor=actor,
        storage=storage,
        rows=rows,
        ids=ids,
        assets=repository,
        projects=MemoryRepository(),
        media=RepairMediaStore(storage),
        payload=SmartRemakeAssetIntakeRequest(
            metadata=intake_payload(),
            sourceAssetVersionId=ids["source"],
            productAssetVersionId=ids["product"],
        ),
    )


async def ingest(assets):
    return await create_intake_from_assets(
        assets.assets,
        assets.projects,
        assets.media,
        assets.workspace,
        assets.actor,
        assets.payload,
    )


async def test_completed_assets_become_owned_project_inputs_and_replay_multipart(assets):
    row = await ingest(assets)
    assert row.context_json["p0"]["actorId"] == str(assets.actor)
    assert assets.storage.downloads == [
        assets.rows[assets.ids[role]][1].storage_key for role in ("source", "product")
    ]
    assert row.context_json["sourceKey"] != assets.rows[assets.ids["source"]][1].storage_key
    assert assets.storage.objects[row.context_json["productKey"]] == image_upload().bytes
    replay = await create_intake(
        assets.projects,
        assets.media,
        assets.workspace,
        assets.actor,
        assets.payload.metadata,
        source_upload(),
        image_upload(),
    )
    assert replay.id == row.id
    assert len(assets.projects.rows) == 1
    assert len(assets.storage.objects) == 4


async def test_source_is_read_with_a_network_size_bound(assets, monkeypatch):
    monkeypatch.setenv("SMART_REMAKE_MAX_REFERENCE_VIDEO_BYTES", "64")
    await ingest(assets)
    assert assets.storage.bounded_reads[0] == (assets.rows[assets.ids["source"]][1].storage_key, 64)


async def test_reused_upload_cannot_change_bytes_with_a_persisted_checksum(assets):
    version = assets.rows[assets.ids["source"]][1]
    data = assets.storage.objects[version.storage_key]
    version.checksum_sha256 = hashlib.sha256(data).hexdigest()
    assets.storage.objects[version.storage_key] = data[:-1] + b"!"
    with pytest.raises(AppError) as error:
        await ingest(assets)
    assert error.value.code == "SMART_REMAKE_INPUT_CHANGED"
    assert assets.projects.rows == {}


@pytest.mark.parametrize("status", ["uploaded", "processed"])
async def test_completed_and_processed_versions_are_accepted(assets, status):
    assets.rows[assets.ids["source"]][1].validation_status = status
    assert (await ingest(assets)).state_json["phase"] == "intake"


@pytest.mark.parametrize("case", ["missing", "foreign", "market", "public", "unowned", "deleted"])
async def test_unowned_asset_versions_never_read_storage(assets, case):
    asset, _ = assets.rows[assets.ids["product"]]
    if case == "missing":
        del assets.rows[assets.ids["product"]]
    elif case == "foreign":
        asset.workspace_id = uuid4()
    elif case == "market":
        asset.library_scope = "MARKET"
    elif case == "public":
        asset.workspace_id = None
    elif case == "unowned":
        asset.created_by_user_id = None
    else:
        asset.deleted_at = datetime.now(UTC)
    with pytest.raises(AppError) as error:
        await ingest(assets)
    assert error.value.status_code == 404
    assert assets.storage.reads == []
    assert assets.projects.rows == {}


@pytest.mark.parametrize("status", ["pending", "metadata_only", "failed"])
async def test_incomplete_versions_never_read_storage(assets, status):
    assets.rows[assets.ids["product"]][1].validation_status = status
    with pytest.raises(AppError) as error:
        await ingest(assets)
    assert error.value.code == "SMART_REMAKE_ASSET_NOT_READY"
    assert assets.storage.reads == []


@pytest.mark.parametrize("field", ["declared_mime_type", "detected_mime_type"])
async def test_wrong_role_mime_is_rejected_before_reads(assets, field):
    setattr(assets.rows[assets.ids["product"]][1], field, "video/mp4")
    with pytest.raises(AppError) as error:
        await ingest(assets)
    assert error.value.code == "UNSUPPORTED_SMART_REMAKE_MEDIA_TYPE"
    assert assets.storage.reads == []


@pytest.mark.parametrize("boundary", ["version", "object", "bytes"])
async def test_video_size_is_bounded_at_every_boundary(assets, monkeypatch, boundary):
    monkeypatch.setenv("SMART_REMAKE_MAX_REFERENCE_VIDEO_BYTES", "64")
    version = assets.rows[assets.ids["source"]][1]
    if boundary == "version":
        version.size_bytes = 65
    elif boundary == "object":
        assets.storage.metadata[version.storage_key] = ObjectMetadata(65, "video/mp4")
    else:
        assets.storage.objects[version.storage_key] = b"x" * 65
    with pytest.raises(AppError) as error:
        await ingest(assets)
    assert error.value.code == "SMART_REMAKE_UPLOAD_TOO_LARGE"
    assert error.value.status_code == 413
    assert assets.projects.rows == {}


async def test_image_size_is_bounded_before_reads(assets, monkeypatch):
    monkeypatch.setenv("SMART_REMAKE_MAX_PRODUCT_IMAGE_BYTES", "2")
    with pytest.raises(AppError) as error:
        await ingest(assets)
    assert error.value.status_code == 413
    assert assets.storage.reads == []


@pytest.mark.parametrize("boundary", ["object_mime", "object_size", "actual_size", "actual_image"])
async def test_overwritten_or_invalid_objects_are_not_retained(assets, boundary):
    version = assets.rows[assets.ids["product"]][1]
    if boundary == "object_mime":
        assets.storage.metadata[version.storage_key] = ObjectMetadata(
            version.size_bytes, "video/mp4"
        )
    elif boundary == "object_size":
        assets.storage.metadata[version.storage_key] = ObjectMetadata(
            version.size_bytes - 1, "image/png"
        )
    elif boundary == "actual_size":
        assets.storage.objects[version.storage_key] = b"short"
    else:
        assets.storage.objects[version.storage_key] = b"x" * version.size_bytes
    with pytest.raises(AppError):
        await ingest(assets)
    assert assets.projects.rows == {}


async def test_character_consent_and_reference_gates_precede_all_asset_reads(assets):
    assets.payload.metadata.requirements.requiresCharacter = True
    with pytest.raises(AppError) as error:
        await ingest(assets)
    assert error.value.code == "SMART_REMAKE_CHARACTER_REFERENCE_REQUIRED"
    assets.payload.characterAssetVersionId = uuid4()
    with pytest.raises(AppError) as error:
        await ingest(assets)
    assert error.value.code == "SMART_REMAKE_CHARACTER_CONSENT_REQUIRED"
    assets.assets.get_version_by_id_in_workspace.assert_not_awaited()
    assert assets.storage.reads == []


async def test_character_asset_is_retained_with_separate_consent(assets):
    from viraldy.modules.smart_remake.project_contracts import SmartRemakeCharacterConsent

    assets.payload.metadata.requirements.requiresCharacter = True
    assets.payload.metadata.rights.character = assets.payload.metadata.rights.product.model_copy()
    assets.payload.metadata.rights.characterConsent = SmartRemakeCharacterConsent(
        consented=True, scope="remake", evidenceNote="Character consent recorded."
    )
    assets.payload.characterAssetVersionId = assets.ids["product"]
    row = await ingest(assets)
    assert assets.storage.objects[row.context_json["characterKey"]] == image_upload().bytes
    assert set(row.context_json["p0"]["assets"]) == {"source", "product", "character"}


def test_asset_request_accepts_uuid_json_and_rejects_client_storage_keys(assets):
    wire = assets.payload.model_dump(mode="json")
    assert SmartRemakeAssetIntakeRequest.model_validate(wire) == assets.payload
    for field in ("sourceStorageKey", "sourceUrl", "actorId"):
        with pytest.raises(ValidationError):
            SmartRemakeAssetIntakeRequest.model_validate({**wire, field: "forged"})
