from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0006_feedback_events_model_runs"
down_revision: str | None = "0005_auth_workspace_rbac"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _jsonb_default_object() -> sa.TextClause:
    return sa.text("'{}'::jsonb")


def upgrade() -> None:
    _upgrade_ai_model_runs()
    _upgrade_recommendation_actions()
    _create_product_events()
    _create_feedback_items()


def _upgrade_ai_model_runs() -> None:
    op.add_column("ai_model_runs", sa.Column("operation", sa.String(length=100), nullable=True))
    op.add_column(
        "ai_model_runs", sa.Column("schema_version", sa.String(length=100), nullable=True)
    )
    op.add_column("ai_model_runs", sa.Column("input_hash", sa.String(length=64), nullable=True))
    op.add_column(
        "ai_model_runs",
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "ai_model_runs",
        sa.Column(
            "usage_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=_jsonb_default_object(),
        ),
    )
    op.add_column("ai_model_runs", sa.Column("estimated_cost", sa.Numeric(12, 6), nullable=True))
    op.add_column("ai_model_runs", sa.Column("safe_error_message", sa.Text(), nullable=True))
    op.execute(
        sa.text(
            """
            UPDATE ai_model_runs
            SET
                operation = COALESCE(operation, capability),
                schema_version = COALESCE(schema_version, response_schema_version),
                input_hash = COALESCE(input_hash, request_hash),
                attempt_count = GREATEST(attempt_count, attempt)
            """
        )
    )
    op.alter_column(
        "ai_model_runs",
        "operation",
        existing_type=sa.String(length=100),
        nullable=False,
    )
    op.alter_column(
        "ai_model_runs",
        "schema_version",
        existing_type=sa.String(length=100),
        nullable=False,
    )
    op.alter_column(
        "ai_model_runs",
        "input_hash",
        existing_type=sa.String(length=64),
        nullable=False,
    )
    op.create_check_constraint(
        "ck_ai_model_runs_attempt_count",
        "ai_model_runs",
        "attempt_count >= 1",
    )
    op.create_index(
        "ix_ai_model_runs_job_operation",
        "ai_model_runs",
        ["processing_job_id", "operation"],
    )
    op.create_index(
        "ix_ai_model_runs_operation_created",
        "ai_model_runs",
        ["workspace_id", "operation", "created_at"],
    )


def _upgrade_recommendation_actions() -> None:
    op.execute(
        sa.text(
            """
            UPDATE recommendation_actions
            SET
                metadata_json = metadata_json || jsonb_build_object(
                    'legacy_action_type', action_type
                ),
                action_type = 'ignored'
            WHERE action_type = 'dismissed'
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE recommendation_actions
            SET
                metadata_json = metadata_json || jsonb_build_object(
                    'legacy_action_type', action_type
                ),
                action_type = 'applied'
            WHERE action_type = 'exported'
            """
        )
    )
    op.create_check_constraint(
        "ck_recommendation_actions_action_type",
        "recommendation_actions",
        "action_type IN ('viewed', 'accepted', 'rejected', 'applied', 'ignored')",
    )


def _create_product_events() -> None:
    op.create_table(
        "product_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id"),
            nullable=True,
        ),
        sa.Column(
            "actor_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("subject_type", sa.String(length=100), nullable=True),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "payload_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=_jsonb_default_object(),
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "event_type IN ("
            "'user_signed_up', 'workspace_created', 'product_created', "
            "'reference_uploaded', 'reference_analyzed', 'creative_dna_viewed', "
            "'creative_dna_corrected', 'pattern_kit_created', "
            "'pattern_kit_version_created', 'pattern_kit_reviewed', "
            "'pattern_kit_validated', 'pattern_kit_corrected', 'viral_kit_created', "
            "'viral_kit_version_created', 'concept_selected', 'concept_rejected', "
            "'campaign_pack_created', 'campaign_pack_exported', 'ugc_uploaded', "
            "'preflight_viewed', 'recommendation_accepted', "
            "'recommendation_rejected', 'recommendation_applied', 'revision_uploaded'"
            ")",
            name="ck_product_events_event_type",
        ),
    )
    op.create_index("ix_product_events_workspace_id", "product_events", ["workspace_id"])
    op.create_index("ix_product_events_actor_user_id", "product_events", ["actor_user_id"])
    op.create_index(
        "ix_product_events_workspace_created",
        "product_events",
        ["workspace_id", "created_at"],
    )
    op.create_index(
        "ix_product_events_workspace_event_created",
        "product_events",
        ["workspace_id", "event_type", "created_at"],
    )
    op.create_index(
        "ix_product_events_actor_created",
        "product_events",
        ["actor_user_id", "created_at"],
    )


def _create_feedback_items() -> None:
    op.create_table(
        "feedback_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id"),
            nullable=False,
        ),
        sa.Column("subject_type", sa.String(length=100), nullable=False),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("subject_version", sa.Integer(), nullable=True),
        sa.Column("field_path", sa.String(length=500), nullable=False),
        sa.Column("feedback_type", sa.String(length=50), nullable=False),
        sa.Column("ai_value_json", postgresql.JSONB(), nullable=True),
        sa.Column("user_value_json", postgresql.JSONB(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
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
        sa.CheckConstraint(
            "subject_type IN ("
            "'creative_dna', 'pattern_kit', 'viral_kit', 'tiktok_score', "
            "'preflight', 'recommendation'"
            ")",
            name="ck_feedback_items_subject_type",
        ),
        sa.CheckConstraint(
            "feedback_type IN ("
            "'correct', 'incorrect', 'partial', 'missing', 'false_positive', "
            "'false_negative', 'not_useful'"
            ")",
            name="ck_feedback_items_feedback_type",
        ),
        sa.CheckConstraint(
            "subject_version IS NULL OR subject_version >= 1",
            name="ck_feedback_items_subject_version",
        ),
    )
    op.create_index("ix_feedback_items_workspace_id", "feedback_items", ["workspace_id"])
    op.create_index("ix_feedback_items_model_run_id", "feedback_items", ["model_run_id"])
    op.create_index(
        "ix_feedback_items_workspace_subject",
        "feedback_items",
        ["workspace_id", "subject_type", "subject_id"],
    )
    op.create_index(
        "ix_feedback_items_workspace_created",
        "feedback_items",
        ["workspace_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_table("feedback_items")
    op.drop_table("product_events")
    op.drop_constraint(
        "ck_recommendation_actions_action_type",
        "recommendation_actions",
        type_="check",
    )
    op.drop_index("ix_ai_model_runs_operation_created", table_name="ai_model_runs")
    op.drop_index("ix_ai_model_runs_job_operation", table_name="ai_model_runs")
    op.drop_constraint("ck_ai_model_runs_attempt_count", "ai_model_runs", type_="check")
    op.drop_column("ai_model_runs", "safe_error_message")
    op.drop_column("ai_model_runs", "estimated_cost")
    op.drop_column("ai_model_runs", "usage_json")
    op.drop_column("ai_model_runs", "attempt_count")
    op.drop_column("ai_model_runs", "input_hash")
    op.drop_column("ai_model_runs", "schema_version")
    op.drop_column("ai_model_runs", "operation")
