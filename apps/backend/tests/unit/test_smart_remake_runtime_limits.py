from __future__ import annotations

import copy
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from viraldy.modules.jobs.dispatcher import CeleryJobDispatcher, DispatchResult
from viraldy.modules.jobs.registry import JobType, get_job_definition
from viraldy.modules.jobs.repository import WorkerJobRepository
from viraldy.modules.jobs.service import JobService
from viraldy.modules.smart_remake.engine.config import get_kie_poll_timeout_seconds
from viraldy.modules.smart_remake.runtime_limits import kie_job_runtime_input


def _workload(groups=1, *, images=True, repair=False, structured=False):
    plan = {
        "groups": [{"renderUnitIds": [str(index)]} for index in range(groups)],
        "imageModel": "sunburst" if images else None,
    }
    result = {"kind": "repair" if repair else "render", "renderPlan": plan}
    if structured:
        result["request"] = {"repairIntent": {"instruction": "Keep the action"}}
    return kie_job_runtime_input({"scenes": [{}] * groups}, {}, result)


def test_runtime_uses_frozen_provider_groups_not_a_global_24_hour_grant(monkeypatch):
    monkeypatch.delenv("KIE_POLL_TIMEOUT_SECONDS", raising=False)
    small = get_job_definition(JobType.SMART_REMAKE_KIE, input_json=_workload())
    assert 900 < small.hard_timeout_seconds < 7200
    assert small.hard_timeout_seconds - small.soft_timeout_seconds == 60
    large = get_job_definition(JobType.SMART_REMAKE_KIE, input_json=_workload(20))
    assert large.soft_timeout_seconds > 20 * 900
    assert large.hard_timeout_seconds > small.hard_timeout_seconds


def test_runtime_counts_two_conditioned_bookends_and_one_structured_repair_analysis():
    plain = get_job_definition(JobType.SMART_REMAKE_KIE, input_json=_workload(images=False))
    with_image = get_job_definition(JobType.SMART_REMAKE_KIE, input_json=_workload())
    repair = get_job_definition(
        JobType.SMART_REMAKE_KIE, input_json=_workload(20, repair=True, structured=True)
    )
    assert with_image.hard_timeout_seconds > plain.hard_timeout_seconds
    assert 0 < repair.hard_timeout_seconds - with_image.hard_timeout_seconds <= 300
    plan = {"groups": [{"renderUnitIds": ["a", "b", "c"]}], "imageModel": "sunburst"}
    units = kie_job_runtime_input({}, {}, {"kind": "render", "renderPlan": plan})
    assert units["kie_runtime"]["conditioningImageCount"] == 2
    assert _workload()["kie_runtime"]["conditioningImageCount"] == 2
    assert _workload(repair=True)["kie_runtime"]["conditioningImageCount"] == 2


def test_dense_fixed_windows_count_only_conditioning_references_actually_generated():
    groups = [{"renderUnitIds": [str(index) for index in range(100)]}] * 2
    result = {"kind": "render", "renderPlan": {"groups": groups, "imageModel": "sunburst"}}
    data = kie_job_runtime_input({}, {}, result)
    assert data["kie_runtime"]["videoCallCount"] == 2
    assert data["kie_runtime"]["conditioningImageCount"] == 4
    assert get_job_definition(JobType.SMART_REMAKE_KIE, input_json=data).hard_timeout_seconds < 7200
    character = kie_job_runtime_input({}, {"characterKey": "owned-character"}, result)
    assert character["kie_runtime"]["conditioningImageCount"] == 4


def test_only_server_frozen_plan_controls_workload_not_browser_or_current_context():
    result = {"kind": "render", "renderPlan": {"groups": [{"renderUnitIds": ["a"]}]}}
    context = {"renderPlan": {"groups": [{}] * 200}, "kie_runtime": {"videoCallCount": 99999}}
    before = copy.deepcopy((context, result))
    data = kie_job_runtime_input({}, context, result)
    assert data["kie_runtime"]["videoCallCount"] == 1
    assert (context, result) == before


def test_legacy_ungrouped_render_and_repair_use_actual_saved_work():
    state = {"scenes": [{}, {}, {}, {}, {}]}
    render = kie_job_runtime_input(state, {}, {"kind": "render"})
    repair = kie_job_runtime_input(state, {}, {"kind": "repair"})
    assert render["kie_runtime"]["videoCallCount"] == 5
    assert repair["kie_runtime"]["videoCallCount"] == 1
    assert kie_job_runtime_input({}, {}, {"kind": "compose"}) == {}
    assert kie_job_runtime_input({}, {}, {"kind": "render"}) == {}


def test_poll_window_is_frozen_for_dispatch_and_recovery(monkeypatch):
    monkeypatch.setenv("KIE_POLL_TIMEOUT_SECONDS", "1275.5")
    assert get_kie_poll_timeout_seconds() == 1275.5
    data = _workload(12)
    original = get_job_definition(JobType.SMART_REMAKE_KIE, input_json=data)
    monkeypatch.setenv("KIE_POLL_TIMEOUT_SECONDS", "60")
    assert get_job_definition(JobType.SMART_REMAKE_KIE, input_json=data) == original


@pytest.mark.parametrize("value", ["nan", "NaN", "inf", "+inf", "-inf", "Infinity"])
def test_nonfinite_poll_config_cannot_create_an_endless_worker_window(monkeypatch, value):
    monkeypatch.setenv("KIE_POLL_TIMEOUT_SECONDS", value)
    with pytest.raises(ValueError, match="finite"):
        get_kie_poll_timeout_seconds()
    with pytest.raises(ValueError, match="finite"):
        _workload()


@pytest.mark.parametrize("value", ["", "invalid", "0", "-1"])
def test_existing_invalid_or_nonpositive_poll_config_keeps_default(monkeypatch, value):
    monkeypatch.setenv("KIE_POLL_TIMEOUT_SECONDS", value)
    assert get_kie_poll_timeout_seconds() == 900


@pytest.mark.parametrize(
    "change",
    [
        {"schemaVersion": 9},
        {"videoCallCount": True},
        {"videoCallCount": -1},
        {"conditioningImageCount": -1},
        {"analysisCallCount": 2},
        {"pollTimeoutSeconds": float("inf")},
        {"pollTimeoutSeconds": float("nan")},
        {"pollTimeoutSeconds": "900"},
    ],
)
def test_malformed_runtime_metadata_cannot_inflate_worker_window(change):
    data = _workload(12)
    data["kie_runtime"].update(change)
    assert (
        get_job_definition(JobType.SMART_REMAKE_KIE, input_json=data).hard_timeout_seconds == 7200
    )


def test_legacy_jobs_and_other_types_keep_existing_limits():
    assert get_job_definition(JobType.SMART_REMAKE_KIE).hard_timeout_seconds == 7200
    data = _workload(20)
    data["kie_runtime"]["hardTimeoutSeconds"] = 10**18
    expected = get_job_definition(JobType.SMART_REMAKE_KIE, input_json=_workload(20))
    assert get_job_definition(JobType.SMART_REMAKE_KIE, input_json=data) == expected
    definition = get_job_definition(JobType.TIKTOK_SCORE_RUN, input_json=data)
    assert (definition.soft_timeout_seconds, definition.hard_timeout_seconds) == (2340, 2400)
    assert (
        get_job_definition(JobType.SMART_REMAKE_COMPOSE, input_json=data).hard_timeout_seconds
        == 900
    )


def test_dispatch_and_stale_recovery_use_the_same_frozen_window(monkeypatch):
    from viraldy.worker.tasks import process_asset

    data = _workload(20)
    definition = get_job_definition(JobType.SMART_REMAKE_KIE, input_json=data)
    calls = []
    monkeypatch.setattr(
        process_asset.run_processing_job,
        "apply_async",
        lambda **kw: (calls.append(kw) or SimpleNamespace(id="task")),
    )
    job_id, now = uuid4(), datetime.now(UTC)
    CeleryJobDispatcher().dispatch_job(job_id, JobType.SMART_REMAKE_KIE, input_json=data)
    assert calls[0]["time_limit"] == definition.hard_timeout_seconds
    assert calls[0]["soft_time_limit"] == definition.soft_timeout_seconds
    job = SimpleNamespace(
        id=job_id,
        job_type=JobType.SMART_REMAKE_KIE,
        input_json=data,
        updated_at=now - timedelta(seconds=definition.hard_timeout_seconds + 119),
        attempt_count=1,
        max_attempts=3,
    )
    session = SimpleNamespace(execute=lambda _: SimpleNamespace(scalars=lambda: [job]))
    repo = WorkerJobRepository(session)
    recovered = []
    monkeypatch.setattr(repo, "mark_retrying", lambda *args: recovered.append(args[0].id))
    assert repo.recover_stale_jobs(now, 60) == []
    job.updated_at -= timedelta(seconds=2)
    assert repo.recover_stale_jobs(now, 60) == [job_id]
    assert recovered == [job_id]


@pytest.mark.asyncio
async def test_new_kie_dispatch_forwards_frozen_input_after_commit_only(monkeypatch):
    from viraldy.modules.jobs import service as module

    session = SimpleNamespace(commit=AsyncMock())
    repository = SimpleNamespace(
        record_dispatch_requested=AsyncMock(),
        record_dispatch_succeeded=AsyncMock(),
        record_dispatch_failed=AsyncMock(),
    )
    monkeypatch.setattr(module, "JobRepository", lambda _: repository)
    calls = []

    class Dispatcher:
        def dispatch_job(self, *args, **kwargs):
            assert session.commit.await_count == 1
            calls.append((args, kwargs))
            return DispatchResult("task", True)

    job = SimpleNamespace(id=uuid4(), job_type=JobType.SMART_REMAKE_KIE, input_json=_workload(12))
    await JobService(session, Dispatcher())._dispatch_created_job(job)
    assert calls == [((job.id, job.job_type), {"input_json": job.input_json})]


@pytest.mark.asyncio
async def test_timeline_queue_adds_trusted_frozen_workload_only_for_kie(monkeypatch):
    from viraldy.modules.smart_remake import kie_workflow, timeline_service

    calls = []

    async def request(*args):
        calls.append(args)
        return SimpleNamespace(id=uuid4())

    monkeypatch.setattr(
        timeline_service, "JobService", lambda _: SimpleNamespace(request_mvp_job=request)
    )
    monkeypatch.setattr(kie_workflow, "_dispatch", AsyncMock())
    service = SimpleNamespace(
        workspace_id=uuid4(),
        repository=SimpleNamespace(
            refresh=AsyncMock(),
            attach_processing_job=AsyncMock(),
        ),
    )
    row = SimpleNamespace(id=uuid4(), state_json={"scenes": [{}] * 20}, context_json={})
    result = {"kind": "render", "renderPlan": {"groups": [{"renderUnitIds": ["a"]}]}}
    operation = SimpleNamespace(id=uuid4(), request_hash="hash", result_json=result)
    await timeline_service._queue(object(), service, row, operation, JobType.SMART_REMAKE_KIE)
    assert calls[0][4]["kie_runtime"]["videoCallCount"] == 1
    await timeline_service._queue(object(), service, row, operation, JobType.SMART_REMAKE_COMPOSE)
    assert "kie_runtime" not in calls[1][4]


def test_recovery_redispatch_preserves_new_metadata_and_legacy_dispatch_calls(monkeypatch):
    from viraldy.modules.jobs import dispatcher as dispatcher_module
    from viraldy.worker.tasks import process_asset

    jobs = [
        SimpleNamespace(id=uuid4(), job_type=JobType.SMART_REMAKE_KIE, input_json=_workload(12)),
        SimpleNamespace(id=uuid4(), job_type=JobType.SMART_REMAKE_KIE, input_json={}),
        SimpleNamespace(id=uuid4(), job_type=JobType.MEDIA_ANALYSIS, input_json={}),
    ]
    session = SimpleNamespace(commit=lambda: None, close=lambda: None)
    repository = SimpleNamespace(
        recover_stale_jobs=lambda *args: [job.id for job in jobs],
        load_job=lambda key: next(job for job in jobs if job.id == key),
    )
    calls = []

    class Dispatcher:
        def dispatch_job(self, *args, **kwargs):
            calls.append((args, kwargs))

    monkeypatch.setattr(dispatcher_module, "CeleryJobDispatcher", Dispatcher)
    monkeypatch.setattr(process_asset, "create_worker_session", lambda: session)
    monkeypatch.setattr(process_asset, "WorkerJobRepository", lambda _: repository)
    monkeypatch.setattr(
        process_asset, "get_settings", lambda: SimpleNamespace(job_stale_after_seconds=60)
    )
    assert process_asset.recover_stale_processing_jobs.run() == {
        "recovered_job_ids": [str(job.id) for job in jobs]
    }
    assert calls == [
        ((jobs[0].id, jobs[0].job_type), {"input_json": jobs[0].input_json}),
        ((jobs[1].id, jobs[1].job_type), {}),
        ((jobs[2].id, jobs[2].job_type), {}),
    ]


@pytest.mark.asyncio
async def test_workflow_polling_uses_frozen_window_after_environment_changes(monkeypatch):
    from viraldy.modules.smart_remake import kie_workflow

    monkeypatch.setenv("KIE_POLL_TIMEOUT_SECONDS", "900")
    data = _workload()
    monkeypatch.setenv("KIE_POLL_TIMEOUT_SECONDS", "1")
    statuses = iter(
        [{"status": "processing"}, {"status": "completed", "output": {"video_url": "ok"}}]
    )
    client = SimpleNamespace(get_task=AsyncMock(side_effect=lambda _: next(statuses)))
    clock = iter([0, 500])
    monkeypatch.setattr(kie_workflow, "monotonic", lambda: next(clock))
    monkeypatch.setattr(kie_workflow.asyncio, "sleep", AsyncMock())
    monkeypatch.setattr(kie_workflow, "require_generation_policy", AsyncMock())
    monkeypatch.setattr(kie_workflow, "settle_generation_attempt", AsyncMock())
    runner = kie_workflow.KieWorkflow(
        SimpleNamespace(),
        client=client,
        poll_timeout_seconds=data["kie_runtime"]["pollTimeoutSeconds"],
    )
    operation = SimpleNamespace(result_json={"tasks": {"0": {"taskId": "submitted-once"}}})
    result = await runner._task(SimpleNamespace(), operation, 0, reconcile_only=False)
    assert result["url"] == "ok"
    assert client.get_task.await_count == 2


@pytest.mark.parametrize("with_runtime", [False, True])
def test_worker_threads_validated_frozen_poll_window_to_workflow(monkeypatch, with_runtime):
    from viraldy.modules.smart_remake import kie_worker
    from viraldy.modules.smart_remake import service as boundary_service

    monkeypatch.setenv("KIE_POLL_TIMEOUT_SECONDS", "900")
    data = _workload() if with_runtime else {}
    monkeypatch.setenv("KIE_POLL_TIMEOUT_SECONDS", "1")
    project_id, operation_id = uuid4(), uuid4()
    job = SimpleNamespace(
        subject_id=project_id,
        workspace_id=uuid4(),
        input_json={"project_id": str(project_id), "operation_id": str(operation_id), **data},
    )
    calls = []

    class Context:
        async def __aenter__(self):
            return object()

        async def __aexit__(self, *args):
            pass

    class Workflow:
        def __init__(self, *args, **kwargs):
            calls.append(kwargs)

        async def execute(self, project, operation):
            assert (project, operation) == (project_id, operation_id)
            return {"status": "completed"}

    engine = SimpleNamespace(dispose=AsyncMock())
    monkeypatch.setattr(kie_worker, "create_async_engine", lambda *args, **kwargs: engine)
    monkeypatch.setattr(kie_worker, "async_sessionmaker", lambda *args, **kwargs: Context)
    monkeypatch.setattr(kie_worker, "_service", lambda *args: object())
    monkeypatch.setattr(kie_worker, "KieWorkflow", Workflow)
    monkeypatch.setattr(boundary_service, "require_kie_renderer", lambda _: None)
    result = kie_worker.execute_kie_job(job, SimpleNamespace(database_url="fixture"), lambda: None)
    assert result == {"status": "completed"}
    assert calls[0]["poll_timeout_seconds"] == (900 if with_runtime else None)
    engine.dispose.assert_awaited_once()
