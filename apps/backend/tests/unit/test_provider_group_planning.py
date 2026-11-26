from __future__ import annotations

import copy
import hashlib
import json
from types import SimpleNamespace
from uuid import uuid4

import pytest

from tests.smart_remake_expectations import install_expectations
from viraldy.modules.smart_remake.engine.kie_adapter import (
    build_kie_group_request,
    validate_kie_video_input,
)
from viraldy.modules.smart_remake.generation_budget import saved_requirements_prompt
from viraldy.modules.smart_remake.generation_expectations import expectations_hash
from viraldy.modules.smart_remake.preflight_contracts import PreflightRequest
from viraldy.modules.smart_remake.preflight_service import calculate_preflight
from viraldy.modules.smart_remake.provider_group_planning import freeze_provider_groups
from viraldy.modules.smart_remake.timeline_planner import build_timeline_plan
from viraldy.shared.errors.base import AppError


def context(*, count=12, prompt_length=0, character=False, target_duration=8):
    plan = build_timeline_plan(
        target_duration=target_duration,
        source_frame_count=count * 48,
        reference_start_frame=0,
        cut_frames=list(range(0, count * 48 + 1, 48)),
        timing_mode="fit_target",
    )
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
    suffix = "\n\nGENERATION EXPECTATIONS HASH: " + expectations_hash(snapshot)
    suffix += saved_requirements_prompt({**value, "renderPlan": plan})
    for group in plan["groups"]:
        scenes = [{**units[identity], **by_id[identity]} for identity in group["renderUnitIds"]]
        request = build_kie_group_request(
            scenes=scenes,
            segments=group["segments"],
            reference_image_urls=["https://1.1.1.1/product.png"],
            has_character_reference=bool(value.get("characterKey")),
            product_lock=snapshot["productLock"],
            reference_analysis=snapshot["sourceContext"],
        )
        request["input"]["prompt"] += suffix
        validate_kie_video_input(request["input"])
        lines = request["input"]["prompt"].splitlines()
        shared_prefix = "SHARED SCENE DIRECTION TEXT: "
        shared = next(
            (
                json.loads(line.removeprefix(shared_prefix))
                for line in lines
                if line.startswith(shared_prefix)
            ),
            {},
        )
        direction_prefix = "Scene direction (shotPlan times are local to THIS scene): "
        serialized = [
            json.loads(line.removeprefix(direction_prefix))
            for line in lines
            if line.startswith(direction_prefix)
        ]
        assert [direction["renderUnitId"] for direction in serialized] == group["renderUnitIds"]
        for scene, direction in zip(scenes, serialized, strict=True):
            restored = direction["videoPrompt"]
            for token, literal in shared.items():
                restored = restored.replace(token, literal)
            assert restored == scene["videoPrompt"]


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
