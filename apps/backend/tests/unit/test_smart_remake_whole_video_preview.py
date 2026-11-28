# ruff: noqa: F811 -- imported pytest fixture is resolved by name.
"""Preview composition never pretends individual trims or final content were approved."""

from __future__ import annotations

import copy
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from tests.unit.test_smart_remake_timeline_runtime import frozen_media, runtime  # noqa: F401
from tests.unit.test_smart_remake_twelve_second_windows import state_for, twelve_second_context
from viraldy.modules.smart_remake import timeline_service
from viraldy.modules.smart_remake.repair_schemas import PublishTimelineRequest
from viraldy.shared.errors.base import AppError


def test_legacy_publish_serialization_and_hash_input_do_not_gain_a_default_mode():
    value = PublishTimelineRequest(expectedRevision=1, idempotencyKey="old-key")
    assert value.model_dump(mode="json") == {"expectedRevision": 1, "idempotencyKey": "old-key"}
    assert (
        PublishTimelineRequest(
            expectedRevision=1,
            idempotencyKey="new",
            reviewMode="whole_video",
        ).model_dump(mode="json")["reviewMode"]
        == "whole_video"
    )


def test_whole_video_preview_skips_only_trim_confirmation():
    timeline = {"items": [{"versionId": "retained", "reviewed": False}]}
    timeline_service._ready(timeline, require_reviewed=False)
    with pytest.raises(AppError, match="SMART_REMAKE_TIMELINE_UNREVIEWED"):
        timeline_service._ready(timeline)
    timeline["items"][0]["versionId"] = None
    with pytest.raises(AppError):
        timeline_service._ready(timeline, require_reviewed=False)


@pytest.mark.asyncio
async def test_whole_video_compose_uses_unreviewed_retained_ranges_without_auto_approval(
    runtime,
    monkeypatch,  # noqa: F811
):
    service, row, repo = runtime
    _, operation, _ = await repo.start(row.workspace_id, row.id, "preview", "hash")
    operation.result_json = {
        "kind": "compose",
        "reviewMode": "whole_video",
        "expectedRevision": 1,
        "timeline": copy.deepcopy(row.state_json["draftTimeline"]),
        "mediaManifest": frozen_media(row),
    }

    async def compose(*args):
        return b"output", {"status": "passed", "frameCount": 192}

    monkeypatch.setattr(timeline_service, "compose_timeline", compose)
    await timeline_service.TimelineWorkflow(service).execute(row.id, operation.id)
    assert operation.status == "completed"
    assert not any(item["reviewed"] for item in row.state_json["draftTimeline"]["items"])
    assert row.state_json["finalStorageKey"] == "new-output"
    assert not row.context_json.get("p0", {}).get("release", {}).get("activeApprovalId")


@pytest.mark.asyncio
async def test_explicit_whole_video_preview_enqueue_is_free_and_idempotent(
    runtime,
    monkeypatch,  # noqa: F811
):
    from viraldy.modules.smart_remake import kie_workflow

    service, row, repo = runtime
    calls = []
    monkeypatch.setattr(kie_workflow, "_service", lambda *args: service)

    async def queue(session, repair, project, operation, kind):
        calls.append((str(operation.id), kind))
        return SimpleNamespace(id=uuid4())

    monkeypatch.setattr(timeline_service, "_queue", queue)
    request = PublishTimelineRequest(
        expectedRevision=1,
        idempotencyKey="whole-preview",
        reviewMode="whole_video",
    )
    for _ in range(2):
        await timeline_service.enqueue_publish(
            object(),
            SimpleNamespace(),
            row.workspace_id,
            row.id,
            request,
        )
    assert len(repo.operations) == 1
    assert len({identity for identity, _ in calls}) == 1
    assert all(kind == "smart_remake_compose" for _, kind in calls)


def automatic_runtime():
    context = twelve_second_context()
    context["p0"].update(inputHash="owned", actorId=str(uuid4()))
    state = state_for(context)
    tasks = {}
    for group in context["renderPlan"]["groups"]:
        task_id = f"provider-{group['id']}"
        tasks[f"group:{group['id']}"] = {"taskId": task_id, "status": "submitted"}
        for segment in group["segments"]:
            scene = next(
                value for value in state["scenes"] if value["id"] == segment["renderUnitId"]
            )
            version_id = str(uuid4())
            scene["activeVersionId"] = version_id
            scene["versions"] = [
                {
                    "id": version_id,
                    "storageKey": f"private/{group['id']}",
                    "mediaHash": "a" * 64,
                    "technicalCheck": {"status": "passed"},
                    "frameCount": 144,
                    "providerMetadata": {
                        "renderGroupId": group["id"],
                        "providerRequestId": task_id,
                    },
                }
            ]
            item = next(
                value
                for value in state["draftTimeline"]["items"]
                if value["renderUnitId"] == scene["id"]
            )
            item.update(
                versionId=version_id, inFrame=segment["inFrame"], outFrame=segment["outFrame"]
            )
    state["revision"] = 4
    row = SimpleNamespace(id=uuid4(), workspace_id=uuid4(), context_json=context, state_json=state)
    operation = SimpleNamespace(
        id=uuid4(), status="running", result_json={"kind": "render", "tasks": tasks}
    )
    repository = SimpleNamespace(project=AsyncMock(return_value=row), finish=AsyncMock())
    service = SimpleNamespace(
        repository=repository, workspace_id=row.workspace_id, settings=object()
    )
    return row, operation, service


@pytest.mark.asyncio
async def test_automatic_preview_pending_marker_and_crash_retry_keep_the_same_local_key(
    monkeypatch,
):
    from viraldy.modules.smart_remake.project_preview import (
        mark_automatic_preview,
        queue_automatic_preview,
    )

    row, operation, service = automatic_runtime()
    assert mark_automatic_preview(row, operation)
    marker = copy.deepcopy(row.context_json["p0"]["preview"])
    assert marker["status"] == "pending"
    assert not any(item["reviewed"] for item in row.state_json["draftTimeline"]["items"])
    operation.status = "completed"
    calls = AsyncMock(return_value={"operationId": str(uuid4()), "status": "running"})
    service.repository.session = object()
    monkeypatch.setattr(timeline_service, "enqueue_publish", calls)
    for _ in range(2):
        await queue_automatic_preview(service, row, operation)
    assert calls.await_count == 2
    requests = [call.args[4] for call in calls.await_args_list]
    assert requests[0].idempotencyKey == requests[1].idempotencyKey == marker["requestKey"]
    assert all(request.reviewMode == "whole_video" for request in requests)


@pytest.mark.asyncio
async def test_local_preview_failure_keeps_paid_render_completed_and_only_exposes_local_retry(
    monkeypatch,
):
    from viraldy.modules.smart_remake.project_preview import (
        mark_automatic_preview,
        public_project_preview,
        queue_automatic_preview,
    )

    row, operation, service = automatic_runtime()
    mark_automatic_preview(row, operation)
    operation.status = "completed"
    service.repository.session = object()
    failure = AsyncMock(side_effect=AppError("SMART_REMAKE_QUEUE_UNAVAILABLE", "local queue down"))
    monkeypatch.setattr(timeline_service, "enqueue_publish", failure)
    await queue_automatic_preview(service, row, operation)
    assert operation.status == "completed" and "errorCode" not in operation.result_json
    preview = public_project_preview(row)
    assert preview["status"] == "failed" and preview["retryable"] is True
    assert "requestKey" not in preview and "storageKey" not in str(preview)


def test_changed_trim_projects_preview_stale_without_mutating_persisted_state():
    from viraldy.modules.smart_remake.project_preview import (
        mark_automatic_preview,
        public_project_preview,
    )

    row, operation, _ = automatic_runtime()
    mark_automatic_preview(row, operation)
    row.state_json["draftTimeline"]["items"][0]["inFrame"] += 1
    before = copy.deepcopy(row.context_json)
    assert public_project_preview(row)["status"] == "stale"
    assert row.context_json == before


def test_technical_failure_or_unaccepted_candidate_never_gets_an_automatic_preview():
    from viraldy.modules.smart_remake.project_preview import mark_automatic_preview

    row, operation, _ = automatic_runtime()
    row.state_json["scenes"][0]["versions"][0]["technicalCheck"]["status"] = "failed"
    assert mark_automatic_preview(row, operation) is False
    assert "preview" not in row.context_json["p0"]


@pytest.mark.asyncio
async def test_local_failure_with_database_down_cannot_reclassify_paid_generation(monkeypatch):
    from viraldy.modules.smart_remake.project_preview import (
        mark_automatic_preview,
        queue_automatic_preview,
    )

    row, operation, service = automatic_runtime()
    mark_automatic_preview(row, operation)
    operation.status = "completed"
    service.repository.session = object()
    service.repository.project = AsyncMock(side_effect=[row, RuntimeError("database unavailable")])
    monkeypatch.setattr(
        timeline_service, "enqueue_publish", AsyncMock(side_effect=RuntimeError("local"))
    )
    await queue_automatic_preview(service, row, operation)
    assert operation.status == "completed" and "errorCode" not in operation.result_json


@pytest.mark.asyncio
async def test_worker_commits_paid_completion_before_local_preview_and_duplicate_only_resumes(
    monkeypatch,
):
    from viraldy.modules.smart_remake import kie_workflow, project_preview

    row, operation, service = automatic_runtime()
    repository = service.repository
    repository.operation = AsyncMock(return_value=operation)

    @asynccontextmanager
    async def guard(operation_id):
        yield True

    repository.execution_guard = guard
    commits = []

    async def finish(op, status, result):
        op.status, op.result_json = status, copy.deepcopy(result)
        commits.append((status, row.context_json["p0"].get("preview", {}).get("status")))

    repository.finish = finish
    monkeypatch.setattr(kie_workflow, "require_generation_policy", AsyncMock())
    local_handoff = AsyncMock()
    monkeypatch.setattr(project_preview, "queue_automatic_preview", local_handoff)
    client = SimpleNamespace(
        get_task=AsyncMock(return_value={"status": "completed", "output": {}}),
        create_task=AsyncMock(side_effect=AssertionError("No paid retry")),
    )
    worker = kie_workflow.KieWorkflow(service, client=client)
    await worker.execute(row.id, operation.id, reconcile_only=True)
    assert commits[-1] == ("completed", "pending")
    assert local_handoff.await_count == 1
    assert client.get_task.await_count == 2
    await worker.execute(row.id, operation.id, reconcile_only=True)
    assert local_handoff.await_count == 2
    assert client.get_task.await_count == 2 and client.create_task.await_count == 0
