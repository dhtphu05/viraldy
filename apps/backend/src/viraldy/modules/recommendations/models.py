from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from viraldy.platform.database.base import Base


class RecommendationModel(Base):
    __tablename__ = "recommendations"
    __table_args__ = (Index("ix_recommendations_workspace_created", "workspace_id", "created_at"),)

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False, index=True
    )
    subject_type: Mapped[str] = mapped_column(String(100), nullable=False)
    subject_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    recommendation_type: Mapped[str] = mapped_column(String(100), nullable=False)
    action: Mapped[str] = mapped_column(String(255), nullable=False)
    confidence: Mapped[str] = mapped_column(String(50), nullable=False)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    assumptions_json: Mapped[list[object]] = mapped_column(JSONB, nullable=False, default=list)
    model_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    rule_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source_run_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RecommendationActionModel(Base):
    __tablename__ = "recommendation_actions"
    __table_args__ = (
        Index("ix_recommendation_actions_workspace_created", "workspace_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    recommendation_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("recommendations.id"), nullable=False
    )
    workspace_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False, index=True
    )
    user_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    action_type: Mapped[str] = mapped_column(String(50), nullable=False)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
