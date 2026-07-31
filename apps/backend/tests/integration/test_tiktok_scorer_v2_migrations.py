from __future__ import annotations

from sqlalchemy import create_engine, inspect, text
from testcontainers.postgres import PostgresContainer  # type: ignore[import-untyped]

from alembic import command
from alembic.config import Config
from viraldy.platform.config.settings import get_settings


def test_tiktok_scorer_v2_migrations_create_normalized_schema_and_seed_profiles(
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    with PostgresContainer("postgres:16.6-alpine") as postgres:
        sync_url = postgres.get_connection_url().replace(
            "postgresql+psycopg2",
            "postgresql+psycopg",
        )
        async_url = sync_url.replace("postgresql+psycopg", "postgresql+asyncpg")
        monkeypatch.setenv("DATABASE_SYNC_URL", sync_url)
        monkeypatch.setenv("DATABASE_URL", async_url)
        get_settings.cache_clear()

        command.upgrade(Config("alembic.ini"), "head")

        engine = create_engine(sync_url)
        try:
            inspector = inspect(engine)
            tables = set(inspector.get_table_names())
            run_columns = {column["name"] for column in inspector.get_columns("tiktok_score_runs")}
            with engine.connect() as connection:
                profile_codes = set(
                    connection.execute(
                        text(
                            "SELECT code FROM tiktok_score_profiles "
                            "WHERE profile_version = 1 AND is_system = true"
                        )
                    ).scalars()
                )
        finally:
            engine.dispose()

    assert {
        "tiktok_score_profiles",
        "tiktok_score_dimensions",
        "tiktok_score_findings",
        "tiktok_fix_actions",
        "tiktok_fix_action_events",
        "tiktok_score_comparisons",
    }.issubset(tables)
    assert {
        "asset_id",
        "product_id",
        "score_mode",
        "intended_use",
        "score_profile",
        "product_context_snapshot_hash",
        "parent_score_run_id",
        "current_stage",
    }.issubset(run_columns)
    assert profile_codes == {
        "general_tiktok_v1",
        "product_led_demo_v1",
        "creator_review_v1",
        "story_led_pov_v1",
        "tutorial_howto_v1",
        "unboxing_reaction_v1",
        "comment_reply_faq_v1",
        "offer_led_shop_v1",
    }
