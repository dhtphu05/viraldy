from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from viraldy.platform.database.base import Base


class TikTokScoreProfileModel(Base):
    __tablename__ = "tiktok_score_profiles"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "code",
            "profile_version",
            name="uq_tiktok_score_profiles_workspace_code_version",
        ),
        Index("ix_tiktok_score_profiles_code_active", "code", "is_active"),
        Index(
            "uq_tiktok_score_profiles_system_code_version",
            "code",
            "profile_version",
            unique=True,
            postgresql_where=text("workspace_id IS NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    code: Mapped[str] = mapped_column(String(100), nullable=False)
    label: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    profile_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    weights_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    thresholds_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    configuration_json: Mapped[dict[str, object]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class TikTokScoreRunModel(Base):
    __tablename__ = "tiktok_score_runs"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "idempotency_key",
            name="uq_tiktok_score_runs_workspace_idempotency",
        ),
        Index(
            "ix_tiktok_score_runs_workspace_status_created",
            "workspace_id",
            "status",
            "created_at",
        ),
        Index(
            "ix_tiktok_score_runs_workspace_asset_created",
            "workspace_id",
            "asset_id",
            "created_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False, index=True
    )
    asset_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("assets.id"), nullable=True, index=True
    )
    asset_version_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("asset_versions.id"), nullable=False, index=True
    )
    product_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True
    )
    parent_score_run_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("tiktok_score_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    creative_dna_version_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("creative_dna_versions.id"), nullable=True
    )
    processing_job_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("processing_jobs.id"), nullable=True, index=True
    )
    primary_model_run_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("ai_model_runs.id"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    current_stage: Mapped[str] = mapped_column(String(100), nullable=False, default="queued")
    schema_version: Mapped[str] = mapped_column(
        String(100), nullable=False, default="tiktok_score_v1"
    )
    idempotency_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    score_mode: Mapped[str] = mapped_column(String(50), nullable=False, default="quick")
    intended_use: Mapped[str] = mapped_column(String(50), nullable=False, default="tiktok_organic")
    score_profile: Mapped[str] = mapped_column(
        String(100), nullable=False, default="general_tiktok_v1"
    )
    score_profile_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    score_profile_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("tiktok_score_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    profile_selection_mode: Mapped[str] = mapped_column(
        String(100), nullable=False, default="user_selected"
    )
    profile_selection_confidence: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 4), nullable=True
    )
    alternative_profiles_json: Mapped[list[object]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    profile_evidence_ids_json: Mapped[list[object]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    profile_override_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    product_context_snapshot_json: Mapped[dict[str, object] | None] = mapped_column(
        JSONB, nullable=True
    )
    product_context_snapshot_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    product_context_schema_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    product_context_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    policy_pack_versions_json: Mapped[dict[str, object]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    rule_versions_json: Mapped[dict[str, object]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    prompt_versions_json: Mapped[dict[str, object]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    model_provider_versions_json: Mapped[dict[str, object]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    media_checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    creative_direction_context_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), nullable=True
    )
    creative_direction_context_snapshot_json: Mapped[dict[str, object] | None] = mapped_column(
        JSONB, nullable=True
    )
    creative_direction_context_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    creative_direction_lookup_error: Mapped[str | None] = mapped_column(String(100), nullable=True)
    structural_score: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    confidence: Mapped[str] = mapped_column(String(50), nullable=False, default="low")
    confidence_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    action_label: Mapped[str] = mapped_column(String(100), nullable=False, default="pending")
    creative_structure_decision: Mapped[str] = mapped_column(
        String(100), nullable=False, default="pending"
    )
    paid_use_rights_status: Mapped[str] = mapped_column(
        String(100), nullable=False, default="not_evaluated"
    )
    final_paid_readiness: Mapped[str] = mapped_column(
        String(100), nullable=False, default="not_evaluated"
    )
    dimension_scores_json: Mapped[dict[str, object]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    strengths_json: Mapped[list[object]] = mapped_column(JSONB, nullable=False, default=list)
    blockers_json: Mapped[list[object]] = mapped_column(JSONB, nullable=False, default=list)
    fixes_json: Mapped[list[object]] = mapped_column(JSONB, nullable=False, default=list)
    evidence_ids_json: Mapped[list[object]] = mapped_column(JSONB, nullable=False, default=list)
    scene_inventory_json: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    auxiliary_signals_json: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    creative_upgrades_json: Mapped[list[object]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    result_json: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    analysis_mode: Mapped[str] = mapped_column(String(50), nullable=False)
    pipeline_version: Mapped[str] = mapped_column(
        String(100), nullable=False, default="media_pipeline_v1"
    )
    rubric_version: Mapped[str] = mapped_column(String(100), nullable=False)
    rule_version: Mapped[str] = mapped_column(String(100), nullable=False)
    model_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    token_usage_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    cost_estimate: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    failure_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TikTokScoreDimensionModel(Base):
    __tablename__ = "tiktok_score_dimensions"
    __table_args__ = (
        UniqueConstraint("score_run_id", "code", name="uq_tiktok_score_dimensions_run_code"),
        Index("ix_tiktok_score_dimensions_workspace_run", "workspace_id", "score_run_id"),
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False, index=True
    )
    score_run_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("tiktok_score_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(String(100), nullable=False)
    label: Mapped[str] = mapped_column(String(160), nullable=False)
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    applicability: Mapped[str] = mapped_column(String(50), nullable=False)
    evidence_status: Mapped[str] = mapped_column(String(50), nullable=False)
    confidence: Mapped[str] = mapped_column(String(50), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    positive_signals_json: Mapped[list[object]] = mapped_column(JSONB, nullable=False, default=list)
    missing_signals_json: Mapped[list[object]] = mapped_column(JSONB, nullable=False, default=list)
    uncertainty_json: Mapped[list[object]] = mapped_column(JSONB, nullable=False, default=list)
    evidence_ids_json: Mapped[list[object]] = mapped_column(JSONB, nullable=False, default=list)
    contributing_rule_codes_json: Mapped[list[object]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    result_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TikTokScoreFindingModel(Base):
    __tablename__ = "tiktok_score_findings"
    __table_args__ = (
        Index("ix_tiktok_score_findings_workspace_run", "workspace_id", "score_run_id"),
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False, index=True
    )
    score_run_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("tiktok_score_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(String(120), nullable=False)
    rule_code: Mapped[str] = mapped_column(String(160), nullable=False)
    rule_class: Mapped[str] = mapped_column(String(100), nullable=False)
    source_dimension: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[str] = mapped_column(String(50), nullable=False)
    priority: Mapped[str] = mapped_column(String(10), nullable=False)
    applicability: Mapped[str] = mapped_column(String(50), nullable=False)
    evidence_status: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    expected_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    observed_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    target_time_range_ms_json: Mapped[list[object] | None] = mapped_column(JSONB, nullable=True)
    evidence_ids_json: Mapped[list[object]] = mapped_column(JSONB, nullable=False, default=list)
    uncertainty_json: Mapped[list[object]] = mapped_column(JSONB, nullable=False, default=list)
    requires_seller_truth: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    can_be_resolved_by_edit: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    requires_physical_reshoot: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    finding_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TikTokFixActionModel(Base):
    __tablename__ = "tiktok_fix_actions"
    __table_args__ = (Index("ix_tiktok_fix_actions_workspace_run", "workspace_id", "score_run_id"),)

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False, index=True
    )
    score_run_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("tiktok_score_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    finding_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("tiktok_score_findings.id", ondelete="SET NULL"),
        nullable=True,
    )
    code: Mapped[str] = mapped_column(String(120), nullable=False)
    recommendation_class: Mapped[str] = mapped_column(String(100), nullable=False)
    basis: Mapped[str] = mapped_column(String(100), nullable=False)
    priority: Mapped[str] = mapped_column(String(10), nullable=False)
    severity: Mapped[str] = mapped_column(String(50), nullable=False)
    source_dimension: Mapped[str] = mapped_column(String(100), nullable=False)
    owner_role: Mapped[str] = mapped_column(String(50), nullable=False)
    fix_type: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    why_it_matters: Mapped[str] = mapped_column(Text, nullable=False)
    expected_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    observed_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    evidence_ids_json: Mapped[list[object]] = mapped_column(JSONB, nullable=False, default=list)
    target_time_range_ms_json: Mapped[list[object] | None] = mapped_column(JSONB, nullable=True)
    video_operations_json: Mapped[list[object]] = mapped_column(JSONB, nullable=False, default=list)
    instructions_json: Mapped[list[object]] = mapped_column(JSONB, nullable=False, default=list)
    strengths_to_preserve_json: Mapped[list[object]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    required_inputs_json: Mapped[list[object]] = mapped_column(JSONB, nullable=False, default=list)
    estimated_effort: Mapped[str] = mapped_column(String(50), nullable=False)
    reshoot_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    completion_criteria_json: Mapped[list[object]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    verification_method: Mapped[str] = mapped_column(Text, nullable=False)
    current_action_state: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    action_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class TikTokFixActionEventModel(Base):
    __tablename__ = "tiktok_fix_action_events"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "fix_action_id",
            "idempotency_key",
            name="uq_tiktok_fix_action_events_action_idempotency",
        ),
        Index("ix_tiktok_fix_action_events_workspace_action", "workspace_id", "fix_action_id"),
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False, index=True
    )
    score_run_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("tiktok_score_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    fix_action_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("tiktok_fix_actions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    actor_user_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    details_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TikTokScoreComparisonModel(Base):
    __tablename__ = "tiktok_score_comparisons"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "before_score_run_id",
            "after_score_run_id",
            name="uq_tiktok_score_comparisons_run_pair",
        ),
        Index(
            "ix_tiktok_score_comparisons_workspace_before",
            "workspace_id",
            "before_score_run_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False, index=True
    )
    before_score_run_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("tiktok_score_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    after_score_run_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("tiktok_score_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    accepted_fix_action_ids_json: Mapped[list[object]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    resolved_blockers_json: Mapped[list[object]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    unresolved_blockers_json: Mapped[list[object]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    new_regressions_json: Mapped[list[object]] = mapped_column(JSONB, nullable=False, default=list)
    dimension_changes_json: Mapped[list[object]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    evidence_before_after_json: Mapped[list[object]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    strengths_preserved_json: Mapped[list[object]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    actions_verified_json: Mapped[list[object]] = mapped_column(JSONB, nullable=False, default=list)
    final_next_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    comparison_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    failure_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
