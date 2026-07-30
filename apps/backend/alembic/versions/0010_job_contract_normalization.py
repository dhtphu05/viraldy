from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0010_job_contract_normalization"
down_revision: str | None = "0009_generation_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PRIVATE_BETA_JOB_STATUSES = (
    "queued",
    "running",
    "retrying",
    "succeeded",
    "failed",
    "cancelled",
)
LEGACY_JOB_STATUSES = (
    "queued",
    "dispatching",
    "running",
    "retrying",
    "completed",
    "failed",
    "cancelled",
)
JOB_TYPE_MAPPINGS = (
    ("process_asset", "media_analysis"),
    ("analyze_reference", "creative_dna_build"),
    ("score_tiktok_asset", "tiktok_score_run"),
    ("run_ugc_preflight", "preflight_run"),
)


def upgrade() -> None:
    op.drop_constraint("ck_processing_jobs_status", "processing_jobs", type_="check")
    op.execute(
        sa.text(
            "UPDATE processing_jobs "
            "SET status = CASE "
            "WHEN status = 'completed' THEN 'succeeded' "
            "WHEN status = 'dispatching' THEN 'queued' "
            "ELSE status END, "
            "stage = CASE "
            "WHEN stage = 'completed' THEN 'succeeded' "
            "WHEN stage = 'dispatching' THEN 'queued' "
            "ELSE stage END "
            "WHERE status IN ('completed', 'dispatching')"
        )
    )
    op.execute(
        sa.text(
            "UPDATE processing_job_events "
            "SET status = CASE "
            "WHEN status = 'completed' THEN 'succeeded' "
            "WHEN status = 'dispatching' THEN 'queued' "
            "ELSE status END, "
            "stage = CASE "
            "WHEN stage = 'completed' THEN 'succeeded' "
            "WHEN stage = 'dispatching' THEN 'queued' "
            "ELSE stage END "
            "WHERE status IN ('completed', 'dispatching')"
        )
    )
    for legacy, canonical in JOB_TYPE_MAPPINGS:
        op.execute(
            sa.text(
                "UPDATE processing_jobs AS legacy_job "
                "SET job_type = :canonical "
                "WHERE legacy_job.job_type = :legacy "
                "AND (legacy_job.idempotency_key IS NULL OR NOT EXISTS ("
                "SELECT 1 FROM processing_jobs AS canonical_job "
                "WHERE canonical_job.workspace_id = legacy_job.workspace_id "
                "AND canonical_job.job_type = :canonical "
                "AND canonical_job.idempotency_key = legacy_job.idempotency_key"
                "))"
            ).bindparams(legacy=legacy, canonical=canonical)
        )
    op.create_check_constraint(
        "ck_processing_jobs_status",
        "processing_jobs",
        f"status IN {PRIVATE_BETA_JOB_STATUSES}",
    )
    op.create_check_constraint(
        "ck_processing_job_events_status",
        "processing_job_events",
        f"status IN {PRIVATE_BETA_JOB_STATUSES}",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_processing_job_events_status",
        "processing_job_events",
        type_="check",
    )
    op.drop_constraint("ck_processing_jobs_status", "processing_jobs", type_="check")
    op.execute(
        sa.text(
            "UPDATE processing_jobs SET status = 'completed', "
            "stage = CASE WHEN stage = 'succeeded' THEN 'completed' ELSE stage END "
            "WHERE status = 'succeeded'"
        )
    )
    op.execute(
        sa.text(
            "UPDATE processing_job_events SET status = 'completed', "
            "stage = CASE WHEN stage = 'succeeded' THEN 'completed' ELSE stage END "
            "WHERE status = 'succeeded'"
        )
    )
    for legacy, canonical in JOB_TYPE_MAPPINGS:
        op.execute(
            sa.text(
                "UPDATE processing_jobs SET job_type = :legacy " "WHERE job_type = :canonical"
            ).bindparams(legacy=legacy, canonical=canonical)
        )
    op.create_check_constraint(
        "ck_processing_jobs_status",
        "processing_jobs",
        f"status IN {LEGACY_JOB_STATUSES}",
    )
