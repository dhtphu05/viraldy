"""Regressions for real model payloads and exact opening references; no provider calls."""

from __future__ import annotations

import hashlib
from io import BytesIO
from types import SimpleNamespace

import pytest
from PIL import Image

from viraldy.modules.smart_remake import image_workflow
from viraldy.modules.smart_remake.engine.kie_adapter import (
    build_kie_group_request,
    build_kie_video_request,
)


def png(color: str) -> bytes:
    output = BytesIO()
    Image.new("RGB", (96, 160), color).save(output, format="PNG")
    return output.getvalue()


def source_scene():
    return {
        "id": "unit", "sourceSceneId": "source", "prompt": "Show target bottle",
        "imagePrompt": "On a red background and wood table",
        "videoPrompt": "Open the target bottle lid",
        "shotPlan": {"shots": [{"action": "Open Acme bottle lid", "stateBefore": "Acme lid closed",
            "physicalAction": {"contact": "hand on Acme cap"}, "stateAfter": "Acme lid open",
            "setting": "red background and wood table", "transition": "continuous"}]},
    }


@pytest.mark.parametrize("group", [False, True])
def test_final_kie_payload_cleans_source_identity_in_every_scene_field(group):
    scene = source_scene()
    params = {"product_lock": {"productName": "Seller Bottle", "productType": "bottle"},
        "reference_analysis": {"forbiddenReuse": ["Acme"]}}
    if group:
        request = build_kie_group_request(scenes=[scene],
            segments=[{"inFrame": 0, "outFrame": 192}],
            reference_image_urls=["https://8.8.8.8/opening.png", "https://8.8.8.8/ending.png"],
            **params)
    else:
        request = build_kie_video_request(scene=scene,
            product_image_url="https://8.8.8.8/product.png", **params)
    prompt = request["input"]["prompt"]
    assert "Acme" not in prompt
    assert all(value in prompt for value in ("red background", "wood table", "hand", "lid"))
    assert "sequential hard cuts" not in prompt


@pytest.mark.asyncio
async def test_opening_reference_ignores_midpoint_thumbnail_and_verifies_absolute_frame(
    monkeypatch,
):
    product, opening, midpoint = png("pink"), png("red"), png("blue")
    objects = {"product": product, "video": b"original source bytes", "midpoint": midpoint}
    calls = []

    async def read(key):
        calls.append(key)
        return objects[key]

    source_hash = hashlib.sha256(objects["video"]).hexdigest()
    row = SimpleNamespace(context_json={"productKey": "product", "productMimeType": "image/png",
        "productMediaHash": hashlib.sha256(product).hexdigest(), "sourceKey": "video",
        "sourceMediaHash": source_hash,
        "sourceThumbnailKeys": {"source": "midpoint"},
        "sourceSceneMap": {"scenes": [{"id": "source", "startFrame": 144, "endFrame": 192}]},
        "renderPlan": {"units": [{"id": "unit", "sourceSceneId": "source"}]},
        "sourceOpeningFrames": {"source": {"sourceMediaHash": source_hash, "frame": 144,
            "layoutHash": hashlib.sha256(opening).hexdigest(),
            "extractorVersion": "source-opening-frame-v1"}}})
    captures = []
    monkeypatch.setattr(image_workflow, "extract_layout_frame",
        lambda data, frame: captures.append((data, frame)) or opening)
    repair = SimpleNamespace(media=SimpleNamespace(read=read))
    _, layout = await image_workflow._references(repair, row, 0)
    assert captures == [(objects["video"], 144)]
    assert "midpoint" not in calls
    assert layout.bytes == opening


def canonical_runtime():
    from viraldy.modules.smart_remake.generation_expectations import (
        build_generation_expectations,
        expectations_hash,
    )

    scene = source_scene()
    context = {
        "productKey": "product", "productMimeType": "image/png",
        "productLock": {"productName": "Seller Bottle", "visualIdentity": {"colors": ["pink"]}},
        "productMediaHash": "a" * 64, "sourceMediaHash": "b" * 64,
        "referenceAnalysis": {"forbiddenReuse": ["Acme"]},
        "sourceSceneMap": {"scenes": [{"id": "source", "startFrame": 120, "endFrame": 192}]},
        "sourceOpeningFrames": {"source": {"sourceMediaHash": "b" * 64, "frame": 120,
            "layoutHash": "c" * 64, "extractorVersion": "source-opening-frame-v1"}},
        "sceneMap": {"scenes": [scene]},
        "renderPlan": {"units": [{"id": "unit", "sourceSceneId": "source", "sceneIndex": 0,
                                   "targetDurationFrames": 72}],
                       "imageModel": "gpt-image-2.6-sunburst"},
    }
    snapshot = build_generation_expectations(context)
    context.update(generationExpectations=snapshot, expectationsHash=expectations_hash(snapshot))
    return context


@pytest.mark.asyncio
async def test_kie_combined_payload_is_checked_before_any_image_or_upload(monkeypatch):
    from viraldy.modules.smart_remake import kie_workflow
    from viraldy.modules.smart_remake.engine import kie_adapter

    row = SimpleNamespace(context_json=canonical_runtime())
    op = SimpleNamespace(result_json={"kind": "render", "tasks": {}})

    async def finish(operation, status, result):
        operation.result_json = result

    repair = SimpleNamespace(repository=SimpleNamespace(finish=finish), settings=None)
    runner = kie_workflow.KieWorkflow(repair, client=object(), image_client=object())
    await runner._freeze_plan(row, op)

    original_adapter = kie_adapter.build_kie_group_request

    def unsafe_provider_payload(**kwargs):
        request = original_adapter(**kwargs)
        request["input"]["prompt"] += "Use Acme instead of the target"
        return request

    monkeypatch.setattr(kie_adapter, "build_kie_group_request", unsafe_provider_payload)
    with pytest.raises(Exception, match="Source product identity remains"):
        await runner._request(row, op, 0, None)
    assert op.result_json["expectationsHash"] == row.context_json["expectationsHash"]


@pytest.mark.asyncio
async def test_old_submitted_intent_keeps_original_plan_for_reconciliation():
    from viraldy.modules.smart_remake.kie_workflow import KieWorkflow

    row = SimpleNamespace(context_json={"renderPlan": {"version": "new"}})
    op = SimpleNamespace(result_json={"renderPlan": {"version": "original"},
        "tasks": {"0": {"status": "submitted", "taskId": "existing-paid-task"}}})
    runner = KieWorkflow(SimpleNamespace(), client=object())
    assert await runner._freeze_plan(row, op) == {"version": "original"}
    assert "generationExpectations" not in op.result_json


@pytest.mark.asyncio
async def test_old_unknown_image_intent_is_not_upgraded_into_new_paid_work():
    from viraldy.modules.smart_remake.kie_workflow import KieWorkflow
    from viraldy.shared.errors.base import AppError

    row = SimpleNamespace(context_json=canonical_runtime())
    op = SimpleNamespace(result_json={"tasks": {}, "images": {"0": {"status": "submitting"}}})
    runner = KieWorkflow(SimpleNamespace(), client=object())
    with pytest.raises(AppError, match="OPENAI_IMAGE_SUBMISSION_UNRESOLVED"):
        await runner._freeze_plan(row, op)
    assert "generationExpectations" not in op.result_json


@pytest.mark.asyncio
async def test_operation_without_snapshot_hash_cannot_prepare_any_provider_request():
    from viraldy.modules.smart_remake.kie_workflow import KieWorkflow
    from viraldy.shared.errors.base import AppError

    row = SimpleNamespace(context_json=canonical_runtime())
    op = SimpleNamespace(result_json={
        "generationExpectations": row.context_json["generationExpectations"],
    })
    runner = KieWorkflow(SimpleNamespace(), client=object())
    with pytest.raises(AppError, match="SMART_REMAKE_EXPECTATIONS_REQUIRED"):
        await runner._request(row, op, 0, None)
