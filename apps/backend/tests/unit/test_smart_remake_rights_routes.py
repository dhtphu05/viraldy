"""HTTP boundaries for owned intake and policy updates, without remote AI work."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from httpx import ASGITransport, AsyncClient

from tests.unit.test_smart_remake_rights import image_upload, intake_payload, source_upload
from viraldy.api.dependencies.auth import get_current_user
from viraldy.api.middleware.errors import app_error_handler, validation_error_handler
from viraldy.modules.smart_remake import intake_router as module
from viraldy.platform.auth.policy import Permission
from viraldy.platform.config.settings import get_settings
from viraldy.platform.database.session import get_async_session
from viraldy.shared.errors.base import AppError, ForbiddenError


@pytest.fixture
async def boundary(monkeypatch):
    actor, workspace, project = uuid4(), uuid4(), uuid4()
    db = SimpleNamespace(commit=AsyncMock())
    row = SimpleNamespace(
        id=project, context_json={"p0": {"budgetPolicy": intake_payload().budget.model_dump()}}
    )
    repair = SimpleNamespace(
        repository=SimpleNamespace(project=AsyncMock(return_value=row)),
        media=object(),
        present=AsyncMock(return_value={"id": str(project), "phase": "intake", "revision": 1}),
    )
    permission = AsyncMock()
    create = AsyncMock(return_value=row)
    initialize = AsyncMock()
    patch = AsyncMock(
        return_value={
            "project": {"id": str(project)},
            "operationId": "metadata-op",
            "status": "completed",
        }
    )
    monkeypatch.setattr(module, "require_workspace_permission", permission)
    monkeypatch.setattr(module, "service_for", lambda *args: repair)
    monkeypatch.setattr(module, "create_intake", create)
    monkeypatch.setattr(module, "initialize_budget", initialize)
    monkeypatch.setattr(module, "patch_metadata", patch)
    monkeypatch.setenv("SMART_REMAKE_ENABLED", "true")
    app = FastAPI()
    app.include_router(module.router, prefix="/workspaces/{workspace_id}/smart-remake")
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)

    async def session_override():
        yield db

    app.dependency_overrides[get_async_session] = session_override
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=actor)
    app.dependency_overrides[get_settings] = lambda: SimpleNamespace(ai_mode="live")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield SimpleNamespace(
            client=client,
            base=f"/workspaces/{workspace}/smart-remake",
            actor=actor,
            workspace=workspace,
            project=project,
            row=row,
            repair=repair,
            db=db,
            permission=permission,
            create=create,
            initialize=initialize,
            patch=patch,
        )


def uploads(character=False):
    files = {
        "referenceVideo": ("source.mp4", source_upload().bytes, "video/mp4"),
        "productImage": ("product.png", image_upload().bytes, "image/png"),
    }
    if character:
        files["characterImage"] = ("character.png", image_upload().bytes, "image/png")
    return files


@pytest.mark.asyncio
async def test_intake_http_multipart_delegates_owned_bytes_actor_and_budget(boundary):
    response = await boundary.client.post(
        f"{boundary.base}/projects",
        data={"metadata": intake_payload().model_dump_json()},
        files=uploads(True),
    )
    assert response.status_code == 200
    assert response.json()["data"]["project"]["phase"] == "intake"
    args = boundary.create.await_args.args
    assert args[2] == boundary.workspace
    assert args[3] == boundary.actor
    assert args[4].budget.capUsd == "5.00"
    assert args[5].bytes == source_upload().bytes
    assert args[6].bytes == image_upload().bytes
    assert args[7].bytes == image_upload().bytes
    boundary.initialize.assert_awaited_once()
    boundary.permission.assert_awaited_once()
    assert boundary.permission.await_args.args[1] == Permission.ANALYSIS_RUN


@pytest.mark.asyncio
async def test_intake_replay_preserves_existing_budget_policy(boundary):
    boundary.row.context_json["p0"]["budgetPolicy"].update(
        capUsd="9.00", startedAt="2026-11-25T00:00:00+00:00"
    )
    response = await boundary.client.post(
        f"{boundary.base}/projects",
        data={"metadata": intake_payload().model_dump_json()},
        files=uploads(),
    )
    assert response.status_code == 200
    boundary.initialize.assert_not_awaited()
    boundary.db.commit.assert_awaited_once()
    assert boundary.create.await_args.args[7] is None
    assert boundary.repair.repository.project.await_args.kwargs["lock"] is True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload", ["broken", "[]", '{"idempotencyKey":"private-sensitive-marker"}']
)
async def test_intake_json_422_does_not_echo_input_values(boundary, payload):
    response = await boundary.client.post(
        f"{boundary.base}/projects", data={"metadata": payload}, files=uploads()
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert "private-sensitive-marker" not in response.text
    boundary.create.assert_not_awaited()


@pytest.mark.asyncio
async def test_intake_requires_real_file_field_names(boundary):
    response = await boundary.client.post(
        f"{boundary.base}/projects", data={"metadata": intake_payload().model_dump_json()}
    )
    assert response.status_code == 422
    boundary.create.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("case,status", [("disabled", 503), ("permission", 403)])
async def test_intake_permission_and_feature_gate_precede_storage(
    boundary, monkeypatch, case, status
):
    if case == "disabled":
        monkeypatch.setenv("SMART_REMAKE_ENABLED", "false")
    else:
        boundary.permission.side_effect = ForbiddenError()
    response = await boundary.client.post(
        f"{boundary.base}/projects",
        data={"metadata": intake_payload().model_dump_json()},
        files=uploads(),
    )
    assert response.status_code == status
    boundary.create.assert_not_awaited()


@pytest.mark.asyncio
async def test_intake_bounded_upload_rejects_before_retention(boundary, monkeypatch):
    monkeypatch.setenv("SMART_REMAKE_MAX_REFERENCE_VIDEO_BYTES", "2")
    response = await boundary.client.post(
        f"{boundary.base}/projects",
        data={"metadata": intake_payload().model_dump_json()},
        files=uploads(),
    )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "SMART_REMAKE_UPLOAD_TOO_LARGE"
    boundary.create.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["requirements", "rights", "budget"])
async def test_metadata_http_patch_delegates_typed_request(boundary, kind):
    payload = {
        "expectedRevision": 1,
        "idempotencyKey": "metadata",
        kind: intake_payload().model_dump(mode="json")[kind],
    }
    response = await boundary.client.patch(
        f"{boundary.base}/projects/{boundary.project}/{kind}", json=payload
    )
    assert response.status_code == 200
    assert response.json()["data"]["operationId"] == "metadata-op"
    assert boundary.patch.await_args.args[:3] == (boundary.repair, boundary.project, boundary.actor)
    assert boundary.patch.await_args.kwargs["kind"] == kind
    assert boundary.patch.await_args.args[3].expectedRevision == 1


@pytest.mark.asyncio
async def test_rights_review_http_is_explicit_and_not_verified_flag(boundary):
    response = await boundary.client.post(
        f"{boundary.base}/projects/{boundary.project}/rights/reviews",
        json={
            "expectedRevision": 1,
            "idempotencyKey": "review",
            "evidenceNote": "Reviewed rights evidence.",
        },
    )
    assert response.status_code == 200
    assert boundary.patch.await_args.kwargs["kind"] == "rights_review"
    rights = intake_payload().rights.model_dump(mode="json")
    rights["product"]["verification"] = {"status": "verified", "private": "sensitive-marker"}
    response = await boundary.client.patch(
        f"{boundary.base}/projects/{boundary.project}/rights",
        json={
            "expectedRevision": 1,
            "idempotencyKey": "forge",
            "rights": rights,
        },
    )
    assert response.status_code == 422
    assert "sensitive-marker" not in response.text


@pytest.mark.asyncio
async def test_intake_retention_failures_are_sanitized(boundary):
    boundary.create.side_effect = OSError("private-sensitive-storage-path")
    response = await boundary.client.post(
        f"{boundary.base}/projects",
        data={"metadata": intake_payload().model_dump_json()},
        files=uploads(),
    )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "SMART_REMAKE_RETENTION_UNAVAILABLE"
    assert "private-sensitive-storage-path" not in response.text
