from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0007_pattern_kits"
down_revision: str | None = "0006_feedback_events_model_runs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _jsonb_default_array() -> sa.TextClause:
    return sa.text("'[]'::jsonb")


def upgrade() -> None:
    op.create_table(
        "pattern_kits",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("kind", sa.String(length=100), nullable=False),
        sa.Column("scope", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("primary_category", sa.String(length=100), nullable=True),
        sa.Column(
            "target_platforms_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=_jsonb_default_array(),
        ),
        sa.Column(
            "target_markets_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=_jsonb_default_array(),
        ),
        sa.Column(
            "objectives_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=_jsonb_default_array(),
        ),
        sa.Column("latest_version", sa.Integer(), nullable=False, server_default="1"),
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
            "kind IN ("
            "'single_asset_abstraction', 'multi_asset_cluster', "
            "'workspace_learned_pattern', 'category_playbook'"
            ")",
            name="ck_pattern_kits_kind",
        ),
        sa.CheckConstraint(
            "scope IN ('workspace_private', 'product_specific')",
            name="ck_pattern_kits_scope",
        ),
        sa.CheckConstraint(
            "status IN ('candidate', 'reviewed', 'validated', 'deprecated', 'archived')",
            name="ck_pattern_kits_status",
        ),
        sa.CheckConstraint("latest_version >= 1", name="ck_pattern_kits_latest_version"),
    )
    op.create_index("ix_pattern_kits_workspace_id", "pattern_kits", ["workspace_id"])
    op.create_index(
        "ix_pattern_kits_created_by_user_id",
        "pattern_kits",
        ["created_by_user_id"],
    )
    op.create_index(
        "ix_pattern_kits_workspace_status_created",
        "pattern_kits",
        ["workspace_id", "status", "created_at"],
    )
    op.create_index(
        "ix_pattern_kits_workspace_kind",
        "pattern_kits",
        ["workspace_id", "kind"],
    )
    op.create_index(
        "ix_pattern_kits_workspace_category",
        "pattern_kits",
        ["workspace_id", "primary_category"],
    )

    op.create_table(
        "pattern_kit_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "pattern_kit_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("pattern_kits.id"),
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
        sa.Column("pattern_json", postgresql.JSONB(), nullable=False),
        sa.Column("overall_confidence", sa.String(length=50), nullable=False),
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
        sa.UniqueConstraint("pattern_kit_id", "version", name="uq_pattern_kit_versions_version"),
        sa.CheckConstraint("version >= 1", name="ck_pattern_kit_versions_version"),
    )
    op.create_index(
        "ix_pattern_kit_versions_pattern_kit_id",
        "pattern_kit_versions",
        ["pattern_kit_id"],
    )
    op.create_index(
        "ix_pattern_kit_versions_workspace_id",
        "pattern_kit_versions",
        ["workspace_id"],
    )
    op.create_index(
        "ix_pattern_kit_versions_model_run_id",
        "pattern_kit_versions",
        ["model_run_id"],
    )
    op.create_index(
        "ix_pattern_kit_versions_workspace_created",
        "pattern_kit_versions",
        ["workspace_id", "created_at"],
    )
    op.create_index(
        "ix_pattern_kit_versions_kit_created",
        "pattern_kit_versions",
        ["pattern_kit_id", "created_at"],
    )

    op.create_table(
        "pattern_kit_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id"),
            nullable=False,
        ),
        sa.Column(
            "pattern_kit_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("pattern_kit_versions.id"),
            nullable=False,
        ),
        sa.Column(
            "creative_dna_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("creative_dna_versions.id"),
            nullable=False,
        ),
        sa.Column(
            "asset_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("asset_versions.id"),
            nullable=False,
        ),
        sa.Column("source_order", sa.Integer(), nullable=False),
        sa.UniqueConstraint(
            "pattern_kit_version_id",
            "creative_dna_version_id",
            name="uq_pattern_kit_sources_version_dna",
        ),
        sa.UniqueConstraint(
            "pattern_kit_version_id",
            "source_order",
            name="uq_pattern_kit_sources_version_order",
        ),
        sa.CheckConstraint("source_order >= 1", name="ck_pattern_kit_sources_order"),
    )
    op.create_index("ix_pattern_kit_sources_workspace_id", "pattern_kit_sources", ["workspace_id"])
    op.create_index(
        "ix_pattern_kit_sources_pattern_kit_version_id",
        "pattern_kit_sources",
        ["pattern_kit_version_id"],
    )
    op.create_index(
        "ix_pattern_kit_sources_creative_dna_version_id",
        "pattern_kit_sources",
        ["creative_dna_version_id"],
    )
    op.create_index(
        "ix_pattern_kit_sources_asset_version_id",
        "pattern_kit_sources",
        ["asset_version_id"],
    )
    op.create_index(
        "ix_pattern_kit_sources_workspace_dna",
        "pattern_kit_sources",
        ["workspace_id", "creative_dna_version_id"],
    )

    op.create_table(
        "pattern_kit_evidence_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id"),
            nullable=False,
        ),
        sa.Column(
            "pattern_kit_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("pattern_kit_versions.id"),
            nullable=False,
        ),
        sa.Column(
            "evidence_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("evidence_items.id"),
            nullable=False,
        ),
        sa.Column("feature_path", sa.String(length=500), nullable=False),
        sa.UniqueConstraint(
            "pattern_kit_version_id",
            "evidence_id",
            "feature_path",
            name="uq_pattern_kit_evidence_links_ref",
        ),
        sa.CheckConstraint(
            "char_length(feature_path) > 0",
            name="ck_pattern_kit_evidence_links_feature_path",
        ),
    )
    op.create_index(
        "ix_pattern_kit_evidence_links_workspace",
        "pattern_kit_evidence_links",
        ["workspace_id"],
    )
    op.create_index(
        "ix_pattern_kit_evidence_links_pattern_kit_version_id",
        "pattern_kit_evidence_links",
        ["pattern_kit_version_id"],
    )
    op.create_index(
        "ix_pattern_kit_evidence_links_evidence",
        "pattern_kit_evidence_links",
        ["evidence_id"],
    )

    op.create_table(
        "pattern_kit_actions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id"),
            nullable=False,
        ),
        sa.Column(
            "pattern_kit_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("pattern_kits.id"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
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
            "action IN ('reviewed', 'validated', 'deprecated', 'archived', 'restored')",
            name="ck_pattern_kit_actions_action",
        ),
    )
    op.create_index("ix_pattern_kit_actions_workspace_id", "pattern_kit_actions", ["workspace_id"])
    op.create_index(
        "ix_pattern_kit_actions_pattern_kit_id",
        "pattern_kit_actions",
        ["pattern_kit_id"],
    )
    op.create_index(
        "ix_pattern_kit_actions_workspace_created",
        "pattern_kit_actions",
        ["workspace_id", "created_at"],
    )
    op.create_index(
        "ix_pattern_kit_actions_kit_created",
        "pattern_kit_actions",
        ["pattern_kit_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_table("pattern_kit_actions")
    op.drop_table("pattern_kit_evidence_links")
    op.drop_table("pattern_kit_sources")
    op.drop_table("pattern_kit_versions")
    op.drop_table("pattern_kits")
