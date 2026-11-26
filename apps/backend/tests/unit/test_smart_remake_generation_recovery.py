from __future__ import annotations

import copy
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest

from tests.smart_remake_expectations import install_expectations
from viraldy.modules.smart_remake.generation_recovery import (
    image_rejection_details,
    initial_render_recovery,
    is_known_image_rejection,
)


def rejected_attempt(**changes):
    identity, operation_id = uuid4(), uuid4()
    request_hash = "a" * 64
    proof = {
        "version": 1, "mode": "live", "transport": "verified_tls", "provider": "openai",
        "model": "gpt-image-2.6-sunburst", "attemptId": str(identity),
        "requestHash": request_hash, "operation": "openai.images.edit",
        "responseHash": "b" * 64, "observedAt": datetime.now(UTC).isoformat(),
    }
    receipt = {"errorCode": "OPENAI_IMAGE_RATE_LIMITED", "executionEvidence": proof}
    return SimpleNamespace(**{
        "id": identity, "request_hash": request_hash, "stage": "image", "purpose": "initial",
        "provider": "openai", "model": "gpt-image-2.6-sunburst", "status": "failed",
        "provider_task_id": None, "actual_usd": None, "estimated_usd": Decimal("2"),
        "usage_json": {}, "receipt_json": receipt, "error_json": copy.deepcopy(receipt),
        "metadata_json": {"operationId": str(operation_id)}, **changes,
    })


def recovery_project(attempt):
    state = {"revision": 3, "provider": "kie", "targetDuration": 16, "scenes": [
        {"id": "unit", "index": 0, "activeVersionId": None, "versions": []},
    ]}
    context = {
        "sourceKey": "source", "productKey": "product", "productMimeType": "image/png",
        "renderPlan": {"units": [{
            "id": "unit", "sourceSceneId": "source-scene", "sceneIndex": 0,
            "targetDurationFrames": 192, "rawDurationFrames": 192,
        }]},
    }
    install_expectations(context, state=state)
    row = SimpleNamespace(id=uuid4(), workspace_id=uuid4(), state_json=state, context_json=context)
    operation = SimpleNamespace(
        id=attempt.metadata_json["operationId"], project_id=row.id,
        idempotency_key="render-original", status="failed", result_json={
            "kind": "render", "needsReconciliation": False,
            "errorCode": "OPENAI_IMAGE_RATE_LIMITED", "tasks": {},
            "images": {"0": {"status": "submitting", "attemptId": str(attempt.id),
                              "requestHash": attempt.request_hash}},
            "generationExpectations": copy.deepcopy(context["generationExpectations"]),
            "expectationsHash": context["expectationsHash"],
        },
    )
    attempt.project_id, attempt.workspace_id = row.id, row.workspace_id
    return row, operation


def test_legacy_verified_rejection_is_terminal_without_asserting_zero_cost():
    attempt = rejected_attempt()
    assert is_known_image_rejection(attempt)
    assert attempt.actual_usd is None and attempt.estimated_usd == 2


@pytest.mark.parametrize("change", [
    {"status": "unknown"}, {"status": "submitted"}, {"provider_task_id": "paid-task"},
    {"usage_json": {"tokens": 20}}, {"receipt_json": {}}, {"stage": "video"},
    {"provider": "other"}, {"error_json": {"errorCode": "OPENAI_IMAGE_SUBMISSION_UNRESOLVED"}},
])
def test_only_verified_known_rejections_can_release_control_gate(change):
    assert not is_known_image_rejection(rejected_attempt(**change))


def test_tampered_execution_binding_and_unknown_error_remain_fenced():
    attempt = rejected_attempt()
    attempt.receipt_json["executionEvidence"]["attemptId"] = str(uuid4())
    assert not is_known_image_rejection(attempt)


@pytest.mark.parametrize("field,value", [
    ("operation", "google.generate_content"), ("provider", "google"),
    ("requestHash", "c" * 64), ("model", "other"),
])
def test_borrowed_execution_witness_cannot_authorize_retry(field, value):
    attempt = rejected_attempt()
    attempt.receipt_json["executionEvidence"][field] = value
    assert not is_known_image_rejection(attempt)
    attempt = rejected_attempt()
    attempt.receipt_json["errorCode"] = "OPENAI_IMAGE_SUBMISSION_UNRESOLVED"
    assert not is_known_image_rejection(attempt)


def test_initial_recovery_uses_old_key_and_sanitized_optional_metadata():
    attempt = rejected_attempt()
    attempt.receipt_json.update(
        requestOutcome="rejected", httpStatus=429, providerErrorCode="rate_limit_exceeded",
        retryAfterSeconds=12, message="secret", url="https://private.example",
    )
    row, operation = recovery_project(attempt)
    assert initial_render_recovery(row, operation, [attempt]) == {
        "kind": "retry_initial_render", "stage": "image", "requestKey": "render-original",
        "errorCode": "OPENAI_IMAGE_RATE_LIMITED", "httpStatus": 429,
        "providerErrorCode": "rate_limit_exceeded", "retryAfterSeconds": 12,
    }


def test_legacy_recovery_does_not_invent_provider_status_or_quota_reason():
    attempt = rejected_attempt()
    row, operation = recovery_project(attempt)
    assert initial_render_recovery(row, operation, [attempt]) == {
        "kind": "retry_initial_render", "stage": "image", "requestKey": "render-original",
        "errorCode": "OPENAI_IMAGE_RATE_LIMITED",
    }


@pytest.mark.parametrize("stage,purpose,allowed", [
    ("image", "initial", False), ("analysis", "initial", False),
    ("analysis", "loading_summary", True),
])
def test_recovery_never_promises_retry_while_other_mandatory_receipt_is_unknown(
    stage, purpose, allowed,
):
    attempt = rejected_attempt()
    row, operation = recovery_project(attempt)
    unresolved = rejected_attempt(stage=stage, purpose=purpose, status="unknown")
    recovery = initial_render_recovery(row, operation, [attempt, unresolved])
    assert (recovery is not None) is allowed


@pytest.mark.parametrize("value", [None, {}, {"requestOutcome": "rejected", "httpStatus": 500}])
def test_rejection_details_ignore_unproven_or_wrong_status(value):
    assert image_rejection_details(value) == {}


def test_rejection_details_only_keep_allowlisted_bounded_data():
    assert image_rejection_details({
        "requestOutcome": "rejected", "httpStatus": 429, "providerErrorCode": {"private": "data"},
        "providerErrorType": "rate_limit_error", "classification": [], "retryAfterSeconds": -1,
        "message": "private message", "url": "https://private.example",
    }) == {"requestOutcome": "rejected", "httpStatus": 429, "providerErrorType": "rate_limit_error"}
    assert image_rejection_details({
        "requestOutcome": "rejected", "httpStatus": 429, "providerErrorCode": "slow_down",
        "classification": "rate_limit", "retryAfterSeconds": 2,
    })["retryAfterSeconds"] == 2


@pytest.mark.parametrize("condition", [
    "active_clip", "running", "reconciliation", "repair", "task", "video_attempt",
    "invalid_expectations", "changed_expectations", "foreign_attempt", "foreign_operation",
    "missing_image_binding", "unknown_rejection", "unsafe_metadata",
])
def test_recovery_requires_exact_owned_initial_failure_without_submitted_video(condition):
    attempt = rejected_attempt()
    row, operation = recovery_project(attempt)
    attempts = [attempt]
    if condition == "active_clip":
        row.state_json["scenes"][0]["versions"] = [{"id": "existing"}]
    elif condition == "running":
        operation.status = "running"
    elif condition == "reconciliation":
        operation.result_json["needsReconciliation"] = True
    elif condition == "repair":
        operation.result_json["kind"] = "repair"
    elif condition == "task":
        operation.result_json["tasks"] = {"g": {"taskId": "remote"}}
    elif condition == "video_attempt":
        attempts.append(rejected_attempt(stage="video"))
    elif condition == "invalid_expectations":
        row.context_json.pop("generationExpectations")
    elif condition == "changed_expectations":
        operation.result_json["expectationsHash"] = "c" * 64
    elif condition == "foreign_attempt":
        attempt.workspace_id = uuid4()
    elif condition == "foreign_operation":
        operation.project_id = uuid4()
    elif condition == "missing_image_binding":
        operation.result_json["images"] = {}
    elif condition == "unknown_rejection":
        attempt.status = "unknown"
    else:
        attempt.receipt_json.update(
            httpStatus=500, providerErrorCode="untrusted", retryAfterSeconds=-1,
        )
    assert initial_render_recovery(row, operation, attempts) is None


async def test_project_get_reads_only_its_owned_attempts_and_presents_recovery():
    from unittest.mock import AsyncMock

    from viraldy.modules.smart_remake.repair_service import RepairService

    attempt = rejected_attempt()
    row, operation = recovery_project(attempt)
    session = SimpleNamespace(scalars=AsyncMock(return_value=[attempt]))
    repository = SimpleNamespace(
        project=AsyncMock(return_value=row), running=AsyncMock(return_value=None),
        latest_operation=AsyncMock(return_value=operation), session=session,
    )
    service = RepairService(repository, object(), row.workspace_id)
    service.present = AsyncMock(return_value={"id": str(row.id)})
    result = await service.get(row.id)
    assert result["generationRecovery"]["requestKey"] == "render-original"
    assert result["lastOperation"]["needsReconciliation"] is False
    query = session.scalars.call_args.args[0]
    params = query.compile().params
    assert row.id in params.values() and row.workspace_id in params.values()
    assert attempt.actual_usd is None


async def test_project_get_never_offers_initial_retry_while_any_operation_runs():
    from unittest.mock import AsyncMock

    from viraldy.modules.smart_remake.repair_service import RepairService

    attempt = rejected_attempt()
    row, _ = recovery_project(attempt)
    operation = SimpleNamespace(id=uuid4(), status="running", result_json={"kind": "compile"})
    session = SimpleNamespace(scalars=AsyncMock(side_effect=AssertionError("No recovery query")))
    repository = SimpleNamespace(
        project=AsyncMock(return_value=row), running=AsyncMock(return_value=operation),
        latest_operation=AsyncMock(side_effect=AssertionError("No latest lookup")), session=session,
    )
    service = RepairService(repository, object(), row.workspace_id)
    service.present = AsyncMock(return_value={"id": str(row.id)})
    assert "generationRecovery" not in await service.get(row.id)


@pytest.mark.parametrize("structured", [False, True])
async def test_fresh_repair_without_clip_stops_before_job_for_both_request_contracts(
    monkeypatch, structured,
):
    from unittest.mock import AsyncMock, Mock
    from uuid import UUID

    from viraldy.modules.smart_remake import kie_workflow, service
    from viraldy.modules.smart_remake.repair_schemas import RepairSceneRequest
    from viraldy.shared.errors.base import AppError

    scene_id = str(uuid4())
    row = SimpleNamespace(id=uuid4(), workspace_id=uuid4(),
                          state_json={"revision": 2, "scenes": [
                              {"id": scene_id, "activeVersionId": None, "versions": []},
                          ]}, context_json={})
    operation = SimpleNamespace(id=uuid4(), status="running", result_json={})
    repository = SimpleNamespace(start=AsyncMock(return_value=(row, operation, True)),
                                 finish=AsyncMock())
    repair = SimpleNamespace(repository=repository)
    monkeypatch.setattr(kie_workflow, "_service", lambda *args: repair)
    monkeypatch.setattr(service, "require_kie_renderer", lambda *args: None)
    jobs = Mock(side_effect=AssertionError("No job without a base video"))
    monkeypatch.setattr(kie_workflow, "JobService", jobs)
    fields = ({"repairIntent": {"instruction": "Show another take"}} if structured else
              {"prompt": "p", "imagePrompt": "i", "videoPrompt": "v"})
    request = RepairSceneRequest(expectedRevision=2, idempotencyKey="fresh", **fields)
    with pytest.raises(AppError) as blocked:
        await kie_workflow.enqueue_kie_repair(
            object(), object(), row.workspace_id, row.id, UUID(scene_id), request,
        )
    assert blocked.value.code == "SMART_REMAKE_BASE_VERSION_REQUIRED"
    assert repository.finish.call_args.args[1] == "failed"
    jobs.assert_not_called()


async def test_terminal_legacy_repair_replay_returns_old_result_before_new_guards_or_job(
    monkeypatch,
):
    from unittest.mock import AsyncMock, Mock

    from viraldy.modules.smart_remake import kie_workflow, service
    from viraldy.modules.smart_remake.repair_schemas import RepairSceneRequest

    row = SimpleNamespace(id=uuid4(), workspace_id=uuid4(), state_json={}, context_json={})
    operation = SimpleNamespace(id=uuid4(), status="failed", result_json={"kind": "repair"})
    repository = SimpleNamespace(start=AsyncMock(return_value=(row, operation, False)))
    repair = SimpleNamespace(repository=repository,
                             _operation_result=AsyncMock(return_value={"status": "failed"}))
    monkeypatch.setattr(kie_workflow, "_service", lambda *args: repair)
    monkeypatch.setattr(service, "require_kie_renderer", lambda *args: None)
    jobs = Mock(side_effect=AssertionError("Replay does not enqueue work"))
    monkeypatch.setattr(kie_workflow, "JobService", jobs)
    request = RepairSceneRequest(expectedRevision=2, idempotencyKey="old", prompt="p",
                                 imagePrompt="i", videoPrompt="v")
    result = await kie_workflow.enqueue_kie_repair(
        object(), object(), row.workspace_id, row.id, uuid4(), request,
    )
    assert result == {"status": "failed"}
    jobs.assert_not_called()
