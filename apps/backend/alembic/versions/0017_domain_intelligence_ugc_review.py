from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0017_domain_ugc_review"
down_revision: str | None = "0016_seed_tiktok_profiles"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _json_object() -> sa.TextClause:
    return sa.text("'{}'::jsonb")


def _json_array() -> sa.TextClause:
    return sa.text("'[]'::jsonb")


def _workspace_column() -> sa.Column:
    return sa.Column(
        "workspace_id",
        postgresql.UUID(as_uuid=True),
        sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )


def _created_at() -> sa.Column:
    return sa.Column(
        "created_at",
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        nullable=False,
    )


def _updated_at() -> sa.Column:
    return sa.Column(
        "updated_at",
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        nullable=False,
    )


def upgrade() -> None:
    _create_domain_registry()
    _create_ugc_review_results()
    _create_ugc_review_findings()
    _create_ugc_review_recommendation_events()
    _create_ugc_review_revisions()
    _create_ugc_review_comparisons()


def _create_domain_registry() -> None:
    op.create_table(
        "domain_policy_packs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("pack_name", sa.Text(), nullable=False),
        sa.Column("version", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.Text(), nullable=False),
        sa.Column("meta", postgresql.JSONB(), nullable=False, server_default=_json_object()),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=False),
        sa.Column(
            "imported_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        _updated_at(),
        sa.UniqueConstraint(
            "pack_name",
            "version",
            name="uq_domain_policy_packs_name_version",
        ),
    )
    op.create_index("ix_domain_policy_packs_status", "domain_policy_packs", ["status"])
    op.create_index(
        "ix_domain_policy_packs_imported_at",
        "domain_policy_packs",
        ["imported_at"],
    )

    op.create_table(
        "domain_policy_sources",
        sa.Column("source_id", sa.Text(), primary_key=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("publisher", sa.Text(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("source_type", sa.Text(), nullable=False),
        sa.Column("source_date", sa.Text(), nullable=True),
        sa.Column("evidence_strength", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=False),
        sa.Column(
            "imported_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        _updated_at(),
        sa.CheckConstraint(
            "evidence_strength >= 1 AND evidence_strength <= 5",
            name="ck_domain_policy_sources_evidence_strength",
        ),
    )
    op.create_index(
        "ix_domain_policy_sources_type_publisher",
        "domain_policy_sources",
        ["source_type", "publisher"],
    )

    op.create_table(
        "domain_policy_rules",
        sa.Column("code", sa.Text(), primary_key=True),
        sa.Column(
            "pack_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("domain_policy_packs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("domain", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("rule_type", sa.Text(), nullable=False),
        sa.Column("severity", sa.Text(), nullable=False),
        sa.Column(
            "enabled_for_mvp",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "applicability",
            postgresql.JSONB(),
            nullable=False,
            server_default=_json_object(),
        ),
        sa.Column(
            "required_conditions",
            postgresql.JSONB(),
            nullable=False,
            server_default=_json_object(),
        ),
        sa.Column(
            "implementation",
            postgresql.JSONB(),
            nullable=False,
            server_default=_json_object(),
        ),
        sa.Column(
            "source_ids",
            postgresql.JSONB(),
            nullable=False,
            server_default=_json_array(),
        ),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=False),
        _created_at(),
        _updated_at(),
    )
    op.create_index("ix_domain_policy_rules_pack_id", "domain_policy_rules", ["pack_id"])
    op.create_index(
        "ix_domain_policy_rules_domain_enabled",
        "domain_policy_rules",
        ["domain", "enabled_for_mvp"],
    )

    op.create_table(
        "domain_creative_patterns",
        sa.Column("code", sa.Text(), primary_key=True),
        sa.Column(
            "pack_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("domain_policy_packs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("finding_classification", sa.Text(), nullable=False),
        sa.Column("performance_evidence_status", sa.Text(), nullable=True),
        sa.Column(
            "enabled_for_mvp",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=False),
        _created_at(),
        _updated_at(),
    )
    op.create_index(
        "ix_domain_creative_patterns_pack_enabled",
        "domain_creative_patterns",
        ["pack_id", "enabled_for_mvp"],
    )

    op.create_table(
        "domain_mistake_definitions",
        sa.Column("code", sa.Text(), primary_key=True),
        sa.Column(
            "pack_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("domain_policy_packs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("severity", sa.Text(), nullable=False),
        sa.Column("editable_or_reshoot", sa.Text(), nullable=False),
        sa.Column(
            "enabled_for_mvp",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=False),
        _created_at(),
        _updated_at(),
    )
    op.create_index(
        "ix_domain_mistake_definitions_pack_enabled",
        "domain_mistake_definitions",
        ["pack_id", "enabled_for_mvp"],
    )

    op.create_table(
        "domain_uncertainties",
        sa.Column("code", sa.Text(), primary_key=True),
        sa.Column(
            "pack_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("domain_policy_packs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("topic", sa.Text(), nullable=False),
        sa.Column("classification", sa.Text(), nullable=False),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=False),
        _created_at(),
        _updated_at(),
    )
    op.create_index("ix_domain_uncertainties_pack_id", "domain_uncertainties", ["pack_id"])

    op.create_table(
        "domain_policy_rule_sources",
        sa.Column(
            "rule_code",
            sa.Text(),
            sa.ForeignKey("domain_policy_rules.code", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "source_id",
            sa.Text(),
            sa.ForeignKey("domain_policy_sources.source_id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )
    op.create_index(
        "ix_domain_policy_rule_sources_source_id",
        "domain_policy_rule_sources",
        ["source_id"],
    )


def _create_ugc_review_results() -> None:
    op.create_table(
        "ugc_review_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        _workspace_column(),
        sa.Column(
            "processing_job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("processing_jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "asset_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("assets.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "asset_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("asset_versions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("headline", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("recommended_next_action", sa.Text(), nullable=False),
        sa.Column("overall_confidence", sa.Text(), nullable=False),
        sa.Column(
            "strengths_to_keep",
            postgresql.JSONB(),
            nullable=False,
            server_default=_json_array(),
        ),
        sa.Column("creator_revision_message", sa.Text(), nullable=False),
        sa.Column("policy_pack_version", sa.Text(), nullable=False),
        sa.Column(
            "request_context",
            postgresql.JSONB(),
            nullable=False,
            server_default=_json_object(),
        ),
        sa.Column(
            "analysis_provenance",
            postgresql.JSONB(),
            nullable=False,
            server_default=_json_object(),
        ),
        sa.Column(
            "result_payload",
            postgresql.JSONB(),
            nullable=False,
            server_default=_json_object(),
        ),
        _created_at(),
        _updated_at(),
        sa.UniqueConstraint(
            "processing_job_id",
            name="uq_ugc_review_results_processing_job_id",
        ),
        sa.CheckConstraint(
            "recommended_next_action IN ('use_as_is', 'revise', 'reshoot_scene', "
            "'confirm_information', 'request_better_media')",
            name="ck_ugc_review_results_next_action",
        ),
        sa.CheckConstraint(
            "overall_confidence IN ('high', 'medium', 'low')",
            name="ck_ugc_review_results_confidence",
        ),
    )
    op.create_index(
        "ix_ugc_review_results_workspace_created",
        "ugc_review_results",
        ["workspace_id", "created_at"],
    )
    op.create_index("ix_ugc_review_results_asset_id", "ugc_review_results", ["asset_id"])
    op.create_index(
        "ix_ugc_review_results_asset_version_id",
        "ugc_review_results",
        ["asset_version_id"],
    )


def _create_ugc_review_findings() -> None:
    op.create_table(
        "ugc_review_findings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        _workspace_column(),
        sa.Column(
            "processing_job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("processing_jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "rule_code",
            sa.Text(),
            sa.ForeignKey("domain_policy_rules.code", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "mistake_code",
            sa.Text(),
            sa.ForeignKey("domain_mistake_definitions.code", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("recommendation_id", sa.Text(), nullable=False),
        sa.Column("recommendation_group", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("owner_role", sa.Text(), nullable=False),
        sa.Column("fix_type", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Text(), nullable=False),
        sa.Column(
            "evidence",
            postgresql.JSONB(),
            nullable=False,
            server_default=_json_array(),
        ),
        sa.Column(
            "recommendation_payload",
            postgresql.JSONB(),
            nullable=False,
            server_default=_json_object(),
        ),
        _created_at(),
        sa.CheckConstraint(
            "recommendation_group IN ('fix_first', 'improve', 'confirm')",
            name="ck_ugc_review_findings_recommendation_group",
        ),
        sa.CheckConstraint(
            "owner_role IN ('seller', 'creator', 'editor')",
            name="ck_ugc_review_findings_owner_role",
        ),
        sa.CheckConstraint(
            "fix_type IS NULL OR fix_type IN ('edit_existing_footage', 'add_overlay', "
            "'replace_copy', 'reshoot_scene', 'confirm_seller_input', "
            "'request_better_media')",
            name="ck_ugc_review_findings_fix_type",
        ),
        sa.CheckConstraint(
            "confidence IN ('high', 'medium', 'low')",
            name="ck_ugc_review_findings_confidence",
        ),
        sa.UniqueConstraint(
            "processing_job_id",
            "recommendation_id",
            name="uq_ugc_review_findings_job_recommendation",
        ),
    )
    op.create_index(
        "ix_ugc_review_findings_workspace_job",
        "ugc_review_findings",
        ["workspace_id", "processing_job_id"],
    )
    op.create_index(
        "ix_ugc_review_findings_job_group",
        "ugc_review_findings",
        ["processing_job_id", "recommendation_group"],
    )
    op.create_index("ix_ugc_review_findings_rule_code", "ugc_review_findings", ["rule_code"])
    op.create_index(
        "ix_ugc_review_findings_mistake_code",
        "ugc_review_findings",
        ["mistake_code"],
    )


def _create_ugc_review_recommendation_events() -> None:
    op.create_table(
        "ugc_review_recommendation_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        _workspace_column(),
        sa.Column(
            "processing_job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("processing_jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "finding_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ugc_review_findings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("seller_action", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        _created_at(),
        sa.CheckConstraint(
            "seller_action IN ('accepted', 'ignored', 'not_applicable', "
            "'sent_to_creator', 'marked_completed')",
            name="ck_ugc_review_recommendation_events_seller_action",
        ),
    )
    op.create_index(
        "ix_ugc_review_recommendation_events_workspace_job_created",
        "ugc_review_recommendation_events",
        ["workspace_id", "processing_job_id", "created_at"],
    )
    op.create_index(
        "ix_ugc_review_recommendation_events_finding_id",
        "ugc_review_recommendation_events",
        ["finding_id"],
    )


def _create_ugc_review_revisions() -> None:
    op.create_table(
        "ugc_review_revisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        _workspace_column(),
        sa.Column(
            "parent_processing_job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("processing_jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "child_processing_job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("processing_jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "parent_asset_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("asset_versions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "child_asset_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("asset_versions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        _created_at(),
        sa.UniqueConstraint(
            "child_processing_job_id",
            name="uq_ugc_review_revisions_child_processing_job_id",
        ),
        sa.CheckConstraint(
            "parent_processing_job_id <> child_processing_job_id",
            name="ck_ugc_review_revisions_distinct_jobs",
        ),
    )
    op.create_index(
        "ix_ugc_review_revisions_workspace_parent_created",
        "ugc_review_revisions",
        ["workspace_id", "parent_processing_job_id", "created_at"],
    )
    op.create_index(
        "ix_ugc_review_revisions_parent_asset_version_id",
        "ugc_review_revisions",
        ["parent_asset_version_id"],
    )
    op.create_index(
        "ix_ugc_review_revisions_child_asset_version_id",
        "ugc_review_revisions",
        ["child_asset_version_id"],
    )


def _create_ugc_review_comparisons() -> None:
    op.create_table(
        "ugc_review_comparisons",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        _workspace_column(),
        sa.Column(
            "parent_processing_job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("processing_jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "child_processing_job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("processing_jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "resolved_findings",
            postgresql.JSONB(),
            nullable=False,
            server_default=_json_array(),
        ),
        sa.Column(
            "still_open_findings",
            postgresql.JSONB(),
            nullable=False,
            server_default=_json_array(),
        ),
        sa.Column(
            "new_findings",
            postgresql.JSONB(),
            nullable=False,
            server_default=_json_array(),
        ),
        sa.Column(
            "strengths_preserved",
            postgresql.JSONB(),
            nullable=False,
            server_default=_json_array(),
        ),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column(
            "comparison_payload",
            postgresql.JSONB(),
            nullable=False,
            server_default=_json_object(),
        ),
        _created_at(),
        sa.UniqueConstraint(
            "parent_processing_job_id",
            "child_processing_job_id",
            name="uq_ugc_review_comparisons_job_pair",
        ),
        sa.CheckConstraint(
            "parent_processing_job_id <> child_processing_job_id",
            name="ck_ugc_review_comparisons_distinct_jobs",
        ),
    )
    op.create_index(
        "ix_ugc_review_comparisons_workspace_parent_created",
        "ugc_review_comparisons",
        ["workspace_id", "parent_processing_job_id", "created_at"],
    )
    op.create_index(
        "ix_ugc_review_comparisons_child_processing_job_id",
        "ugc_review_comparisons",
        ["child_processing_job_id"],
    )


def downgrade() -> None:
    op.drop_table("ugc_review_comparisons")
    op.drop_table("ugc_review_revisions")
    op.drop_table("ugc_review_recommendation_events")
    op.drop_table("ugc_review_findings")
    op.drop_table("ugc_review_results")
    op.drop_table("domain_policy_rule_sources")
    op.drop_table("domain_uncertainties")
    op.drop_table("domain_mistake_definitions")
    op.drop_table("domain_creative_patterns")
    op.drop_table("domain_policy_rules")
    op.drop_table("domain_policy_sources")
    op.drop_table("domain_policy_packs")
