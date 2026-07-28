from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from viraldy.platform.database.base import Base


class MediaArtifactModel(Base):
    __tablename__ = "media_artifacts"
    __table_args__ = (
        Index(
            "ix_media_artifacts_workspace_version_type",
            "workspace_id",
            "asset_version_id",
            "artifact_type",
        ),
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False, index=True
    )
    asset_version_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("asset_versions.id"), nullable=False, index=True
    )
    artifact_type: Mapped[str] = mapped_column(String(100), nullable=False)
    storage_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload_json: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    provider: Mapped[str] = mapped_column(String(100), nullable=False)
    model_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    analysis_mode: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EvidenceItemModel(Base):
    __tablename__ = "evidence_items"
    __table_args__ = (
        Index(
            "ix_evidence_items_workspace_version_type",
            "workspace_id",
            "asset_version_id",
            "evidence_type",
        ),
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False, index=True
    )
    asset_version_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("asset_versions.id"), nullable=False, index=True
    )
    analysis_run_type: Mapped[str] = mapped_column(String(100), nullable=False)
    analysis_run_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    evidence_type: Mapped[str] = mapped_column(String(100), nullable=False)
    start_ms: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    end_ms: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    frame_storage_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    value_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    provider: Mapped[str | None] = mapped_column(String(100), nullable=True)
    model_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
