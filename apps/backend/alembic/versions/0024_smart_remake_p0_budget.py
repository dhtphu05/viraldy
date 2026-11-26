"""Atomic Smart Remake paid-attempt ledger, retaining uncertain billing exposure."""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0024_smart_remake_p0_budget"
down_revision = "0023_smart_remake_scene_repair"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "smart_remake_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("smart_remake_projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id"),
            nullable=False,
        ),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("idempotency_key", sa.String(200), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("stage", sa.String(20), nullable=False),
        sa.Column("purpose", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("provider", sa.String(100), nullable=False),
        sa.Column("model", sa.String(200), nullable=False),
        sa.Column("provider_task_id", sa.String(500), nullable=True),
        sa.Column("estimated_usd", sa.Numeric(18, 8), nullable=False),
        sa.Column("actual_usd", sa.Numeric(18, 8), nullable=True),
        *(
            sa.Column(name, postgresql.JSONB(), nullable=False)
            for name in (
                "profile_json",
                "metadata_json",
                "policy_json",
                "usage_json",
                "receipt_json",
                "error_json",
            )
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("project_id", "idempotency_key", name="uq_smart_remake_attempt_key"),
        sa.CheckConstraint("estimated_usd >= 0", name="ck_smart_remake_attempt_estimate"),
        sa.CheckConstraint(
            "actual_usd IS NULL OR actual_usd >= 0", name="ck_smart_remake_attempt_actual"
        ),
    )
    op.create_index("ix_smart_remake_attempts_project_id", "smart_remake_attempts", ["project_id"])


def downgrade() -> None:
    op.drop_table("smart_remake_attempts")
