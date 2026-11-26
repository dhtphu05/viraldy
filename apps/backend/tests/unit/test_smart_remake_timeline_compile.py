from __future__ import annotations

import hashlib
from io import BytesIO
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import UploadFile

from viraldy.modules.smart_remake import timeline_compile as module
from viraldy.modules.smart_remake.engine.schemas import UploadedMedia
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
async def test_compile_prompts_preserve_each_source_action_at_original_timing():
    client = FixtureGeminiClient()
    analysis = await client.generate_json(system_instruction="", prompt="analyze 16 seconds")
    lock = await client.generate_json(system_instruction="", prompt="product lock")
    plan = build_timeline_plan(
        target_duration=16,
        source_frame_count=720,
        reference_start_frame=120,
        cut_frames=[0, 72, 192, 288, 384],
    )
    result = module.build_timeline_compile(
        analysis=analysis, product_lock=lock, plan=plan, language="Vietnamese", mode="smart_remake"
    )
    assert result["sceneMap"]["sceneCount"] == 4
    assert result["schemaVersion"] == 2
    assert [s["shotPlan"]["targetDuration"] for s in result["sceneMap"]["scenes"]] == [3, 5, 4, 4]
    assert result["sceneMap"]["scenes"][1]["sourceSegment"]["sourceTimeRange"] == {
        "startSecond": 8,
        "endSecond": 13,
    }
    assert result["sceneMap"]["scenes"][0]["shotPlan"]["shots"][0]["endSecond"] == 3
    assert all(
        u["prompt"] and u["imagePrompt"] and u["videoPrompt"] for u in result["renderPlan"]["units"]
    )
    assert "stretch" not in result["sceneMap"]["scenes"][0]["prompt"]


class Repository:
    async def create(self, row):
        self.row = row


class Media:
    def __init__(self):
        self.stored = []

    async def put(self, prefix, data, mime_type):
        self.stored.append((prefix, data, mime_type))
        return f"private/{len(self.stored)}"

    async def url(self, key):
        return f"https://private.test/{key}"


@pytest.mark.asyncio
async def test_initializer_retains_private_original_media_and_independent_unreviewed_draft():
    analysis = await FixtureGeminiClient().generate_json(system_instruction="", prompt="8 seconds")
    lock = await FixtureGeminiClient().generate_json(system_instruction="", prompt="product lock")
    plan = build_timeline_plan(
        target_duration=8, source_frame_count=480, reference_start_frame=96, cut_frames=[0, 48, 192]
    )
    result = module.build_timeline_compile(
        analysis=analysis, product_lock=lock, plan=plan, language=None, mode="smart_remake"
    )
    repository, media = Repository(), Media()
    row = await module.initialize_timeline_project(
        repository=repository,
        media=media,
        workspace_id=uuid4(),
        compile_result=result,
        source=UploadedMedia(bytes=b"original-source", mime_type="video/mp4"),
        product=UploadedMedia(bytes=b"product", mime_type="image/png"),
        source_probe={"durationSeconds": 20},
    )
    assert repository.row is row
    assert [value[1] for value in media.stored] == [b"original-source", b"product"]
    assert row.context_json["sourceKey"] == "private/1"
    assert row.context_json["productKey"] == "private/2"
    assert row.context_json["sourceMediaHash"]
    assert row.state_json["publishedTimeline"] is None
    assert [s["id"] for s in row.state_json["scenes"]] == [
        u["id"] for u in plan["renderPlan"]["units"]
    ]
    assert all(
        not i["reviewed"] and i["versionId"] is None
        for i in row.state_json["draftTimeline"]["items"]
    )
    assert row.state_json["status"] == "draft"


@pytest.mark.asyncio
async def test_compile_fixture_only_analyzes_selected_excerpt(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        module, "measure_video_frames", lambda data: 192 if data == b"excerpt" else 720
    )
    monkeypatch.setattr(
        module, "extract_timeline_thumbnails", lambda source, seconds: [b"jpeg"] * len(seconds)
    )
    monkeypatch.setattr(
        module,
        "probe_media_bytes",
        lambda _: {
            "hasVideo": True,
            "durationSeconds": 30,
            "effectiveWidth": 90,
            "effectiveHeight": 160,
        },
    )

    def extract(source, *, start_frame, total_frames):
        captured["range"] = (start_frame, total_frames)
        return UploadedMedia(bytes=b"excerpt", mime_type="video/mp4")

    monkeypatch.setattr(module, "extract_source_excerpt", extract)

    async def analyze(**kwargs):
        captured["gemini"] = kwargs["gemini"]
        captured["reference"] = kwargs["reference_video"].bytes
        return await FixtureGeminiClient().generate_json(system_instruction="", prompt="8 seconds")

    monkeypatch.setattr(module, "analyze_reference_video", analyze)
    monkeypatch.setattr(module, "enrich_reference_analysis_with_detected_cuts", lambda a, b: a)
    repository, media = Repository(), Media()
    monkeypatch.setattr(module, "RepairRepository", lambda _: repository)
    monkeypatch.setattr(module, "RepairMediaStore", lambda _: media)
    monkeypatch.setattr(module, "S3StorageAdapter", lambda _: object())
    result = await module.compile_timeline_request(
        session=object(),
        settings=SimpleNamespace(ai_mode="fixture"),
        workspace_id=uuid4(),
        mode="smart_remake",
        target_duration="8",
        aspect_ratio="9:16",
        language=None,
        prompt=None,
        description=None,
        product_url=None,
        product_title=None,
        product_description=None,
        reference_video=UploadFile(filename="reference.mp4", file=BytesIO(b"original-source")),
        product_image=UploadFile(filename="product.png", file=BytesIO(b"product")),
        reference_start_frame=96,
        source_cut_frames=[0, 48, 192],
    )
    assert captured["range"] == (96, 192)
    assert captured["reference"] == b"excerpt"
    assert isinstance(captured["gemini"], FixtureGeminiClient)
    assert result["projectId"] == str(repository.row.id)
    assert result["revision"] == 1


@pytest.mark.asyncio
async def test_recompile_loads_owned_source_and_product_without_public_url_fetch(monkeypatch):
    workspace_id, project_id = uuid4(), uuid4()
    row = SimpleNamespace(
        context_json={
            "sourceKey": "source-owned",
            "sourceMimeType": "video/mp4",
            "productKey": "product-owned",
            "productMimeType": "image/png",
        }
    )

    class OwnedRepository(Repository):
        async def project(self, wid, pid):
            assert (wid, pid) == (workspace_id, project_id)
            return row

    class ReadMedia(Media):
        async def read(self, key):
            return b"source" if key == "source-owned" else b"product"

    repository, media = OwnedRepository(), ReadMedia()
    monkeypatch.setattr(module, "measure_video_frames", lambda data: 192)
    monkeypatch.setattr(
        module, "extract_timeline_thumbnails", lambda source, seconds: [b"jpeg"] * len(seconds)
    )
    monkeypatch.setattr(module, "RepairRepository", lambda _: repository)
    monkeypatch.setattr(module, "RepairMediaStore", lambda _: media)
    monkeypatch.setattr(module, "S3StorageAdapter", lambda _: object())
    monkeypatch.setattr(
        module, "probe_media_bytes", lambda _: {"hasVideo": True, "durationSeconds": 8}
    )
    monkeypatch.setattr(module, "extract_source_excerpt", lambda source, **kwargs: source)
    monkeypatch.setattr(
        module, "enrich_reference_analysis_with_detected_cuts", lambda analysis, source: analysis
    )
    result = await module.compile_timeline_request(
        session=object(),
        settings=SimpleNamespace(ai_mode="fixture"),
        workspace_id=workspace_id,
        project_id=project_id,
        mode="smart_remake",
        target_duration="8",
        aspect_ratio="9:16",
        language=None,
        prompt=None,
        description=None,
        product_url=None,
        product_title=None,
        product_description=None,
        reference_video=None,
        product_image=None,
        source_cut_frames=[0, 192],
    )
    assert result["projectId"] != str(project_id)
    assert media.stored[0][1] == b"source"
    assert media.stored[1][1] == b"product"


def test_measured_video_coverage_does_not_follow_longer_audio(tmp_path):
    import subprocess

    from viraldy.modules.smart_remake.engine.media_binaries import ffmpeg_path

    source = tmp_path / "short-video-long-audio.mp4"
    subprocess.run(  # noqa: S603 - generated local fixture with fixed ffmpeg arguments
        [
            ffmpeg_path(),
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=90x160:rate=24:duration=3",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=10",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            str(source),
        ],
        check=True,
        capture_output=True,
    )
    assert module.measure_video_frames(source.read_bytes()) == 72


def test_excerpt_is_exact_24fps_and_thumbnails_are_real_jpeg(tmp_path):
    import subprocess

    from viraldy.modules.smart_remake.engine.media_binaries import ffmpeg_path
    from viraldy.modules.smart_remake.engine.media_probe import probe_media_bytes

    source = tmp_path / "source.mp4"
    subprocess.run(  # noqa: S603 - generated local fixture with fixed ffmpeg arguments
        [
            ffmpeg_path(),
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=90x160:rate=30:duration=12",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=12",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            str(source),
        ],
        check=True,
        capture_output=True,
    )
    excerpt = module.extract_source_excerpt(
        UploadedMedia(bytes=source.read_bytes(), mime_type="video/mp4"),
        start_frame=96,
        total_frames=192,
    )
    assert module.measure_video_frames(excerpt.bytes) == 192
    info = probe_media_bytes(excerpt.bytes)
    assert info["fps"] == 24 and abs(info["durationSeconds"] - 8) < 0.05
    thumbs = module.extract_timeline_thumbnails(excerpt, [1, 5])
    assert len(thumbs) == 2 and all(value.startswith(b"\xff\xd8") for value in thumbs)
