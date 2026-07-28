from __future__ import annotations

from sqlalchemy import create_engine, inspect
from testcontainers.postgres import PostgresContainer

from alembic import command
from alembic.config import Config
from viraldy.platform.config.settings import get_settings


def test_initial_migration_runs_on_clean_postgres(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    with PostgresContainer("postgres:16.6-alpine") as postgres:
        sync_url = postgres.get_connection_url().replace(
            "postgresql+psycopg2",
            "postgresql+psycopg",
        )
        async_url = sync_url.replace("postgresql+psycopg", "postgresql+asyncpg")
        monkeypatch.setenv("DATABASE_SYNC_URL", sync_url)
        monkeypatch.setenv("DATABASE_URL", async_url)
        get_settings.cache_clear()

        config = Config("alembic.ini")
        command.upgrade(config, "head")

        engine = create_engine(sync_url)
        try:
            tables = set(inspect(engine).get_table_names())
        finally:
            engine.dispose()

    assert {
        "users",
        "workspaces",
        "workspace_members",
        "products",
        "assets",
        "asset_versions",
        "processing_jobs",
        "recommendations",
        "recommendation_actions",
    }.issubset(tables)
