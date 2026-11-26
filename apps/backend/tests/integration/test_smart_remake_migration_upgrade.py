"""Verify the Smart Remake migration preserves existing workspace and job data."""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy import create_engine, inspect, select
from sqlalchemy.orm import Session
from testcontainers.postgres import PostgresContainer

from alembic import command
from alembic.config import Config
from viraldy.modules.identity.models import UserModel
from viraldy.modules.jobs.models import ProcessingJobModel
from viraldy.modules.workspaces.models import WorkspaceModel
from viraldy.platform.config.settings import get_settings


def legacy_snapshot(engine):
    with engine.connect() as connection:
        return {
            model.__tablename__: [
                dict(row) for row in connection.execute(select(model.__table__)).mappings()
            ]
            for model in (UserModel, WorkspaceModel, ProcessingJobModel)
        }


def assert_smart_remake_schema(engine):
    schema = inspect(engine)
    assert {"smart_remake_projects", "smart_remake_operations"}.issubset(schema.get_table_names())
    assert any(
        foreign_key["constrained_columns"] == ["workspace_id"]
        and foreign_key["referred_table"] == "workspaces"
        and foreign_key["referred_columns"] == ["id"]
        for foreign_key in schema.get_foreign_keys("smart_remake_projects")
    )
    assert any(
        foreign_key["constrained_columns"] == ["project_id"]
        and foreign_key["referred_table"] == "smart_remake_projects"
        and foreign_key["referred_columns"] == ["id"]
        and foreign_key["options"].get("ondelete") == "CASCADE"
        for foreign_key in schema.get_foreign_keys("smart_remake_operations")
    )
    assert any(
        constraint["column_names"] == ["project_id", "idempotency_key"]
        for constraint in schema.get_unique_constraints("smart_remake_operations")
    )
    for table, column in (
        ("smart_remake_projects", "workspace_id"),
        ("smart_remake_operations", "project_id"),
    ):
        assert any(index["column_names"] == [column] for index in schema.get_indexes(table))


def test_existing_data_survives_upgrade_downgrade_and_reupgrade(monkeypatch):
    with PostgresContainer("postgres:16.6-alpine") as postgres:
        sync_url = postgres.get_connection_url().replace(
            "postgresql+psycopg2", "postgresql+psycopg"
        )
        monkeypatch.setenv("DATABASE_SYNC_URL", sync_url)
        monkeypatch.setenv("DATABASE_URL", sync_url.replace("+psycopg", "+asyncpg"))
        get_settings.cache_clear()
        engine = create_engine(sync_url)
        try:
            config = Config("alembic.ini")
            command.upgrade(config, "0022_merge_auth_market")
            assert "smart_remake_projects" not in inspect(engine).get_table_names()
            with Session(engine) as session:
                user_id, workspace_id = uuid4(), uuid4()
                session.add(
                    UserModel(
                        id=user_id,
                        external_auth_id=str(user_id),
                        email="migration@example.test",
                    )
                )
                session.flush()
                session.add(
                    WorkspaceModel(
                        id=workspace_id,
                        name="Existing seller workspace",
                        slug=str(workspace_id),
                        created_by_user_id=user_id,
                    )
                )
                session.flush()
                session.add(
                    ProcessingJobModel(
                        workspace_id=workspace_id,
                        subject_type="asset",
                        subject_id=uuid4(),
                        job_type="media_analysis",
                        status="running",
                        progress=40,
                        idempotency_key="existing-job",
                        input_json={
                            "sceneMap": {"scenes": [{"displayOrder": 0, "prompt": "Sản phẩm"}]},
                            "provider": "kie",
                        },
                        output_json={
                            "needsReconciliation": True,
                            "tasks": {"0": {"taskId": "paid-before-upgrade"}},
                        },
                    )
                )
                session.commit()
            before = legacy_snapshot(engine)

            command.upgrade(config, "head")
            assert_smart_remake_schema(engine)
            assert legacy_snapshot(engine) == before

            command.downgrade(config, "0022_merge_auth_market")
            assert not {"smart_remake_projects", "smart_remake_operations"}.intersection(
                inspect(engine).get_table_names()
            )
            assert legacy_snapshot(engine) == before

            command.upgrade(config, "head")
            assert_smart_remake_schema(engine)
            assert legacy_snapshot(engine) == before
        finally:
            engine.dispose()
            get_settings.cache_clear()
