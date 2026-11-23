from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0021_password_auth"
down_revision: str | None = "0017_domain_ugc_review"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    uuid_type = postgresql.UUID(as_uuid=True)
    op.create_table(
        "password_credentials",
        sa.Column("user_id", uuid_type, sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False, unique=True),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.CheckConstraint("email = lower(email)", name="ck_password_credentials_email_lowercase"),
    )
    op.create_table(
        "password_sessions",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("user_id", uuid_type, sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_password_sessions_user_id", "password_sessions", ["user_id"])
    op.create_table(
        "password_refresh_tokens",
        sa.Column("token_hash", sa.String(64), primary_key=True),
        sa.Column("session_id", uuid_type, sa.ForeignKey("password_sessions.id"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_password_refresh_tokens_session_id", "password_refresh_tokens", ["session_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_password_refresh_tokens_session_id", table_name="password_refresh_tokens")
    op.drop_table("password_refresh_tokens")
    op.drop_index("ix_password_sessions_user_id", table_name="password_sessions")
    op.drop_table("password_sessions")
    op.drop_table("password_credentials")
