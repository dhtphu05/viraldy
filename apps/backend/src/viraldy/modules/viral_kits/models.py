from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from viraldy.platform.database.base import Base


class ViralKitModel(Base):
    __tablename__ = "viral_kits"
    __table_args__ = (
        CheckConstraint(
            "objective IN ("
            "'tiktok_shop_affiliate_test', 'tiktok_shop_organic_test', "
            "'small_paid_test', 'spark_candidate', 'ugc_paid_asset', "
            "'pod_gift_campaign', 'dropshipping_demo_test', 'creative_refresh'"
            ")",
            name="ck_viral_kits_objective",
        ),
        CheckConstraint(
            "platform IN ('tiktok_shop', 'tiktok_organic', 'tiktok_paid')",
            name="ck_viral_kits_platform",
        ),
        CheckConstraint(
            "status IN ("
            "'draft', 'generating', 'ready_for_review', 'concept_selected', "
            "'production_ready', 'testing', 'completed', 'archived', 'failed'"
            ")",
            name="ck_viral_kits_status",
        ),
        CheckConstraint("latest_version >= 1", name="ck_viral_kits_latest_version"),
        Index("ix_viral_kits_workspace_status_created", "workspace_id", "status", "created_at"),
        Index("ix_viral_kits_workspace_product", "workspace_id", "product_id"),
        Index("ix_viral_kits_workspace_objective", "workspace_id", "objective"),
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False, index=True
    )
    product_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("products.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    objective: Mapped[str] = mapped_column(String(100), nullable=False)
    platform: Mapped[str] = mapped_column(String(100), nullable=False)
    target_market: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    latest_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    selected_concept_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_by_user_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ViralKitVersionModel(Base):
    __tablename__ = "viral_kit_versions"
    __table_args__ = (
        UniqueConstraint("viral_kit_id", "version", name="uq_viral_kit_versions_version"),
        CheckConstraint("version >= 1", name="ck_viral_kit_versions_version"),
        CheckConstraint(
            "product_context_version >= 1",
            name="ck_viral_kit_versions_product_context_version",
        ),
        Index("ix_viral_kit_versions_workspace_created", "workspace_id", "created_at"),
        Index("ix_viral_kit_versions_kit_created", "viral_kit_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    viral_kit_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("viral_kits.id"), nullable=False, index=True
    )
    workspace_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    parent_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    change_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    schema_version: Mapped[str] = mapped_column(String(100), nullable=False)
    product_context_version: Mapped[int] = mapped_column(Integer, nullable=False)
    product_snapshot_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    viral_kit_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    model_run_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("ai_model_runs.id"), nullable=True, index=True
    )
    created_by_user_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ViralKitPatternLinkModel(Base):
    __tablename__ = "viral_kit_pattern_links"
    __table_args__ = (
        UniqueConstraint(
            "viral_kit_version_id",
            "pattern_kit_version_id",
            name="uq_viral_kit_pattern_links_version_pattern",
        ),
        CheckConstraint("match_score >= 0 AND match_score <= 1", name="ck_viral_pattern_score"),
        CheckConstraint(
            "applicability_status IN ('matched', 'partial', 'override', 'rejected')",
            name="ck_viral_pattern_status",
        ),
        Index("ix_viral_pattern_links_workspace", "workspace_id"),
        Index("ix_viral_pattern_links_pattern", "workspace_id", "pattern_kit_version_id"),
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False, index=True
    )
    viral_kit_version_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("viral_kit_versions.id"), nullable=False, index=True
    )
    pattern_kit_version_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("pattern_kit_versions.id"), nullable=False, index=True
    )
    match_score: Mapped[float] = mapped_column(Float, nullable=False)
    applicability_status: Mapped[str] = mapped_column(String(50), nullable=False)
    selection_reason: Mapped[str] = mapped_column(Text, nullable=False)


class ViralKitConceptActionModel(Base):
    __tablename__ = "viral_kit_concept_actions"
    __table_args__ = (
        CheckConstraint(
            "action IN ('selected', 'rejected', 'restored', 'campaign_pack_created')",
            name="ck_viral_concept_actions_action",
        ),
        CheckConstraint(
            "viral_kit_version >= 1",
            name="ck_viral_concept_actions_version",
        ),
        Index("ix_viral_concept_actions_workspace_created", "workspace_id", "created_at"),
        Index("ix_viral_concept_actions_kit_created", "viral_kit_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False, index=True
    )
    viral_kit_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("viral_kits.id"), nullable=False, index=True
    )
    viral_kit_version: Mapped[int] = mapped_column(Integer, nullable=False)
    concept_id: Mapped[str] = mapped_column(String(120), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    actor_user_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ViralKitCampaignPackLinkModel(Base):
    __tablename__ = "viral_kit_campaign_pack_links"
    __table_args__ = (
        UniqueConstraint(
            "viral_kit_version_id",
            "concept_id",
            "campaign_pack_id",
            name="uq_viral_campaign_pack_links_pack",
        ),
        Index("ix_viral_campaign_pack_links_workspace", "workspace_id"),
        Index("ix_viral_campaign_pack_links_concept", "viral_kit_version_id", "concept_id"),
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False, index=True
    )
    viral_kit_version_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("viral_kit_versions.id"), nullable=False, index=True
    )
    concept_id: Mapped[str] = mapped_column(String(120), nullable=False)
    campaign_pack_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("campaign_packs.id"), nullable=False, index=True
    )
    campaign_pack_version_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("campaign_pack_versions.id"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
