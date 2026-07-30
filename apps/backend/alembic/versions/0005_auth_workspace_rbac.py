from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005_auth_workspace_rbac"
down_revision: str | None = "0004_creative_domain_contracts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True))
    op.execute("UPDATE workspace_members SET role = 'member' WHERE role = 'editor'")
    op.create_check_constraint(
        "ck_users_status",
        "users",
        "status IN ('active', 'suspended', 'deleted')",
    )
    op.create_check_constraint(
        "ck_workspace_members_role",
        "workspace_members",
        "role IN ('owner', 'admin', 'member', 'viewer')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_workspace_members_role", "workspace_members", type_="check")
    op.drop_constraint("ck_users_status", "users", type_="check")
    op.drop_column("users", "last_login_at")
