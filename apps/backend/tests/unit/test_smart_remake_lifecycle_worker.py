from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

from viraldy.modules.jobs.registry import JobType, get_job_definition
from viraldy.modules.smart_remake import inspection_tasks
from viraldy.shared.errors.base import AppError


def _job(**kwargs):
    project = uuid4()
    return SimpleNamespace(
        subject_type="smart_remake_project",
        subject_id=project,
        workspace_id=uuid4(),
        input_json={"project_id": str(project), "operation_id": str(uuid4())},
        **kwargs,
    )


def test_inspection_job_registered_with_no_paid_retries():
    definition = get_job_definition(JobType.SMART_REMAKE_INSPECT.value)
    assert definition.max_attempts == 1
    assert definition.result_subject_type == "smart_remake_project"
    assert definition.required_stages == (
        "loading_sources",
        "inspecting_media",
        "persisting_results",
    )


def test_worker_rejects_foreign_or_malformed_subject_before_database():
    job = _job()
    job.input_json["project_id"] = str(uuid4())
    with pytest.raises(AppError) as wrong:
        inspection_tasks.execute_inspection_job(job, None, lambda: None)
    assert wrong.value.code == "SMART_REMAKE_JOB_BINDING_INVALID"
    job = _job()
    job.input_json["operation_id"] = "invalid"
    with pytest.raises(AppError):
        inspection_tasks.execute_inspection_job(job, None, lambda: None)


@pytest.mark.parametrize(
    "outcome",
    [
        {"phase": "completed", "reportId": "report"},
        {"errorCode": "SMART_REMAKE_INSPECTION_FAILED", "needsReconciliation": False},
        {
            "errorCode": "SMART_REMAKE_INSPECTION_RECONCILIATION_REQUIRED",
            "needsReconciliation": True,
        },
        {"errorCode": "SMART_REMAKE_JOB_BINDING_INVALID", "actorMode": "foreign"},
        {"errorCode": "SMART_REMAKE_JOB_BINDING_INVALID", "actorMode": "missing"},
    ],
)
def test_worker_scopes_actor_disposes_engine_and_propagates_results(monkeypatch, outcome):
    job, actor = _job(), uuid4()
    if outcome.get("actorMode") == "foreign":
        job.input_json["actor_id"] = str(uuid4())
    calls = []
    session = object()

    class Context:
        async def __aenter__(self):
            return session

        async def __aexit__(self, *args):
            calls.append("session_closed")

    class Engine:
        async def dispose(self):
            calls.append("disposed")

    class Repository:
        async def operation(self, workspace, project, operation):
            assert workspace == job.workspace_id and project == job.subject_id
            assert str(operation) == job.input_json["operation_id"]
            return SimpleNamespace(
                result_json={
                    "kind": "inspection",
                    "actorId": None if outcome.get("actorMode") == "missing" else str(actor),
                    "contextHash": "context",
                    "snapshot": {
                        "constraintsHash": "constraints",
                        "manifestHash": "manifest",
                        "subject": {"mediaHash": "media"},
                    },
                }
            )

    repair = SimpleNamespace(repository=Repository(), media=object())
    monkeypatch.setattr(inspection_tasks, "create_async_engine", lambda *args, **kwargs: Engine())
    monkeypatch.setattr(
        inspection_tasks, "async_sessionmaker", lambda *args, **kwargs: lambda: Context()
    )
    monkeypatch.setattr(inspection_tasks, "_service", lambda s, settings, workspace: repair)

    def invoke_factory(s, workspace, project, operation, actor_id, metadata=None):
        assert actor_id == actor and workspace == job.workspace_id and s is session
        assert metadata["contextHash"] == "context"

        async def invoke(payload):
            calls.append("model")
            return {"findings": []}

        invoke.model_profile = {"provider": "fixture"}
        return invoke

    class Service:
        def __init__(self, repository, media, workspace, **kwargs):
            assert repository is repair.repository and media is repair.media

        async def execute(self, project, operation, *, invoke_model):
            assert invoke_model.model_profile == {"provider": "fixture"}
            assert await invoke_model({"prompt": "inspect"}) == {"findings": []}
            return outcome

    monkeypatch.setattr(inspection_tasks, "inspection_invoke", invoke_factory)
    monkeypatch.setattr(inspection_tasks, "InspectionService", Service)
    settings = SimpleNamespace(database_url="postgresql+asyncpg://fixture")
    if outcome.get("errorCode"):
        with pytest.raises(AppError) as failure:
            inspection_tasks.execute_inspection_job(job, settings, lambda: calls.append("active"))
        assert failure.value.code == outcome["errorCode"]
    else:
        assert (
            inspection_tasks.execute_inspection_job(job, settings, lambda: calls.append("active"))
            == outcome
        )
    if outcome.get("actorMode"):
        assert calls.count("model") == 0
    else:
        assert calls.count("active") >= 3
        assert calls.count("model") == 1
    assert calls[-2:] == ["session_closed", "disposed"]


def test_worker_dispatches_inspector_without_affecting_other_job_types(monkeypatch):
    from viraldy.worker.tasks import process_asset

    job = _job(job_type="smart_remake_inspect")
    events = []
    repo = SimpleNamespace(update_progress=lambda *args: events.append(args))
    session = SimpleNamespace(commit=lambda: events.append("commit"))

    def execute(job_arg, settings, ensure_active):
        assert job_arg is job
        ensure_active()
        return {"phase": "completed"}

    monkeypatch.setattr(inspection_tasks, "execute_inspection_job", execute)
    assert process_asset._execute_job(job, repo, None, session) == {"phase": "completed"}
    assert events[0][2] == "inspecting_media"
    assert events[-1] == "commit"


@pytest.mark.parametrize("mode", ["fixture", "mock"])
@pytest.mark.parametrize("phase", ["queued", "invoking", "completed", "wrong_kind"])
def test_nonlive_worker_stops_queued_operation_before_any_provider_or_media_factory(
    monkeypatch, mode, phase
):
    job = _job()
    operation = SimpleNamespace(
        status="completed" if phase == "completed" else "running",
        result_json={"kind": "repair" if phase == "wrong_kind" else "inspection", "phase": phase},
    )
    events = []

    class Context:
        async def __aenter__(self):
            return object()

        async def __aexit__(self, *args):
            events.append("session_closed")

    class Engine:
        async def dispose(self):
            events.append("disposed")

    class Repository:
        async def operation(self, workspace, project, op_id):
            assert workspace == job.workspace_id and project == job.subject_id
            assert str(op_id) == job.input_json["operation_id"]
            return operation

        async def finish(self, target, status, result):
            assert target is operation
            target.status, target.result_json = status, result
            events.append("terminal")

    monkeypatch.setattr(inspection_tasks, "create_async_engine", lambda *a, **kw: Engine())
    monkeypatch.setattr(inspection_tasks, "async_sessionmaker", lambda *a, **kw: lambda: Context())
    monkeypatch.setattr(
        inspection_tasks, "RepairRepository", lambda session: Repository(), raising=False
    )

    def never_factory(*args, **kwargs):
        pytest.fail("fixture/mock must not construct media or paid provider factories")

    monkeypatch.setattr(inspection_tasks, "_service", never_factory)
    monkeypatch.setattr(inspection_tasks, "inspection_invoke", never_factory)
    monkeypatch.setattr(inspection_tasks, "InspectionService", never_factory)
    monkeypatch.setenv("GEMINI_API_KEY", "configured-but-never-used")
    monkeypatch.setenv("SMART_REMAKE_P0_MAX_INSPECTION_USD", "1")
    settings = SimpleNamespace(database_url="postgresql+asyncpg://fixture", ai_mode=mode)
    if phase == "wrong_kind":
        with pytest.raises(AppError) as wrong:
            inspection_tasks.execute_inspection_job(job, settings, lambda: None)
        assert wrong.value.code == "SMART_REMAKE_JOB_BINDING_INVALID"
        assert operation.status == "running" and "terminal" not in events
    elif phase == "completed":
        assert (
            inspection_tasks.execute_inspection_job(job, settings, lambda: None)
            == operation.result_json
        )
        assert operation.status == "completed" and "terminal" not in events
    else:
        with pytest.raises(AppError) as blocked:
            inspection_tasks.execute_inspection_job(job, settings, lambda: None)
        assert blocked.value.code == "SMART_REMAKE_INSPECTION_NOT_LIVE"
        assert operation.status == "failed"
        assert operation.result_json["needsReconciliation"] is (phase == "invoking")
    assert events[-2:] == ["session_closed", "disposed"]
