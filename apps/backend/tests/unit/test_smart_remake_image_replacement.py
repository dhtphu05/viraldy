"""An explicit consent replaces one exact lost image response without hiding its bill."""

from __future__ import annotations

import copy
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from sqlalchemy.dialects import postgresql

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


def image_attempt():
    operation_id, actor_id, attempt_id = uuid4(), uuid4(), uuid4()
    now = datetime.now(UTC)
    attempt = SimpleNamespace(
        id=attempt_id,
        actor_id=actor_id,
        project_id=uuid4(),
        workspace_id=uuid4(),
        status="unknown",
        stage="image",
        provider="openai",
        model="gpt-image-2.6-sunburst",
        purpose="initial",
        provider_task_id=None,
        usage_json={},
        actual_usd=None,
        estimated_usd=Decimal("2"),
        profile_json={},
        policy_json={"mode": "unlimited"},
        created_at=now - timedelta(seconds=5),
        submitted_at=now - timedelta(seconds=4),
        request_hash="a" * 64,
        idempotency_key=f"{operation_id}:image:2:ending",
        receipt_json={"errorCode": "OPENAI_IMAGE_SUBMISSION_UNRESOLVED"},
        error_json={"errorCode": "OPENAI_IMAGE_SUBMISSION_UNRESOLVED"},
        metadata_json={"operationId": str(operation_id), "slot": "image:2:ending"},
    )
    attempt.metadata_json = {
        **attempt.metadata_json,
        "replacementAuthorization": {
            "schemaVersion": 1,
            "actorId": str(actor_id),
            "operationId": str(operation_id),
            "attemptId": str(attempt_id),
            "requestHash": attempt.request_hash,
            "receiptHash": stable_hash(attempt.receipt_json),
            "replacementKey": str(uuid4()),
            "confirmedAt": now.isoformat(),
            "reason": "Seller approved one replacement image.",
        },
    }
    return attempt


def image_collision(stored):
    attempt = image_attempt()
    attempt.project_id, attempt.workspace_id = stored.project.id, stored.workspace
    stored.rows.append(attempt)
    unit_ids = [str(uuid4()) for _ in range(4)]
    owned = {
        "kind": "render",
        "renderPlan": {
            "units": [{"id": value} for value in unit_ids],
            "groups": [{"renderUnitIds": unit_ids[:3]}, {"renderUnitIds": unit_ids[3:]}],
        },
    }
    stored.session.scalar = AsyncMock(return_value=owned)
    operation_id = uuid4()
    metadata = {"operationId": str(operation_id), "slot": "image:2:ending"}
    args = {
        "request_hash": attempt.request_hash,
        "stage": "image",
        "provider": "openai",
        "model": attempt.model,
        "actor_id": attempt.actor_id,
        "reservation_usd": "2",
        "metadata": metadata,
    }
    return SimpleNamespace(
        attempt=attempt, operation_id=operation_id, metadata=metadata, args=args, owned=owned
    )


def test_transport_unknown_image_consent_keeps_receipt_and_unknown_exposure_immutable():
    attempt = image_attempt()
    before = copy.deepcopy(vars(attempt))
    assert recovery.is_authorized_unconfirmed_replacement(attempt)
    assert not recovery.attempt_needs_reconciliation(attempt)
    assert vars(attempt) == before
    assert attempt.actual_usd is None and attempt.status == "unknown"


@pytest.mark.parametrize(
    "field,value",
    [
        ("status", "submitted"),
        ("status", "completed"),
        ("stage", "analysis"),
        ("provider", "kie"),
        ("model", "unknown-image-model"),
        ("purpose", "recheck"),
        ("provider_task_id", "task-known"),
        ("usage_json", {"total_tokens": 1}),
        ("actual_usd", Decimal("0")),
        ("error_json", {}),
        ("receipt_json", {"errorCode": "OTHER"}),
        ("receipt_json", {"errorCode": "OPENAI_IMAGE_SUBMISSION_UNRESOLVED", "requestId": "req_x"}),
        ("submitted_at", None),
    ],
)
def test_image_consent_does_not_grant_other_outcomes_or_unbounded_provider_calls(field, value):
    attempt = image_attempt()
    setattr(attempt, field, value)
    attempt.metadata_json["replacementAuthorization"]["receiptHash"] = stable_hash(
        attempt.receipt_json
    )
    assert not recovery.is_authorized_unconfirmed_replacement(attempt)


@pytest.mark.parametrize(
    "field,value",
    [
        ("actorId", str(uuid4())),
        ("operationId", str(uuid4())),
        ("attemptId", str(uuid4())),
        ("requestHash", "b" * 64),
        ("receiptHash", "b" * 64),
        ("replacementKey", "not-a-uuid"),
        ("schemaVersion", True),
        ("reason", ""),
        ("confirmedAt", (datetime.now(UTC) - timedelta(days=1)).isoformat()),
        ("confirmedAt", (datetime.now(UTC) + timedelta(days=1)).isoformat()),
    ],
)
def test_image_authorization_is_bound_to_exact_receipt_actor_operation_and_submission(field, value):
    attempt = image_attempt()
    attempt.metadata_json["replacementAuthorization"][field] = value
    assert not recovery.is_authorized_unconfirmed_replacement(attempt)


@pytest.mark.parametrize("slot", ["image:02:ending", "image:-1", "video:2", "image:2:other"])
def test_malformed_original_image_slot_cannot_receive_an_authorization(slot):
    attempt = image_attempt()
    attempt.metadata_json["slot"] = slot
    attempt.idempotency_key = f"{attempt.metadata_json['operationId']}:{slot}"
    assert not recovery.is_authorized_unconfirmed_replacement(attempt)


async def test_exact_ending_replacement_reserves_once_and_retains_the_old_bill(stored_ledger):
    stored = stored_ledger
    incoming = image_collision(stored)
    before = copy.deepcopy(vars(incoming.attempt))
    key = f"{incoming.operation_id}:{incoming.metadata['slot']}"
    fresh, created = await reserve(stored, key, **incoming.args)
    assert created and fresh is not incoming.attempt
    again, created = await reserve(stored, key, **incoming.args)
    assert again is fresh and not created
    assert vars(incoming.attempt) == before
    assert ledger._exposure(stored.rows) == Decimal("4")
    query = stored.session.scalar.call_args.args[0].compile(dialect=postgresql.dialect())
    assert stored.workspace in query.params.values() and stored.project.id in query.params.values()
    assert [
        incoming.attempt.metadata_json["replacementAuthorization"]["replacementKey"]
    ] in query.params.values()


@pytest.mark.parametrize(
    "change",
    [
        "hash",
        "slot",
        "role",
        "actor",
        "workspace",
        "project",
        "old_operation",
        "wrong_key",
        "missing_plan",
        "non_bookend",
        "wrong_idempotency",
        "purpose",
        "incoming_purpose",
    ],
)
async def test_image_consent_cannot_authorize_a_different_image_or_operation(stored_ledger, change):
    stored = stored_ledger
    incoming = image_collision(stored)
    if change == "hash":
        incoming.args["request_hash"] = "b" * 64
    elif change == "slot":
        incoming.metadata["slot"] = "image:3:ending"
    elif change == "role":
        incoming.metadata["slot"] = "image:2"
    elif change == "actor":
        incoming.args["actor_id"] = uuid4()
    elif change == "workspace":
        incoming.attempt.workspace_id = uuid4()
    elif change == "project":
        incoming.attempt.project_id = uuid4()
    elif change == "old_operation":
        incoming.metadata["operationId"] = incoming.attempt.metadata_json["operationId"]
    elif change == "wrong_key":
        stored.session.scalar.return_value = None
    elif change == "missing_plan":
        incoming.owned["renderPlan"] = {}
    elif change == "non_bookend":
        incoming.owned["renderPlan"]["groups"] = [
            {"renderUnitIds": [u["id"] for u in incoming.owned["renderPlan"]["units"]]}
        ]
    elif change == "purpose":
        incoming.attempt.purpose = "repair"
    elif change == "incoming_purpose":
        incoming.args["purpose"] = "repair"
    key = f"{incoming.metadata['operationId']}:{incoming.metadata['slot']}"
    if change == "wrong_idempotency":
        key = "different-key"
    if change == "old_operation":
        replay, created = await reserve(stored, key, **incoming.args)
        assert replay is incoming.attempt and not created and len(stored.rows) == 1
        assert not await ledger._authorized_replacement_collision(
            stored.session,
            stored.workspace,
            stored.project.id,
            incoming.attempt,
            actor_id=incoming.attempt.actor_id,
            idempotency_key=key,
            metadata=incoming.metadata,
            request_hash=incoming.attempt.request_hash,
        )
        return
    with pytest.raises(ConflictError) as caught:
        await reserve(stored, key, **incoming.args)
    assert caught.value.code == "SMART_REMAKE_ATTEMPT_RECONCILIATION_REQUIRED"
    assert len(stored.rows) == 1 and incoming.attempt.status == "unknown"


@pytest.mark.parametrize("role", ["", ":ending"])
async def test_exact_repair_image_matches_its_one_scene_and_preserves_unknown(stored_ledger, role):
    stored = stored_ledger
    incoming = image_collision(stored)
    slot = "image:2" + role
    incoming.attempt.purpose = "repair"
    incoming.attempt.metadata_json["slot"] = slot
    incoming.attempt.idempotency_key = f"{incoming.attempt.metadata_json['operationId']}:{slot}"
    incoming.metadata["slot"] = slot
    incoming.args["purpose"] = "repair"
    incoming.owned.update(kind="repair", sceneIndex=2)
    _, created = await reserve(stored, f"{incoming.operation_id}:{slot}", **incoming.args)
    assert created and incoming.attempt.status == "unknown"


async def test_repair_image_consent_does_not_cover_another_scene(stored_ledger):
    stored = stored_ledger
    incoming = image_collision(stored)
    incoming.attempt.purpose = "repair"
    incoming.owned.update(kind="repair", sceneIndex=3)
    with pytest.raises(ConflictError):
        await reserve(
            stored, f"{incoming.operation_id}:{incoming.metadata['slot']}", **incoming.args
        )


def test_image_authorization_requires_original_operation_slot_binding():
    attempt = image_attempt()
    attempt.idempotency_key = "another-image-slot"
    assert not recovery.is_authorized_unconfirmed_replacement(attempt)


def test_render_preflight_honors_image_consent_without_rewriting_unknown_fee_or_marker():
    row, attempt = project(), image_attempt()
    row.workspace_id = uuid4()
    attempt.project_id, attempt.workspace_id = row.id, row.workspace_id
    operation = SimpleNamespace(
        id=UUID(attempt.metadata_json["operationId"]),
        project_id=row.id,
        status="failed",
        result_json={
            "kind": "render",
            "needsReconciliation": True,
            "images": {"2:ending": {"status": "submitting", "attemptId": str(attempt.id)}},
        },
    )
    before = copy.deepcopy((vars(attempt), operation.result_json))
    response = run(
        "render", row=row, rows=[attempt], operations=[operation], budgetMode="unlimited"
    )
    assert not response.blockers
    assert response.budget.reservedUsd == response.budget.exposureUsd == "2"
    assert (vars(attempt), operation.result_json) == before
