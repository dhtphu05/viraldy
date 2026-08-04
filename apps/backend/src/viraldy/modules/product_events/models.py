from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from viraldy.platform.database.base import Base


class ProductEventModel(Base):
    __tablename__ = "product_events"
    __table_args__ = (
        CheckConstraint(
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
            ", 'tiktok_scorer_opened', 'tiktok_score_started', "
            "'tiktok_score_completed', 'tiktok_score_failed', 'tiktok_finding_viewed', "
            "'tiktok_evidence_opened', 'tiktok_fix_accepted', 'tiktok_fix_rejected', "
            "'tiktok_fix_sent_to_creator', 'tiktok_fix_sent_to_editor', "
            "'tiktok_fix_marked_completed', 'tiktok_revision_uploaded', "
            "'tiktok_comparison_viewed', 'tiktok_action_verified_after_revision'"
            ")",
            name="ck_product_events_event_type",
        ),
        Index("ix_product_events_workspace_created", "workspace_id", "created_at"),
        Index(
            "ix_product_events_workspace_event_created",
            "workspace_id",
            "event_type",
            "created_at",
        ),
        Index("ix_product_events_actor_created", "actor_user_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=True, index=True
    )
    actor_user_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    subject_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    subject_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    payload_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
