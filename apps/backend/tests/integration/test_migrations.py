from __future__ import annotations

import asyncio
from uuid import uuid4

from sqlalchemy import create_engine, inspect
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from testcontainers.postgres import PostgresContainer  # type: ignore[import-untyped]

from alembic import command
from alembic.config import Config
from viraldy.modules.identity.models import UserModel
from viraldy.modules.jobs.models import ProcessingJobModel
from viraldy.modules.jobs.repository import JobRepository
from viraldy.modules.workspaces.models import WorkspaceModel
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
        asyncio.run(_assert_canonical_job_wins_alias_collision(async_url))

        engine = create_engine(sync_url)
        try:
            inspector = inspect(engine)
            tables = set(inspector.get_table_names())
            ai_model_run_columns = {
                column["name"] for column in inspector.get_columns("ai_model_runs")
            }
            product_columns = {column["name"] for column in inspector.get_columns("products")}
            job_constraints = {
                constraint["name"]: constraint.get("sqltext", "")
                for constraint in inspector.get_check_constraints("processing_jobs")
            }
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
        "generation_runs",
        "generation_artifacts",
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
    assert "succeeded" in job_constraints["ck_processing_jobs_status"]
    assert "completed" not in job_constraints["ck_processing_jobs_status"]


async def _assert_canonical_job_wins_alias_collision(async_url: str) -> None:
    engine = create_async_engine(async_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            user = UserModel(
                external_auth_id=f"migration-test-{uuid4()}",
                email="migration-test@example.com",
            )
            session.add(user)
            await session.flush()
            workspace = WorkspaceModel(
                name="Migration Test",
                slug=f"migration-test-{uuid4()}",
                created_by_user_id=user.id,
            )
            session.add(workspace)
            await session.flush()
            canonical = ProcessingJobModel(
                workspace_id=workspace.id,
                subject_type="asset",
                subject_id=uuid4(),
                job_type="media_analysis",
                queue_name="default",
                status="queued",
                progress=0,
                stage="queued",
                attempt_count=0,
                max_attempts=3,
                idempotency_key="alias-collision",
                input_json={},
            )
            legacy = ProcessingJobModel(
                workspace_id=workspace.id,
                subject_type="asset",
                subject_id=uuid4(),
                job_type="process_asset",
                queue_name="default",
                status="queued",
                progress=0,
                stage="queued",
                attempt_count=0,
                max_attempts=3,
                idempotency_key="alias-collision",
                input_json={},
            )
            session.add_all([legacy, canonical])
            await session.flush()

            resolved = await JobRepository(session).get_existing_idempotent(
                workspace.id,
                "process_asset",
                "alias-collision",
            )

            assert resolved is not None
            assert resolved.id == canonical.id
            await session.rollback()
    finally:
        await engine.dispose()
