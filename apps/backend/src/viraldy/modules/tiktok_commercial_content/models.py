from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from viraldy.platform.database.base import Base


class ExternalSourceRecordModel(Base):
    __tablename__ = "external_source_records"
    __table_args__ = (
        UniqueConstraint(
            "provider",
            "provider_entity_type",
            "provider_entity_id",
            name="uq_external_source_records_identity",
        ),
        Index("ix_external_source_records_workspace_fetched", "workspace_id", "fetched_at"),
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=True, index=True
    )
    provider: Mapped[str] = mapped_column(String(100), nullable=False)
    provider_entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    provider_entity_id: Mapped[str] = mapped_column(String(255), nullable=False)
    raw_payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    schema_version: Mapped[str] = mapped_column(String(100), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    request_context: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    provider_log_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class CreativeSourceLinkModel(Base):
    __tablename__ = "creative_source_links"
    __table_args__ = (
        UniqueConstraint(
            "creative_asset_id",
            "provider",
            "provider_entity_type",
            "provider_entity_id",
            name="uq_creative_source_links_identity",
        ),
        Index("ix_creative_source_links_asset", "creative_asset_id"),
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    creative_asset_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("assets.id"), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(String(100), nullable=False)
    provider_entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    provider_entity_id: Mapped[str] = mapped_column(String(255), nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_metadata: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CreativeFamilyModel(Base):
    __tablename__ = "creative_families"
    __table_args__ = (Index("ix_creative_families_workspace_scope", "workspace_id", "scope"),)

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=True, index=True
    )
    scope: Mapped[str] = mapped_column(String(30), nullable=False)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    family_type: Mapped[str] = mapped_column(String(50), nullable=False, default="candidate")
    representative_asset_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("assets.id"), nullable=True
    )
    confidence: Mapped[float | None] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="candidate")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class CreativeFamilyMemberModel(Base):
    __tablename__ = "creative_family_members"
    __table_args__ = (
        UniqueConstraint(
            "creative_family_id", "creative_asset_id", name="uq_creative_family_members_asset"
        ),
        Index("ix_creative_family_members_asset", "creative_asset_id"),
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    creative_family_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("creative_families.id"), nullable=False, index=True
    )
    creative_asset_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("assets.id"), nullable=False, index=True
    )
    relationship: Mapped[str] = mapped_column(String(50), nullable=False)
    similarity_score: Mapped[float | None] = mapped_column(nullable=True)
    similarity_evidence: Mapped[dict[str, object]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CreativeFamilyCandidateModel(Base):
    __tablename__ = "creative_family_candidates"
    __table_args__ = (
        UniqueConstraint(
            "scope",
            "workspace_id",
            "asset_a_id",
            "asset_b_id",
            name="uq_creative_family_candidates_pair",
        ),
        Index("ix_creative_family_candidates_scope_status", "scope", "status"),
        Index("ix_creative_family_candidates_asset_a", "asset_a_id"),
        Index("ix_creative_family_candidates_asset_b", "asset_b_id"),
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    scope: Mapped[str] = mapped_column(String(30), nullable=False)
    workspace_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=True, index=True
    )
    asset_a_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("assets.id"), nullable=False
    )
    asset_b_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("assets.id"), nullable=False
    )
    relationship: Mapped[str] = mapped_column(String(50), nullable=False)
    candidate_score: Mapped[float] = mapped_column(nullable=False, default=0.0)
    confidence: Mapped[str] = mapped_column(String(30), nullable=False, default="low")
    signals_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="reviewable")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class PatternEvidenceModel(Base):
    __tablename__ = "pattern_evidence"
    __table_args__ = (
        Index("ix_pattern_evidence_scope_market_category", "scope", "market", "category"),
        Index("ix_pattern_evidence_pattern_kit", "pattern_kit_id"),
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    pattern_kit_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("pattern_kits.id"), nullable=True, index=True
    )
    scope: Mapped[str] = mapped_column(String(30), nullable=False)
    workspace_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=True, index=True
    )
    evidence_level: Mapped[str] = mapped_column(String(50), nullable=False)
    source_asset_ids: Mapped[list[object]] = mapped_column(JSONB, nullable=False, default=list)
    source_family_ids: Mapped[list[object]] = mapped_column(JSONB, nullable=False, default=list)
    market: Mapped[str | None] = mapped_column(String(100), nullable=True)
    category: Mapped[str | None] = mapped_column(String(160), nullable=True)
    date_min: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    date_max: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sample_size: Mapped[int] = mapped_column(nullable=False, default=0)
    comparable_sample_size: Mapped[int | None] = mapped_column(nullable=True)
    metric: Mapped[str | None] = mapped_column(String(100), nullable=True)
    metric_summary: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    confidence: Mapped[str] = mapped_column(String(50), nullable=False, default="low")
    recency: Mapped[str | None] = mapped_column(String(50), nullable=True)
    limitations: Mapped[list[object]] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class CreativeDirectionModel(Base):
    __tablename__ = "creative_directions"
    __table_args__ = (
        Index("ix_creative_directions_workspace_created", "workspace_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False, index=True
    )
    adaptation_run_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("adaptation_runs.id"), nullable=False, index=True
    )
    direction_number: Mapped[int] = mapped_column(nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    payload_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    provenance_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="available")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    selected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class BatchReviewModel(Base):
    __tablename__ = "batch_reviews"
    __table_args__ = (Index("ix_batch_reviews_workspace_created", "workspace_id", "created_at"),)

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False, index=True
    )
    product_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("products.id"), nullable=True, index=True
    )
    objective: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="queued")
    created_by_user_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    summary_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class BatchReviewItemModel(Base):
    __tablename__ = "batch_review_items"
    __table_args__ = (
        UniqueConstraint(
            "batch_review_id", "creative_asset_id", name="uq_batch_review_items_asset"
        ),
        Index("ix_batch_review_items_batch_status", "batch_review_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    batch_review_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("batch_reviews.id"), nullable=False, index=True
    )
    creative_asset_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("assets.id"), nullable=False, index=True
    )
    creative_family_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("creative_families.id"), nullable=True, index=True
    )
    score_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("tiktok_score_runs.id"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="queued")
    decision: Mapped[str | None] = mapped_column(String(50), nullable=True)
    priority: Mapped[str | None] = mapped_column(String(20), nullable=True)
    primary_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommended_action: Mapped[str | None] = mapped_column(String(100), nullable=True)
    evidence_ids_json: Mapped[list[object]] = mapped_column(JSONB, nullable=False, default=list)


class DecisionLogModel(Base):
    __tablename__ = "decision_logs"
    __table_args__ = (
        Index("ix_decision_logs_workspace_entity", "workspace_id", "entity_type", "entity_id"),
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False, index=True
    )
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False, index=True)
    recommendation_type: Mapped[str] = mapped_column(String(100), nullable=False)
    recommended_action: Mapped[str] = mapped_column(String(100), nullable=False)
    reason_codes: Mapped[list[object]] = mapped_column(JSONB, nullable=False, default=list)
    evidence_ids: Mapped[list[object]] = mapped_column(JSONB, nullable=False, default=list)
    model_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    rule_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    seller_response: Mapped[str | None] = mapped_column(String(30), nullable=True)
    seller_final_action: Mapped[str | None] = mapped_column(String(100), nullable=True)
    seller_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MarketInsightSnapshotModel(Base):
    __tablename__ = "market_insight_snapshots"
    __table_args__ = (UniqueConstraint("slug", name="uq_market_insight_snapshots_slug"),)

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    snapshot_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str | None] = mapped_column(String(160), nullable=True)
    market: Mapped[str | None] = mapped_column(String(100), nullable=True)
    date_range_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    source_scope: Mapped[str] = mapped_column(String(30), nullable=False, default="MARKET")
    payload_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_user_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )


class WorkspaceCommercialProfileModel(Base):
    __tablename__ = "workspace_commercial_profiles"

    workspace_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("workspaces.id"), primary_key=True
    )
    account_mode: Mapped[str] = mapped_column(String(30), nullable=False, default="normal")
    feature_flags_json: Mapped[dict[str, object]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    pilot_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    pilot_cohort: Mapped[str | None] = mapped_column(String(100), nullable=True)
    founder_owner: Mapped[str | None] = mapped_column(String(255), nullable=True)


class AnalyticsAttributionModel(Base):
    __tablename__ = "analytics_attributions"
    __table_args__ = (
        Index("ix_analytics_attributions_workspace_created", "workspace_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=True, index=True
    )
    user_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True
    )
    entry_flow: Mapped[str] = mapped_column(String(50), nullable=False)
    utm_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
