"""Download routes sign only owned retained images after workspace authorization."""

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from tests.unit.test_smart_remake_generated_media import use_r2_image
from tests.unit.test_smart_remake_generation_progress import fixture, image
from viraldy.api.dependencies.auth import get_current_user
from viraldy.api.middleware.errors import app_error_handler
from viraldy.platform.config.settings import get_settings
from viraldy.platform.database.session import get_async_session
from viraldy.shared.errors.base import AppError, ForbiddenError


@pytest.fixture
async def boundary(monkeypatch):
    from viraldy.modules.smart_remake import generation_media_router

    row, operation = fixture()
    asset = use_r2_image(row, operation, image(row, operation, frame_role="opening"))
    repository = SimpleNamespace(
        project=AsyncMock(return_value=row), operation=AsyncMock(return_value=operation)
    )
    media = SimpleNamespace(download_url=AsyncMock(return_value="https://signed.example/original"))
    repair = SimpleNamespace(repository=repository, media=media)
    permission = AsyncMock()
    monkeypatch.setattr(generation_media_router, "require_workspace_permission", permission)
    monkeypatch.setattr(generation_media_router, "service_for", lambda *args: repair)
    app = FastAPI()
    app.include_router(
        generation_media_router.router, prefix="/workspaces/{workspace_id}/smart-remake"
    )
    app.add_exception_handler(AppError, app_error_handler)

    async def session():
        yield SimpleNamespace()

    app.dependency_overrides[get_async_session] = session
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=uuid4())
    app.dependency_overrides[get_settings] = lambda: SimpleNamespace()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield SimpleNamespace(
            client=client,
            row=row,
            operation=operation,
            asset=asset,
            media=media,
            permission=permission,
            repository=repository,
            path=f'/workspaces/{row.workspace_id}/smart-remake/projects/{row.id}/generation/{operation.id}/images/{asset["requestHash"]}/download',
        )


async def test_image_download_refreshes_attachment_url_without_storage_reads(boundary):
    response = await boundary.client.get(boundary.path)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data == {
        "url": "https://signed.example/original",
        "filename": f'smart-remake-opening-{boundary.asset["requestHash"][:12]}.png',
    }
    boundary.media.download_url.assert_awaited_once_with(
        boundary.asset["storageKey"], data["filename"]
    )
    boundary.repository.operation.assert_awaited_once_with(
        boundary.row.workspace_id, boundary.row.id, boundary.operation.id
    )


async def test_workspace_permission_denial_precedes_project_or_storage(boundary):
    boundary.permission.side_effect = ForbiddenError()
    response = await boundary.client.get(boundary.path)
    assert response.status_code == 403
    boundary.repository.project.assert_not_awaited()
    boundary.media.download_url.assert_not_awaited()


@pytest.mark.parametrize(
    "change",
    [
        "foreign_operation",
        "foreign_workspace",
        "unknown_image",
        "stopped",
        "stale",
        "mime",
        "invalid_key",
    ],
)
async def test_download_rejects_unowned_or_invalid_reference(boundary, change):
    if change == "foreign_operation":
        boundary.operation.project_id = uuid4()
    elif change == "foreign_workspace":
        boundary.row.workspace_id = uuid4()
    elif change == "unknown_image":
        boundary.operation.result_json["images"] = {}
    elif change == "stopped":
        boundary.row.context_json["p0"]["status"] = "suspended"
    elif change == "stale":
        boundary.operation.result_json["expectationsHash"] = "0" * 64
    elif change == "mime":
        boundary.asset["mimeType"] = "text/html"
        boundary.operation.result_json["images"]["0"]["mimeType"] = "text/html"
    else:
        boundary.asset["storageKey"] += "?other=secret"
        boundary.operation.result_json["images"]["0"]["storageKey"] = boundary.asset["storageKey"]
    response = await boundary.client.get(boundary.path)
    assert response.status_code in {403, 404}
    boundary.media.download_url.assert_not_awaited()


async def test_download_signing_failure_never_leaks_private_provider_details(boundary):
    boundary.media.download_url.side_effect = RuntimeError("https://private.example/secret-token")
    response = await boundary.client.get(boundary.path)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "SMART_REMAKE_MEDIA_DOWNLOAD_UNAVAILABLE"
    assert "secret-token" not in response.text and "private.example" not in response.text


@pytest.mark.parametrize("mime,extension", [("image/jpeg", "jpg"), ("image/webp", "webp")])
async def test_download_filename_matches_original_retained_image_format(boundary, mime, extension):
    boundary.asset["mimeType"] = mime
    boundary.operation.result_json["images"]["0"]["mimeType"] = mime
    response = await boundary.client.get(boundary.path)
    assert response.status_code == 200
    assert response.json()["data"]["filename"].endswith("." + extension)
