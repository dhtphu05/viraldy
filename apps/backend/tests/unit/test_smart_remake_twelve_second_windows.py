"""New Wan output is twelve seconds with sound, split into two frozen six-second calls."""

from __future__ import annotations

import copy
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from tests.smart_remake_expectations import install_expectations
from tests.unit.test_provider_group_planning import context
from tests.unit.test_smart_remake_grouped_enqueue import enqueue_runtime  # noqa: F401
from tests.unit.test_smart_remake_grouped_workflow import grouped  # noqa: F401
from tests.unit.test_smart_remake_rights import (
    MemoryMedia,
    MemoryRepository,
    image_upload,
    intake_payload,
    source_upload,
)
from viraldy.modules.smart_remake.preflight_contracts import PreflightRequest
from viraldy.modules.smart_remake.preflight_service import calculate_preflight
from viraldy.modules.smart_remake.project_intake import create_intake
from viraldy.modules.smart_remake.provider_group_planning import freeze_provider_groups
from viraldy.modules.smart_remake.timeline_planner import build_timeline_plan
from viraldy.modules.smart_remake.timeline_service import _validate_group_plan, validate_manifest

WAN = "wan/3-0-video"


def twelve_second_context():
    return {"schemaVersion": 2, **context(count=24, target_duration=12, video_model=WAN)}


def state_for(value):
    return {
        "schemaVersion": 2, "provider": "kie", "targetDuration": 12,
        **{key: copy.deepcopy(value[key]) for key in (
            "sourceSceneMap", "renderPlan", "draftTimeline",
        )},
        "scenes": [{**unit, "index": index, "versions": [], "activeVersionId": None}
                   for index, unit in enumerate(value["renderPlan"]["units"])],
    }


def test_twelve_seconds_keeps_every_scene_and_uses_exactly_two_six_second_windows():
    value = twelve_second_context()
    plan = value["renderPlan"]
    assert len(value["sourceSceneMap"]["scenes"]) == 24
    assert value["draftTimeline"]["totalFrames"] == 288
    assert len(plan["groups"]) == 2 and plan["audioRequired"] is True
    assert all(unit["rawDurationFrames"] == 144 for unit in plan["units"])
    assert all(group["rawDurationFrames"] == group["targetDurationFrames"] == 144
               for group in plan["groups"])
    _validate_group_plan(plan, {unit["id"] for unit in plan["units"]})
    validate_manifest(SimpleNamespace(context_json=value, state_json=state_for(value)))
    assert freeze_provider_groups(value) == plan


def test_long_source_scene_is_split_at_six_seconds_without_dropping_source_range():
    value = build_timeline_plan(
        target_duration=12, source_frame_count=720, reference_start_frame=0,
        cut_frames=[0, 720], timing_mode="fit_target",
    )
    units = value["renderPlan"]["units"]
    assert [unit["targetDurationFrames"] for unit in units] == [144, 144]
    assert [(unit["sourceStartFrame"], unit["sourceEndFrame"]) for unit in units] == [
        (0, 360), (360, 720),
    ]
    assert [group["segments"][0]["outFrame"]
            for group in value["renderPlan"]["groups"]] == [144, 144]


@pytest.mark.parametrize("duration,calls", [(8, 1), (16, 2)])
def test_legacy_durations_keep_eight_second_frozen_windows(duration, calls):
    value = context(count=8, target_duration=duration, video_model=WAN)
    plan = value["renderPlan"]
    assert len(plan["groups"]) == calls
    assert all(group["rawDurationFrames"] == 192 for group in plan["groups"])
    assert "audioRequired" not in plan
    assert freeze_provider_groups(value) == plan


def test_twelve_seconds_is_not_accepted_for_legacy_veo(monkeypatch):
    monkeypatch.setenv("SMART_REMAKE_KIE_VIDEO_MODEL", "veo3_lite")
    with pytest.raises(Exception) as error:
        build_timeline_plan(target_duration=12, source_frame_count=288, reference_start_frame=0,
                            cut_frames=[0, 144, 288], timing_mode="fit_target")
    assert error.value.code == "SMART_REMAKE_VIDEO_DURATION_INVALID"


def test_twelve_second_preflight_reserves_two_calls_and_four_bookends():
    value = twelve_second_context()
    value["p0"].update(targetDuration=12, budgetPolicy={"mode": "unlimited"})
    row = SimpleNamespace(id=uuid4(), revision=1, state_json=state_for(value), context_json=value)
    result = calculate_preflight(
        PreflightRequest(action="render", projectId=str(row.id), expectedRevision=1),
        mode="live", bounds={}, row=row,
    )
    assert result.calls.video == 2 and result.calls.image == 4
    assert not any(block.code == "PROVIDER_PLAN_UPDATE_REQUIRED" for block in result.blockers)


@pytest.mark.asyncio
async def test_new_twelve_second_intake_requires_sound():
    row = await create_intake(
        MemoryRepository(), MemoryMedia(), uuid4(), uuid4(), intake_payload(targetDuration=12),
        source_upload(), image_upload(),
    )
    assert row.context_json["audioRequired"] is True
    assert row.state_json["targetDuration"] == 12


@pytest.fixture
def twelve_runtime(grouped, monkeypatch):  # noqa: F811
    from viraldy.modules.smart_remake import kie_workflow

    monkeypatch.setattr(kie_workflow, "require_generation_policy", AsyncMock())
    monkeypatch.setattr(
        kie_workflow, "reserve_generation_attempt", AsyncMock(return_value=(None, True)),
    )
    monkeypatch.setattr(kie_workflow, "settle_generation_attempt", AsyncMock())
    value = twelve_second_context()
    grouped.row.context_json.update(value, audioRequired=True)
    grouped.row.state_json = state_for(value)
    original_poll = grouped.client.get_task

    async def poll(task_id, *, model=None):
        return await original_poll(task_id)

    grouped.client.get_task = poll
    return grouped


@pytest.mark.asyncio
async def test_frozen_twelve_second_workflow_submits_two_six_second_requests_with_audio(
    twelve_runtime,
):
    value = twelve_runtime
    await value.runner.execute(value.row.id, value.op.id)
    assert len(value.client.submits) == 2
    assert all(request["input_data"]["duration"] == 6 for request in value.client.submits)
    assert all(request["input_data"]["audio"] is True for request in value.client.submits)
    assert len(value.images) == 4
    assert value.op.result_json["windowContinuityVersion"] == "two-part-film-v1"
    assert value.op.result_json["conditioningPolicy"] == "source-frame-authority-v1"


@pytest.mark.asyncio
async def test_old_partially_prepared_twelve_second_operation_keeps_its_prompt_policy(
    twelve_runtime,
):
    value = twelve_runtime
    value.op.result_json["images"] = {"0": {"status": "completed", "requestHash": "old"}}
    await value.runner._freeze_plan(value.row, value.op)
    assert "windowContinuityVersion" not in value.op.result_json
    assert "conditioningPolicy" not in value.op.result_json


@pytest.mark.asyncio
@pytest.mark.parametrize("changed", ["audio", "duration"])
async def test_changed_audio_or_duration_reconciles_old_task_without_second_submit(
    twelve_runtime, changed,
):
    value = twelve_runtime
    value.client.fail_download = True
    with pytest.raises(RuntimeError, match="retrieval can be retried"):
        await value.runner.execute(value.row.id, value.op.id)
    assert len(value.client.submits) == 1
    value.client.fail_download = False
    if changed == "audio":
        value.row.context_json["renderPlan"]["audioRequired"] = False
    else:
        value.row.context_json["renderPlan"]["groups"][1]["rawDurationFrames"] = 192
    with pytest.raises(Exception) as error:
        await value.runner.execute(value.row.id, value.op.id)
    assert error.value.code == "SMART_REMAKE_RENDER_PLAN_CHANGED"
    assert len(value.client.submits) == 1 and len(value.images) == 2


def test_technical_check_uses_six_seconds_and_requires_audio(monkeypatch):
    from viraldy.modules.smart_remake import repair_service

    captured = {}

    def technical(data, **kwargs):
        captured.update(kwargs)
        return {"status": "passed"}

    monkeypatch.setattr(repair_service, "technical_check", technical)
    repair_service._new_version(
        b"video", "private/clip", {"prompt": "p", "imagePrompt": "i", "videoPrompt": "v"},
        None, {}, source="generated", audio_required=True, expected_duration=6,
    )
    assert captured == {"expected_duration": 6, "audio_required": True}


@pytest.mark.asyncio
async def test_legacy_browser_audio_false_cannot_turn_off_new_twelve_second_sound(
    enqueue_runtime,  # noqa: F811
):
    from viraldy.modules.smart_remake import timeline_service

    row, _, _ = enqueue_runtime
    value = twelve_second_context()
    previous_policy = row.context_json["p0"]
    row.context_json.update({key: item for key, item in value.items() if key != "p0"})
    row.context_json["p0"] = {**previous_policy, "targetDuration": 12}
    for role in ("source", "product"):
        row.context_json[f"{role}MediaHash"] = previous_policy["assets"][role]["mediaHash"]
    row.context_json["audioRequired"] = True
    for opening in row.context_json["sourceOpeningFrames"].values():
        opening["sourceMediaHash"] = row.context_json["sourceMediaHash"]
    row.state_json = {**state_for(value), "revision": 1}
    install_expectations(
        row.context_json, state=row.state_json, source_bytes=b"owned reference video",
        product_bytes=b"owned seller product",
    )
    await timeline_service.enqueue_timeline_render(
        object(), SimpleNamespace(ai_mode="live", openai_api_key="fixture-token"),
        row.workspace_id, row.id, 1, "initial", actor_id=row.actor_id, audio_required=False,
    )
    assert row.context_json["audioRequired"] is True
