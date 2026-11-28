"""Wan uses the same receipt-bound recovery controls as other unified KIE video."""

from __future__ import annotations

import copy
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest

from viraldy.modules.smart_remake import budget_ledger, generation_recovery, provider_execution
from viraldy.modules.smart_remake.project_policy import stable_hash


def observed_attempt(monkeypatch, *, unknown=False, model="wan/3-0-video", owned=True):
    # Exercise the real nominal witness/binding path. TLS negotiation is the offline boundary.
    monkeypatch.setattr(provider_execution, "_verified_tls", lambda response, host: True)
    attempt_id, actor_id, operation_id = uuid4(), uuid4(), uuid4()
    request_hash = "d" * 64
    response = httpx.Response(
        200,
        request=httpx.Request(
            "POST",
            "https://api.kie.ai/api/v1/jobs/createTask",
            json={"model": model, "input": {"prompt": "Product demo"}},
        ),
        json={"code": 500 if unknown else 422, "msg": "Provider response", "data": None},
    )
    witness = provider_execution.observe_response(
        response,
        provider="kie",
        model=model,
        operation="kie.tasks.create",
        owned_transport=owned,
    )
    proof = provider_execution.bind_execution_evidence(
        witness,
        attempt_id=attempt_id,
        request_hash=request_hash,
        provider="kie",
        model=model,
    )
    receipt = {
        "errorCode": "SMART_REMAKE_SUBMISSION_UNRESOLVED" if unknown else "KIE_VALIDATION_FAILED",
        "httpStatus": 200,
        "providerCode": 500 if unknown else 422,
        **({"executionEvidence": proof} if proof else {}),
    }
    attempt = SimpleNamespace(
        id=attempt_id,
        actor_id=actor_id,
        request_hash=request_hash,
        stage="video",
        provider="kie",
        model=model,
        purpose="initial",
        status="unknown" if unknown else "failed",
        provider_task_id=None,
        usage_json={},
        actual_usd=None,
        estimated_usd=Decimal("2"),
        receipt_json=receipt,
        error_json=copy.deepcopy(receipt),
        metadata_json={"operationId": str(operation_id)},
    )
    if unknown:
        attempt.metadata_json["replacementAuthorization"] = {
            "schemaVersion": 1,
            "actorId": str(actor_id),
            "operationId": str(operation_id),
            "attemptId": str(attempt_id),
            "requestHash": request_hash,
            "receiptHash": stable_hash(receipt),
            "replacementKey": str(uuid4()),
            "confirmedAt": datetime.now(UTC).isoformat(),
            "reason": "Seller explicitly approved one replacement with the bill still unknown.",
        }
    return attempt


@pytest.mark.parametrize("unknown", [False, True])
def test_wan_physical_http_witness_releases_only_the_matching_control(unknown, monkeypatch):
    attempt = observed_attempt(monkeypatch, unknown=unknown)
    before = copy.deepcopy(vars(attempt))
    assert attempt.receipt_json["executionEvidence"]["model"] == "wan/3-0-video"
    assert generation_recovery.is_known_video_rejection(attempt) is (not unknown)
    assert generation_recovery.is_authorized_unconfirmed_replacement(attempt) is unknown
    assert not generation_recovery.attempt_needs_reconciliation(attempt)
    assert vars(attempt) == before
    assert attempt.actual_usd is None and budget_ledger._exposure([attempt]) == Decimal("2")


@pytest.mark.parametrize("unknown", [False, True])
@pytest.mark.parametrize(
    "change",
    ["unowned", "other_model", "wrong_actor", "wrong_hash", "wrong_proof_model", "known_task"],
)
def test_wan_compatibility_does_not_allow_unproven_or_borrowed_receipts(
    monkeypatch,
    unknown,
    change,
):
    attempt = observed_attempt(
        monkeypatch,
        unknown=unknown,
        model="other-model" if change == "other_model" else "wan/3-0-video",
        owned=change != "unowned",
    )
    if change == "wrong_hash":
        attempt.request_hash = "e" * 64
    elif change == "wrong_proof_model":
        attempt.receipt_json["executionEvidence"]["model"] = "veo-3-1"
    elif change == "known_task":
        attempt.provider_task_id = "known-task"
    elif change == "wrong_actor" and unknown:
        attempt.actor_id = uuid4()
    elif change == "wrong_actor":
        # A synchronous rejection has no actor authorization to borrow; corrupt its witness.
        attempt.receipt_json["executionEvidence"]["attemptId"] = str(uuid4())
    assert not generation_recovery.is_known_video_rejection(attempt)
    assert not generation_recovery.is_authorized_unconfirmed_replacement(attempt)
    assert generation_recovery.attempt_needs_reconciliation(attempt)


def test_wan_unknown_requires_explicit_consent_even_with_a_verified_http_response(monkeypatch):
    attempt = observed_attempt(monkeypatch, unknown=True)
    attempt.metadata_json.pop("replacementAuthorization")
    assert not generation_recovery.is_authorized_unconfirmed_replacement(attempt)
    assert generation_recovery.attempt_needs_reconciliation(attempt)
