from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from viraldy.platform.database.base import Base


class FeedbackItemModel(Base):
    __tablename__ = "feedback_items"
    __table_args__ = (
        CheckConstraint(
            "subject_type IN ("
            "'creative_dna', 'pattern_kit', 'viral_kit', 'tiktok_score', "
            "'preflight', 'recommendation'"
            ")",
            name="ck_feedback_items_subject_type",
        ),
        CheckConstraint(
            "feedback_type IN ("
            "'correct', 'incorrect', 'partial', 'missing', 'false_positive', "
            "'false_negative', 'not_useful'"
            ")",
            name="ck_feedback_items_feedback_type",
        ),
        CheckConstraint(
            "subject_version IS NULL OR subject_version >= 1",
            name="ck_feedback_items_subject_version",
        ),
        Index(
            "ix_feedback_items_workspace_subject",
            "workspace_id",
            "subject_type",
            "subject_id",
        ),
        Index("ix_feedback_items_workspace_created", "workspace_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False, index=True
    )
    subject_type: Mapped[str] = mapped_column(String(100), nullable=False)
    subject_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    subject_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    field_path: Mapped[str] = mapped_column(String(500), nullable=False)
    feedback_type: Mapped[str] = mapped_column(String(50), nullable=False)
    ai_value_json: Mapped[object | None] = mapped_column(JSONB, nullable=True)
    user_value_json: Mapped[object | None] = mapped_column(JSONB, nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_run_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("ai_model_runs.id"), nullable=True, index=True
    )
    created_by_user_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
