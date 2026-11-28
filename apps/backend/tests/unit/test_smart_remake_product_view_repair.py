"""Repair retains product identity while bounding multi-view analysis evidence."""

from __future__ import annotations

import copy
import hashlib
from types import SimpleNamespace

import pytest

from tests.smart_remake_expectations import fixture_opening_bytes, install_expectations
from tests.unit.test_smart_remake_image_workflow import image
from tests.unit.test_smart_remake_repair_intent import prepared
from viraldy.modules.smart_remake import repair_intent_media
from viraldy.modules.smart_remake.engine.schemas import UploadedMedia
from viraldy.modules.smart_remake.repair_intent import repair_base_scene
from viraldy.modules.smart_remake.repair_intent_workflow import normalization_prompt
from viraldy.modules.smart_remake.repair_schemas import RepairIntent
from viraldy.shared.errors.base import AppError


def repair_inputs(monkeypatch, *, excerpt=b"excerpt"):
    row, scene = prepared()
    primary, secondary = image((90, 160), "red"), image((90, 160), "blue")
    originals = [primary, secondary]
    row.context_json.setdefault("p0", {})["assets"] = {
        "product": {"storageKey": "product", "mimeType": "image/png", "role": "product"}
    }
    row.context_json["p0"]["additionalProductReferences"] = [
        {
            "storageKey": "extra",
            "mimeType": "image/png",
            "role": "product",
            "mediaHash": hashlib.sha256(secondary).hexdigest(),
        }
    ]
    install_expectations(row.context_json, state=row.state_json, product_bytes=primary)
    clip = b"active-owned-clip"
    scene["versions"][0].update(storageKey="active", mediaHash=hashlib.sha256(clip).hexdigest())

    async def references(*_):
        return UploadedMedia(bytes=primary, mime_type="image/png"), UploadedMedia(
            bytes=fixture_opening_bytes("source"), mime_type="image/png"
        )

    async def read(key):
        return {"product": primary, "extra": secondary, "active": clip}[key]

    monkeypatch.setattr(repair_intent_media, "_references", references)
    monkeypatch.setattr(repair_intent_media, "probe_timeline_media", lambda _: {"frameCount": 192})
    monkeypatch.setattr(repair_intent_media, "trim_repair_evidence", lambda *_: excerpt)
    return row, scene, SimpleNamespace(media=SimpleNamespace(read=read)), originals


@pytest.mark.asyncio
async def test_repair_passes_all_angles_as_bounded_copies_with_original_identity_hashes(
    monkeypatch,
):
    row, scene, repair, originals = repair_inputs(monkeypatch)
    derived = [
        UploadedMedia(bytes=image((45, 80), color), mime_type="image/png")
        for color in ("green", "yellow")
    ]
    seen = []

    def copies(images):
        seen.extend(value.bytes for value in images)
        return derived

    monkeypatch.setattr(
        repair_intent_media, "prepare_product_analysis_images", copies, raising=False
    )
    media, evidence = await repair_intent_media.repair_evidence(repair, row, scene)
    assert seen == originals
    assert [item["bytes"] for item in media[:2]] == [item.bytes for item in derived]
    assert media[2]["bytes"] == fixture_opening_bytes("source")
    assert media[3]["bytes"] == b"excerpt"
    assert evidence["productReferenceHashes"] == [hashlib.sha256(v).hexdigest() for v in originals]
    assert evidence["evidenceHashes"] == [hashlib.sha256(v["bytes"]).hexdigest() for v in media]
    system, _ = normalization_prompt(
        row,
        repair_base_scene(row, scene),
        RepairIntent(schemaVersion=1, issues=[], instruction=""),
        evidence,
    )
    assert "Images 1 through 2" in system
    assert "Image 3 is the immutable source opening" in system
    assert "video 4 is the active clip" in system


@pytest.mark.asyncio
async def test_repair_rejects_product_views_not_retained_by_active_version(monkeypatch):
    row, scene, repair, _ = repair_inputs(monkeypatch)
    single = copy.deepcopy(row.context_json["generationExpectations"])
    single.pop("productReferenceHashes")
    from viraldy.modules.smart_remake.generation_expectations import expectations_hash

    scene["versions"][0].update(
        generationExpectations=single, expectationsHash=expectations_hash(single)
    )
    with pytest.raises(AppError, match="SMART_REMAKE_INPUT_CHANGED"):
        await repair_intent_media.repair_evidence(repair, row, scene)


@pytest.mark.asyncio
async def test_multiview_repair_rejects_oversized_inline_payload_before_analysis(monkeypatch):
    row, scene, repair, _ = repair_inputs(monkeypatch, excerpt=b"x" * 14_000_001)
    with pytest.raises(AppError, match="SMART_REMAKE_REPAIR_EVIDENCE_TOO_LARGE"):
        await repair_intent_media.repair_evidence(repair, row, scene)
