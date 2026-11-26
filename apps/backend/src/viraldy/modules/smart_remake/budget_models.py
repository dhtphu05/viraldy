from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from viraldy.platform.database.base import Base


class SmartRemakeAttemptModel(Base):
    __tablename__ = "smart_remake_attempts"
    __table_args__ = (
        UniqueConstraint("project_id", "idempotency_key", name="uq_smart_remake_attempt_key"),
        CheckConstraint("estimated_usd >= 0", name="ck_smart_remake_attempt_estimate"),
        CheckConstraint(
            "actual_usd IS NULL OR actual_usd >= 0", name="ck_smart_remake_attempt_actual"
        ),
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("smart_remake_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workspace_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("workspaces.id"))
    actor_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(200))
    request_hash: Mapped[str] = mapped_column(String(64))
    stage: Mapped[str] = mapped_column(String(20))
    purpose: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20))
    provider: Mapped[str] = mapped_column(String(100))
    model: Mapped[str] = mapped_column(String(200))
    provider_task_id: Mapped[str | None] = mapped_column(String(500), nullable=True)
    estimated_usd: Mapped[Decimal] = mapped_column(Numeric(18, 8))
    actual_usd: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    profile_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    policy_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    usage_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    receipt_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    error_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
