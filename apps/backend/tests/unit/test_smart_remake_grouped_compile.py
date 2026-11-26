from __future__ import annotations

import hashlib
from io import BytesIO
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import UploadFile

from viraldy.modules.smart_remake import timeline_compile as module
from viraldy.modules.smart_remake.fixture import FixtureGeminiClient
from viraldy.modules.smart_remake.timeline_planner import build_timeline_plan


@pytest.fixture(autouse=True)
def retained_opening_frame_bindings(monkeypatch):
    # These orchestration fixtures intentionally contain fake video buffers.
    # Real frame decoding and frame/hash binding have dedicated fidelity tests.
    monkeypatch.setattr(module, "source_opening_bindings", lambda source, scenes: {
        scene["id"]: {
            "sourceMediaHash": hashlib.sha256(source.bytes).hexdigest(),
            "frame": scene["startFrame"],
            "layoutHash": hashlib.sha256(
                f"opening:{scene['startFrame']}".encode()
            ).hexdigest(),
            "extractorVersion": "source-opening-frame-v1",
        }
        for scene in scenes
    })


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "source_matches,product_matches", [(True, True), (False, True), (True, False)]
)
@pytest.mark.parametrize("upload_inputs", [False, True])
async def test_recompile_carries_only_matching_owned_image_cache_and_freezes_policy(
    monkeypatch, source_matches, product_matches, upload_inputs
):
    wid, pid = uuid4(), uuid4()
    image_assets = {"request-hash": {"storageKey": "owned/images/key", "mediaHash": "image-hash"}}
    owned = SimpleNamespace(
        context_json={
            "sourceKey": "source-key",
            "sourceMimeType": "video/mp4",
            "productKey": "product-key",
            "productMimeType": "image/png",
            "sourceMediaHash": hashlib.sha256(
                b"source" if source_matches else b"changed"
            ).hexdigest(),
            "productMediaHash": hashlib.sha256(
                b"product" if product_matches else b"changed"
            ).hexdigest(),
            "imageAssets": image_assets,
        }
    )

    class Repository:
        lookups = 0

        async def project(self, workspace_id, project_id):
            assert (workspace_id, project_id) == (wid, pid)
            self.lookups += 1
            return owned

        async def create(self, row):
            self.created = row

    class Media:
        async def read(self, key):
            return b"source" if key == "source-key" else b"product"

        async def put(self, prefix, data, mime):
            return f"{prefix}/{uuid4()}"

        async def url(self, key):
            return f"https://media.test/{key}"

    repository, media = Repository(), Media()
    monkeypatch.setattr(module, "RepairRepository", lambda _: repository)
    monkeypatch.setattr(module, "RepairMediaStore", lambda _: media)
    monkeypatch.setattr(module, "S3StorageAdapter", lambda _: object())
    monkeypatch.setattr(module, "measure_video_frames", lambda _: 192)
    monkeypatch.setattr(
        module, "probe_media_bytes", lambda _: {"hasVideo": True, "durationSeconds": 8}
    )
    monkeypatch.setattr(module, "extract_source_excerpt", lambda source, **kwargs: source)
    monkeypatch.setattr(module, "extract_timeline_thumbnails", lambda *args: [b"jpeg", b"jpeg"])
    monkeypatch.setattr(
        module, "enrich_reference_analysis_with_detected_cuts", lambda analysis, _: analysis
    )
    monkeypatch.setattr(module, "get_openai_image_quality", lambda: "medium")
    result = await module.compile_timeline_request(
        session=object(),
        settings=SimpleNamespace(ai_mode="fixture"),
        workspace_id=wid,
        project_id=pid,
        mode="smart_remake",
        target_duration="8",
        aspect_ratio="9:16",
        language=None,
        prompt=None,
        description=None,
        product_url=None,
        product_title=None,
        product_description=None,
        reference_video=UploadFile(filename="source.mp4", file=BytesIO(b"source"))
        if upload_inputs
        else None,
        product_image=UploadFile(filename="product.png", file=BytesIO(b"product"))
        if upload_inputs
        else None,
        source_cut_frames=[0, 48, 192],
        render_group_breaks=[1],
    )
    assert repository.lookups == 1
    assert result["projectId"] != str(pid)
    assert len(result["renderPlan"]["groups"]) == 2
    assert result["renderPlan"]["renderGroupBreaks"] == [1]
    assert result["renderPlan"]["imageQuality"] == "medium"
    assert result["renderPlan"]["imageModel"] == "gpt-image-2.6-sunburst"
    assert result["renderPlan"]["imageComplexity"] == "high"
    assert repository.created.context_json.get("imageAssets", {}) == (
        image_assets if source_matches and product_matches else {}
    )
    image_assets["new"] = "must not alias the retained cache"
    assert "new" not in repository.created.context_json.get("imageAssets", {})


@pytest.mark.asyncio
async def test_grouped_scene_directions_do_not_reset_each_scene_to_a_new_eight_second_clip():
    fixture = FixtureGeminiClient()
    analysis = await fixture.generate_json(system_instruction="", prompt="16 seconds")
    lock = await fixture.generate_json(system_instruction="", prompt="product lock")
    result = module.build_timeline_compile(
        analysis=analysis,
        product_lock=lock,
        plan=build_timeline_plan(
            target_duration=16,
            source_frame_count=384,
            reference_start_frame=0,
            cut_frames=[0, 72, 192, 288, 384],
        ),
        language=None,
        mode="smart_remake",
    )
    for scene, duration in zip(result["sceneMap"]["scenes"], (3, 5, 4, 4), strict=True):
        direction = scene["videoPrompt"]
        assert f"{duration}-second source" in direction
        assert "raw clip" not in direction
        assert "8 seconds" not in direction
        assert "beginning" not in direction
        assert "local to this scene" in direction
