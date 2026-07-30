from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
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


class PatternKitModel(Base):
    __tablename__ = "pattern_kits"
    __table_args__ = (
        CheckConstraint(
            "kind IN ("
            "'single_asset_abstraction', 'multi_asset_cluster', "
            "'workspace_learned_pattern', 'category_playbook'"
            ")",
            name="ck_pattern_kits_kind",
        ),
        CheckConstraint(
            "scope IN ('workspace_private', 'product_specific')",
            name="ck_pattern_kits_scope",
        ),
        CheckConstraint(
            "status IN ('candidate', 'reviewed', 'validated', 'deprecated', 'archived')",
            name="ck_pattern_kits_status",
        ),
        CheckConstraint("latest_version >= 1", name="ck_pattern_kits_latest_version"),
        Index("ix_pattern_kits_workspace_status_created", "workspace_id", "status", "created_at"),
        Index("ix_pattern_kits_workspace_kind", "workspace_id", "kind"),
        Index("ix_pattern_kits_workspace_category", "workspace_id", "primary_category"),
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    kind: Mapped[str] = mapped_column(String(100), nullable=False)
    scope: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    primary_category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    target_platforms_json: Mapped[list[object]] = mapped_column(JSONB, nullable=False, default=list)
    target_markets_json: Mapped[list[object]] = mapped_column(JSONB, nullable=False, default=list)
    objectives_json: Mapped[list[object]] = mapped_column(JSONB, nullable=False, default=list)
    latest_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_by_user_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PatternKitVersionModel(Base):
    __tablename__ = "pattern_kit_versions"
    __table_args__ = (
        UniqueConstraint("pattern_kit_id", "version", name="uq_pattern_kit_versions_version"),
        CheckConstraint("version >= 1", name="ck_pattern_kit_versions_version"),
        Index("ix_pattern_kit_versions_workspace_created", "workspace_id", "created_at"),
        Index("ix_pattern_kit_versions_kit_created", "pattern_kit_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    pattern_kit_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("pattern_kits.id"), nullable=False, index=True
    )
    workspace_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    parent_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    change_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    schema_version: Mapped[str] = mapped_column(String(100), nullable=False)
    pattern_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    overall_confidence: Mapped[str] = mapped_column(String(50), nullable=False)
    model_run_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("ai_model_runs.id"), nullable=True, index=True
    )
    created_by_user_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PatternKitSourceModel(Base):
    __tablename__ = "pattern_kit_sources"
    __table_args__ = (
        UniqueConstraint(
            "pattern_kit_version_id",
            "creative_dna_version_id",
            name="uq_pattern_kit_sources_version_dna",
        ),
        UniqueConstraint(
            "pattern_kit_version_id",
            "source_order",
            name="uq_pattern_kit_sources_version_order",
        ),
        CheckConstraint("source_order >= 1", name="ck_pattern_kit_sources_order"),
        Index("ix_pattern_kit_sources_workspace_dna", "workspace_id", "creative_dna_version_id"),
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False, index=True
    )
    pattern_kit_version_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("pattern_kit_versions.id"), nullable=False, index=True
    )
    creative_dna_version_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("creative_dna_versions.id"), nullable=False, index=True
    )
    asset_version_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("asset_versions.id"), nullable=False, index=True
    )
    source_order: Mapped[int] = mapped_column(Integer, nullable=False)


class PatternKitEvidenceLinkModel(Base):
    __tablename__ = "pattern_kit_evidence_links"
    __table_args__ = (
        UniqueConstraint(
            "pattern_kit_version_id",
            "evidence_id",
            "feature_path",
            name="uq_pattern_kit_evidence_links_ref",
        ),
        Index("ix_pattern_kit_evidence_links_workspace", "workspace_id"),
        Index("ix_pattern_kit_evidence_links_evidence", "evidence_id"),
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False, index=True
    )
    pattern_kit_version_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("pattern_kit_versions.id"), nullable=False, index=True
    )
    evidence_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("evidence_items.id"), nullable=False, index=True
    )
    feature_path: Mapped[str] = mapped_column(String(500), nullable=False)


class PatternKitActionModel(Base):
    __tablename__ = "pattern_kit_actions"
    __table_args__ = (
        CheckConstraint(
            "action IN ('reviewed', 'validated', 'deprecated', 'archived', 'restored')",
            name="ck_pattern_kit_actions_action",
        ),
        Index("ix_pattern_kit_actions_workspace_created", "workspace_id", "created_at"),
        Index("ix_pattern_kit_actions_kit_created", "pattern_kit_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False, index=True
    )
    pattern_kit_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("pattern_kits.id"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    actor_user_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
