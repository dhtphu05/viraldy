from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0014_user_phone_number"
down_revision: str | None = "0013_media_request_cache"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("phone_number", sa.String(length=16), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "phone_number")
