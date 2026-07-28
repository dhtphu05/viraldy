from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from viraldy.platform.database.base import Base


class AdaptationRunModel(Base):
    __tablename__ = "adaptation_runs"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False, index=True
    )
    product_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("products.id"), nullable=False, index=True
    )
    creative_dna_version_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("creative_dna_versions.id"), nullable=False, index=True
    )
    objective: Mapped[str] = mapped_column(String(255), nullable=False)
    target_market: Mapped[str] = mapped_column(String(100), nullable=False)
    target_buyer_json: Mapped[dict[str, object]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    constraints_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    result_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    analysis_mode: Mapped[str] = mapped_column(String(50), nullable=False)
    model_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    prompt_version: Mapped[str] = mapped_column(String(100), nullable=False)
    created_by_user_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
