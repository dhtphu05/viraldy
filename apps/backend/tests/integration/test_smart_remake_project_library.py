"""Saved generated clips and final videos through HTTP and migrated PostgreSQL."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from tests.integration.test_smart_remake_kie_workflow import kie_database_url as _database_url
from viraldy.api.dependencies.auth import get_current_user
from viraldy.api.middleware.errors import app_error_handler, validation_error_handler
from viraldy.modules.identity.models import UserModel
from viraldy.modules.smart_remake import project_library
from viraldy.modules.smart_remake.models import SmartRemakeProjectModel
from viraldy.modules.smart_remake.router import router as smart_remake_router
from viraldy.modules.workspaces.models import WorkspaceMemberModel, WorkspaceModel
from viraldy.platform.auth.current_user import CurrentUser
from viraldy.platform.config.settings import get_settings
from viraldy.platform.database.session import get_async_session
from viraldy.shared.errors.base import AppError


@pytest.fixture(scope="module")
def library_database_url():
    yield from _database_url.__wrapped__()


def _scene(key, index):
    version = str(uuid4())
    return {
        "id": str(uuid4()),
        "index": index,
        "durationSeconds": 8,
        "activeVersionId": version,
        "versions": [{"id": version, "storageKey": key, "frameCount": 192}],
    }


async def _seed_library(session):
    actor, workspace, foreign = uuid4(), uuid4(), uuid4()
    session.add(UserModel(id=actor, external_auth_id=str(actor), email=f"{actor}@example.test"))
    await session.flush()
    for identity in (workspace, foreign):
        session.add(
            WorkspaceModel(
                id=identity,
                name="Saved video integration",
                slug=str(identity),
                created_by_user_id=actor,
            )
        )
    await session.flush()
    session.add(WorkspaceMemberModel(workspace_id=workspace, user_id=actor, role="viewer"))

    def add(scope, name, day, *, final=None, scenes=None, policy=None):
        row = SmartRemakeProjectModel(
            id=uuid4(),
            workspace_id=scope,
            revision=2,
            created_at=datetime(2026, 11, 20, tzinfo=UTC) + timedelta(days=day),
            state_json={
                "schemaVersion": 2,
                "status": "draft" if final is None else "ready",
                "targetDuration": 16,
                "provider": "kie",
                "scenes": scenes or [],
                "finalStorageKey": final,
                "finalVideoUrl": "https://expired.test/output.mp4",
                "downloadUrl": "https://unchecked.test/download.mp4",
            },
            context_json={
                "projectName": name,
                "productKey": f"product/{name}",
                "p0": policy or {"status": "active"},
            },
        )
        session.add(row)
        return row

    raw_keys = [f"workspaces/{workspace}/raw/group-one", f"workspaces/{workspace}/raw/group-two"]
    raw = add(
        workspace,
        "Raw clips",
        2,
        scenes=[
            _scene(raw_keys[0], 0),
            _scene(raw_keys[0], 1),
            _scene(raw_keys[1], 2),
        ],
    )
    final_key = f"workspaces/{workspace}/final/output"
    final_clip = f"workspaces/{workspace}/raw/final-scene"
    final = add(workspace, "Final video", 1, final=final_key, scenes=[_scene(final_clip, 0)])
    add(foreign, "Foreign output", 9, final="foreign/final")
    add(workspace, "Deleted output", 8, final="deleted/final", policy={"status": "deleted"})
    add(
        workspace,
        "Deletion pending",
        7,
        scenes=[_scene("blocked/raw", 0)],
        policy={
            "status": "active",
            "deletion": {"status": "blocked"},
        },
    )
    add(
        workspace,
        "Revoked output",
        6,
        final="revoked/final",
        policy={
            "status": "active",
            "rights": {"source": {"revoked": True}},
        },
    )
    add(workspace, "Empty intake", 5)
    await session.commit()
    return SimpleNamespace(
        actor=actor,
        workspace=workspace,
        foreign=foreign,
        raw=raw,
        raw_keys=raw_keys,
        final=final,
        final_key=final_key,
        final_clip=final_clip,
    )


@pytest.fixture
async def library_api(library_database_url, monkeypatch):
    engine = create_async_engine(library_database_url)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions() as session:
        stored = await _seed_library(session)
    signatures = []

    async def sign(key):
        signatures.append(key)
        return f"https://private.test/{hashlib.sha256(key.encode()).hexdigest()}?signed={len(signatures)}"

    media = SimpleNamespace(url=AsyncMock(side_effect=sign), download_url=AsyncMock())
    monkeypatch.setattr(project_library, "service_for", lambda *args: SimpleNamespace(media=media))
    app = FastAPI()
    app.include_router(smart_remake_router)
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)

    async def session_dependency():
        async with sessions() as session:
            yield session

    app.dependency_overrides[get_async_session] = session_dependency
    app.dependency_overrides[get_settings] = lambda: SimpleNamespace(ai_mode="live")
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        id=stored.actor,
        external_auth_id=str(stored.actor),
        email="viewer@example.test",
        display_name="Saved video viewer",
        status="active",
    )
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield SimpleNamespace(
                client=client,
                stored=stored,
                media=media,
                signatures=signatures,
                base=f"/workspaces/{stored.workspace}/smart-remake/projects",
            )
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_library_http_lists_retained_clips_before_compose_and_final_videos(library_api):
    api, stored = library_api, library_api.stored
    first = await api.client.get(f"{api.base}?limit=1&offset=0")
    assert first.status_code == 200
    data = first.json()["data"]
    assert (data["total"], data["limit"], data["offset"]) == (2, 1, 0)
    raw = data["items"][0]
    assert raw["id"] == str(stored.raw.id) and raw["finalVideoUrl"] == ""
    assert [video["kind"] for video in raw["videos"]] == ["clip", "clip"]
    assert [video["durationSeconds"] for video in raw["videos"]] == [8, 8]
    assert all(video["id"] and video["label"] for video in raw["videos"])
    assert api.signatures.count(stored.raw_keys[0]) == 1
    assert api.signatures.count(stored.raw_keys[1]) == 1
    assert all(video["url"].startswith("https://private.test/") for video in raw["videos"])
    assert "storageKey" not in first.text and "unchecked.test" not in first.text

    second = await api.client.get(f"{api.base}?limit=1&offset=1")
    assert second.status_code == 200
    final = second.json()["data"]["items"][0]
    assert final["id"] == str(stored.final.id)
    assert [video["kind"] for video in final["videos"]] == ["final", "clip"]
    assert final["videos"][0]["durationSeconds"] == 16
    assert final["finalVideoUrl"] == final["videos"][0]["url"]
    assert "downloadUrl" not in final
    assert stored.final_key in api.signatures and stored.final_clip in api.signatures
    api.media.download_url.assert_not_awaited()

    refreshed = await api.client.get(f"{api.base}?limit=1&offset=0")
    refreshed_raw = refreshed.json()["data"]["items"][0]
    assert refreshed_raw["videos"][0]["url"] != raw["videos"][0]["url"]
    end = await api.client.get(f"{api.base}?limit=1&offset=2")
    assert end.json()["data"] == {"items": [], "total": 2, "limit": 1, "offset": 2}


@pytest.mark.asyncio
async def test_library_http_forbids_foreign_workspace_before_signing(library_api):
    api = library_api
    response = await api.client.get(f"/workspaces/{api.stored.foreign}/smart-remake/projects")
    assert response.status_code == 403
    api.media.url.assert_not_awaited()
    api.media.download_url.assert_not_awaited()
