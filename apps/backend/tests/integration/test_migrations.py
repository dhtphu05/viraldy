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
            inspector = inspect(engine)
            tables = set(inspector.get_table_names())
            ai_model_run_columns = {
                column["name"] for column in inspector.get_columns("ai_model_runs")
            }
            product_columns = {column["name"] for column in inspector.get_columns("products")}
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
        "feedback_items",
        "product_events",
        "pattern_kits",
        "pattern_kit_versions",
        "pattern_kit_sources",
        "pattern_kit_evidence_links",
        "pattern_kit_actions",
        "viral_kits",
        "viral_kit_versions",
        "viral_kit_pattern_links",
        "viral_kit_concept_actions",
        "viral_kit_campaign_pack_links",
    }.issubset(tables)
    assert {
        "operation",
        "schema_version",
        "input_hash",
        "attempt_count",
        "usage_json",
        "estimated_cost",
        "safe_error_message",
    }.issubset(ai_model_run_columns)
    assert "product_context_version" in product_columns
