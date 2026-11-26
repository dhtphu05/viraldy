from __future__ import annotations

import asyncio
import json
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from testcontainers.postgres import PostgresContainer

from alembic import command
from alembic.config import Config
from viraldy.modules.identity.models import UserModel
from viraldy.modules.smart_remake.budget_ledger import budget_summary, list_attempts
from viraldy.modules.smart_remake.budgeted_analysis import LedgerGeminiClient, inspection_invoke
from viraldy.modules.smart_remake.models import SmartRemakeProjectModel
from viraldy.modules.workspaces.models import WorkspaceModel
from viraldy.platform.config.settings import get_settings
from viraldy.shared.errors.base import AppError, ConflictError


@pytest.fixture
def analysis_database(monkeypatch):
    monkeypatch.setenv("SMART_REMAKE_P0_MAX_ANALYSIS_USD", "0.50")
    monkeypatch.setenv("SMART_REMAKE_P0_MAX_INSPECTION_USD", "0.10")
    monkeypatch.setenv("GEMINI_API_KEY", "fixture-key")
    with PostgresContainer("postgres:16.6-alpine") as postgres:
        sync_url = postgres.get_connection_url().replace(
            "postgresql+psycopg2", "postgresql+psycopg"
        )
        url = sync_url.replace("postgresql+psycopg", "postgresql+asyncpg")
        monkeypatch.setenv("DATABASE_SYNC_URL", sync_url)
        monkeypatch.setenv("DATABASE_URL", url)
        get_settings.cache_clear()
        try:
            command.upgrade(Config("alembic.ini"), "head")
            yield url
        finally:
            get_settings.cache_clear()


@pytest.mark.parametrize("trusted_tls_witness", [False, True])
def test_analysis_and_inspection_ledger_replay_and_ambiguity(
    analysis_database, monkeypatch, trusted_tls_witness
):
    asyncio.run(_exercise(analysis_database, monkeypatch, trusted_tls_witness))


@pytest.mark.parametrize("boundary", ["reserve_attempt", "mark_submitted"])
def test_revocation_during_budget_preflight_makes_zero_http_calls(
    analysis_database, monkeypatch, boundary
):
    asyncio.run(_exercise_revocation_barrier(analysis_database, monkeypatch, boundary))


async def _exercise_revocation_barrier(url, monkeypatch, boundary):
    from viraldy.modules.smart_remake import budgeted_analysis

    engine = create_async_engine(url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    user, workspace, project = uuid4(), uuid4(), uuid4()
    rights = {"declared": True, "scope": "pilot", "basis": "owned", "evidenceNote": "owned"}
    context = {
        "p0": {
            "inputHash": "owned",
            "assets": {
                "source": {"storageKey": "private/source"},
                "product": {"storageKey": "private/product"},
            },
            "rights": {"source": rights, "product": rights, "providerDisclosureAcknowledged": True},
            "budgetPolicy": {"capUsd": "10", "maxAttempts": 20, "maxDurationSeconds": 3600},
        }
    }
    calls, entered, release = [], asyncio.Event(), asyncio.Event()

    class NeverHTTP:
        async def generate_json(self, **kwargs):
            calls.append("HTTP")
            return {"bad": "called after revocation"}

    original = getattr(budgeted_analysis, boundary)

    async def paused(*args, **kwargs):
        result = await original(*args, **kwargs)
        entered.set()
        await release.wait()
        return result

    monkeypatch.setattr(budgeted_analysis, boundary, paused)
    try:
        async with factory() as session:
            session.add(UserModel(id=user, external_auth_id=str(user), email="race@test.example"))
            await session.flush()
            session.add(
                WorkspaceModel(
                    id=workspace, name="race", slug=str(workspace), created_by_user_id=user
                )
            )
            await session.flush()
            session.add(
                SmartRemakeProjectModel(
                    id=project,
                    workspace_id=workspace,
                    revision=1,
                    state_json={},
                    context_json=context,
                )
            )
            await session.commit()

            async def revoke():
                await entered.wait()
                async with factory() as other:
                    row = (
                        await other.execute(
                            select(SmartRemakeProjectModel).where(
                                SmartRemakeProjectModel.id == project
                            )
                        )
                    ).scalar_one()
                    p0 = row.context_json["p0"]
                    row.context_json = {
                        "p0": {
                            **p0,
                            "rights": {**p0["rights"], "source": {**rights, "revoked": True}},
                        }
                    }
                    await other.commit()
                release.set()

            client = LedgerGeminiClient(
                session, workspace, project, uuid4(), user, client=NeverHTTP()
            )
            result, _ = await asyncio.gather(
                client.generate_json(system_instruction="s", prompt="p"),
                revoke(),
                return_exceptions=True,
            )
            assert isinstance(result, AppError) and result.code == "SMART_REMAKE_RIGHTS_REQUIRED"
            assert calls == []
            rows = await list_attempts(session, workspace, project)
            assert len(rows) == 1 and rows[0]["status"] == "failed"
            assert rows[0]["actualUsd"] == "0.00000000"
    finally:
        await engine.dispose()


async def _exercise(url, monkeypatch, trusted_tls_witness):
    from viraldy.modules.smart_remake import provider_execution

    # Exercise serialization with a trusted observer witness, entirely offline.
    # The default MockTransport/no-TLS case stays unverified in the other case.
    monkeypatch.setattr(
        provider_execution, "_verified_tls", lambda response, host: trusted_tls_witness
    )
    engine = create_async_engine(url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    user, workspace, project, operation = uuid4(), uuid4(), uuid4(), uuid4()
    rights = {"declared": True, "scope": "pilot", "basis": "owned", "evidenceNote": "owned"}
    context = {
        "p0": {
            "inputHash": "owned",
            "assets": {
                "source": {"storageKey": "private/source"},
                "product": {"storageKey": "private/product"},
            },
            "rights": {"source": rights, "product": rights, "providerDisclosureAcknowledged": True},
            "budgetPolicy": {"capUsd": "10", "maxAttempts": 20, "maxDurationSeconds": 3600},
        }
    }
    calls, outcomes = [], []

    class HTTP:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, url, **kwargs):
            calls.append(kwargs["json"])
            assert not active_session.in_transaction()
            outcome = outcomes.pop(0)
            if isinstance(outcome, Exception):
                raise outcome
            if isinstance(outcome, tuple) and outcome[0] == "status":
                return httpx.Response(outcome[1], request=httpx.Request("POST", url))
            content = outcome[1] if isinstance(outcome, tuple) else json.dumps(outcome)
            return httpx.Response(
                200,
                request=httpx.Request("POST", url),
                json={
                    "candidates": [{"content": {"parts": [{"text": content}]}}],
                    "usageMetadata": {"promptTokenCount": 5, "candidatesTokenCount": 8},
                    "responseId": f"fixture-{len(calls)}",
                },
            )

    monkeypatch.setattr(httpx, "AsyncClient", HTTP)
    try:
        async with factory() as session:
            session.add(
                UserModel(id=user, external_auth_id=str(user), email="analysis@test.example")
            )
            await session.flush()
            session.add(
                WorkspaceModel(
                    id=workspace, name="analysis", slug=str(workspace), created_by_user_id=user
                )
            )
            await session.flush()
            session.add(
                SmartRemakeProjectModel(
                    id=project,
                    workspace_id=workspace,
                    revision=1,
                    state_json={},
                    context_json=context,
                )
            )
            await session.commit()
            active_session = session
            client = LedgerGeminiClient(session, workspace, project, operation, user)
            outcomes.append({"scene": "analysis"})
            args = {
                "system_instruction": "system",
                "prompt": "analyze source",
                "media": [{"bytes": b"source", "mime_type": "video/mp4"}],
            }
            assert await client.generate_json(**args) == {"scene": "analysis"}
            assert len(calls) == 1
            # Same instance and a restarted compiler replay without another HTTP request.
            assert await client.generate_json(**args) == {"scene": "analysis"}
            restarted = LedgerGeminiClient(session, workspace, project, operation, user)
            assert await restarted.generate_json(**args) == {"scene": "analysis"}
            outcomes.append({"product": "locked"})
            assert await client.generate_json(system_instruction="product", prompt="lock") == {
                "product": "locked"
            }
            rows = await list_attempts(session, workspace, project)
            assert len(rows) == 2
            assert rows[0]["receipt"]["requestId"] == "fixture-1"
            assert rows[0]["usage"]["promptTokenCount"] == 5
            assert rows[0]["actualUsd"] is None
            assert (
                provider_execution.validated_execution_evidence(rows[0]) is not None
            ) is trusted_tls_witness
            summary = await budget_summary(session, workspace, project)
            assert summary["policy"]["startedAt"]
            assert summary["exposureUsd"] == "1.00000000"
            outcomes.append(httpx.ReadTimeout("secret must not escape"))
            with pytest.raises(AppError) as uncertain:
                await client.generate_json(system_instruction="system", prompt="timeout")
            assert uncertain.value.code == "SMART_REMAKE_MODEL_ATTEMPT_UNCERTAIN"
            with pytest.raises(ConflictError):
                await client.generate_json(system_instruction="system", prompt="timeout")
            with pytest.raises(ConflictError):
                await LedgerGeminiClient(session, workspace, project, uuid4(), user).generate_json(
                    system_instruction="system", prompt="timeout"
                )
            assert len(calls) == 3
            rows = await list_attempts(session, workspace, project)
            assert rows[2]["status"] == "unknown"
            assert "executionEvidence" not in rows[2]["receipt"]
            assert "secret" not in json.dumps(rows[2]["error"])
            # Inspector uses a separately counted stage and the same single-call discipline.
            invoke = inspection_invoke(
                session,
                workspace,
                project,
                uuid4(),
                user,
                metadata={"reportContextHash": "manifest"},
            )
            outcomes.append({"findings": []})
            payload = {
                "systemInstruction": "inspect",
                "prompt": "compare",
                "media": [{"bytes": b"frame", "mimeType": "image/png"}],
            }
            assert await invoke(payload) == {"findings": []}
            assert await invoke(payload) == {"findings": []}
            rows = await list_attempts(session, workspace, project)
            assert rows[-1]["stage"] == "inspection"
            assert rows[-1]["purpose"] == "recheck"
            assert rows[-1]["metadata"]["reportContextHash"] == "manifest"
            assert len(calls) == 4
            outcomes.append(("raw", "{bad"))
            with pytest.raises(AppError):
                await client.generate_json(system_instruction="system", prompt="malformed")
            rows = await list_attempts(session, workspace, project)
            assert len(calls) == 5 and rows[-1]["status"] == "unknown"
            assert rows[-1]["usage"]["promptTokenCount"] == 5
            assert rows[-1]["receipt"]["requestId"] == "fixture-5"
            assert (
                provider_execution.validated_execution_evidence(rows[-1]) is not None
            ) is trusted_tls_witness
            outcomes.append(("status", 503))
            with pytest.raises(AppError):
                await client.generate_json(system_instruction="system", prompt="unavailable")
            assert len(calls) == 6
            assert (await list_attempts(session, workspace, project))[-1]["usage"] == {}
            rows = await list_attempts(session, workspace, project)
            assert (
                provider_execution.validated_execution_evidence(rows[-1]) is not None
            ) is trusted_tls_witness
            # A completed receipt with lost cache is never silently resubmitted.
            stored = (
                await session.execute(
                    select(SmartRemakeProjectModel).where(SmartRemakeProjectModel.id == project)
                )
            ).scalar_one()
            p0 = stored.context_json["p0"]
            stored.context_json = {"p0": {**p0, "modelResults": {}}}
            await session.commit()
            with pytest.raises(ConflictError):
                await restarted.generate_json(**args)
            assert len(calls) == 6
            # Rights revocation blocks even cached-result access and makes zero paid calls.
            stored = (
                await session.execute(
                    select(SmartRemakeProjectModel).where(SmartRemakeProjectModel.id == project)
                )
            ).scalar_one()
            p0 = stored.context_json["p0"]
            stored.context_json = {
                "p0": {**p0, "rights": {**p0["rights"], "source": {**rights, "revoked": True}}}
            }
            await session.commit()
            with pytest.raises(AppError) as revoked:
                await LedgerGeminiClient(session, workspace, project, uuid4(), user).generate_json(
                    **args
                )
            assert revoked.value.code == "SMART_REMAKE_RIGHTS_REQUIRED"
            assert len(calls) == 6
    finally:
        await engine.dispose()
