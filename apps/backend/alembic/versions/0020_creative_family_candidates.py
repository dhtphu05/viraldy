from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0020_creative_family_candidates"
down_revision: str | None = "0019_market_intel_workflow"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_EVENT_TYPES = (
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
    "'tiktok_fix_sent_to_editor', 'tiktok_fix_marked_completed', 'tiktok_revision_uploaded', "
    "'tiktok_comparison_viewed', 'tiktok_action_verified_after_revision', "
    "'tiktok_search_executed', 'tiktok_search_result_opened', 'tiktok_ad_saved_reference', "
    "'tiktok_ad_analyze_started', 'tiktok_ad_analyze_completed', "
    "'tiktok_ad_attached_product', 'tiktok_ad_used_for_direction', "
    "'tiktok_commercial_content_opened', 'creative_family_candidate_created', "
    "'creative_family_confirmed', 'market_pattern_created', 'market_pattern_used', "
    "'provider_error', 'acquisition_entry', 'activation_market_search', "
    "'activation_reference_saved', 'creative_direction_created', 'creative_direction_selected', "
    "'batch_review_created', 'batch_review_completed', 'seller_decision_recorded', "
    "'market_snapshot_created', 'market_snapshot_published', 'creative_explorer_opened', "
    "'market_search_started', 'market_search_completed', 'market_result_opened', "
    "'market_snapshot_opened', 'market_creative_analyze_started', "
    "'market_creative_analyze_completed', 'market_reference_saved', "
    "'adapt_to_product_clicked', 'product_selected_for_adaptation', "
    "'creative_directions_generated', 'score_started', 'score_completed', 'fix_viewed', "
    "'fix_copied', 'batch_review_started', 'batch_decision_viewed', "
    "'batch_recommendation_accepted', 'batch_recommendation_rejected', "
    "'share_snapshot_created', 'share_snapshot_opened', 'upgrade_prompt_viewed', "
    "'upgrade_started', 'upgrade_completed', 'creative_revision_uploaded', "
    "'creative_family_reused'"
)

_PREVIOUS_EVENT_TYPES = (
    "'user_signed_up', 'workspace_created', 'product_created', 'reference_uploaded', "
    "'reference_analyzed', 'creative_dna_viewed', 'creative_dna_corrected', "
    "'pattern_kit_created', 'pattern_kit_version_created', 'pattern_kit_reviewed', "
    "'pattern_kit_validated', 'pattern_kit_corrected', 'viral_kit_created', "
    "'viral_kit_version_created', 'concept_selected', 'concept_rejected', "
    "'campaign_pack_created', 'campaign_pack_exported', 'ugc_uploaded', "
    "'preflight_viewed', 'recommendation_accepted', 'recommendation_rejected', "
    "'recommendation_applied', 'revision_uploaded', 'tiktok_scorer_opened', "
    "'tiktok_score_started', 'tiktok_score_completed', 'tiktok_score_failed', "
    "'tiktok_finding_viewed', 'tiktok_evidence_opened', 'tiktok_fix_accepted', "
    "'tiktok_fix_rejected', 'tiktok_fix_sent_to_creator', 'tiktok_fix_sent_to_editor', "
    "'tiktok_fix_marked_completed', 'tiktok_revision_uploaded', 'tiktok_comparison_viewed', "
    "'tiktok_action_verified_after_revision', 'tiktok_search_executed', "
    "'tiktok_search_result_opened', 'tiktok_ad_saved_reference', "
    "'tiktok_ad_analyze_started', 'tiktok_ad_analyze_completed', "
    "'tiktok_ad_attached_product', 'tiktok_ad_used_for_direction', "
    "'tiktok_commercial_content_opened', 'creative_family_candidate_created', "
    "'creative_family_confirmed', 'market_pattern_created', 'market_pattern_used', "
    "'provider_error', 'acquisition_entry', 'activation_market_search', "
    "'activation_reference_saved', 'creative_direction_created', "
    "'creative_direction_selected', 'batch_review_created', 'batch_review_completed', "
    "'seller_decision_recorded', 'market_snapshot_created', 'market_snapshot_published'"
)


def upgrade() -> None:
    uuid_type = postgresql.UUID(as_uuid=True)
    op.drop_constraint("ck_product_events_event_type", "product_events", type_="check")
    op.create_check_constraint(
        "ck_product_events_event_type", "product_events", f"event_type IN ({_EVENT_TYPES})"
    )
    op.create_table(
        "creative_family_candidates",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("scope", sa.String(30), nullable=False),
        sa.Column("workspace_id", uuid_type, sa.ForeignKey("workspaces.id"), nullable=True),
        sa.Column("asset_a_id", uuid_type, sa.ForeignKey("assets.id"), nullable=False),
        sa.Column("asset_b_id", uuid_type, sa.ForeignKey("assets.id"), nullable=False),
        sa.Column("relationship", sa.String(50), nullable=False),
        sa.Column("candidate_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("confidence", sa.String(30), nullable=False, server_default="low"),
        sa.Column(
            "signals_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(30), nullable=False, server_default="reviewable"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint(
            "scope",
            "workspace_id",
            "asset_a_id",
            "asset_b_id",
            name="uq_creative_family_candidates_pair",
        ),
    )
    op.create_index(
        "ix_creative_family_candidates_scope_status",
        "creative_family_candidates",
        ["scope", "status"],
    )
    op.create_index(
        "ix_creative_family_candidates_asset_a", "creative_family_candidates", ["asset_a_id"]
    )
    op.create_index(
        "ix_creative_family_candidates_asset_b", "creative_family_candidates", ["asset_b_id"]
    )


def downgrade() -> None:
    op.drop_constraint("ck_product_events_event_type", "product_events", type_="check")
    op.create_check_constraint(
        "ck_product_events_event_type",
        "product_events",
        f"event_type IN ({_PREVIOUS_EVENT_TYPES})",
    )
    op.drop_index("ix_creative_family_candidates_asset_b", table_name="creative_family_candidates")
    op.drop_index("ix_creative_family_candidates_asset_a", table_name="creative_family_candidates")
    op.drop_index(
        "ix_creative_family_candidates_scope_status", table_name="creative_family_candidates"
    )
    op.drop_table("creative_family_candidates")
