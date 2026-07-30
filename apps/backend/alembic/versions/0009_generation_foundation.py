from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0009_generation_foundation"
down_revision: str | None = "0008_viral_kits"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "generation_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id"),
            nullable=False,
        ),
        sa.Column(
            "viral_kit_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("viral_kits.id"),
            nullable=False,
        ),
        sa.Column(
            "viral_kit_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("viral_kit_versions.id"),
            nullable=False,
        ),
        sa.Column("viral_kit_version", sa.Integer(), nullable=False),
        sa.Column("concept_id", sa.String(length=120), nullable=False),
        sa.Column("operation", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("prompt_version", sa.String(length=100), nullable=False),
        sa.Column("schema_version", sa.String(length=100), nullable=False),
        sa.Column("generation_brief_json", postgresql.JSONB(), nullable=False),
        sa.Column("source_asset_ids_json", postgresql.JSONB(), nullable=False),
        sa.Column("input_hash", sa.String(length=64), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=True),
        sa.Column(
            "processing_job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("processing_jobs.id"),
            nullable=True,
        ),
        sa.Column(
            "model_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ai_model_runs.id"),
            nullable=True,
        ),
        sa.Column("output_json", postgresql.JSONB(), nullable=True),
        sa.Column("safe_error_code", sa.String(length=100), nullable=True),
        sa.Column("safe_error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "operation IN ('storyboard_image_generate', 'concept_video_preview_generate')",
            name="ck_generation_runs_operation",
        ),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled')",
            name="ck_generation_runs_status",
        ),
        sa.UniqueConstraint(
            "workspace_id",
            "operation",
            "idempotency_key",
            name="uq_generation_runs_workspace_operation_idempotency",
        ),
    )
    op.create_index("ix_generation_runs_workspace_id", "generation_runs", ["workspace_id"])
    op.create_index("ix_generation_runs_viral_kit_id", "generation_runs", ["viral_kit_id"])
    op.create_index(
        "ix_generation_runs_viral_kit_version_id",
        "generation_runs",
        ["viral_kit_version_id"],
    )
    op.create_index(
        "ix_generation_runs_processing_job_id",
        "generation_runs",
        ["processing_job_id"],
    )
    op.create_index("ix_generation_runs_model_run_id", "generation_runs", ["model_run_id"])
    op.create_index(
        "ix_generation_runs_created_by_user_id",
        "generation_runs",
        ["created_by_user_id"],
    )
    op.create_index("ix_generation_runs_status", "generation_runs", ["status"])
    op.create_index(
        "ix_generation_runs_workspace_status_created",
        "generation_runs",
        ["workspace_id", "status", "created_at"],
    )
    op.create_index(
        "ix_generation_runs_viral_kit_version",
        "generation_runs",
        ["workspace_id", "viral_kit_version_id"],
    )

    op.create_table(
        "generation_artifacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id"),
            nullable=False,
        ),
        sa.Column(
            "generation_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("generation_runs.id"),
            nullable=False,
        ),
        sa.Column(
            "model_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ai_model_runs.id"),
            nullable=False,
        ),
        sa.Column("provider_artifact_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("artifact_kind", sa.String(length=50), nullable=False),
        sa.Column("scene_id", sa.String(length=120), nullable=True),
        sa.Column("storage_key", sa.Text(), nullable=True),
        sa.Column("media_type", sa.String(length=100), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column(
            "payload_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("provider", sa.String(length=100), nullable=False),
        sa.Column("model", sa.String(length=200), nullable=False),
        sa.Column("provider_request_id", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "artifact_kind IN ('storyboard_image', 'concept_video_preview')",
            name="ck_generation_artifacts_kind",
        ),
        sa.UniqueConstraint(
            "generation_run_id",
            "provider_artifact_id",
            name="uq_generation_artifacts_run_provider_artifact",
        ),
    )
    op.create_index(
        "ix_generation_artifacts_workspace_id",
        "generation_artifacts",
        ["workspace_id"],
    )
    op.create_index(
        "ix_generation_artifacts_generation_run_id",
        "generation_artifacts",
        ["generation_run_id"],
    )
    op.create_index(
        "ix_generation_artifacts_model_run_id",
        "generation_artifacts",
        ["model_run_id"],
    )
    op.create_index(
        "ix_generation_artifacts_workspace_run",
        "generation_artifacts",
        ["workspace_id", "generation_run_id"],
    )


def downgrade() -> None:
    op.drop_table("generation_artifacts")
    op.drop_table("generation_runs")
