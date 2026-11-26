from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.orm import Session
from testcontainers.postgres import PostgresContainer

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from viraldy.modules.identity.models import UserModel
from viraldy.platform.config.settings import get_settings


def test_release_keeps_published_auth_history_and_one_head() -> None:
    script = ScriptDirectory.from_config(Config("alembic.ini"))
    auth = script.get_revision("0021_password_auth")
    assert auth is not None
    assert auth.down_revision == "0017_domain_ugc_review"
    assert script.get_heads() == ["0024_smart_remake_p0_budget"]
    merge = script.get_revision("0022_merge_auth_market")
    assert merge is not None
    assert set(merge.down_revision) == {"0020_creative_family_candidates", "0021_password_auth"}


@pytest.mark.parametrize("starting_revision", ["base", "0021_password_auth"])
def test_release_upgrades_clean_and_existing_auth_databases(
    starting_revision: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    with PostgresContainer("postgres:16.6-alpine") as postgres:
        url = postgres.get_connection_url().replace("postgresql+psycopg2", "postgresql+psycopg")
        monkeypatch.setenv("DATABASE_SYNC_URL", url)
        monkeypatch.setenv("AUTH_MODE", "local_test")
        get_settings.cache_clear()
        config = Config("alembic.ini")
        user_id = uuid4()
        engine = create_engine(url)
        try:
            if starting_revision != "base":
                command.upgrade(config, starting_revision)
                with Session(engine) as session:
                    session.add(
                        UserModel(
                            id=user_id,
                            external_auth_id=f"password:{user_id}",
                            email="migration-seller@example.com",
                            display_name="Migration Seller",
                            status="active",
                        )
                    )
                    session.commit()
            command.upgrade(config, "head")
            inspector = inspect(engine)
            assert {
                "password_credentials",
                "password_sessions",
                "password_refresh_tokens",
                "creative_families",
                "external_source_records",
                "market_insight_snapshots",
                "smart_remake_projects",
                "smart_remake_operations",
                "smart_remake_attempts",
            } <= set(inspector.get_table_names())
            with engine.connect() as connection:
                assert connection.execute(
                    text("SELECT version_num FROM alembic_version")
                ).scalars().all() == ["0024_smart_remake_p0_budget"]
                if starting_revision != "base":
                    assert (
                        connection.execute(
                            select(UserModel.email).where(UserModel.id == user_id)
                        ).scalar_one()
                        == "migration-seller@example.com"
                    )
            command.upgrade(config, "head")
        finally:
            engine.dispose()
            get_settings.cache_clear()
