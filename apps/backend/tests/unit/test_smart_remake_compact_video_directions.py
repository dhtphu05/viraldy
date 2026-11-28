"""Compact provider briefs keep scene coverage, product identity and creative edits."""

from __future__ import annotations

import copy
import json
import re

import pytest

from viraldy.modules.smart_remake.engine.kie_adapter import build_kie_group_request
from viraldy.modules.smart_remake.engine.video_directions import video_requirements
from viraldy.modules.smart_remake.fixture import FixtureGeminiClient
from viraldy.modules.smart_remake.timeline_compile import build_timeline_compile
from viraldy.modules.smart_remake.timeline_planner import build_timeline_plan


def group(scenes, **kwargs):
    cursor, segments = 0, []
    for scene in scenes:
        end = cursor + scene.get("targetDurationFrames", 192 // len(scenes))
        segments.append({"inFrame": cursor, "outFrame": end})
        cursor = end
    return build_kie_group_request(
        scenes=scenes, segments=segments,
        reference_image_urls=["https://8.8.8.8/first.png", "https://8.8.8.8/last.png"],
        **kwargs,
    )["input"]["prompt"]


@pytest.mark.asyncio
async def test_compiled_many_scene_brief_is_short_without_losing_any_actions():
    lock = await FixtureGeminiClient().generate_json(system_instruction="", prompt="product lock")
    analysis = {
        "subjectPresence": "hands_only",
        "cameraStyle": {"angle": "eye_level", "movement": "static"},
        "setting": {"locationType": "studio", "backgroundElements": ["red wall", "wood table"]},
        "sourceShots": [{
            "shotIndex": index, "startSecond": index, "endSecond": index + 1,
            "durationSeconds": 1,
            "action": f"Perform observed action {index + 1} on the product",
            "physicalAction": {"contactPoint": f"contact point {index + 1}"},
            "stateBefore": f"before {index + 1}", "stateAfter": f"after {index + 1}",
            "transitionOut": "hard_cut",
        } for index in range(13)],
    }
    plan = build_timeline_plan(
        target_duration=8, source_frame_count=13 * 24, reference_start_frame=0,
        cut_frames=list(range(0, 13 * 24 + 1, 24)), timing_mode="fit_target",
    )
    compiled = build_timeline_compile(
        analysis=analysis, product_lock=lock, plan=plan, language="Tiếng Việt", mode="smart_remake",
    )
    scenes = compiled["sceneMap"]["scenes"]
    original = copy.deepcopy(scenes)
    prompt = group(scenes, product_lock=lock, reference_analysis=analysis)
    assert len(prompt) < 10000
    assert len(re.findall(r"^\[.*\] SCENE \d+", prompt, re.M)) == 13
    assert "SHARED SCENE DIRECTION TEXT" not in prompt
    assert "SOURCE ACTION TIMELINE" not in prompt
    assert "imagePrompt" not in prompt and "videoPrompt" not in prompt
    assert prompt.count("Tiếng Việt") == 1
    for index in range(13):
        assert prompt.count(f"Perform observed action {index + 1} on the product") == 1
        assert f"contact point {index + 1}" in prompt
        assert f"before {index + 1}" in prompt and f"after {index + 1}" in prompt
    assert "red wall" in prompt and "wood table" in prompt
    assert lock["productName"] in prompt
    assert scenes == original


def test_unrecognized_and_previously_edited_prompts_keep_unique_creative_directions():
    scene = {
        "targetDurationFrames": 192, "prompt": "Warm rim lighting. Warm rim lighting.",
        "imagePrompt": "Warm rim lighting. Keep a red background and wood table.",
        "videoPrompt": "Pour slowly. Keep the subject's blue sleeve visible.",
        "userEdits": "Use a low camera angle.",
        "shotPlan": {"shots": [{"action": "Pour slowly", "stateBefore": "full",
            "stateAfter": "half full", "startSecond": 0, "endSecond": 8}]},
    }
    prompt = group([scene])
    for text in ("Warm rim lighting", "red background", "wood table", "blue sleeve",
                 "Use a low camera angle"):
        assert text in prompt
    assert prompt.count("Warm rim lighting") == 1
    assert prompt.count("Pour slowly") == 1


def test_repeated_actions_at_different_times_and_distinct_beats_are_retained():
    scene = {"targetDurationFrames": 192, "shotPlan": {
        "shots": [{"action": "Raise the cup", "startSecond": start, "endSecond": start + 4}
                  for start in (0, 4)],
        "motionBeats": [{"action": "Twist clockwise before lifting",
                         "startSecond": 2, "endSecond": 3}],
        "cutTimes": [2, 4], "visualStructure": "sequential_shots",
    }}
    prompt = group([scene])
    assert prompt.count("Raise the cup") == 2
    assert "Twist clockwise before lifting" in prompt
    assert '"cutTimes":[2,4]' in prompt


def test_product_brief_keeps_identity_and_constraints_while_omitting_usage_examples():
    lock = {"productName": "Seller Cup", "visualIdentity": {"colors": ["pink"], "shape": None},
            "mustPreserve": ["white handle"], "forbiddenErrors": ["invented logos"],
            "productUsage": {"usageConstraints": ["keep upright"],
                             "realisticUseCases": ["Unneeded lifestyle example"],
                             "handlingInstructions": ["Unlock safety ring before pressing"],
                             "contactPoints": ["press silver top switch"],
                             "suitableSurfaces": ["flat wood table"]}}
    prompt = group([{"targetDurationFrames": 192, "videoPrompt": "Rotate the cup."}],
                   product_lock=lock)
    for text in (
        "Seller Cup", "pink", "white handle", "invented logos", "keep upright",
        "Unlock safety ring before pressing", "press silver top switch", "flat wood table",
    ):
        assert prompt.count(text) == 1
    assert "Unneeded lifestyle example" not in prompt
    assert '"shape":null' not in prompt


def test_long_legacy_instruction_is_preserved_without_truncation_or_shared_token_indirection():
    text = "Unique seller detail " + "x" * 16000
    prompt = group([{"targetDurationFrames": 192, "videoPrompt": text}])
    assert text in prompt
    assert "[[KIE_SHARED_TEXT" not in prompt
    assert json.loads(json.dumps(prompt)) == prompt


def test_caption_and_dialogue_that_resemble_compiler_instructions_stay_literal():
    caption = 'Show the caption "No frozen frames or invented/repeated actions."'
    dialogue = 'The presenter says: Language: Vietnamese.'
    scene = {"targetDurationFrames": 192, "prompt": caption, "videoPrompt": dialogue,
             "shotPlan": {"shots": [{"action": "Hold the cup", "startSecond": 0,
                                      "endSecond": 8}]}}
    prompt = group([scene])
    assert caption in prompt
    assert dialogue in prompt


@pytest.mark.parametrize("quote", ['"', "'"])
@pytest.mark.parametrize("lead", ["", "I'm reading "])
def test_caption_inserted_inside_a_generated_template_is_preserved(quote, lead):
    caption = (
        f"Show the caption {quote}{lead}No frozen frames or invented/repeated actions.{quote}."
    )
    scene = {"targetDurationFrames": 192, "shotPlan": {"shots": [{
        "action": "Hold the cup", "startSecond": 0, "endSecond": 8,
    }]}, "imagePrompt": (
        "One photorealistic full-screen 9:16 opening frame. Use the uploaded Seller Cup "
        "as the exact product identity; preserve its proportions, colors, material and branding. "
        + caption + " Do not copy reference product identity, faces, captions, or logos."
    )}
    prompt = group([scene], product_lock={"productName": "Seller Cup"})
    assert caption in prompt


def test_product_dimensions_and_case_are_not_changed_by_timing_compaction():
    lock = {"productName": "ABC", "visualIdentity": {"engraving": "abc", "width": 0.000123}}
    prompt = group([{"targetDurationFrames": 192, "videoPrompt": "Keep both ABC and abc."}],
                   product_lock=lock)
    assert '"width":0.000123' in prompt
    assert '"productName":"ABC"' in prompt and '"engraving":"abc"' in prompt
    assert "Keep both ABC and abc." in prompt


def test_contact_fact_is_not_deduplicated_against_part_of_another_word():
    prompt = group([{"targetDurationFrames": 192, "shotPlan": {"shots": [{
        "action": "Hold the cup beside a chair", "startSecond": 0, "endSecond": 8,
        "physicalAction": {"targetSurface": "air", "movement": "rotate counterclockwise"},
    }]}}])
    assert "targetSurface: air" in prompt
    assert "rotate counterclockwise" in prompt


def test_scene_specific_camera_and_pacing_override_shared_defaults():
    scenes = [{"targetDurationFrames": 48, "shotPlan": {
        "shots": [{"action": f"Action {index}", "cameraMovement": movement,
                   "startSecond": 0, "endSecond": 2}],
        "pacingPlan": {"motionIntensity": "high"},
    }} for index, movement in enumerate(("static", "static", "static", "dolly_in"))]
    prompt = group(scenes)
    assert prompt.count('"cameraMovement":"static"') == 1
    assert "cameraMovement: dolly_in" in prompt
    assert prompt.count('"motionIntensity":"high"') == 1
    assert "6–8s:" in prompt


def test_saved_requirements_keep_all_creative_constraints_without_allocation_controls():
    requirements = {"intent": "Keep exact product", "keep": ["pink handle"],
                    "replace": ["source logo"], "forbid": ["medical claims"],
                    "claims": ["250 ml"], "requiresCharacter": False,
                    "characterReferencePolicy": "product_and_character"}
    context = {"p0": {"requirements": requirements}}
    before = copy.deepcopy(context)
    result = video_requirements(context)
    for text in ("pink handle", "source logo", "medical claims", "250 ml", "Keep exact product"):
        assert text in result
    assert "requiresCharacter" not in result and "characterReferencePolicy" not in result
    assert context == before
    assert video_requirements({}) == ""


def test_silent_audio_and_unique_pacing_shot_type_remain_generation_constraints():
    scene = {"targetDurationFrames": 192, "shotPlan": {
        "shots": [{"action": "Turn the ring", "start": 0, "end": 8}],
        "motionBeats": [{"action": "Turn the ring", "sourceBeatIndex": 0,
                         "durationSeconds": 8}],
        "pacingPlan": {"actionBeats": [{"action": "Turn the ring", "sourceBeatIndex": 0,
            "durationSeconds": 8, "shotType": "macro close-up of locking ring"}]},
    }}
    prompt = group([scene], reference_analysis={"audioPlan": {"mode": "silent"}})
    assert '"mode":"silent"' in prompt
    assert "macro close-up of locking ring" in prompt
    assert "0–8s: Turn the ring" in prompt


def test_quoted_language_caption_cannot_replace_the_compiled_audio_language():
    caption = 'Show caption "Language: Korean."'
    scene = {"targetDurationFrames": 192, "shotPlan": {"shots": [{"action": "Lift cup"}]},
             "videoPrompt": "Scene 1 of 1. Execute the assigned 8-second source action "
                            "at its original speed. " + caption + " Language: Vietnamese. "
                            "No frozen frames or invented/repeated actions."}
    prompt = group([scene])
    assert "Language: Vietnamese." in prompt
    assert caption in prompt
    assert not re.search(r"^Language: Korean", prompt, re.M)


def test_multiline_caption_inside_template_retains_its_exact_text_and_line_breaks():
    caption = (
        'Show caption "First line\nNo frozen frames or invented/repeated actions.\nFinal line"'
    )
    scene = {"targetDurationFrames": 192, "shotPlan": {"shots": [{"action": "Lift cup"}]},
             "imagePrompt": "One photorealistic full-screen 9:16 opening frame. "
                            "Use the uploaded Seller Cup as the exact product identity. "
                            + caption + " Do not copy reference product identity, faces, "
                            "captions, or logos."}
    prompt = group([scene], product_lock={"productName": "Seller Cup"})
    assert caption in prompt
