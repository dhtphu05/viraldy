from __future__ import annotations

import copy
import hashlib
from types import SimpleNamespace
from uuid import uuid4

import pytest

from tests.smart_remake_expectations import install_expectations
from viraldy.modules.smart_remake import kie_workflow, timeline_service
from viraldy.modules.smart_remake import service as boundary_service
from viraldy.modules.smart_remake.project_policy import stable_hash
from viraldy.modules.smart_remake.timeline_planner import build_timeline_plan
from viraldy.shared.errors.base import AppError


@pytest.fixture
def enqueue_runtime(monkeypatch):
    plan = build_timeline_plan(
        target_duration=8,
        source_frame_count=192,
        reference_start_frame=0,
        cut_frames=[0, 48, 192],
    )
    plan["renderPlan"]["groupingPolicy"] = "fixed_provider_windows"
    workspace_id, project_id, actor_id = uuid4(), uuid4(), uuid4()
    prefix = f"workspaces/{workspace_id}/smart-remake/{project_id}/inputs"
    objects = {
        f"{prefix}/source.mp4": b"owned reference video",
        f"{prefix}/product.png": b"owned seller product",
    }
    assets = {
        role: {
            "storageKey": key,
            "mediaHash": hashlib.sha256(objects[key]).hexdigest(),
        }
        for role, key in zip(("source", "product"), objects, strict=True)
    }
    context = {"schemaVersion": 2, **copy.deepcopy(plan)}
    context["p0"] = {
        "actorId": str(actor_id),
        "inputHash": stable_hash({role: asset["mediaHash"] for role, asset in assets.items()}),
        "assets": assets,
        "requirements": {"intent": "Preserve the source action", "requiresCharacter": False},
        "rights": {
            "providerDisclosureAcknowledged": True,
            **{
                role: {
                    "declared": True,
                    "basis": "owned",
                    "scope": "offline test pilot",
                    "evidenceNote": "Test-owned input fixtures",
                }
                for role in assets
            },
        },
        "budgetPolicy": {"capUsd": "10", "maxAttempts": 20, "maxDurationSeconds": 1800},
    }
    for role, asset in assets.items():
        context[f"{role}Key"] = asset["storageKey"]
        context[f"{role}MediaHash"] = asset["mediaHash"]
    row = SimpleNamespace(
        id=project_id,
        workspace_id=workspace_id,
        actor_id=actor_id,
        revision=1,
        context_json=context,
        state_json={
            "schemaVersion": 2,
            "revision": 1,
            "provider": "kie",
            "targetDuration": 8,
            **copy.deepcopy(plan),
            "scenes": [
                {**unit, "index": index, "versions": []}
                for index, unit in enumerate(plan["renderPlan"]["units"])
            ],
        },
    )
    operation = SimpleNamespace(status="running", result_json={})
    queued = []

    class Repository:
        async def project(self, workspace_id, project_id, **kwargs):
            assert (workspace_id, project_id) == (row.workspace_id, row.id)
            return row

        async def start(self, *args):
            return row, operation, True

        async def finish(self, op, status, result):
            op.status, op.result_json = status, copy.deepcopy(result)

    class MemoryMedia:
        def __init__(self):
            self.reads = []

        async def read(self, key):
            self.reads.append(key)
            return objects[key]

    row.media = MemoryMedia()
    install_expectations(
        context, source_bytes=b"owned reference video", product_bytes=b"owned seller product",
    )
    repair = SimpleNamespace(repository=Repository(), media=row.media, workspace_id=workspace_id)

    async def queue(*args):
        queued.append(copy.deepcopy(operation.result_json))
        return SimpleNamespace(id=uuid4())

    async def response(*args):
        return {"submitted": True}

    monkeypatch.setattr(kie_workflow, "_service", lambda *args: repair)
    monkeypatch.setattr(kie_workflow, "_render_response", response)
    monkeypatch.setattr(timeline_service, "_queue", queue)
    monkeypatch.setattr(boundary_service, "require_kie_renderer", lambda settings: None)
    return row, operation, queued


@pytest.mark.asyncio
async def test_enqueue_freezes_complete_group_provider_plan_before_worker_dispatch(enqueue_runtime):
    row, operation, queued = enqueue_runtime
    response = await timeline_service.enqueue_timeline_render(
        object(),
        SimpleNamespace(ai_mode="live", openai_api_key="fixture-token"),
        row.workspace_id,
        row.id,
        1,
        "initial",
        actor_id=row.actor_id,
    )
    assert response == {"submitted": True}
    assert len(queued) == 1
    assert queued[0]["renderPlan"] == row.context_json["renderPlan"]
    assert queued[0]["renderPlanHash"] == kie_workflow._fingerprint(row.context_json["renderPlan"])
    assert operation.result_json["tasks"] == {}
    assert row.revision == 2
    row.context_json["renderPlan"]["imageQuality"] = "medium"
    assert operation.result_json["renderPlan"]["imageQuality"] == "max"
    assert operation.result_json["renderPlan"]["imageModel"] == "gpt-image-2.6-sunburst"
    assert operation.result_json["renderPlan"]["imageComplexity"] == "high"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "settings,code",
    [
        (
            SimpleNamespace(ai_mode="fixture", openai_api_key="fixture-token"),
            "SMART_REMAKE_FIXTURE_MODE",
        ),
        (SimpleNamespace(ai_mode="live", openai_api_key=None), "OPENAI_IMAGES_NOT_CONFIGURED"),
    ],
)
async def test_new_image_plan_requires_live_openai_before_job_is_queued(
    enqueue_runtime, settings, code
):
    row, operation, queued = enqueue_runtime
    with pytest.raises(AppError, match=code):
        await timeline_service.enqueue_timeline_render(
            object(), settings, row.workspace_id, row.id, 1, "initial", actor_id=row.actor_id
        )
    assert not queued
    assert row.revision == 1
    assert operation.status == "failed"
    assert operation.result_json["errorCode"] == code


@pytest.mark.asyncio
async def test_current_product_only_plan_does_not_require_openai(enqueue_runtime, monkeypatch):
    row, _, queued = enqueue_runtime
    for plan in (row.context_json["renderPlan"], row.state_json["renderPlan"]):
        for key in (
            "groupingPolicy",
            "groups",
            "renderGroupBreaks",
            "videoModel",
            "videoResolution",
            "imageModel",
            "imageQuality",
            "imageComplexity",
            "imageSize",
        ):
            plan.pop(key)

    def fail_guard(settings):
        pytest.fail("Legacy product-only plan must not require an image provider.")

    monkeypatch.setattr(boundary_service, "require_openai_images", fail_guard)
    with pytest.raises(AppError, match="SMART_REMAKE_PROVIDER_PLAN_UPDATE_REQUIRED"):
        await timeline_service.enqueue_timeline_render(
            object(),
            SimpleNamespace(ai_mode="live"),
            row.workspace_id,
            row.id,
            1,
            "initial",
            actor_id=row.actor_id,
        )
    assert queued == []


@pytest.mark.asyncio
async def test_missing_owned_intake_blocks_before_input_reads_or_queue(enqueue_runtime):
    row, operation, queued = enqueue_runtime
    row.context_json.pop("p0")
    with pytest.raises(AppError, match="SMART_REMAKE_INTAKE_REQUIRED"):
        await timeline_service.enqueue_timeline_render(
            object(),
            SimpleNamespace(ai_mode="live", openai_api_key="fixture-token"),
            row.workspace_id,
            row.id,
            1,
            "no-intake",
            actor_id=row.actor_id,
        )
    assert queued == []
    assert row.media.reads == []
    assert row.revision == 1
    assert operation.status == "failed"


@pytest.mark.asyncio
async def test_legacy_plan_without_current_snapshot_cannot_queue_new_paid_work(enqueue_runtime):
    row, operation, queued = enqueue_runtime
    row.context_json.pop("generationExpectations")
    row.context_json.pop("expectationsHash")
    with pytest.raises(AppError, match="SMART_REMAKE_EXPECTATIONS_REQUIRED"):
        await timeline_service.enqueue_timeline_render(
            object(), SimpleNamespace(ai_mode="live", openai_api_key="fixture-token"),
            row.workspace_id, row.id, 1, "legacy-needs-compile", actor_id=row.actor_id,
        )
    assert queued == [] and row.revision == 1
    assert operation.status == "failed"
