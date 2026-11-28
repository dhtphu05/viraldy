"""Provider prose excludes provenance while the canonical snapshot remains intact."""

from __future__ import annotations

import copy

import pytest

from viraldy.modules.smart_remake.engine import kie_adapter


def scene_direction():
    return {
        "renderUnitId": "11111111-1111-4111-8111-111111111111",
        "sourceSceneId": "22222222-2222-4222-8222-222222222222",
        "sourceRange": {"startFrame": 240, "endFrame": 432},
        "openingFrame": {
            "sourceMediaHash": "a" * 64,
            "layoutHash": "b" * 64,
            "frame": 240,
            "extractorVersion": "source-opening-frame-v1",
        },
        "prompt": "Show the pink cup on a red background and wood table.",
        "imagePrompt": "The hand holds the closed lid on a red background and wood table.",
        "videoPrompt": "Open the lid clockwise, then pour without reversing the action.",
        "shotPlan": {
            "timingMode": "fit_target",
            "rawDurationFrames": 192,
            "targetDurationFrames": 192,
            "shots": [{
                "action": "Open the lid clockwise, then pour",
                "stateBefore": "closed",
                "stateAfter": "open, pouring",
                "startSecond": 0,
                "endSecond": 8,
                "cameraMovement": "dolly_in",
                "transitionOut": "continuous",
                "physicalAction": {"contactPoint": "hand on cap", "movement": "clockwise"},
                "sourceTimeRange": {"startSecond": 10, "endSecond": 18},
                "sourceShotIndex": 42,
            }],
            "sourceSegment": {
                "sourceSceneId": "22222222-2222-4222-8222-222222222222",
                "sourceTimeRange": {"startSecond": 10, "endSecond": 18},
                "sourceSceneIndex": 42,
                "fragmentIndex": 1,
                "fragmentCount": 2,
                "boundary": {"kind": "continuous_handoff"},
                "continuity": {"previousState": "closed", "openingState": "closed"},
            },
        },
        "targetDurationFrames": 192,
        "rawDurationFrames": 192,
        "userEdits": "Keep the engraving ABC-123 visible.",
    }


@pytest.mark.parametrize("grouped", [False, True])
def test_video_prompt_excludes_provenance_but_retains_creative_and_timing_constraints(grouped):
    scene = scene_direction()
    scene["sourceSegment"] = copy.deepcopy(scene["shotPlan"]["sourceSegment"])
    before = copy.deepcopy(scene)
    values = {"product_lock": {"productName": "Pink cup", "mustPreserve": ["white handle"]}}
    if grouped:
        request = kie_adapter.build_kie_group_request(
            scenes=[scene], segments=[{"inFrame": 0, "outFrame": 192}],
            reference_image_urls=["https://8.8.8.8/first.png", "https://8.8.8.8/last.png"],
            **values,
        )
    else:
        request = kie_adapter.build_kie_video_request(
            scene=scene, product_image_url="https://8.8.8.8/first.png", **values,
        )
    prompt = request["input"]["prompt"]
    for value in (
        scene["renderUnitId"], scene["sourceSceneId"], "a" * 64, "b" * 64,
        "extractorVersion", "source-opening-frame-v1", "sourceTimeRange", "sourceShotIndex",
        "sourceSceneIndex", "sourceRange", "openingFrame", "fragmentIndex", "fragmentCount",
        "rawDurationFrames", "timingMode",
    ):
        assert value not in prompt
    for value in (
        "Pink cup", "white handle", "red background", "wood table", "closed", "open, pouring",
        "hand on cap", "clockwise", "dolly_in", "continuous", "continuous_handoff", "ABC-123",
        "0–8s:",
    ):
        assert value in prompt
    assert scene == before


def test_user_written_literal_identifier_is_not_stripped_as_machine_provenance():
    literal = "Engrave 33333333-3333-4333-8333-333333333333 exactly as supplied."
    scene = {**scene_direction(), "userEdits": literal}
    prompt = kie_adapter.build_kie_group_request(
        scenes=[scene], segments=[{"inFrame": 0, "outFrame": 192}],
        reference_image_urls=["https://8.8.8.8/first.png", "https://8.8.8.8/last.png"],
    )["input"]["prompt"]
    assert literal in prompt
