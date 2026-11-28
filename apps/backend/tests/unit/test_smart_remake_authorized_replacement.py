"""Explicit consent permits one bound replacement while retaining the unknown receipt."""

from __future__ import annotations

import copy
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from sqlalchemy.dialects import postgresql

from tests.unit.test_smart_remake_kie_rejection_control import video_rejection
from tests.unit.test_smart_remake_preflight import project, run
from tests.unit.test_smart_remake_unlimited_ledger import reserve
from tests.unit.test_smart_remake_unlimited_ledger import stored_ledger as _stored_ledger
from viraldy.modules.smart_remake import budget_ledger as ledger
from viraldy.modules.smart_remake import generation_recovery as recovery
from viraldy.modules.smart_remake.project_policy import stable_hash
from viraldy.shared.errors.base import ConflictError


@pytest.fixture
def stored_ledger(monkeypatch):
    return _stored_ledger.__wrapped__(monkeypatch)


def authorized_attempt():
    attempt = video_rejection(status="unknown", actor_id=uuid4())
    slot = f"video:group:{uuid4()}"
    attempt.metadata_json = {**attempt.metadata_json, "slot": slot}
    attempt.idempotency_key = f"{attempt.metadata_json['operationId']}:{slot}"
    attempt.receipt_json["errorCode"] = "SMART_REMAKE_SUBMISSION_UNRESOLVED"
    attempt.error_json = copy.deepcopy(attempt.receipt_json)
    authorization = {
        "schemaVersion": 1,
        "actorId": str(attempt.actor_id),
        "operationId": attempt.metadata_json["operationId"],
        "attemptId": str(attempt.id),
        "requestHash": attempt.request_hash,
        "receiptHash": stable_hash(attempt.receipt_json),
        "replacementKey": str(uuid4()),
        "confirmedAt": datetime.now(UTC).isoformat(),
        "reason": "Seller explicitly accepts a new paid request with the old outcome unknown.",
    }
    attempt.metadata_json = {**attempt.metadata_json, "replacementAuthorization": authorization}
    return attempt


def test_exact_manual_authorization_releases_control_without_rewriting_unknown_evidence():
    attempt = authorized_attempt()
    before = copy.deepcopy(vars(attempt))
    assert recovery.is_authorized_unconfirmed_replacement(attempt)
    assert not recovery.attempt_needs_reconciliation(attempt)
    assert vars(attempt) == before
    assert attempt.status == "unknown" and attempt.actual_usd is None


@pytest.mark.parametrize(
    "field,value",
    [
        ("schemaVersion", True), ("schemaVersion", 2),
        ("actorId", str(uuid4())), ("actorId", "not-a-uuid"),
        ("operationId", str(uuid4())), ("attemptId", str(uuid4())),
        ("requestHash", "c" * 64), ("receiptHash", "c" * 64),
        ("replacementKey", "not-a-uuid"),
        ("confirmedAt", "2026-11-26T13:57:43"),
        ("confirmedAt", "2026-11-26T13:57:43+07:00"),
        ("confirmedAt", (datetime.now(UTC) + timedelta(days=1)).isoformat()),
        ("confirmedAt", "2000-01-01T00:00:00+00:00"),
        ("reason", ""), ("reason", "  "), ("reason", "x" * 1001),
    ],
)
def test_manual_authorization_cannot_be_borrowed_or_malformed(field, value):
    attempt = authorized_attempt()
    attempt.metadata_json["replacementAuthorization"][field] = value
    assert not recovery.is_authorized_unconfirmed_replacement(attempt)
    assert recovery.attempt_needs_reconciliation(attempt)


@pytest.mark.parametrize(
    "change",
    [
        {"status": "submitted"}, {"status": "reserved"}, {"status": "failed"},
        {"stage": "image"}, {"provider": "other"}, {"model": "other"},
        {"provider_task_id": "accepted-task"}, {"usage_json": {"credits": 30}},
        {"actor_id": None}, {"metadata_json": {}},
    ],
)
def test_manual_authorization_is_only_for_the_unconfirmed_taskless_kie_attempt(change):
    attempt = authorized_attempt()
    for field, value in change.items():
        setattr(attempt, field, value)
    assert not recovery.is_authorized_unconfirmed_replacement(attempt)
    assert recovery.attempt_needs_reconciliation(attempt)


@pytest.mark.parametrize("change", ["receipt", "proof", "operation"])
def test_changed_receipt_or_source_operation_invalidates_saved_authorization(change):
    attempt = authorized_attempt()
    if change == "receipt":
        attempt.receipt_json["laterObservation"] = "new evidence"
    elif change == "proof":
        attempt.receipt_json["executionEvidence"]["attemptId"] = str(uuid4())
        attempt.metadata_json["replacementAuthorization"]["receiptHash"] = stable_hash(
            attempt.receipt_json
        )
    else:
        attempt.metadata_json["operationId"] = str(uuid4())
    assert not recovery.is_authorized_unconfirmed_replacement(attempt)


def collision(stored, attempt):
    stored.rows.append(attempt)
    attempt.project_id, attempt.workspace_id = stored.project.id, stored.workspace
    operation_id = uuid4()
    group_id = attempt.metadata_json["slot"].removeprefix("video:group:")
    second_group = str(uuid4())
    result = {"kind": "render", "renderPlan": {"groups": [{"id": group_id}, {"id": second_group}]}}
    stored.session.scalar = AsyncMock(return_value=result)
    metadata = {"operationId": str(operation_id), "slot": attempt.metadata_json["slot"]}
    arguments = {
        "request_hash": attempt.request_hash, "model": attempt.model,
        "reservation_usd": "2", "metadata": metadata, "actor_id": attempt.actor_id,
    }
    return SimpleNamespace(
        operation_id=operation_id, metadata=metadata, arguments=arguments,
        second_slot=f"video:group:{second_group}",
    )


async def test_write_boundary_requires_the_exact_owned_replacement_operation(stored_ledger):
    attempt = authorized_attempt()
    stored = stored_ledger
    incoming = collision(stored, attempt)
    before = copy.deepcopy(vars(attempt))
    fresh, created = await reserve(
        stored, f"{incoming.operation_id}:{incoming.metadata['slot']}", **incoming.arguments
    )
    assert created and fresh.id != attempt.id
    assert vars(attempt) == before
    assert ledger._exposure(stored.rows) == Decimal("4")
    query = stored.session.scalar.call_args.args[0].compile(dialect=postgresql.dialect())
    parameters = query.params.values()
    authorization = attempt.metadata_json["replacementAuthorization"]
    assert stored.project.id in parameters and stored.workspace in parameters
    assert any(
        value == authorization["replacementKey"]
        or isinstance(value, list) and authorization["replacementKey"] in value
        for value in parameters
    )
    assert str(attempt.actor_id) in parameters and incoming.operation_id in parameters


async def test_exact_authorized_render_can_generate_both_saved_eight_second_groups(stored_ledger):
    attempt = authorized_attempt()
    stored = stored_ledger
    incoming = collision(stored, attempt)
    first, _ = await reserve(
        stored, f"{incoming.operation_id}:{incoming.metadata['slot']}", **incoming.arguments
    )
    first.status = "completed"
    second_args = {
        **incoming.arguments, "request_hash": "d" * 64,
        "metadata": {**incoming.metadata, "slot": incoming.second_slot},
    }
    second, created = await reserve(
        stored, f"{incoming.operation_id}:{incoming.second_slot}", **second_args
    )
    assert created and second.id != first.id
    assert attempt.status == "unknown" and attempt.actual_usd is None
    assert ledger._exposure(stored.rows) == Decimal("6")


async def test_changed_hash_does_not_authorize_an_arbitrary_future_request(stored_ledger):
    attempt = authorized_attempt()
    stored = stored_ledger
    incoming = collision(stored, attempt)
    first, _ = await reserve(
        stored, f"{incoming.operation_id}:{incoming.metadata['slot']}", **incoming.arguments
    )
    first.status = "completed"
    stored.session.scalar.return_value = None
    next_id = uuid4()
    with pytest.raises(ConflictError):
        await reserve(
            stored, f"{next_id}:{incoming.metadata['slot']}",
            **{**incoming.arguments, "request_hash": "e" * 64,
               "metadata": {**incoming.metadata, "operationId": str(next_id)}},
        )
    assert len(stored.rows) == 2


@pytest.mark.parametrize("change", ["wrong_saved_key", "actor", "prefix", "slot", "old_operation"])
async def test_one_consent_cannot_authorize_other_keys_actors_or_video_slots(stored_ledger, change):
    attempt = authorized_attempt()
    stored = stored_ledger
    incoming = collision(stored, attempt)
    key = f"{incoming.operation_id}:{incoming.metadata['slot']}"
    if change == "wrong_saved_key":
        stored.session.scalar.return_value = None
    elif change == "actor":
        incoming.arguments["actor_id"] = uuid4()
    elif change == "prefix":
        key = str(uuid4())
    elif change == "slot":
        incoming.metadata["slot"] = f"video:group:{uuid4()}"
        key = f"{incoming.operation_id}:{incoming.metadata['slot']}"
    else:
        incoming.metadata["operationId"] = attempt.metadata_json["operationId"]
    with pytest.raises(ConflictError) as blocked:
        await reserve(stored, key, **incoming.arguments)
    assert blocked.value.code == "SMART_REMAKE_ATTEMPT_RECONCILIATION_REQUIRED"
    assert len(stored.rows) == 1 and attempt.status == "unknown"


async def test_original_key_still_replays_original_receipt_after_admin_annotation(stored_ledger):
    attempt = authorized_attempt()
    stored = stored_ledger
    stored.rows.append(attempt)
    original_metadata = {
        key: value for key, value in attempt.metadata_json.items()
        if key != "replacementAuthorization"
    }
    replay, created = await reserve(
        stored, attempt.idempotency_key, request_hash=attempt.request_hash,
        model=attempt.model, actor_id=attempt.actor_id, reservation_usd="2",
        metadata=original_metadata,
    )
    assert replay is attempt and not created
    assert len(stored.rows) == 1 and attempt.actual_usd is None


def pending_operation():
    row, attempt = project(), authorized_attempt()
    row.workspace_id = uuid4()
    attempt.project_id, attempt.workspace_id = row.id, row.workspace_id
    operation = SimpleNamespace(
        id=UUID(attempt.metadata_json["operationId"]), project_id=row.id, status="failed",
        result_json={"kind": "render", "needsReconciliation": True,
                     "tasks": {"group": {"status": "submitting", "attemptId": str(attempt.id)}}},
    )
    return row, attempt, operation


@pytest.mark.parametrize("kind", ["render", "repair"])
def test_preflight_keeps_old_unconfirmed_result_but_honors_exact_manual_consent(kind):
    row, attempt, operation = pending_operation()
    operation.result_json["kind"] = kind
    before = copy.deepcopy((vars(attempt), operation.result_json))
    fields = {"sceneId": "s0", "baseVersionId": "v0"} if kind == "repair" else {}
    result = run(
        kind, row=row, rows=[attempt], operations=[operation], budgetMode="unlimited", **fields,
    )
    assert not result.blockers
    assert result.calls.video == (1 if kind == "repair" else 2)
    assert result.budget.reservedUsd == result.budget.exposureUsd == "2"
    assert (vars(attempt), operation.result_json) == before


@pytest.mark.parametrize(
    "kind,action,fields",
    [
        ("render", "analyze", {}),
        ("render", "reanalyze", {}),
        ("render", "inspect", {"subject": {"kind": "assembly", "assemblyId": "a1"}}),
        ("render", "repair", {"sceneId": "s0", "baseVersionId": "v0"}),
        ("repair", "render", {}),
    ],
)
def test_manual_video_replacement_consent_does_not_authorize_other_action_kinds(
    kind, action, fields,
):
    row, attempt, operation = pending_operation()
    operation.result_json["kind"] = kind
    result = run(
        action, row=row, rows=[attempt], operations=[operation], budgetMode="unlimited", **fields,
    )
    assert "SMART_REMAKE_ATTEMPT_RECONCILIATION_REQUIRED" in {
        block.code for block in result.blockers
    }


@pytest.mark.parametrize(
    "change", ["running", "completed", "other_project", "foreign_attempt", "no_attempt", "extra"],
)
def test_preflight_never_generically_ignores_unknown_operations(change):
    row, attempt, operation = pending_operation()
    attempts = [attempt]
    if change in {"running", "completed"}:
        operation.status = change
    elif change == "other_project":
        operation.project_id = uuid4()
    elif change == "foreign_attempt":
        attempt.workspace_id = uuid4()
    elif change == "no_attempt":
        attempts = []
    else:
        other = video_rejection(status="unknown")
        other.project_id, other.workspace_id = row.id, row.workspace_id
        other.metadata_json["operationId"] = str(operation.id)
        attempts.append(other)
    result = run(row=row, rows=attempts, operations=[operation], budgetMode="unlimited")
    assert "SMART_REMAKE_ATTEMPT_RECONCILIATION_REQUIRED" in {
        block.code for block in result.blockers
    }
