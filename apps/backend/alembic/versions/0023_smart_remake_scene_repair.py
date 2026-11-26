"""Persist Smart Remake projects, immutable scene versions and controlled operations."""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0023_smart_remake_scene_repair"
down_revision = "0022_merge_auth_market"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "smart_remake_projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id"),
            nullable=False,
        ),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("state_json", postgresql.JSONB(), nullable=False),
        sa.Column("context_json", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index(
        "ix_smart_remake_projects_workspace_id", "smart_remake_projects", ["workspace_id"]
    )
    op.create_table(
        "smart_remake_operations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("smart_remake_projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("idempotency_key", sa.String(200), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("result_json", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("project_id", "idempotency_key", name="uq_smart_remake_operation_key"),
    )
    op.create_index(
        "ix_smart_remake_operations_project_id", "smart_remake_operations", ["project_id"]
    )


def downgrade() -> None:
    op.drop_table("smart_remake_operations")
    op.drop_table("smart_remake_projects")
