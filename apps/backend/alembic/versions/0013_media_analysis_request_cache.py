from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013_media_request_cache"
down_revision: str | None = "0012_openai_provenance"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "evidence_items",
        sa.Column("analysis_request_hash", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "ix_evidence_items_workspace_analysis_request",
        "evidence_items",
        ["workspace_id", "asset_version_id", "analysis_request_hash"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_evidence_items_workspace_analysis_request",
        table_name="evidence_items",
    )
    op.drop_column("evidence_items", "analysis_request_hash")
