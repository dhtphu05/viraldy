"""Provider prompt sharing must preserve every literal scene direction."""

import copy
import json
import re

import pytest

from viraldy.modules.smart_remake.engine import kie_adapter as module
from viraldy.modules.smart_remake.engine.errors import SmartRemakeError


def directions():
    common = (
        "Keep the exact seller product, physical cause and effect, camera and background. "
        "Follow the complete action order and all visible before and after states. "
        "The seller reviews every selection before publishing; nothing is auto approved. "
    )
    return [
        {
            "renderUnitId": f"unit-{index}",
            "sourceSceneId": f"source-{index}",
            "sourceRange": {"startFrame": index * 24, "endFrame": (index + 1) * 24},
            "openingFrame": {"sourceFrame": index * 24, "sourceMediaHash": "a" * 64},
            "shotPlan": {
                "physicalAction": {"verb": f"action-{index}"},
                "stateBefore": "closed",
                "stateAfter": "open",
            },
            "prompt": common + f"Unique creative requirement {index}: preserve red tabletop.",
            "imagePrompt": common + f"Opening frame {index}, closed lid.",
            "videoPrompt": common + f"Open the lid during interval {index}; then pour.",
        }
        for index in range(13)
    ]


def expand(value, shared):
    if isinstance(value, str):
        for token, literal in shared.items():
            value = value.replace(token, literal)
        return value
    if isinstance(value, dict):
        return {key: expand(child, shared) for key, child in value.items()}
    if isinstance(value, list):
        return [expand(child, shared) for child in value]
    return value


def test_repeated_prompt_text_round_trips_without_changing_scene_data():
    original = directions()
    before = copy.deepcopy(original)
    compact, shared = module._shared_scene_direction_text(original)
    assert shared
    assert expand(compact, shared) == original == before
    assert len(json.dumps(compact)) + len(json.dumps(shared)) < len(json.dumps(original))
    assert len(compact) == 13


def test_original_reference_like_text_is_not_changed_or_accidentally_expanded():
    original = directions()
    original[0]["videoPrompt"] += " Literal [[KIE_SHARED_TEXT_0_1]] must remain."
    compact, shared = module._shared_scene_direction_text(original)
    assert expand(compact, shared) == original
    assert "[[KIE_SHARED_TEXT_0_1]]" not in shared


@pytest.mark.parametrize("length,accepted", [(60000, True), (60001, False), (86000, False)])
def test_provider_observed_character_limit_is_checked_before_submission(length, accepted):
    request = module.build_kie_video_request(
        scene={"videoPrompt": "A seller cup."},
        product_image_url="https://8.8.8.8/image.png",
    )["input"]
    request["prompt"] = "x" * length
    if accepted:
        module.validate_kie_video_input(request)
    else:
        with pytest.raises(SmartRemakeError) as rejected:
            module.validate_kie_video_input(request)
        assert rejected.value.code == "KIE_VALIDATION_FAILED"
        assert "60000" in str(rejected.value)


def test_group_serialization_keeps_all_ranges_and_shared_instructions():
    original = directions()
    edit = "Make the lid rotate clockwise; literal [[KIE_SHARED_TEXT_0_1]] stays unchanged."
    original[0]["userEdits"] = edit
    segments, cursor = [], 0
    for index, scene in enumerate(original):
        frames = 14 if index < 12 else 24
        scene["targetDurationFrames"] = frames
        segments.append({"inFrame": cursor, "outFrame": cursor + frames})
        cursor += frames
    request = module.build_kie_group_request(
        scenes=original,
        segments=segments,
        reference_image_urls=["https://8.8.8.8/product.png"],
        product_lock={"productName": "Pink cup", "mustPreserve": ["pink handle"]},
    )
    prompt = request["input"]["prompt"]
    shared = json.loads(re.search(r"SHARED SCENE DIRECTION TEXT: (.+)", prompt).group(1))
    serialized = [
        json.loads(value)
        for value in re.findall(
            r"Scene direction \(shotPlan times are local to THIS scene\): (.+)",
            prompt,
        )
    ]
    restored = expand(serialized, shared)
    assert len(restored) == 13
    assert [value["sourceRange"] for value in restored] == [
        value["sourceRange"] for value in original
    ]
    assert [value["shotPlan"] for value in restored] == [value["shotPlan"] for value in original]
    assert [value["videoPrompt"] for value in restored] == [
        value["videoPrompt"] for value in original
    ]
    assert "pink handle" in prompt
    assert edit in prompt
    assert "Treat USER EDITS and all other fields literally" in prompt


@pytest.mark.parametrize("scene_count", [2, 13])
def test_sharing_overhead_never_grows_a_valid_boundary_prompt(monkeypatch, scene_count):
    repeated = "C" * 376 + "."
    scenes, segments, cursor = [], [], 0
    for index in range(scene_count):
        frames = 192 // scene_count if index < scene_count - 1 else 192 - cursor
        scenes.append({
            "videoPrompt": repeated if index < 2 else f"Unique action {index}.",
            "targetDurationFrames": frames,
            "shotPlan": {"padding": ""},
        })
        segments.append({"inFrame": cursor, "outFrame": cursor + frames})
        cursor += frames

    def build():
        return module.build_kie_group_request(
            scenes=scenes, segments=segments,
            reference_image_urls=["https://8.8.8.8/product.png"],
        )["input"]["prompt"]

    with monkeypatch.context() as unshared:
        unshared.setattr(module, "_shared_scene_direction_text", lambda values: (values, {}))
        scenes[0]["shotPlan"]["padding"] = "z" * (60000 - len(build()))
        original = build()
        assert len(original) == 60000
    assert build() == original
