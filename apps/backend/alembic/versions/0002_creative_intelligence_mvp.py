from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0002_creative_intelligence_mvp"
down_revision: str | None = "0001_initial_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    ]


def upgrade() -> None:
    op.create_table(
        "reference_boards",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id"),
            nullable=False,
        ),
        sa.Column(
            "product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("products.id"), nullable=True
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "board_type", sa.String(length=100), nullable=False, server_default="creative_research"
        ),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="active"),
        sa.Column(
            "created_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        *_timestamps(),
    )
    op.create_index("ix_reference_boards_workspace_id", "reference_boards", ["workspace_id"])
    op.create_index("ix_reference_boards_product_id", "reference_boards", ["product_id"])
    op.create_index("ix_reference_boards_created_at", "reference_boards", ["created_at"])
    op.create_index(
        "ix_reference_boards_workspace_created", "reference_boards", ["workspace_id", "created_at"]
    )

    op.create_table(
        "references",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id"),
            nullable=False,
        ),
        sa.Column(
            "board_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("reference_boards.id"),
            nullable=False,
        ),
        sa.Column(
            "product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("products.id"), nullable=True
        ),
        sa.Column(
            "asset_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("assets.id"), nullable=False
        ),
        sa.Column("source_platform", sa.String(length=100), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="ready"),
        sa.Column(
            "created_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        *_timestamps(),
    )
    op.create_index("ix_references_workspace_id", "references", ["workspace_id"])
    op.create_index("ix_references_board_id", "references", ["board_id"])
    op.create_index("ix_references_product_id", "references", ["product_id"])
    op.create_index("ix_references_asset_id", "references", ["asset_id"])
    op.create_index("ix_references_created_at", "references", ["created_at"])
    op.create_index("ix_references_workspace_created", "references", ["workspace_id", "created_at"])

    op.create_table(
        "media_artifacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id"),
            nullable=False,
        ),
        sa.Column(
            "asset_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("asset_versions.id"),
            nullable=False,
        ),
        sa.Column("artifact_type", sa.String(length=100), nullable=False),
        sa.Column("storage_key", sa.Text(), nullable=True),
        sa.Column("payload_json", postgresql.JSONB(), nullable=True),
        sa.Column("provider", sa.String(length=100), nullable=False),
        sa.Column("model_version", sa.String(length=100), nullable=True),
        sa.Column("analysis_mode", sa.String(length=50), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_media_artifacts_workspace_id", "media_artifacts", ["workspace_id"])
    op.create_index("ix_media_artifacts_asset_version_id", "media_artifacts", ["asset_version_id"])
    op.create_index(
        "ix_media_artifacts_workspace_version_type",
        "media_artifacts",
        ["workspace_id", "asset_version_id", "artifact_type"],
    )

    op.create_table(
        "evidence_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id"),
            nullable=False,
        ),
        sa.Column(
            "asset_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("asset_versions.id"),
            nullable=False,
        ),
        sa.Column("analysis_run_type", sa.String(length=100), nullable=False),
        sa.Column("analysis_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("evidence_type", sa.String(length=100), nullable=False),
        sa.Column("start_ms", sa.BigInteger(), nullable=True),
        sa.Column("end_ms", sa.BigInteger(), nullable=True),
        sa.Column("frame_storage_key", sa.Text(), nullable=True),
        sa.Column("value_json", postgresql.JSONB(), nullable=False),
        sa.Column("confidence", sa.Numeric(), nullable=True),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("provider", sa.String(length=100), nullable=True),
        sa.Column("model_version", sa.String(length=100), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_evidence_items_workspace_id", "evidence_items", ["workspace_id"])
    op.create_index("ix_evidence_items_asset_version_id", "evidence_items", ["asset_version_id"])
    op.create_index(
        "ix_evidence_items_workspace_version_type",
        "evidence_items",
        ["workspace_id", "asset_version_id", "evidence_type"],
    )

    op.create_table(
        "creative_dna_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id"),
            nullable=False,
        ),
        sa.Column(
            "reference_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("references.id"),
            nullable=True,
        ),
        sa.Column(
            "asset_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("asset_versions.id"),
            nullable=False,
        ),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("dna_json", postgresql.JSONB(), nullable=False),
        sa.Column("confidence", sa.String(length=50), nullable=False),
        sa.Column("analysis_mode", sa.String(length=50), nullable=False),
        sa.Column("taxonomy_version", sa.String(length=100), nullable=False),
        sa.Column("model_version", sa.String(length=100), nullable=True),
        sa.Column("prompt_version", sa.String(length=100), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint(
            "asset_version_id", "version_number", name="uq_creative_dna_asset_version_number"
        ),
    )
    op.create_index(
        "ix_creative_dna_versions_workspace_id", "creative_dna_versions", ["workspace_id"]
    )
    op.create_index(
        "ix_creative_dna_versions_reference_id", "creative_dna_versions", ["reference_id"]
    )
    op.create_index(
        "ix_creative_dna_versions_asset_version_id", "creative_dna_versions", ["asset_version_id"]
    )

    op.create_table(
        "tiktok_score_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id"),
            nullable=False,
        ),
        sa.Column(
            "asset_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("asset_versions.id"),
            nullable=False,
        ),
        sa.Column(
            "creative_dna_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("creative_dna_versions.id"),
            nullable=True,
        ),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("structural_score", sa.Numeric(), nullable=False, server_default="0"),
        sa.Column("confidence", sa.String(length=50), nullable=False, server_default="low"),
        sa.Column("action_label", sa.String(length=100), nullable=False, server_default="pending"),
        sa.Column(
            "dimension_scores_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "strengths_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "blockers_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "fixes_json", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")
        ),
        sa.Column(
            "evidence_ids_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("analysis_mode", sa.String(length=50), nullable=False),
        sa.Column("rubric_version", sa.String(length=100), nullable=False),
        sa.Column("rule_version", sa.String(length=100), nullable=False),
        sa.Column("model_version", sa.String(length=100), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_tiktok_score_runs_workspace_id", "tiktok_score_runs", ["workspace_id"])
    op.create_index(
        "ix_tiktok_score_runs_asset_version_id", "tiktok_score_runs", ["asset_version_id"]
    )

    op.create_table(
        "adaptation_runs",
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
        sa.Column(
            "creative_dna_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("creative_dna_versions.id"),
            nullable=False,
        ),
        sa.Column("objective", sa.String(length=255), nullable=False),
        sa.Column("target_market", sa.String(length=100), nullable=False),
        sa.Column(
            "target_buyer_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "constraints_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "result_json", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        sa.Column("analysis_mode", sa.String(length=50), nullable=False),
        sa.Column("model_version", sa.String(length=100), nullable=True),
        sa.Column("prompt_version", sa.String(length=100), nullable=False),
        sa.Column(
            "created_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_adaptation_runs_workspace_id", "adaptation_runs", ["workspace_id"])
    op.create_index("ix_adaptation_runs_product_id", "adaptation_runs", ["product_id"])
    op.create_index(
        "ix_adaptation_runs_creative_dna_version_id", "adaptation_runs", ["creative_dna_version_id"]
    )

    op.create_table(
        "campaign_packs",
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
        sa.Column(
            "adaptation_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("adaptation_runs.id"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="active"),
        sa.Column("current_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        *_timestamps(),
    )
    op.create_index("ix_campaign_packs_workspace_id", "campaign_packs", ["workspace_id"])
    op.create_index("ix_campaign_packs_product_id", "campaign_packs", ["product_id"])
    op.create_index("ix_campaign_packs_adaptation_run_id", "campaign_packs", ["adaptation_run_id"])

    op.create_table(
        "campaign_pack_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "campaign_pack_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("campaign_packs.id"),
            nullable=False,
        ),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("brief_json", postgresql.JSONB(), nullable=False),
        sa.Column("change_note", sa.Text(), nullable=True),
        sa.Column(
            "created_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint(
            "campaign_pack_id", "version_number", name="uq_campaign_pack_versions_pack_number"
        ),
    )
    op.create_index(
        "ix_campaign_pack_versions_campaign_pack_id", "campaign_pack_versions", ["campaign_pack_id"]
    )

    op.create_table(
        "preflight_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id"),
            nullable=False,
        ),
        sa.Column(
            "ugc_asset_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("asset_versions.id"),
            nullable=False,
        ),
        sa.Column(
            "campaign_pack_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("campaign_pack_versions.id"),
            nullable=False,
        ),
        sa.Column(
            "structural_score_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tiktok_score_runs.id"),
            nullable=True,
        ),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("structural_score", sa.Numeric(), nullable=False, server_default="0"),
        sa.Column("brief_alignment_score", sa.Numeric(), nullable=False, server_default="0"),
        sa.Column("preflight_score", sa.Numeric(), nullable=False, server_default="0"),
        sa.Column("confidence", sa.String(length=50), nullable=False, server_default="low"),
        sa.Column("action_label", sa.String(length=100), nullable=False, server_default="pending"),
        sa.Column(
            "dimension_scores_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "brief_alignment_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "strengths_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "blockers_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "fixes_json", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")
        ),
        sa.Column("revision_message", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "evidence_ids_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("analysis_mode", sa.String(length=50), nullable=False),
        sa.Column("rubric_version", sa.String(length=100), nullable=False),
        sa.Column("rule_version", sa.String(length=100), nullable=False),
        sa.Column("model_version", sa.String(length=100), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_preflight_runs_workspace_id", "preflight_runs", ["workspace_id"])
    op.create_index(
        "ix_preflight_runs_ugc_asset_version_id", "preflight_runs", ["ugc_asset_version_id"]
    )
    op.create_index(
        "ix_preflight_runs_campaign_pack_version_id", "preflight_runs", ["campaign_pack_version_id"]
    )


def downgrade() -> None:
    op.drop_table("preflight_runs")
    op.drop_table("campaign_pack_versions")
    op.drop_table("campaign_packs")
    op.drop_table("adaptation_runs")
    op.drop_table("tiktok_score_runs")
    op.drop_table("creative_dna_versions")
    op.drop_table("evidence_items")
    op.drop_table("media_artifacts")
    op.drop_table("references")
    op.drop_table("reference_boards")
