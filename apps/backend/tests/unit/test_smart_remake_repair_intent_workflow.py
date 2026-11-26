from __future__ import annotations

import copy

import pytest

from tests.unit import test_smart_remake_grouped_workflow as grouped_module
from viraldy.modules.smart_remake import repair_intent_workflow
from viraldy.shared.errors.base import AppError

grouped = grouped_module.grouped


def setup_repair(value):
    scene = value.row.state_json["scenes"][1]
    snapshot = copy.deepcopy(value.row.context_json["generationExpectations"])
    scene["activeVersionId"] = "base"
    scene["versions"] = [
        {
            "id": "base",
            "generationExpectations": snapshot,
            "expectationsHash": value.row.context_json["expectationsHash"],
        }
    ]
    value.op.result_json = {
        "kind": "repair",
        "sceneIndex": 1,
        "sceneId": scene["id"],
        "tasks": {},
        "request": {
            "baseVersionId": "base",
            "repairIntent": {
                "schemaVersion": 1,
                "issues": ["action"],
                "instruction": "Pour slowly",
            },
        },
    }
    return scene


@pytest.mark.asyncio
async def test_read_only_repair_reconciliation_does_not_begin_normalization(grouped, monkeypatch):
    value = grouped
    setup_repair(value)
    called = []

    async def resolver(*args, **kwargs):
        called.append(kwargs["reconcile_only"])
        return not kwargs["reconcile_only"]

    monkeypatch.setattr(repair_intent_workflow, "resolve_repair_intent", resolver)
    result = await value.runner.execute(value.row.id, value.op.id, reconcile_only=True)
    assert result["status"] == "running"
    assert called == [True]
    assert not value.images and not value.client.submits


@pytest.mark.asyncio
async def test_uncertain_repair_analysis_remains_running_before_image_video(grouped, monkeypatch):
    value = grouped
    setup_repair(value)

    async def uncertain(*args, **kwargs):
        raise AppError("SMART_REMAKE_MODEL_ATTEMPT_UNCERTAIN", "No replacement attempt.", 409)

    monkeypatch.setattr(repair_intent_workflow, "resolve_repair_intent", uncertain)
    with pytest.raises(AppError, match="SMART_REMAKE_MODEL_ATTEMPT_UNCERTAIN"):
        await value.runner.execute(value.row.id, value.op.id)
    assert value.op.status == "running"
    assert value.op.result_json["needsReconciliation"] is True
    assert not value.images and not value.client.submits


@pytest.mark.asyncio
async def test_repair_conflict_is_terminal_before_any_image_video(grouped, monkeypatch):
    value = grouped
    setup_repair(value)

    async def rejected(*args, **kwargs):
        raise AppError("SMART_REMAKE_REPAIR_INTENT_REJECTED", "Keep the product.", 409)

    monkeypatch.setattr(repair_intent_workflow, "resolve_repair_intent", rejected)
    with pytest.raises(AppError, match="SMART_REMAKE_REPAIR_INTENT_REJECTED"):
        await value.runner.execute(value.row.id, value.op.id)
    assert value.op.status == "failed"
    assert value.op.result_json["needsReconciliation"] is False
    assert not value.images and not value.client.submits


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["accepted", "conflict", "insufficient_evidence", "invalid"])
async def test_resolver_one_call_durable_outcome_and_replay(grouped, monkeypatch, status):
    import json

    value = grouped
    setup_repair(value)
    calls = []
    value.repair.repository.session = object()

    async def evidence(*args):
        return [{"bytes": b"owned", "mime_type": "image/png"}], {"versionId": "base"}

    class Ledger:
        def __init__(self, *args, **kwargs):
            assert kwargs["purpose"] == "repair" and kwargs["stage"] == "analysis"

        async def generate_json(self, **kwargs):
            calls.append(kwargs)
            scene = json.loads(kwargs["prompt"])["scene"]
            if status == "invalid":
                return {"bad": True}
            if status != "accepted":
                return {"status": status, "reason": "Keep the product and opening."}
            return {
                "status": "accepted",
                "reason": "Compatible",
                "scenePatch": {
                    "prompt": "New direction",
                    "imagePrompt": "New opening presentation",
                    "videoPrompt": "New slower movement",
                    "shots": [
                        {"shotIndex": index, "action": "move slowly"}
                        for index, _ in enumerate((scene.get("shotPlan") or {}).get("shots", []))
                    ],
                },
            }

    monkeypatch.setattr(repair_intent_workflow, "repair_evidence", evidence)
    monkeypatch.setattr(repair_intent_workflow, "LedgerGeminiClient", Ledger)
    if status == "accepted":
        assert await repair_intent_workflow.resolve_repair_intent(
            value.repair, value.row, value.op, save=value.runner._save
        )
        assert value.op.result_json["compiledScene"]["videoPrompt"] == "New slower movement"
    else:
        with pytest.raises(AppError, match="SMART_REMAKE_REPAIR_INTENT_"):
            await repair_intent_workflow.resolve_repair_intent(
                value.repair, value.row, value.op, save=value.runner._save
            )
        assert "compiledScene" not in value.op.result_json
    assert len(calls) == 1
    assert value.op.result_json["repairNormalization"]["phase"] == "resolved"
    if status == "accepted":
        assert await repair_intent_workflow.resolve_repair_intent(
            value.repair, value.row, value.op, save=value.runner._save
        )
    else:
        with pytest.raises(AppError, match="SMART_REMAKE_REPAIR_INTENT_"):
            await repair_intent_workflow.resolve_repair_intent(
                value.repair, value.row, value.op, save=value.runner._save
            )
    assert len(calls) == 1
    assert value.op.result_json["request"]["repairIntent"]["instruction"] == "Pour slowly"


@pytest.mark.asyncio
async def test_resolver_does_not_start_ledger_during_read_only_refresh(grouped, monkeypatch):
    value = grouped
    setup_repair(value)
    monkeypatch.setattr(
        repair_intent_workflow, "repair_evidence", lambda *args: pytest.fail("read")
    )
    assert not await repair_intent_workflow.resolve_repair_intent(
        value.repair, value.row, value.op, save=value.runner._save, reconcile_only=True
    )


@pytest.mark.asyncio
async def test_changed_repair_inputs_stop_before_analysis(grouped, monkeypatch):
    value = grouped
    setup_repair(value)
    value.op.result_json["repairNormalization"] = {"phase": "invoking", "inputHash": "old"}

    async def evidence(*args):
        return [], {"versionId": "base"}

    monkeypatch.setattr(repair_intent_workflow, "repair_evidence", evidence)
    with pytest.raises(AppError, match="SMART_REMAKE_INPUT_CHANGED"):
        await repair_intent_workflow.resolve_repair_intent(
            value.repair, value.row, value.op, save=value.runner._save
        )


@pytest.mark.asyncio
async def test_rejected_enqueue_retains_exact_request_binding_for_receipt(grouped, monkeypatch):
    from uuid import UUID

    from viraldy.modules.smart_remake import kie_workflow, service
    from viraldy.modules.smart_remake.repair_schemas import RepairSceneRequest

    value = grouped
    scene = setup_repair(value)
    value.row.state_json["revision"] = 4
    value.row.context_json["renderPlan"].pop("imageModel")
    request = RepairSceneRequest(
        expectedRevision=3,
        baseVersionId=None,
        repairIntent={"instruction": "slowly"},
        idempotencyKey="exact-failed-request",
    )

    async def start(*args):
        return value.row, value.op, True

    value.repair.repository.start = start
    monkeypatch.setattr(kie_workflow, "_service", lambda *args: value.repair)
    monkeypatch.setattr(service, "require_kie_renderer", lambda settings: None)
    with pytest.raises(AppError, match="SMART_REMAKE_REVISION_CONFLICT"):
        await kie_workflow.enqueue_kie_repair(
            None,
            value.repair.settings,
            value.row.workspace_id,
            value.row.id,
            UUID(scene["id"]),
            request,
        )
    assert value.op.status == "failed"
    assert value.op.result_json["sceneId"] == scene["id"]
    assert value.op.result_json["request"] == request.model_dump(
        mode="json", exclude={"idempotencyKey"}
    )
    assert value.op.result_json["needsReconciliation"] is False


@pytest.mark.parametrize("phase,expected", [("invoking", "running"), ("prepared", "failed")])
def test_worker_configuration_failure_preserves_uncertain_analysis(monkeypatch, phase, expected):
    from contextlib import asynccontextmanager
    from types import SimpleNamespace
    from uuid import uuid4

    from viraldy.modules.smart_remake import kie_worker, service

    project_id, operation_id, workspace_id = uuid4(), uuid4(), uuid4()
    operation = SimpleNamespace(
        status="running",
        result_json={
            "kind": "repair",
            "repairNormalization": {"phase": phase},
            "tasks": {},
        },
    )

    class Repository:
        @asynccontextmanager
        async def execution_guard(self, *args):
            yield True

        async def operation(self, *args):
            return operation

        async def finish(self, op, status, result):
            op.status, op.result_json = status, result

    @asynccontextmanager
    async def session():
        yield object()

    async def dispose():
        return None

    def unavailable(settings):
        raise AppError("KIE_NOT_CONFIGURED", "Configure provider", 503)

    monkeypatch.setattr(service, "require_kie_renderer", unavailable)
    monkeypatch.setattr(
        kie_worker, "create_async_engine", lambda *args, **kwargs: SimpleNamespace(dispose=dispose)
    )
    monkeypatch.setattr(kie_worker, "async_sessionmaker", lambda *args, **kwargs: session)
    monkeypatch.setattr(kie_worker, "RepairRepository", lambda session: Repository())
    job = SimpleNamespace(
        subject_id=project_id,
        workspace_id=workspace_id,
        input_json={"project_id": str(project_id), "operation_id": str(operation_id)},
    )
    with pytest.raises(AppError, match="KIE_NOT_CONFIGURED"):
        kie_worker.execute_kie_job(job, SimpleNamespace(database_url="unused"), lambda: None)
    assert operation.status == expected
    assert operation.result_json["needsReconciliation"] is (expected == "running")
