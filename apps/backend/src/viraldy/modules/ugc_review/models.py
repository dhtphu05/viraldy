from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from viraldy.platform.database.base import Base


class UGCReviewResultModel(Base):
    __tablename__ = "ugc_review_results"
    __table_args__ = (
        UniqueConstraint(
            "processing_job_id",
            name="uq_ugc_review_results_processing_job_id",
        ),
        CheckConstraint(
            "recommended_next_action IN ('use_as_is', 'revise', 'reshoot_scene', "
            "'confirm_information', 'request_better_media')",
            name="ck_ugc_review_results_next_action",
        ),
        CheckConstraint(
            "overall_confidence IN ('high', 'medium', 'low')",
            name="ck_ugc_review_results_confidence",
        ),
        Index("ix_ugc_review_results_workspace_created", "workspace_id", "created_at"),
        Index("ix_ugc_review_results_asset_id", "asset_id"),
        Index("ix_ugc_review_results_asset_version_id", "asset_version_id"),
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    processing_job_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("processing_jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    asset_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("assets.id", ondelete="SET NULL"), nullable=True
    )
    asset_version_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("asset_versions.id", ondelete="SET NULL"),
        nullable=True,
    )
    headline: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    recommended_next_action: Mapped[str] = mapped_column(Text, nullable=False)
    overall_confidence: Mapped[str] = mapped_column(Text, nullable=False)
    strengths_to_keep: Mapped[list[object]] = mapped_column(JSONB, nullable=False, default=list)
    creator_revision_message: Mapped[str] = mapped_column(Text, nullable=False)
    policy_pack_version: Mapped[str] = mapped_column(Text, nullable=False)
    request_context: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    analysis_provenance: Mapped[dict[str, object]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    result_payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class UGCReviewFindingModel(Base):
    __tablename__ = "ugc_review_findings"
    __table_args__ = (
        CheckConstraint(
            "recommendation_group IN ('fix_first', 'improve', 'confirm')",
            name="ck_ugc_review_findings_recommendation_group",
        ),
        CheckConstraint(
            "owner_role IN ('seller', 'creator', 'editor')",
            name="ck_ugc_review_findings_owner_role",
        ),
        CheckConstraint(
            "fix_type IS NULL OR fix_type IN ('edit_existing_footage', 'add_overlay', "
            "'replace_copy', 'reshoot_scene', 'confirm_seller_input', "
            "'request_better_media')",
            name="ck_ugc_review_findings_fix_type",
        ),
        CheckConstraint(
            "confidence IN ('high', 'medium', 'low')",
            name="ck_ugc_review_findings_confidence",
        ),
        UniqueConstraint(
            "processing_job_id",
            "recommendation_id",
            name="uq_ugc_review_findings_job_recommendation",
        ),
        Index("ix_ugc_review_findings_workspace_job", "workspace_id", "processing_job_id"),
        Index("ix_ugc_review_findings_job_group", "processing_job_id", "recommendation_group"),
        Index("ix_ugc_review_findings_rule_code", "rule_code"),
        Index("ix_ugc_review_findings_mistake_code", "mistake_code"),
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    processing_job_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("processing_jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    rule_code: Mapped[str | None] = mapped_column(
        Text, ForeignKey("domain_policy_rules.code", ondelete="SET NULL"), nullable=True
    )
    mistake_code: Mapped[str | None] = mapped_column(
        Text,
        ForeignKey("domain_mistake_definitions.code", ondelete="SET NULL"),
        nullable=True,
    )
    recommendation_id: Mapped[str] = mapped_column(Text, nullable=False)
    recommendation_group: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    owner_role: Mapped[str] = mapped_column(Text, nullable=False)
    fix_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[list[object]] = mapped_column(JSONB, nullable=False, default=list)
    recommendation_payload: Mapped[dict[str, object]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class UGCReviewRecommendationEventModel(Base):
    __tablename__ = "ugc_review_recommendation_events"
    __table_args__ = (
        CheckConstraint(
            "seller_action IN ('accepted', 'ignored', 'not_applicable', "
            "'sent_to_creator', 'marked_completed')",
            name="ck_ugc_review_recommendation_events_seller_action",
        ),
        Index(
            "ix_ugc_review_recommendation_events_workspace_job_created",
            "workspace_id",
            "processing_job_id",
            "created_at",
        ),
        Index("ix_ugc_review_recommendation_events_finding_id", "finding_id"),
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    processing_job_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("processing_jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    finding_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("ugc_review_findings.id", ondelete="CASCADE"),
        nullable=False,
    )
    seller_action: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class UGCReviewRevisionModel(Base):
    __tablename__ = "ugc_review_revisions"
    __table_args__ = (
        UniqueConstraint(
            "child_processing_job_id",
            name="uq_ugc_review_revisions_child_processing_job_id",
        ),
        CheckConstraint(
            "parent_processing_job_id <> child_processing_job_id",
            name="ck_ugc_review_revisions_distinct_jobs",
        ),
        Index(
            "ix_ugc_review_revisions_workspace_parent_created",
            "workspace_id",
            "parent_processing_job_id",
            "created_at",
        ),
        Index("ix_ugc_review_revisions_parent_asset_version_id", "parent_asset_version_id"),
        Index("ix_ugc_review_revisions_child_asset_version_id", "child_asset_version_id"),
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    parent_processing_job_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("processing_jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    child_processing_job_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("processing_jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    parent_asset_version_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("asset_versions.id", ondelete="SET NULL"),
        nullable=True,
    )
    child_asset_version_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("asset_versions.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class UGCReviewComparisonModel(Base):
    __tablename__ = "ugc_review_comparisons"
    __table_args__ = (
        UniqueConstraint(
            "parent_processing_job_id",
            "child_processing_job_id",
            name="uq_ugc_review_comparisons_job_pair",
        ),
        CheckConstraint(
            "parent_processing_job_id <> child_processing_job_id",
            name="ck_ugc_review_comparisons_distinct_jobs",
        ),
        Index(
            "ix_ugc_review_comparisons_workspace_parent_created",
            "workspace_id",
            "parent_processing_job_id",
            "created_at",
        ),
        Index(
            "ix_ugc_review_comparisons_child_processing_job_id",
            "child_processing_job_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    parent_processing_job_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("processing_jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    child_processing_job_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("processing_jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    resolved_findings: Mapped[list[object]] = mapped_column(JSONB, nullable=False, default=list)
    still_open_findings: Mapped[list[object]] = mapped_column(JSONB, nullable=False, default=list)
    new_findings: Mapped[list[object]] = mapped_column(JSONB, nullable=False, default=list)
    strengths_preserved: Mapped[list[object]] = mapped_column(JSONB, nullable=False, default=list)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    comparison_payload: Mapped[dict[str, object]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
