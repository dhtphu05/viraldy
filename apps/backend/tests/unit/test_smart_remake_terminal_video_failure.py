"""Observed terminal provider failures settle control while the bill stays unknown."""

from __future__ import annotations

import copy
from decimal import Decimal

import pytest

from tests.unit.test_smart_remake_kie_rejection_control import video_rejection
from tests.unit.test_smart_remake_preflight import run
from tests.unit.test_smart_remake_unlimited_ledger import reserve
from tests.unit.test_smart_remake_unlimited_ledger import stored_ledger as _stored_ledger
from viraldy.modules.smart_remake import budget_ledger as ledger
from viraldy.modules.smart_remake import generation_recovery as recovery
from viraldy.shared.errors.base import ConflictError


@pytest.fixture
def stored_ledger(monkeypatch):
    return _stored_ledger.__wrapped__(monkeypatch)


def terminal_failure(model="veo-3-1", *, separate_proof=False):
    attempt = video_rejection()
    task_id = "terminal-task-123"
    proof = {
        **attempt.receipt_json["executionEvidence"],
        "model": model,
        "operation": "kie.tasks.get",
        "taskId": task_id,
    }
    receipt = {
        "errorCode": "KIE_TASK_FAILED",
        "providerTaskId": task_id,
        "providerCode": 500,
        "providerMessage": "Internal Error, Please try again later.",
        "executionEvidence": proof,
    }
    if separate_proof:
        receipt["terminalExecutionEvidence"] = proof
        receipt["executionEvidence"] = {
            **attempt.receipt_json["executionEvidence"],
            "model": model,
            "taskId": task_id,
        }
    attempt.model = model
    attempt.provider_task_id = task_id
    attempt.receipt_json = receipt
    attempt.error_json = {"errorCode": "KIE_TASK_FAILED", "providerTaskId": task_id}
    return attempt


@pytest.mark.parametrize("model", ["veo-3-1", "wan/3-0-video"])
@pytest.mark.parametrize("separate_proof", [False, True])
def test_verified_terminal_failure_releases_control_without_changing_receipts_or_money(
    model,
    separate_proof,
):
    attempt = terminal_failure(model, separate_proof=separate_proof)
    before = copy.deepcopy(vars(attempt))
    assert recovery.is_terminal_failed_video_response(attempt)
    assert not recovery.attempt_needs_reconciliation(attempt)
    assert vars(attempt) == before
    assert attempt.actual_usd is None and ledger._exposure([attempt]) == Decimal("2")


@pytest.mark.parametrize("model", ["veo-3-1", "wan/3-0-video"])
def test_preflight_keeps_unknown_terminal_failure_fee_reserved(model):
    attempt = terminal_failure(model)
    before = copy.deepcopy(vars(attempt))
    response = run(rows=[attempt])
    assert not response.blockers
    assert response.budget.knownActualUsd == "0"
    assert response.budget.reservedUsd == response.budget.exposureUsd == "2"
    assert vars(attempt) == before


@pytest.mark.parametrize(
    "field,value",
    [
        ("status", "reserved"),
        ("status", "submitted"),
        ("status", "unknown"),
        ("stage", "image"),
        ("provider", "openai"),
        ("model", "other"),
        ("provider_task_id", None),
        ("provider_task_id", "different-task"),
        ("provider_task_id", "https://provider.invalid/task"),
        ("error_json", []),
        ("error_json", {"errorCode": "KIE_AUTH_FAILED"}),
    ],
)
def test_unknown_other_provider_and_contradictory_outcomes_stay_fenced(field, value):
    attempt = terminal_failure()
    setattr(attempt, field, value)
    assert not recovery.is_terminal_failed_video_response(attempt)
    assert recovery.attempt_needs_reconciliation(attempt)


@pytest.mark.parametrize(
    "field,value",
    [
        ("providerTaskId", "different-task"),
        ("errorCode", "KIE_AUTH_FAILED"),
        ("errorCode", "SMART_REMAKE_SUBMISSION_UNRESOLVED"),
        ("executionEvidence", None),
        ("requestOutcome", "unknown"),
        ("httpStatus", 401),
        ("httpStatus", "200"),
    ],
)
def test_receipt_without_terminal_matching_task_observation_stays_fenced(field, value):
    attempt = terminal_failure()
    attempt.receipt_json[field] = value
    assert not recovery.is_terminal_failed_video_response(attempt)
    assert recovery.attempt_needs_reconciliation(attempt)


@pytest.mark.parametrize(
    "field,value",
    [
        ("operation", "kie.tasks.create"),
        ("operation", "openai.images.edit"),
        ("taskId", "different-task"),
        ("model", "other"),
        ("provider", "google"),
        ("requestHash", "c" * 64),
        ("attemptId", "00000000-0000-4000-8000-000000000001"),
        ("responseHash", "not-a-hash"),
        ("transport", "mock"),
        ("mode", "fixture"),
    ],
)
def test_forged_borrowed_or_non_get_proof_cannot_release_failed_video(field, value):
    attempt = terminal_failure()
    attempt.receipt_json["executionEvidence"][field] = value
    assert not recovery.is_terminal_failed_video_response(attempt)
    assert recovery.attempt_needs_reconciliation(attempt)


def test_get_proof_requires_an_explicit_matching_task_id():
    attempt = terminal_failure()
    attempt.receipt_json["executionEvidence"].pop("taskId")
    assert not recovery.is_terminal_failed_video_response(attempt)
    assert recovery.attempt_needs_reconciliation(attempt)


def test_invalid_additional_terminal_proof_does_not_fall_back_to_another_receipt():
    attempt = terminal_failure(separate_proof=True)
    attempt.receipt_json["terminalExecutionEvidence"]["taskId"] = "borrowed-task"
    assert not recovery.is_terminal_failed_video_response(attempt)
    assert recovery.attempt_needs_reconciliation(attempt)


def test_completed_receipt_semantics_remain_terminal_even_without_known_usd():
    attempt = terminal_failure()
    attempt.status = "completed"
    before = copy.deepcopy(vars(attempt))
    assert not recovery.is_terminal_failed_video_response(attempt)
    assert not recovery.attempt_needs_reconciliation(attempt)
    assert vars(attempt) == before and attempt.actual_usd is None


@pytest.mark.parametrize("model", ["veo-3-1", "wan/3-0-video"])
async def test_confirmed_new_intent_can_reserve_same_terminal_failed_payload_without_erasing_bill(
    stored_ledger, model,
):
    stored = stored_ledger
    attempt = terminal_failure(model, separate_proof=True)
    stored.rows.append(attempt)
    before = copy.deepcopy(vars(attempt))
    arguments = {
        "stage": "video", "provider": "kie", "model": model,
        "request_hash": attempt.request_hash, "reservation_usd": "2",
        "metadata": attempt.metadata_json,
    }
    replay, created = await reserve(stored, attempt.idempotency_key, **arguments)
    assert replay is attempt and not created
    fresh, created = await reserve(stored, "seller-confirmed-new-video", **arguments)
    assert created and fresh is not attempt
    assert ledger._exposure(stored.rows) == Decimal("4")
    assert vars(attempt) == before and attempt.actual_usd is None


@pytest.mark.parametrize("change", ["create_only", "unknown", "wrong_hash", "no_proof"])
async def test_ledger_still_fences_same_payload_without_a_known_terminal_get(stored_ledger, change):
    stored = stored_ledger
    attempt = terminal_failure("wan/3-0-video", separate_proof=True)
    if change == "create_only":
        attempt.receipt_json.pop("terminalExecutionEvidence")
    elif change == "unknown":
        attempt.status = "unknown"
    elif change == "wrong_hash":
        attempt.receipt_json["terminalExecutionEvidence"]["requestHash"] = "e" * 64
    else:
        attempt.receipt_json.pop("terminalExecutionEvidence")
        attempt.receipt_json.pop("executionEvidence")
    stored.rows.append(attempt)
    before = copy.deepcopy(vars(attempt))
    with pytest.raises(ConflictError) as caught:
        await reserve(
            stored, "new-unproven-video", request_hash=attempt.request_hash,
            model=attempt.model, reservation_usd="2", metadata=attempt.metadata_json,
        )
    assert caught.value.code == "SMART_REMAKE_ATTEMPT_RECONCILIATION_REQUIRED"
    assert len(stored.rows) == 1 and ledger._exposure(stored.rows) == Decimal("2")
    assert vars(attempt) == before
