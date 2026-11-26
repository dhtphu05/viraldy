from __future__ import annotations

import copy

import pytest

from viraldy.modules.smart_remake.engine import reference_analyzer as analyzer
from viraldy.modules.smart_remake.engine import source_shot_detector as detector
from viraldy.modules.smart_remake.engine.prompts import build_reference_analysis_prompt
from viraldy.modules.smart_remake.fixture import FixtureGeminiClient
from viraldy.modules.smart_remake.timeline_compile import _local_shots, build_timeline_compile
from viraldy.modules.smart_remake.timeline_planner import build_timeline_plan


def source_analysis():
    return {
        "subjectPresence": "hands_only",
        "sourceShots": [
            {
                "shotIndex": 0,
                "startSecond": 0,
                "endSecond": 8,
                "durationSeconds": 8,
                "action": "open the lid then pour",
                "physicalAction": {
                    "operator": "right hand",
                    "contactPoint": "lid",
                    "movement": "twist",
                },
                "stateBefore": "closed",
                "stateAfter": "open",
            }
        ],
    }


def test_new_measured_cut_does_not_invent_semantics_or_repeat_parent_states():
    analysis = source_analysis()
    original = copy.deepcopy(analysis)
    result = detector.expand_source_shots_to_cut_boundaries(
        analysis, duration_seconds=8, cut_times=[4]
    )
    assert result["sourceCutDetection"]["requiresSemanticReanalysis"] is True
    assert result["sourceCutDetection"]["cutFrames"] == [0, 96, 192]
    assert result["sourceShots"] == original["sourceShots"]
    assert result.get("shotPreservationMode") != "exact"
    assert analysis == original


def test_unchanged_source_ranges_keep_physical_action():
    analysis = source_analysis()
    analysis["sourceShots"] = [
        {**analysis["sourceShots"][0], "endSecond": 4, "durationSeconds": 4},
        {**analysis["sourceShots"][0], "shotIndex": 1, "startSecond": 4, "stateBefore": "open"},
    ]
    result = detector.expand_source_shots_to_cut_boundaries(
        analysis, duration_seconds=8, cut_times=[4]
    )
    assert (
        result["sourceShots"][0]["physicalAction"] == analysis["sourceShots"][0]["physicalAction"]
    )


@pytest.mark.asyncio
async def test_one_semantic_reanalysis_uses_measured_ranges_and_same_budget_client():
    analysis = detector.expand_source_shots_to_cut_boundaries(
        source_analysis(), duration_seconds=8, cut_times=[4]
    )
    calls = []

    class Client:
        async def generate_json(self, **kwargs):
            calls.append(kwargs)
            result = source_analysis()
            result["sourceShots"] = [
                {
                    **result["sourceShots"][0],
                    "endSecond": 4,
                    "action": "open lid",
                    "stateAfter": "open",
                },
                {
                    **result["sourceShots"][0],
                    "shotIndex": 1,
                    "startSecond": 4,
                    "action": "pour",
                    "stateBefore": "open",
                    "stateAfter": "emptied",
                },
            ]
            return result

    from viraldy.modules.smart_remake.engine.schemas import UploadedMedia

    resolved = await analyzer.resolve_source_cut_semantics(
        analysis=analysis,
        target_duration=8,
        prompt=None,
        description=None,
        reference_video=UploadedMedia(bytes=b"owned", mime_type="video/mp4"),
        gemini=Client(),
    )
    assert len(calls) == 1
    assert "96" in calls[0]["prompt"] and "192" in calls[0]["prompt"]
    assert calls[0]["media"][0]["bytes"] == b"owned"
    assert resolved["sourceShots"][1]["action"] == "pour"
    assert resolved["sourceCutDetection"]["requiresSemanticReanalysis"] is False


@pytest.mark.asyncio
async def test_bad_semantic_reanalysis_stops_after_one_call():
    analysis = detector.expand_source_shots_to_cut_boundaries(
        source_analysis(), duration_seconds=8, cut_times=[4]
    )
    calls = []

    class Client:
        async def generate_json(self, **kwargs):
            calls.append(kwargs)
            return source_analysis()

    from viraldy.modules.smart_remake.engine.schemas import UploadedMedia

    with pytest.raises(Exception) as raised:
        await analyzer.resolve_source_cut_semantics(
            analysis=analysis,
            target_duration=8,
            prompt=None,
            description=None,
            reference_video=UploadedMedia(bytes=b"owned", mime_type="video/mp4"),
            gemini=Client(),
        )
    assert raised.value.code == "SMART_REMAKE_SOURCE_ANALYSIS_INCOMPLETE"
    assert len(calls) == 1


def test_source_excerpt_instructions_keep_speed_and_do_not_condense():
    _, prompt = build_reference_analysis_prompt(target_duration=8, has_video=True)
    assert "condense the full reference" not in prompt
    assert "original speed" in prompt


@pytest.mark.asyncio
@pytest.mark.parametrize("offset", [1 / 24, 2 / 24])
async def test_semantic_range_alignment_accepts_only_one_frame_tolerance(offset):
    analysis = detector.expand_source_shots_to_cut_boundaries(
        source_analysis(), duration_seconds=8, cut_times=[4]
    )

    class Client:
        async def generate_json(self, **kwargs):
            value = source_analysis()
            value["sourceShots"] = [
                {**value["sourceShots"][0], "endSecond": 4 + offset},
                {**value["sourceShots"][0], "startSecond": 4 + offset},
            ]
            return value

    from viraldy.modules.smart_remake.engine.schemas import UploadedMedia

    request = dict(
        analysis=analysis,
        target_duration=8,
        prompt=None,
        description=None,
        reference_video=UploadedMedia(bytes=b"owned", mime_type="video/mp4"),
        gemini=Client(),
    )
    if offset > 1 / 24:
        with pytest.raises(Exception, match="Source cuts"):
            await analyzer.resolve_source_cut_semantics(**request)
    else:
        value = await analyzer.resolve_source_cut_semantics(**request)
        assert value["sourceShots"][0]["endSecond"] == 4


@pytest.mark.asyncio
async def test_semantic_reanalysis_propagates_budget_rejection_without_retry():
    from viraldy.modules.smart_remake.engine.schemas import UploadedMedia
    from viraldy.shared.errors.base import AppError

    analysis = detector.expand_source_shots_to_cut_boundaries(
        source_analysis(), duration_seconds=8, cut_times=[4]
    )
    calls = []

    class Client:
        async def generate_json(self, **kwargs):
            calls.append(kwargs)
            raise AppError("SMART_REMAKE_BUDGET_EXCEEDED", "Cap reached", 409)

    with pytest.raises(AppError) as raised:
        await analyzer.resolve_source_cut_semantics(
            analysis=analysis,
            target_duration=8,
            prompt=None,
            description=None,
            reference_video=UploadedMedia(bytes=b"owned", mime_type="video/mp4"),
            gemini=Client(),
        )
    assert raised.value.code == "SMART_REMAKE_BUDGET_EXCEEDED"
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_compile_blocks_unsupported_source_and_empty_product_lock():
    client = FixtureGeminiClient()
    analysis = await client.generate_json(system_instruction="", prompt="8 seconds")
    lock = await client.generate_json(system_instruction="", prompt="product lock")
    plan = build_timeline_plan(
        target_duration=8, source_frame_count=192, reference_start_frame=0, cut_frames=[0, 96, 192]
    )
    with pytest.raises(Exception) as raised:
        build_timeline_compile(
            analysis={**analysis, "renderability": {"supported": False}},
            product_lock=lock,
            plan=plan,
            language=None,
            mode="smart_remake",
        )
    assert raised.value.code == "SMART_REMAKE_SOURCE_UNSUPPORTED"
    with pytest.raises(Exception) as raised:
        build_timeline_compile(
            analysis=analysis, product_lock={}, plan=plan, language=None, mode="smart_remake"
        )
    assert raised.value.code == "SMART_REMAKE_PRODUCT_ANALYSIS_INCOMPLETE"


@pytest.mark.asyncio
async def test_compiled_shot_plan_is_product_safe_and_raw_analysis_is_retained():
    client = FixtureGeminiClient()
    analysis = await client.generate_json(system_instruction="", prompt="8 seconds")
    analysis["forbiddenReuse"] = ["Acme"]
    analysis["sourceShots"][0]["action"] = "open the Acme lid beside a red wall"
    analysis["sourceShots"][0]["physicalAction"]["contactPoint"] = "Acme lid"
    original = copy.deepcopy(analysis)
    lock = await client.generate_json(system_instruction="", prompt="product lock")
    plan = build_timeline_plan(
        target_duration=8, source_frame_count=192, reference_start_frame=0, cut_frames=[0, 96, 192]
    )
    result = build_timeline_compile(
        analysis=analysis, product_lock=lock, plan=plan, language=None, mode="smart_remake"
    )
    shot = result["sceneMap"]["scenes"][0]["shotPlan"]["shots"][0]
    assert "Acme" not in str(shot)
    assert "red wall" in shot["action"]
    assert result["referenceAnalysis"] == original
    assert analysis == original


def test_manual_scene_clipping_does_not_copy_unobserved_parent_states():
    first = _local_shots(source_analysis(), 0, 4)[0]
    last = _local_shots(source_analysis(), 4, 8)[0]
    assert first["stateBefore"] == "closed"
    assert first["stateAfter"] is None
    assert last["stateBefore"] is None
    assert last["stateAfter"] == "open"


@pytest.mark.asyncio
async def test_manual_cut_inside_a_coarse_shot_gets_one_semantic_analysis():
    calls = []

    class Client:
        async def generate_json(self, **kwargs):
            calls.append(kwargs)
            value = source_analysis()
            value["sourceShots"] = [
                {**value["sourceShots"][0], "endSecond": 4, "action": "open lid"},
                {**value["sourceShots"][0], "startSecond": 4, "action": "pour"},
            ]
            return value

    from viraldy.modules.smart_remake.engine.schemas import UploadedMedia

    value = await analyzer.resolve_source_cut_semantics(
        analysis=source_analysis(),
        target_duration=8,
        prompt=None,
        description=None,
        reference_video=UploadedMedia(bytes=b"owned", mime_type="video/mp4"),
        gemini=Client(),
        requested_cut_frames=[0, 96, 192],
    )
    assert len(calls) == 1
    assert "do not imply visual cuts" in calls[0]["prompt"]
    assert [shot["action"] for shot in value["sourceShots"]] == ["open lid", "pour"]


@pytest.mark.asyncio
async def test_fixture_client_honors_explicit_intervals_without_becoming_live():
    _, prompt = build_reference_analysis_prompt(
        target_duration=8, has_video=True, source_cut_frames=[0, 48, 96, 192]
    )
    value = await FixtureGeminiClient().generate_json(system_instruction="", prompt=prompt)
    assert [(shot["startSecond"], shot["endSecond"]) for shot in value["sourceShots"]] == [
        (0, 2),
        (2, 4),
        (4, 8),
    ]


def test_opening_bindings_use_absolute_frames_and_owned_source_hash(monkeypatch):
    import hashlib

    from viraldy.modules.smart_remake import image_workflow
    from viraldy.modules.smart_remake.engine.schemas import UploadedMedia
    from viraldy.modules.smart_remake.timeline_compile import source_opening_bindings

    calls = []

    def extract(data, frame):
        calls.append((data, frame))
        return f"full-resolution-opening-{frame}".encode()

    monkeypatch.setattr(image_workflow, "extract_layout_frame", extract)
    result = source_opening_bindings(
        UploadedMedia(bytes=b"owned-original", mime_type="video/mp4"),
        [{"id": "first", "startFrame": 96}, {"id": "second", "startFrame": 144}],
    )
    assert calls == [(b"owned-original", 96), (b"owned-original", 144)]
    assert result["second"] == {
        "sourceMediaHash": hashlib.sha256(b"owned-original").hexdigest(),
        "frame": 144,
        "layoutHash": hashlib.sha256(b"full-resolution-opening-144").hexdigest(),
        "extractorVersion": "source-opening-frame-v1",
    }


def test_measured_cut_mismatch_is_resolved_even_when_shot_counts_match(monkeypatch):
    from viraldy.modules.smart_remake.engine.schemas import UploadedMedia

    analysis = source_analysis()
    analysis["sourceShots"] = [
        {**analysis["sourceShots"][0], "endSecond": 3},
        {**analysis["sourceShots"][0], "startSecond": 3},
    ]
    monkeypatch.setattr(detector, "detect_source_cuts", lambda *a, **k: (8, [4]))
    result = detector.enrich_reference_analysis_with_detected_cuts(
        analysis, UploadedMedia(bytes=b"owned", mime_type="video/mp4")
    )
    assert result["sourceCutDetection"]["requiresSemanticReanalysis"] is True
    assert result["sourceCutDetection"]["cutFrames"] == [0, 72, 96, 192]


@pytest.mark.asyncio
@pytest.mark.parametrize("incomplete", [False, True])
async def test_legacy_compile_uses_the_same_single_semantic_guard(monkeypatch, incomplete):
    from viraldy.modules.smart_remake.engine import compile_service
    from viraldy.modules.smart_remake.engine.schemas import CompileSmartRemakeRequest, UploadedMedia

    calls = []

    class Client:
        async def generate_json(self, **kwargs):
            calls.append(kwargs["prompt"])
            value = await FixtureGeminiClient().generate_json(**kwargs)
            if incomplete and "Required source analysis interval" in kwargs["prompt"]:
                value["sourceShots"] = source_analysis()["sourceShots"]
            return value

    monkeypatch.setattr(compile_service, "cleanup_smart_remake_assets", lambda: None)
    monkeypatch.setattr(
        compile_service, "attach_source_frame_assets", lambda **kwargs: kwargs["scene_map"]
    )
    monkeypatch.setattr(
        compile_service,
        "enrich_reference_analysis_with_detected_cuts",
        lambda a, b: {
            **a,
            "sourceCutDetection": {"requiresSemanticReanalysis": True, "cutFrames": [0, 96, 192]},
        },
    )
    request = CompileSmartRemakeRequest(
        targetDuration=8,
        aspectRatio="9:16",
        productSource="upload",
        referenceVideo=UploadedMedia(bytes=b"owned", mime_type="video/mp4"),
        productImage=UploadedMedia(bytes=b"product", mime_type="image/png"),
    )
    if incomplete:
        with pytest.raises(Exception) as raised:
            await compile_service.compile_smart_remake(request, gemini=Client())
        assert raised.value.code == "SMART_REMAKE_SOURCE_ANALYSIS_INCOMPLETE"
        assert len(calls) == 2
    else:
        result = await compile_service.compile_smart_remake(request, gemini=Client())
        assert result["success"] is True
        assert result["compilerVersion"] == "smart-remake-compiler-v2.1"
        assert len(calls) == 3  # source, one semantic pass, product lock


@pytest.mark.asyncio
async def test_initializer_freezes_opening_hash_and_public_expectations_binding(monkeypatch):
    import hashlib
    from types import SimpleNamespace
    from unittest.mock import AsyncMock
    from uuid import uuid4

    from viraldy.modules.smart_remake import image_workflow, timeline_compile
    from viraldy.modules.smart_remake.engine.schemas import UploadedMedia
    from viraldy.modules.smart_remake.generation_expectations import require_generation_expectations

    client = FixtureGeminiClient()
    result = build_timeline_compile(
        analysis=await client.generate_json(system_instruction="", prompt="8 seconds"),
        product_lock=await client.generate_json(system_instruction="", prompt="product lock"),
        plan=build_timeline_plan(
            target_duration=8,
            source_frame_count=480,
            reference_start_frame=96,
            cut_frames=[0, 96, 192],
        ),
        language=None,
        mode="smart_remake",
    )
    monkeypatch.setattr(
        image_workflow, "extract_layout_frame", lambda data, frame: str(frame).encode()
    )
    repository = SimpleNamespace(create=AsyncMock())
    media = SimpleNamespace(put=AsyncMock(side_effect=["owned-source", "owned-product"]))
    row = await timeline_compile.initialize_timeline_project(
        repository=repository,
        media=media,
        workspace_id=uuid4(),
        compile_result=result,
        source=UploadedMedia(bytes=b"source", mime_type="video/mp4"),
        product=UploadedMedia(bytes=b"product", mime_type="image/png"),
        source_probe={},
    )
    saved = require_generation_expectations(row.context_json)
    assert saved["scenes"][0]["openingFrame"]["frame"] == 96
    assert saved["scenes"][0]["openingFrame"]["layoutHash"] == hashlib.sha256(b"96").hexdigest()
    assert row.context_json["compileResult"]["expectationsVersion"] == 1
    assert (
        row.context_json["compileResult"]["expectationsHash"]
        == row.context_json["expectationsHash"]
    )
    assert len(row.context_json["expectationsHash"]) == 64


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "raw",
    [
        {},
        {
            "sourceShots": [
                {"startSecond": 0, "endSecond": 3, "action": "open lid"},
                {"startSecond": 4, "endSecond": 8, "action": "pour"},
            ]
        },
    ],
)
async def test_generic_or_gapped_initial_source_analysis_cannot_compile(raw):
    analysis = analyzer.normalize_reference_analysis(raw, 8)
    lock = await FixtureGeminiClient().generate_json(system_instruction="", prompt="product lock")
    plan = build_timeline_plan(
        target_duration=8, source_frame_count=192, reference_start_frame=0, cut_frames=[0, 192]
    )
    with pytest.raises(Exception) as raised:
        build_timeline_compile(
            analysis=analysis, product_lock=lock, plan=plan, language=None, mode="smart_remake"
        )
    assert raised.value.code == "SMART_REMAKE_SOURCE_ANALYSIS_INCOMPLETE"
