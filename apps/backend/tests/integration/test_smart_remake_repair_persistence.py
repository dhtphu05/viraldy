from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from testcontainers.postgres import PostgresContainer

from alembic import command
from alembic.config import Config
from viraldy.modules.identity.models import UserModel
from viraldy.modules.smart_remake.models import SmartRemakeProjectModel
from viraldy.modules.smart_remake.repair_repository import RepairRepository
from viraldy.modules.workspaces.models import WorkspaceModel
from viraldy.platform.config.settings import get_settings
from viraldy.shared.errors.base import ConflictError, NotFoundError


def test_migration_ownership_and_concurrent_operation_reservation(monkeypatch):
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
            engine = create_engine(sync_url)
            assert {"smart_remake_projects", "smart_remake_operations"}.issubset(
                set(inspect(engine).get_table_names())
            )
            engine.dispose()
            asyncio.run(_exercise_repository(async_url))
            command.downgrade(config, "0022_merge_auth_market")
            engine = create_engine(sync_url)
            assert "smart_remake_projects" not in inspect(engine).get_table_names()
            engine.dispose()
        finally:
            get_settings.cache_clear()


async def _exercise_repository(async_url):
    engine = create_async_engine(async_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    user_id, workspace_id, project_id = uuid4(), uuid4(), uuid4()
    try:
        async with factory() as session:
            session.add(
                UserModel(id=user_id, external_auth_id=str(user_id), email="repair@example.test")
            )
            await session.flush()
            session.add(
                WorkspaceModel(
                    id=workspace_id,
                    name="repair",
                    slug=str(workspace_id),
                    created_by_user_id=user_id,
                )
            )
            await session.flush()
            session.add(
                SmartRemakeProjectModel(
                    id=project_id,
                    workspace_id=workspace_id,
                    revision=1,
                    state_json={"revision": 1},
                    context_json={},
                )
            )
            await session.commit()
        async with factory() as session:
            with pytest.raises(NotFoundError):
                await RepairRepository(session).project(uuid4(), project_id)

        async def reserve(key, fingerprint):
            async with factory() as session:
                return await RepairRepository(session).start(
                    workspace_id, project_id, key, fingerprint
                )

        first, second = await asyncio.gather(
            reserve("same-key", "same-request"), reserve("same-key", "same-request")
        )
        assert first[1].id == second[1].id
        assert sorted([first[2], second[2]]) == [False, True]
        with pytest.raises(ConflictError, match="different request"):
            await reserve("same-key", "different-request")
        with pytest.raises(ConflictError, match="still running"):
            await reserve("new-key", "new-request")
    finally:
        await engine.dispose()
