"""Uploaded product angles remain owned, hash-bound and visible in the intake."""

import copy
import hashlib
from io import BytesIO
from uuid import UUID, uuid4

import pytest
from PIL import Image
from pydantic import ValidationError

from tests.unit.test_smart_remake_asset_intake import assets, ingest  # noqa: F401
from tests.unit.test_smart_remake_rights import (
    MemoryMedia,
    MemoryRepository,
    image_upload,
    intake_payload,
    source_upload,
)
from viraldy.modules.smart_remake.asset_intake import SmartRemakeAssetIntakeRequest
from viraldy.modules.smart_remake.engine.schemas import UploadedMedia
from viraldy.modules.smart_remake.product_references import (
    MAX_PRODUCT_REFERENCE_IMAGES,
    product_reference_assets,
    read_product_references,
)
from viraldy.modules.smart_remake.project_deletion import deletion_inventory
from viraldy.modules.smart_remake.project_intake import assert_input_binding, create_intake
from viraldy.modules.smart_remake.project_policy import constraints_hash, stable_hash
from viraldy.modules.smart_remake.project_presentation import project_policy_fields
from viraldy.modules.smart_remake.repair_service import RepairService
from viraldy.shared.errors.base import AppError


def other_angle(index=0):
    buffer = BytesIO()
    Image.new("RGB", (5, 5), (0, index, 255)).save(buffer, format="PNG")
    return UploadedMedia(bytes=buffer.getvalue(), mime_type="image/png")


async def intake_with_angles(*angles):
    repository, media, workspace, actor = MemoryRepository(), MemoryMedia(), uuid4(), uuid4()
    row = await create_intake(
        repository,
        media,
        workspace,
        actor,
        intake_payload(),
        source_upload(),
        image_upload(),
        additional_products=list(angles),
    )
    return row, repository, media, workspace


async def test_single_image_intake_keeps_exact_legacy_hash_serialization():
    row, _, _, _ = await intake_with_angles()
    hashes = {
        "source": hashlib.sha256(source_upload().bytes).hexdigest(),
        "product": hashlib.sha256(image_upload().bytes).hexdigest(),
    }
    assert row.context_json["p0"]["inputHash"] == stable_hash(hashes)
    assert row.context_json["p0"]["intakeRequestHash"] == stable_hash(
        {
            "request": intake_payload().model_dump(mode="json"),
            "inputs": hashes,
        }
    )
    assert "additionalProductReferences" not in row.context_json["p0"]


async def test_all_angles_are_private_owned_ordered_and_bound_without_extra_rights_roles():
    second = other_angle()
    row, _, media, workspace = await intake_with_angles(second)
    context = row.context_json
    refs = product_reference_assets(context)
    assert len(refs) == 2 and refs[0] == context["p0"]["assets"]["product"]
    assert set(context["p0"]["assets"]) == {"source", "product"}
    assert all(ref["role"] == "product" for ref in refs)
    assert all(ref["storageKey"].startswith(f"workspaces/{workspace}/") for ref in refs)
    assert [value.bytes for value in await read_product_references(context, media)] == [
        image_upload().bytes,
        second.bytes,
    ]
    await assert_input_binding(row, media)
    public = project_policy_fields(context)
    assert public["inputMediaHashes"]["additionalProducts"] == [
        hashlib.sha256(second.bytes).hexdigest()
    ]
    assert "storageKey" not in str(public)


async def test_additional_angle_changes_intake_identity_and_replay_cannot_replace_it():
    row, repository, media, workspace = await intake_with_angles(other_angle())
    with pytest.raises(AppError, match="SMART_REMAKE_IDEMPOTENCY_CONFLICT"):
        await create_intake(
            repository,
            media,
            workspace,
            UUID(row.context_json["p0"]["actorId"]),
            intake_payload(),
            source_upload(),
            image_upload(),
            additional_products=[other_angle(1)],
        )


async def test_fourteen_product_images_fit_and_fifteen_are_rejected_before_retention():
    assert MAX_PRODUCT_REFERENCE_IMAGES == 14
    row, _, media, _ = await intake_with_angles(*[other_angle(index) for index in range(13)])
    assert len(await read_product_references(row.context_json, media)) == 14
    with pytest.raises(AppError, match="SMART_REMAKE_PRODUCT_REFERENCES_INVALID"):
        await intake_with_angles(*[other_angle(index) for index in range(14)])


def test_asset_intake_bounds_additional_ids_and_preserves_single_primary():
    with pytest.raises(ValidationError):
        SmartRemakeAssetIntakeRequest(
            metadata=intake_payload(),
            sourceAssetVersionId=uuid4(),
            productAssetVersionId=uuid4(),
            additionalProductAssetVersionIds=[uuid4() for _ in range(14)],
        )


async def test_asset_intake_retains_and_validates_additional_product_angles(assets):  # noqa: F811
    primary_asset, primary_version = assets.rows[assets.ids["product"]]
    extra_id = uuid4()
    extra_asset, extra_version = copy.deepcopy(primary_asset), copy.deepcopy(primary_version)
    extra_asset.id, extra_version.id = uuid4(), extra_id
    extra_version.storage_key += "/alternate"
    assets.rows[extra_id] = extra_asset, extra_version
    original_key = primary_version.storage_key
    assets.storage.objects[extra_version.storage_key] = other_angle().bytes
    extra_version.size_bytes = len(other_angle().bytes)
    metadata_type = type(assets.storage.metadata[original_key])
    assets.storage.metadata[extra_version.storage_key] = metadata_type(
        extra_version.size_bytes,
        "image/png",
    )
    assets.payload = assets.payload.model_copy(
        update={"additionalProductAssetVersionIds": [extra_id]}
    )
    row = await ingest(assets)
    assert len(product_reference_assets(row.context_json)) == 2
    assert extra_version.storage_key in assets.storage.downloads


async def test_foreign_additional_asset_rejects_before_any_storage_read(assets):  # noqa: F811
    assets.payload = assets.payload.model_copy(
        update={"additionalProductAssetVersionIds": [uuid4()]}
    )
    with pytest.raises(AppError):
        await ingest(assets)
    assert assets.storage.reads == []


async def test_additional_references_survive_public_project_and_deletion_inventory():
    row, repository, media, workspace = await intake_with_angles(other_angle())

    async def url(key):
        return "https://private.invalid/" + key.rsplit("/", 1)[-1]

    media.url = url
    public = await RepairService(repository, media, workspace).present(row)
    assert len(public["additionalProductImageUrls"]) == 1
    assert "storageKey" not in str(public)
    inventory = deletion_inventory(
        row.state_json, row.context_json, owned_prefix=f"workspaces/{workspace}/smart-remake/"
    )
    assert row.context_json["p0"]["additionalProductReferences"][0]["storageKey"] in {
        item.get("storageKey") for item in inventory
    }


def test_legacy_context_exposes_one_primary_without_mutating_context():
    context = {
        "productKey": "private/product",
        "productMimeType": "image/png",
        "productMediaHash": "a" * 64,
    }
    before = copy.deepcopy(context)
    assert product_reference_assets(context) == [
        {
            "role": "product",
            "storageKey": "private/product",
            "mimeType": "image/png",
            "mediaHash": "a" * 64,
        }
    ]
    assert context == before


async def test_each_uploaded_product_angle_is_bound_to_constraints():
    row, _, _, _ = await intake_with_angles(other_angle())
    before = constraints_hash(row.context_json)
    context = copy.deepcopy(row.context_json)
    context["p0"]["additionalProductReferences"][0]["mediaHash"] = "f" * 64
    assert constraints_hash(context) != before


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["bytes", "digest", "mime", "missing"])
async def test_changed_or_missing_additional_reference_is_rejected(change):
    row, _, media, _ = await intake_with_angles(other_angle())
    ref = row.context_json["p0"]["additionalProductReferences"][0]
    if change == "bytes":
        media.objects[ref["storageKey"]] = image_upload().bytes
    elif change == "digest":
        ref["mediaHash"] = "f" * 64
    elif change == "mime":
        ref["mimeType"] = "image/jpeg"
    else:
        del media.objects[ref["storageKey"]]
    with pytest.raises(AppError):
        await read_product_references(row.context_json, media)
    with pytest.raises(AppError):
        await assert_input_binding(row, media)
