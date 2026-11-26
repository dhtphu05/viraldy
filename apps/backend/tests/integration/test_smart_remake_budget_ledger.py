from __future__ import annotations

import asyncio
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from testcontainers.postgres import PostgresContainer

from alembic import command
from alembic.config import Config
from viraldy.modules.identity.models import UserModel
from viraldy.modules.smart_remake.budget_ledger import (
    budget_summary,
    complete_attempt,
    fail_attempt,
    get_attempt,
    initialize_budget,
    list_attempts,
    mark_submitted,
    reserve_attempt,
    unknown_attempt,
)
from viraldy.modules.smart_remake.budget_models import SmartRemakeAttemptModel
from viraldy.modules.smart_remake.models import SmartRemakeProjectModel
from viraldy.modules.workspaces.models import WorkspaceModel
from viraldy.platform.config.settings import get_settings
from viraldy.shared.errors.base import AppError, ConflictError, NotFoundError


def test_atomic_budget_ledger_and_migration(monkeypatch):
    with PostgresContainer("postgres:16.6-alpine") as postgres:
        sync_url = postgres.get_connection_url().replace(
            "postgresql+psycopg2", "postgresql+psycopg"
        )
        async_url = sync_url.replace("postgresql+psycopg", "postgresql+asyncpg")
        monkeypatch.setenv("DATABASE_SYNC_URL", sync_url)
        monkeypatch.setenv("DATABASE_URL", async_url)
        get_settings.cache_clear()
        try:
            config = Config("alembic.ini")
            command.upgrade(config, "head")
            asyncio.run(_exercise(async_url))
            command.downgrade(config, "0023_smart_remake_scene_repair")
            command.upgrade(config, "head")
        finally:
            get_settings.cache_clear()


async def _exercise(url):
    engine = create_async_engine(url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    user, workspace, project = uuid4(), uuid4(), uuid4()
    policy = {"capUsd": "2", "maxAttempts": 4, "maxDurationSeconds": 3600}
    try:
        async with factory() as session:
            session.add(UserModel(id=user, external_auth_id=str(user), email="budget@test.example"))
            await session.flush()
            session.add(
                WorkspaceModel(
                    id=workspace, name="budget", slug=str(workspace), created_by_user_id=user
                )
            )
            await session.flush()
            session.add(
                SmartRemakeProjectModel(
                    id=project,
                    workspace_id=workspace,
                    revision=1,
                    state_json={"revision": 1},
                    context_json={"p0": {"rights": {"granted": True}}},
                )
            )
            await session.commit()
            await initialize_budget(session, workspace, project, policy)
            with pytest.raises(NotFoundError):
                await budget_summary(session, uuid4(), project)

        async def reserve(key, **kwargs):
            async with factory() as session:
                return await reserve_attempt(
                    session,
                    workspace,
                    project,
                    idempotency_key=key,
                    request_hash=kwargs.pop("request_hash", key),
                    stage="image",
                    reservation_usd="1",
                    actor_id=user,
                    provider="openai",
                    model="image",
                    profile={"quality": "max"},
                    metadata={"inputHash": "abc"},
                    **kwargs,
                )

        results = await asyncio.gather(reserve("one"), reserve("one"))
        assert results[0][0].id == results[1][0].id
        assert sorted(item[1] for item in results) == [False, True]
        one = results[0][0]
        with pytest.raises(ConflictError):
            await reserve("one", request_hash="different")
        two, _ = await reserve("two")
        with pytest.raises(AppError) as exceeded:
            await reserve("three")
        assert exceeded.value.code == "SMART_REMAKE_BUDGET_EXCEEDED"
        async with factory() as session:
            await mark_submitted(session, workspace, project, one.id, provider_task_id="task-one")
            await unknown_attempt(session, workspace, project, one.id, error={"code": "TIMEOUT"})
            summary = await budget_summary(session, workspace, project)
            assert summary["exposureUsd"] == "2.00000000"
            assert summary["actualUsd"] is None
            assert summary["unknownAttemptCount"] == 2
            # A timeout cannot be represented as free, and cannot permit another request.
            replay, created = await reserve("one")
            assert not created and replay.status == "unknown"
            await complete_attempt(
                session,
                workspace,
                project,
                one.id,
                usage={"tokens": 17},
                receipt={"id": "usage-only"},
            )
            summary = await budget_summary(session, workspace, project)
            assert summary["exposureUsd"] == "2.00000000"
            assert summary["actualUsd"] is None
            await complete_attempt(
                session,
                workspace,
                project,
                one.id,
                actual_usd="0.4",
                receipt={"id": "billed-one", "billedUsd": "0.4"},
            )
            await complete_attempt(
                session,
                workspace,
                project,
                one.id,
                actual_usd="0.4",
                receipt={"id": "billed-one", "billedUsd": "0.4"},
            )
            with pytest.raises(ConflictError):
                await complete_attempt(
                    session, workspace, project, one.id, actual_usd="0.5", receipt={"id": "changed"}
                )
            await fail_attempt(
                session,
                workspace,
                project,
                two.id,
                error={"code": "LOCAL_VALIDATION"},
                definitely_not_submitted=True,
            )
            summary = await budget_summary(session, workspace, project)
            assert Decimal(summary["exposureUsd"]) == Decimal("0.4")
            assert Decimal(summary["actualUsd"]) == Decimal("0.4")
            assert summary["unknownAttemptCount"] == 0
            # Shrinking below spent is rejected; attempt quota includes failed and repair work.
            with pytest.raises(AppError):
                await initialize_budget(session, workspace, project, {**policy, "capUsd": "0.2"})
            await initialize_budget(
                session, workspace, project, {**policy, "capUsd": "5", "maxAttempts": 3}
            )
        three, _ = await reserve("three", purpose="repair")
        with pytest.raises(AppError) as quota:
            await reserve("four")
        assert quota.value.code == "SMART_REMAKE_ATTEMPT_LIMIT"
        async with factory() as session:
            await mark_submitted(
                session, workspace, project, three.id, provider_task_id="task-three"
            )
            with pytest.raises(ConflictError):
                await fail_attempt(
                    session, workspace, project, three.id, definitely_not_submitted=True
                )
            await fail_attempt(session, workspace, project, three.id, error={"code": "NETWORK"})
            await fail_attempt(
                session,
                workspace,
                project,
                three.id,
                error={"code": "REMOTE_FAILED"},
                actual_usd="0.25",
                receipt={"billedUsd": "0.25"},
                usage={"credits": 4},
            )
            await fail_attempt(
                session,
                workspace,
                project,
                three.id,
                actual_usd="0.25",
                receipt={"billedUsd": "0.25"},
            )
            with pytest.raises(ConflictError):
                await fail_attempt(
                    session,
                    workspace,
                    project,
                    three.id,
                    actual_usd="0.5",
                    receipt={"billedUsd": "0.5"},
                )
            rows = await list_attempts(session, workspace, project)
            assert len(rows) == 3
            assert rows[0]["actorId"] == str(user)
            assert rows[0]["profile"] == {"quality": "max"}
            assert rows[2]["purpose"] == "repair"
            assert Decimal(rows[2]["actualUsd"]) == Decimal("0.25")
            assert rows[2]["status"] == "failed"
            assert rows[2]["usage"] == {"credits": 4}
            stored = (await session.execute(select(SmartRemakeProjectModel))).scalar_one()
            assert stored.context_json["p0"]["rights"] == {"granted": True}
            # Lock was committed before the API returned, so another transaction proceeds.
            async with factory() as other:
                await other.execute(text("SET LOCAL lock_timeout = '100ms'"))
                await other.execute(select(SmartRemakeProjectModel).with_for_update())
            assert (await session.execute(select(SmartRemakeAttemptModel))).scalars().all()
        await _concurrent_cap_and_validation(factory, workspace, user)
        await _unlimited_cost_history(factory, workspace, user)
        await _generation_preflight_cancellation(factory, workspace, user)
    finally:
        await engine.dispose()


async def _concurrent_cap_and_validation(factory, workspace, user):
    project = uuid4()
    policy = {"capUsd": "1", "maxAttempts": 10, "maxDurationSeconds": 3600}
    async with factory() as session:
        session.add(
            SmartRemakeProjectModel(
                id=project, workspace_id=workspace, revision=1, state_json={}, context_json={}
            )
        )
        await session.commit()
        arguments = dict(
            idempotency_key="unpriced",
            request_hash="request",
            stage="video",
            reservation_usd="1",
            actor_id=user,
            provider="kie",
            model="veo",
        )
        default, created = await reserve_attempt(session, workspace, project, **arguments)
        assert created and default.policy_json["mode"] == "unlimited"
        await fail_attempt(
            session, workspace, project, default.id, definitely_not_submitted=True
        )
        with pytest.raises(AppError):
            await reserve_attempt(session, workspace, project, **{**arguments, "stage": "invalid"})
        await initialize_budget(session, workspace, project, policy)

    async def reserve(key):
        async with factory() as session:
            return await reserve_attempt(
                session, workspace, project, **{**arguments, "idempotency_key": key}
            )

    competing = await asyncio.gather(reserve("left"), reserve("right"), return_exceptions=True)
    accepted = [item for item in competing if isinstance(item, tuple)]
    rejected = [item for item in competing if isinstance(item, AppError)]
    assert len(accepted) == len(rejected) == 1
    assert rejected[0].code == "SMART_REMAKE_BUDGET_EXCEEDED"
    attempt = accepted[0][0]
    async with factory() as session:
        with pytest.raises(NotFoundError):
            await mark_submitted(session, workspace, project, uuid4())
        await mark_submitted(session, workspace, project, attempt.id, provider_task_id="accepted")
        with pytest.raises(ConflictError):
            await mark_submitted(
                session, workspace, project, attempt.id, provider_task_id="changed"
            )
        with pytest.raises(AppError):
            await complete_attempt(session, workspace, project, attempt.id, actual_usd="0")
        await complete_attempt(
            session, workspace, project, attempt.id, actual_usd="0", receipt={"billedUsd": "0"}
        )
        await fail_attempt(session, workspace, project, attempt.id, error={"code": "LATE_FAILURE"})
        assert (await get_attempt(session, workspace, project, attempt.id)).status == "completed"
        await unknown_attempt(session, workspace, project, attempt.id, error={"code": "LATE"})
        stored = (
            await session.execute(
                select(SmartRemakeProjectModel).where(SmartRemakeProjectModel.id == project)
            )
        ).scalar_one()
        p0 = stored.context_json["p0"]
        stored.context_json = {
            "p0": {
                **p0,
                "budgetPolicy": {**p0["budgetPolicy"], "startedAt": "2000-01-01T00:00:00+00:00"},
            }
        }
        await session.commit()
        with pytest.raises(AppError) as expired:
            await reserve_attempt(
                session, workspace, project, **{**arguments, "idempotency_key": "expired"}
            )
        assert expired.value.code == "SMART_REMAKE_BUDGET_EXPIRED"


async def _unlimited_cost_history(factory, workspace, user):
    project = uuid4()
    async with factory() as session:
        session.add(SmartRemakeProjectModel(
            id=project, workspace_id=workspace, revision=1, state_json={}, context_json={
                "p0": {"budgetPolicy": {
                    "mode": "unlimited", "capUsd": "0.01", "maxAttempts": 1,
                    "maxDurationSeconds": 1, "startedAt": "2000-01-01T00:00:00+00:00",
                }},
            },
        ))
        await session.commit()
    unknown = {"costEstimate": {"status": "unknown", "reason": "server_price_unconfigured"}}

    async def reserve(key, **overrides):
        async with factory() as session:
            arguments = {
                "idempotency_key": key, "request_hash": "same-owned-input", "stage": "video",
                "reservation_usd": "0", "actor_id": user, "provider": "kie", "model": "veo",
                "metadata": unknown,
            }
            return await reserve_attempt(session, workspace, project, **{**arguments, **overrides})

    concurrent = await asyncio.gather(reserve("same-key"), reserve("same-key"))
    assert concurrent[0][0].id == concurrent[1][0].id
    assert sorted(item[1] for item in concurrent) == [False, True]
    first = concurrent[0][0]
    assert first.policy_json == {
        "mode": "unlimited", "startedAt": "2000-01-01T00:00:00+00:00",
    }
    replay, created = await reserve("same-key", reservation_usd="3.25", metadata={})
    assert not created and replay.estimated_usd == 0 and replay.metadata_json == unknown
    with pytest.raises(ConflictError):
        await reserve("same-key", request_hash="changed-media")
    async with factory() as session:
        await mark_submitted(session, workspace, project, first.id, provider_task_id="original")
        await unknown_attempt(session, workspace, project, first.id, error={"code": "TIMEOUT"})
    with pytest.raises(ConflictError) as uncertain:
        await reserve("replacement")
    assert uncertain.value.code == "SMART_REMAKE_ATTEMPT_RECONCILIATION_REQUIRED"
    async with factory() as session:
        await complete_attempt(
            session, workspace, project, first.id, receipt={"taskId": "original"}
        )
    second, created = await reserve("explicit-new")
    assert created and second.id != first.id
    async with factory() as session:
        summary = await budget_summary(session, workspace, project)
        assert summary["attemptCount"] == summary["unknownEstimateAttemptCount"] == 2
        assert summary["exposureUsd"] is summary["reservedUsd"] is summary["remainingUsd"] is None
        assert Decimal(summary["knownExposureUsd"]) == 0
        rows = await list_attempts(session, workspace, project)
        assert all(row["estimatedUsd"] is None and row["actualUsd"] is None for row in rows)
        with pytest.raises(AppError) as unbounded_cost:
            await initialize_budget(session, workspace, project, {
                "capUsd": "10", "maxAttempts": 10, "maxDurationSeconds": 3600,
            })
        assert unbounded_cost.value.code == "SMART_REMAKE_BUDGET_BELOW_EXPOSURE"
        await complete_attempt(
            session, workspace, project, first.id, actual_usd="0.2", receipt={"billedUsd": "0.2"},
        )
        await fail_attempt(session, workspace, project, second.id, definitely_not_submitted=True)
        settled = await budget_summary(session, workspace, project)
        assert Decimal(settled["exposureUsd"]) == Decimal(settled["actualUsd"]) == Decimal("0.2")
        assert settled["estimatedUsd"] is None and settled["unknownAttemptCount"] == 0


async def _generation_preflight_cancellation(factory, workspace, user):
    project = uuid4()
    async with factory() as session:
        session.add(
            SmartRemakeProjectModel(
                id=project, workspace_id=workspace, revision=1, state_json={}, context_json={}
            )
        )
        await session.commit()
        await initialize_budget(
            session,
            workspace,
            project,
            {"capUsd": "20", "maxAttempts": 20, "maxDurationSeconds": 3600},
        )
        for provider, stage in (("openai", "image"), ("kie", "video")):

            async def reserve(key, request_provider=provider, request_stage=stage):
                return await reserve_attempt(
                    session,
                    workspace,
                    project,
                    idempotency_key=f"{request_provider}:{key}",
                    request_hash=request_provider + key,
                    stage=request_stage,
                    reservation_usd="1",
                    actor_id=user,
                    provider=request_provider,
                    model="fixture-model",
                )

            row, _ = await reserve("preflight")
            await mark_submitted(session, workspace, project, row.id)
            cancelled = await fail_attempt(
                session,
                workspace,
                project,
                row.id,
                definitely_not_submitted=True,
                preflight_rejected=True,
                error={"code": "RIGHTS_REVOKED", "phase": "preflight", "httpAttempted": False},
            )
            assert cancelled.status == "failed" and cancelled.actual_usd == Decimal(0)
            cancelled = await fail_attempt(
                session,
                workspace,
                project,
                cancelled.id,
                definitely_not_submitted=True,
                preflight_rejected=True,
                error={"code": "RIGHTS_REVOKED", "phase": "preflight", "httpAttempted": False},
            )
            assert cancelled.status == "failed" and cancelled.actual_usd == Decimal(0)
            # A known provider task/receipt cannot be cleared using the local-only flag.
            for witness in (
                {"provider_task_id": "retained-task"},
                {"receipt": {"requestId": "remote"}},
            ):
                row, _ = await reserve(str(witness))
                await mark_submitted(session, workspace, project, row.id, **witness)
                with pytest.raises(ConflictError):
                    await fail_attempt(
                        session,
                        workspace,
                        project,
                        row.id,
                        definitely_not_submitted=True,
                        preflight_rejected=True,
                    )
            # Incoming receipt or usage contradicts proof that HTTP never started.
            for witness in ({"receipt": {"requestId": "remote"}}, {"usage": {"tokens": 5}}):
                row, _ = await reserve("incoming" + str(witness))
                await mark_submitted(session, workspace, project, row.id)
                with pytest.raises(ConflictError):
                    await fail_attempt(
                        session,
                        workspace,
                        project,
                        row.id,
                        definitely_not_submitted=True,
                        preflight_rejected=True,
                        **witness,
                    )
