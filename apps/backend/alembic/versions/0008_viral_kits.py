from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0008_viral_kits"
down_revision: str | None = "0007_pattern_kits"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "products",
        sa.Column("product_context_version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.alter_column(
        "campaign_packs",
        "adaptation_run_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )

    op.create_table(
        "viral_kits",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id"),
            nullable=False,
        ),
        sa.Column(
            "product_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("products.id"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("objective", sa.String(length=100), nullable=False),
        sa.Column("platform", sa.String(length=100), nullable=False),
        sa.Column("target_market", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("latest_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("selected_concept_id", sa.String(length=120), nullable=True),
        sa.Column(
            "created_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "objective IN ("
            "'tiktok_shop_affiliate_test', 'tiktok_shop_organic_test', "
            "'small_paid_test', 'spark_candidate', 'ugc_paid_asset', "
            "'pod_gift_campaign', 'dropshipping_demo_test', 'creative_refresh'"
            ")",
            name="ck_viral_kits_objective",
        ),
        sa.CheckConstraint(
            "platform IN ('tiktok_shop', 'tiktok_organic', 'tiktok_paid')",
            name="ck_viral_kits_platform",
        ),
        sa.CheckConstraint(
            "status IN ("
            "'draft', 'generating', 'ready_for_review', 'concept_selected', "
            "'production_ready', 'testing', 'completed', 'archived', 'failed'"
            ")",
            name="ck_viral_kits_status",
        ),
        sa.CheckConstraint("latest_version >= 1", name="ck_viral_kits_latest_version"),
    )
    op.create_index("ix_viral_kits_workspace_id", "viral_kits", ["workspace_id"])
    op.create_index("ix_viral_kits_product_id", "viral_kits", ["product_id"])
    op.create_index(
        "ix_viral_kits_created_by_user_id",
        "viral_kits",
        ["created_by_user_id"],
    )
    op.create_index(
        "ix_viral_kits_workspace_status_created",
        "viral_kits",
        ["workspace_id", "status", "created_at"],
    )
    op.create_index(
        "ix_viral_kits_workspace_product",
        "viral_kits",
        ["workspace_id", "product_id"],
    )
    op.create_index(
        "ix_viral_kits_workspace_objective",
        "viral_kits",
        ["workspace_id", "objective"],
    )

    op.create_table(
        "viral_kit_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "viral_kit_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("viral_kits.id"),
            nullable=False,
        ),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("parent_version", sa.Integer(), nullable=True),
        sa.Column("change_reason", sa.Text(), nullable=True),
        sa.Column("schema_version", sa.String(length=100), nullable=False),
        sa.Column("product_context_version", sa.Integer(), nullable=False),
        sa.Column("product_snapshot_json", postgresql.JSONB(), nullable=False),
        sa.Column("viral_kit_json", postgresql.JSONB(), nullable=False),
        sa.Column(
            "model_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ai_model_runs.id"),
            nullable=True,
        ),
        sa.Column(
            "created_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("viral_kit_id", "version", name="uq_viral_kit_versions_version"),
        sa.CheckConstraint("version >= 1", name="ck_viral_kit_versions_version"),
        sa.CheckConstraint(
            "product_context_version >= 1",
            name="ck_viral_kit_versions_product_context_version",
        ),
    )
    op.create_index(
        "ix_viral_kit_versions_viral_kit_id",
        "viral_kit_versions",
        ["viral_kit_id"],
    )
    op.create_index(
        "ix_viral_kit_versions_workspace_id",
        "viral_kit_versions",
        ["workspace_id"],
    )
    op.create_index(
        "ix_viral_kit_versions_model_run_id",
        "viral_kit_versions",
        ["model_run_id"],
    )
    op.create_index(
        "ix_viral_kit_versions_workspace_created",
        "viral_kit_versions",
        ["workspace_id", "created_at"],
    )
    op.create_index(
        "ix_viral_kit_versions_kit_created",
        "viral_kit_versions",
        ["viral_kit_id", "created_at"],
    )

    op.create_table(
        "viral_kit_pattern_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id"),
            nullable=False,
        ),
        sa.Column(
            "viral_kit_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("viral_kit_versions.id"),
            nullable=False,
        ),
        sa.Column(
            "pattern_kit_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("pattern_kit_versions.id"),
            nullable=False,
        ),
        sa.Column("match_score", sa.Float(), nullable=False),
        sa.Column("applicability_status", sa.String(length=50), nullable=False),
        sa.Column("selection_reason", sa.Text(), nullable=False),
        sa.UniqueConstraint(
            "viral_kit_version_id",
            "pattern_kit_version_id",
            name="uq_viral_kit_pattern_links_version_pattern",
        ),
        sa.CheckConstraint("match_score >= 0 AND match_score <= 1", name="ck_viral_pattern_score"),
        sa.CheckConstraint(
            "applicability_status IN ('matched', 'partial', 'override', 'rejected')",
            name="ck_viral_pattern_status",
        ),
    )
    op.create_index(
        "ix_viral_kit_pattern_links_workspace_id",
        "viral_kit_pattern_links",
        ["workspace_id"],
    )
    op.create_index(
        "ix_viral_kit_pattern_links_viral_kit_version_id",
        "viral_kit_pattern_links",
        ["viral_kit_version_id"],
    )
    op.create_index(
        "ix_viral_kit_pattern_links_pattern_kit_version_id",
        "viral_kit_pattern_links",
        ["pattern_kit_version_id"],
    )
    op.create_index(
        "ix_viral_pattern_links_workspace",
        "viral_kit_pattern_links",
        ["workspace_id"],
    )
    op.create_index(
        "ix_viral_pattern_links_pattern",
        "viral_kit_pattern_links",
        ["workspace_id", "pattern_kit_version_id"],
    )

    op.create_table(
        "viral_kit_concept_actions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id"),
            nullable=False,
        ),
        sa.Column(
            "viral_kit_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("viral_kits.id"),
            nullable=False,
        ),
        sa.Column("viral_kit_version", sa.Integer(), nullable=False),
        sa.Column("concept_id", sa.String(length=120), nullable=False),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "actor_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "action IN ('selected', 'rejected', 'restored', 'campaign_pack_created')",
            name="ck_viral_concept_actions_action",
        ),
        sa.CheckConstraint(
            "viral_kit_version >= 1",
            name="ck_viral_concept_actions_version",
        ),
    )
    op.create_index(
        "ix_viral_kit_concept_actions_workspace_id",
        "viral_kit_concept_actions",
        ["workspace_id"],
    )
    op.create_index(
        "ix_viral_kit_concept_actions_viral_kit_id",
        "viral_kit_concept_actions",
        ["viral_kit_id"],
    )
    op.create_index(
        "ix_viral_concept_actions_workspace_created",
        "viral_kit_concept_actions",
        ["workspace_id", "created_at"],
    )
    op.create_index(
        "ix_viral_concept_actions_kit_created",
        "viral_kit_concept_actions",
        ["viral_kit_id", "created_at"],
    )

    op.create_table(
        "viral_kit_campaign_pack_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id"),
            nullable=False,
        ),
        sa.Column(
            "viral_kit_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("viral_kit_versions.id"),
            nullable=False,
        ),
        sa.Column("concept_id", sa.String(length=120), nullable=False),
        sa.Column(
            "campaign_pack_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("campaign_packs.id"),
            nullable=False,
        ),
        sa.Column(
            "campaign_pack_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("campaign_pack_versions.id"),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint(
            "viral_kit_version_id",
            "concept_id",
            "campaign_pack_id",
            name="uq_viral_campaign_pack_links_pack",
        ),
    )
    op.create_index(
        "ix_viral_kit_campaign_pack_links_workspace_id",
        "viral_kit_campaign_pack_links",
        ["workspace_id"],
    )
    op.create_index(
        "ix_viral_kit_campaign_pack_links_viral_kit_version_id",
        "viral_kit_campaign_pack_links",
        ["viral_kit_version_id"],
    )
    op.create_index(
        "ix_viral_kit_campaign_pack_links_campaign_pack_id",
        "viral_kit_campaign_pack_links",
        ["campaign_pack_id"],
    )
    op.create_index(
        "ix_viral_kit_campaign_pack_links_campaign_pack_version_id",
        "viral_kit_campaign_pack_links",
        ["campaign_pack_version_id"],
    )
    op.create_index(
        "ix_viral_campaign_pack_links_workspace",
        "viral_kit_campaign_pack_links",
        ["workspace_id"],
    )
    op.create_index(
        "ix_viral_campaign_pack_links_concept",
        "viral_kit_campaign_pack_links",
        ["viral_kit_version_id", "concept_id"],
    )


def downgrade() -> None:
    op.drop_table("viral_kit_campaign_pack_links")
    op.drop_table("viral_kit_concept_actions")
    op.drop_table("viral_kit_pattern_links")
    op.drop_table("viral_kit_versions")
    op.drop_table("viral_kits")
    op.alter_column(
        "campaign_packs",
        "adaptation_run_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
    op.drop_column("products", "product_context_version")
