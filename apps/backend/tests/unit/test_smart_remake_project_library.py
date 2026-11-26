"""Saved Smart Remake videos remain workspace-scoped and use private media URLs."""

import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, event, insert, text
from sqlalchemy.dialects.postgresql import JSONPATH
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session

from viraldy.api.dependencies.auth import get_current_user
from viraldy.api.middleware.errors import app_error_handler, validation_error_handler
from viraldy.modules.smart_remake import project_library as module
from viraldy.modules.smart_remake.models import SmartRemakeProjectModel
from viraldy.platform.auth.policy import Permission
from viraldy.platform.config.settings import get_settings
from viraldy.platform.database.session import get_async_session
from viraldy.shared.errors.base import AppError, ForbiddenError


@compiles(JSONPATH, "sqlite")
def sqlite_jsonpath_type(element, compiler, **kwargs):
    return "TEXT"


def _sqlite_clip_path_exists(value, path):
    assert path == '$.scenes[*].versions[*].storageKey ? (@.type() == "string" && @ != "")'
    state = json.loads(value)
    return any(
        isinstance(version.get("storageKey"), str) and version["storageKey"] != ""
        for scene in state.get("scenes", [])
        for version in scene.get("versions", [])
    )


def test_library_route_is_mounted_under_workspace_router():
    from viraldy.modules.smart_remake.router import router

    app = FastAPI()
    app.include_router(router)
    assert "get" in app.openapi()["paths"]["/workspaces/{workspace_id}/smart-remake/projects"]


@pytest.fixture
def stored(monkeypatch):
    engine = create_engine("sqlite://")

    @event.listens_for(engine, "connect")
    def register_jsonpath(connection, record):
        connection.create_function("jsonb_path_exists", 2, _sqlite_clip_path_exists)

    with engine.begin() as connection:
        # Exercise the actual SQLAlchemy query without requiring a PostgreSQL service.
        connection.execute(
            text(
                "CREATE TABLE smart_remake_projects (id CHAR(32) PRIMARY KEY, "
                "workspace_id CHAR(32), revision INTEGER, state_json JSON, "
                "context_json JSON, created_at DATETIME)"
            )
        )
    session = Session(engine)
    db = SimpleNamespace(
        execute=AsyncMock(side_effect=session.execute), scalar=AsyncMock(side_effect=session.scalar)
    )
    media = SimpleNamespace(
        url=AsyncMock(side_effect=lambda key: f"https://private.test/{key}?fresh=1"),
        download_url=AsyncMock(return_value="https://private.test/download?fresh=1"),
    )

    def service(*args):
        return SimpleNamespace(media=media)

    monkeypatch.setattr(module, "service_for", service)

    def add(workspace, *, created=None, state=None, context=None):
        project_id = uuid4()
        session.execute(
            insert(SmartRemakeProjectModel).values(
                id=project_id,
                workspace_id=workspace,
                revision=2,
                created_at=created or datetime(2026, 11, 26, tzinfo=UTC),
                state_json={
                    "finalStorageKey": f"final/{project_id}",
                    "finalVideoUrl": "https://expired.test/final",
                    "status": "ready",
                    "targetDuration": 8,
                    "provider": "kie",
                    "scenes": [],
                    **(state or {}),
                },
                context_json={
                    "projectName": "Video đã tạo",
                    "productKey": "product/private",
                    **(context or {}),
                },
            )
        )
        session.commit()
        return project_id

    yield SimpleNamespace(db=db, media=media, add=add)
    session.close()
    engine.dispose()


@pytest.mark.asyncio
async def test_library_empty_does_not_require_media_storage(stored, monkeypatch):
    monkeypatch.setattr(module, "service_for", lambda *args: pytest.fail("No media to sign"))
    result = await module.list_project_library(
        stored.db, uuid4(), SimpleNamespace(ai_mode="live"), limit=24, offset=0
    )
    assert result == {"items": [], "total": 0, "limit": 24, "offset": 0}


@pytest.mark.asyncio
async def test_library_filters_workspace_and_orders_before_pagination(stored):
    workspace = uuid4()
    earliest = datetime(2026, 11, 24, tzinfo=UTC)
    stored.add(workspace, created=earliest)
    middle = stored.add(workspace, created=earliest + timedelta(days=1))
    newest = stored.add(workspace, created=earliest + timedelta(days=2))
    stored.add(uuid4(), created=earliest + timedelta(days=3))
    result = await module.list_project_library(
        stored.db, workspace, SimpleNamespace(ai_mode="live"), limit=1, offset=1
    )
    assert result["total"] == 3
    assert result["limit"] == 1 and result["offset"] == 1
    assert [item["id"] for item in result["items"]] == [str(middle)]
    first = await module.list_project_library(
        stored.db, workspace, SimpleNamespace(ai_mode="live"), limit=1, offset=0
    )
    assert first["items"][0]["id"] == str(newest)


@pytest.mark.asyncio
async def test_library_same_time_order_is_deterministic(stored):
    workspace = uuid4()
    ids = [stored.add(workspace), stored.add(workspace)]
    result = await module.list_project_library(
        stored.db, workspace, SimpleNamespace(ai_mode="live"), limit=24, offset=0
    )
    assert [item["id"] for item in result["items"]] == sorted(map(str, ids), reverse=True)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "context,state",
    [
        ({}, {"finalStorageKey": None}),
        ({}, {"finalStorageKey": ""}),
        ({"p0": {"status": "suspended"}}, {}),
        ({"p0": {"status": "deleted"}}, {}),
        ({"p0": {"deletion": {"status": "blocked"}}}, {}),
        ({"p0": {"deletion": {"status": "completed"}}}, {}),
        *[
            ({"p0": {"rights": {role: {"revoked": True}}}}, {})
            for role in ("source", "product", "character", "characterConsent", "attestation")
        ],
    ],
)
async def test_library_omits_missing_and_unavailable_outputs(stored, context, state):
    workspace = uuid4()
    stored.add(workspace, context=context, state=state)
    result = await module.list_project_library(
        stored.db, workspace, SimpleNamespace(ai_mode="live"), limit=24, offset=0
    )
    assert result["items"] == [] and result["total"] == 0
    stored.media.url.assert_not_awaited()


@pytest.mark.asyncio
async def test_library_resigns_media_and_projects_only_public_card_fields(stored):
    workspace = uuid4()
    project = stored.add(
        workspace,
        context={
            "p0": {"deletion": {"status": "cancelled"}, "rights": {"source": {"revoked": False}}},
            "providerPayload": {"secret": "private"},
        },
        state={"downloadUrl": "https://forged.test/download", "providerPayload": "private"},
    )
    stored.media.url.side_effect = [
        "https://private.test/final?fresh=1",
        "https://private.test/product?fresh=1",
        "https://private.test/final?fresh=2",
        "https://private.test/product?fresh=2",
    ]
    first = await module.list_project_library(
        stored.db, workspace, SimpleNamespace(ai_mode="fixture"), limit=24, offset=0
    )
    second = await module.list_project_library(
        stored.db, workspace, SimpleNamespace(ai_mode="fixture"), limit=24, offset=0
    )
    item = first["items"][0]
    assert item == {
        "id": str(project),
        "projectName": "Video đã tạo",
        "createdAt": "2026-11-26T00:00:00+00:00",
        "status": "ready",
        "targetDuration": 8,
        "provider": "kie",
        "finalVideoUrl": "https://private.test/final?fresh=1",
        "productImageUrl": "https://private.test/product?fresh=1",
        "videos": [
            {
                "id": "final",
                "label": "Video hoàn chỉnh",
                "kind": "final",
                "url": "https://private.test/final?fresh=1",
                "durationSeconds": 8,
            }
        ],
    }
    assert second["items"][0]["finalVideoUrl"].endswith("fresh=2")
    stored.media.download_url.assert_not_awaited()


@pytest.mark.asyncio
async def test_library_includes_retained_clips_before_final_composition(stored):
    workspace = uuid4()
    project = stored.add(
        workspace,
        state={
            "finalStorageKey": None,
            "status": "incomplete",
            "targetDuration": 16,
            "scenes": [
                {"versions": [{"id": "clip-1", "storageKey": "clips/first", "frameCount": 192}]}
            ],
        },
        context={"p0": {"status": "active"}},
    )
    result = await module.list_project_library(
        stored.db, workspace, SimpleNamespace(ai_mode="live"), limit=24, offset=0
    )
    assert result["total"] == 1
    item = result["items"][0]
    assert item["id"] == str(project)
    assert item["finalVideoUrl"] == ""
    assert item["targetDuration"] == 16
    assert item["videos"] == [
        {
            "id": "clip-1",
            "label": "Clip 1",
            "kind": "clip",
            "url": "https://private.test/clips/first?fresh=1",
            "durationSeconds": 8,
        }
    ]
    assert "downloadUrl" not in item
    stored.media.download_url.assert_not_awaited()


@pytest.mark.asyncio
async def test_library_deduplicates_shared_group_files_and_keeps_every_unique_version(stored):
    workspace = uuid4()
    stored.add(
        workspace,
        state={
            "scenes": [
                {
                    "versions": [
                        {"id": "first", "storageKey": "clips/shared", "frameCount": 192},
                        {"id": "repair", "storageKey": "clips/repair", "rawDurationFrames": 180},
                    ]
                },
                {
                    "versions": [
                        {
                            "id": "shared-other-scene",
                            "storageKey": "clips/shared",
                            "frameCount": 192,
                        },
                        {"id": "legacy", "storageKey": "clips/legacy"},
                    ]
                },
            ]
        },
    )
    result = await module.list_project_library(
        stored.db, workspace, SimpleNamespace(ai_mode="live"), limit=24, offset=0
    )
    videos = result["items"][0]["videos"]
    assert [video["kind"] for video in videos] == ["final", "clip", "clip", "clip"]
    assert [video["id"] for video in videos[1:]] == ["first", "repair", "legacy"]
    assert [video["label"] for video in videos[1:]] == ["Clip 1", "Clip 2", "Clip 3"]
    assert [video["durationSeconds"] for video in videos[1:]] == [8, 7.5, 8]
    assert [call.args[0] for call in stored.media.url.await_args_list].count("clips/shared") == 1


@pytest.mark.asyncio
async def test_library_paginates_clip_only_projects_with_the_same_visibility_rules(stored):
    workspace = uuid4()
    base = datetime(2026, 11, 20, tzinfo=UTC)
    clip_state = {
        "finalStorageKey": None,
        "scenes": [
            {
                "versions": [
                    {"id": "clip", "storageKey": "clips/retained"},
                ]
            }
        ],
    }
    stored.add(workspace, created=base, state=clip_state)
    newer = stored.add(workspace, created=base + timedelta(days=1), state=clip_state)
    stored.add(
        workspace,
        created=base + timedelta(days=2),
        state=clip_state,
        context={"p0": {"deletion": {"status": "suspended"}}},
    )
    stored.add(uuid4(), created=base + timedelta(days=3), state=clip_state)
    result = await module.list_project_library(
        stored.db, workspace, SimpleNamespace(ai_mode="live"), limit=1, offset=0
    )
    assert result["total"] == 2
    assert [item["id"] for item in result["items"]] == [str(newer)]
    assert len(stored.media.url.await_args_list) == 2  # Selected clip + product only.


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["fixture", "mock", "live"])
async def test_library_never_offers_a_download_for_only_raw_clips(stored, mode):
    workspace = uuid4()
    stored.add(
        workspace,
        state={
            "finalStorageKey": None,
            "scenes": [
                {
                    "versions": [
                        {"id": "clip", "storageKey": "clips/retained"},
                    ]
                }
            ],
        },
    )
    result = await module.list_project_library(
        stored.db, workspace, SimpleNamespace(ai_mode=mode), limit=24, offset=0
    )
    assert "downloadUrl" not in result["items"][0]
    stored.media.download_url.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("storage_key", [None, "", 123])
async def test_library_does_not_count_empty_or_invalid_raw_storage_keys(stored, storage_key):
    workspace = uuid4()
    stored.add(
        workspace,
        state={
            "finalStorageKey": None,
            "scenes": [
                {
                    "versions": [
                        {"id": "missing", "storageKey": storage_key},
                    ]
                }
            ],
        },
    )
    result = await module.list_project_library(
        stored.db, workspace, SimpleNamespace(ai_mode="live"), limit=24, offset=0
    )
    assert result["total"] == 0 and result["items"] == []
    stored.media.url.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("mode,download", [("fixture", True), ("mock", True), ("live", False)])
async def test_library_legacy_download_matches_presenter_mode(stored, mode, download):
    workspace = uuid4()
    project = stored.add(workspace)
    result = await module.list_project_library(
        stored.db, workspace, SimpleNamespace(ai_mode=mode), limit=24, offset=0
    )
    assert ("downloadUrl" in result["items"][0]) is download
    if download:
        stored.media.download_url.assert_awaited_once_with(
            f"final/{project}", f"smart-remake-{project}.mp4"
        )


@pytest.fixture
async def routes(monkeypatch):
    workspace, actor = uuid4(), uuid4()
    db, settings = object(), SimpleNamespace(ai_mode="live")
    authorize = AsyncMock()
    listing = AsyncMock(return_value={"items": [], "total": 0, "limit": 24, "offset": 0})
    monkeypatch.setattr(module, "require_workspace_permission", authorize)
    monkeypatch.setattr(module, "list_project_library", listing)
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
            workspace=workspace,
            actor=actor,
            db=db,
            settings=settings,
            authorize=authorize,
            listing=listing,
            base=f"/workspaces/{workspace}/smart-remake/projects",
        )


@pytest.mark.asyncio
async def test_library_route_checks_read_permission_then_binds_scope_and_pagination(routes):
    response = await routes.client.get(f"{routes.base}?limit=12&offset=24")
    assert response.status_code == 200
    called = routes.authorize.await_args.args
    assert called[0:2] == (routes.workspace, Permission.WORKSPACE_READ)
    assert called[2].id == routes.actor and called[3] is routes.db
    routes.listing.assert_awaited_once_with(
        routes.db, routes.workspace, routes.settings, limit=12, offset=24
    )


@pytest.mark.asyncio
async def test_library_permission_denial_never_reads_rows(routes):
    routes.authorize.side_effect = ForbiddenError()
    response = await routes.client.get(routes.base)
    assert response.status_code == 403
    routes.listing.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("query", ["limit=0", "limit=101", "offset=-1"])
async def test_library_route_validates_pagination(routes, query):
    response = await routes.client.get(f"{routes.base}?{query}")
    assert response.status_code == 422
    routes.listing.assert_not_awaited()
