from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, func, inspect, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker
from testcontainers.postgres import PostgresContainer  # type: ignore[import-untyped]

from alembic import command
from alembic.config import Config
from viraldy.modules.assets.models import AssetModel, AssetVersionModel
from viraldy.modules.deletion.contracts import DeletionResourceType
from viraldy.modules.deletion.models import (
    DeletionAuditRecordModel,
    StorageDeletionBatchModel,
)
from viraldy.modules.deletion.retention import execute_retention_cleanup
from viraldy.modules.deletion.service import DeletionService
from viraldy.modules.deletion.storage_cleanup import (
    process_storage_deletion_batch_async,
)
from viraldy.modules.identity.models import UserModel
from viraldy.modules.jobs.models import ProcessingJobModel
from viraldy.modules.jobs.repository import JobRepository
from viraldy.modules.media_analysis.models import EvidenceItemModel, MediaArtifactModel
from viraldy.modules.workspaces.models import WorkspaceModel
from viraldy.platform.config.settings import get_settings
from viraldy.platform.storage.ports import StoragePort, StoredObject
from viraldy.shared.errors.base import AppError


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
        asyncio.run(_assert_workspace_deletion_cleans_storage(async_url))
        asyncio.run(_assert_deletion_rejects_cross_workspace_graph(async_url))
        asyncio.run(_assert_storage_cleanup_failure_is_retryable(async_url))
        _assert_retention_cleanup_removes_expired_pending_upload(sync_url)

        engine = create_engine(sync_url)
        try:
            inspector = inspect(engine)
            tables = set(inspector.get_table_names())
            ai_model_run_columns = {
                column["name"] for column in inspector.get_columns("ai_model_runs")
            }
            product_columns = {column["name"] for column in inspector.get_columns("products")}
            user_columns = {column["name"] for column in inspector.get_columns("users")}
            preflight_columns = {
                column["name"] for column in inspector.get_columns("preflight_runs")
            }
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
        "deletion_audit_records",
        "storage_deletion_batches",
    }.issubset(tables)
    assert {
        "operation",
        "schema_version",
        "input_hash",
        "attempt_count",
        "endpoint_family",
        "prompt_name",
        "repair_attempt_count",
        "request_id",
        "usage_json",
        "estimated_cost",
        "safe_error_message",
    }.issubset(ai_model_run_columns)
    assert "product_context_version" in product_columns
    assert "phone_number" in user_columns
    assert {
        "seller_summary_json",
        "creator_revision_json",
        "presentation_model_run_ids_json",
        "presentation_source_json",
    }.issubset(preflight_columns)
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


async def _assert_workspace_deletion_cleans_storage(async_url: str) -> None:
    engine = create_async_engine(async_url)
    sync_engine = create_engine(async_url.replace("postgresql+asyncpg", "postgresql+psycopg"))
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            user = UserModel(
                external_auth_id=f"deletion-test-{uuid4()}",
                email="deletion-test@example.com",
            )
            session.add(user)
            await session.flush()
            workspace = WorkspaceModel(
                name="Deletion Test",
                slug=f"deletion-test-{uuid4()}",
                created_by_user_id=user.id,
            )
            session.add(workspace)
            await session.flush()
            asset = AssetModel(
                workspace_id=workspace.id,
                asset_type="reference",
                status="uploaded",
                created_by_user_id=user.id,
                metadata_json={},
            )
            session.add(asset)
            await session.flush()
            storage_key = f"workspaces/{workspace.id}/assets/{asset.id}/source.mp4"
            version = AssetVersionModel(
                asset_id=asset.id,
                version_number=1,
                storage_key=storage_key,
                original_filename="source.mp4",
                declared_mime_type="video/mp4",
                detected_mime_type="video/mp4",
                size_bytes=128,
                validation_status="valid",
                metadata_json={},
            )
            session.add(version)
            await session.flush()
            asset.current_version_id = version.id
            frame_one = f"workspaces/{workspace.id}/frames/one.jpg"
            frame_two = f"workspaces/{workspace.id}/frames/two.jpg"
            frame_three = f"workspaces/{workspace.id}/frames/three.jpg"
            thumbnail = f"workspaces/{workspace.id}/thumbnails/opening.jpg"
            session.add(
                MediaArtifactModel(
                    workspace_id=workspace.id,
                    asset_version_id=version.id,
                    artifact_type="sampled_frames",
                    storage_key=thumbnail,
                    payload_json={
                        "frames": [
                            {"storage_key": frame_one},
                            {"storage_key": frame_two},
                            {"storage_key": "fixtures/opening.jpg"},
                        ]
                    },
                    provider="integration_test",
                    analysis_mode="mock",
                )
            )
            session.add(
                EvidenceItemModel(
                    workspace_id=workspace.id,
                    asset_version_id=version.id,
                    analysis_run_type="media_analysis",
                    evidence_type="visual_observation",
                    frame_storage_key=frame_one,
                    value_json={
                        "frame_storage_keys": [frame_one, frame_three],
                    },
                    source="model",
                )
            )
            await session.commit()

            def assert_database_committed_before_storage() -> None:
                with Session(sync_engine) as verification_session:
                    assert verification_session.get(WorkspaceModel, workspace.id) is None
                    assert (
                        verification_session.scalar(
                            select(func.count())
                            .select_from(StorageDeletionBatchModel)
                            .where(
                                StorageDeletionBatchModel.workspace_id == workspace.id,
                                StorageDeletionBatchModel.status == "pending",
                            )
                        )
                        == 1
                    )

            untracked_artifact = (
                f"workspaces/{workspace.id}/assets/{asset.id}"
                f"/versions/{version.id}/artifacts/orphaned-frame.jpg"
            )
            storage = _RecordingStorage(
                assert_database_committed_before_storage,
                objects=[StoredObject(untracked_artifact, datetime.now(UTC), 64)],
            )
            result = await DeletionService(
                session,
                cast(StoragePort, storage),
            ).delete(
                workspace_id=workspace.id,
                resource_type=DeletionResourceType.WORKSPACE,
                resource_id=workspace.id,
                user_id=user.id,
            )

            assert result.status == "succeeded"
            assert result.deleted_object_count == 6
            assert storage.deleted_keys == sorted(
                {
                    storage_key,
                    frame_one,
                    frame_two,
                    frame_three,
                    thumbnail,
                    untracked_artifact,
                }
            )
            assert (
                await session.scalar(
                    select(func.count())
                    .select_from(WorkspaceModel)
                    .where(WorkspaceModel.id == workspace.id)
                )
                == 0
            )
            assert (
                await session.scalar(
                    select(func.count()).select_from(AssetModel).where(AssetModel.id == asset.id)
                )
                == 0
            )
            audit = await session.get(DeletionAuditRecordModel, result.audit_id)
            assert audit is not None
            assert audit.status == "succeeded"
            assert audit.workspace_id == workspace.id
            assert audit.deleted_object_count == 6
    finally:
        await engine.dispose()
        sync_engine.dispose()


class _RecordingStorage:
    def __init__(  # type: ignore[no-untyped-def]
        self,
        before_delete=None,
        *,
        objects: list[StoredObject] | None = None,
    ) -> None:
        self.deleted_keys: list[str] = []
        self._before_delete = before_delete
        self._objects = objects or []

    def delete_object(self, key: str) -> None:
        if self._before_delete is not None:
            self._before_delete()
        self.deleted_keys.append(key)

    def list_objects(self, prefix: str) -> list[StoredObject]:
        return [item for item in self._objects if item.key.startswith(prefix)]


class _FailOnceStorage(_RecordingStorage):
    def __init__(self) -> None:
        super().__init__()
        self._failed = False

    def delete_object(self, key: str) -> None:
        if not self._failed:
            self._failed = True
            raise RuntimeError("temporary object storage outage")
        super().delete_object(key)


async def _assert_deletion_rejects_cross_workspace_graph(async_url: str) -> None:
    engine = create_async_engine(async_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    storage = _RecordingStorage()
    try:
        async with session_factory() as session:
            user = UserModel(
                external_auth_id=f"deletion-isolation-test-{uuid4()}",
                email="deletion-isolation-test@example.com",
            )
            session.add(user)
            await session.flush()
            workspace_a = WorkspaceModel(
                name="Deletion Isolation A",
                slug=f"deletion-isolation-a-{uuid4()}",
                created_by_user_id=user.id,
            )
            workspace_b = WorkspaceModel(
                name="Deletion Isolation B",
                slug=f"deletion-isolation-b-{uuid4()}",
                created_by_user_id=user.id,
            )
            session.add_all([workspace_a, workspace_b])
            await session.flush()
            asset = AssetModel(
                workspace_id=workspace_a.id,
                asset_type="reference",
                status="uploaded",
                created_by_user_id=user.id,
                metadata_json={},
            )
            session.add(asset)
            await session.flush()
            version = AssetVersionModel(
                asset_id=asset.id,
                version_number=1,
                storage_key=f"workspaces/{workspace_a.id}/assets/{asset.id}/source.mp4",
                original_filename="source.mp4",
                declared_mime_type="video/mp4",
                size_bytes=128,
                validation_status="valid",
                metadata_json={},
            )
            session.add(version)
            await session.flush()
            asset.current_version_id = version.id
            rogue_artifact = MediaArtifactModel(
                workspace_id=workspace_b.id,
                asset_version_id=version.id,
                artifact_type="thumbnail",
                storage_key=f"workspaces/{workspace_b.id}/rogue.jpg",
                payload_json={},
                provider="integration_test",
                analysis_mode="mock",
            )
            session.add(rogue_artifact)
            await session.commit()
            workspace_a_id = workspace_a.id
            workspace_b_id = workspace_b.id
            asset_id = asset.id
            rogue_artifact_id = rogue_artifact.id
            user_id = user.id

            with pytest.raises(AppError) as exc_info:
                await DeletionService(
                    session,
                    cast(StoragePort, storage),
                ).delete(
                    workspace_id=workspace_a_id,
                    resource_type=DeletionResourceType.ASSET,
                    resource_id=asset_id,
                    user_id=user_id,
                )

            assert exc_info.value.code == "DELETION_TENANT_GRAPH_CONFLICT"
            assert await session.get(AssetModel, asset_id) is not None
            assert await session.get(MediaArtifactModel, rogue_artifact_id) is not None
            assert await session.get(WorkspaceModel, workspace_b_id) is not None
            assert storage.deleted_keys == []
    finally:
        await engine.dispose()


async def _assert_storage_cleanup_failure_is_retryable(async_url: str) -> None:
    engine = create_async_engine(async_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    storage = _FailOnceStorage()
    try:
        async with session_factory() as session:
            user = UserModel(
                external_auth_id=f"deletion-retry-test-{uuid4()}",
                email="deletion-retry-test@example.com",
            )
            session.add(user)
            await session.flush()
            workspace = WorkspaceModel(
                name="Deletion Retry Test",
                slug=f"deletion-retry-test-{uuid4()}",
                created_by_user_id=user.id,
            )
            session.add(workspace)
            await session.flush()
            asset = AssetModel(
                workspace_id=workspace.id,
                asset_type="reference",
                status="uploaded",
                created_by_user_id=user.id,
                metadata_json={},
            )
            session.add(asset)
            await session.flush()
            storage_key = f"workspaces/{workspace.id}/assets/{asset.id}/source.mp4"
            version = AssetVersionModel(
                asset_id=asset.id,
                version_number=1,
                storage_key=storage_key,
                original_filename="source.mp4",
                declared_mime_type="video/mp4",
                size_bytes=128,
                validation_status="valid",
                metadata_json={},
            )
            session.add(version)
            await session.flush()
            asset.current_version_id = version.id
            asset_id = asset.id
            await session.commit()

            result = await DeletionService(
                session,
                cast(StoragePort, storage),
            ).delete(
                workspace_id=workspace.id,
                resource_type=DeletionResourceType.ASSET,
                resource_id=asset_id,
                user_id=user.id,
            )

            assert result.status == "storage_cleanup_pending"
            assert await session.get(AssetModel, asset_id) is None
            audit = await session.get(DeletionAuditRecordModel, result.audit_id)
            assert audit is not None
            assert audit.status == "storage_cleanup_pending"
            batch = await session.scalar(
                select(StorageDeletionBatchModel).where(
                    StorageDeletionBatchModel.source_id == result.audit_id
                )
            )
            assert batch is not None
            assert batch.status == "pending"

            cleanup = await process_storage_deletion_batch_async(
                session,
                batch.id,
                cast(StoragePort, storage),
            )

            assert cleanup.status == "succeeded"
            assert storage.deleted_keys == [storage_key]
            await session.refresh(audit)
            assert audit.status == "succeeded"
    finally:
        await engine.dispose()


def _assert_retention_cleanup_removes_expired_pending_upload(sync_url: str) -> None:
    engine = create_engine(sync_url)
    session_factory = sessionmaker(engine, expire_on_commit=False)
    now = datetime(2026, 7, 30, tzinfo=UTC)
    try:
        with session_factory() as session:
            user = UserModel(
                external_auth_id=f"retention-test-{uuid4()}",
                email="retention-test@example.com",
            )
            session.add(user)
            session.flush()
            workspace = WorkspaceModel(
                name="Retention Test",
                slug=f"retention-test-{uuid4()}",
                created_by_user_id=user.id,
            )
            session.add(workspace)
            session.flush()
            asset = AssetModel(
                workspace_id=workspace.id,
                asset_type="reference",
                status="pending_upload",
                created_by_user_id=user.id,
                metadata_json={},
                created_at=now - timedelta(days=30),
            )
            session.add(asset)
            session.flush()
            storage_key = f"workspaces/{workspace.id}/pending/{asset.id}.mp4"
            version = AssetVersionModel(
                asset_id=asset.id,
                version_number=1,
                storage_key=storage_key,
                original_filename="pending.mp4",
                declared_mime_type="video/mp4",
                size_bytes=128,
                validation_status="pending",
                metadata_json={},
            )
            session.add(version)
            session.flush()
            asset.current_version_id = version.id
            active_asset = AssetModel(
                workspace_id=workspace.id,
                asset_type="reference",
                status="uploaded",
                created_by_user_id=user.id,
                metadata_json={},
                created_at=now - timedelta(days=30),
            )
            session.add(active_asset)
            session.flush()
            active_storage_key = f"workspaces/{workspace.id}/assets/{active_asset.id}/active.mp4"
            active_version = AssetVersionModel(
                asset_id=active_asset.id,
                version_number=1,
                storage_key=active_storage_key,
                original_filename="active.mp4",
                declared_mime_type="video/mp4",
                size_bytes=128,
                validation_status="valid",
                metadata_json={},
            )
            session.add(active_version)
            session.flush()
            active_asset.current_version_id = active_version.id
            session.commit()

            def assert_database_committed_before_storage() -> None:
                with Session(engine) as verification_session:
                    assert verification_session.get(AssetModel, asset.id) is None
                    assert (
                        verification_session.scalar(
                            select(func.count())
                            .select_from(StorageDeletionBatchModel)
                            .where(
                                StorageDeletionBatchModel.workspace_id == workspace.id,
                                StorageDeletionBatchModel.status == "pending",
                            )
                        )
                        == 1
                    )

            orphan_key = f"workspaces/{workspace.id}/orphan/old.bin"
            recent_key = f"workspaces/{workspace.id}/orphan/recent.bin"
            storage = _RecordingStorage(
                assert_database_committed_before_storage,
                objects=[
                    StoredObject(orphan_key, now - timedelta(days=30), 64),
                    StoredObject(active_storage_key, now - timedelta(days=30), 128),
                    StoredObject(recent_key, now - timedelta(days=1), 64),
                ],
            )
            output = execute_retention_cleanup(
                session,
                workspace.id,
                get_settings(),
                cast(StoragePort, storage),
                now=now,
            )
            session.commit()

            assert output["deleted_asset_count"] == 1
            assert output["deleted_orphan_count"] == 1
            assert output["deleted_object_count"] == 2
            assert output["storage_cleanup_status"] == "succeeded"
            assert storage.deleted_keys == sorted({storage_key, orphan_key})
            assert session.get(AssetModel, asset.id) is None
            assert session.get(AssetModel, active_asset.id) is not None
    finally:
        engine.dispose()
