from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from viraldy.platform.database.base import Base


class CampaignPackModel(Base):
    __tablename__ = "campaign_packs"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False, index=True
    )
    product_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("products.id"), nullable=False, index=True
    )
    adaptation_run_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("adaptation_runs.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    current_version_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("campaign_pack_versions.id"), nullable=True
    )
    created_by_user_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CampaignPackVersionModel(Base):
    __tablename__ = "campaign_pack_versions"
    __table_args__ = (
        UniqueConstraint(
            "campaign_pack_id", "version_number", name="uq_campaign_pack_versions_pack_number"
        ),
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    campaign_pack_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("campaign_packs.id"), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    brief_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    change_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_adaptation_run_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("adaptation_runs.id"), nullable=True, index=True
    )
    source_model_run_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("ai_model_runs.id"), nullable=True, index=True
    )
    source_prompt_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source_schema_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_by_user_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
