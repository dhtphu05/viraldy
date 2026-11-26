from __future__ import annotations

import copy
import hashlib
from io import BytesIO
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import UploadFile

from viraldy.modules.smart_remake import timeline_compile as module
from viraldy.modules.smart_remake.engine import reference_analyzer
from viraldy.modules.smart_remake.engine.schemas import UploadedMedia
from viraldy.modules.smart_remake.fixture import FixtureGeminiClient
from viraldy.modules.smart_remake.timeline_planner import build_timeline_plan
from viraldy.shared.errors.base import AppError


def full_analysis(count: int = 6, duration: int = 30) -> dict:
    return {
        "subjectPresence": "hands_only",
        "cameraStyle": {"angle": "front", "movement": "static"},
        "setting": {"locationType": "studio", "backgroundElements": ["red wall"]},
        "sourceShots": [
            {
                "shotIndex": index,
                "startSecond": index * duration / count,
                "endSecond": (index + 1) * duration / count,
                "durationSeconds": duration / count,
                "action": f"demonstrate distinct product action {index + 1}",
                "physicalAction": {"movement": f"movement {index + 1}"},
                "stateBefore": f"state {index + 1}",
                "stateAfter": f"state {index + 2}",
            }
            for index in range(count)
        ],
    }


@pytest.mark.asyncio
async def test_full_source_compiler_retains_every_logical_prompt_and_retimes_only_output():
    analysis = full_analysis()
    original = copy.deepcopy(analysis)
    lock = await FixtureGeminiClient().generate_json(system_instruction="", prompt="product lock")
    plan = build_timeline_plan(
        target_duration=16,
        source_frame_count=720,
        reference_start_frame=0,
        cut_frames=[0, 120, 240, 360, 480, 600, 720],
        timing_mode="fit_target",
    )
    result = module.build_timeline_compile(
        analysis=analysis, product_lock=lock, plan=plan, language=None, mode="smart_remake"
    )
    assert len(result["compiledPrompts"]) == len(result["sourceSceneMap"]["scenes"]) == 6
    assert sum(item["targetDurationFrames"] for item in result["draftTimeline"]["items"]) == 384
    assert result["referenceAnalysis"] == original
    for index, scene in enumerate(result["sceneMap"]["scenes"]):
        assert scene["sourceSegment"]["sourceTimeRange"] == {
            "startSecond": index * 5,
            "endSecond": (index + 1) * 5,
        }
        assert scene["shotPlan"]["shots"][0]["endSecond"] == pytest.approx(64 / 24)
        assert "original speed" not in scene["videoPrompt"]
        assert f"action {index + 1}" in scene["videoPrompt"]


@pytest.mark.asyncio
async def test_continuous_source_has_one_logical_prompt_and_distinct_provider_fragments():
    lock = await FixtureGeminiClient().generate_json(system_instruction="", prompt="product lock")
    plan = build_timeline_plan(
        target_duration=16,
        source_frame_count=720,
        reference_start_frame=0,
        cut_frames=[0, 720],
        timing_mode="fit_target",
    )
    analysis = full_analysis(count=2)
    analysis["sourceShots"][0].update(
        action="open the lid",
        stateBefore="closed",
        stateAfter="open",
        physicalAction={"movement": "twist lid"},
    )
    analysis["sourceShots"][1].update(
        action="pour the drink",
        stateBefore="open",
        stateAfter="emptied",
        physicalAction={"movement": "tilt product"},
    )
    result = module.build_timeline_compile(
        analysis=analysis, product_lock=lock, plan=plan, language=None, mode="smart_remake"
    )
    assert len(result["sourceSceneMap"]["scenes"]) == len(result["compiledPrompts"]) == 1
    assert len(result["sceneMap"]["scenes"]) == 2
    first, second = result["sceneMap"]["scenes"]
    assert first["shotPlan"]["shots"][0]["stateBefore"] == "closed"
    assert second["shotPlan"]["shots"][0]["stateBefore"] == "open"
    assert second["shotPlan"]["shots"][0]["physicalAction"]["movement"] == "tilt product"
    assert second["sourceSegment"]["sourceTimeRange"]["startSecond"] == 15
    assert second["sourceSegment"]["boundary"]["kind"] == "source_continuation"
    canonical = result["sourceSceneMap"]["scenes"][0]["shotPlan"]
    assert canonical["cutTimes"] == []
    assert canonical["visualStructure"] == "continuous"
    assert canonical["shotCount"] == 1
    assert all(scene["shotPlan"]["shots"][0]["endSecond"] == 8 for scene in (first, second))


@pytest.mark.asyncio
async def test_coarse_action_cannot_be_copied_into_new_provider_fragment_ranges():
    lock = await FixtureGeminiClient().generate_json(system_instruction="", prompt="product lock")
    plan = build_timeline_plan(
        target_duration=16,
        source_frame_count=720,
        reference_start_frame=0,
        cut_frames=[0, 720],
        timing_mode="fit_target",
    )
    with pytest.raises(Exception) as failure:
        module.build_timeline_compile(
            analysis=full_analysis(count=1),
            product_lock=lock,
            plan=plan,
            language=None,
            mode="smart_remake",
        )
    assert failure.value.code == "SMART_REMAKE_SOURCE_ANALYSIS_INCOMPLETE"


@pytest.mark.asyncio
async def test_full_source_request_analyzes_original_bytes_and_absolute_thumbnails(monkeypatch):
    calls = []
    thumbnails = []

    async def analyze(**kwargs):
        calls.append(kwargs)
        return full_analysis()

    class Repository:
        async def create(self, row):
            self.row = row

    class Media:
        async def put(self, prefix, data, mime_type):
            return f"private/{uuid4()}"

        async def url(self, key):
            return f"https://private.test/{key}"

    repository, media = Repository(), Media()
    monkeypatch.setattr(module, "measure_video_frames", lambda _: 720)
    monkeypatch.setattr(
        module, "probe_media_bytes", lambda _: {"hasVideo": True, "durationSeconds": 30}
    )
    monkeypatch.setattr(
        module, "extract_source_excerpt", lambda *a, **k: pytest.fail("must not crop full source")
    )
    monkeypatch.setattr(module, "analyze_reference_video", analyze)
    monkeypatch.setattr(module, "enrich_reference_analysis_with_detected_cuts", lambda a, b: a)
    monkeypatch.setattr(module, "RepairRepository", lambda _: repository)
    monkeypatch.setattr(module, "RepairMediaStore", lambda _: media)
    monkeypatch.setattr(module, "S3StorageAdapter", lambda _: object())
    monkeypatch.setattr(module, "source_opening_bindings", lambda source, scenes: {})

    def extract_thumbnails(source, seconds):
        thumbnails.append((source.bytes, seconds))
        return []

    monkeypatch.setattr(module, "extract_timeline_thumbnails", extract_thumbnails)

    async def initialize(**kwargs):
        return SimpleNamespace(
            id=uuid4(),
            revision=1,
            context_json={
                "expectationsHash": "a" * 64,
                "sourceThumbnailKeys": {},
            },
        )

    monkeypatch.setattr(module, "initialize_timeline_project", initialize)
    result = await module.compile_timeline_request(
        session=object(),
        settings=SimpleNamespace(ai_mode="fixture"),
        workspace_id=uuid4(),
        mode="smart_remake",
        target_duration="16",
        aspect_ratio="9:16",
        language=None,
        prompt=None,
        description=None,
        product_url=None,
        product_title=None,
        product_description=None,
        reference_video=UploadFile(filename="reference.mp4", file=BytesIO(b"original-source")),
        product_image=UploadFile(filename="product.png", file=BytesIO(b"product")),
        analysis_scope="full_source",
    )
    assert calls[0]["reference_video"].bytes == b"original-source"
    assert calls[0]["target_duration"] == 30
    assert len(calls) == 1
    assert thumbnails == [(b"original-source", [2.5, 7.5, 12.5, 17.5, 22.5, 27.5])]
    assert result["sourceSceneMap"]["scenes"][-1]["endFrame"] == 720
    assert result["inputSummary"]["analysisScope"] == "full_source"


@pytest.mark.asyncio
async def test_fixture_analysis_uses_the_full_measured_source_clock():
    result = await reference_analyzer.analyze_reference_video(
        target_duration=30.5,
        prompt=None,
        description=None,
        reference_video=UploadedMedia(bytes=b"owned-source", mime_type="video/mp4"),
        gemini=FixtureGeminiClient(),
    )
    reference_analyzer.validate_source_analysis(result, target_duration=30.5)
    assert result["sourceShots"][-1]["endSecond"] == 30.5


@pytest.mark.asyncio
async def test_continuous_full_source_gets_one_semantic_pass_for_provider_boundaries(monkeypatch):
    calls = []

    async def analyze(**kwargs):
        calls.append(kwargs)
        if kwargs.get("source_cut_frames"):
            resolved = full_analysis(count=2)
            resolved["sourceShots"][0].update(
                action="open the lid",
                stateBefore="closed",
                stateAfter="open",
                physicalAction={"movement": "twist lid"},
            )
            resolved["sourceShots"][1].update(
                action="pour the drink",
                stateBefore="open",
                stateAfter="emptied",
                physicalAction={"movement": "tilt product"},
            )
            return resolved
        return full_analysis(count=1)

    async def initialize(**kwargs):
        return SimpleNamespace(
            id=uuid4(),
            revision=1,
            context_json={
                "expectationsHash": "a" * 64,
                "sourceThumbnailKeys": {},
                "compileResult": kwargs["compile_result"],
            },
        )

    monkeypatch.setattr(module, "measure_video_frames", lambda _: 720)
    monkeypatch.setattr(
        module, "probe_media_bytes", lambda _: {"hasVideo": True, "durationSeconds": 30}
    )
    monkeypatch.setattr(module, "analyze_reference_video", analyze)
    monkeypatch.setattr(reference_analyzer, "analyze_reference_video", analyze)
    monkeypatch.setattr(module, "enrich_reference_analysis_with_detected_cuts", lambda a, b: a)
    monkeypatch.setattr(module, "extract_timeline_thumbnails", lambda *args: [])
    monkeypatch.setattr(module, "initialize_timeline_project", initialize)
    monkeypatch.setattr(module, "S3StorageAdapter", lambda _: object())
    result = await module.compile_timeline_request(
        session=object(),
        settings=SimpleNamespace(ai_mode="fixture"),
        workspace_id=uuid4(),
        mode="smart_remake",
        target_duration="16",
        aspect_ratio="9:16",
        language=None,
        prompt=None,
        description=None,
        product_url=None,
        product_title=None,
        product_description=None,
        reference_video=UploadFile(filename="reference.mp4", file=BytesIO(b"source")),
        product_image=UploadFile(filename="product.png", file=BytesIO(b"product")),
        analysis_scope="full_source",
    )
    assert len(calls) == 2
    assert calls[1]["source_cut_frames"] == [0, 360, 720]
    assert all(call["reference_video"].bytes == b"source" for call in calls)
    assert len(result["sourceSceneMap"]["scenes"]) == len(result["compiledPrompts"]) == 1
    assert result["sceneMap"]["scenes"][1]["shotPlan"]["shots"][0]["stateBefore"] == "open"
    assert result["sceneMap"]["scenes"][1]["shotPlan"]["shots"][0]["action"] == "pour the drink"


def test_observed_actions_are_not_silently_dropped_to_fit_one_output_frame():
    from viraldy.modules.smart_remake.source_timing import fit_observed_shots

    with pytest.raises(Exception) as failure:
        fit_observed_shots(
            [{"startSecond": 0, "endSecond": 1}, {"startSecond": 1, "endSecond": 2}],
            source_start=0,
            source_end=2,
            target_frames=1,
        )
    assert failure.value.code == "SMART_REMAKE_OUTPUT_DENSITY_UNSUPPORTED"


@pytest.mark.asyncio
async def test_initialization_binds_each_provider_fragment_to_its_own_source_opening(monkeypatch):
    analysis = full_analysis(count=2)
    lock = await FixtureGeminiClient().generate_json(system_instruction="", prompt="product lock")
    plan = build_timeline_plan(
        target_duration=16,
        source_frame_count=720,
        reference_start_frame=0,
        cut_frames=[0, 720],
        timing_mode="fit_target",
    )
    result = module.build_timeline_compile(
        analysis=analysis, product_lock=lock, plan=plan, language=None, mode="smart_remake"
    )
    observed = []

    def bindings(source, scenes):
        observed.extend(scenes)
        return {
            scene["id"]: {
                "sourceMediaHash": hashlib.sha256(source.bytes).hexdigest(),
                "frame": scene["startFrame"],
                "layoutHash": hashlib.sha256(str(scene["startFrame"]).encode()).hexdigest(),
                "extractorVersion": "source-opening-frame-v1",
            }
            for scene in scenes
        }

    class Repository:
        async def create(self, row):
            self.row = row

    class Media:
        async def put(self, prefix, data, mime_type):
            return f"private/{uuid4()}"

    monkeypatch.setattr(module, "source_opening_bindings", bindings)
    row = await module.initialize_timeline_project(
        repository=Repository(),
        media=Media(),
        workspace_id=uuid4(),
        compile_result=result,
        source=UploadedMedia(bytes=b"source", mime_type="video/mp4"),
        product=UploadedMedia(bytes=b"product", mime_type="image/png"),
        source_probe={"durationSeconds": 30},
    )
    units = row.context_json["renderPlan"]["units"]
    assert observed == [
        {"id": units[0]["id"], "startFrame": 0},
        {"id": units[1]["id"], "startFrame": 360},
    ]
    assert set(row.context_json["sourceOpeningFrames"]) == {unit["id"] for unit in units}
    assert [
        scene["openingFrame"]["frame"]
        for scene in row.context_json["generationExpectations"]["scenes"]
    ] == [0, 360]


@pytest.mark.asyncio
async def test_full_analysis_checkpoint_survives_a_later_planning_failure(monkeypatch):
    from viraldy.modules.smart_remake import project_intake, project_policy

    operation = SimpleNamespace(id=uuid4(), result_json={})
    row = SimpleNamespace(
        id=uuid4(),
        context_json={
            "p0": {"targetDuration": 16, "requirements": {}},
            "sourceMediaHash": hashlib.sha256(b"source").hexdigest(),
            "productMediaHash": hashlib.sha256(b"product").hexdigest(),
        },
        state_json={"revision": 1},
    )
    finished = []

    class Repository:
        async def project(self, *args):
            return row

        async def start(self, *args):
            return row, operation, True

        async def finish(self, current, status, result):
            finished.append((status, result))

    class Session:
        async def scalars(self, statement):
            return []

        async def commit(self):
            return None

        async def refresh(self, *args, **kwargs):
            return None

    async def no_input_read(*args):
        return None

    async def analyze(**kwargs):
        return full_analysis()

    def fail_plan(**kwargs):
        raise AppError("SMART_REMAKE_OUTPUT_DENSITY_UNSUPPORTED", "Too dense", 409)

    monkeypatch.setattr(project_policy, "assert_project_policy", lambda *a, **k: None)
    monkeypatch.setattr(project_intake, "assert_input_binding", no_input_read)
    monkeypatch.setattr(module, "RepairRepository", lambda _: Repository())
    monkeypatch.setattr(module, "S3StorageAdapter", lambda _: object())
    monkeypatch.setattr(module, "measure_video_frames", lambda _: 720)
    monkeypatch.setattr(
        module, "probe_media_bytes", lambda _: {"hasVideo": True, "durationSeconds": 30}
    )
    monkeypatch.setattr(module, "analyze_reference_video", analyze)
    monkeypatch.setattr(module, "enrich_reference_analysis_with_detected_cuts", lambda a, b: a)
    monkeypatch.setattr(module, "build_timeline_plan", fail_plan)
    with pytest.raises(AppError):
        await module.compile_timeline_request(
            session=Session(),
            settings=SimpleNamespace(ai_mode="fixture"),
            workspace_id=uuid4(),
            project_id=uuid4(),
            expected_revision=1,
            idempotency_key="full-source-once",
            mode="smart_remake",
            target_duration="16",
            aspect_ratio="9:16",
            language=None,
            prompt=None,
            description=None,
            product_url=None,
            product_title=None,
            product_description=None,
            reference_video=UploadFile(filename="reference.mp4", file=BytesIO(b"source")),
            product_image=UploadFile(filename="product.png", file=BytesIO(b"product")),
            analysis_scope="full_source",
        )
    assert finished[0][0] == "failed"
    checkpoint = finished[0][1]["sourceAnalysisCheckpoint"]
    assert checkpoint["sourceFrameCount"] == 720
    assert len(checkpoint["analysis"]["sourceShots"]) == 6
    assert checkpoint["sourceMediaHash"] == hashlib.sha256(b"source").hexdigest()


@pytest.mark.asyncio
async def test_late_source_motion_beat_reaches_its_retimed_scene_and_kie_payload():
    from viraldy.modules.smart_remake.engine.kie_adapter import build_kie_group_request

    analysis = full_analysis()
    analysis["sourceShots"][4]["action"] = "rotate the target product to show its base"
    analysis["sourceShots"][4]["transitionOut"] = "match cut to the final hero shot"
    analysis["motionBeats"] = [
        {**copy.deepcopy(shot), "priority": "mandatory", "role": "demonstration"}
        for shot in analysis["sourceShots"]
    ]
    analysis["pacingPlan"] = {
        "pace": "fast",
        "motionIntensity": "high",
        "cutStyle": "hard_cut",
        "shotCount": 6,
    }
    original = copy.deepcopy(analysis)
    lock = await FixtureGeminiClient().generate_json(system_instruction="", prompt="product lock")
    plan = build_timeline_plan(
        target_duration=8,
        source_frame_count=720,
        reference_start_frame=0,
        cut_frames=[0, 120, 240, 360, 480, 600, 720],
        timing_mode="fit_target",
    )
    result = module.build_timeline_compile(
        analysis=analysis, product_lock=lock, plan=plan, language=None, mode="smart_remake"
    )
    scene = result["sceneMap"]["scenes"][4]
    beat = scene["shotPlan"]["motionBeats"][0]
    assert beat["sourceBeatIndex"] == 4
    assert beat["sourceTimeRange"] == {"startSecond": 20, "endSecond": 25}
    assert beat["startSecond"] == 0 and beat["endSecond"] == pytest.approx(32 / 24)
    assert beat["priority"] == "mandatory"
    assert scene["shotPlan"]["pacingPlan"]["motionIntensity"] == "high"
    assert scene["shotPlan"]["pacingPlan"]["cutStyle"] == "continuous"
    assert len(scene["shotPlan"]["pacingPlan"]["actionBeats"]) == 1
    request = build_kie_group_request(
        scenes=[scene],
        segments=[{"inFrame": 0, "outFrame": 32}],
        reference_image_urls=["https://1.1.1.1/opening.png", "https://1.1.1.1/ending.png"],
        product_lock=lock,
        reference_analysis=analysis,
    )
    prompt = request["input"]["prompt"]
    assert "[00:00.000–00:01.333] SCENE 1" in prompt
    assert "0–1.333s:" in prompt
    assert "rotate the target product to show its base" in prompt
    assert "match cut to the final hero shot" in prompt
    assert analysis == original


@pytest.mark.asyncio
async def test_cross_window_motion_beat_uses_observed_fragment_actions_without_reopening():
    analysis = full_analysis(count=2)
    analysis["sourceShots"][0].update(action="open lid", stateBefore="closed", stateAfter="open")
    analysis["sourceShots"][1].update(action="pour drink", stateBefore="open", stateAfter="emptied")
    analysis["motionBeats"] = [
        {
            "startSecond": 0,
            "endSecond": 30,
            "action": "open lid then pour drink",
            "stateBefore": "closed",
            "stateAfter": "emptied",
            "priority": "mandatory",
            "physicalAction": {"movement": "twist lid then tilt"},
        }
    ]
    lock = await FixtureGeminiClient().generate_json(system_instruction="", prompt="product lock")
    plan = build_timeline_plan(
        target_duration=16,
        source_frame_count=720,
        reference_start_frame=0,
        cut_frames=[0, 720],
        timing_mode="fit_target",
    )
    result = module.build_timeline_compile(
        analysis=analysis, product_lock=lock, plan=plan, language=None, mode="smart_remake"
    )
    second = result["sceneMap"]["scenes"][1]["shotPlan"]["motionBeats"][0]
    assert second["action"] == "pour drink" and second["stateBefore"] == "open"
    assert second["sourceTimeRange"] == {"startSecond": 15, "endSecond": 30}
    assert second["continuesFromPreviousWindow"] is True
    assert "open lid" not in second["action"]


@pytest.mark.asyncio
async def test_fractional_source_seconds_do_not_invent_overlapping_one_frame_actions():
    from viraldy.modules.smart_remake.timeline_planner import source_boundaries

    analysis = await reference_analyzer.analyze_reference_video(
        target_duration=30.5,
        prompt=None,
        description=None,
        reference_video=UploadedMedia(bytes=b"owned-source", mime_type="video/mp4"),
        gemini=FixtureGeminiClient(),
    )
    lock = await FixtureGeminiClient().generate_json(system_instruction="", prompt="product lock")
    plan = build_timeline_plan(
        target_duration=8,
        source_frame_count=732,
        reference_start_frame=0,
        cut_frames=source_boundaries(analysis, total_frames=732),
        timing_mode="fit_target",
    )
    result = module.build_timeline_compile(
        analysis=analysis, product_lock=lock, plan=plan, language=None, mode="smart_remake"
    )
    assert len(result["compiledPrompts"]) == 8
    assert all(len(scene["shotPlan"]["shots"]) == 1 for scene in result["sceneMap"]["scenes"])


@pytest.mark.asyncio
async def test_uneven_source_splits_at_global_eight_second_window_with_one_semantic_pass(
    monkeypatch,
):
    boundaries = [0, 225, 450, 720]
    original = full_analysis(count=3)
    for shot, start, end in zip(
        original["sourceShots"], boundaries, boundaries[1:], strict=False,
    ):
        shot.update(startSecond=start / 24, endSecond=end / 24, durationSeconds=(end-start) / 24)
    original["sourceShots"][1].update(
        action="open the lid then pour the drink", stateBefore="closed", stateAfter="emptied",
    )
    original["motionBeats"] = copy.deepcopy(original["sourceShots"])
    original["pacingPlan"] = {"pace": "medium", "motionIntensity": "high", "cutStyle": "soft_cut"}
    resolved = copy.deepcopy(original)
    opening, middle, final = resolved["sourceShots"]
    resolved["sourceShots"] = [
        opening,
        {**middle, "endSecond": 15, "durationSeconds": 135 / 24,
         "action": "open the lid", "stateAfter": "open",
         "physicalAction": {"movement": "twist the lid"}, "transitionOut": "continuous"},
        {**middle, "shotIndex": 2, "startSecond": 15, "durationSeconds": 90 / 24,
         "action": "pour the drink", "stateBefore": "open",
         "physicalAction": {"movement": "tilt the product"}},
        {**final, "shotIndex": 3},
    ]
    calls = []
    openings = []

    async def analyze(**kwargs):
        calls.append(kwargs)
        return copy.deepcopy(resolved if kwargs.get("source_cut_frames") else original)

    class Repository:
        async def create(self, row):
            self.row = row

    class Media:
        async def put(self, prefix, data, mime_type):
            return f"private/{uuid4()}"

        async def url(self, key):
            return f"https://private.test/{key}"

    repository, media = Repository(), Media()

    def bindings(source, scenes):
        openings.extend(scenes)
        return {scene["id"]: {
            "sourceMediaHash": hashlib.sha256(source.bytes).hexdigest(),
            "frame": scene["startFrame"],
            "layoutHash": hashlib.sha256(str(scene["startFrame"]).encode()).hexdigest(),
            "extractorVersion": "source-opening-frame-v1",
        } for scene in scenes}

    monkeypatch.setattr(module, "measure_video_frames", lambda _: 720)
    monkeypatch.setattr(
        module, "probe_media_bytes", lambda _: {"hasVideo": True, "durationSeconds": 30}
    )
    monkeypatch.setattr(module, "analyze_reference_video", analyze)
    monkeypatch.setattr(reference_analyzer, "analyze_reference_video", analyze)
    monkeypatch.setattr(module, "enrich_reference_analysis_with_detected_cuts", lambda a, b: a)
    monkeypatch.setattr(module, "extract_timeline_thumbnails", lambda *args: [])
    monkeypatch.setattr(module, "source_opening_bindings", bindings)
    monkeypatch.setattr(module, "RepairRepository", lambda _: repository)
    monkeypatch.setattr(module, "RepairMediaStore", lambda _: media)
    monkeypatch.setattr(module, "S3StorageAdapter", lambda _: object())
    result = await module.compile_timeline_request(
        session=object(), settings=SimpleNamespace(ai_mode="fixture"), workspace_id=uuid4(),
        mode="smart_remake", target_duration="16", aspect_ratio="9:16", language=None,
        prompt=None, description=None, product_url=None, product_title=None,
        product_description=None,
        reference_video=UploadFile(filename="source.mp4", file=BytesIO(b"source")),
        product_image=UploadFile(filename="product.png", file=BytesIO(b"product")),
        analysis_scope="full_source",
    )
    assert len(calls) == 2
    assert calls[1]["source_cut_frames"] == [0, 225, 360, 450, 720]
    assert len(result["compiledPrompts"]) == len(result["sourceSceneMap"]["scenes"]) == 3
    assert result["compilerVersion"] == "smart-remake-timeline-v2.3"
    plan = result["renderPlan"]
    assert plan["groupingPolicy"] == "fixed_provider_windows" and len(plan["groups"]) == 2
    assert [unit["targetDurationFrames"] for unit in plan["units"]] == [120, 72, 48, 144]
    assert [item["startFrame"] for item in openings] == [0, 225, 360, 450]
    scenes = result["sceneMap"]["scenes"]
    assert scenes[1]["shotPlan"]["shots"][0]["stateBefore"] == "closed"
    continuation = scenes[2]["shotPlan"]
    assert continuation["sourceSegment"]["boundary"]["kind"] == "source_continuation"
    assert continuation["shots"][0]["action"] == "pour the drink"
    assert continuation["shots"][0]["physicalAction"]["movement"] == "tilt the product"
    beat = continuation["motionBeats"][0]
    assert beat["sourceBeatIndex"] == 1 and beat["startSecond"] == 0 and beat["endSecond"] == 2
    assert beat["action"] == "pour the drink" and beat["stateBefore"] == "open"
    assert beat["sourceTimeRange"] == {"startSecond": 15, "endSecond": 18.75}
    assert continuation["pacingPlan"]["pace"] == "medium"
    assert result["sourceSceneMap"]["scenes"][1]["shotPlan"]["cutTimes"] == []
    assert [scene["openingFrame"]["frame"] for scene in
            repository.row.context_json["generationExpectations"]["scenes"]] == [0, 225, 360, 450]


def test_supplemental_analysis_instructions_distinguish_intervals_from_visual_shots():
    from viraldy.modules.smart_remake.engine.prompts import build_reference_analysis_prompt

    _, initial = build_reference_analysis_prompt(target_duration=30, has_video=True)
    _, supplemental = build_reference_analysis_prompt(
        target_duration=30, has_video=True, source_cut_frames=[0, 225, 360, 450, 720],
    )
    assert "return one sourceShot with one combined action" in initial
    assert "return one sourceShot with one combined action" not in supplemental
    assert "exactly one sourceShot per adjacent frame range" in supplemental
    assert "pacingPlan.shotCount and cutStyle describe actual visual shots" in supplemental


def test_subframe_source_action_cannot_become_an_empty_interval():
    from viraldy.modules.smart_remake.source_timing import source_frame_clock_analysis

    observed = {"sourceShots": [{"startSecond": 0.001, "endSecond": 0.002}]}
    with pytest.raises(AppError) as failure:
        source_frame_clock_analysis(observed)
    assert failure.value.code == "SMART_REMAKE_SOURCE_ANALYSIS_INCOMPLETE"
    assert observed["sourceShots"][0]["endSecond"] == 0.002
