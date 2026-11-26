"""Join the independently published auth and market-intelligence histories."""

from __future__ import annotations

revision: str = "0022_merge_auth_market"
down_revision: tuple[str, str] = ("0020_creative_family_candidates", "0021_password_auth")
branch_labels: None = None
depends_on: None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
