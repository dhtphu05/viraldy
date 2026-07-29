from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0003_keyless_product_hardening"
down_revision: str | None = "0002_creative_intelligence_mvp"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


ANALYTICAL_STATUSES = ("pending", "queued", "processing", "completed", "failed", "cancelled")
JOB_STATUSES = ("queued", "dispatching", "running", "retrying", "completed", "failed", "cancelled")


def _jsonb_default_object() -> sa.TextClause:
    return sa.text("'{}'::jsonb")


def upgrade() -> None:
    op.create_table(
        "processing_job_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id"),
            nullable=False,
        ),
        sa.Column(
            "processing_job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("processing_jobs.id"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("stage", sa.String(length=100), nullable=True),
        sa.Column("progress", sa.Integer(), nullable=True),
        sa.Column("message", sa.String(length=500), nullable=True),
        sa.Column(
            "details_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=_jsonb_default_object(),
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index(
        "ix_processing_job_events_workspace_id", "processing_job_events", ["workspace_id"]
    )
    op.create_index(
        "ix_processing_job_events_processing_job_id",
        "processing_job_events",
        ["processing_job_id"],
    )
    op.create_index(
        "ix_processing_job_events_job_created",
        "processing_job_events",
        ["processing_job_id", "created_at"],
    )
    op.create_index(
        "ix_processing_job_events_workspace_created",
        "processing_job_events",
        ["workspace_id", "created_at"],
    )

    op.create_table(
        "ai_model_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id"),
            nullable=False,
        ),
        sa.Column(
            "processing_job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("processing_jobs.id"),
            nullable=True,
        ),
        sa.Column("subject_type", sa.String(length=100), nullable=False),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("capability", sa.String(length=100), nullable=False),
        sa.Column("analysis_mode", sa.String(length=50), nullable=False),
        sa.Column("provider", sa.String(length=100), nullable=False),
        sa.Column("model", sa.String(length=200), nullable=False),
        sa.Column("prompt_version", sa.String(length=100), nullable=True),
        sa.Column("response_schema_version", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "input_summary_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=_jsonb_default_object(),
        ),
        sa.Column(
            "output_summary_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=_jsonb_default_object(),
        ),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("provider_request_id", sa.String(length=255), nullable=True),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "analysis_mode IN ('fixture', 'mock', 'live')", name="ck_ai_model_runs_analysis_mode"
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed')",
            name="ck_ai_model_runs_status",
        ),
        sa.CheckConstraint("attempt >= 1", name="ck_ai_model_runs_attempt"),
    )
    op.create_index("ix_ai_model_runs_workspace_id", "ai_model_runs", ["workspace_id"])
    op.create_index("ix_ai_model_runs_processing_job_id", "ai_model_runs", ["processing_job_id"])
    op.create_index(
        "ix_ai_model_runs_workspace_created", "ai_model_runs", ["workspace_id", "created_at"]
    )
    op.create_index(
        "ix_ai_model_runs_job_capability", "ai_model_runs", ["processing_job_id", "capability"]
    )
    op.create_index(
        "ix_ai_model_runs_subject", "ai_model_runs", ["workspace_id", "subject_type", "subject_id"]
    )

    _add_job_constraints()
    _add_current_version_foreign_keys()
    _add_media_provenance()
    _add_analytical_links()
    _add_campaign_pack_provenance()


def _add_job_constraints() -> None:
    op.create_check_constraint(
        "ck_processing_jobs_status",
        "processing_jobs",
        f"status IN {JOB_STATUSES}",
    )
    op.create_check_constraint(
        "ck_processing_jobs_attempt_count",
        "processing_jobs",
        "attempt_count >= 0 AND max_attempts >= 1 AND attempt_count <= max_attempts",
    )
    op.create_check_constraint(
        "ck_processing_job_events_progress",
        "processing_job_events",
        "progress IS NULL OR (progress >= 0 AND progress <= 100)",
    )


def _add_current_version_foreign_keys() -> None:
    op.create_foreign_key(
        "fk_assets_current_version_id_asset_versions",
        "assets",
        "asset_versions",
        ["current_version_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_campaign_packs_current_version_id_versions",
        "campaign_packs",
        "campaign_pack_versions",
        ["current_version_id"],
        ["id"],
    )


def _add_media_provenance() -> None:
    op.add_column(
        "media_artifacts",
        sa.Column("processing_job_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column("media_artifacts", sa.Column("stage", sa.String(length=100), nullable=True))
    op.add_column("media_artifacts", sa.Column("ordinal", sa.BigInteger(), nullable=True))
    op.add_column("media_artifacts", sa.Column("sha256", sa.String(length=64), nullable=True))
    op.add_column(
        "media_artifacts",
        sa.Column(
            "pipeline_version",
            sa.String(length=100),
            nullable=False,
            server_default="media_pipeline_v1",
        ),
    )
    op.create_foreign_key(
        "fk_media_artifacts_processing_job_id",
        "media_artifacts",
        "processing_jobs",
        ["processing_job_id"],
        ["id"],
    )
    op.create_index(
        "ix_media_artifacts_processing_job_id", "media_artifacts", ["processing_job_id"]
    )
    op.create_index(
        "uq_media_artifacts_job_stage_type_ordinal",
        "media_artifacts",
        ["processing_job_id", "stage", "artifact_type", "ordinal"],
        unique=True,
    )

    op.add_column(
        "evidence_items",
        sa.Column("processing_job_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column("evidence_items", sa.Column("stage", sa.String(length=100), nullable=True))
    op.add_column("evidence_items", sa.Column("identity_hash", sa.String(length=64), nullable=True))
    op.add_column(
        "evidence_items",
        sa.Column(
            "pipeline_version",
            sa.String(length=100),
            nullable=False,
            server_default="media_pipeline_v1",
        ),
    )
    op.create_foreign_key(
        "fk_evidence_items_processing_job_id",
        "evidence_items",
        "processing_jobs",
        ["processing_job_id"],
        ["id"],
    )
    op.create_index("ix_evidence_items_processing_job_id", "evidence_items", ["processing_job_id"])
    op.create_index(
        "uq_evidence_items_job_stage_type_identity",
        "evidence_items",
        ["processing_job_id", "stage", "evidence_type", "identity_hash"],
        unique=True,
    )
    op.create_check_constraint(
        "ck_evidence_items_time_range",
        "evidence_items",
        "(start_ms IS NULL OR start_ms >= 0) AND "
        "(end_ms IS NULL OR end_ms >= 0) AND "
        "(start_ms IS NULL OR end_ms IS NULL OR end_ms >= start_ms)",
    )


def _add_analytical_links() -> None:
    op.add_column(
        "adaptation_runs",
        sa.Column(
            "status",
            sa.String(length=50),
            nullable=False,
            server_default="completed",
        ),
    )
    for table in (
        "creative_dna_versions",
        "tiktok_score_runs",
        "adaptation_runs",
        "preflight_runs",
    ):
        op.add_column(
            table,
            sa.Column("processing_job_id", postgresql.UUID(as_uuid=True), nullable=True),
        )
        op.add_column(
            table,
            sa.Column("primary_model_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        )
        op.add_column(
            table,
            sa.Column(
                "pipeline_version",
                sa.String(length=100),
                nullable=False,
                server_default="media_pipeline_v1",
            ),
        )
        op.create_foreign_key(
            f"fk_{table}_processing_job_id",
            table,
            "processing_jobs",
            ["processing_job_id"],
            ["id"],
        )
        op.create_foreign_key(
            f"fk_{table}_primary_model_run_id",
            table,
            "ai_model_runs",
            ["primary_model_run_id"],
            ["id"],
        )
        op.create_index(f"ix_{table}_processing_job_id", table, ["processing_job_id"])
        op.create_index(f"ix_{table}_primary_model_run_id", table, ["primary_model_run_id"])

    for table in (
        "creative_dna_versions",
        "tiktok_score_runs",
        "adaptation_runs",
        "preflight_runs",
    ):
        op.create_check_constraint(
            f"ck_{table}_status",
            table,
            f"status IN {ANALYTICAL_STATUSES}",
        )


def _add_campaign_pack_provenance() -> None:
    op.add_column(
        "campaign_pack_versions",
        sa.Column("source_adaptation_run_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "campaign_pack_versions",
        sa.Column("source_model_run_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "campaign_pack_versions",
        sa.Column("source_prompt_version", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "campaign_pack_versions",
        sa.Column("source_schema_version", sa.String(length=100), nullable=True),
    )
    op.create_foreign_key(
        "fk_campaign_pack_versions_source_adaptation_run_id",
        "campaign_pack_versions",
        "adaptation_runs",
        ["source_adaptation_run_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_campaign_pack_versions_source_model_run_id",
        "campaign_pack_versions",
        "ai_model_runs",
        ["source_model_run_id"],
        ["id"],
    )
    op.create_check_constraint(
        "ck_reference_status",
        "references",
        "status IN ('draft', 'ready', 'analyzing', 'analyzed', 'failed', 'archived')",
    )
    op.create_check_constraint(
        "ck_campaign_pack_status",
        "campaign_packs",
        "status IN ('draft', 'ready', 'sent', 'archived', 'active')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_campaign_pack_status", "campaign_packs", type_="check")
    op.drop_constraint("ck_reference_status", "references", type_="check")
    op.drop_constraint(
        "fk_campaign_pack_versions_source_model_run_id",
        "campaign_pack_versions",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_campaign_pack_versions_source_adaptation_run_id",
        "campaign_pack_versions",
        type_="foreignkey",
    )
    op.drop_column("campaign_pack_versions", "source_schema_version")
    op.drop_column("campaign_pack_versions", "source_prompt_version")
    op.drop_column("campaign_pack_versions", "source_model_run_id")
    op.drop_column("campaign_pack_versions", "source_adaptation_run_id")

    for table in (
        "preflight_runs",
        "adaptation_runs",
        "tiktok_score_runs",
        "creative_dna_versions",
    ):
        op.drop_constraint(f"ck_{table}_status", table, type_="check")
        op.drop_index(f"ix_{table}_primary_model_run_id", table_name=table)
        op.drop_index(f"ix_{table}_processing_job_id", table_name=table)
        op.drop_constraint(f"fk_{table}_primary_model_run_id", table, type_="foreignkey")
        op.drop_constraint(f"fk_{table}_processing_job_id", table, type_="foreignkey")
        op.drop_column(table, "pipeline_version")
        op.drop_column(table, "primary_model_run_id")
        op.drop_column(table, "processing_job_id")
    op.drop_column("adaptation_runs", "status")

    op.drop_constraint("ck_evidence_items_time_range", "evidence_items", type_="check")
    op.drop_index("uq_evidence_items_job_stage_type_identity", table_name="evidence_items")
    op.drop_index("ix_evidence_items_processing_job_id", table_name="evidence_items")
    op.drop_constraint("fk_evidence_items_processing_job_id", "evidence_items", type_="foreignkey")
    op.drop_column("evidence_items", "pipeline_version")
    op.drop_column("evidence_items", "identity_hash")
    op.drop_column("evidence_items", "stage")
    op.drop_column("evidence_items", "processing_job_id")

    op.drop_index("uq_media_artifacts_job_stage_type_ordinal", table_name="media_artifacts")
    op.drop_index("ix_media_artifacts_processing_job_id", table_name="media_artifacts")
    op.drop_constraint(
        "fk_media_artifacts_processing_job_id", "media_artifacts", type_="foreignkey"
    )
    op.drop_column("media_artifacts", "pipeline_version")
    op.drop_column("media_artifacts", "sha256")
    op.drop_column("media_artifacts", "ordinal")
    op.drop_column("media_artifacts", "stage")
    op.drop_column("media_artifacts", "processing_job_id")

    op.drop_constraint(
        "fk_campaign_packs_current_version_id_versions", "campaign_packs", type_="foreignkey"
    )
    op.drop_constraint("fk_assets_current_version_id_asset_versions", "assets", type_="foreignkey")
    op.drop_constraint("ck_processing_job_events_progress", "processing_job_events", type_="check")
    op.drop_constraint("ck_processing_jobs_attempt_count", "processing_jobs", type_="check")
    op.drop_constraint("ck_processing_jobs_status", "processing_jobs", type_="check")

    op.drop_index("ix_ai_model_runs_subject", table_name="ai_model_runs")
    op.drop_index("ix_ai_model_runs_job_capability", table_name="ai_model_runs")
    op.drop_index("ix_ai_model_runs_workspace_created", table_name="ai_model_runs")
    op.drop_index("ix_ai_model_runs_processing_job_id", table_name="ai_model_runs")
    op.drop_index("ix_ai_model_runs_workspace_id", table_name="ai_model_runs")
    op.drop_table("ai_model_runs")

    op.drop_index("ix_processing_job_events_workspace_created", table_name="processing_job_events")
    op.drop_index("ix_processing_job_events_job_created", table_name="processing_job_events")
    op.drop_index("ix_processing_job_events_processing_job_id", table_name="processing_job_events")
    op.drop_index("ix_processing_job_events_workspace_id", table_name="processing_job_events")
    op.drop_table("processing_job_events")
