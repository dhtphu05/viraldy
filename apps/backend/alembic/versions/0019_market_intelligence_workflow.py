from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0019_market_intel_workflow"
down_revision: str | None = "0018_tiktok_commercial_content"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _json_object() -> sa.TextClause:
    return sa.text("'{}'::jsonb")


def _json_array() -> sa.TextClause:
    return sa.text("'[]'::jsonb")


_LEGACY_EVENT_TYPES = (
    "'user_signed_up', 'workspace_created', 'product_created', "
    "'reference_uploaded', 'reference_analyzed', 'creative_dna_viewed', "
    "'creative_dna_corrected', 'pattern_kit_created', 'pattern_kit_version_created', "
    "'pattern_kit_reviewed', 'pattern_kit_validated', 'pattern_kit_corrected', "
    "'viral_kit_created', 'viral_kit_version_created', 'concept_selected', "
    "'concept_rejected', 'campaign_pack_created', 'campaign_pack_exported', "
    "'ugc_uploaded', 'preflight_viewed', 'recommendation_accepted', "
    "'recommendation_rejected', 'recommendation_applied', 'revision_uploaded', "
    "'tiktok_scorer_opened', 'tiktok_score_started', 'tiktok_score_completed', "
    "'tiktok_score_failed', 'tiktok_finding_viewed', 'tiktok_evidence_opened', "
    "'tiktok_fix_accepted', 'tiktok_fix_rejected', 'tiktok_fix_sent_to_creator', "
    "'tiktok_fix_sent_to_editor', 'tiktok_fix_marked_completed', "
    "'tiktok_revision_uploaded', 'tiktok_comparison_viewed', "
    "'tiktok_action_verified_after_revision', 'tiktok_search_executed', "
    "'tiktok_search_result_opened', 'tiktok_ad_saved_reference', "
    "'tiktok_ad_analyze_started', 'tiktok_ad_analyze_completed', "
    "'tiktok_ad_attached_product', 'tiktok_ad_used_for_direction', "
    "'tiktok_commercial_content_opened', 'creative_family_candidate_created', "
    "'creative_family_confirmed', 'market_pattern_created', 'market_pattern_used', "
    "'provider_error'"
)

_EVENT_TYPES = (
    _LEGACY_EVENT_TYPES + ", 'acquisition_entry', 'activation_market_search', "
    "'activation_reference_saved', 'creative_direction_created', "
    "'creative_direction_selected', 'batch_review_created', 'batch_review_completed', "
    "'seller_decision_recorded', 'market_snapshot_created', 'market_snapshot_published'"
)


def upgrade() -> None:
    uuid_type = postgresql.UUID(as_uuid=True)

    op.alter_column("assets", "workspace_id", existing_type=uuid_type, nullable=True)
    op.alter_column("assets", "created_by_user_id", existing_type=uuid_type, nullable=True)
    op.add_column(
        "assets",
        sa.Column("library_scope", sa.String(30), nullable=False, server_default="WORKSPACE"),
    )
    op.add_column("assets", sa.Column("source_provider", sa.String(100), nullable=True))
    op.add_column("assets", sa.Column("source_entity_type", sa.String(50), nullable=True))
    op.add_column("assets", sa.Column("source_entity_id", sa.String(255), nullable=True))
    op.add_column("assets", sa.Column("media_type", sa.String(50), nullable=True))
    op.add_column(
        "assets",
        sa.Column(
            "processing_status", sa.String(50), nullable=False, server_default="NOT_ANALYZED"
        ),
    )
    op.create_index(
        "ix_assets_market_source",
        "assets",
        ["source_provider", "source_entity_type", "source_entity_id"],
        unique=True,
    )

    op.add_column(
        "external_source_records",
        sa.Column("provider_updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "external_source_records",
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True
        ),
    )
    op.add_column(
        "external_source_records",
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True
        ),
    )
    op.create_unique_constraint(
        "uq_creative_source_links_provider_identity",
        "creative_source_links",
        ["provider", "provider_entity_type", "provider_entity_id"],
    )
    op.add_column("references", sa.Column("reason_for_saving", sa.Text(), nullable=True))
    op.add_column(
        "evidence_items",
        sa.Column("evidence_scope", sa.String(30), nullable=False, server_default="WORKSPACE"),
    )

    op.create_table(
        "pattern_evidence",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("pattern_kit_id", uuid_type, sa.ForeignKey("pattern_kits.id"), nullable=True),
        sa.Column("scope", sa.String(30), nullable=False),
        sa.Column("workspace_id", uuid_type, sa.ForeignKey("workspaces.id"), nullable=True),
        sa.Column("evidence_level", sa.String(50), nullable=False),
        sa.Column(
            "source_asset_ids", postgresql.JSONB(), nullable=False, server_default=_json_array()
        ),
        sa.Column(
            "source_family_ids", postgresql.JSONB(), nullable=False, server_default=_json_array()
        ),
        sa.Column("market", sa.String(100), nullable=True),
        sa.Column("category", sa.String(160), nullable=True),
        sa.Column("date_min", sa.DateTime(timezone=True), nullable=True),
        sa.Column("date_max", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sample_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("comparable_sample_size", sa.Integer(), nullable=True),
        sa.Column("metric", sa.String(100), nullable=True),
        sa.Column("metric_summary", postgresql.JSONB(), nullable=True),
        sa.Column("confidence", sa.String(50), nullable=False, server_default="low"),
        sa.Column("recency", sa.String(50), nullable=True),
        sa.Column("limitations", postgresql.JSONB(), nullable=False, server_default=_json_array()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_pattern_evidence_scope_market_category",
        "pattern_evidence",
        ["scope", "market", "category"],
    )
    op.create_index("ix_pattern_evidence_pattern_kit", "pattern_evidence", ["pattern_kit_id"])

    op.create_table(
        "creative_directions",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("workspace_id", uuid_type, sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column(
            "adaptation_run_id", uuid_type, sa.ForeignKey("adaptation_runs.id"), nullable=False
        ),
        sa.Column("direction_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("payload_json", postgresql.JSONB(), nullable=False),
        sa.Column(
            "provenance_json", postgresql.JSONB(), nullable=False, server_default=_json_object()
        ),
        sa.Column("status", sa.String(50), nullable=False, server_default="available"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("selected_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_creative_directions_workspace_created",
        "creative_directions",
        ["workspace_id", "created_at"],
    )
    op.create_index(
        "ix_creative_directions_adaptation", "creative_directions", ["adaptation_run_id"]
    )

    op.create_table(
        "batch_reviews",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("workspace_id", uuid_type, sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("product_id", uuid_type, sa.ForeignKey("products.id"), nullable=True),
        sa.Column("objective", sa.String(255), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="queued"),
        sa.Column("created_by_user_id", uuid_type, sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "summary_json", postgresql.JSONB(), nullable=False, server_default=_json_object()
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_batch_reviews_workspace_created", "batch_reviews", ["workspace_id", "created_at"]
    )

    op.create_table(
        "batch_review_items",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("batch_review_id", uuid_type, sa.ForeignKey("batch_reviews.id"), nullable=False),
        sa.Column("creative_asset_id", uuid_type, sa.ForeignKey("assets.id"), nullable=False),
        sa.Column(
            "creative_family_id", uuid_type, sa.ForeignKey("creative_families.id"), nullable=True
        ),
        sa.Column("score_id", uuid_type, sa.ForeignKey("tiktok_score_runs.id"), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="queued"),
        sa.Column("decision", sa.String(50), nullable=True),
        sa.Column("priority", sa.String(20), nullable=True),
        sa.Column("primary_reason", sa.Text(), nullable=True),
        sa.Column("recommended_action", sa.String(100), nullable=True),
        sa.Column(
            "evidence_ids_json", postgresql.JSONB(), nullable=False, server_default=_json_array()
        ),
        sa.UniqueConstraint(
            "batch_review_id", "creative_asset_id", name="uq_batch_review_items_asset"
        ),
    )
    op.create_index(
        "ix_batch_review_items_batch_status", "batch_review_items", ["batch_review_id", "status"]
    )
    op.create_index("ix_batch_review_items_asset", "batch_review_items", ["creative_asset_id"])

    op.create_table(
        "decision_logs",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("workspace_id", uuid_type, sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("entity_type", sa.String(100), nullable=False),
        sa.Column("entity_id", uuid_type, nullable=False),
        sa.Column("recommendation_type", sa.String(100), nullable=False),
        sa.Column("recommended_action", sa.String(100), nullable=False),
        sa.Column("reason_codes", postgresql.JSONB(), nullable=False, server_default=_json_array()),
        sa.Column("evidence_ids", postgresql.JSONB(), nullable=False, server_default=_json_array()),
        sa.Column("model_version", sa.String(100), nullable=True),
        sa.Column("rule_version", sa.String(100), nullable=True),
        sa.Column("seller_response", sa.String(30), nullable=True),
        sa.Column("seller_final_action", sa.String(100), nullable=True),
        sa.Column("seller_feedback", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_decision_logs_workspace_entity",
        "decision_logs",
        ["workspace_id", "entity_type", "entity_id"],
    )

    op.create_table(
        "market_insight_snapshots",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("slug", sa.String(255), nullable=False),
        sa.Column("snapshot_type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("category", sa.String(160), nullable=True),
        sa.Column("market", sa.String(100), nullable=True),
        sa.Column(
            "date_range_json", postgresql.JSONB(), nullable=False, server_default=_json_object()
        ),
        sa.Column("source_scope", sa.String(30), nullable=False, server_default="MARKET"),
        sa.Column("payload_json", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", uuid_type, sa.ForeignKey("users.id"), nullable=True),
        sa.UniqueConstraint("slug", name="uq_market_insight_snapshots_slug"),
    )

    op.create_table(
        "workspace_commercial_profiles",
        sa.Column("workspace_id", uuid_type, sa.ForeignKey("workspaces.id"), primary_key=True),
        sa.Column("account_mode", sa.String(30), nullable=False, server_default="normal"),
        sa.Column(
            "feature_flags_json", postgresql.JSONB(), nullable=False, server_default=_json_object()
        ),
        sa.Column("pilot_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("pilot_cohort", sa.String(100), nullable=True),
        sa.Column("founder_owner", sa.String(255), nullable=True),
    )

    op.create_table(
        "analytics_attributions",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("workspace_id", uuid_type, sa.ForeignKey("workspaces.id"), nullable=True),
        sa.Column("user_id", uuid_type, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("entry_flow", sa.String(50), nullable=False),
        sa.Column("utm_json", postgresql.JSONB(), nullable=False, server_default=_json_object()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_analytics_attributions_workspace_created",
        "analytics_attributions",
        ["workspace_id", "created_at"],
    )

    op.add_column("product_events", sa.Column("entry_flow", sa.String(50), nullable=True))
    op.add_column(
        "product_events",
        sa.Column(
            "attribution_id", uuid_type, sa.ForeignKey("analytics_attributions.id"), nullable=True
        ),
    )
    op.add_column(
        "product_events",
        sa.Column("utm_json", postgresql.JSONB(), nullable=False, server_default=_json_object()),
    )
    op.create_index("ix_product_events_attribution", "product_events", ["attribution_id"])
    op.drop_constraint("ck_product_events_event_type", "product_events", type_="check")
    op.create_check_constraint(
        "ck_product_events_event_type",
        "product_events",
        f"event_type IN ({_EVENT_TYPES})",
    )


def downgrade() -> None:
    op.drop_constraint("ck_product_events_event_type", "product_events", type_="check")
    op.create_check_constraint(
        "ck_product_events_event_type",
        "product_events",
        f"event_type IN ({_LEGACY_EVENT_TYPES})",
    )
    op.drop_index("ix_product_events_attribution", table_name="product_events")
    op.drop_column("product_events", "utm_json")
    op.drop_column("product_events", "attribution_id")
    op.drop_column("product_events", "entry_flow")
    op.drop_index(
        "ix_analytics_attributions_workspace_created", table_name="analytics_attributions"
    )
    op.drop_table("analytics_attributions")
    op.drop_table("workspace_commercial_profiles")
    op.drop_table("market_insight_snapshots")
    op.drop_index("ix_decision_logs_workspace_entity", table_name="decision_logs")
    op.drop_table("decision_logs")
    op.drop_index("ix_batch_review_items_asset", table_name="batch_review_items")
    op.drop_index("ix_batch_review_items_batch_status", table_name="batch_review_items")
    op.drop_table("batch_review_items")
    op.drop_index("ix_batch_reviews_workspace_created", table_name="batch_reviews")
    op.drop_table("batch_reviews")
    op.drop_index("ix_creative_directions_adaptation", table_name="creative_directions")
    op.drop_index("ix_creative_directions_workspace_created", table_name="creative_directions")
    op.drop_table("creative_directions")
    op.drop_index("ix_pattern_evidence_pattern_kit", table_name="pattern_evidence")
    op.drop_index("ix_pattern_evidence_scope_market_category", table_name="pattern_evidence")
    op.drop_table("pattern_evidence")
    op.drop_column("evidence_items", "evidence_scope")
    op.drop_column("references", "reason_for_saving")
    op.drop_constraint(
        "uq_creative_source_links_provider_identity", "creative_source_links", type_="unique"
    )
    op.drop_column("external_source_records", "updated_at")
    op.drop_column("external_source_records", "created_at")
    op.drop_column("external_source_records", "provider_updated_at")
    op.drop_index("ix_assets_market_source", table_name="assets")
    op.drop_column("assets", "processing_status")
    op.drop_column("assets", "media_type")
    op.drop_column("assets", "source_entity_id")
    op.drop_column("assets", "source_entity_type")
    op.drop_column("assets", "source_provider")
    op.drop_column("assets", "library_scope")
    op.alter_column(
        "assets", "created_by_user_id", existing_type=postgresql.UUID(as_uuid=True), nullable=False
    )
    op.alter_column(
        "assets", "workspace_id", existing_type=postgresql.UUID(as_uuid=True), nullable=False
    )
