"""A proven rejected KIE request settles control without inventing its bill."""

from __future__ import annotations

import copy
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest

from tests.unit.test_smart_remake_generation_recovery import rejected_attempt
from tests.unit.test_smart_remake_preflight import run
from tests.unit.test_smart_remake_unlimited_ledger import reserve
from tests.unit.test_smart_remake_unlimited_ledger import stored_ledger as _stored_ledger
from viraldy.modules.smart_remake import budget_ledger as ledger
from viraldy.modules.smart_remake import generation_recovery as recovery
from viraldy.shared.errors.base import AppError, ConflictError


@pytest.fixture
def stored_ledger(monkeypatch):
    return _stored_ledger.__wrapped__(monkeypatch)


def video_rejection(**changes):
    previous = rejected_attempt()
    proof = {
        **previous.receipt_json["executionEvidence"],
        "provider": "kie",
        "model": "veo-3-1",
        "operation": "kie.tasks.create",
    }
    receipt = {"errorCode": "KIE_VALIDATION_FAILED", "executionEvidence": proof}
    return SimpleNamespace(
        **{
            **vars(previous),
            "stage": "video",
            "provider": "kie",
            "model": "veo-3-1",
            "idempotency_key": "old-video",
            "actor_id": None,
            "profile_json": {},
            "policy_json": {"mode": "unlimited"},
            "receipt_json": receipt,
            "error_json": copy.deepcopy(receipt),
            **changes,
        }
    )


@pytest.mark.parametrize(
    "code",
    [
        "KIE_AUTH_FAILED",
        "KIE_CREDITS_EXHAUSTED",
        "KIE_RATE_LIMITED",
        "KIE_VALIDATION_FAILED",
    ],
)
def test_verified_legacy_kie_rejection_is_terminal_without_asserting_zero_cost(code):
    attempt = video_rejection()
    attempt.receipt_json["errorCode"] = code
    attempt.error_json["errorCode"] = code
    before = copy.deepcopy(vars(attempt))
    assert recovery.is_known_video_rejection(attempt)
    assert not recovery.attempt_needs_reconciliation(attempt)
    assert vars(attempt) == before
    assert attempt.actual_usd is None and attempt.estimated_usd == Decimal("2")


@pytest.mark.parametrize("purpose", ["initial", "repair"])
def test_observed_http200_business_rejection_settles_control_with_unknown_bill(purpose):
    attempt = video_rejection(purpose=purpose)
    attempt.receipt_json.update(
        requestOutcome="rejected", httpStatus=200, providerCode=422,
        providerMessage="Prompt is too long",
    )
    result = run(rows=[attempt])
    assert not result.blockers
    assert result.calls.video == 2
    assert result.budget.knownActualUsd == "0"
    assert result.budget.reservedUsd == result.budget.exposureUsd == "2"
    assert attempt.status == "failed" and attempt.actual_usd is None


@pytest.mark.parametrize("provider_code", [None, 409])
def test_generic_task_failure_cannot_prove_that_kie_did_not_accept_the_request(provider_code):
    attempt = video_rejection()
    attempt.receipt_json["errorCode"] = "KIE_TASK_CREATE_FAILED"
    attempt.error_json["errorCode"] = "KIE_TASK_CREATE_FAILED"
    if provider_code is not None:
        attempt.receipt_json.update(httpStatus=200, providerCode=provider_code)
    assert not recovery.is_known_video_rejection(attempt)
    assert recovery.attempt_needs_reconciliation(attempt)


@pytest.mark.parametrize(
    "change",
    [
        {"status": "reserved"},
        {"status": "submitted"},
        {"status": "unknown"},
        {"stage": "image"},
        {"provider": "other"},
        {"model": "other"},
        {"purpose": "loading_summary"},
        {"provider_task_id": "accepted-task"},
        {"usage_json": {"credits": 30}},
        {"receipt_json": {}},
        {"receipt_json": []},
        {"error_json": []},
        {"error_json": {"errorCode": "SMART_REMAKE_SUBMISSION_UNRESOLVED"}},
    ],
)
def test_inflight_or_unverified_kie_outcomes_remain_fenced(change):
    attempt = video_rejection(**change)
    assert not recovery.is_known_video_rejection(attempt)
    assert recovery.attempt_needs_reconciliation(attempt)


@pytest.mark.parametrize(
    "field,value",
    [
        ("operation", "kie.tasks.get"),
        ("provider", "openai"),
        ("model", "other"),
        ("requestHash", "c" * 64),
        ("attemptId", str(uuid4())),
        ("responseHash", "invalid"),
        ("observedAt", "2026-11-26T13:57:43"),
        ("taskId", "borrowed-task"),
    ],
)
def test_borrowed_or_malformed_kie_proof_cannot_release_control(field, value):
    attempt = video_rejection()
    attempt.receipt_json["executionEvidence"][field] = value
    assert not recovery.is_known_video_rejection(attempt)
    assert recovery.attempt_needs_reconciliation(attempt)


@pytest.mark.parametrize(
    "extra",
    [
        {"httpStatus": 500},
        {"httpStatus": "200"},
        {"providerCode": 200},
        {"providerCode": 500},
        {"providerCode": "422"},
        {"requestOutcome": "accepted"},
        {"errorCode": "KIE_SUBMISSION_UNCERTAIN"},
        {"errorCode": []},
    ],
)
def test_contradictory_or_unknown_rejection_metadata_remains_fenced(extra):
    attempt = video_rejection()
    attempt.receipt_json.update(extra)
    assert not recovery.is_known_video_rejection(attempt)
    assert recovery.attempt_needs_reconciliation(attempt)


async def test_confirmed_new_key_reuses_inputs_without_erasing_failed_kie_exposure(stored_ledger):
    rejected = video_rejection()
    stored = stored_ledger
    stored.rows.append(rejected)
    arguments = {
        "request_hash": rejected.request_hash,
        "model": rejected.model,
        "reservation_usd": "2",
        "metadata": rejected.metadata_json,
    }
    before = copy.deepcopy(vars(rejected))
    replay, created = await reserve(stored, "old-video", **arguments)
    assert replay is rejected and not created
    fresh, created = await reserve(stored, "confirmed-new-video", **arguments)
    assert created and fresh.id != rejected.id
    assert vars(rejected) == before
    assert ledger._exposure(stored.rows) == Decimal("4")


async def test_unproven_video_error_cannot_authorize_replacement_key(stored_ledger):
    rejected = video_rejection(receipt_json={})
    stored_ledger.rows.append(rejected)
    with pytest.raises(ConflictError) as blocked:
        await reserve(
            stored_ledger, "replacement", request_hash=rejected.request_hash,
            model=rejected.model, reservation_usd="2", metadata={},
        )
    assert blocked.value.code == "SMART_REMAKE_ATTEMPT_RECONCILIATION_REQUIRED"
    assert len(stored_ledger.rows) == 1


async def test_known_kie_rejection_does_not_release_held_money_from_finite_budget(stored_ledger):
    stored = stored_ledger
    stored.project.context_json["p0"]["budgetPolicy"] = {
        "capUsd": "3", "maxAttempts": 10, "maxDurationSeconds": 3600,
    }
    rejected = video_rejection()
    stored.rows.append(rejected)
    with pytest.raises(AppError) as blocked:
        await reserve(
            stored, "confirmed", request_hash=rejected.request_hash, model=rejected.model,
            reservation_usd="2", metadata={},
        )
    assert blocked.value.code == "SMART_REMAKE_BUDGET_EXCEEDED"
    assert rejected.actual_usd is None and ledger._exposure(stored.rows) == Decimal("2")
