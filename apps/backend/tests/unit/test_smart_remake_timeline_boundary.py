"""The timeline HTTP boundary delegates only owned, explicit v2 operations."""

import json
import sys
from importlib import import_module
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from viraldy.shared.errors.base import AppError


@pytest.fixture
def boundary(monkeypatch):
    module = import_module("viraldy.modules.smart_remake.router")
    monkeypatch.setattr(module, "require_workspace_permission", AsyncMock())
    monkeypatch.setenv("SMART_REMAKE_ENABLED", "true")
    monkeypatch.setenv("KIE_API_KEY", "offline-test-key")
    return module


def compile_args():
    return {
        "workspace_id": uuid4(),
        "current_user": object(),
        "db": object(),
        "settings": SimpleNamespace(ai_mode="fixture"),
        "mode": "smart_remake",
        "target_duration": "8",
        "aspect_ratio": "9:16",
        "language": "vi",
        "prompt": None,
        "description": None,
        "product_url": None,
        "product_title": None,
        "product_description": None,
        "reference_video": object(),
        "product_image": object(),
        "request_id": "test",
    }


@pytest.mark.asyncio
async def test_reference_compile_uses_persisted_timeline_service(boundary, monkeypatch):
    compile_timeline = AsyncMock(return_value={"schemaVersion": 2, "projectId": "draft"})
    monkeypatch.setitem(
        sys.modules,
        "viraldy.modules.smart_remake.timeline_compile",
        SimpleNamespace(compile_timeline_request=compile_timeline),
    )
    legacy = AsyncMock(side_effect=AssertionError("Legacy compile must not handle v2"))
    monkeypatch.setattr(boundary, "compile_request", legacy)
    values = compile_args()
    result = await boundary.compile_smart_remake_route(
        **values,
        timeline_mode="reference",
        reference_start_frame=48,
        source_cut_frames="[0,48,192]",
        render_group_breaks="[1]",
    )
    assert result.data["projectId"] == "draft"
    sent = compile_timeline.await_args.kwargs
    assert sent["session"] is values["db"]
    assert sent["workspace_id"] == values["workspace_id"]
    assert sent["reference_start_frame"] == 48
    assert sent["source_cut_frames"] == [0, 48, 192]
    assert sent["render_group_breaks"] == [1]
    legacy.assert_not_awaited()


@pytest.mark.asyncio
async def test_full_source_scope_and_unlimited_explicit_groups_reach_compiler(
    boundary, monkeypatch
):
    compile_timeline = AsyncMock(return_value={"schemaVersion": 2, "projectId": "draft"})
    monkeypatch.setitem(
        sys.modules, "viraldy.modules.smart_remake.timeline_compile",
        SimpleNamespace(compile_timeline_request=compile_timeline),
    )
    await boundary.compile_smart_remake_route(
        **compile_args(), timeline_mode="reference", analysis_scope="full_source",
        source_cut_frames="[0,48,96,144,192,240,288]", render_group_breaks="[1,5]",
    )
    assert compile_timeline.await_args.kwargs["analysis_scope"] == "full_source"
    assert compile_timeline.await_args.kwargs["render_group_breaks"] == [1,5]


def test_render_prompt_drafts_keep_more_than_four_scenes(boundary):
    scenes = [{"prompt": "p", "imagePrompt": "i", "videoPrompt": "v"} for _ in range(6)]
    assert len(boundary._timeline_prompt_drafts({"sceneMap": {"scenes": scenes}})) == 6


def test_source_cut_parser_does_not_truncate_by_an_arbitrary_text_budget(boundary):
    cuts = list(range(384))
    assert boundary._parse_source_cut_frames(json.dumps(cuts)) == cuts


@pytest.mark.asyncio
@pytest.mark.parametrize("cuts", ['{"start":0}', "[0,true,192]", '[0,"48",192]', "broken"])
async def test_malformed_source_cuts_rejected_before_compile(boundary, cuts):
    with pytest.raises(AppError) as error:
        await boundary.compile_smart_remake_route(
            **compile_args(),
            timeline_mode="reference",
            source_cut_frames=cuts,
        )
    assert error.value.code == "SMART_REMAKE_TIMELINE_INVALID"


@pytest.mark.asyncio
async def test_unknown_timeline_mode_does_not_fall_back(boundary):
    with pytest.raises(AppError) as error:
        await boundary.compile_smart_remake_route(**compile_args(), timeline_mode="guess")
    assert error.value.code == "SMART_REMAKE_TIMELINE_INVALID"


@pytest.mark.asyncio
@pytest.mark.parametrize("breaks", ["[true]", "[0]", "[1,1]", "[2,1]", "broken"])
async def test_invalid_group_breaks_rejected_before_compile(boundary, breaks):
    with pytest.raises(AppError) as error:
        await boundary.compile_smart_remake_route(
            **compile_args(), timeline_mode="reference", render_group_breaks=breaks
        )
    assert error.value.code == "SMART_REMAKE_TIMELINE_INVALID"


def render_args():
    project_id = uuid4()
    return {
        "workspace_id": uuid4(),
        "current_user": object(),
        "db": object(),
        "settings": SimpleNamespace(ai_mode="live"),
        "compile_result": json.dumps(
            {
                "schemaVersion": 2,
                "projectId": str(project_id),
                "revision": 3,
                "sceneMap": {
                    "scenes": [
                        {
                            "prompt": "Scene",
                            "imagePrompt": "Image",
                            "videoPrompt": "Video",
                            "durationSeconds": 999,
                        }
                    ]
                },
            }
        ),
        "product_image": None,
        "product_url": None,
        "provider": "kie",
        "project_name": "Seller video",
        "audio_required": False,
        "idempotency_key": "initial-render",
        "request_id": "test",
        "project_id": project_id,
        "expected_revision": 3,
    }


@pytest.mark.asyncio
async def test_v2_render_delegates_project_revision_and_only_prompt_edits(boundary, monkeypatch):
    enqueue = AsyncMock(return_value={"status": "submitted", "projectId": "owned"})
    monkeypatch.setitem(
        sys.modules,
        "viraldy.modules.smart_remake.timeline_service",
        SimpleNamespace(enqueue_timeline_render=enqueue),
    )
    monkeypatch.setattr(boundary, "render_request", AsyncMock(side_effect=AssertionError("v1")))
    values = render_args()
    result = await boundary.render_smart_remake_route(**values)
    assert result.data["projectId"] == "owned"
    sent = enqueue.await_args
    assert sent.args[3:6] == (values["project_id"], 3, "initial-render")
    assert sent.kwargs["prompt_drafts"] == [
        {"prompt": "Scene", "imagePrompt": "Image", "videoPrompt": "Video"},
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("missing", ["project_id", "expected_revision"])
async def test_v2_render_requires_explicit_owned_project_and_revision(boundary, missing):
    values = render_args()
    values[missing] = None
    with pytest.raises(AppError) as error:
        await boundary.render_smart_remake_route(**values)
    assert error.value.code == "SMART_REMAKE_TIMELINE_INVALID"


@pytest.mark.asyncio
async def test_v2_render_rejects_mismatched_project_identity(boundary):
    values = render_args()
    values["project_id"] = uuid4()
    with pytest.raises(AppError) as error:
        await boundary.render_smart_remake_route(**values)
    assert error.value.code == "SMART_REMAKE_TIMELINE_INVALID"


@pytest.mark.asyncio
async def test_v2_render_fixture_cannot_dispatch_kie(boundary):
    values = render_args()
    values["settings"] = SimpleNamespace(ai_mode="fixture")
    with pytest.raises(AppError) as error:
        await boundary.render_smart_remake_route(**values)
    assert error.value.code == "SMART_REMAKE_FIXTURE_MODE"


@pytest.mark.asyncio
async def test_v2_render_cannot_fall_back_to_legacy_renderer(boundary):
    values = render_args()
    values["provider"] = "flowkit"
    with pytest.raises(AppError) as error:
        await boundary.render_smart_remake_route(**values)
    assert error.value.code == "SMART_REMAKE_TIMELINE_PROVIDER_REQUIRED"


@pytest.mark.asyncio
async def test_timeline_save_and_publish_delegate_with_workspace_scope(boundary, monkeypatch):
    save, publish = (
        AsyncMock(return_value={"status": "completed"}),
        AsyncMock(return_value={"status": "running"}),
    )
    monkeypatch.setitem(
        sys.modules,
        "viraldy.modules.smart_remake.timeline_service",
        SimpleNamespace(save_timeline=save, enqueue_publish=publish),
    )
    scoped = object()
    monkeypatch.setattr(boundary, "_repair_service", lambda *_: scoped)
    workspace_id, project_id = uuid4(), uuid4()
    payload = SimpleNamespace(expectedRevision=2, idempotencyKey="use-segment")
    args = dict(
        workspace_id=workspace_id,
        project_id=project_id,
        payload=payload,
        current_user=object(),
        db=object(),
        settings=SimpleNamespace(ai_mode="fixture"),
        request_id="test",
    )
    response = await boundary.save_smart_remake_timeline(**args)
    assert response.data["status"] == "completed"
    assert save.await_args.args == (scoped, project_id, payload)
    response = await boundary.publish_smart_remake_timeline(**args)
    assert response.data["status"] == "running"
    assert publish.await_args.args[2:] == (workspace_id, project_id, payload)
