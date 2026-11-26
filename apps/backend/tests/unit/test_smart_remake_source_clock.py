from __future__ import annotations

import copy
from io import BytesIO
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import UploadFile

from viraldy.modules.smart_remake import timeline_compile
from viraldy.modules.smart_remake.engine import reference_analyzer, source_shot_detector
from viraldy.modules.smart_remake.source_timing import source_frame_clock_analysis
from viraldy.shared.errors.base import AppError


def source_analysis(end: float) -> dict:
    shot = {
        "shotIndex": 0,
        "startSecond": 0,
        "endSecond": end,
        "durationSeconds": end,
        "action": "turn the bottle to reveal its cap and label",
        "physicalAction": {"movement": "rotate bottle"},
        "stateBefore": "bottle faces away",
        "stateAfter": "label faces the viewer",
    }
    return {
        "subjectPresence": "hands_only",
        "cameraStyle": {"angle": "front", "movement": "static"},
        "setting": {"locationType": "studio", "backgroundElements": ["table"]},
        "sourceShots": [shot],
        "motionBeats": [copy.deepcopy(shot)],
    }


@pytest.mark.parametrize("observed_end", [22.777, 22.72])
def test_measured_source_clock_aligns_only_terminal_quantization_without_mutating_evidence(
    observed_end,
):
    analysis = source_analysis(observed_end)
    original = copy.deepcopy(analysis)

    aligned = source_frame_clock_analysis(analysis, source_frame_count=546)

    assert analysis == original
    assert aligned["sourceShots"][0]["endSecond"] == 546 / 24
    assert aligned["motionBeats"][0]["endSecond"] == 546 / 24
    assert aligned["sourceShots"][0]["durationSeconds"] == 546 / 24
    assert aligned["sourceShots"][0]["action"] == original["sourceShots"][0]["action"]
    reference_analyzer.validate_source_analysis(aligned, target_duration=546 / 24)


@pytest.mark.parametrize("observed_end", [22.6, 23.0])
def test_measured_source_clock_does_not_hide_missing_or_excess_observed_evidence(observed_end):
    analysis = source_analysis(observed_end)
    original = copy.deepcopy(analysis)

    with pytest.raises(AppError) as failure:
        aligned = source_frame_clock_analysis(analysis, source_frame_count=546)
        reference_analyzer.validate_source_analysis(aligned, target_duration=546 / 24)

    assert failure.value.code == "SMART_REMAKE_SOURCE_ANALYSIS_INCOMPLETE"
    assert analysis == original


@pytest.mark.parametrize("frame_error", [-1.49, 1.49])
def test_terminal_tolerance_uses_original_observed_time_before_frame_rounding(frame_error):
    analysis = source_analysis((546 + frame_error) / 24)
    original = copy.deepcopy(analysis)

    with pytest.raises(AppError) as failure:
        source_frame_clock_analysis(analysis, source_frame_count=546)

    assert failure.value.code == "SMART_REMAKE_SOURCE_ANALYSIS_INCOMPLETE"
    assert analysis == original


@pytest.mark.parametrize(
    "detected_cuts",
    [[0, 192, 384, 547], [0, 192, 384, 600, 720], [0, 192, 384, 546, 547]],
)
def test_detected_cuts_use_video_endpoint_and_ignore_audio_only_tail(detected_cuts):
    analysis = {
        **source_analysis(22.75),
        "sourceCutDetection": {
            "requiresSemanticReanalysis": True,
            "cutFrames": detected_cuts,
            "detectedCutCount": len(detected_cuts) - 2,
        },
    }
    original = copy.deepcopy(analysis)

    aligned = source_frame_clock_analysis(analysis, source_frame_count=546)

    assert aligned["sourceCutDetection"]["cutFrames"] == [0, 192, 384, 546]
    assert aligned["sourceCutDetection"]["requiresSemanticReanalysis"] is True
    assert analysis == original


async def compile_source_analysis(
    monkeypatch,
    raw_analysis,
    calls,
    *,
    container_duration=22.777,
    detected_cuts=(),
    incomplete_supplemental=False,
):
    async def analyze(**kwargs):
        calls.append(kwargs)
        cuts = kwargs.get("source_cut_frames")
        if cuts is None:
            return raw_analysis
        if incomplete_supplemental:
            return source_analysis(0.22)
        result = source_analysis(cuts[-1] / 24)
        result["sourceShots"] = [
            {
                **copy.deepcopy(result["sourceShots"][0]),
                "shotIndex": index,
                "startSecond": start / 24,
                "endSecond": end / 24,
                "durationSeconds": (end - start) / 24,
                "action": f"demonstrate observed bottle action {index + 1}",
            }
            for index, (start, end) in enumerate(zip(cuts, cuts[1:], strict=False))
        ]
        result["motionBeats"] = copy.deepcopy(result["sourceShots"])
        return result

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

    monkeypatch.setattr(timeline_compile, "measure_video_frames", lambda _: 546)
    monkeypatch.setattr(
        timeline_compile,
        "probe_media_bytes",
        lambda _: {"hasVideo": True, "durationSeconds": container_duration},
    )
    monkeypatch.setattr(
        source_shot_detector,
        "detect_source_cuts",
        lambda *args, **kwargs: (container_duration, detected_cuts),
    )
    monkeypatch.setattr(timeline_compile, "analyze_reference_video", analyze)
    monkeypatch.setattr(reference_analyzer, "analyze_reference_video", analyze)
    monkeypatch.setattr(timeline_compile, "extract_timeline_thumbnails", lambda *args: [])
    monkeypatch.setattr(timeline_compile, "initialize_timeline_project", initialize)
    monkeypatch.setattr(timeline_compile, "S3StorageAdapter", lambda _: object())

    return await timeline_compile.compile_timeline_request(
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


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("observed_end", "container_duration", "detected_cuts"),
    [
        (22.75, 22.777, [8, 16]),
        (22.777, 22.777, [8, 16]),
        (22.75, 30.0, [8, 16, 25]),
        (0.22, 22.777, [8, 16]),
        (0.22, 22.777, []),
    ],
)
async def test_full_source_auto_cuts_use_video_clock_through_semantic_resolution(
    monkeypatch, observed_end, container_duration, detected_cuts
):
    raw_analysis = source_analysis(observed_end)
    raw_analysis["sourceDurationSeconds"] = 22.75
    original = copy.deepcopy(raw_analysis)
    calls = []

    result = await compile_source_analysis(
        monkeypatch,
        raw_analysis,
        calls,
        container_duration=container_duration,
        detected_cuts=detected_cuts,
    )

    assert len(calls) == 2
    assert calls[0]["target_duration"] == 546 / 24
    expected_semantic_cuts = [0, 192, 273, 384, 546] if detected_cuts else [0, 273, 546]
    assert calls[1]["source_cut_frames"] == expected_semantic_cuts
    assert result["sourceSceneMap"]["scenes"][-1]["endFrame"] == 546
    expected_scene_starts = [0, 192, 384] if detected_cuts else [0]
    assert [
        scene["startFrame"] for scene in result["sourceSceneMap"]["scenes"]
    ] == expected_scene_starts
    assert raw_analysis == original


@pytest.mark.asyncio
async def test_subframe_initial_interval_requires_observed_semantic_reanalysis(monkeypatch):
    raw_analysis = source_analysis(22.75)
    first = {**raw_analysis["sourceShots"][0], "endSecond": 0.02, "durationSeconds": 0.02}
    second = {**raw_analysis["sourceShots"][0], "startSecond": 0.02}
    raw_analysis["sourceShots"] = [first, second]
    raw_analysis["motionBeats"] = copy.deepcopy(raw_analysis["sourceShots"])
    original = copy.deepcopy(raw_analysis)
    calls = []

    result = await compile_source_analysis(monkeypatch, raw_analysis, calls)

    assert len(calls) == 2
    assert calls[1]["source_cut_frames"] == [0, 273, 546]
    assert result["sourceSceneMap"]["scenes"][-1]["endFrame"] == 546
    assert raw_analysis == original


@pytest.mark.asyncio
async def test_incomplete_supplemental_analysis_stays_blocked_without_another_attempt(monkeypatch):
    raw_analysis = source_analysis(0.22)
    original = copy.deepcopy(raw_analysis)
    calls = []

    with pytest.raises(AppError) as failure:
        await compile_source_analysis(
            monkeypatch,
            raw_analysis,
            calls,
            incomplete_supplemental=True,
        )

    assert failure.value.code == "SMART_REMAKE_SOURCE_ANALYSIS_INCOMPLETE"
    assert len(calls) == 2
    assert calls[1]["source_cut_frames"] == [0, 273, 546]
    assert raw_analysis == original
