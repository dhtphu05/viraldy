"""Provider-local windows form one ordered film without replaying a whole audio script."""
from __future__ import annotations

import copy

import pytest
from test_smart_remake_wan_duration import six_second_args
from test_smart_remake_wan_video import MODEL, group_args

from viraldy.modules.smart_remake.engine.errors import SmartRemakeError
from viraldy.modules.smart_remake.engine.video_requests import build_group_request


def frozen_story():
    states = ["closed on table", "closed in hand", "lid open", "filled on table", "closed filled"]
    units = [{"id": f"private-unit-{index}", "targetDurationFrames": 72} for index in range(4)]
    groups = [{
        "id": f"private-group-{index}", "rawDurationFrames": 144,
        "targetDurationFrames": 144,
        "renderUnitIds": [unit["id"] for unit in units[index * 2:index * 2 + 2]],
    } for index in range(2)]
    plan = {"videoModel": MODEL, "units": units, "groups": groups}
    snapshot = {"scenes": [{
        "renderUnitId": unit["id"], "sourceSceneId": f"private-source-{index}",
        "sourceRange": {"startFrame": index * 72, "endFrame": (index + 1) * 72},
        "openingFrame": {"layoutHash": "private-layout-hash"},
        "sourceSegment": {"boundary": {"kind": "source_start" if index == 0 else "source_cut"}},
        "shotPlan": {"shots": [{
            "action": ("Lift product", "Remove lid", "Pour water", "Close lid")[index],
            "stateBefore": states[index], "stateAfter": states[index + 1],
        }]},
    } for index, unit in enumerate(units)]}
    return plan, snapshot


def test_frozen_window_context_has_global_order_and_state_without_private_identifiers():
    from viraldy.modules.smart_remake.engine.window_continuity import build_window_context

    plan, snapshot = frozen_story()
    before = copy.deepcopy((plan, snapshot))
    first = build_window_context(plan, plan["groups"][0], snapshot)
    second = build_window_context(plan, plan["groups"][1], snapshot)
    assert first == {
        "partIndex": 1, "partCount": 2, "globalStart": 0, "globalEnd": 6,
        "totalDuration": 12, "previousAction": None, "openingState": "closed on table",
        "finalState": "lid open", "nextOpeningState": "lid open", "boundaryKind": "source_start",
    }
    assert second == {
        "partIndex": 2, "partCount": 2, "globalStart": 6, "globalEnd": 12,
        "totalDuration": 12, "previousAction": "Remove lid", "openingState": "lid open",
        "finalState": "closed filled", "nextOpeningState": None, "boundaryKind": "source_cut",
    }
    assert "private-" not in repr((first, second))
    assert (plan, snapshot) == before


@pytest.mark.parametrize("raw_frames,count", [(192, 1), (192, 2)])
def test_historical_eight_and_sixteen_second_plans_do_not_get_new_context(raw_frames, count):
    from viraldy.modules.smart_remake.engine.window_continuity import build_window_context

    plan, snapshot = frozen_story()
    plan["groups"] = [{
        **group, "rawDurationFrames": raw_frames, "targetDurationFrames": raw_frames,
    } for group in plan["groups"][:count]]
    assert build_window_context(plan, plan["groups"][0], snapshot) is None


def test_context_cannot_bind_another_group_or_missing_scene():
    from viraldy.modules.smart_remake.engine.window_continuity import build_window_context

    plan, snapshot = frozen_story()
    with pytest.raises(SmartRemakeError):
        build_window_context(plan, {**plan["groups"][0], "id": "other"}, snapshot)
    with pytest.raises(SmartRemakeError):
        build_window_context(plan, plan["groups"][0], {"scenes": []})


def test_second_window_continues_film_and_omits_global_untimed_dialogue():
    from viraldy.modules.smart_remake.engine.window_continuity import build_window_context

    plan, snapshot = frozen_story()
    context = build_window_context(plan, plan["groups"][1], snapshot)
    args = six_second_args()
    args["reference_analysis"]["audioPlan"] = {
        "mode": "native", "dialogue": "Entire video summary must not be repeated",
        "music": "light guitar pulse", "language": "Vietnamese", "ambience": "quiet room",
    }
    before = copy.deepcopy(args)
    request = build_group_request(
        model=MODEL, duration_seconds=6, audio=True, window_context=context, **args,
    )
    prompt = request["input"]["prompt"]
    assert "PART 2 OF 2" in prompt and "6–12 seconds of one 12-second film" in prompt
    assert "not a new introduction" in prompt
    assert "Previously shown (context only, do not replay): Remove lid" in prompt
    assert (
        "Opening-state analysis summary (context only, not a verified instant): lid open" in prompt
    )
    assert "Entire video summary" not in prompt
    assert '"dialogue"' not in prompt
    assert "light guitar pulse" in prompt and "Vietnamese" in prompt and "quiet room" in prompt
    assert "do not restart" in prompt
    assert "[00:00.000–00:03.000] SCENE 1" in prompt
    assert "private-" not in prompt
    assert args == before


def test_first_window_hands_off_without_forcing_an_outro():
    from viraldy.modules.smart_remake.engine.window_continuity import build_window_context

    plan, snapshot = frozen_story()
    context = build_window_context(plan, plan["groups"][0], snapshot)
    prompt = build_group_request(
        model=MODEL, duration_seconds=6, window_context=context, **six_second_args(),
    )["input"]["prompt"]
    assert "PART 1 OF 2" in prompt and "0–6 seconds of one 12-second film" in prompt
    assert "handoff" in prompt and "not a complete ending" in prompt
    assert (
        "Next opening-state analysis summary (context only, not a verified instant): "
        "lid open" in prompt
    )
    assert "unless the analyzed scene explicitly requires it" in prompt


def test_conditioned_boundary_frames_override_conflicting_unverified_state_summaries():
    from viraldy.modules.smart_remake.engine.window_continuity import build_window_context

    plan, snapshot = frozen_story()
    context = build_window_context(plan, plan["groups"][0], snapshot)
    context["finalState"] = "Top-down open cup filled with ice resting on a coaster"
    context["nextOpeningState"] = "Closed cup held by the presenter"
    prompt = build_group_request(
        model=MODEL, duration_seconds=6, window_context=context, **six_second_args(),
    )["input"]["prompt"]
    assert "FIRST and LAST conditioning images are authoritative" in prompt
    assert "physical state, pose and layout" in prompt
    assert "cannot override the conditioning images when they conflict" in prompt
    assert "Final-state analysis summary (context only, not a verified instant): Top-down" in prompt
    assert "Final state:" not in prompt and "Next part opening state:" not in prompt
    assert "Preserve every interior timed action and its order" in prompt


def test_only_dialogue_bound_to_current_scenes_is_included_without_invented_times():
    from viraldy.modules.smart_remake.engine.window_continuity import build_window_context

    plan, snapshot = frozen_story()
    snapshot["scenes"][0]["shotPlan"]["audioPlan"] = {"dialogue": "Earlier spoken line"}
    snapshot["scenes"][2]["shotPlan"]["shots"][0].update(
        dialogue="Observed current line", sourceTimeRange={"startSecond": 6, "endSecond": 9},
    )
    # Unbound free text is not observed speech evidence.
    snapshot["scenes"][3]["shotPlan"]["shots"][0]["dialogue"] = "Unbound invented line"
    context = build_window_context(plan, plan["groups"][1], snapshot)
    assert context["windowDialogue"] == ["Observed current line"]
    prompt = build_group_request(
        model=MODEL, duration_seconds=6, audio=True, window_context=context,
        **six_second_args(),
    )["input"]["prompt"]
    assert "Observed current line" in prompt
    assert "Earlier spoken line" not in prompt and "Unbound invented line" not in prompt
    assert "6–9" not in prompt and "00:09" not in prompt


@pytest.mark.parametrize("time_range", [{}, {"startSecond": 3, "endSecond": 4},
                                       {"startSecond": 9, "endSecond": 6}])
def test_missing_or_outside_dialogue_source_timing_does_not_become_window_evidence(time_range):
    from viraldy.modules.smart_remake.engine.window_continuity import build_window_context

    plan, snapshot = frozen_story()
    snapshot["scenes"][2]["shotPlan"]["shots"][0].update(
        dialogue="Unsupported spoken line", sourceTimeRange=time_range,
    )
    context = build_window_context(plan, plan["groups"][1], snapshot)
    assert "windowDialogue" not in context


def test_optional_none_preserves_old_wan_and_veo_requests_exactly():
    for model in (MODEL, "veo3_lite"):
        assert build_group_request(model=model, window_context=None, **group_args()) == (
            build_group_request(model=model, **group_args())
        )


def test_window_context_cannot_be_forwarded_to_a_historical_duration_or_veo():
    from viraldy.modules.smart_remake.engine.window_continuity import build_window_context

    plan, snapshot = frozen_story()
    context = build_window_context(plan, plan["groups"][0], snapshot)
    for model in (MODEL, "veo3_lite"):
        with pytest.raises(SmartRemakeError):
            build_group_request(model=model, window_context=context, **group_args())
