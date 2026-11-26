from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest

from viraldy.modules.smart_remake import budget_ledger as ledger
from viraldy.modules.smart_remake import budgeted_analysis, generation_budget
from viraldy.shared.errors.base import AppError, ConflictError


@pytest.fixture
def stored_ledger(monkeypatch):
    project = SimpleNamespace(
        id=uuid4(),
        context_json={"p0": {"budgetPolicy": {"mode": "unlimited"}}},
    )
    rows = []

    class Session:
        commits = 0
        rollbacks = 0

        def add(self, row):
            row.id = row.id or uuid4()
            row.created_at = datetime.now(UTC)
            rows.append(row)

        async def commit(self):
            self.commits += 1

        async def rollback(self):
            self.rollbacks += 1

        async def execute(self, statement, params=None):
            if params and "results" in params:
                project.context_json["p0"].setdefault("modelResults", {}).update(
                    json.loads(params["results"])
                )

    async def owned(*args, **kwargs):
        return project

    async def attempts(*args):
        return rows

    async def locked(session, workspace, pid, attempt_id):
        return next(row for row in rows if row.id == attempt_id)

    monkeypatch.setattr(ledger, "_project", owned)
    monkeypatch.setattr(ledger, "_attempts", attempts)
    monkeypatch.setattr(ledger, "_locked_attempt", locked)
    return SimpleNamespace(project=project, rows=rows, session=Session(), workspace=uuid4())


async def reserve(stored, key="request", **overrides):
    args = {
        "idempotency_key": key, "request_hash": "request-hash", "stage": "video",
        "reservation_usd": "0", "actor_id": None, "provider": "kie", "model": "veo3_lite",
        "metadata": {"costEstimate": {"status": "unknown", "reason": "server_price_unconfigured"}},
    }
    return await ledger.reserve_attempt(
        stored.session, stored.workspace, stored.project.id, **{**args, **overrides}
    )


async def test_verified_image_rejection_new_key_keeps_exposure_and_old_key_replays(stored_ledger):
    from tests.unit.test_smart_remake_generation_recovery import rejected_attempt

    stored = stored_ledger
    rejected = rejected_attempt(idempotency_key="old-image", actor_id=None,
                                profile_json={}, policy_json={"mode": "unlimited"})
    stored.rows.append(rejected)
    args = {"request_hash": rejected.request_hash, "stage": "image", "provider": "openai",
            "model": rejected.model, "reservation_usd": "2", "metadata": rejected.metadata_json}
    replay, created = await reserve(stored, "old-image", **args)
    assert replay is rejected and not created
    fresh, created = await reserve(stored, "confirmed-new-image", **args)
    assert created and fresh.id != rejected.id
    assert rejected.actual_usd is None and rejected.estimated_usd == 2
    assert ledger._exposure(stored.rows) == 4


async def test_unverified_failed_image_still_blocks_new_key(stored_ledger):
    from tests.unit.test_smart_remake_generation_recovery import rejected_attempt

    rejected = rejected_attempt(receipt_json={})
    rejected.idempotency_key = "old-unverified"
    stored_ledger.rows.append(rejected)
    with pytest.raises(ConflictError) as blocked:
        await reserve(stored_ledger, "new", request_hash=rejected.request_hash,
                      stage="image", provider="openai", model=rejected.model)
    assert blocked.value.code == "SMART_REMAKE_ATTEMPT_RECONCILIATION_REQUIRED"


async def test_known_rejection_does_not_release_reservation_under_finite_policy(stored_ledger):
    from tests.unit.test_smart_remake_generation_recovery import rejected_attempt

    stored = stored_ledger
    stored.project.context_json["p0"]["budgetPolicy"] = {
        "capUsd": "3", "maxAttempts": 10, "maxDurationSeconds": 3600,
    }
    rejected = rejected_attempt()
    rejected.idempotency_key = "old-known"
    stored.rows.append(rejected)
    with pytest.raises(AppError) as blocked:
        await reserve(stored, "confirmed", request_hash=rejected.request_hash,
                      stage="image", provider="openai", model=rejected.model,
                      reservation_usd="2", metadata={})
    assert blocked.value.code == "SMART_REMAKE_BUDGET_EXCEEDED"
    assert rejected.actual_usd is None and ledger._exposure(stored.rows) == 2


def test_unlimited_policy_has_no_synthetic_money_attempt_or_time_limits():
    assert ledger.normalize_policy({}) == {"mode": "unlimited"}
    assert ledger.normalize_policy({
        "mode": "unlimited", "capUsd": "0", "maxAttempts": 1,
        "maxDurationSeconds": 1, "startedAt": "2000-01-01T00:00:00+00:00",
    }) == {"mode": "unlimited", "startedAt": "2000-01-01T00:00:00+00:00"}
    legacy = {"capUsd": "2.5", "maxAttempts": 5, "maxDurationSeconds": 30}
    assert ledger.normalize_policy(legacy) == legacy


@pytest.mark.parametrize("raw_bound", [None, "", "0", "NaN", "invalid"])
def test_unavailable_price_is_unknown_only_for_unlimited_policy(raw_bound):
    arguments = {"error_code": "PRICE_REQUIRED", "message": "Configure a price."}
    amount, metadata = ledger.reservation_estimate({}, raw_bound, **arguments)
    assert amount == 0 and metadata["costEstimate"]["status"] == "unknown"
    with pytest.raises(AppError):
        ledger.reservation_estimate(
            {"capUsd": "2", "maxAttempts": 5, "maxDurationSeconds": 3600},
            raw_bound, **arguments,
        )


def test_configured_prices_remain_exact_for_both_policy_modes():
    for policy in ({}, {"capUsd": "2", "maxAttempts": 5, "maxDurationSeconds": 3600}):
        amount, metadata = ledger.reservation_estimate(
            policy, "0.125", error_code="PRICE_REQUIRED", message="Configure a price.",
        )
        assert amount == Decimal("0.125") and metadata == {}
    with pytest.raises(AppError):
        ledger.normalize_policy({"mode": "other"})


@pytest.mark.asyncio
async def test_unlimited_reservations_ignore_old_caps_and_elapsed_project_time(stored_ledger):
    stored = stored_ledger
    stored.project.context_json["p0"]["budgetPolicy"].update(
        capUsd="0.01", maxAttempts=1, maxDurationSeconds=1,
        startedAt="2000-01-01T00:00:00+00:00",
    )
    one, created = await reserve(stored, reservation_usd="50", metadata={})
    assert created
    one.status = "completed"
    two, created = await reserve(stored, "next", reservation_usd="50", metadata={})
    assert created and one.id != two.id
    assert two.policy_json == {"mode": "unlimited", "startedAt": "2000-01-01T00:00:00+00:00"}


@pytest.mark.asyncio
async def test_initializing_unlimited_preserves_history_without_a_ceiling(stored_ledger):
    stored = stored_ledger
    started = "2000-01-01T00:00:00+00:00"
    stored.project.context_json["p0"]["budgetPolicy"]["startedAt"] = started
    await reserve(stored)
    policy = await ledger.initialize_budget(
        stored.session, stored.workspace, stored.project.id, {},
    )
    assert policy == {"mode": "unlimited", "startedAt": started}
    assert len(stored.rows) == 1


@pytest.mark.asyncio
async def test_unknown_estimate_is_explicit_and_replay_does_not_reprice(stored_ledger):
    stored = stored_ledger
    first, created = await reserve(stored)
    assert created and first.actual_usd is None and first.estimated_usd == 0
    replay, created = await reserve(stored, reservation_usd="3.25", metadata={})
    assert not created and replay is first
    assert replay.estimated_usd == 0 and replay.metadata_json["costEstimate"]["status"] == "unknown"
    with pytest.raises(ConflictError):
        await reserve(stored, request_hash="different")


@pytest.mark.asyncio
async def test_zero_estimate_without_unknown_marker_and_bounded_zero_are_rejected(stored_ledger):
    stored = stored_ledger
    with pytest.raises(AppError):
        await reserve(stored, metadata={})
    stored.project.context_json["p0"]["budgetPolicy"] = {
        "capUsd": "2", "maxAttempts": 5, "maxDurationSeconds": 3600,
    }
    with pytest.raises(AppError):
        await reserve(stored)
    assert not stored.rows


@pytest.mark.asyncio
async def test_unknown_receipt_still_fences_a_replacement_key(stored_ledger):
    stored = stored_ledger
    first, _ = await reserve(stored)
    first.status = "unknown"
    with pytest.raises(ConflictError) as conflict:
        await reserve(stored, "replacement")
    assert conflict.value.code == "SMART_REMAKE_ATTEMPT_RECONCILIATION_REQUIRED"
    assert len(stored.rows) == 1
    first.status = "completed"
    _, created = await reserve(stored, "explicit-next")
    assert created


@pytest.mark.asyncio
async def test_unknown_amounts_are_nullable_and_known_exposure_remains_visible(stored_ledger):
    stored = stored_ledger
    unknown, _ = await reserve(stored)
    unknown.status = "completed"
    billed, _ = await reserve(
        stored, "billed", request_hash="billed", reservation_usd="2", metadata={}
    )
    billed.actual_usd = Decimal("1")
    await reserve(stored, "priced", request_hash="priced", reservation_usd="2", metadata={})
    summary = await ledger.budget_summary(stored.session, stored.workspace, stored.project.id)
    assert summary["knownActualUsd"] == "1"
    assert summary["knownExposureUsd"] == "3"
    assert summary["unknownEstimateAttemptCount"] == 1
    assert summary["estimatedUsd"] is summary["reservedUsd"] is summary["exposureUsd"] is None
    assert summary["remainingUsd"] is None
    presented = ledger.present_attempt(unknown)
    assert presented["estimatedUsd"] is presented["reservedUsd"] is None
    assert presented["actualUsd"] is None and presented["estimateStatus"] == "unknown"


@pytest.mark.asyncio
@pytest.mark.parametrize("stage", ["image", "video"])
async def test_unlimited_generation_records_unknown_estimate_without_price_configuration(
    stored_ledger, monkeypatch, stage,
):
    stored = stored_ledger
    monkeypatch.delenv(f"SMART_REMAKE_P0_MAX_{stage.upper()}_USD", raising=False)

    async def allowed(*args):
        return None

    monkeypatch.setattr(generation_budget, "require_generation_policy", allowed)
    repair = SimpleNamespace(
        repository=SimpleNamespace(session=stored.session), workspace_id=stored.workspace,
    )
    operation = SimpleNamespace(id=uuid4(), result_json={"kind": "initial"})
    attempt, created = await generation_budget.reserve_generation_attempt(
        repair, stored.project, operation, slot=stage, request_hash=stage,
        stage=stage, provider="kie" if stage == "video" else "openai", model="fixture", profile={},
    )
    assert created and attempt.actual_usd is None and attempt.estimated_usd == 0
    assert attempt.metadata_json["costEstimate"]["status"] == "unknown"
    monkeypatch.setenv(f"SMART_REMAKE_P0_MAX_{stage.upper()}_USD", "2")
    replay, created = await generation_budget.reserve_generation_attempt(
        repair, stored.project, operation, slot=stage, request_hash=stage,
        stage=stage, provider="kie" if stage == "video" else "openai", model="fixture", profile={},
    )
    assert not created and replay is attempt and len(stored.rows) == 1
    assert replay.estimated_usd == 0 and replay.metadata_json["costEstimate"]["status"] == "unknown"


@pytest.mark.asyncio
@pytest.mark.parametrize("stage", ["analysis", "inspection"])
async def test_unlimited_gemini_replay_after_price_configuration_never_calls_again(
    stored_ledger, monkeypatch, stage,
):
    stored = stored_ledger
    env = f"SMART_REMAKE_P0_MAX_{stage.upper()}_USD"
    monkeypatch.delenv(env, raising=False)
    calls = []

    class Client:
        async def generate_json(self, **kwargs):
            calls.append(kwargs)
            return {"observed": True}

    client = budgeted_analysis.LedgerGeminiClient(
        stored.session, stored.workspace, stored.project.id, uuid4(), None,
        stage=stage, client=Client(),
    )

    async def project():
        return stored.project

    async def preflight(binding):
        return stored.project

    monkeypatch.setattr(client, "_project", project)
    monkeypatch.setattr(client, "_preflight", preflight)
    first = await client.generate_json(system_instruction="system", prompt="read owned media")
    monkeypatch.setenv(env, "1.50")
    second = await client.generate_json(system_instruction="system", prompt="read owned media")
    assert first == second == {"observed": True}
    assert len(calls) == len(stored.rows) == 1
    assert stored.rows[0].actual_usd is None
    assert stored.rows[0].metadata_json["costEstimate"]["status"] == "unknown"
