"""Performer execution roles supplement, rather than rewrite, frozen scene actions."""

from __future__ import annotations

import copy
import re

import pytest

from viraldy.modules.smart_remake.engine.kie_adapter import build_kie_group_request
from viraldy.modules.smart_remake.engine.performer_continuity import performer_continuity_directions
from viraldy.modules.smart_remake.engine.video_directions import video_brief


def test_continuity_brief_assigns_contacts_and_handoffs_per_performer_and_panel():
    directions = performer_continuity_directions()
    assert 0 < len(directions) < 650
    for detail in (
        "Where a performer is visible", "identity and outfit unchanged",
        "shots and clip joins", "two connected arms",
        "one hand to support/grip", "the other to interact", "tabletop can support",
        "Release an old contact", "free a supporting hand before adjusting",
        "support hand brings the rim/straw to the mouth", "free hand rests",
        "unless the action requires adjustment", "per performer/panel",
        "not a two-hand limit across a split screen",
    ):
        assert detail in directions
    assert not re.search(r"celebr|public figure|Vietnamese|Caucasian", directions, re.I)


@pytest.mark.parametrize("ending", [False, True])
def test_video_brief_includes_the_shared_execution_contract_once(ending):
    brief = video_brief({}, {}, ending=ending)
    assert brief.count(performer_continuity_directions()) == 1
    assert "FIRST image is the exact opening frame" in brief
    assert ("SECOND image is the exact final frame" in brief) is ending
    assert "At rapid cuts, enter the next action already underway" in brief
    assert "cut cleanly instead of blending the previous actor or hand contacts" in brief
    assert "At rapid cuts" not in performer_continuity_directions()


def test_group_retains_every_shot_timing_and_product_requirement_with_one_continuity_brief():
    scenes = [{
        "targetDurationFrames": 64,
        "shotPlan": {"shots": [{
            "action": action, "startSecond": 0, "endSecond": 64 / 24,
            "physicalAction": {"operator": operator, "contactPoint": contact},
            "stateBefore": f"before {index}", "stateAfter": f"after {index}",
            "subjectPresence": "person", "transitionOut": "hard_cut",
        }]},
    } for index, (action, operator, contact) in enumerate([
        ("Four-panel montage: place, sip, pour and present the cup.",
         "each panel's performer", "cup body"),
        ("One hand supports the cup while the other adjusts the straw.", "other hand", "straw"),
        ("Release the straw, then sip while holding the cup upright.", "mouth", "straw opening"),
    ])]
    product = {"productName": "Seller Tumbler", "mustPreserve": ["engraved STAR"],
               "productUsage": {"usageConstraints": ["Keep upright"]}}
    before = copy.deepcopy((scenes, product))
    result = build_kie_group_request(
        scenes=scenes,
        segments=[{"inFrame": i * 64, "outFrame": (i + 1) * 64} for i in range(3)],
        reference_image_urls=["https://1.1.1.1/open.png", "https://1.1.1.1/end.png"],
        product_lock=product,
    )
    prompt = result["input"]["prompt"]
    assert prompt.count(performer_continuity_directions()) == 1
    assert len(re.findall(r"^\[.*\] SCENE \d+", prompt, re.M)) == 3
    for scene in scenes:
        shot = scene["shotPlan"]["shots"][0]
        for key in ("action", "stateBefore", "stateAfter"):
            assert shot[key] in prompt
        assert shot["physicalAction"]["contactPoint"] in prompt
    for timing in ("[00:00.000–00:02.667]", "[00:02.667–00:05.333]", "[00:05.333–00:08.000]"):
        assert timing in prompt
    assert "engraved STAR" in prompt and "Keep upright" in prompt
    assert result["input"]["duration"] == 8
    assert (scenes, product) == before


def test_continuity_does_not_hide_an_upstream_product_mechanism_mismatch_by_rewriting_video_only():
    # Known upstream limitation: normalize this conflict before freezing Expectations.
    # This execution contract must not silently change only the KIE interpretation.
    action = "Press the lid button to retract the straw."
    scene = {"targetDurationFrames": 192, "shotPlan": {"shots": [{
        "action": action, "startSecond": 0, "endSecond": 8,
        "stateBefore": "straw extended", "stateAfter": "straw retracted",
    }]}}
    product = {"productName": "Seller Tumbler", "mustPreserve": ["Fixed straw; no retraction"]}
    before = copy.deepcopy((scene, product))
    prompt = build_kie_group_request(
        scenes=[scene], segments=[{"inFrame": 0, "outFrame": 192}], product_lock=product,
        reference_image_urls=["https://1.1.1.1/open.png", "https://1.1.1.1/end.png"],
    )["input"]["prompt"]
    assert action in prompt and "Fixed straw; no retraction" in prompt
    assert "straw extended → straw retracted" in prompt
    assert (scene, product) == before
