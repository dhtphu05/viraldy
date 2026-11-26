# ruff: noqa: F811 -- pytest fixture imports are intentionally injected by name.
from __future__ import annotations

import copy
from types import SimpleNamespace
from uuid import uuid4

import pytest
from test_smart_remake_image_workflow import prepare, setup  # noqa: F401
from test_smart_remake_kie_workflow_unit import workflow  # noqa: F401

from viraldy.modules.smart_remake import budget_ledger, generation_budget
from viraldy.modules.smart_remake.generation_expectations import (
    build_generation_expectations,
    expectations_hash,
)
from viraldy.shared.errors.base import AppError


@pytest.fixture
def ledger(monkeypatch):
    calls = []
    records = {}
    created = True

    async def reserve(session, workspace, project, **kwargs):
        calls.append(("reserve", copy.deepcopy(kwargs)))
        key = kwargs["idempotency_key"]
        if key in records:
            return records[key], False
        row = SimpleNamespace(id=uuid4(), status="reserved", provider_task_id=None)
        records[key] = row
        return row, created

    async def submitted(session, workspace, project, attempt_id, **kwargs):
        calls.append(("submitted", kwargs))
        row = next(row for row in records.values() if row.id == attempt_id)
        row.status = "submitted"
        row.provider_task_id = kwargs.get("provider_task_id") or row.provider_task_id
        return row

    async def complete(session, workspace, project, attempt_id, **kwargs):
        calls.append(("complete", kwargs))
        row = next(row for row in records.values() if row.id == attempt_id)
        row.status = "completed"
        return row

    async def failed(session, workspace, project, attempt_id, **kwargs):
        calls.append(("failed", kwargs))

    async def unknown(session, workspace, project, attempt_id, **kwargs):
        calls.append(("unknown", kwargs))

    async def policy(*args):
        calls.append(("policy", {}))

    monkeypatch.setattr(budget_ledger, "reserve_attempt", reserve)
    monkeypatch.setattr(budget_ledger, "mark_submitted", submitted)
    monkeypatch.setattr(budget_ledger, "complete_attempt", complete)
    monkeypatch.setattr(budget_ledger, "fail_attempt", failed)
    monkeypatch.setattr(budget_ledger, "unknown_attempt", unknown)
    monkeypatch.setattr(generation_budget, "require_generation_policy", policy)
    # Call sites also hold an import of the policy function.
    from viraldy.modules.smart_remake import image_workflow, kie_workflow

    monkeypatch.setattr(image_workflow, "require_generation_policy", policy)
    monkeypatch.setattr(kie_workflow, "require_generation_policy", policy)
    monkeypatch.setenv("SMART_REMAKE_P0_MAX_IMAGE_USD", "0.5")
    monkeypatch.setenv("SMART_REMAKE_P0_MAX_VIDEO_USD", "1.5")
    return SimpleNamespace(calls=calls, records=records)


def enable(repair, row):
    repair.repository.session = object()
    row.context_json["p0"] = {"actorId": str(uuid4())}
    # These positive fixtures model a successful compile and the durable
    # operation snapshot committed before entering a direct _task call.
    snapshot = build_generation_expectations(row.context_json)
    digest = expectations_hash(snapshot)
    row.context_json.update(generationExpectations=snapshot, expectationsHash=digest)
    operation = getattr(repair.repository, "op", None)
    if operation is not None:
        operation.result_json.update(
            generationExpectations=copy.deepcopy(snapshot), expectationsHash=digest,
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("stage", ["image", "video"])
async def test_policy_revoked_during_submitted_commit_never_enters_provider(
    setup, workflow, ledger, monkeypatch, stage
):
    from viraldy.modules.smart_remake import budget_ledger

    revoked = False
    original = budget_ledger.mark_submitted

    async def mark(*args, **kwargs):
        nonlocal revoked
        result = await original(*args, **kwargs)
        revoked = True
        return result

    async def policy(*args):
        if revoked:
            raise AppError("SMART_REMAKE_RIGHTS_REVOKED", "Stop use was requested", 409)

    monkeypatch.setattr(budget_ledger, "mark_submitted", mark)
    monkeypatch.setattr(generation_budget, "require_generation_policy", policy)
    if stage == "image":
        repair, row, operation, client, _, _, _ = setup
        enable(repair, row)
        with pytest.raises(AppError, match="SMART_REMAKE_RIGHTS_REVOKED"):
            await prepare(setup)
        assert client.calls == []
        assert operation.result_json["images"]["0"]["status"] == "preflight_rejected"
    else:
        runner, repair, client, row, operation = workflow
        enable(repair, row)
        with pytest.raises(AppError, match="SMART_REMAKE_RIGHTS_REVOKED"):
            await runner._task(row, operation, 0, reconcile_only=False)
        assert client.submits == [] and client.polls == []
        assert operation.result_json["tasks"]["0"]["status"] == "preflight_rejected"
    failed = next(value for name, value in ledger.calls if name == "failed")
    assert failed["definitely_not_submitted"] is True
    assert failed["preflight_rejected"] is True
    assert failed["error"] == {
        "code": "SMART_REMAKE_RIGHTS_REVOKED", "phase": "preflight", "httpAttempted": False
    }
    assert "receipt" not in failed
    assert not any(name == "unknown" for name, _ in ledger.calls)


@pytest.mark.asyncio
async def test_image_reservation_is_durable_before_edit_and_cache_has_no_extra_attempt(
    setup, ledger
):
    repair, row, _, client, _, _, _ = setup
    enable(repair, row)
    original = client.edit

    async def edit(**kwargs):
        assert next(iter(ledger.records.values())).status == "submitted"
        return await original(**kwargs)

    client.edit = edit
    first = await prepare(setup)
    await prepare(setup)
    assert len(ledger.records) == 1 and len(client.calls) == 1
    assert ledger.calls[-1][0] == "policy"
    complete = next(payload for name, payload in ledger.calls if name == "complete")
    assert complete["actual_usd"] is None
    assert complete["usage"] == {"input_tokens": 30, "output_tokens": 90}
    assert first["attemptId"] == str(next(iter(ledger.records.values())).id)


@pytest.mark.asyncio
async def test_image_unknown_stays_reserved_and_never_retries(setup, ledger):
    repair, row, _, client, _, _, _ = setup
    enable(repair, row)
    client.fail = True
    for _ in range(2):
        with pytest.raises(AppError, match="OPENAI_IMAGE_SUBMISSION_UNRESOLVED"):
            await prepare(setup)
    assert len(client.calls) == len(ledger.records) == 1
    assert any(name == "unknown" for name, _ in ledger.calls)
    assert not any(name == "complete" for name, _ in ledger.calls)


@pytest.mark.asyncio
async def test_missing_server_image_cost_ceiling_never_submits(setup, ledger, monkeypatch):
    repair, row, _, client, _, _, _ = setup
    enable(repair, row)
    row.context_json["p0"]["budgetPolicy"] = {
        "capUsd": "2", "maxAttempts": 5, "maxDurationSeconds": 3600,
    }
    monkeypatch.delenv("SMART_REMAKE_P0_MAX_IMAGE_USD")
    with pytest.raises(AppError, match="SMART_REMAKE_COST_BOUND_REQUIRED"):
        await prepare(setup)
    assert not client.calls and not ledger.records


@pytest.mark.asyncio
async def test_video_receipt_settles_usage_only_as_unknown_and_preserves_task_id(workflow, ledger):
    runner, repair, client, row, operation = workflow
    enable(repair, row)
    result = await runner._task(row, operation, 0, reconcile_only=False)
    assert result["taskId"] == "paid-once"
    assert len(ledger.records) == 1
    assert ledger.calls[1][0] == "policy"
    assert len([name for name, _ in ledger.calls if name == "submitted"]) == 2
    assert next(iter(ledger.records.values())).provider_task_id == "paid-once"
    assert (
        next(payload for name, payload in ledger.calls if name == "complete")["actual_usd"] is None
    )
    await runner._task(row, operation, 0, reconcile_only=True)
    assert len(client.submits) == 1 and len(ledger.records) == 1


@pytest.mark.asyncio
async def test_ledger_replay_without_receipt_never_submits_after_lost_operation_save(
    workflow, ledger
):
    runner, repair, client, row, operation = workflow
    enable(repair, row)
    await runner._task(row, operation, 0, reconcile_only=False)
    prior = next(iter(ledger.records.values()))
    prior.provider_task_id = None
    operation.result_json = {**operation.result_json, "kind": "render", "tasks": {}}
    with pytest.raises(AppError, match="SMART_REMAKE_SUBMISSION_UNRESOLVED"):
        await runner._task(row, operation, 0, reconcile_only=False)
    assert len(client.submits) == 1


@pytest.mark.asyncio
async def test_known_ledger_receipt_recovers_without_another_video_create(workflow, ledger):
    runner, repair, client, row, operation = workflow
    enable(repair, row)
    await runner._task(row, operation, 0, reconcile_only=False)
    operation.result_json = {**operation.result_json, "kind": "render", "tasks": {}}
    await runner._task(row, operation, 0, reconcile_only=False)
    assert len(client.submits) == 1 and client.polls == ["paid-once", "paid-once"]


@pytest.mark.asyncio
async def test_live_legacy_project_fails_closed_before_provider(workflow):
    runner, repair, client, row, operation = workflow
    repair.settings = SimpleNamespace(ai_mode="live")
    with pytest.raises(AppError, match="SMART_REMAKE_INTAKE_REQUIRED"):
        await runner._task(row, operation, 0, reconcile_only=False)
    assert not client.submits


@pytest.mark.asyncio
async def test_numeric_kie_credits_are_receipts_without_invented_usd():
    import httpx

    from viraldy.modules.smart_remake.engine.kie_client import KieClient

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json={
                    "code": 200,
                    "data": {
                        "taskId": "task",
                        "state": "success",
                        "credits": 8,
                        "usage": {"input_tokens": 3, "providerText": "private"},
                        "resultJson": {"resultUrls": ["https://1.1.1.1/video.mp4"]},
                    },
                },
            )
        )
    ) as http:
        result = await KieClient(api_key="unit-only", http_client=http).get_task("task")
    assert result["receipt"] == {"credits": 8}
    assert result["usage"] == {"input_tokens": 3}
    assert "billedUsd" not in result["receipt"]


@pytest.mark.asyncio
async def test_explicit_billed_usd_is_settled_without_estimating_credit_rate(workflow, ledger):
    runner, repair, client, row, operation = workflow
    enable(repair, row)

    async def status(task_id):
        return {
            "status": "completed",
            "output": {"video_url": "https://1.1.1.1/v.mp4"},
            "receipt": {"billedUsd": "0.85", "credits": 8},
        }

    client.get_task = status
    await runner._task(row, operation, 0, reconcile_only=False)
    value = next(payload for name, payload in ledger.calls if name == "complete")
    assert value["actual_usd"] == "0.85"
    assert value["receipt"]["credits"] == 8


@pytest.mark.asyncio
async def test_remote_rejection_has_failed_attempt_and_keeps_cost_unknown(setup, ledger):
    repair, row, _, client, _, _, _ = setup
    enable(repair, row)

    async def rejected(**kwargs):
        raise AppError("OPENAI_IMAGE_RATE_LIMITED", "rate limited")

    client.edit = rejected
    with pytest.raises(AppError, match="OPENAI_IMAGE_RATE_LIMITED"):
        await prepare(setup)
    failure = next(payload for name, payload in ledger.calls if name == "failed")
    assert failure["definitely_not_submitted"] is False
    assert not any(name == "complete" for name, _ in ledger.calls)


@pytest.mark.asyncio
async def test_numeric_json_billed_usd_is_normalized_to_exact_decimal(workflow, ledger):
    runner, repair, client, row, operation = workflow
    enable(repair, row)

    async def status(task_id):
        return {
            "status": "completed",
            "output": {"video_url": "https://1.1.1.1/v.mp4"},
            "receipt": {"billedUsd": 0.85},
        }

    client.get_task = status
    await runner._task(row, operation, 0, reconcile_only=False)
    value = next(payload for name, payload in ledger.calls if name == "complete")
    assert value["actual_usd"] == "0.85"


@pytest.mark.asyncio
async def test_known_receipt_recovers_after_crash_before_submitted_operation_save(
    workflow, ledger, monkeypatch
):
    runner, repair, client, row, operation = workflow
    enable(repair, row)
    original = runner._save

    async def crash(operation, result, **kwargs):
        if result.get("tasks", {}).get("0", {}).get("status") == "submitted":
            raise RuntimeError("crash before operation write")
        await original(operation, result, **kwargs)

    async def get_attempt(session, workspace, project, attempt_id):
        return next(row for row in ledger.records.values() if row.id == attempt_id)

    monkeypatch.setattr(budget_ledger, "get_attempt", get_attempt)
    monkeypatch.setattr(runner, "_save", crash)
    with pytest.raises(RuntimeError, match="crash before operation write"):
        await runner._task(row, operation, 0, reconcile_only=False)
    assert operation.result_json["tasks"]["0"]["status"] == "submitting"
    monkeypatch.setattr(runner, "_save", original)
    result = await runner._task(row, operation, 0, reconcile_only=True)
    assert result["taskId"] == "paid-once" and len(client.submits) == 1


@pytest.mark.asyncio
async def test_policy_gate_uses_current_persisted_policy_after_preparation(workflow):
    from test_smart_remake_rights import (
        MemoryMedia,
        MemoryRepository,
        image_upload,
        intake_payload,
        source_upload,
    )

    from viraldy.modules.smart_remake.project_intake import create_intake

    runner, repair, _, row, _ = workflow
    repository, media = MemoryRepository(), MemoryMedia()
    current = await create_intake(
        repository,
        media,
        row.workspace_id,
        uuid4(),
        intake_payload(),
        source_upload(),
        image_upload(),
    )
    stale = copy.deepcopy(current)
    current.context_json = copy.deepcopy(current.context_json)
    current.context_json["p0"]["rights"]["source"]["revoked"] = True
    repair.repository = repository
    repair.media = media
    repair.settings = SimpleNamespace(ai_mode="live")
    with pytest.raises(AppError, match="SMART_REMAKE_RIGHTS_REQUIRED"):
        await generation_budget.require_generation_policy(repair, stale)


@pytest.mark.asyncio
async def test_failed_video_retains_receipt_usage_and_known_bill(workflow, ledger):
    runner, repair, client, row, operation = workflow
    enable(repair, row)

    async def status(task_id):
        return {
            "status": "failed",
            "receipt": {"billedUsd": "0.25", "credits": 2},
            "usage": {"output_tokens": 0},
        }

    client.get_task = status
    with pytest.raises(AppError, match="KIE_TASK_FAILED"):
        await runner._task(row, operation, 0, reconcile_only=False)
    failure = next(payload for name, payload in ledger.calls if name == "failed")
    assert failure["actual_usd"] == "0.25"
    assert failure["receipt"]["credits"] == 2
    assert failure["usage"] == {"output_tokens": 0}


@pytest.mark.asyncio
async def test_paid_attempt_is_attributed_to_operation_actor_instead_of_intake_actor(setup, ledger):
    repair, row, operation, _, _, _, _ = setup
    enable(repair, row)
    operator = uuid4()
    operation.result_json["actorId"] = str(operator)
    await prepare(setup)
    attempt = next(payload for name, payload in ledger.calls if name == "reserve")
    assert attempt["actor_id"] == operator
