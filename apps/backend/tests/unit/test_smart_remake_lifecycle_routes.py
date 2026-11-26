"""Lifecycle HTTP routing keeps workspace authorization and actor identity."""

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from httpx import ASGITransport, AsyncClient

from viraldy.api.dependencies.auth import get_current_user
from viraldy.api.middleware.errors import app_error_handler, validation_error_handler
from viraldy.modules.smart_remake import lifecycle_router as module
from viraldy.platform.config.settings import get_settings
from viraldy.platform.database.session import get_async_session
from viraldy.shared.errors.base import AppError, ForbiddenError


@pytest.fixture
async def routes(monkeypatch):
    actor, workspace, project = uuid4(), uuid4(), uuid4()
    db, settings = object(), SimpleNamespace(ai_mode="live")
    repair = SimpleNamespace(repository=object(), media=object(), get=AsyncMock(return_value={}))
    operation = SimpleNamespace(id=uuid4(), status="running")
    inspector = SimpleNamespace(
        queue=AsyncMock(return_value=(SimpleNamespace(id=project), operation, True)),
        review=AsyncMock(return_value={"decision": "accept", "operationId": "review-operation"}),
    )
    actions = SimpleNamespace(
        **{
            name: AsyncMock(return_value={"status": "completed"})
            for name in ("approve", "export", "restore", "delete", "provenance")
        }
    )
    authorize, permission = AsyncMock(), AsyncMock()
    queue = AsyncMock(return_value=SimpleNamespace(id=uuid4()))
    monkeypatch.setattr(module, "authorize", authorize)
    monkeypatch.setattr(module, "require_workspace_permission", permission)
    monkeypatch.setattr(module, "service_for", lambda *a: repair)
    monkeypatch.setattr(module, "InspectionService", lambda *a, **k: inspector)
    monkeypatch.setattr(module, "ProjectLifecycleService", lambda *a: actions)
    from viraldy.modules.smart_remake import timeline_service

    monkeypatch.setattr(timeline_service, "_queue", queue)
    app = FastAPI()
    app.include_router(module.router, prefix="/workspaces/{workspace_id}/smart-remake")
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)

    async def session():
        yield db

    app.dependency_overrides[get_async_session] = session
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=actor)
    app.dependency_overrides[get_settings] = lambda: settings
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield SimpleNamespace(
            client=client,
            actor=actor,
            workspace=workspace,
            project=project,
            base=f"/workspaces/{workspace}/smart-remake/projects/{project}",
            inspector=inspector,
            actions=actions,
            operation=operation,
            authorize=authorize,
            settings=settings,
            permission=permission,
            queue=queue,
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path,method,extra",
    [
        ("approvals", "approve", {"assemblyId": "assembly", "reportId": "report"}),
        ("exports", "export", {"assemblyId": "assembly", "approvalId": "approval"}),
        ("restore", "restore", {"assemblyId": "assembly"}),
        ("deletions", "delete", {"reason": "Stop using owned assets"}),
    ],
)
async def test_release_http_binds_actor_and_revision(routes, path, method, extra):
    response = await routes.client.post(
        f"{routes.base}/{path}",
        json={
            "expectedRevision": 3,
            "idempotencyKey": f"{path}-once",
            **extra,
        },
    )
    assert response.status_code == 200
    routes.authorize.assert_awaited_once()
    called = getattr(routes.actions, method).await_args.args
    assert called[:2] == (routes.project, routes.actor)
    assert called[2].expectedRevision == 3


@pytest.mark.asyncio
async def test_inspection_http_dispatches_only_durable_running_operation(routes):
    payload = {
        "expectedRevision": 3,
        "idempotencyKey": "inspect",
        "subject": {"kind": "assembly", "assemblyId": "assembly"},
    }
    response = await routes.client.post(f"{routes.base}/inspections", json=payload)
    assert response.status_code == 200
    assert response.json()["data"]["processingJobId"]
    routes.queue.assert_awaited_once()
    assert routes.queue.await_args.args[-1] == "smart_remake_inspect"
    assert routes.inspector.queue.await_args.args[:2] == (routes.project, routes.actor)
    routes.operation.status = "completed"
    routes.queue.reset_mock()
    response = await routes.client.post(f"{routes.base}/inspections", json=payload)
    assert response.json()["data"]["processingJobId"] is None
    routes.queue.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["fixture", "mock", " FIXTURE "])
async def test_fixture_inspection_cannot_queue_a_paid_worker(routes, mode):
    routes.settings.ai_mode = mode
    response = await routes.client.post(
        f"{routes.base}/inspections",
        json={
            "expectedRevision": 3,
            "idempotencyKey": "inspect",
            "subject": {"kind": "assembly", "assemblyId": "assembly"},
        },
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "SMART_REMAKE_FIXTURE_MODE"
    routes.inspector.queue.assert_not_awaited()
    routes.queue.assert_not_awaited()


@pytest.mark.asyncio
async def test_inspection_review_http_passes_human_reason(routes):
    response = await routes.client.post(
        f"{routes.base}/inspection-reviews",
        json={
            "expectedRevision": 3,
            "idempotencyKey": "review",
            "reportId": "r",
            "findingId": "f",
            "decision": "accept",
            "reason": "Reviewed sampled limitation",
        },
    )
    assert response.status_code == 200
    assert routes.inspector.review.await_args.args[2].reason == "Reviewed sampled limitation"


@pytest.mark.asyncio
async def test_provenance_uses_read_permission(routes):
    response = await routes.client.get(f"{routes.base}/provenance")
    assert response.status_code == 200
    routes.permission.assert_awaited_once()
    routes.authorize.assert_not_awaited()
    routes.actions.provenance.assert_awaited_once_with(routes.project)


@pytest.mark.asyncio
async def test_authorization_blocks_action_and_strict_body_blocks_forgery(routes):
    routes.authorize.side_effect = ForbiddenError()
    response = await routes.client.post(
        f"{routes.base}/approvals",
        json={
            "expectedRevision": 3,
            "idempotencyKey": "approve",
            "assemblyId": "a",
            "reportId": "r",
        },
    )
    assert response.status_code == 403
    routes.actions.approve.assert_not_awaited()
    response = await routes.client.post(
        f"{routes.base}/approvals",
        json={
            "expectedRevision": 3,
            "idempotencyKey": "approve",
            "assemblyId": "a",
            "reportId": "r",
            "actorId": "forged-actor",
        },
    )
    assert response.status_code == 422
    assert "forged-actor" not in response.text
