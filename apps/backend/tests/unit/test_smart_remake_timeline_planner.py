from __future__ import annotations

from uuid import UUID

import pytest

from viraldy.modules.smart_remake.timeline_planner import build_timeline_plan, source_boundaries
from viraldy.shared.errors.base import AppError


@pytest.mark.parametrize("duration,cuts", [(8, [0, 48, 192]), (16, [0, 72, 192, 288, 384])])
def test_source_scenes_and_render_units_preserve_exact_variable_lengths(duration, cuts):
    result = build_timeline_plan(
        target_duration=duration,
        source_frame_count=720,
        reference_start_frame=120,
        cut_frames=cuts,
    )
    source = result["sourceSceneMap"]
    units = result["renderPlan"]["units"]
    items = result["draftTimeline"]["items"]
    assert [s["startFrame"] for s in source["scenes"]] == [120 + x for x in cuts[:-1]]
    assert [u["targetDurationFrames"] for u in units] == [
        b - a for a, b in zip(cuts, cuts[1:], strict=False)
    ]
    assert all(u["rawDurationFrames"] == 192 for u in units)
    assert [i["targetStartFrame"] for i in items] == cuts[:-1]
    assert all(i["reviewed"] is False and i["versionId"] is None for i in items)
    assert all(UUID(u["id"]) for u in units)
    assert all(
        u["id"] != s["id"] and i["id"] != u["id"]
        for s, u, i in zip(source["scenes"], units, items, strict=False)
    )


@pytest.mark.parametrize(
    "cuts",
    [
        [],
        [0, 384],
        [0, 192, 191, 384],
        [1, 192, 384],
        [0, 192, 383],
        [0, 192.5, 384],
        [0, True, 384],
    ],
)
def test_invalid_boundaries_never_silently_merge_or_stretch(cuts):
    with pytest.raises(AppError):
        build_timeline_plan(
            target_duration=16, source_frame_count=720, reference_start_frame=0, cut_frames=cuts
        )


@pytest.mark.parametrize("start,count", [(-1, 720), (1, 384), (0, 383)])
def test_excerpt_must_fit_measured_media(start, count):
    with pytest.raises(AppError, match="source"):
        build_timeline_plan(
            target_duration=16,
            source_frame_count=count,
            reference_start_frame=start,
            cut_frames=[0, 192, 384],
        )


def test_detected_source_boundaries_keep_all_cuts_and_frame_quantization():
    analysis = {
        "sourceShots": [
            {"startSecond": 0, "endSecond": 3},
            {"startSecond": 3, "endSecond": 8},
            {"startSecond": 8, "endSecond": 12},
            {"startSecond": 12, "endSecond": 16},
        ]
    }
    assert source_boundaries(analysis, total_frames=384) == [0, 72, 192, 288, 384]


def test_continuous_long_scene_requires_explicit_cut():
    cuts = source_boundaries(
        {"sourceShots": [{"startSecond": 0, "endSecond": 16}]}, total_frames=384
    )
    with pytest.raises(AppError) as error:
        build_timeline_plan(
            target_duration=16, source_frame_count=384, reference_start_frame=0, cut_frames=cuts
        )
    assert error.value.code == "SMART_REMAKE_TIMELINE_SCENE_TOO_LONG"


def test_explicit_v2_scene_map_keeps_variable_frame_lengths_and_v1_rules():
    from pydantic import ValidationError

    from viraldy.modules.smart_remake.engine.schemas import SceneMap

    scene = {
        "displayOrder": 0,
        "prompt": "prompt",
        "imagePrompt": "image",
        "videoPrompt": "video",
        "characterNames": ["Target"],
        "targetDurationFrames": 48,
        "rawDurationFrames": 192,
    }
    payload = {
        "schemaVersion": 2,
        "targetDuration": 8,
        "aspectRatio": "9:16",
        "sceneCount": 2,
        "scenes": [scene, {**scene, "displayOrder": 1, "targetDurationFrames": 144}],
    }
    assert SceneMap.model_validate(payload).scenes[1].targetDurationFrames == 144
    with pytest.raises(ValidationError):
        SceneMap.model_validate({**payload, "schemaVersion": 1})
    with pytest.raises(ValidationError):
        SceneMap.model_validate({**payload, "scenes": [scene, scene]})


def test_fitting_full_source_keeps_all_logical_scenes_and_packs_provider_calls():
    result = build_timeline_plan(
        target_duration=16,
        source_frame_count=720,
        reference_start_frame=0,
        cut_frames=list(range(0, 721, 120)),
        timing_mode="fit_target",
    )
    sources = result["sourceSceneMap"]["scenes"]
    units = result["renderPlan"]["units"]
    assert result["sourceSceneMap"]["timingMode"] == "fit_target"
    assert len(sources) == len(units) == 6
    assert [(scene["startFrame"], scene["endFrame"]) for scene in sources] == [
        (start, start + 120) for start in range(0, 720, 120)
    ]
    assert [scene["targetDurationFrames"] for scene in sources] == [64] * 6
    assert [unit["sourceSceneIndex"] for unit in units] == list(range(6))
    assert [group["targetDurationFrames"] for group in result["renderPlan"]["groups"]] == [192, 192]
    assert len(result["draftTimeline"]["items"]) == 6


def test_fitting_one_continuous_scene_splits_provider_fragments_not_source_scenes():
    result = build_timeline_plan(
        target_duration=16,
        source_frame_count=720,
        reference_start_frame=0,
        cut_frames=[0, 720],
        timing_mode="fit_target",
    )
    source = result["sourceSceneMap"]["scenes"][0]
    units = result["renderPlan"]["units"]
    assert len(result["sourceSceneMap"]["scenes"]) == 1
    assert source["targetDurationFrames"] == 384
    assert [unit["sourceSceneId"] for unit in units] == [source["id"], source["id"]]
    assert [(unit["sourceStartFrame"], unit["sourceEndFrame"]) for unit in units] == [
        (0, 360),
        (360, 720),
    ]
    assert [unit["fragmentIndex"] for unit in units] == [0, 1]
    assert [unit["fragmentCount"] for unit in units] == [2, 2]
    assert [item["targetStartFrame"] for item in result["draftTimeline"]["items"]] == [0, 192]
    assert [unit["targetDurationFrames"] for unit in units] == [192, 192]


def test_provider_windows_split_a_short_logical_scene_at_the_global_eight_second_boundary():
    result = build_timeline_plan(
        target_duration=16,
        source_frame_count=384,
        reference_start_frame=0,
        cut_frames=[0, 120, 240, 384],
        timing_mode="fit_target",
    )
    sources = result["sourceSceneMap"]["scenes"]
    units = result["renderPlan"]["units"]
    groups = result["renderPlan"]["groups"]
    assert len(sources) == 3
    assert [scene["targetDurationFrames"] for scene in sources] == [120, 120, 144]
    assert [unit["targetDurationFrames"] for unit in units] == [120, 72, 48, 144]
    assert [unit["sourceSceneId"] for unit in units] == [
        sources[0]["id"],
        sources[1]["id"],
        sources[1]["id"],
        sources[2]["id"],
    ]
    assert [(unit["sourceStartFrame"], unit["sourceEndFrame"]) for unit in units] == [
        (0, 120),
        (120, 192),
        (192, 240),
        (240, 384),
    ]
    assert [unit["fragmentIndex"] for unit in units] == [0, 0, 1, 0]
    assert [unit["fragmentCount"] for unit in units] == [1, 2, 2, 1]
    assert [group["targetDurationFrames"] for group in groups] == [192, 192]
    assert result["renderPlan"]["groupingPolicy"] == "fixed_provider_windows"
    assert [[segment["inFrame"], segment["outFrame"]] for segment in groups[1]["segments"]] == [
        [0, 48],
        [48, 192],
    ]


@pytest.mark.parametrize("duration", [8, 16])
@pytest.mark.parametrize(
    "cuts",
    [
        [0, 120, 240, 384],
        [0, 29, 131, 170, 301, 384],
        list(range(0, 385, 16)),
        [0, 384],
    ],
)
def test_fit_target_always_has_exactly_one_kie_window_per_eight_seconds(duration, cuts):
    result = build_timeline_plan(
        target_duration=duration,
        source_frame_count=384,
        reference_start_frame=0,
        cut_frames=cuts,
        timing_mode="fit_target",
        render_group_breaks=[1, 2, 3],
    )
    groups = result["renderPlan"]["groups"]
    assert len(groups) == duration // 8
    assert [group["targetDurationFrames"] for group in groups] == [192] * (duration // 8)
    assert result["renderPlan"]["renderGroupBreaks"] == []
    assert len(result["sourceSceneMap"]["scenes"]) == len(cuts) - 1
    cursor = 0
    for item in result["draftTimeline"]["items"]:
        assert item["targetStartFrame"] == cursor
        assert item["targetDurationFrames"] > 0
        cursor += item["targetDurationFrames"]
    assert cursor == duration * 24
    assert all(
        segment["outFrame"] > segment["inFrame"]
        for group in groups
        for segment in group["segments"]
    )


def test_global_window_split_preserves_nonempty_source_ranges_when_expanding_short_media():
    result = build_timeline_plan(
        target_duration=16,
        source_frame_count=47,
        reference_start_frame=0,
        cut_frames=[0, 23, 25, 47],
        timing_mode="fit_target",
    )
    sources = result["sourceSceneMap"]["scenes"]
    assert [scene["targetDurationFrames"] for scene in sources] == [188, 16, 180]
    middle_fragments = [
        unit for unit in result["renderPlan"]["units"] if unit["sourceSceneId"] == sources[1]["id"]
    ]
    assert [unit["targetDurationFrames"] for unit in middle_fragments] == [4, 12]
    assert [(unit["sourceStartFrame"], unit["sourceEndFrame"]) for unit in middle_fragments] == [
        (23, 24),
        (24, 25),
    ]
    assert [group["targetDurationFrames"] for group in result["renderPlan"]["groups"]] == [192, 192]


def test_target_frame_allocation_is_exact_proportional_and_deterministic():
    kwargs = {
        "target_duration": 16,
        "source_frame_count": 720,
        "reference_start_frame": 0,
        "cut_frames": [0, 144, 288, 432, 576, 720],
        "timing_mode": "fit_target",
    }
    first = build_timeline_plan(**kwargs)
    second = build_timeline_plan(**kwargs)
    durations = [scene["targetDurationFrames"] for scene in first["sourceSceneMap"]["scenes"]]
    assert durations == [77, 77, 77, 77, 76]
    assert durations == [
        scene["targetDurationFrames"] for scene in second["sourceSceneMap"]["scenes"]
    ]
    assert sum(durations) == first["draftTimeline"]["totalFrames"] == 384


def test_tiny_source_scenes_are_not_dropped_when_fitting():
    result = build_timeline_plan(
        target_duration=8,
        source_frame_count=720,
        reference_start_frame=0,
        cut_frames=[0, 718, 719, 720],
        timing_mode="fit_target",
    )
    assert [scene["targetDurationFrames"] for scene in result["sourceSceneMap"]["scenes"]] == [
        190,
        1,
        1,
    ]


def test_physical_frame_density_is_reported_without_dropping_analyzed_scenes():
    with pytest.raises(AppError) as error:
        build_timeline_plan(
            target_duration=8,
            source_frame_count=193,
            reference_start_frame=0,
            cut_frames=list(range(194)),
            timing_mode="fit_target",
        )
    assert error.value.code == "SMART_REMAKE_TIMELINE_DENSITY_UNSUPPORTED"
    assert error.value.details["sourceSceneCount"] == 193
    assert error.value.details["availableFrames"] == 192


def test_short_source_can_expand_to_output_duration_with_source_ranges_preserved():
    result = build_timeline_plan(
        target_duration=8,
        source_frame_count=48,
        reference_start_frame=0,
        cut_frames=[0, 24, 48],
        timing_mode="fit_target",
    )
    assert [scene["targetDurationFrames"] for scene in result["sourceSceneMap"]["scenes"]] == [
        96,
        96,
    ]
    assert [unit["sourceEndFrame"] for unit in result["renderPlan"]["units"]] == [24, 48]


def test_exact_timing_mode_has_no_arbitrary_scene_limit():
    result = build_timeline_plan(
        target_duration=8,
        source_frame_count=192,
        reference_start_frame=0,
        cut_frames=[0, 24, 48, 72, 96, 120, 144, 168, 192],
    )
    assert len(result["sourceSceneMap"]["scenes"]) == 8
    assert len(result["renderPlan"]["groups"]) == 1
    assert len(result["renderPlan"]["groups"][0]["segments"]) == 8


def test_scene_map_accepts_many_timeline_scenes_without_changing_legacy_count_rules():
    from pydantic import ValidationError

    from viraldy.modules.smart_remake.engine.schemas import SceneMap

    scene = {
        "displayOrder": 0,
        "prompt": "prompt",
        "imagePrompt": "image",
        "videoPrompt": "video",
        "characterNames": ["Target"],
        "targetDurationFrames": 24,
        "rawDurationFrames": 192,
    }
    payload = {
        "schemaVersion": 2,
        "targetDuration": 8,
        "aspectRatio": "9:16",
        "sceneCount": 8,
        "scenes": [{**scene, "displayOrder": index} for index in range(8)],
    }
    assert SceneMap.model_validate(payload).sceneCount == 8
    with pytest.raises(ValidationError):
        SceneMap.model_validate({**payload, "schemaVersion": 1})


@pytest.mark.parametrize("cuts", [[1, 720], [0, 719], [0, 480, 479, 720], [0, False, 720]])
def test_full_source_boundaries_must_cover_the_actual_media_in_order(cuts):
    with pytest.raises(AppError) as error:
        build_timeline_plan(
            target_duration=8,
            source_frame_count=720,
            reference_start_frame=0,
            cut_frames=cuts,
            timing_mode="fit_target",
        )
    assert error.value.code == "SMART_REMAKE_TIMELINE_CUTS_INVALID"


@pytest.mark.parametrize(
    "changes,code",
    [
        ({"target_duration": 12}, "INVALID_SMART_REMAKE_DURATION"),
        ({"target_duration": True}, "INVALID_SMART_REMAKE_DURATION"),
        ({"reference_start_frame": 1}, "SMART_REMAKE_SOURCE_RANGE_INVALID"),
        ({"source_frame_count": False}, "SMART_REMAKE_SOURCE_RANGE_INVALID"),
        ({"source_frame_count": 0}, "SMART_REMAKE_SOURCE_RANGE_INVALID"),
        ({"timing_mode": "unknown"}, "SMART_REMAKE_TIMELINE_INVALID"),
    ],
)
def test_full_source_timing_inputs_are_explicit_and_valid(changes, code):
    values = {
        "target_duration": 8,
        "source_frame_count": 720,
        "reference_start_frame": 0,
        "cut_frames": [0, 720],
        "timing_mode": "fit_target",
    }
    with pytest.raises(AppError) as error:
        build_timeline_plan(**{**values, **changes})
    assert error.value.code == code


def test_fragment_source_ranges_still_require_observed_source_frames():
    with pytest.raises(AppError) as error:
        build_timeline_plan(
            target_duration=16,
            source_frame_count=1,
            reference_start_frame=0,
            cut_frames=[0, 1],
            timing_mode="fit_target",
        )
    assert error.value.code == "SMART_REMAKE_SOURCE_RANGE_INVALID"


@pytest.mark.parametrize(
    "changes",
    [
        {"sourceStartFrame": 2},
        {"sourceStartFrame": 2, "sourceEndFrame": 2},
        {"fragmentIndex": 1},
    ],
)
def test_render_unit_fragment_metadata_cannot_be_partial_or_out_of_range(changes):
    from pydantic import ValidationError

    from viraldy.modules.smart_remake.timeline_schemas import RenderUnit

    with pytest.raises(ValidationError):
        RenderUnit.model_validate(
            {
                "id": "unit",
                "sourceSceneId": "source",
                "sceneIndex": 0,
                "targetDurationFrames": 192,
                **changes,
            }
        )
