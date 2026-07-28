from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from viraldy.platform.database.base import Base


class CreativeDnaVersionModel(Base):
    __tablename__ = "creative_dna_versions"
    __table_args__ = (
        UniqueConstraint(
            "asset_version_id", "version_number", name="uq_creative_dna_asset_version_number"
        ),
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False, index=True
    )
    reference_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("references.id"), nullable=True, index=True
    )
    asset_version_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("asset_versions.id"), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    dna_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    confidence: Mapped[str] = mapped_column(String(50), nullable=False)
    analysis_mode: Mapped[str] = mapped_column(String(50), nullable=False)
    taxonomy_version: Mapped[str] = mapped_column(String(100), nullable=False)
    model_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
