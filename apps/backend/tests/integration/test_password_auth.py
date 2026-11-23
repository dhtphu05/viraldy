from __future__ import annotations

import asyncio
import os
import secrets
from collections.abc import AsyncIterator, Iterator
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

from alembic import command
from alembic.config import Config
from viraldy.api.middleware.errors import app_error_handler, validation_error_handler
from viraldy.modules.identity.models import UserModel
from viraldy.modules.identity.password_models import (
    PasswordCredentialModel,
    PasswordRefreshTokenModel,
    PasswordSessionModel,
)
from viraldy.modules.identity.password_router import router as password_router
from viraldy.modules.identity.password_service import token_hash
from viraldy.modules.identity.router import router as identity_router
from viraldy.modules.workspaces.router import router as workspace_router
from viraldy.platform.clock.utc import utc_now
from viraldy.platform.config.settings import Settings, get_settings
from viraldy.platform.database.session import get_async_session
from viraldy.shared.errors.base import AppError

PASSWORD = secrets.token_urlsafe(24)


@pytest.fixture(scope="module")
def auth_settings() -> Iterator[Settings]:
    previous = os.environ.get("DATABASE_SYNC_URL")
    with (
        PostgresContainer("postgres:16.6-alpine") as postgres,
        RedisContainer("redis:7.4-alpine") as redis,
    ):
        sync_url = postgres.get_connection_url().replace(
            "postgresql+psycopg2", "postgresql+psycopg"
        )
        os.environ["DATABASE_SYNC_URL"] = sync_url
        get_settings.cache_clear()
        backend = Path(__file__).resolve().parents[2]
        config = Config(str(backend / "alembic.ini"))
        config.set_main_option("script_location", str(backend / "alembic"))
        command.upgrade(config, "head")
        yield Settings(
            _env_file=None,
            auth_mode="password",
            auth_jwt_secret="test-only-native-secret-at-least-32bytes-ABC123!",  # noqa: S106
            database_url=sync_url.replace("postgresql+psycopg", "postgresql+asyncpg"),
            redis_url=f"redis://{redis.get_container_host_ip()}:{redis.get_exposed_port(6379)}/0",
        )
    if previous is None:
        os.environ.pop("DATABASE_SYNC_URL", None)
    else:
        os.environ["DATABASE_SYNC_URL"] = previous
    get_settings.cache_clear()


@pytest.fixture
async def client(auth_settings: Settings) -> AsyncIterator[httpx.AsyncClient]:
    engine = create_async_engine(auth_settings.database_url)
    sessions = async_sessionmaker(engine, expire_on_commit=False)

    async def database():
        async with sessions() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    app = FastAPI()
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.include_router(identity_router, prefix="/api/v1")
    app.include_router(password_router, prefix="/api/v1")
    app.include_router(workspace_router, prefix="/api/v1")
    app.dependency_overrides[get_settings] = lambda: auth_settings
    app.dependency_overrides[get_async_session] = database
    transport = httpx.ASGITransport(app, client=(uuid4().hex, 12345))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
        yield http
    await engine.dispose()


async def register(client: httpx.AsyncClient) -> tuple[str, dict[str, str]]:
    email = f"seller-{uuid4().hex}@example.com"
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "display_name": "Seller One",
            "password": PASSWORD,
        },
    )
    assert response.status_code == 201, response.text
    assert response.headers["cache-control"] == "no-store"
    return email, response.json()["data"]


def bearer(tokens: dict[str, str]) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


@pytest.mark.asyncio
async def test_registration_login_and_private_workspace(
    client: httpx.AsyncClient, auth_settings: Settings
) -> None:
    email, tokens = await register(client)
    profile = await client.get("/api/v1/me", headers=bearer(tokens))
    assert profile.status_code == 200
    assert profile.json()["data"]["email"] == email
    assert profile.json()["data"]["phone_number"] is None
    workspaces = await client.get("/api/v1/workspaces", headers=bearer(tokens))
    assert len(workspaces.json()["data"]) == 1
    workspace_id = workspaces.json()["data"][0]["id"]
    login = await client.post(
        "/api/v1/auth/login", json={"email": email.upper(), "password": PASSWORD}
    )
    assert login.status_code == 200
    _, other = await register(client)
    denied = await client.get(f"/api/v1/workspaces/{workspace_id}", headers=bearer(other))
    assert denied.status_code == 403
    engine = create_async_engine(auth_settings.database_url)
    async with async_sessionmaker(engine)() as db:
        credential = await db.scalar(
            select(PasswordCredentialModel).where(PasswordCredentialModel.email == email)
        )
        assert credential.password_hash.startswith("$argon2id$")
        assert credential.password_hash != PASSWORD
    await engine.dispose()


@pytest.mark.asyncio
async def test_duplicate_email_validation_and_wrong_password(client: httpx.AsyncClient) -> None:
    email, _ = await register(client)
    duplicate = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email.upper(),
            "display_name": "Another Seller",
            "password": PASSWORD,
        },
    )
    assert duplicate.status_code == 409
    wrong = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "wrong-password"}
    )
    unknown = await client.post(
        "/api/v1/auth/login", json={"email": "unknown@example.com", "password": "wrong-password"}
    )
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json()["error"]["message"] == unknown.json()["error"]["message"]
    short = await client.post(
        "/api/v1/auth/register",
        json={"email": "new@example.com", "display_name": "Seller", "password": "short"},
    )
    assert short.status_code == 422
    assert '"input"' not in short.text


@pytest.mark.asyncio
async def test_refresh_rotation_replay_and_logout(
    client: httpx.AsyncClient, auth_settings: Settings
) -> None:
    _, tokens = await register(client)
    refresh = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert refresh.status_code == 200
    rotated = refresh.json()["data"]
    assert rotated["refresh_token"] != tokens["refresh_token"]
    concurrent = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert concurrent.status_code == 409
    assert (await client.get("/api/v1/me", headers=bearer(rotated))).status_code == 200
    engine = create_async_engine(auth_settings.database_url)
    async with async_sessionmaker(engine)() as db:
        await db.execute(
            update(PasswordRefreshTokenModel)
            .where(
                PasswordRefreshTokenModel.token_hash == token_hash(tokens["refresh_token"]),
            )
            .values(consumed_at=utc_now() - timedelta(seconds=10))
        )
        await db.commit()
    await engine.dispose()
    replay = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert replay.status_code == 401
    assert (await client.get("/api/v1/me", headers=bearer(rotated))).status_code == 401
    assert (
        await client.post("/api/v1/auth/refresh", json={"refresh_token": rotated["refresh_token"]})
    ).status_code == 401
    _, active = await register(client)
    assert (
        await client.post("/api/v1/auth/logout", json={"refresh_token": active["refresh_token"]})
    ).status_code == 204
    assert (await client.get("/api/v1/me", headers=bearer(active))).status_code == 401
    assert (
        await client.post("/api/v1/auth/logout", json={"refresh_token": active["refresh_token"]})
    ).status_code == 204


@pytest.mark.asyncio
async def test_login_attempts_are_limited_across_requests(client: httpx.AsyncClient) -> None:
    email = f"unknown-{uuid4().hex}@example.com"
    responses = [
        await client.post("/api/v1/auth/login", json={"email": email, "password": "wrong-password"})
        for _ in range(9)
    ]
    assert responses[-1].status_code == 429


@pytest.mark.asyncio
async def test_simultaneous_refresh_and_logout_preserve_revocation(
    client: httpx.AsyncClient,
) -> None:
    _, tokens = await register(client)
    first, second = await asyncio.gather(
        *[
            client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
            for _ in range(2)
        ]
    )
    assert sorted([first.status_code, second.status_code]) == [200, 409]
    winner = (first if first.status_code == 200 else second).json()["data"]
    refresh, logout = await asyncio.gather(
        client.post("/api/v1/auth/refresh", json={"refresh_token": winner["refresh_token"]}),
        client.post("/api/v1/auth/logout", json={"refresh_token": winner["refresh_token"]}),
    )
    assert logout.status_code == 204
    assert refresh.status_code in {200, 401}
    assert (await client.get("/api/v1/me", headers=bearer(winner))).status_code == 401
    if refresh.status_code == 200:
        assert (
            await client.get("/api/v1/me", headers=bearer(refresh.json()["data"]))
        ).status_code == 401


@pytest.mark.asyncio
async def test_expired_and_suspended_sessions_cannot_be_used(
    client: httpx.AsyncClient,
    auth_settings: Settings,
) -> None:
    _, expired = await register(client)
    engine = create_async_engine(auth_settings.database_url)
    async with async_sessionmaker(engine)() as db:
        session_id = await db.scalar(
            select(PasswordRefreshTokenModel.session_id).where(
                PasswordRefreshTokenModel.token_hash == token_hash(expired["refresh_token"])
            )
        )
        await db.execute(
            update(PasswordSessionModel)
            .where(PasswordSessionModel.id == session_id)
            .values(expires_at=utc_now() - timedelta(seconds=1))
        )
        await db.commit()
    assert (await client.get("/api/v1/me", headers=bearer(expired))).status_code == 401
    assert (
        await client.post("/api/v1/auth/refresh", json={"refresh_token": expired["refresh_token"]})
    ).status_code == 401
    email, suspended = await register(client)
    async with async_sessionmaker(engine)() as db:
        await db.execute(
            update(UserModel).where(UserModel.email == email).values(status="suspended")
        )
        await db.commit()
    assert (await client.get("/api/v1/me", headers=bearer(suspended))).status_code == 401
    assert (
        await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    ).status_code == 401
    assert (
        await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": suspended["refresh_token"]}
        )
    ).status_code == 401
    assert (
        await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "unrecognized-refresh-token-of-sufficient-length"},
        )
    ).status_code == 401
    await engine.dispose()
