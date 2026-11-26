from __future__ import annotations

import copy
import hashlib
import json
from io import BytesIO
from types import SimpleNamespace
from uuid import uuid4

import pytest
from PIL import Image

from viraldy.modules.smart_remake import image_workflow as module
from viraldy.modules.smart_remake.generation_expectations import (
    build_generation_expectations,
    expectations_hash,
)
from viraldy.shared.errors.base import AppError


def image(size=(720, 1280), color="pink"):
    stream = BytesIO()
    Image.new("RGB", size, color).save(stream, format="PNG")
    return stream.getvalue()


class Media:
    def __init__(self):
        self.objects = {
            "product": image((20, 30)),
            "layout": image((30, 20), "white"),
            "source": b"owned video",
        }
        self.puts = []

    async def read(self, key):
        return self.objects[key]

    async def put(self, prefix, data, mime_type):
        key = f"{prefix}/image-{len(self.puts)}"
        self.objects[key] = data
        self.puts.append(key)
        return key


class Repository:
    def __init__(self, row):
        self.row = row
        self.updates = []

    async def project(self, workspace_id, project_id, **kwargs):
        assert self.row.workspace_id == workspace_id and self.row.id == project_id
        return self.row

    async def merge_context(self, row, updates):
        row.context_json = {**row.context_json, **copy.deepcopy(updates)}
        self.updates.append(copy.deepcopy(updates))


class ImageClient:
    def __init__(self, op):
        self.op = op
        self.calls = []
        self.fail = False

    async def edit(self, **kwargs):
        assert self.op.result_json["images"]["0"]["status"] == "submitting"
        self.calls.append(kwargs)
        if self.fail:
            raise TimeoutError("lost accepted response")
        data = image()
        return {
            "bytes": data,
            "mimeType": "image/png",
            "mediaHash": hashlib.sha256(data).hexdigest(),
            "model": kwargs["model"],
            "size": "720x1280",
            "quality": kwargs["quality"],
            "complexity": kwargs["complexity"],
            "usage": {"input_tokens": 30, "output_tokens": 90},
        }


@pytest.fixture
def setup(monkeypatch):
    row = SimpleNamespace(
        id=uuid4(),
        workspace_id=uuid4(),
        context_json={
            "productKey": "product",
            "productMimeType": "image/png",
            "sourceKey": "source",
            "sourceMimeType": "video/mp4",
            "sourceThumbnailKeys": {"source-scene": "layout"},
            "sourceSceneMap": {
                "scenes": [{"id": "source-scene", "startFrame": 48, "endFrame": 120}]
            },
            "renderPlan": {
                "imageModel": "gpt-image-2.6-flare",
                "imageQuality": "low",
                "imageSize": "720x1280",
                "units": [{"id": "unit", "sceneIndex": 0, "sourceSceneId": "source-scene"}],
            },
            "productLock": {"productName": "Pink Cup", "mustPreserve": ["pink handle"],
                            "visualIdentity": {"colors": ["pink"]}},
        },
    )
    op = SimpleNamespace(id=uuid4(), result_json={"kind": "render", "tasks": {}})
    repair = SimpleNamespace(
        workspace_id=row.workspace_id, media=Media(), repository=Repository(row)
    )
    client = ImageClient(op)
    history = []

    async def save(operation, result, **kwargs):
        operation.result_json = copy.deepcopy(result)
        history.append(copy.deepcopy(result))

    scene = {"id": "unit", "imagePrompt": "Close view from the left", "prompt": "Product demo",
             "videoPrompt": "Open the lid"}
    row.context_json["sceneMap"] = {"scenes": [scene]}
    row.context_json.update(
        sourceMediaHash=hashlib.sha256(repair.media.objects["source"]).hexdigest(),
        productMediaHash=hashlib.sha256(repair.media.objects["product"]).hexdigest(),
    )
    row.context_json["sourceOpeningFrames"] = {"source-scene": {
        "sourceMediaHash": row.context_json["sourceMediaHash"], "frame": 48,
        "layoutHash": hashlib.sha256(repair.media.objects["layout"]).hexdigest(),
        "extractorVersion": module.OPENING_FRAME_EXTRACTOR_VERSION,
    }}
    monkeypatch.setattr(module, "extract_layout_frame",
                        lambda data, frame: repair.media.objects["layout"])
    refresh_expectations(row)
    op.result_json.update(
        generationExpectations=copy.deepcopy(row.context_json["generationExpectations"]),
        expectationsHash=row.context_json["expectationsHash"],
    )
    return repair, row, op, client, scene, save, history


async def prepare(setup, **kwargs):
    repair, row, op, client, scene, save, _ = setup
    refresh_expectations(row)
    op.result_json.update(
        generationExpectations=copy.deepcopy(row.context_json["generationExpectations"]),
        expectationsHash=row.context_json["expectationsHash"],
    )
    return await module.prepare_scene_image(
        repair=repair,
        row=row,
        operation=op,
        index=0,
        compiled_scene=scene,
        image_client=client,
        save=save,
        ensure_active=lambda: None,
        **kwargs,
    )


def refresh_expectations(row):
    try:
        snapshot = build_generation_expectations(row.context_json)
    except AppError:
        return  # The production guard must reject intentionally invalid test inputs.
    row.context_json.update(
        generationExpectations=snapshot, expectationsHash=expectations_hash(snapshot),
    )


def fragment_references(setup):
    repair, row, _, _, _, _, _ = setup
    row.context_json["sourceSceneMap"] = {
        "timingMode": "fit_target",
        "scenes": [{"id": "source-scene", "startFrame": 48, "endFrame": 120}],
    }
    row.context_json["renderPlan"]["units"] = [
        {
            "id": f"unit-{index}", "sourceSceneId": "source-scene", "sceneIndex": index,
            "sourceStartFrame": start, "sourceEndFrame": end,
            "fragmentIndex": index, "fragmentCount": 2,
        }
        for index, (start, end) in enumerate(((48, 84), (84, 120)))
    ]
    layouts = {48: image((30, 20), "white"), 84: image((30, 20), "pink")}
    row.context_json["sourceOpeningFrames"] = {
        f"unit-{index}": {
            "sourceMediaHash": row.context_json["sourceMediaHash"], "frame": frame,
            "layoutHash": hashlib.sha256(layouts[frame]).hexdigest(),
            "extractorVersion": module.OPENING_FRAME_EXTRACTOR_VERSION,
        }
        for index, frame in enumerate((48, 84))
    }
    return repair, row, layouts


@pytest.mark.asyncio
async def test_fragment_references_use_each_unit_opening_in_original_source_clock(
    setup, monkeypatch,
):
    repair, row, layouts = fragment_references(setup)
    captured = []

    def extract(data, frame):
        assert data == repair.media.objects["source"]
        captured.append(frame)
        return layouts[frame]

    monkeypatch.setattr(module, "extract_layout_frame", extract)
    first = await module._references(repair, row, 0)
    second = await module._references(repair, row, 1)
    assert captured == [48, 84]
    assert first[1].bytes == layouts[48]
    assert second[1].bytes == layouts[84]
    assert first[1].bytes != second[1].bytes


@pytest.mark.asyncio
async def test_fragment_reference_never_falls_back_to_logical_scene_binding(setup, monkeypatch):
    repair, row, layouts = fragment_references(setup)
    row.context_json["sourceOpeningFrames"] = {
        "source-scene": row.context_json["sourceOpeningFrames"]["unit-0"],
    }
    monkeypatch.setattr(module, "extract_layout_frame", lambda data, frame: layouts[frame])
    with pytest.raises(AppError) as error:
        await module._references(repair, row, 1)
    assert error.value.code == "SMART_REMAKE_IMAGE_ASSET_INVALID"


@pytest.mark.asyncio
@pytest.mark.parametrize("changed", ["sourceMediaHash", "frame", "layoutHash"])
async def test_fragment_reference_rejects_another_units_opening_binding(
    setup, monkeypatch, changed,
):
    repair, row, layouts = fragment_references(setup)
    original = row.context_json["sourceOpeningFrames"]
    row.context_json["sourceOpeningFrames"]["unit-1"] = {
        **original["unit-1"],
        changed: "0" * 64 if changed == "sourceMediaHash" else original["unit-0"][changed],
    }
    monkeypatch.setattr(module, "extract_layout_frame", lambda data, frame: layouts[frame])
    with pytest.raises(AppError) as error:
        await module._references(repair, row, 1)
    assert error.value.code == "SMART_REMAKE_IMAGE_ASSET_INVALID"


@pytest.mark.asyncio
@pytest.mark.parametrize("start,end", [(47, 84), (84, 121), (84, 84), (True, 120)])
async def test_fragment_reference_rejects_ranges_outside_its_logical_scene(
    setup, monkeypatch, start, end,
):
    repair, row, _ = fragment_references(setup)
    row.context_json["renderPlan"]["units"][1].update(
        sourceStartFrame=start, sourceEndFrame=end,
    )
    monkeypatch.setattr(module, "extract_layout_frame", lambda *args: pytest.fail("decode"))
    with pytest.raises(AppError) as error:
        await module._references(repair, row, 1)
    assert error.value.code == "SMART_REMAKE_IMAGE_ASSET_INVALID"


@pytest.mark.asyncio
async def test_intent_committed_then_owned_image_cached_and_usage_saved(setup):
    repair, row, op, client, _, _, history = setup
    result = await prepare(setup)
    assert history[0]["images"]["0"]["status"] == "submitting"
    assert result["storageKey"].startswith(
        f"workspaces/{row.workspace_id}/smart-remake/{row.id}/images/"
    )
    assert row.context_json["imageAssets"][result["requestHash"]] == result
    assert op.result_json["images"]["0"]["status"] == "completed"
    assert result["usage"] == {"input_tokens": 30, "output_tokens": 90}
    assert client.calls[0]["product"].bytes == repair.media.objects["product"]
    assert client.calls[0]["layout"].bytes == repair.media.objects["layout"]
    assert all(
        text in client.calls[0]["prompt"]
        for text in ["Pink Cup", "pink handle", "Close view from the left"]
    )


async def test_known_image_rejection_persists_terminal_receipt_without_inventing_bill(
    setup, monkeypatch,
):
    from unittest.mock import AsyncMock

    _, _, operation, client, _, _, _ = setup
    client.last_rejection_receipt = {
        "requestOutcome": "rejected", "httpStatus": 429,
        "providerErrorCode": "insufficient_quota", "retryAfterSeconds": 12,
        "classification": "credits_exhausted",
    }
    client.edit = AsyncMock(side_effect=AppError("OPENAI_IMAGE_CREDITS_EXHAUSTED", "Rejected", 429))
    settle = AsyncMock()
    monkeypatch.setattr(module, "settle_generation_attempt", settle)
    with pytest.raises(AppError) as error:
        await prepare(setup)
    assert error.value.code == "OPENAI_IMAGE_CREDITS_EXHAUSTED"
    receipt = settle.call_args.kwargs["receipt"]
    assert settle.call_args.kwargs["status"] == "failed"
    assert receipt["requestOutcome"] == "rejected" and receipt["httpStatus"] == 429
    assert "billedUsd" not in receipt
    saved = operation.result_json["images"]["0"]
    assert saved["status"] == "rejected" and saved["errorCode"] == error.value.code
    assert saved["providerErrorCode"] == "insufficient_quota"


@pytest.mark.asyncio
async def test_cache_reused_across_operation_without_another_paid_image(setup):
    _, _, op, client, _, _, _ = setup
    first = await prepare(setup)
    op.result_json = {"kind": "repair", "tasks": {}}
    second = await prepare(setup)
    assert first == second and len(client.calls) == 1


@pytest.mark.asyncio
async def test_unknown_submit_marks_reconciliation_and_never_reposts(setup):
    _, _, op, client, _, _, _ = setup
    client.fail = True
    for _ in range(2):
        with pytest.raises(AppError) as exc:
            await prepare(setup)
        assert exc.value.code == "OPENAI_IMAGE_SUBMISSION_UNRESOLVED"
    assert op.result_json["needsReconciliation"] is True and len(client.calls) == 1


@pytest.mark.asyncio
async def test_cache_recovered_after_crash_before_operation_completion_write(setup):
    repair, row, op, client, scene, save, _ = setup

    async def crash_after_cache(operation, result):
        if result.get("images", {}).get("0", {}).get("status") == "completed":
            raise RuntimeError("crash before operation save")
        await save(operation, result)

    with pytest.raises(RuntimeError):
        await module.prepare_scene_image(
            repair=repair,
            row=row,
            operation=op,
            index=0,
            compiled_scene=scene,
            image_client=client,
            save=crash_after_cache,
            ensure_active=lambda: None,
        )
    assert op.result_json["images"]["0"]["status"] == "submitting"
    result = await prepare(setup)
    assert row.context_json["imageAssets"][result["requestHash"]] == result
    assert len(client.calls) == 1


@pytest.mark.asyncio
async def test_changed_prompt_or_quality_has_distinct_cache_identity(setup):
    _, row, op, client, scene, _, _ = setup
    first = await prepare(setup)
    scene["imagePrompt"] = "Changed visual direction"
    op.result_json = {}
    second = await prepare(setup)
    row.context_json["renderPlan"]["imageQuality"] = "medium"
    op.result_json = {}
    third = await prepare(setup)
    assert len({r["requestHash"] for r in [first, second, third]}) == 3
    assert len(client.calls) == 3 and third["quality"] == "medium"


@pytest.mark.asyncio
async def test_corrupt_retained_asset_fails_without_spending_again(setup):
    repair, _, _, client, _, _, _ = setup
    record = await prepare(setup)
    repair.media.objects[record["storageKey"]] = b"changed media"
    with pytest.raises(AppError) as exc:
        await prepare(setup)
    assert exc.value.code == "SMART_REMAKE_IMAGE_ASSET_INVALID" and len(client.calls) == 1


@pytest.mark.asyncio
async def test_owned_product_hash_mismatch_never_submits(setup):
    _, row, _, client, _, _, _ = setup
    row.context_json["productMediaHash"] = "incorrect"
    with pytest.raises(AppError) as exc:
        await prepare(setup)
    assert exc.value.code == "SMART_REMAKE_IMAGE_ASSET_INVALID" and client.calls == []


@pytest.mark.asyncio
async def test_missing_thumbnail_extracts_owned_source_at_absolute_scene_start(setup, monkeypatch):
    _, row, _, client, _, _, _ = setup
    row.context_json["sourceThumbnailKeys"] = {}
    layout = image((30, 20), "blue")
    row.context_json["sourceOpeningFrames"]["source-scene"]["layoutHash"] = (
        hashlib.sha256(layout).hexdigest()
    )
    captures = []
    monkeypatch.setattr(
        module, "extract_layout_frame", lambda data, frame: captures.append((data, frame)) or layout
    )
    await prepare(setup)
    assert captures == [(b"owned video", 48)]
    assert client.calls[0]["layout"].bytes == layout


@pytest.mark.asyncio
async def test_worker_claim_fence_runs_before_paid_image(setup):
    repair, row, op, client, scene, save, _ = setup

    def cancelled():
        raise AppError("JOB_ATTEMPT_SUPERSEDED", "superseded")

    with pytest.raises(AppError, match="JOB_ATTEMPT_SUPERSEDED"):
        await module.prepare_scene_image(
            repair=repair,
            row=row,
            operation=op,
            index=0,
            compiled_scene=scene,
            image_client=client,
            save=save,
            ensure_active=cancelled,
        )
    assert client.calls == []


@pytest.mark.asyncio
async def test_output_storage_failure_is_unresolved_and_never_regenerates(setup):
    repair, _, op, client, _, _, _ = setup

    async def unavailable(*args):
        raise OSError("storage unavailable")

    repair.media.put = unavailable
    for _ in range(2):
        with pytest.raises(AppError) as exc:
            await prepare(setup)
        assert exc.value.code == "OPENAI_IMAGE_SUBMISSION_UNRESOLVED"
    assert op.result_json["needsReconciliation"] is True and len(client.calls) == 1


@pytest.mark.asyncio
async def test_cached_media_must_belong_to_same_workspace_and_project(setup):
    _, row, _, client, _, _, _ = setup
    record = await prepare(setup)
    row.context_json["imageAssets"][record["requestHash"]]["storageKey"] = "other-workspace/image"
    with pytest.raises(AppError) as exc:
        await prepare(setup)
    assert exc.value.code == "SMART_REMAKE_IMAGE_ASSET_INVALID" and len(client.calls) == 1


@pytest.mark.asyncio
async def test_server_carried_cache_reuses_owned_image_after_new_draft_compile(setup):
    _, row, op, client, _, _, _ = setup
    record = await prepare(setup)
    row.id = uuid4()
    op.result_json = {}
    reused = await prepare(setup)
    assert reused == record and len(client.calls) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "setting,value",
    [("imageModel", "other"), ("imageQuality", "ultra"), ("imageComplexity", "max")],
)
async def test_invalid_saved_image_configuration_spends_nothing(setup, setting, value):
    _, row, _, client, _, _, _ = setup
    row.context_json["renderPlan"][setting] = value
    with pytest.raises(AppError) as exc:
        await prepare(setup)
    assert exc.value.code == "OPENAI_IMAGE_VALIDATION_FAILED" and client.calls == []


@pytest.mark.asyncio
async def test_sunburst_plan_freezes_max_quality_and_high_complexity_in_request_and_cache(setup):
    _, row, op, client, _, _, history = setup
    row.context_json["renderPlan"].update(
        imageModel="gpt-image-2.6-sunburst", imageQuality="max", imageComplexity="high"
    )
    first = await prepare(setup)
    assert client.calls[0]["model"] == "gpt-image-2.6-sunburst"
    assert client.calls[0]["quality"] == "max" and client.calls[0]["complexity"] == "high"
    assert history[0]["images"]["0"]["complexity"] == "high"
    assert first["quality"] == "max" and first["complexity"] == "high"
    op.result_json = {}
    assert await prepare(setup) == first
    assert len(client.calls) == 1


@pytest.mark.asyncio
async def test_model_and_complexity_changes_do_not_reuse_lower_configuration_cache(setup):
    _, row, op, client, _, _, _ = setup
    first = await prepare(setup)
    row.context_json["renderPlan"].update(
        imageModel="gpt-image-2.6-sunburst", imageQuality="max", imageComplexity="high"
    )
    op.result_json = {}
    second = await prepare(setup)
    row.context_json["renderPlan"]["imageComplexity"] = "medium"
    op.result_json = {}
    third = await prepare(setup)
    assert len({result["requestHash"] for result in (first, second, third)}) == 3
    assert len(client.calls) == 3 and third["complexity"] == "medium"


@pytest.mark.asyncio
async def test_legacy_flare_cache_is_invalidated_by_canonical_opening_binding(setup):
    _, _, _, client, _, _, _ = setup
    result = await prepare(setup)
    request = client.calls[0]
    legacy_hash = hashlib.sha256(
        json.dumps(
            {
                "model": "gpt-image-2.6-flare",
                "size": "720x1280",
                "quality": "low",
                "prompt": request["prompt"],
                "productHash": hashlib.sha256(request["product"].bytes).hexdigest(),
                "layoutHash": hashlib.sha256(request["layout"].bytes).hexdigest(),
            },
            sort_keys=True,
        ).encode()
    ).hexdigest()
    assert result["requestHash"] != legacy_hash
    assert result["openingFrame"]["extractorVersion"] == module.OPENING_FRAME_EXTRACTOR_VERSION
    assert result["expectationsHash"]
    assert request["model"] == "gpt-image-2.6-flare"
    assert request["quality"] == "low" and request["complexity"] == "high"


@pytest.mark.asyncio
async def test_sunburst_plan_missing_complexity_cannot_spend(setup):
    _, row, _, client, _, _, _ = setup
    row.context_json["renderPlan"].update(imageModel="gpt-image-2.6-sunburst", imageQuality="max")
    with pytest.raises(AppError) as exc:
        await prepare(setup)
    assert exc.value.code == "OPENAI_IMAGE_VALIDATION_FAILED" and client.calls == []


@pytest.mark.asyncio
async def test_missing_opening_direction_is_rejected_before_submit(setup):
    _, _, _, client, scene, _, _ = setup
    scene["imagePrompt"] = ""
    with pytest.raises(AppError) as exc:
        await prepare(setup)
    assert exc.value.code == "SMART_REMAKE_EXPECTATIONS_REQUIRED" and client.calls == []


@pytest.mark.asyncio
async def test_explicit_openai_rejection_is_terminal_not_ambiguous(setup):
    _, _, op, client, _, _, _ = setup

    async def rejected(**kwargs):
        raise AppError("OPENAI_IMAGE_AUTH_FAILED", "not configured")

    client.edit = rejected
    with pytest.raises(AppError) as exc:
        await prepare(setup)
    assert exc.value.code == "OPENAI_IMAGE_AUTH_FAILED"
    assert op.result_json.get("needsReconciliation") is not True


def test_layout_fallback_decodes_requested_real_source_frame(tmp_path):
    import shutil
    import subprocess

    from viraldy.modules.smart_remake.engine.media_binaries import ffmpeg_path

    if not shutil.which("ffmpeg"):
        pytest.skip("FFmpeg is required for real-frame extraction")
    source = tmp_path / "source.mp4"
    subprocess.run(  # noqa: S603 - fixed generated fixture path
        [
            ffmpeg_path(),
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=red:s=32x48:r=24:d=1",
            "-f",
            "lavfi",
            "-i",
            "color=c=blue:s=32x48:r=24:d=1",
            "-filter_complex",
            "[0:v][1:v]concat=n=2:v=1:a=0[v]",
            "-map",
            "[v]",
            "-c:v",
            "libx264",
            str(source),
        ],
        check=True,
        capture_output=True,
    )
    extracted = module.extract_layout_frame(source.read_bytes(), 30)
    with Image.open(BytesIO(extracted)) as frame:
        red, green, blue = frame.convert("RGB").getpixel((16, 24))
    assert blue > 200 and red < 30 and green < 30


@pytest.mark.asyncio
async def test_image_record_binds_canonical_scene_opening_and_expectations(setup):
    _, row, op, _, _, _, _ = setup
    record = await prepare(setup)
    assert record["expectationsHash"] == row.context_json["expectationsHash"]
    assert record["renderUnitId"] == "unit" and record["sourceSceneId"] == "source-scene"
    assert record["openingFrame"] == row.context_json["sourceOpeningFrames"]["source-scene"]
    assert op.result_json["images"]["0"]["openingFrame"] == record["openingFrame"]


@pytest.mark.asyncio
async def test_openai_final_payload_uses_clean_canonical_action_and_preserves_setting(setup):
    _, row, _, client, scene, _, _ = setup
    row.context_json["referenceAnalysis"] = {"forbiddenReuse": ["Acme"]}
    scene.update(
        imagePrompt="Acme bottle closed on a wood table with red background",
        shotPlan={"shots": [{"stateBefore": "Acme lid closed", "stateAfter": "Acme lid open",
                            "physicalAction": {"contact": "hand on Acme cap"}}]},
    )
    await prepare(setup)
    prompt = client.calls[0]["prompt"]
    assert "Acme" not in prompt
    assert all(value in prompt for value in ("wood table", "red background", "closed", "hand"))


@pytest.mark.asyncio
async def test_changed_opening_binding_cannot_generate_with_a_midpoint_cache(setup):
    _, row, _, client, _, _, _ = setup
    row.context_json["sourceOpeningFrames"]["source-scene"]["layoutHash"] = "a" * 64
    with pytest.raises(AppError, match="SMART_REMAKE_IMAGE_ASSET_INVALID"):
        await prepare(setup)
    assert client.calls == []
