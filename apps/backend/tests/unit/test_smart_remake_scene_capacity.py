from __future__ import annotations

import copy
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from tests.unit.test_smart_remake_timeline_runtime import project
from tests.unit.test_smart_remake_timeline_runtime import runtime as _runtime_fixture
from viraldy.modules.smart_remake import kie_workflow, timeline_service
from viraldy.modules.smart_remake.assembly_snapshots import record_assembly
from viraldy.modules.smart_remake.engine.kie_adapter import (
    build_kie_group_request,
    build_kie_video_request,
)
from viraldy.modules.smart_remake.inspection.contracts import (
    FrameRange,
    InspectionConstraints,
    InspectionSubject,
)
from viraldy.modules.smart_remake.inspection.core import _source_bounds, _windows
from viraldy.modules.smart_remake.inspection_mappings import inspection_mapping_projection
from viraldy.modules.smart_remake.repair_schemas import SaveTimelineRequest
from viraldy.modules.smart_remake.timeline_planner import build_render_groups
from viraldy.modules.smart_remake.timeline_service import validate_manifest
from viraldy.shared.errors.base import AppError

runtime = _runtime_fixture


@pytest.mark.asyncio
@pytest.mark.parametrize("timing_mode", [None, "source_rhythm", "fit_target"])
async def test_fresh_render_of_historical_plan_requires_update_before_queue(
    runtime, monkeypatch, timing_mode
):
    service, row, _ = runtime
    if timing_mode is not None:
        row.state_json["sourceSceneMap"]["timingMode"] = timing_mode
    monkeypatch.setattr(kie_workflow, "_service", lambda *args: service)
    monkeypatch.setattr(
        "viraldy.modules.smart_remake.service.require_kie_renderer", lambda settings: None
    )
    queue = AsyncMock(side_effect=AssertionError("An old plan cannot queue new paid work"))
    monkeypatch.setattr(timeline_service, "_queue", queue)
    service.media.read = AsyncMock(side_effect=AssertionError("No generation media reads"))
    with pytest.raises(AppError, match="SMART_REMAKE_PROVIDER_PLAN_UPDATE_REQUIRED"):
        await timeline_service.enqueue_timeline_render(
            None,
            SimpleNamespace(ai_mode="fixture"),
            row.workspace_id,
            row.id,
            1,
            "fresh-old-plan",
        )
    queue.assert_not_awaited()
    service.media.read.assert_not_awaited()


@pytest.mark.asyncio
async def test_existing_historical_render_reconciles_without_new_plan_gate(runtime, monkeypatch):
    service, row, repo = runtime
    old_operation = SimpleNamespace(id="old-operation", status="running", result_json={})
    repo.start = AsyncMock(return_value=(row, old_operation, False))
    monkeypatch.setattr(kie_workflow, "_service", lambda *args: service)
    monkeypatch.setattr(
        "viraldy.modules.smart_remake.service.require_kie_renderer", lambda settings: None
    )
    old_job = SimpleNamespace(id="old-job")
    queue = AsyncMock(return_value=old_job)
    monkeypatch.setattr(timeline_service, "_queue", queue)
    monkeypatch.setattr(
        kie_workflow, "_render_response", AsyncMock(return_value={"processingJobId": old_job.id})
    )
    result = await timeline_service.enqueue_timeline_render(
        None, SimpleNamespace(ai_mode="fixture"), row.workspace_id, row.id, 1, "old-key"
    )
    assert result["processingJobId"] == old_job.id
    assert queue.await_args.args[3] is old_operation


def payload_split_project(*, manual_breaks=None):
    # Historical compiled plans remain readable/exportable; new plans never split by payload.
    row = project((16,) * 12)
    plan = row.state_json["renderPlan"]
    plan.update(
        videoModel="veo3_lite",
        imageModel="gpt-image-2.6-sunburst",
        imageQuality="max",
        imageComplexity="high",
        imageSize="720x1280",
        renderGroupBreaks=manual_breaks or [],
        groups=build_render_groups(
            plan["units"], render_group_breaks=sorted({3, 6, 9, *(manual_breaks or [])})
        ),
    )
    row.context_json["renderPlan"] = copy.deepcopy(plan)
    return row


@pytest.mark.parametrize("manual_breaks", [None, [5]])
def test_manifest_accepts_frozen_payload_groups_in_addition_to_duration_groups(manual_breaks):
    row = payload_split_project(manual_breaks=manual_breaks)
    assert len(row.state_json["renderPlan"]["groups"]) > 1
    validate_manifest(row)


@pytest.mark.parametrize("durations", [(16,) * 12, (32,) * 12])
def test_fixed_provider_window_plan_accepts_exactly_one_or_two_full_clips(durations):
    row = payload_split_project()
    if sum(durations) == 384:
        row = project(durations)
        row.state_json["renderPlan"].update(
            {
                key: value
                for key, value in payload_split_project().state_json["renderPlan"].items()
                if key not in {"units", "groups"}
            }
        )
    plan = row.state_json["renderPlan"]
    plan["groupingPolicy"] = "fixed_provider_windows"
    plan["groups"] = build_render_groups(plan["units"])
    row.context_json["renderPlan"] = copy.deepcopy(plan)
    validate_manifest(row)
    assert len(plan["groups"]) == row.state_json["targetDuration"] / 8


@pytest.mark.parametrize("damage", ["extra_groups", "manual_breaks", "partial_group", "no_groups"])
def test_fixed_provider_windows_never_accept_extra_or_partial_provider_calls(damage):
    row = payload_split_project()
    plan = row.state_json["renderPlan"]
    plan["groupingPolicy"] = "fixed_provider_windows"
    if damage == "manual_breaks":
        plan["renderGroupBreaks"] = [3]
    elif damage == "partial_group":
        plan["groups"] = build_render_groups(plan["units"])
        plan["groups"][0]["targetDurationFrames"] = 191
    elif damage == "no_groups":
        for key in (
            "groups", "videoModel", "imageModel", "imageQuality", "imageComplexity", "imageSize"
        ):
            plan.pop(key)
    row.context_json["renderPlan"] = copy.deepcopy(plan)
    with pytest.raises(AppError, match="SMART_REMAKE_TIMELINE_INVALID"):
        validate_manifest(row)


def test_long_prompt_keeps_every_scene_in_one_eight_second_provider_request():
    scenes = [
        {
            "videoPrompt": (
                f"VISIBLE_ACTION_{index}: " + "specific physical direction " * 150
            ).strip(),
            "targetDurationFrames": 16,
        }
        for index in range(12)
    ]
    request = build_kie_group_request(
        scenes=scenes,
        segments=[{"inFrame": index * 16, "outFrame": (index + 1) * 16} for index in range(12)],
        reference_image_urls=["https://1.1.1.1/opening.png", "https://1.1.1.1/ending.png"],
    )
    assert request["input"]["duration"] == 8
    prompt = request["input"]["prompt"]
    assert all(f"] SCENE {index + 1}\n" in prompt for index in range(len(scenes)))
    assert all(scene["videoPrompt"] in prompt for scene in scenes)


@pytest.mark.parametrize("damage", ["omitted", "duplicated", "reordered", "missing_manual_break"])
def test_frozen_payload_groups_cannot_change_whole_unit_coverage_or_manual_breaks(damage):
    row = payload_split_project(manual_breaks=[5])
    plan = row.state_json["renderPlan"]
    if damage == "missing_manual_break":
        plan["renderGroupBreaks"] = []
        plan["groups"] = build_render_groups(plan["units"])
        plan["renderGroupBreaks"] = [5]
    elif damage == "omitted":
        plan["groups"].pop()
    elif damage == "duplicated":
        plan["groups"].append(copy.deepcopy(plan["groups"][-1]))
    else:
        plan["groups"].reverse()
    row.context_json["renderPlan"] = copy.deepcopy(plan)
    with pytest.raises(AppError, match="SMART_REMAKE_TIMELINE_INVALID"):
        validate_manifest(row)


def adapted_project():
    row = project((192, 192))
    source = row.state_json["sourceSceneMap"]
    first = source["scenes"][0]
    source.update(timingMode="fit_target", sourceFrameCount=720)
    source["scenes"] = [{**first, "endFrame": 720, "targetDurationFrames": 384}]
    for index, (unit, item) in enumerate(
        zip(
            row.state_json["renderPlan"]["units"],
            row.state_json["draftTimeline"]["items"],
            strict=False,
        )
    ):
        unit.update(
            sourceSceneId=first["id"],
            sourceStartFrame=index * 360,
            sourceEndFrame=(index + 1) * 360,
            fragmentIndex=index,
            fragmentCount=2,
        )
        item["sourceSceneId"] = first["id"]
    row.context_json["sourceSceneMap"] = copy.deepcopy(source)
    row.context_json["renderPlan"] = copy.deepcopy(row.state_json["renderPlan"])
    return row


def test_more_than_four_valid_source_scenes_can_save_and_validate():
    row = project((32,) * 6)
    validate_manifest(row)
    request = SaveTimelineRequest(
        expectedRevision=1,
        idempotencyKey="six-scenes",
        items=[
            {
                "renderUnitId": unit["id"],
                "versionId": scene["activeVersionId"],
                "inFrame": 0,
                "outFrame": 32,
            }
            for unit, scene in zip(
                row.state_json["renderPlan"]["units"], row.state_json["scenes"], strict=False
            )
        ],
    )
    assert len(request.items) == 6


def test_frozen_assembly_preserves_mapping_for_every_scene_beyond_four():
    row = project((32,) * 6)
    prefix = f"workspaces/{row.workspace_id}/smart-remake/{row.id}"
    for scene in row.state_json["scenes"]:
        scene["versions"][0].update(
            storageKey=f"{prefix}/{scene['id']}", mediaHash="a" * 64, frameCount=192
        )
    row.context_json["p0"] = record_assembly(
        {},
        project_id=str(row.id),
        timeline=row.state_json["draftTimeline"],
        state=row.state_json,
        storage_key=f"{prefix}/final",
        media_hash="b" * 64,
        technical_check={"status": "passed", "frameCount": 192},
        constraints_hash="c" * 64,
        context_hash="d" * 64,
        revision=1,
        actor_id="actor",
        operation_id="compose",
    )
    mappings = inspection_mapping_projection(row, row.workspace_id)["inspectionMappings"]
    final = [item for item in mappings if item["from"]["timebase"] == "final"]
    assert len(final) == 6
    assert {item["sceneId"] for item in final} == {
        scene["id"] for scene in row.state_json["scenes"]
    }


def test_one_logical_source_scene_can_have_two_bound_provider_fragments():
    validate_manifest(adapted_project())


@pytest.mark.parametrize(
    "damage",
    [
        "source_gap",
        "source_overlap",
        "fragment_order",
        "fragment_count",
        "logical_duration",
        "missing_source",
    ],
)
def test_adapted_manifest_never_loses_or_reorders_source_evidence(damage):
    row = adapted_project()
    source, plan = row.state_json["sourceSceneMap"], row.state_json["renderPlan"]
    if damage == "source_gap":
        plan["units"][1]["sourceStartFrame"] += 1
    elif damage == "source_overlap":
        plan["units"][1]["sourceStartFrame"] -= 1
    elif damage == "fragment_order":
        plan["units"][1]["fragmentIndex"] = 0
    elif damage == "fragment_count":
        plan["units"][1]["fragmentCount"] = 3
    elif damage == "logical_duration":
        source["scenes"][0]["targetDurationFrames"] = 383
    else:
        source["scenes"][0]["endFrame"] = 719
    row.context_json["sourceSceneMap"] = copy.deepcopy(source)
    row.context_json["renderPlan"] = copy.deepcopy(plan)
    with pytest.raises(AppError, match="SMART_REMAKE_TIMELINE_INVALID"):
        validate_manifest(row)


def test_kie_groups_preserve_six_logical_directions_in_one_provider_clip():
    scenes = [{"videoPrompt": f"Action {index}", "targetDurationFrames": 32} for index in range(6)]
    segments = [{"inFrame": index * 32, "outFrame": (index + 1) * 32} for index in range(6)]
    request = build_kie_group_request(
        scenes=scenes, segments=segments,
        reference_image_urls=["https://1.1.1.1/opening.png", "https://1.1.1.1/ending.png"]
    )
    assert request["input"]["duration"] == 8
    assert all(f"Action {index}" in request["input"]["prompt"] for index in range(6))


def test_adapted_single_and_group_prompts_use_output_timing_without_original_speed():
    scene = {
        "videoPrompt": "Open then pour within the assigned output time",
        "targetDurationFrames": 96,
        "rawDurationFrames": 192,
        "sourceRange": {"startFrame": 0, "endFrame": 240},
        "shotPlan": {"timingMode": "fit_target", "shots": [{"action": "Open then pour"}]},
    }
    single = build_kie_video_request(scene=scene, product_image_url="https://1.1.1.1/product.png")
    group = build_kie_group_request(
        scenes=[scene],
        segments=[{"inFrame": 0, "outFrame": 96}],
        reference_image_urls=["https://1.1.1.1/opening.png", "https://1.1.1.1/ending.png"],
    )
    for request in (single, group):
        assert "original speed" not in request["input"]["prompt"]
        assert "assigned output" in request["input"]["prompt"].lower()


def test_final_inspection_uses_every_scene_window_beyond_four():
    subject = InspectionSubject(
        kind="assembly",
        projectId="project",
        assemblyId="assembly",
        mediaHash="a" * 64,
        range=FrameRange(inFrame=0, outFrame=192, timebase="final"),
    )
    constraints = InspectionConstraints(
        constraintsHash="b" * 64,
        manifestHash="c" * 64,
        requirements={},
        timeline={
            "items": [
                {
                    "sourceSceneId": str(index),
                    "renderUnitId": f"unit-{index}",
                    "targetStartFrame": index * 32,
                    "targetDurationFrames": 32,
                }
                for index in range(6)
            ]
        },
    )
    assert _windows(subject, constraints) == [
        (index * 32, (index + 1) * 32, str(index)) for index in range(6)
    ]


def test_fragment_source_evidence_is_bound_by_render_unit_not_shared_logical_scene():
    constraints = SimpleNamespace(
        expectations=SimpleNamespace(
            scenes=[
                SimpleNamespace(
                    renderUnitId=f"unit-{index}",
                    sourceSceneId="logical",
                    sourceRange=SimpleNamespace(startFrame=index * 360, endFrame=(index + 1) * 360),
                )
                for index in range(2)
            ]
        )
    )
    assert _source_bounds(
        constraints, SimpleNamespace(frameCount=720), "logical", render_unit_id="unit-1"
    ) == (360, 720, True)


def test_ambiguous_logical_source_evidence_is_never_guessed():
    constraints = SimpleNamespace(
        expectations=SimpleNamespace(
            scenes=[
                SimpleNamespace(
                    renderUnitId=f"unit-{index}",
                    sourceSceneId="logical",
                    sourceRange=SimpleNamespace(startFrame=index * 360, endFrame=(index + 1) * 360),
                )
                for index in range(2)
            ]
        )
    )
    with pytest.raises(ValueError, match="retained scene expectations"):
        _source_bounds(constraints, SimpleNamespace(frameCount=720), "logical")
