from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0011_deletion_audit"
down_revision: str | None = "0010_job_contract_normalization"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "deletion_audit_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("resource_type", sa.String(length=50), nullable=False),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("initiated_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column(
            "deleted_object_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "deleted_row_counts_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("safe_error_code", sa.String(length=100), nullable=True),
        sa.Column("safe_error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "resource_type IN ("
            "'workspace', 'product', 'asset', 'reference', 'creative_dna', "
            "'pattern_kit', 'viral_kit', 'campaign_pack'"
            ")",
            name="ck_deletion_audit_resource_type",
        ),
        sa.CheckConstraint(
            "status IN ('processing', 'storage_cleanup_pending', 'succeeded', 'failed')",
            name="ck_deletion_audit_status",
        ),
    )
    op.create_index(
        "ix_deletion_audit_workspace_created",
        "deletion_audit_records",
        ["workspace_id", "created_at"],
    )
    op.create_table(
        "storage_deletion_batches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_type", sa.String(length=50), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "object_keys_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column(
            "attempt_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "deleted_object_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("safe_error_code", sa.String(length=100), nullable=True),
        sa.Column("safe_error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "source_type IN ('hard_delete', 'retention')",
            name="ck_storage_deletion_batch_source_type",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'succeeded')",
            name="ck_storage_deletion_batch_status",
        ),
    )
    op.create_index(
        "ix_storage_deletion_batches_status_created",
        "storage_deletion_batches",
        ["status", "created_at"],
    )
    op.create_index(
        "ix_storage_deletion_batches_workspace_status",
        "storage_deletion_batches",
        ["workspace_id", "status"],
    )


def downgrade() -> None:
    op.drop_table("storage_deletion_batches")
    op.drop_table("deletion_audit_records")
