from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from viraldy.platform.database.base import Base


class GenerationRunModel(Base):
    __tablename__ = "generation_runs"
    __table_args__ = (
        CheckConstraint(
            "operation IN ('storyboard_image_generate', 'concept_video_preview_generate')",
            name="ck_generation_runs_operation",
        ),
        CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled')",
            name="ck_generation_runs_status",
        ),
        UniqueConstraint(
            "workspace_id",
            "operation",
            "idempotency_key",
            name="uq_generation_runs_workspace_operation_idempotency",
        ),
        Index(
            "ix_generation_runs_workspace_status_created",
            "workspace_id",
            "status",
            "created_at",
        ),
        Index(
            "ix_generation_runs_viral_kit_version",
            "workspace_id",
            "viral_kit_version_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False, index=True
    )
    viral_kit_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("viral_kits.id"), nullable=False, index=True
    )
    viral_kit_version_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("viral_kit_versions.id"), nullable=False, index=True
    )
    viral_kit_version: Mapped[int] = mapped_column(Integer, nullable=False)
    concept_id: Mapped[str] = mapped_column(String(120), nullable=False)
    operation: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    prompt_version: Mapped[str] = mapped_column(String(100), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(100), nullable=False)
    generation_brief_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    source_asset_ids_json: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    processing_job_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("processing_jobs.id"), nullable=True, index=True
    )
    model_run_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("ai_model_runs.id"), nullable=True, index=True
    )
    output_json: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    safe_error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    safe_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class GenerationArtifactModel(Base):
    __tablename__ = "generation_artifacts"
    __table_args__ = (
        CheckConstraint(
            "artifact_kind IN ('storyboard_image', 'concept_video_preview')",
            name="ck_generation_artifacts_kind",
        ),
        UniqueConstraint(
            "generation_run_id",
            "provider_artifact_id",
            name="uq_generation_artifacts_run_provider_artifact",
        ),
        Index(
            "ix_generation_artifacts_workspace_run",
            "workspace_id",
            "generation_run_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False, index=True
    )
    generation_run_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("generation_runs.id"), nullable=False, index=True
    )
    model_run_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("ai_model_runs.id"), nullable=False, index=True
    )
    provider_artifact_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    artifact_kind: Mapped[str] = mapped_column(String(50), nullable=False)
    scene_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    storage_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    media_type: Mapped[str] = mapped_column(String(100), nullable=False)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    payload_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    provider: Mapped[str] = mapped_column(String(100), nullable=False)
    model: Mapped[str] = mapped_column(String(200), nullable=False)
    provider_request_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
