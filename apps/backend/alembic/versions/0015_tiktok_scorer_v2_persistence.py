from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0015_tiktok_scorer_v2"
down_revision: str | None = "0014_user_phone_number"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _json_object() -> sa.TextClause:
    return sa.text("'{}'::jsonb")


def _json_array() -> sa.TextClause:
    return sa.text("'[]'::jsonb")


def _workspace_column(nullable: bool = False) -> sa.Column:
    return sa.Column(
        "workspace_id",
        postgresql.UUID(as_uuid=True),
        sa.ForeignKey("workspaces.id"),
        nullable=nullable,
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
    _create_profiles()
    _expand_score_runs()
    _create_dimensions()
    _create_findings()
    _create_fix_actions()
    _create_fix_action_events()
    _create_comparisons()
    _extend_product_event_types()


def _create_profiles() -> None:
    op.create_table(
        "tiktok_score_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("label", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("profile_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "weights_json", postgresql.JSONB(), nullable=False, server_default=_json_object()
        ),
        sa.Column(
            "thresholds_json", postgresql.JSONB(), nullable=False, server_default=_json_object()
        ),
        sa.Column(
            "configuration_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=_json_object(),
        ),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        _created_at(),
        _updated_at(),
        sa.UniqueConstraint(
            "workspace_id",
            "code",
            "profile_version",
            name="uq_tiktok_score_profiles_workspace_code_version",
        ),
    )
    op.create_index(
        "ix_tiktok_score_profiles_workspace_id", "tiktok_score_profiles", ["workspace_id"]
    )
    op.create_index(
        "ix_tiktok_score_profiles_code_active", "tiktok_score_profiles", ["code", "is_active"]
    )
    op.create_index(
        "uq_tiktok_score_profiles_system_code_version",
        "tiktok_score_profiles",
        ["code", "profile_version"],
        unique=True,
        postgresql_where=sa.text("workspace_id IS NULL"),
    )


def _expand_score_runs() -> None:
    op.drop_constraint("ck_tiktok_score_runs_status", "tiktok_score_runs", type_="check")
    columns = (
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("parent_score_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("current_stage", sa.String(length=100), nullable=False, server_default="queued"),
        sa.Column("idempotency_key", sa.String(length=255), nullable=True),
        sa.Column("score_mode", sa.String(length=50), nullable=False, server_default="quick"),
        sa.Column(
            "intended_use", sa.String(length=50), nullable=False, server_default="tiktok_organic"
        ),
        sa.Column(
            "score_profile",
            sa.String(length=100),
            nullable=False,
            server_default="general_tiktok_v1",
        ),
        sa.Column("score_profile_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("score_profile_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "profile_selection_mode",
            sa.String(length=100),
            nullable=False,
            server_default="user_selected",
        ),
        sa.Column("profile_selection_confidence", sa.Numeric(5, 4), nullable=True),
        sa.Column(
            "alternative_profiles_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=_json_array(),
        ),
        sa.Column(
            "profile_evidence_ids_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=_json_array(),
        ),
        sa.Column("profile_override_reason", sa.Text(), nullable=True),
        sa.Column("product_context_snapshot_json", postgresql.JSONB(), nullable=True),
        sa.Column("product_context_snapshot_hash", sa.String(length=64), nullable=True),
        sa.Column("product_context_schema_version", sa.String(length=100), nullable=True),
        sa.Column("product_context_version", sa.Integer(), nullable=True),
        sa.Column(
            "policy_pack_versions_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=_json_object(),
        ),
        sa.Column(
            "rule_versions_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=_json_object(),
        ),
        sa.Column(
            "prompt_versions_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=_json_object(),
        ),
        sa.Column(
            "model_provider_versions_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=_json_object(),
        ),
        sa.Column("media_checksum_sha256", sa.String(length=64), nullable=True),
        sa.Column("creative_direction_context_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("creative_direction_context_snapshot_json", postgresql.JSONB(), nullable=True),
        sa.Column("creative_direction_context_version", sa.Integer(), nullable=True),
        sa.Column("creative_direction_lookup_error", sa.String(length=100), nullable=True),
        sa.Column(
            "confidence_json", postgresql.JSONB(), nullable=False, server_default=_json_object()
        ),
        sa.Column(
            "creative_structure_decision",
            sa.String(length=100),
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "paid_use_rights_status",
            sa.String(length=100),
            nullable=False,
            server_default="not_evaluated",
        ),
        sa.Column(
            "final_paid_readiness",
            sa.String(length=100),
            nullable=False,
            server_default="not_evaluated",
        ),
        sa.Column("scene_inventory_json", postgresql.JSONB(), nullable=True),
        sa.Column("auxiliary_signals_json", postgresql.JSONB(), nullable=True),
        sa.Column(
            "creative_upgrades_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=_json_array(),
        ),
        sa.Column("result_json", postgresql.JSONB(), nullable=True),
        sa.Column("latency_ms", sa.BigInteger(), nullable=True),
        sa.Column(
            "token_usage_json", postgresql.JSONB(), nullable=False, server_default=_json_object()
        ),
        sa.Column("cost_estimate", sa.Numeric(18, 8), nullable=True),
        sa.Column("failure_code", sa.String(length=100), nullable=True),
        _updated_at(),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    for column in columns:
        op.add_column("tiktok_score_runs", column)

    op.execute(
        sa.text(
            "UPDATE tiktok_score_runs AS score "
            "SET asset_id = version.asset_id "
            "FROM asset_versions AS version "
            "WHERE score.asset_version_id = version.id AND score.asset_id IS NULL"
        )
    )
    op.alter_column(
        "tiktok_score_runs",
        "structural_score",
        existing_type=sa.Numeric(),
        nullable=True,
        server_default=None,
    )
    op.create_foreign_key(
        "fk_tiktok_score_runs_asset_id", "tiktok_score_runs", "assets", ["asset_id"], ["id"]
    )
    op.create_foreign_key(
        "fk_tiktok_score_runs_product_id",
        "tiktok_score_runs",
        "products",
        ["product_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_tiktok_score_runs_parent_score_run_id",
        "tiktok_score_runs",
        "tiktok_score_runs",
        ["parent_score_run_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_tiktok_score_runs_score_profile_id",
        "tiktok_score_runs",
        "tiktok_score_profiles",
        ["score_profile_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_unique_constraint(
        "uq_tiktok_score_runs_workspace_idempotency",
        "tiktok_score_runs",
        ["workspace_id", "idempotency_key"],
    )
    op.create_check_constraint(
        "ck_tiktok_score_runs_status",
        "tiktok_score_runs",
        "status IN ('pending', 'queued', 'processing', 'partial_evidence', "
        "'completed', 'failed', 'cancelled')",
    )
    op.create_check_constraint(
        "ck_tiktok_score_runs_score_mode",
        "tiktok_score_runs",
        "score_mode IN ('quick', 'product_aware', 'usage_aware')",
    )
    op.create_check_constraint(
        "ck_tiktok_score_runs_intended_use",
        "tiktok_score_runs",
        "intended_use IN ('tiktok_organic', 'tiktok_shop_affiliate', "
        "'ugc_paid_candidate', 'spark_candidate')",
    )
    op.create_check_constraint(
        "ck_tiktok_score_runs_profile_confidence",
        "tiktok_score_runs",
        "profile_selection_confidence IS NULL OR "
        "(profile_selection_confidence >= 0 AND profile_selection_confidence <= 1)",
    )
    op.create_index("ix_tiktok_score_runs_asset_id", "tiktok_score_runs", ["asset_id"])
    op.create_index(
        "ix_tiktok_score_runs_parent_score_run_id", "tiktok_score_runs", ["parent_score_run_id"]
    )
    op.create_index(
        "ix_tiktok_score_runs_workspace_status_created",
        "tiktok_score_runs",
        ["workspace_id", "status", "created_at"],
    )
    op.create_index(
        "ix_tiktok_score_runs_workspace_asset_created",
        "tiktok_score_runs",
        ["workspace_id", "asset_id", "created_at"],
    )


def _create_dimensions() -> None:
    op.create_table(
        "tiktok_score_dimensions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        _workspace_column(),
        sa.Column(
            "score_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tiktok_score_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("label", sa.String(length=160), nullable=False),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("applicability", sa.String(length=50), nullable=False),
        sa.Column("evidence_status", sa.String(length=50), nullable=False),
        sa.Column("confidence", sa.String(length=50), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "positive_signals_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=_json_array(),
        ),
        sa.Column(
            "missing_signals_json", postgresql.JSONB(), nullable=False, server_default=_json_array()
        ),
        sa.Column(
            "uncertainty_json", postgresql.JSONB(), nullable=False, server_default=_json_array()
        ),
        sa.Column(
            "evidence_ids_json", postgresql.JSONB(), nullable=False, server_default=_json_array()
        ),
        sa.Column(
            "contributing_rule_codes_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=_json_array(),
        ),
        sa.Column("result_json", postgresql.JSONB(), nullable=False, server_default=_json_object()),
        _created_at(),
        sa.UniqueConstraint("score_run_id", "code", name="uq_tiktok_score_dimensions_run_code"),
        sa.CheckConstraint(
            "score IS NULL OR (score >= 0 AND score <= 100)",
            name="ck_tiktok_score_dimensions_score",
        ),
    )
    op.create_index(
        "ix_tiktok_score_dimensions_workspace_id", "tiktok_score_dimensions", ["workspace_id"]
    )
    op.create_index(
        "ix_tiktok_score_dimensions_score_run_id", "tiktok_score_dimensions", ["score_run_id"]
    )
    op.create_index(
        "ix_tiktok_score_dimensions_workspace_run",
        "tiktok_score_dimensions",
        ["workspace_id", "score_run_id"],
    )


def _create_findings() -> None:
    op.create_table(
        "tiktok_score_findings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        _workspace_column(),
        sa.Column(
            "score_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tiktok_score_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("code", sa.String(length=120), nullable=False),
        sa.Column("rule_code", sa.String(length=160), nullable=False),
        sa.Column("rule_class", sa.String(length=100), nullable=False),
        sa.Column("source_dimension", sa.String(length=100), nullable=False),
        sa.Column("severity", sa.String(length=50), nullable=False),
        sa.Column("priority", sa.String(length=10), nullable=False),
        sa.Column("applicability", sa.String(length=50), nullable=False),
        sa.Column("evidence_status", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "expected_json", postgresql.JSONB(), nullable=False, server_default=_json_object()
        ),
        sa.Column(
            "observed_json", postgresql.JSONB(), nullable=False, server_default=_json_object()
        ),
        sa.Column("target_time_range_ms_json", postgresql.JSONB(), nullable=True),
        sa.Column(
            "evidence_ids_json", postgresql.JSONB(), nullable=False, server_default=_json_array()
        ),
        sa.Column(
            "uncertainty_json", postgresql.JSONB(), nullable=False, server_default=_json_array()
        ),
        sa.Column("requires_seller_truth", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("can_be_resolved_by_edit", sa.Boolean(), nullable=True),
        sa.Column("requires_physical_reshoot", sa.Boolean(), nullable=True),
        sa.Column(
            "finding_json", postgresql.JSONB(), nullable=False, server_default=_json_object()
        ),
        _created_at(),
    )
    op.create_index(
        "ix_tiktok_score_findings_workspace_id", "tiktok_score_findings", ["workspace_id"]
    )
    op.create_index(
        "ix_tiktok_score_findings_score_run_id", "tiktok_score_findings", ["score_run_id"]
    )
    op.create_index(
        "ix_tiktok_score_findings_workspace_run",
        "tiktok_score_findings",
        ["workspace_id", "score_run_id"],
    )


def _create_fix_actions() -> None:
    op.create_table(
        "tiktok_fix_actions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        _workspace_column(),
        sa.Column(
            "score_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tiktok_score_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "finding_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tiktok_score_findings.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("code", sa.String(length=120), nullable=False),
        sa.Column("recommendation_class", sa.String(length=100), nullable=False),
        sa.Column("basis", sa.String(length=100), nullable=False),
        sa.Column("priority", sa.String(length=10), nullable=False),
        sa.Column("severity", sa.String(length=50), nullable=False),
        sa.Column("source_dimension", sa.String(length=100), nullable=False),
        sa.Column("owner_role", sa.String(length=50), nullable=False),
        sa.Column("fix_type", sa.String(length=100), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("why_it_matters", sa.Text(), nullable=False),
        sa.Column(
            "expected_json", postgresql.JSONB(), nullable=False, server_default=_json_object()
        ),
        sa.Column(
            "observed_json", postgresql.JSONB(), nullable=False, server_default=_json_object()
        ),
        sa.Column(
            "evidence_ids_json", postgresql.JSONB(), nullable=False, server_default=_json_array()
        ),
        sa.Column("target_time_range_ms_json", postgresql.JSONB(), nullable=True),
        sa.Column(
            "video_operations_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=_json_array(),
        ),
        sa.Column(
            "instructions_json", postgresql.JSONB(), nullable=False, server_default=_json_array()
        ),
        sa.Column(
            "strengths_to_preserve_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=_json_array(),
        ),
        sa.Column(
            "required_inputs_json", postgresql.JSONB(), nullable=False, server_default=_json_array()
        ),
        sa.Column("estimated_effort", sa.String(length=50), nullable=False),
        sa.Column("reshoot_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "completion_criteria_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=_json_array(),
        ),
        sa.Column("verification_method", sa.Text(), nullable=False),
        sa.Column(
            "current_action_state", sa.String(length=50), nullable=False, server_default="pending"
        ),
        sa.Column("action_json", postgresql.JSONB(), nullable=False, server_default=_json_object()),
        _created_at(),
        _updated_at(),
    )
    op.create_index("ix_tiktok_fix_actions_workspace_id", "tiktok_fix_actions", ["workspace_id"])
    op.create_index("ix_tiktok_fix_actions_score_run_id", "tiktok_fix_actions", ["score_run_id"])
    op.create_index(
        "ix_tiktok_fix_actions_workspace_run",
        "tiktok_fix_actions",
        ["workspace_id", "score_run_id"],
    )


def _create_fix_action_events() -> None:
    op.create_table(
        "tiktok_fix_action_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        _workspace_column(),
        sa.Column(
            "score_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tiktok_score_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "fix_action_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tiktok_fix_actions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "actor_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=True),
        sa.Column(
            "details_json", postgresql.JSONB(), nullable=False, server_default=_json_object()
        ),
        _created_at(),
        sa.UniqueConstraint(
            "workspace_id",
            "fix_action_id",
            "idempotency_key",
            name="uq_tiktok_fix_action_events_action_idempotency",
        ),
        sa.CheckConstraint(
            "event_type IN ('viewed', 'accepted', 'rejected', 'sent_to_creator', "
            "'sent_to_editor', 'marked_completed', 'verified_after_revision')",
            name="ck_tiktok_fix_action_events_event_type",
        ),
    )
    op.create_index(
        "ix_tiktok_fix_action_events_workspace_id", "tiktok_fix_action_events", ["workspace_id"]
    )
    op.create_index(
        "ix_tiktok_fix_action_events_score_run_id", "tiktok_fix_action_events", ["score_run_id"]
    )
    op.create_index(
        "ix_tiktok_fix_action_events_fix_action_id", "tiktok_fix_action_events", ["fix_action_id"]
    )
    op.create_index(
        "ix_tiktok_fix_action_events_workspace_action",
        "tiktok_fix_action_events",
        ["workspace_id", "fix_action_id"],
    )


def _create_comparisons() -> None:
    op.create_table(
        "tiktok_score_comparisons",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        _workspace_column(),
        sa.Column(
            "before_score_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tiktok_score_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "after_score_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tiktok_score_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="pending"),
        sa.Column(
            "accepted_fix_action_ids_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=_json_array(),
        ),
        sa.Column(
            "resolved_blockers_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=_json_array(),
        ),
        sa.Column(
            "unresolved_blockers_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=_json_array(),
        ),
        sa.Column(
            "new_regressions_json", postgresql.JSONB(), nullable=False, server_default=_json_array()
        ),
        sa.Column(
            "dimension_changes_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=_json_array(),
        ),
        sa.Column(
            "evidence_before_after_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=_json_array(),
        ),
        sa.Column(
            "strengths_preserved_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=_json_array(),
        ),
        sa.Column(
            "actions_verified_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=_json_array(),
        ),
        sa.Column("final_next_action", sa.Text(), nullable=True),
        sa.Column(
            "comparison_json", postgresql.JSONB(), nullable=False, server_default=_json_object()
        ),
        sa.Column("failure_code", sa.String(length=100), nullable=True),
        _created_at(),
        _updated_at(),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint(
            "workspace_id",
            "before_score_run_id",
            "after_score_run_id",
            name="uq_tiktok_score_comparisons_run_pair",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'processing', 'completed', 'failed')",
            name="ck_tiktok_score_comparisons_status",
        ),
    )
    op.create_index(
        "ix_tiktok_score_comparisons_workspace_id", "tiktok_score_comparisons", ["workspace_id"]
    )
    op.create_index(
        "ix_tiktok_score_comparisons_before_score_run_id",
        "tiktok_score_comparisons",
        ["before_score_run_id"],
    )
    op.create_index(
        "ix_tiktok_score_comparisons_after_score_run_id",
        "tiktok_score_comparisons",
        ["after_score_run_id"],
    )
    op.create_index(
        "ix_tiktok_score_comparisons_workspace_before",
        "tiktok_score_comparisons",
        ["workspace_id", "before_score_run_id"],
    )


def _extend_product_event_types() -> None:
    op.drop_constraint("ck_product_events_event_type", "product_events", type_="check")
    op.create_check_constraint(
        "ck_product_events_event_type",
        "product_events",
        "event_type IN ("
        "'user_signed_up', 'workspace_created', 'product_created', "
        "'reference_uploaded', 'reference_analyzed', 'creative_dna_viewed', "
        "'creative_dna_corrected', 'pattern_kit_created', "
        "'pattern_kit_version_created', 'pattern_kit_reviewed', "
        "'pattern_kit_validated', 'pattern_kit_corrected', 'viral_kit_created', "
        "'viral_kit_version_created', 'concept_selected', 'concept_rejected', "
        "'campaign_pack_created', 'campaign_pack_exported', 'ugc_uploaded', "
        "'preflight_viewed', 'recommendation_accepted', 'recommendation_rejected', "
        "'recommendation_applied', 'revision_uploaded', 'tiktok_scorer_opened', "
        "'tiktok_score_started', 'tiktok_score_completed', 'tiktok_score_failed', "
        "'tiktok_finding_viewed', 'tiktok_evidence_opened', 'tiktok_fix_accepted', "
        "'tiktok_fix_rejected', 'tiktok_fix_sent_to_creator', "
        "'tiktok_fix_sent_to_editor', 'tiktok_fix_marked_completed', "
        "'tiktok_revision_uploaded', 'tiktok_comparison_viewed', "
        "'tiktok_action_verified_after_revision')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_product_events_event_type", "product_events", type_="check")
    op.create_check_constraint(
        "ck_product_events_event_type",
        "product_events",
        "event_type IN ("
        "'user_signed_up', 'workspace_created', 'product_created', "
        "'reference_uploaded', 'reference_analyzed', 'creative_dna_viewed', "
        "'creative_dna_corrected', 'pattern_kit_created', "
        "'pattern_kit_version_created', 'pattern_kit_reviewed', "
        "'pattern_kit_validated', 'pattern_kit_corrected', 'viral_kit_created', "
        "'viral_kit_version_created', 'concept_selected', 'concept_rejected', "
        "'campaign_pack_created', 'campaign_pack_exported', 'ugc_uploaded', "
        "'preflight_viewed', 'recommendation_accepted', "
        "'recommendation_rejected', 'recommendation_applied', 'revision_uploaded')",
    )
    op.drop_table("tiktok_score_comparisons")
    op.drop_table("tiktok_fix_action_events")
    op.drop_table("tiktok_fix_actions")
    op.drop_table("tiktok_score_findings")
    op.drop_table("tiktok_score_dimensions")
    for index_name in (
        "ix_tiktok_score_runs_workspace_asset_created",
        "ix_tiktok_score_runs_workspace_status_created",
        "ix_tiktok_score_runs_parent_score_run_id",
        "ix_tiktok_score_runs_asset_id",
    ):
        op.drop_index(index_name, table_name="tiktok_score_runs")
    for constraint_name, constraint_type in (
        ("ck_tiktok_score_runs_status", "check"),
        ("ck_tiktok_score_runs_profile_confidence", "check"),
        ("ck_tiktok_score_runs_intended_use", "check"),
        ("ck_tiktok_score_runs_score_mode", "check"),
        ("uq_tiktok_score_runs_workspace_idempotency", "unique"),
        ("fk_tiktok_score_runs_score_profile_id", "foreignkey"),
        ("fk_tiktok_score_runs_parent_score_run_id", "foreignkey"),
        ("fk_tiktok_score_runs_product_id", "foreignkey"),
        ("fk_tiktok_score_runs_asset_id", "foreignkey"),
    ):
        op.drop_constraint(constraint_name, "tiktok_score_runs", type_=constraint_type)
    op.create_check_constraint(
        "ck_tiktok_score_runs_status",
        "tiktok_score_runs",
        "status IN ('pending', 'queued', 'processing', 'completed', 'failed', 'cancelled')",
    )
    op.alter_column(
        "tiktok_score_runs",
        "structural_score",
        existing_type=sa.Numeric(),
        nullable=False,
        server_default="0",
    )
    for column_name in reversed(
        (
            "asset_id",
            "product_id",
            "parent_score_run_id",
            "current_stage",
            "idempotency_key",
            "score_mode",
            "intended_use",
            "score_profile",
            "score_profile_version",
            "score_profile_id",
            "profile_selection_mode",
            "profile_selection_confidence",
            "alternative_profiles_json",
            "profile_evidence_ids_json",
            "profile_override_reason",
            "product_context_snapshot_json",
            "product_context_snapshot_hash",
            "product_context_schema_version",
            "product_context_version",
            "policy_pack_versions_json",
            "rule_versions_json",
            "prompt_versions_json",
            "model_provider_versions_json",
            "media_checksum_sha256",
            "creative_direction_context_id",
            "creative_direction_context_snapshot_json",
            "creative_direction_context_version",
            "creative_direction_lookup_error",
            "confidence_json",
            "creative_structure_decision",
            "paid_use_rights_status",
            "final_paid_readiness",
            "scene_inventory_json",
            "auxiliary_signals_json",
            "creative_upgrades_json",
            "result_json",
            "latency_ms",
            "token_usage_json",
            "cost_estimate",
            "failure_code",
            "updated_at",
            "completed_at",
        )
    ):
        op.drop_column("tiktok_score_runs", column_name)
    op.drop_table("tiktok_score_profiles")
