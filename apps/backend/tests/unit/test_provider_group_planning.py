from __future__ import annotations

import copy
import hashlib
import re
from types import SimpleNamespace
from uuid import uuid4

import pytest

from tests.smart_remake_expectations import install_expectations
from viraldy.modules.smart_remake.engine.kie_adapter import (
    build_kie_group_request,
    validate_kie_video_input,
)
from viraldy.modules.smart_remake.engine.video_directions import video_requirements
from viraldy.modules.smart_remake.preflight_contracts import PreflightRequest
from viraldy.modules.smart_remake.preflight_service import calculate_preflight
from viraldy.modules.smart_remake.provider_group_planning import freeze_provider_groups
from viraldy.modules.smart_remake.timeline_planner import build_timeline_plan
from viraldy.shared.errors.base import AppError


def context(*, count=12, prompt_length=0, character=False, target_duration=8,
            video_model="veo3_lite"):
    plan = build_timeline_plan(
        target_duration=target_duration,
        source_frame_count=count * 48,
        reference_start_frame=0,
        cut_frames=list(range(0, count * 48 + 1, 48)),
        timing_mode="fit_target",
    )
    plan["renderPlan"]["videoModel"] = video_model
    if video_model == "veo3_lite":
        plan["renderPlan"].pop("videoResolution", None)
    value = {
        **plan,
        "characterKey": "character" if character else None,
        "sceneMap": {
            "scenes": [
                {
                    **unit,
                    "prompt": "Show the seller bottle.",
                    "imagePrompt": "Seller bottle opening frame.",
                    "videoPrompt": "Move the seller bottle naturally. "
                    + "detailed direction " * prompt_length,
                }
                for unit in plan["renderPlan"]["units"]
            ]
        },
        "sourceOpeningFrames": {
            unit["id"]: {
                "sourceMediaHash": hashlib.sha256(b"source").hexdigest(),
                "frame": unit["sourceStartFrame"],
                "layoutHash": "b" * 64,
                "extractorVersion": "source-opening-frame-v1",
            }
            for unit in plan["renderPlan"]["units"]
        },
        "p0": {"requirements": {"intent": "Keep every source scene.", "keep": ["blue color"]}},
    }
    install_expectations(value, source_bytes=b"source", product_bytes=b"product")
    return value


def assert_requests_fit(value, plan):
    snapshot = value["generationExpectations"]
    by_id = {scene["renderUnitId"]: scene for scene in snapshot["scenes"]}
    units = {unit["id"]: unit for unit in plan["units"]}
    suffix = video_requirements({**value, "renderPlan": plan})
    for group in plan["groups"]:
        scenes = [{**units[identity], **by_id[identity]} for identity in group["renderUnitIds"]]
        request = build_kie_group_request(
            scenes=scenes,
            segments=group["segments"],
            reference_image_urls=["https://1.1.1.1/opening.png", "https://1.1.1.1/ending.png"],
            has_character_reference=bool(value.get("characterKey")),
            product_lock=snapshot["productLock"],
            reference_analysis=snapshot["sourceContext"],
        )
        request["input"]["prompt"] += suffix
        validate_kie_video_input(request["input"])
        prompt = request["input"]["prompt"]
        blocks = re.findall(
            r"(\[00:\d+\.\d{3}–00:\d+\.\d{3}\] SCENE \d+\n.*?)"
            r"(?=\n\n\[00:|\Z)", prompt, re.DOTALL,
        )
        assert len(blocks) == len(group["renderUnitIds"])
        for index, (scene, segment, block) in enumerate(zip(
            scenes, group["segments"], blocks, strict=True,
        )):
            assert block.startswith(
                f"[00:{segment['inFrame'] / 24:06.3f}–00:{segment['outFrame'] / 24:06.3f}] "
                f"SCENE {index + 1}\n"
            )
            assert scene["videoPrompt"] in block
        assert "blue color" in prompt and "Keep every source scene." in prompt
        assert "SHARED SCENE DIRECTION TEXT" not in prompt


def test_many_logical_scenes_remain_one_provider_call_when_payload_and_duration_fit():
    value = context()
    before = copy.deepcopy(value)
    plan = freeze_provider_groups(value)
    assert len(plan["groups"]) == 1
    assert len(plan["groups"][0]["renderUnitIds"]) == 12
    assert_requests_fit(value, plan)
    assert value == before


@pytest.mark.parametrize("duration,expected_calls", [(8, 1), (16, 2)])
def test_long_prompts_never_create_additional_paid_video_calls(duration, expected_calls):
    value = context(prompt_length=100, target_duration=duration)
    plan = freeze_provider_groups(value)
    assert len(plan["groups"]) == expected_calls
    assert [identity for group in plan["groups"] for identity in group["renderUnitIds"]] == [
        unit["id"] for unit in plan["units"]
    ]
    assert_requests_fit(value, plan)
    row = SimpleNamespace(
        id=uuid4(),
        revision=1,
        context_json={**value, "renderPlan": plan},
        state_json={
            "targetDuration": duration,
            "scenes": [{"id": unit["id"]} for unit in plan["units"]],
        },
    )
    result = calculate_preflight(
        PreflightRequest(action="render", projectId=str(row.id), expectedRevision=1),
        mode="fixture",
        bounds={},
        row=row,
    )
    assert result.scope.sceneCount == 12
    assert result.calls.video == expected_calls


def test_single_long_scene_prompt_is_preserved_in_one_provider_request():
    value = context(count=1, prompt_length=2000)
    original = value["sceneMap"]["scenes"][0]["videoPrompt"]
    plan = freeze_provider_groups(value)
    assert len(plan["groups"]) == 1
    assert_requests_fit(value, plan)
    assert value["sceneMap"]["scenes"][0]["videoPrompt"] == original


def test_extra_provider_groups_cannot_be_frozen_for_eight_second_output():
    value = context()
    original = value["renderPlan"]["groups"][0]
    value["renderPlan"]["groups"] = [
        {**original, "id": "extra-first", "renderUnitIds": original["renderUnitIds"][:6]},
        {**original, "id": "extra-second", "renderUnitIds": original["renderUnitIds"][6:]},
    ]
    with pytest.raises(AppError) as error:
        freeze_provider_groups(value)
    assert error.value.code == "SMART_REMAKE_PROVIDER_PLAN_UPDATE_REQUIRED"


def test_legacy_group_plan_is_unchanged():
    value = context()
    value["sourceSceneMap"].pop("timingMode")
    assert freeze_provider_groups(value) == value["renderPlan"]


@pytest.mark.parametrize("character", [False, True])
@pytest.mark.parametrize("scene_count", [1, 12])
def test_planner_validates_two_composed_frames_for_every_provider_window(
    monkeypatch, character, scene_count
):
    from viraldy.modules.smart_remake import provider_group_planning

    value = context(count=scene_count, character=character, target_duration=16)
    original = provider_group_planning.build_group_request
    references = []

    def capture(**kwargs):
        references.append(kwargs["reference_image_urls"])
        assert len(kwargs["reference_image_urls"]) == 2
        return original(**kwargs)

    monkeypatch.setattr(provider_group_planning, "build_group_request", capture)
    plan = freeze_provider_groups(value)
    assert len(plan["groups"]) == len(references) == 2
