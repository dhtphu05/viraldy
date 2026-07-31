from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0012_openai_provenance"
down_revision: str | None = "0011_deletion_audit"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "ai_model_runs",
        sa.Column("request_id", sa.String(length=255), nullable=True),
    )
    op.execute("UPDATE ai_model_runs SET request_id = id::text WHERE request_id IS NULL")
    op.alter_column("ai_model_runs", "request_id", nullable=False)
    op.add_column(
        "ai_model_runs",
        sa.Column("endpoint_family", sa.String(length=50), nullable=True),
    )
    op.create_index(
        "ix_ai_model_runs_request_id",
        "ai_model_runs",
        ["request_id"],
        unique=False,
    )
    op.add_column(
        "ai_model_runs",
        sa.Column("prompt_name", sa.String(length=150), nullable=True),
    )
    op.add_column(
        "ai_model_runs",
        sa.Column(
            "repair_attempt_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.create_check_constraint(
        "ck_ai_model_runs_repair_attempt_count",
        "ai_model_runs",
        "repair_attempt_count >= 0",
    )
    op.add_column(
        "preflight_runs",
        sa.Column("seller_summary_json", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "preflight_runs",
        sa.Column("creator_revision_json", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "preflight_runs",
        sa.Column(
            "presentation_model_run_ids_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "preflight_runs",
        sa.Column(
            "presentation_source_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("preflight_runs", "presentation_source_json")
    op.drop_column("preflight_runs", "presentation_model_run_ids_json")
    op.drop_column("preflight_runs", "creator_revision_json")
    op.drop_column("preflight_runs", "seller_summary_json")
    op.drop_constraint(
        "ck_ai_model_runs_repair_attempt_count",
        "ai_model_runs",
        type_="check",
    )
    op.drop_column("ai_model_runs", "repair_attempt_count")
    op.drop_column("ai_model_runs", "prompt_name")
    op.drop_column("ai_model_runs", "endpoint_family")
    op.drop_index("ix_ai_model_runs_request_id", table_name="ai_model_runs")
    op.drop_column("ai_model_runs", "request_id")
