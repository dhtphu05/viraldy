from __future__ import annotations

import copy
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from tests.unit.test_smart_remake_unlimited_ledger import stored_ledger as _stored_ledger
from viraldy.modules.smart_remake import generation_recovery as recovery
from viraldy.modules.smart_remake.analysis_progress import public_analysis_progress
from viraldy.modules.smart_remake.preflight_contracts import PreflightRequest
from viraldy.modules.smart_remake.preflight_service import calculate_preflight
from viraldy.shared.errors.base import AppError, ConflictError

stored_ledger = _stored_ledger


def returned_attempt(**changes):
    identity, project, workspace, operation = uuid4(), uuid4(), uuid4(), uuid4()
    request_hash, request_id = "a" * 64, "gemini-response-observed"
    proof = {
        "version": 1, "mode": "live", "transport": "verified_tls", "provider": "google",
        "model": "gemini-2.5-flash", "attemptId": str(identity), "requestHash": request_hash,
        "operation": "google.generate_content", "responseHash": "b" * 64,
        "observedAt": datetime.now(UTC).isoformat(), "requestId": request_id,
    }
    return SimpleNamespace(**{
        "id": identity, "project_id": project, "workspace_id": workspace,
        "request_hash": request_hash, "idempotency_key": "old-analysis", "stage": "analysis",
        "purpose": "initial", "provider": "google", "model": "gemini-2.5-flash",
        "status": "unknown", "provider_task_id": None, "actor_id": None,
        "actual_usd": None, "estimated_usd": Decimal("0.50"), "profile_json": {},
        "policy_json": {"mode": "unlimited"},
        "usage_json": {"totalTokenCount": 27801, "promptTokenCount": 11431,
                       "thoughtsTokenCount": 7859, "candidatesTokenCount": 8511},
        "receipt_json": {"requestId": request_id, "executionEvidence": proof},
        "error_json": {"code": "MODEL_ATTEMPT_UNCERTAIN", "exceptionType": "SmartRemakeError"},
        "metadata_json": {"operationId": str(operation)}, **changes,
    })


def failed_compile(attempt):
    row = SimpleNamespace(id=attempt.project_id, workspace_id=attempt.workspace_id,
                          state_json={}, context_json={"p0": {}})
    operation = SimpleNamespace(
        id=attempt.metadata_json["operationId"], project_id=row.id, status="failed",
        idempotency_key="analysis-intent", result_json={
            "kind": "compile", "errorCode": "SMART_REMAKE_MODEL_ATTEMPT_UNCERTAIN",
            "analysisProgress": {"schemaVersion": 1, "stage": "failed", "scenes": []},
        },
    )
    return row, operation


def test_observed_response_settles_control_without_claiming_a_known_bill_or_failure_cause():
    attempt = returned_attempt()
    original = copy.deepcopy(vars(attempt))
    assert recovery.is_completed_analysis_response(attempt)
    assert not recovery.attempt_needs_reconciliation(attempt)
    assert vars(attempt) == original
    assert attempt.status == "unknown" and attempt.actual_usd is None


@pytest.mark.parametrize("change", [
    {"status": "submitted"}, {"status": "reserved"}, {"stage": "video"},
    {"stage": "inspection"}, {"purpose": "repair"}, {"purpose": "loading_summary"},
    {"provider": "other"}, {"provider_task_id": "asynchronous-task"},
    {"receipt_json": {}}, {"usage_json": {}}, {"usage_json": {"totalTokenCount": 0}},
    {"usage_json": {"totalTokenCount": True}}, {"usage_json": {"totalTokenCount": -1}},
    {"usage_json": {"totalTokenCount": float("nan")}},
    {"usage_json": {"thoughtsTokenCount": 1}},
    {"error_json": {"code": "OTHER_FAILURE"}},
])
def test_unproven_transport_or_other_work_never_authorizes_new_analysis(change):
    assert not recovery.is_completed_analysis_response(returned_attempt(**change))


@pytest.mark.parametrize("field,value", [
    ("attemptId", "foreign-attempt"), ("requestHash", "c" * 64),
    ("provider", "other"), ("operation", "kie.tasks.create"),
    ("requestId", "foreign-response"), ("responseHash", "invalid"),
])
def test_borrowed_or_changed_response_evidence_never_authorizes_another_request(field, value):
    attempt = returned_attempt()
    attempt.receipt_json["executionEvidence"][field] = value
    assert not recovery.is_completed_analysis_response(attempt)


def test_receipt_requires_the_same_safe_provider_response_id_and_meaningful_integer_usage():
    attempt = returned_attempt()
    attempt.receipt_json.pop("requestId")
    assert not recovery.is_completed_analysis_response(attempt)
    attempt = returned_attempt(usage_json={"promptTokenCount": 10})
    assert recovery.is_completed_analysis_response(attempt)
    attempt.usage_json["candidatesTokenCount"] = "private"
    assert not recovery.is_completed_analysis_response(attempt)


def test_failed_compile_can_offer_only_explicit_new_analysis_from_owned_terminal_response():
    attempt = returned_attempt()
    row, operation = failed_compile(attempt)
    assert recovery.analysis_retry_disposition(
        row, operation, [attempt], workspace_id=row.workspace_id,
    ) == "new_analysis"
    assert public_analysis_progress(operation, retry_disposition="new_analysis")[
        "retryDisposition"
    ] == "new_analysis"
    assert public_analysis_progress(operation)["retryDisposition"] == "reconcile"
    operation.result_json["analysisProgress"]["retryDisposition"] = "new_analysis"
    assert public_analysis_progress(operation)["retryDisposition"] == "reconcile"


@pytest.mark.parametrize("condition", [
    "foreign_project", "foreign_workspace", "foreign_attempt_project", "foreign_attempt_workspace",
    "foreign_operation", "running", "completed", "render", "pending", "no_attempts", "timeout",
    "unrelated_unknown",
])
def test_retry_disposition_refuses_unowned_unfinished_or_unproven_compile(condition):
    attempt = returned_attempt()
    row, operation = failed_compile(attempt)
    attempts, workspace = [attempt], row.workspace_id
    if condition == "foreign_project":
        operation.project_id = uuid4()
    elif condition == "foreign_workspace":
        workspace = uuid4()
    elif condition == "foreign_attempt_project":
        attempt.project_id = uuid4()
    elif condition == "foreign_attempt_workspace":
        attempt.workspace_id = uuid4()
    elif condition == "foreign_operation":
        attempt.metadata_json["operationId"] = str(uuid4())
    elif condition in {"running", "completed"}:
        operation.status = condition
    elif condition == "render":
        operation.result_json["kind"] = "render"
    elif condition == "pending":
        operation.result_json["needsReconciliation"] = True
    elif condition == "no_attempts":
        attempts = []
    elif condition == "timeout":
        attempt.receipt_json, attempt.usage_json = {}, {}
    elif condition == "unrelated_unknown":
        attempts.append(returned_attempt(project_id=row.id, workspace_id=workspace,
                                         receipt_json={}, usage_json={}))
    assert recovery.analysis_retry_disposition(
        row, operation, attempts, workspace_id=workspace,
    ) == "reconcile"


def test_retired_conditioning_marker_does_not_block_a_known_returned_analysis():
    attempt = returned_attempt()
    row, operation = failed_compile(attempt)
    row.context_json["p0"]["conditioningChecks"] = {"check": {"phase": "unknown"}}
    assert recovery.analysis_retry_disposition(
        row, operation, [attempt], workspace_id=row.workspace_id,
    ) == "new_analysis"
    assert row.context_json["p0"]["conditioningChecks"]["check"]["phase"] == "unknown"


def test_optional_summary_timeout_does_not_erase_its_unknown_cost_or_block_new_analysis():
    attempt = returned_attempt()
    row, operation = failed_compile(attempt)
    summary = returned_attempt(project_id=row.id, workspace_id=row.workspace_id,
                               purpose="loading_summary", receipt_json={}, usage_json={})
    assert recovery.analysis_retry_disposition(
        row, operation, [attempt, summary], workspace_id=row.workspace_id,
    ) == "new_analysis"
    assert summary.actual_usd is None and summary.status == "unknown"


def test_preflight_uses_observed_response_without_releasing_unknown_cost_exposure():
    attempt = returned_attempt()
    row, operation = failed_compile(attempt)
    row.revision = 4
    row.state_json = {"revision": 4, "targetDuration": 16}
    request = PreflightRequest(action="reanalyze", projectId=str(row.id), expectedRevision=4,
                               targetDuration=16, budgetMode="unlimited")
    result = calculate_preflight(request, mode="live", bounds={}, row=row,
                                 attempts=[attempt], operations=[operation])
    assert not any(block.action == "reconcile" for block in result.blockers)
    assert result.budget.reservedUsd == "0.50"
    assert result.budget.exposureUsd == "0.50"
    assert attempt.actual_usd is None


@pytest.mark.asyncio
async def test_fresh_analysis_key_can_reserve_but_old_key_never_becomes_a_fresh_submission(
    stored_ledger,
):
    from viraldy.modules.smart_remake import budget_ledger as ledger

    stored = stored_ledger
    old = returned_attempt(project_id=stored.project.id, workspace_id=stored.workspace)
    stored.rows.append(old)
    args = {"request_hash": old.request_hash, "stage": old.stage, "reservation_usd": "0.50",
            "actor_id": None, "provider": old.provider, "model": old.model,
            "profile": {}, "metadata": old.metadata_json}
    replay, created = await ledger.reserve_attempt(
        stored.session, stored.workspace, stored.project.id,
        idempotency_key=old.idempotency_key, **args,
    )
    assert replay is old and not created
    fresh, created = await ledger.reserve_attempt(
        stored.session, stored.workspace, stored.project.id,
        idempotency_key="explicit-new-analysis", **args,
    )
    assert created and fresh.id != old.id
    assert old.status == "unknown" and old.actual_usd is None
    assert ledger._exposure(stored.rows) == Decimal("1.00")
    with pytest.raises(ConflictError):
        await ledger.reserve_attempt(
            stored.session, stored.workspace, stored.project.id,
            idempotency_key="third-with-unresolved-new-attempt", **args,
        )


@pytest.mark.asyncio
async def test_observed_response_does_not_make_old_ledger_client_replay_call_provider(
    stored_ledger, monkeypatch,
):
    from viraldy.modules.smart_remake.budgeted_analysis import LedgerGeminiClient
    from viraldy.modules.smart_remake.engine.errors import SmartRemakeError
    from viraldy.shared.errors.base import AppError

    stored, calls = stored_ledger, []

    class Client:
        last_usage = {"totalTokenCount": 20}
        last_request_id = "returned-invalid-json"

        async def generate_json(self, **kwargs):
            calls.append(kwargs)
            raise SmartRemakeError("Invalid JSON", "SMART_REMAKE_GEMINI_ERROR")

    client = LedgerGeminiClient(
        stored.session, stored.workspace, stored.project.id, uuid4(), None, client=Client(),
    )
    monkeypatch.setattr(client, "_project", AsyncMock(return_value=stored.project))
    monkeypatch.setattr(client, "_preflight", AsyncMock(return_value=stored.project))
    with pytest.raises(AppError):
        await client.generate_json(system_instruction="system", prompt="observe")
    attempt = stored.rows[0]
    proof = returned_attempt().receipt_json["executionEvidence"]
    attempt.receipt_json["executionEvidence"] = {
        **proof, "attemptId": str(attempt.id), "requestHash": attempt.request_hash,
        "model": attempt.model, "requestId": attempt.receipt_json["requestId"],
    }
    assert recovery.is_completed_analysis_response(attempt)
    with pytest.raises(ConflictError) as replay:
        await client.generate_json(system_instruction="system", prompt="observe")
    assert replay.value.code == "SMART_REMAKE_ATTEMPT_RECONCILIATION_REQUIRED"
    assert len(calls) == len(stored.rows) == 1


@pytest.mark.asyncio
async def test_project_get_exposes_retry_disposition_from_owned_rows_without_writes_or_provider():
    from viraldy.modules.smart_remake.repair_service import RepairService

    attempt = returned_attempt()
    row, operation = failed_compile(attempt)
    session = SimpleNamespace(scalars=AsyncMock(return_value=[attempt]), commit=AsyncMock())
    repository = SimpleNamespace(
        project=AsyncMock(return_value=row), running=AsyncMock(return_value=None),
        latest_operation=AsyncMock(return_value=operation), session=session,
    )
    service = RepairService(repository, object(), row.workspace_id)
    service.present = AsyncMock(return_value={"id": str(row.id)})
    result = await service.get(row.id)
    assert result["analysisProgress"]["retryDisposition"] == "new_analysis"
    assert session.scalars.await_count == 1
    session.commit.assert_not_awaited()
    assert "executionEvidence" not in str(result)
    assert attempt.status == "unknown" and attempt.actual_usd is None


@pytest.mark.asyncio
async def test_fresh_compile_rejects_prior_timeout_even_when_new_profile_changes_request_hash(
    monkeypatch,
):
    from tests.unit.test_smart_remake_lifecycle_compile import compile_arguments, owned_compile
    from viraldy.modules.smart_remake import loading_summary, timeline_compile

    row, _, repository = owned_compile(monkeypatch)
    arguments = compile_arguments()
    attempt = returned_attempt(
        project_id=row.id, workspace_id=arguments["workspace_id"], receipt_json={}, usage_json={},
        profile_json={"thinkingBudget": 8192},
    )
    arguments["session"].scalars = AsyncMock(return_value=[attempt])
    paid = AsyncMock(side_effect=AssertionError("No new analysis after a true timeout"))
    summary = AsyncMock(side_effect=AssertionError("No optional summary after a true timeout"))
    monkeypatch.setattr(timeline_compile, "analyze_reference_video", paid)
    monkeypatch.setattr(loading_summary, "start_loading_summary", summary)
    with pytest.raises(AppError) as blocked:
        await timeline_compile.compile_timeline_request(**arguments, analysis_scope="full_source")
    assert blocked.value.code == "SMART_REMAKE_ATTEMPT_RECONCILIATION_REQUIRED"
    paid.assert_not_awaited()
    summary.assert_not_called()
    assert repository.finish.await_args.args[1] == "failed"
    query = arguments["session"].scalars.await_args.args[0]
    assert {row.id, arguments["workspace_id"]} <= set(query.compile().params.values())
    assert attempt.actual_usd is None and attempt.status == "unknown"


@pytest.mark.asyncio
async def test_fresh_compile_allows_observed_response_and_optional_timeout_before_new_analysis(
    monkeypatch,
):
    from tests.unit.test_smart_remake_lifecycle_compile import compile_arguments, owned_compile
    from viraldy.modules.smart_remake import timeline_compile

    row, _, _ = owned_compile(monkeypatch)
    arguments = compile_arguments()
    attempt = returned_attempt(project_id=row.id, workspace_id=arguments["workspace_id"])
    preview = returned_attempt(project_id=row.id, workspace_id=arguments["workspace_id"],
                               purpose="loading_summary", receipt_json={}, usage_json={})
    arguments["session"].scalars = AsyncMock(return_value=[attempt, preview])
    monkeypatch.setattr(timeline_compile, "probe_media_bytes", lambda _: {
        "hasVideo": True, "durationSeconds": 8,
    })
    monkeypatch.setattr(timeline_compile, "measure_video_frames", lambda _: 192)
    monkeypatch.setattr(timeline_compile, "extract_source_excerpt", lambda source, **_: source)
    paid = AsyncMock(side_effect=AppError("OFFLINE_ANALYSIS_REACHED", "Stop before provider"))
    monkeypatch.setattr(timeline_compile, "analyze_reference_video", paid)
    with pytest.raises(AppError) as stopped:
        await timeline_compile.compile_timeline_request(**arguments)
    assert stopped.value.code == "OFFLINE_ANALYSIS_REACHED"
    paid.assert_awaited_once()
    assert paid.await_args.kwargs["gemini"].client.thinking_budget == 1024


@pytest.mark.asyncio
@pytest.mark.parametrize("phase", ["invoking", "unknown"])
async def test_fresh_compile_ignores_removed_conditioning_markers_without_repeating_image_qc(
    monkeypatch, phase,
):
    from tests.unit.test_smart_remake_lifecycle_compile import compile_arguments, owned_compile
    from viraldy.modules.smart_remake import timeline_compile

    row, _, _ = owned_compile(monkeypatch)
    row.context_json["p0"]["conditioningChecks"] = {"prior-check": {"phase": phase}}
    monkeypatch.setattr(timeline_compile, "probe_media_bytes", lambda _: {
        "hasVideo": True, "durationSeconds": 8,
    })
    monkeypatch.setattr(timeline_compile, "measure_video_frames", lambda _: 192)
    monkeypatch.setattr(timeline_compile, "extract_source_excerpt", lambda source, **_: source)
    paid = AsyncMock(side_effect=AppError("OFFLINE_ANALYSIS_REACHED", "Stop before provider"))
    monkeypatch.setattr(timeline_compile, "analyze_reference_video", paid)
    with pytest.raises(AppError) as stopped:
        await timeline_compile.compile_timeline_request(**compile_arguments())
    assert stopped.value.code == "OFFLINE_ANALYSIS_REACHED"
    paid.assert_awaited_once()
    assert row.context_json["p0"]["conditioningChecks"]["prior-check"]["phase"] == phase


@pytest.mark.asyncio
async def test_old_compile_key_replay_skips_new_attempt_guard_and_never_calls_ai(monkeypatch):
    from tests.unit.test_smart_remake_lifecycle_compile import compile_arguments, owned_compile
    from viraldy.modules.smart_remake import timeline_compile

    _, operation, _ = owned_compile(monkeypatch, fresh=False, status="completed")
    operation.result_json = {"compileResult": {"sourceSceneMap": {"scenes": []}}}
    arguments = compile_arguments()
    arguments["session"].scalars = AsyncMock(side_effect=AssertionError("Replay is read-only"))
    paid = AsyncMock(side_effect=AssertionError("No AI on replay"))
    monkeypatch.setattr(timeline_compile, "analyze_reference_video", paid)
    assert await timeline_compile.compile_timeline_request(**arguments) == {
        "sourceSceneMap": {"scenes": []},
    }
    arguments["session"].scalars.assert_not_awaited()
    paid.assert_not_awaited()
