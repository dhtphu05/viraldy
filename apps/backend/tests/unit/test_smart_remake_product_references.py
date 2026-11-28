"""Every selected product angle is retained, verified and sent in one analysis call."""

from __future__ import annotations

import copy
import hashlib
from io import BytesIO
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi import UploadFile
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
from viraldy.modules.smart_remake.engine.product_lock_generator import generate_product_lock
from viraldy.modules.smart_remake.engine.schemas import CompileSmartRemakeRequest, UploadedMedia
from viraldy.modules.smart_remake.fixture import FixtureGeminiClient
from viraldy.modules.smart_remake.product_references import (
    MAX_PRODUCT_REFERENCE_IMAGES,
    product_reference_assets,
    read_product_references,
)
from viraldy.modules.smart_remake.project_deletion import deletion_inventory
from viraldy.modules.smart_remake.project_intake import assert_input_binding, create_intake
from viraldy.modules.smart_remake.project_policy import stable_hash
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
        repository, media, workspace, actor, intake_payload(), source_upload(), image_upload(),
        additional_products=list(angles),
    )
    return row, repository, media, workspace


@pytest.mark.asyncio
async def test_single_image_intake_keeps_exact_legacy_hash_serialization():
    row, _, _, _ = await intake_with_angles()
    hashes = {"source": hashlib.sha256(source_upload().bytes).hexdigest(),
              "product": hashlib.sha256(image_upload().bytes).hexdigest()}
    assert row.context_json["p0"]["inputHash"] == stable_hash(hashes)
    assert row.context_json["p0"]["intakeRequestHash"] == stable_hash({
        "request": intake_payload().model_dump(mode="json"), "inputs": hashes,
    })
    assert "additionalProductReferences" not in row.context_json["p0"]


@pytest.mark.asyncio
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
        image_upload().bytes, second.bytes,
    ]
    await assert_input_binding(row, media)
    public = project_policy_fields(context)
    assert public["inputMediaHashes"]["additionalProducts"] == [
        hashlib.sha256(second.bytes).hexdigest()
    ]
    assert "storageKey" not in str(public)


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


@pytest.mark.asyncio
async def test_additional_angle_changes_intake_identity_and_replay_cannot_replace_it():
    row, repository, media, workspace = await intake_with_angles(other_angle())
    with pytest.raises(AppError, match="SMART_REMAKE_IDEMPOTENCY_CONFLICT"):
        await create_intake(
            repository, media, workspace, UUID(row.context_json["p0"]["actorId"]),
            intake_payload(), source_upload(), image_upload(),
            additional_products=[other_angle(1)],
        )


@pytest.mark.asyncio
async def test_fourteen_product_images_fit_and_fifteen_are_rejected_before_retention():
    assert MAX_PRODUCT_REFERENCE_IMAGES == 14
    row, _, media, _ = await intake_with_angles(*[other_angle(index) for index in range(13)])
    assert len(await read_product_references(row.context_json, media)) == 14
    with pytest.raises(AppError, match="SMART_REMAKE_PRODUCT_REFERENCES_INVALID"):
        await intake_with_angles(*[other_angle(index) for index in range(14)])


def test_asset_intake_bounds_additional_ids_and_preserves_single_primary():
    with pytest.raises(ValidationError):
        SmartRemakeAssetIntakeRequest(
            metadata=intake_payload(), sourceAssetVersionId=uuid4(), productAssetVersionId=uuid4(),
            additionalProductAssetVersionIds=[uuid4() for _ in range(14)],
        )


@pytest.mark.parametrize("case", ["missing_primary", "duplicate"])
def test_internal_compile_rejects_invalid_product_sets_before_any_analysis(case):
    with pytest.raises(ValidationError):
        CompileSmartRemakeRequest(
            targetDuration=8, aspectRatio="9:16", productSource="upload",
            productImage=image_upload() if case == "duplicate" else None,
            additionalProductImages=[image_upload()],
        )


@pytest.mark.asyncio
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
        extra_version.size_bytes, "image/png",
    )
    assets.payload = assets.payload.model_copy(
        update={"additionalProductAssetVersionIds": [extra_id]}
    )
    row = await ingest(assets)
    assert len(product_reference_assets(row.context_json)) == 2
    assert extra_version.storage_key in assets.storage.downloads


@pytest.mark.asyncio
async def test_foreign_additional_asset_rejects_before_any_storage_read(assets):  # noqa: F811
    assets.payload = assets.payload.model_copy(
        update={"additionalProductAssetVersionIds": [uuid4()]}
    )
    with pytest.raises(AppError):
        await ingest(assets)
    assert assets.storage.reads == []


@pytest.mark.asyncio
async def test_product_lock_uses_every_angle_in_one_call_and_labels_their_role():
    class Gemini(FixtureGeminiClient):
        def __init__(self):
            self.calls = []

        async def generate_json(self, **kwargs):
            self.calls.append(kwargs)
            return await super().generate_json(**kwargs)

    gemini = Gemini()
    await generate_product_lock(
        product_image=image_upload(), additional_product_images=[other_angle()], metadata=None,
        prompt=None, description=None, product_lock=None, visual_identity=None,
        product_reference=None, gemini=gemini,
    )
    assert len(gemini.calls) == 1
    assert [value["bytes"] for value in gemini.calls[0]["media"]] == [
        image_upload().bytes, other_angle().bytes,
    ]
    assert "same product" in gemini.calls[0]["prompt"]
    assert "cutaway" in gemini.calls[0]["prompt"]


@pytest.mark.asyncio
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
    context = {"productKey": "private/product", "productMimeType": "image/png",
               "productMediaHash": "a" * 64}
    before = copy.deepcopy(context)
    assert product_reference_assets(context) == [{
        "role": "product", "storageKey": "private/product", "mimeType": "image/png",
        "mediaHash": "a" * 64,
    }]
    assert context == before


@pytest.mark.asyncio
async def test_multi_image_analysis_bounds_inline_media_but_keeps_original_references():
    import random

    references = []
    for seed in (1, 2):
        output = BytesIO()
        noise = random.Random(seed).randbytes(1024 * 1024 * 3)  # noqa: S311 -- image fixture noise.
        Image.frombytes("RGB", (1024, 1024), noise).save(
            output, format="PNG",
        )
        references.append(UploadedMedia(bytes=output.getvalue(), mime_type="image/png"))
    original_hashes = [hashlib.sha256(value.bytes).hexdigest() for value in references]
    captured = []

    class Gemini(FixtureGeminiClient):
        async def generate_json(self, **kwargs):
            captured.extend(kwargs["media"])
            return await super().generate_json(**kwargs)

    await generate_product_lock(
        product_image=references[0], additional_product_images=references[1:], metadata=None,
        prompt=None, description=None, product_lock=None, visual_identity=None,
        product_reference=None, gemini=Gemini(),
    )
    assert len(captured) == 2
    assert all(len(value["bytes"]) <= 900_000 for value in captured)
    assert [hashlib.sha256(value.bytes).hexdigest() for value in references] == original_hashes
    for value in captured:
        with Image.open(BytesIO(value["bytes"])) as decoded:
            assert decoded.format == "JPEG" and max(decoded.size) <= 2048
    assert captured[0]["bytes"] != captured[1]["bytes"]


@pytest.mark.asyncio
async def test_duplicate_image_bytes_are_rejected_before_retention_or_provider_work():
    media, repository = MemoryMedia(), MemoryRepository()
    with pytest.raises(AppError, match="SMART_REMAKE_PRODUCT_REFERENCES_INVALID"):
        await create_intake(
            repository, media, uuid4(), uuid4(), intake_payload(), source_upload(), image_upload(),
            additional_products=[image_upload()],
        )
    assert media.objects == {} and repository.rows == {}
    row, _, _, _ = await intake_with_angles(other_angle())
    row.context_json["p0"]["additionalProductReferences"][0]["mediaHash"] = (
        row.context_json["productMediaHash"]
    )
    with pytest.raises(AppError, match="SMART_REMAKE_PRODUCT_REFERENCES_INVALID"):
        product_reference_assets(row.context_json)


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid", [False, True])
async def test_compile_retains_all_angles_and_rejects_bad_views_before_source_analysis(
    monkeypatch, invalid,
):
    from tests.unit.test_smart_remake_timeline_compile import Media, Repository
    from viraldy.modules.smart_remake import timeline_compile as module

    observed = []
    repository, media = Repository(), Media()
    monkeypatch.setattr(module, "RepairRepository", lambda _: repository)
    monkeypatch.setattr(module, "RepairMediaStore", lambda _: media)
    monkeypatch.setattr(module, "S3StorageAdapter", lambda _: object())
    monkeypatch.setattr(module, "probe_media_bytes", lambda _: {
        "hasVideo": True, "durationSeconds": 8,
    })
    monkeypatch.setattr(module, "measure_video_frames", lambda _: 192)
    monkeypatch.setattr(module, "extract_timeline_thumbnails", lambda source, seconds: [])
    monkeypatch.setattr(module, "extract_source_excerpt", lambda source, **kwargs: source)
    monkeypatch.setattr(module, "enrich_reference_analysis_with_detected_cuts", lambda a, b: a)
    monkeypatch.setattr(module, "source_opening_bindings", lambda source, scenes: {
        scene["id"]: {"sourceMediaHash": hashlib.sha256(source.bytes).hexdigest(),
                      "frame": scene["startFrame"], "layoutHash": "a" * 64,
                      "extractorVersion": "source-opening-frame-v1"}
        for scene in scenes
    })

    async def analyze(**kwargs):
        observed.append("source")
        return await FixtureGeminiClient().generate_json(system_instruction="", prompt="8 seconds")

    original_lock = module.generate_product_lock

    async def lock(**kwargs):
        observed.append([kwargs["product_image"], *kwargs["additional_product_images"]])
        return await original_lock(**kwargs)

    monkeypatch.setattr(module, "analyze_reference_video", analyze)
    monkeypatch.setattr(module, "generate_product_lock", lock)
    second = b"not an image" if invalid else other_angle().bytes
    task = module.compile_timeline_request(
        session=object(), settings=SimpleNamespace(ai_mode="fixture"), workspace_id=uuid4(),
        mode="smart_remake", target_duration="8", aspect_ratio="9:16", language=None,
        prompt=None, description=None, product_url=None, product_title=None,
        product_description=None, reference_video=UploadFile(
            filename="source.mp4", file=BytesIO(source_upload().bytes),
        ), product_image=UploadFile(filename="primary.png", file=BytesIO(image_upload().bytes)),
        additional_product_images=[UploadFile(filename="other.png", file=BytesIO(second))],
        source_cut_frames=[0, 192],
    )
    if invalid:
        with pytest.raises(AppError):
            await task
        assert observed == []
    else:
        await task
        assert observed[0] == "source"
        assert [value.bytes for value in observed[1]] == [image_upload().bytes, second]
        assert len(product_reference_assets(repository.row.context_json)) == 2
