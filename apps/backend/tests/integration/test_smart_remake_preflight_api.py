"""Real workspace authorization and PostgreSQL read-only preflight requests."""

from __future__ import annotations

import copy
import importlib
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from tests.integration.test_smart_remake_kie_workflow import kie_database_url
from tests.unit.test_smart_remake_preflight import project
from viraldy.api.dependencies.auth import get_current_user
from viraldy.api.middleware.errors import app_error_handler, validation_error_handler
from viraldy.modules.identity.models import UserModel
from viraldy.modules.smart_remake import intake_router
from viraldy.modules.smart_remake.budget_models import SmartRemakeAttemptModel
from viraldy.modules.smart_remake.models import SmartRemakeOperationModel, SmartRemakeProjectModel
from viraldy.modules.workspaces.models import WorkspaceMemberModel, WorkspaceModel
from viraldy.platform.config.settings import get_settings
from viraldy.platform.database.session import get_async_session
from viraldy.shared.errors.base import AppError

router = importlib.import_module("viraldy.modules.smart_remake.router")


@pytest.fixture(scope="module")
def preflight_database_url():
    yield from kie_database_url.__wrapped__()


@pytest.fixture
async def api(preflight_database_url, monkeypatch):
    monkeypatch.setenv("SMART_REMAKE_ENABLED", "true")
    monkeypatch.setenv("SMART_REMAKE_P0_MAX_ANALYSIS_USD", "0.20000001")
    monkeypatch.setenv("SMART_REMAKE_P0_MAX_IMAGE_USD", "0.5")
    monkeypatch.setenv("SMART_REMAKE_P0_MAX_VIDEO_USD", "1")
    monkeypatch.setenv("SMART_REMAKE_P0_MAX_INSPECTION_USD", "0.1")
    engine = create_async_engine(preflight_database_url)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    actor, workspace, foreign, viewer = uuid4(), uuid4(), uuid4(), uuid4()
    row = project()
    row.context_json["p0"]["budgetPolicy"]["startedAt"] = datetime.now(UTC).isoformat()
    async with sessions() as session:
        session.add(
            UserModel(id=actor, external_auth_id=str(actor), email=f"{actor}@preflight.example")
        )
        await session.flush()
        for identity, role in [(workspace, "owner"), (foreign, "owner"), (viewer, "viewer")]:
            session.add(
                WorkspaceModel(
                    id=identity, name="Preflight", slug=str(identity), created_by_user_id=actor
                )
            )
            await session.flush()
            session.add(WorkspaceMemberModel(workspace_id=identity, user_id=actor, role=role))
        session.add(
            SmartRemakeProjectModel(
                id=row.id,
                workspace_id=workspace,
                revision=row.revision,
                state_json=row.state_json,
                context_json=row.context_json,
            )
        )
        await session.commit()

    storage = Mock(side_effect=AssertionError("Preflight must not construct private storage."))
    monkeypatch.setattr(intake_router, "S3StorageAdapter", storage)
    settings = get_settings().model_copy(update={"ai_mode": "live"})
    app = FastAPI()
    app.include_router(router.router)
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)

    async def db_override():
        async with sessions() as session:
            # PostgreSQL rejects accidental writes, including reservations.
            await session.execute(text("SET TRANSACTION READ ONLY"))
            yield session

    app.dependency_overrides[get_async_session] = db_override
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=actor)
    app.dependency_overrides[get_settings] = lambda: settings
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        try:
            yield SimpleNamespace(
                client=client,
                workspace=workspace,
                foreign=foreign,
                viewer=viewer,
                project=row,
                sessions=sessions,
                storage=storage,
                app=app,
            )
        finally:
            await engine.dispose()


def path(workspace):
    return f"/workspaces/{workspace}/smart-remake/preflight"


async def test_preflight_new_analysis_is_read_only_and_rounds_policy_up_to_six_decimals(api):
    response = await api.client.post(
        path(api.workspace), json={"action": "analyze", "targetDuration": 16}
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["calls"]["analysis"] == data["calls"]["total"] == 4
    assert data["budget"]["additionalReservationUsd"] == "0.80000004"
    assert data["budget"]["minimumCapUsd"] == "0.800001"
    assert Decimal(data["budget"]["recommended"]["capUsd"]) >= Decimal("0.80000004")
    assert data["budget"]["minimumMaxAttempts"] == 4
    assert data["budget"]["recommended"]["maxAttempts"] == 4
    assert data["scope"]["targetDuration"] == 16
    assert not data["blockers"] and "projectId" not in data
    api.storage.assert_not_called()


async def test_preflight_existing_plan_uses_server_scope_and_keeps_retained_rows_unchanged(api):
    before = copy.deepcopy(api.project.context_json)
    response = await api.client.post(
        path(api.workspace),
        json={
            "action": "render",
            "projectId": str(api.project.id),
            "expectedRevision": 4,
            "targetDuration": 8,
            "requiresCharacter": True,
        },
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["scope"]["targetDuration"] == 16
    assert (data["calls"]["video"], data["calls"]["image"]) == (2, 3)
    async with api.sessions() as session:
        stored = await session.get(SmartRemakeProjectModel, api.project.id)
        assert stored.context_json == before
        assert stored.revision == 4
        for table in (SmartRemakeAttemptModel, SmartRemakeOperationModel):
            assert (
                await session.scalar(
                    select(func.count())
                    .select_from(table)
                    .where(table.project_id == api.project.id),
                )
                == 0
            )
    api.storage.assert_not_called()


async def test_preflight_rejects_viewer_foreign_workspace_and_client_cost_fields(api):
    for workspace in (api.viewer, uuid4()):
        response = await api.client.post(
            path(workspace), json={"action": "analyze", "targetDuration": 8}
        )
        assert response.status_code == 403
    response = await api.client.post(
        path(api.foreign),
        json={"action": "render", "projectId": str(api.project.id), "expectedRevision": 4},
    )
    assert response.status_code == 404
    response = await api.client.post(
        path(api.workspace),
        json={"action": "analyze", "targetDuration": 8, "reservationUsd": "0.01"},
    )
    assert response.status_code == 422


async def test_preflight_completed_unknown_fee_remains_exposure_and_pending_is_reconciled(api):
    attempt_id = uuid4()
    async with api.sessions() as session:
        session.add(
            SmartRemakeAttemptModel(
                id=attempt_id,
                project_id=api.project.id,
                workspace_id=api.workspace,
                idempotency_key="existing",
                request_hash="a" * 64,
                stage="video",
                purpose="initial",
                status="completed",
                provider="kie",
                model="veo3_lite",
                estimated_usd=Decimal("1.25"),
                actual_usd=None,
            )
        )
        await session.commit()
    payload = {"action": "reanalyze", "projectId": str(api.project.id), "expectedRevision": 4}
    first = (await api.client.post(path(api.workspace), json=payload)).json()["data"]
    assert not first["blockers"]
    assert first["budget"]["reservedUsd"] == "1.25000000"
    assert first["budget"]["exposureUsd"] == "1.25000000"
    assert first["calls"]["analysis"] == first["calls"]["total"] == 4
    assert first["budget"]["additionalReservationUsd"] == "0.80000004"
    assert first["budget"]["minimumCapUsd"] == "2.050001"
    assert first["budget"]["minimumMaxAttempts"] == 5
    assert first["budget"]["recommended"]["maxAttempts"] == 5
    async with api.sessions() as session:
        session.add(
            SmartRemakeOperationModel(
                project_id=api.project.id,
                idempotency_key="in-progress",
                request_hash="b" * 64,
                status="running",
                result_json={},
            )
        )
        await session.commit()
    second = (await api.client.post(path(api.workspace), json=payload)).json()["data"]
    assert second["contextHash"] != first["contextHash"]
    assert any(item["action"] == "reconcile" for item in second["blockers"])


async def test_missing_cost_configuration_returns_explicit_null_budget(api, monkeypatch):
    monkeypatch.delenv("SMART_REMAKE_P0_MAX_ANALYSIS_USD")
    response = await api.client.post(
        path(api.workspace), json={"action": "analyze", "targetDuration": 8}
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["budget"] is None
    assert data["blockers"][0]["code"] == "SMART_REMAKE_COST_BOUND_REQUIRED"
