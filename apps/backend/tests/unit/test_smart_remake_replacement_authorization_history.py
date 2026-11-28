"""Server authorization history is additive and bound to each exact replacement key."""

from __future__ import annotations

import copy
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from tests.unit.test_smart_remake_authorized_replacement import authorized_attempt, collision
from tests.unit.test_smart_remake_unlimited_ledger import reserve
from tests.unit.test_smart_remake_unlimited_ledger import stored_ledger as _stored_ledger
from viraldy.modules.smart_remake import budget_ledger as ledger
from viraldy.modules.smart_remake import generation_recovery as recovery
from viraldy.shared.errors.base import ConflictError


@pytest.fixture
def stored_ledger(monkeypatch):
    return _stored_ledger.__wrapped__(monkeypatch)


def attempt_with_history():
    attempt = authorized_attempt()
    original = attempt.metadata_json["replacementAuthorization"]
    addition = {
        **original, "replacementKey": str(uuid4()),
        "confirmedAt": datetime.now(UTC).isoformat(),
        "reason": "Continue the same authorized result after the concrete contract correction.",
    }
    attempt.metadata_json = {
        **attempt.metadata_json, "additionalReplacementAuthorizations": [addition],
    }
    return attempt


def keys_in_query(statement):
    values = statement.compile().params.values()
    return {item for value in values for item in (value if isinstance(value, list) else [value])
            if isinstance(item, str)}


def test_valid_primary_and_additional_consent_are_recognized_without_mutating_history():
    attempt = attempt_with_history()
    before = copy.deepcopy(vars(attempt))
    expected = {
        attempt.metadata_json["replacementAuthorization"]["replacementKey"],
        attempt.metadata_json["additionalReplacementAuthorizations"][0]["replacementKey"],
    }
    assert recovery.authorized_unconfirmed_replacement_keys(attempt) == frozenset(expected)
    assert recovery.is_authorized_unconfirmed_replacement(attempt)
    assert not recovery.attempt_needs_reconciliation(attempt)
    assert vars(attempt) == before


@pytest.mark.parametrize("field", ["actorId", "attemptId", "operationId", "receiptHash"])
def test_stolen_additional_authorization_cannot_lend_its_key_to_valid_primary(field):
    attempt = attempt_with_history()
    original = attempt.metadata_json["replacementAuthorization"]["replacementKey"]
    extra = attempt.metadata_json["additionalReplacementAuthorizations"][0]
    extra[field] = "c" * 64 if field == "receiptHash" else str(uuid4())
    assert recovery.authorized_unconfirmed_replacement_keys(attempt) == frozenset({original})


def test_changed_receipt_invalidates_every_saved_authorization():
    attempt = attempt_with_history()
    attempt.receipt_json["newObservation"] = "provider returned more evidence"
    assert recovery.authorized_unconfirmed_replacement_keys(attempt) == frozenset()
    assert recovery.attempt_needs_reconciliation(attempt)


def test_valid_additional_record_survives_invalid_primary_and_intermediate_record():
    attempt = attempt_with_history()
    addition = attempt.metadata_json["additionalReplacementAuthorizations"][0]
    attempt.metadata_json["replacementAuthorization"]["actorId"] = str(uuid4())
    attempt.metadata_json["additionalReplacementAuthorizations"] = [None, {}, addition, "invalid"]
    assert recovery.authorized_unconfirmed_replacement_keys(attempt) == frozenset({
        addition["replacementKey"],
    })


@pytest.mark.parametrize("index", [0, 1])
async def test_ledger_accepts_only_the_matching_saved_authorized_key(stored_ledger, index):
    attempt = attempt_with_history()
    stored = stored_ledger
    incoming = collision(stored, attempt)
    approved = [attempt.metadata_json["replacementAuthorization"],
                *attempt.metadata_json["additionalReplacementAuthorizations"]]
    expected = approved[index]["replacementKey"]
    result = stored.session.scalar.return_value

    async def owned_query(statement):
        return result if expected in keys_in_query(statement) else None

    stored.session.scalar.side_effect = owned_query
    before = copy.deepcopy(vars(attempt))
    fresh, created = await reserve(
        stored, f"{incoming.operation_id}:{incoming.metadata['slot']}", **incoming.arguments,
    )
    assert created and fresh.id != attempt.id
    assert vars(attempt) == before
    assert ledger._exposure(stored.rows) == Decimal("4")


async def test_unlisted_or_stolen_history_key_remains_fenced(stored_ledger):
    attempt = attempt_with_history()
    stolen = attempt.metadata_json["additionalReplacementAuthorizations"][0]
    stolen["actorId"] = str(uuid4())
    stored = stored_ledger
    incoming = collision(stored, attempt)
    result = stored.session.scalar.return_value

    async def owned_query(statement):
        return result if stolen["replacementKey"] in keys_in_query(statement) else None

    stored.session.scalar.side_effect = owned_query
    with pytest.raises(ConflictError):
        await reserve(
            stored, f"{incoming.operation_id}:{incoming.metadata['slot']}", **incoming.arguments,
        )
    assert len(stored.rows) == 1 and attempt.actual_usd is None


async def test_both_saved_groups_work_with_additional_key_and_old_receipts_stay_unknown(
    stored_ledger,
):
    attempt = attempt_with_history()
    stored = stored_ledger
    incoming = collision(stored, attempt)
    new_key = attempt.metadata_json["additionalReplacementAuthorizations"][0]["replacementKey"]
    result = stored.session.scalar.return_value
    stored.session.scalar.side_effect = lambda statement: (
        result if new_key in keys_in_query(statement) else None
    )
    first, _ = await reserve(
        stored, f"{incoming.operation_id}:{incoming.metadata['slot']}", **incoming.arguments,
    )
    first.status = "completed"
    _, created = await reserve(
        stored, f"{incoming.operation_id}:{incoming.second_slot}",
        **{**incoming.arguments, "request_hash": "f" * 64,
           "metadata": {**incoming.metadata, "slot": incoming.second_slot}},
    )
    assert created and attempt.status == "unknown" and attempt.actual_usd is None
    assert ledger._exposure(stored.rows) == Decimal("6")


async def test_original_attempt_key_replays_without_either_server_admin_annotation(stored_ledger):
    attempt = attempt_with_history()
    stored = stored_ledger
    stored.rows.append(attempt)
    metadata = {
        key: value for key, value in attempt.metadata_json.items()
        if key not in {"replacementAuthorization", "additionalReplacementAuthorizations"}
    }
    before = copy.deepcopy(vars(attempt))
    replay, created = await reserve(
        stored, attempt.idempotency_key, request_hash=attempt.request_hash,
        model=attempt.model, actor_id=attempt.actor_id, reservation_usd="2", metadata=metadata,
    )
    assert replay is attempt and not created
    assert vars(attempt) == before and len(stored.rows) == 1


async def test_two_unknown_receipts_require_the_same_exact_new_authorized_render(stored_ledger):
    first = attempt_with_history()
    second = authorized_attempt()
    second.actor_id = first.actor_id
    second.metadata_json["slot"] = first.metadata_json["slot"]
    authorization = second.metadata_json["replacementAuthorization"]
    new_key = first.metadata_json["additionalReplacementAuthorizations"][0]["replacementKey"]
    authorization.update(actorId=str(first.actor_id), replacementKey=new_key)
    stored = stored_ledger
    incoming = collision(stored, first)
    second.project_id, second.workspace_id = stored.project.id, stored.workspace
    stored.rows.append(second)
    before = copy.deepcopy((vars(first), vars(second)))
    result = stored.session.scalar.return_value
    stored.session.scalar.side_effect = lambda statement: (
        result if new_key in keys_in_query(statement) else None
    )
    fresh, created = await reserve(
        stored, f"{incoming.operation_id}:{incoming.metadata['slot']}", **incoming.arguments,
    )
    assert created and fresh.id not in {first.id, second.id}
    assert (vars(first), vars(second)) == before
    assert ledger._exposure(stored.rows) == Decimal("6")
