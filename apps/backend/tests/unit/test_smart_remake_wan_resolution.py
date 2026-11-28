# ruff: noqa: F811 -- imported pytest fixture is resolved by name.
"""New 480P plans cannot change the resolution of retained 720P requests."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from tests.smart_remake_expectations import install_expectations
from tests.unit.test_provider_group_planning import context
from tests.unit.test_smart_remake_grouped_workflow import grouped  # noqa: F401
from viraldy.modules.smart_remake.engine import config
from viraldy.modules.smart_remake.service import health_payload
from viraldy.modules.smart_remake.timeline_planner import build_timeline_plan
from viraldy.modules.smart_remake.timeline_service import _validate_group_plan

WAN = "wan/3-0-video"


def test_new_wan_plans_default_to_480p_and_keep_two_eight_second_windows(monkeypatch):
    monkeypatch.delenv("SMART_REMAKE_KIE_VIDEO_MODEL", raising=False)
    monkeypatch.delenv("SMART_REMAKE_KIE_VIDEO_RESOLUTION", raising=False)
    plan = build_timeline_plan(target_duration=16, source_frame_count=480,
                               reference_start_frame=0, cut_frames=[0, 120, 240, 480],
                               timing_mode="fit_target")["renderPlan"]
    assert plan["videoModel"] == WAN and plan["videoResolution"] == "480P"
    assert len(plan["groups"]) == 2
    assert all(group["targetDurationFrames"] == 192 for group in plan["groups"])
    assert health_payload(SimpleNamespace(ai_mode="live"))["kieVideoResolution"] == "480P"


@pytest.mark.parametrize("resolution", ["480P", "720P", "1080P"])
def test_explicit_wan_resolution_is_saved_and_validated(monkeypatch, resolution):
    monkeypatch.setenv("SMART_REMAKE_KIE_VIDEO_MODEL", WAN)
    monkeypatch.setenv("SMART_REMAKE_KIE_VIDEO_RESOLUTION", resolution)
    assert config.get_kie_video_resolution() == resolution
    value = context(target_duration=16, video_model=WAN)
    plan = value["renderPlan"]
    assert plan["videoResolution"] == resolution
    _validate_group_plan(plan, {unit["id"] for unit in plan["units"]})


@pytest.mark.parametrize("resolution", ["360P", "4K", "auto"])
def test_unknown_resolution_cannot_fall_back_to_a_more_expensive_request(monkeypatch, resolution):
    monkeypatch.setenv("SMART_REMAKE_KIE_VIDEO_MODEL", WAN)
    monkeypatch.setenv("SMART_REMAKE_KIE_VIDEO_RESOLUTION", resolution)
    with pytest.raises(Exception) as error:
        config.get_kie_video_resolution()
    assert error.value.code == "SMART_REMAKE_VIDEO_RESOLUTION_INVALID"


@pytest.mark.parametrize("resolution", ["480P", "1080P"])
def test_veo_plan_rejects_resolution_outside_its_saved_720p_contract(resolution):
    plan = context(target_duration=16)["renderPlan"]
    plan["videoResolution"] = resolution
    with pytest.raises(ValueError, match="resolution"):
        _validate_group_plan(plan, {unit["id"] for unit in plan["units"]})


@pytest.mark.parametrize("resolution", [None, "720P"])
def test_optional_veo_resolution_preserves_legacy_720p_contract(resolution):
    plan = context(target_duration=16)["renderPlan"]
    plan["videoResolution"] = resolution
    _validate_group_plan(plan, {unit["id"] for unit in plan["units"]})


def test_legacy_veo_configuration_keeps_720p_default(monkeypatch):
    monkeypatch.setenv("SMART_REMAKE_KIE_VIDEO_MODEL", "veo3_lite")
    monkeypatch.delenv("SMART_REMAKE_KIE_VIDEO_RESOLUTION", raising=False)
    assert config.get_kie_video_resolution() == "720P"
    monkeypatch.setenv("SMART_REMAKE_KIE_VIDEO_RESOLUTION", "480P")
    with pytest.raises(Exception) as error:
        config.get_kie_video_resolution()
    assert error.value.code == "SMART_REMAKE_VIDEO_RESOLUTION_INVALID"


@pytest.mark.asyncio
@pytest.mark.parametrize("saved_resolution,expected", [(None, "720P"), ("480P", "480P")])
async def test_generation_uses_saved_resolution_not_current_default(
    grouped, monkeypatch, saved_resolution, expected,
):
    value = grouped
    value.row.context_json["renderPlan"]["videoModel"] = WAN
    if saved_resolution is not None:
        value.row.context_json["renderPlan"]["videoResolution"] = saved_resolution
    before = value.row.context_json["expectationsHash"]
    install_expectations(value.row.context_json, state=value.row.state_json)
    assert value.row.context_json["expectationsHash"] == before
    original_poll = value.client.get_task

    async def poll(task_id, *, model=None):
        return await original_poll(task_id)

    value.client.get_task = poll
    monkeypatch.setenv("SMART_REMAKE_KIE_VIDEO_RESOLUTION", "1080P")
    await value.runner.execute(value.row.id, value.op.id)
    assert len(value.client.submits) == 2
    assert all(request["input_data"]["resolution"] == expected
               for request in value.client.submits)


@pytest.mark.asyncio
async def test_resolution_change_only_reconciles_the_already_submitted_window(grouped):
    value = grouped
    value.row.context_json["renderPlan"].update(videoModel=WAN, videoResolution="720P")
    install_expectations(value.row.context_json, state=value.row.state_json)
    original_poll = value.client.get_task

    async def poll(task_id, *, model=None):
        return await original_poll(task_id)

    value.client.get_task = poll
    value.client.fail_download = True
    with pytest.raises(RuntimeError, match="retrieval can be retried"):
        await value.runner.execute(value.row.id, value.op.id)
    value.client.fail_download = False
    value.row.context_json["renderPlan"]["videoResolution"] = "480P"
    with pytest.raises(Exception) as error:
        await value.runner.execute(value.row.id, value.op.id)
    assert error.value.code == "SMART_REMAKE_RENDER_PLAN_CHANGED"
    assert len(value.client.submits) == 1
    assert value.client.submits[0]["input_data"]["resolution"] == "720P"
    assert len(value.images) == 2
