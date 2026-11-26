from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0018_tiktok_commercial_content"
down_revision: str | None = "0017_domain_ugc_review"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _json_object() -> sa.TextClause:
    return sa.text("'{}'::jsonb")


def upgrade() -> None:
    uuid_type = postgresql.UUID(as_uuid=True)
    op.create_table(
        "external_source_records",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("workspace_id", uuid_type, sa.ForeignKey("workspaces.id"), nullable=True),
        sa.Column("provider", sa.String(100), nullable=False),
        sa.Column("provider_entity_type", sa.String(50), nullable=False),
        sa.Column("provider_entity_id", sa.String(255), nullable=False),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=False),
        sa.Column("schema_version", sa.String(100), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=True),
        sa.Column(
            "request_context", postgresql.JSONB(), nullable=False, server_default=_json_object()
        ),
        sa.Column("provider_log_id", sa.String(255), nullable=True),
        sa.UniqueConstraint(
            "provider",
            "provider_entity_type",
            "provider_entity_id",
            name="uq_external_source_records_identity",
        ),
    )
    op.create_index(
        "ix_external_source_records_workspace_id", "external_source_records", ["workspace_id"]
    )
    op.create_index(
        "ix_external_source_records_workspace_fetched",
        "external_source_records",
        ["workspace_id", "fetched_at"],
    )

    op.create_table(
        "creative_source_links",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("creative_asset_id", uuid_type, sa.ForeignKey("assets.id"), nullable=False),
        sa.Column("provider", sa.String(100), nullable=False),
        sa.Column("provider_entity_type", sa.String(50), nullable=False),
        sa.Column("provider_entity_id", sa.String(255), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column(
            "source_metadata", postgresql.JSONB(), nullable=False, server_default=_json_object()
        ),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint(
            "creative_asset_id",
            "provider",
            "provider_entity_type",
            "provider_entity_id",
            name="uq_creative_source_links_identity",
        ),
    )
    op.create_index(
        "ix_creative_source_links_creative_asset_id", "creative_source_links", ["creative_asset_id"]
    )
    op.create_index(
        "ix_creative_source_links_asset", "creative_source_links", ["creative_asset_id"]
    )

    op.create_table(
        "creative_families",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("workspace_id", uuid_type, sa.ForeignKey("workspaces.id"), nullable=True),
        sa.Column("scope", sa.String(30), nullable=False),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("family_type", sa.String(50), nullable=False, server_default="candidate"),
        sa.Column("representative_asset_id", uuid_type, sa.ForeignKey("assets.id"), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="candidate"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_creative_families_workspace_id", "creative_families", ["workspace_id"])
    op.create_index(
        "ix_creative_families_workspace_scope", "creative_families", ["workspace_id", "scope"]
    )

    op.create_table(
        "creative_family_members",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column(
            "creative_family_id", uuid_type, sa.ForeignKey("creative_families.id"), nullable=False
        ),
        sa.Column("creative_asset_id", uuid_type, sa.ForeignKey("assets.id"), nullable=False),
        sa.Column("relationship", sa.String(50), nullable=False),
        sa.Column("similarity_score", sa.Float(), nullable=True),
        sa.Column(
            "similarity_evidence", postgresql.JSONB(), nullable=False, server_default=_json_object()
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint(
            "creative_family_id", "creative_asset_id", name="uq_creative_family_members_asset"
        ),
    )
    op.create_index(
        "ix_creative_family_members_creative_family_id",
        "creative_family_members",
        ["creative_family_id"],
    )
    op.create_index(
        "ix_creative_family_members_asset", "creative_family_members", ["creative_asset_id"]
    )

    evidence_columns = [
        sa.Column("source_type", sa.String(50), nullable=True),
        sa.Column("source_provider", sa.String(100), nullable=True),
        sa.Column("source_entity_id", sa.String(255), nullable=True),
        sa.Column("field_path", sa.String(500), nullable=True),
        sa.Column("raw_value_json", postgresql.JSONB(), nullable=True),
        sa.Column("normalized_value_json", postgresql.JSONB(), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=True),
    ]
    for column in evidence_columns:
        op.add_column("evidence_items", column)
    op.create_index(
        "ix_evidence_items_source_provider_entity",
        "evidence_items",
        ["source_provider", "source_entity_id"],
    )

    op.add_column(
        "pattern_kit_versions",
        sa.Column(
            "evidence_state_json", postgresql.JSONB(), nullable=False, server_default=_json_object()
        ),
    )
    op.add_column(
        "adaptation_runs",
        sa.Column(
            "provenance_json", postgresql.JSONB(), nullable=False, server_default=_json_object()
        ),
    )
    op.drop_constraint("ck_product_events_event_type", "product_events", type_="check")
    op.create_check_constraint(
        "ck_product_events_event_type",
        "product_events",
        "event_type IN ("
        "'user_signed_up', 'workspace_created', 'product_created', 'reference_uploaded', "
        "'reference_analyzed', 'creative_dna_viewed', 'creative_dna_corrected', "
        "'pattern_kit_created', 'pattern_kit_version_created', 'pattern_kit_reviewed', "
        "'pattern_kit_validated', 'pattern_kit_corrected', 'viral_kit_created', "
        "'viral_kit_version_created', 'concept_selected', 'concept_rejected', "
        "'campaign_pack_created', 'campaign_pack_exported', 'ugc_uploaded', 'preflight_viewed', "
        "'recommendation_accepted', 'recommendation_rejected', 'recommendation_applied', "
        "'revision_uploaded', 'tiktok_scorer_opened', 'tiktok_score_started', "
        "'tiktok_score_completed', 'tiktok_score_failed', 'tiktok_finding_viewed', "
        "'tiktok_evidence_opened', 'tiktok_fix_accepted', 'tiktok_fix_rejected', "
        "'tiktok_fix_sent_to_creator', 'tiktok_fix_sent_to_editor', 'tiktok_fix_marked_completed', "
        "'tiktok_revision_uploaded', 'tiktok_comparison_viewed', "
        "'tiktok_action_verified_after_revision', 'tiktok_search_executed', "
        "'tiktok_search_result_opened', 'tiktok_ad_saved_reference', 'tiktok_ad_analyze_started', "
        "'tiktok_ad_analyze_completed', 'tiktok_ad_attached_product', "
        "'tiktok_ad_used_for_direction', "
        "'tiktok_commercial_content_opened', 'creative_family_candidate_created', "
        "'creative_family_confirmed', 'market_pattern_created', "
        "'market_pattern_used', 'provider_error'"
        ")",
    )


def downgrade() -> None:
    op.drop_constraint("ck_product_events_event_type", "product_events", type_="check")
    op.create_check_constraint(
        "ck_product_events_event_type",
        "product_events",
        "event_type IN ("
        "'user_signed_up', 'workspace_created', 'product_created', 'reference_uploaded', "
        "'reference_analyzed', 'creative_dna_viewed', 'creative_dna_corrected', "
        "'pattern_kit_created', 'pattern_kit_version_created', 'pattern_kit_reviewed', "
        "'pattern_kit_validated', 'pattern_kit_corrected', 'viral_kit_created', "
        "'viral_kit_version_created', 'concept_selected', 'concept_rejected', "
        "'campaign_pack_created', 'campaign_pack_exported', 'ugc_uploaded', 'preflight_viewed', "
        "'recommendation_accepted', 'recommendation_rejected', 'recommendation_applied', "
        "'revision_uploaded', 'tiktok_scorer_opened', 'tiktok_score_started', "
        "'tiktok_score_completed', 'tiktok_score_failed', 'tiktok_finding_viewed', "
        "'tiktok_evidence_opened', 'tiktok_fix_accepted', 'tiktok_fix_rejected', "
        "'tiktok_fix_sent_to_creator', 'tiktok_fix_sent_to_editor', 'tiktok_fix_marked_completed', "
        "'tiktok_revision_uploaded', 'tiktok_comparison_viewed', "
        "'tiktok_action_verified_after_revision'"
        ")",
    )
    op.drop_column("adaptation_runs", "provenance_json")
    op.drop_column("pattern_kit_versions", "evidence_state_json")
    op.drop_index("ix_evidence_items_source_provider_entity", table_name="evidence_items")
    for name in (
        "source_type",
        "source_provider",
        "source_entity_id",
        "field_path",
        "raw_value_json",
        "normalized_value_json",
        "observed_at",
    ):
        op.drop_column("evidence_items", name)
    op.drop_table("creative_family_members")
    op.drop_table("creative_families")
    op.drop_table("creative_source_links")
    op.drop_table("external_source_records")
