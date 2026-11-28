# ruff: noqa: F811 -- imported pytest fixtures are resolved by name.
"""Wan selection follows the saved provider plan through fresh work and restore."""
from __future__ import annotations

import copy
from types import SimpleNamespace

import pytest

from tests.smart_remake_expectations import install_expectations
from tests.unit.test_provider_group_planning import context
from tests.unit.test_smart_remake_grouped_workflow import grouped  # noqa: F401
from viraldy.modules.smart_remake import provider_group_planning
from viraldy.modules.smart_remake.engine import config
from viraldy.modules.smart_remake.service import health_payload
from viraldy.modules.smart_remake.timeline_planner import build_timeline_plan
from viraldy.modules.smart_remake.timeline_schemas import RenderPlan
from viraldy.modules.smart_remake.timeline_service import _validate_group_plan

WAN = "wan/3-0-video"


def test_new_plans_and_capabilities_default_to_wan_without_changing_provider_windows(monkeypatch):
    monkeypatch.delenv("SMART_REMAKE_KIE_VIDEO_MODEL", raising=False)
    for duration, calls in [(8, 1), (16, 2)]:
        plan = build_timeline_plan(target_duration=duration, source_frame_count=480,
                                   reference_start_frame=0, cut_frames=[0, 120, 240, 480],
                                   timing_mode="fit_target")["renderPlan"]
        assert plan["videoModel"] == WAN
        assert len(plan["groups"]) == calls
        assert all(group["targetDurationFrames"] == 192 for group in plan["groups"])
    assert health_payload(SimpleNamespace(ai_mode="live"))["kieVideoModel"] == WAN


@pytest.mark.parametrize("model", [WAN, "veo3_lite"])
def test_model_selection_and_saved_plan_validation_are_explicit(monkeypatch, model):
    monkeypatch.setenv("SMART_REMAKE_KIE_VIDEO_MODEL", model)
    assert config.get_kie_video_model() == model
    value = context(target_duration=16, video_model=model)
    plan = value["renderPlan"]
    assert plan["videoModel"] == model
    assert RenderPlan.model_validate(plan).videoModel == model
    _validate_group_plan(plan, {unit["id"] for unit in plan["units"]})


def test_invalid_model_configuration_cannot_silently_fall_back_to_veo(monkeypatch):
    monkeypatch.setenv("SMART_REMAKE_KIE_VIDEO_MODEL", "wan/not-a-real-model")
    with pytest.raises(Exception) as error:
        config.get_kie_video_model()
    assert error.value.code == "SMART_REMAKE_VIDEO_MODEL_INVALID"


def test_freezing_wan_checks_the_final_payload_and_keeps_every_scene(monkeypatch):
    monkeypatch.setenv("SMART_REMAKE_KIE_VIDEO_MODEL", WAN)
    value = context(count=25, target_duration=16, video_model=WAN)
    before = copy.deepcopy(value)
    frozen = provider_group_planning.freeze_provider_groups(value)
    assert frozen["videoModel"] == WAN
    assert len(frozen["groups"]) == 2
    assert [identity for group in frozen["groups"] for identity in group["renderUnitIds"]] == [
        unit["id"] for unit in frozen["units"]
    ]
    assert value == before


@pytest.mark.asyncio
async def test_wan_generation_and_restore_keep_two_calls_and_the_saved_model(grouped, monkeypatch):
    value = grouped
    value.row.context_json["renderPlan"]["videoModel"] = WAN
    install_expectations(value.row.context_json, state=value.row.state_json)
    original_poll = value.client.get_task
    polled_models = []

    async def poll(task_id, *, model=None):
        polled_models.append(model)
        return await original_poll(task_id)

    value.client.get_task = poll
    await value.runner.execute(value.row.id, value.op.id)
    assert len(value.client.submits) == 2
    for request in value.client.submits:
        assert request["model"] == WAN
        data = request["input_data"]
        assert data["duration"] == 8 and data["resolution"] == "720P"
        assert data["first_frame_url"] and data["last_frame_url"]
        assert not {"image_urls", "generation_type", "model", "enable_translation"} & data.keys()
    assert polled_models == [WAN, WAN]
    assert all(task["requestModel"] == task["model"] == WAN
               for task in value.op.result_json["tasks"].values())
    value.op.status = "running"
    monkeypatch.setenv("SMART_REMAKE_KIE_VIDEO_MODEL", "veo3_lite")
    await value.runner.execute(value.row.id, value.op.id, reconcile_only=True)
    assert len(value.client.submits) == 2
    assert polled_models == [WAN] * 4


@pytest.mark.asyncio
async def test_wan_upload_urls_are_not_part_of_the_durable_request_fingerprint(grouped):
    value = grouped
    value.row.context_json["renderPlan"]["videoModel"] = WAN
    install_expectations(value.row.context_json, state=value.row.state_json)
    original_poll = value.client.get_task

    async def poll(task_id, *, model=None):
        return await original_poll(task_id)

    value.client.get_task = poll
    await value.runner.execute(value.row.id, value.op.id)
    initial = [task["requestHash"] for task in value.op.result_json["tasks"].values()]
    value.op.status = "running"
    value.op.result_json = {"kind": "render", "tasks": {}}
    await value.runner.execute(value.row.id, value.op.id)
    assert [task["requestHash"] for task in value.op.result_json["tasks"].values()] == initial


@pytest.mark.asyncio
async def test_wan_final_prompt_limit_is_checked_before_any_paid_image_or_video(grouped):
    value = grouped
    value.row.context_json["renderPlan"]["videoModel"] = WAN
    value.row.context_json["sceneMap"]["scenes"][0]["videoPrompt"] = "x" * 21000
    install_expectations(value.row.context_json, state=value.row.state_json)
    with pytest.raises(Exception) as error:
        await value.runner.execute(value.row.id, value.op.id)
    assert error.value.code == "KIE_VALIDATION_FAILED"
    assert not value.images and not value.client.submits


@pytest.mark.asyncio
async def test_model_change_reconciles_existing_wan_task_without_starting_the_other_window(grouped):
    value = grouped
    value.row.context_json["renderPlan"]["videoModel"] = WAN
    install_expectations(value.row.context_json, state=value.row.state_json)
    original_poll = value.client.get_task
    polled_models = []

    async def poll(task_id, *, model=None):
        polled_models.append(model)
        return await original_poll(task_id)

    value.client.get_task = poll
    value.client.fail_download = True
    with pytest.raises(RuntimeError, match="retrieval can be retried"):
        await value.runner.execute(value.row.id, value.op.id)
    assert len(value.client.submits) == 1
    value.client.fail_download = False
    value.row.context_json["renderPlan"]["videoModel"] = "veo3_lite"
    with pytest.raises(Exception) as error:
        await value.runner.execute(value.row.id, value.op.id)
    assert error.value.code == "SMART_REMAKE_RENDER_PLAN_CHANGED"
    assert len(value.client.submits) == 1
    assert polled_models == [WAN, WAN]
