"""Compact video briefs preserve timed actions, product facts and unique seller prose."""

import copy
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
            "targetDurationFrames": 14 if index < 12 else 24,
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


def render(scenes, **changes):
    segments, cursor = [], 0
    for index, scene in enumerate(scenes):
        frames = scene.get("targetDurationFrames") or (
            192 // len(scenes) if index < len(scenes) - 1 else 192 - cursor
        )
        segments.append({"inFrame": cursor, "outFrame": cursor + frames})
        cursor += frames
    return module.build_kie_group_request(
        scenes=scenes,
        segments=segments,
        reference_image_urls=["https://8.8.8.8/opening.png", "https://8.8.8.8/final.png"],
        **changes,
    )["input"]["prompt"]


def scene_blocks(prompt):
    return re.findall(
        r"(\[00:\d+\.\d{3}–00:\d+\.\d{3}\] SCENE \d+\n.*?)(?=\n\n\[00:|\Z)",
        prompt,
        re.DOTALL,
    )


def test_repeated_prose_is_deduplicated_without_losing_unique_scene_requirements():
    original = directions()
    before = copy.deepcopy(original)
    prompt = render(original)
    blocks = scene_blocks(prompt)
    assert len(blocks) == len(original) == 13
    for index, block in enumerate(blocks):
        for requirement in (
            f"action-{index}", "closed", "open", f"Unique creative requirement {index}:",
            f"Opening frame {index}, closed lid.",
            f"Open the lid during interval {index}; then pour.",
        ):
            assert requirement in block
        assert block.count("Keep the exact seller product, physical cause and effect") == 1
    assert "SHARED SCENE DIRECTION TEXT" not in prompt
    assert "[[KIE_SHARED_TEXT_" not in prompt
    assert len(prompt) < sum(len(scene[key]) for scene in original
                             for key in ("prompt", "imagePrompt", "videoPrompt"))
    assert original == before


def test_seller_reference_like_literal_is_preserved_without_token_expansion():
    original = directions()
    literal = "Literal [[KIE_SHARED_TEXT_0_1]] must remain."
    original[0]["videoPrompt"] += " " + literal
    before = copy.deepcopy(original)
    prompt = render(original)
    assert prompt.count(literal) == 1
    assert "SHARED SCENE DIRECTION TEXT" not in prompt
    assert original == before


def test_distinct_lettercase_in_product_engraving_directions_is_not_deduplicated():
    scene = {"prompt": "Show engraving ABC.", "videoPrompt": "Show engraving abc."}
    prompt = render([scene])
    assert "Show engraving ABC." in prompt
    assert "Show engraving abc." in prompt


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


def test_group_keeps_all_timed_scenes_product_constraints_and_literal_seller_edits():
    original = directions()
    edit = "Make the lid rotate clockwise; literal [[KIE_SHARED_TEXT_0_1]] stays unchanged."
    original[0]["userEdits"] = edit
    before = copy.deepcopy(original)
    prompt = render(
        original,
        product_lock={"productName": "Pink cup", "mustPreserve": ["pink handle"]},
    )
    blocks = scene_blocks(prompt)
    assert len(blocks) == 13
    cursor = 0
    for index, (scene, block) in enumerate(zip(original, blocks, strict=True)):
        end = cursor + scene["targetDurationFrames"]
        assert block.startswith(f"[00:{cursor / 24:06.3f}–00:{end / 24:06.3f}] SCENE {index + 1}\n")
        assert all(text in block for text in (f"action-{index}", "closed", "open"))
        cursor = end
    assert cursor == 192
    assert all(f"unit-{index}" not in prompt and f"source-{index}" not in prompt
               for index in range(13))
    assert "sourceRange" not in prompt and "openingFrame" not in prompt
    assert "Pink cup" in prompt and "pink handle" in prompt
    assert edit in blocks[0] and all(edit not in block for block in blocks[1:])
    assert "USER EDITS" in prompt
    assert original == before


@pytest.mark.parametrize("scene_count", [2, 13])
def test_unique_prose_at_provider_boundary_is_preserved_and_never_truncated(scene_count):
    scenes = [{"videoPrompt": f"Unique action {index}."} for index in range(scene_count)]
    before_length = len(scenes[0]["videoPrompt"])
    literal = "z" * (60000 - len(render(scenes)) + before_length)
    scenes[0]["videoPrompt"] = literal
    prompt = render(scenes)
    assert len(prompt) == 60000 and literal in prompt
    assert len(scene_blocks(prompt)) == scene_count
    scenes[0]["videoPrompt"] += "z"
    with pytest.raises(SmartRemakeError, match="60000"):
        render(scenes)
