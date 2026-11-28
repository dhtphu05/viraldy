"""HTTP coverage of R2 session authorization and JSON intake budget lifecycle."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from httpx import ASGITransport, AsyncClient

from tests.unit.test_smart_remake_rights import intake_payload
from viraldy.api.dependencies.auth import get_current_user
from viraldy.api.middleware.errors import app_error_handler, validation_error_handler
from viraldy.modules.assets.schemas import UploadSessionResponse
from viraldy.modules.smart_remake import asset_intake_router, asset_upload_router, intake_router
from viraldy.platform.auth.policy import Permission
from viraldy.platform.config.settings import get_settings
from viraldy.platform.database.session import get_async_session
from viraldy.shared.errors.base import AppError, ForbiddenError


@pytest.fixture
async def boundary(monkeypatch):
    workspace, actor, project, asset, version = (uuid4() for _ in range(5))
    db = SimpleNamespace(commit=AsyncMock())
    settings = SimpleNamespace(ai_mode="live", r2_configured=True)
    row = SimpleNamespace(
        id=project, context_json={"p0": {"budgetPolicy": intake_payload().budget.model_dump()}}
    )
    repair = SimpleNamespace(
        repository=SimpleNamespace(project=AsyncMock(return_value=row)),
        media=object(),
        present=AsyncMock(return_value={"id": str(project), "phase": "intake"}),
    )
    permission = AsyncMock()
    create = AsyncMock(return_value=row)
    initialize = AsyncMock()
    upload = AsyncMock(
        return_value=UploadSessionResponse(
            asset_id=asset,
            asset_version_id=version,
            version_number=1,
            upload_url="https://r2.example.test/put",
            upload_method="PUT",
            required_headers={"Content-Type": "video/mp4"},
            expires_at=datetime.now(UTC) + timedelta(minutes=10),
        )
    )
    complete = AsyncMock(return_value=SimpleNamespace(model_dump=lambda **_: {"id": str(asset)}))
    storage = Mock()
    monkeypatch.setattr(intake_router, "require_workspace_permission", permission)
    monkeypatch.setattr(asset_intake_router, "service_for", lambda *args: repair)
    monkeypatch.setattr(asset_intake_router, "create_intake_from_assets", create)
    monkeypatch.setattr(asset_intake_router, "initialize_budget", initialize)
    monkeypatch.setattr(asset_upload_router, "create_upload_session", upload)
    monkeypatch.setattr(asset_upload_router, "complete_upload", complete)
    monkeypatch.setattr(asset_upload_router, "S3StorageAdapter", storage)
    monkeypatch.setenv("SMART_REMAKE_ENABLED", "true")
    app = FastAPI()
    for router in (asset_intake_router.router, asset_upload_router.router):
        app.include_router(router, prefix="/workspaces/{workspace_id}/smart-remake")
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)

    async def session():
        yield db

    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=actor)
    app.dependency_overrides[get_async_session] = session
    app.dependency_overrides[get_settings] = lambda: settings
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield SimpleNamespace(
            client=client,
            workspace=workspace,
            actor=actor,
            project=project,
            asset=asset,
            row=row,
            repair=repair,
            permission=permission,
            create=create,
            initialize=initialize,
            upload=upload,
            complete=complete,
            storage=storage,
            db=db,
            settings=settings,
            base=f"/workspaces/{workspace}/smart-remake",
            body={
                "metadata": intake_payload().model_dump(mode="json"),
                "sourceAssetVersionId": str(uuid4()),
                "productAssetVersionId": str(uuid4()),
            },
            declaration={
                "filename": "source.mp4",
                "declared_mime_type": "video/mp4",
                "declared_size_bytes": 100,
                "role": "reference_video",
            },
        )


async def test_json_intake_binds_actor_and_initializes_budget(boundary):
    response = await boundary.client.post(
        f"{boundary.base}/projects/from-assets", json=boundary.body
    )
    assert response.status_code == 200
    arguments = boundary.create.await_args.args
    assert arguments[3:5] == (boundary.workspace, boundary.actor)
    assert str(arguments[5].sourceAssetVersionId) == boundary.body["sourceAssetVersionId"]
    assert arguments[5].metadata.idempotencyKey == boundary.body["metadata"]["idempotencyKey"]
    boundary.permission.assert_awaited_once()
    assert boundary.permission.await_args.args[1] == Permission.ANALYSIS_RUN
    boundary.initialize.assert_awaited_once()
    assert boundary.repair.repository.project.await_args.kwargs["lock"] is True


async def test_json_intake_replay_keeps_amended_started_budget(boundary):
    boundary.row.context_json["p0"]["budgetPolicy"].update(capUsd="9.00", startedAt="saved")
    response = await boundary.client.post(
        f"{boundary.base}/projects/from-assets", json=boundary.body
    )
    assert response.status_code == 200
    boundary.initialize.assert_not_awaited()
    boundary.db.commit.assert_awaited_once()


@pytest.mark.parametrize("route", ["intake", "session", "complete"])
@pytest.mark.parametrize("denial", ["permission", "feature"])
async def test_authorization_precedes_all_storage_and_service_work(
    boundary, monkeypatch, route, denial
):
    if denial == "permission":
        boundary.permission.side_effect = ForbiddenError()
    else:
        monkeypatch.setenv("SMART_REMAKE_ENABLED", "false")
    path, body = {
        "intake": ("projects/from-assets", boundary.body),
        "session": ("upload-sessions", boundary.declaration),
        "complete": (f"upload-sessions/{boundary.asset}/complete", None),
    }[route]
    response = await boundary.client.post(f"{boundary.base}/{path}", json=body)
    assert response.status_code == (403 if denial == "permission" else 503)
    boundary.create.assert_not_awaited()
    boundary.upload.assert_not_awaited()
    boundary.complete.assert_not_awaited()
    boundary.storage.assert_not_called()


@pytest.mark.parametrize("route", ["intake", "session"])
async def test_request_cannot_supply_storage_keys_or_urls(boundary, route):
    path, body = (
        ("projects/from-assets", boundary.body)
        if route == "intake"
        else ("upload-sessions", boundary.declaration)
    )
    response = await boundary.client.post(
        f"{boundary.base}/{path}", json={**body, "storageKey": "private-sensitive-marker"}
    )
    assert response.status_code == 422
    assert "private-sensitive-marker" not in response.text
    boundary.create.assert_not_awaited()
    boundary.upload.assert_not_awaited()


@pytest.mark.parametrize("route", ["intake", "session", "complete"])
async def test_private_storage_errors_are_sanitized(boundary, route):
    action, path, body = {
        "intake": (boundary.create, "projects/from-assets", boundary.body),
        "session": (boundary.upload, "upload-sessions", boundary.declaration),
        "complete": (boundary.complete, f"upload-sessions/{boundary.asset}/complete", None),
    }[route]
    action.side_effect = OSError("private-sensitive-marker")
    response = await boundary.client.post(f"{boundary.base}/{path}", json=body)
    assert response.status_code == 503
    assert "private-sensitive-marker" not in response.text


async def test_upload_session_and_completion_bind_authenticated_actor(boundary):
    response = await boundary.client.post(
        f"{boundary.base}/upload-sessions", json=boundary.declaration
    )
    assert response.status_code == 201
    assert response.json()["data"]["upload_method"] == "PUT"
    assert boundary.upload.await_args.args[4:6] == (boundary.workspace, boundary.actor)
    response = await boundary.client.post(
        f"{boundary.base}/upload-sessions/{boundary.asset}/complete"
    )
    assert response.status_code == 200
    assert boundary.complete.await_args.args[4:] == (
        boundary.workspace,
        boundary.asset,
        boundary.actor,
    )


@pytest.mark.parametrize("route", ["session", "complete"])
async def test_missing_r2_configuration_fails_before_storage_construction(boundary, route):
    boundary.settings.r2_configured = False
    path, body = (
        ("upload-sessions", boundary.declaration)
        if route == "session"
        else (f"upload-sessions/{boundary.asset}/complete", None)
    )
    response = await boundary.client.post(f"{boundary.base}/{path}", json=body)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "SMART_REMAKE_R2_NOT_CONFIGURED"
    boundary.storage.assert_not_called()
