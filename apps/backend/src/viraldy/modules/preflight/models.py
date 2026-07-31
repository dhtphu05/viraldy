from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from viraldy.platform.database.base import Base


class PreflightRunModel(Base):
    __tablename__ = "preflight_runs"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False, index=True
    )
    ugc_asset_version_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("asset_versions.id"), nullable=False, index=True
    )
    campaign_pack_version_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("campaign_pack_versions.id"), nullable=False, index=True
    )
    structural_score_run_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("tiktok_score_runs.id"), nullable=True
    )
    processing_job_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("processing_jobs.id"), nullable=True, index=True
    )
    primary_model_run_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("ai_model_runs.id"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    structural_score: Mapped[Decimal] = mapped_column(Numeric, nullable=False, default=0)
    brief_alignment_score: Mapped[Decimal] = mapped_column(Numeric, nullable=False, default=0)
    preflight_score: Mapped[Decimal] = mapped_column(Numeric, nullable=False, default=0)
    confidence: Mapped[str] = mapped_column(String(50), nullable=False, default="low")
    action_label: Mapped[str] = mapped_column(String(100), nullable=False, default="pending")
    dimension_scores_json: Mapped[dict[str, object]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    brief_alignment_json: Mapped[dict[str, object]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    strengths_json: Mapped[list[object]] = mapped_column(JSONB, nullable=False, default=list)
    blockers_json: Mapped[list[object]] = mapped_column(JSONB, nullable=False, default=list)
    fixes_json: Mapped[list[object]] = mapped_column(JSONB, nullable=False, default=list)
    revision_message: Mapped[str] = mapped_column(Text, nullable=False, default="")
    seller_summary_json: Mapped[dict[str, object] | None] = mapped_column(
        JSONB, nullable=True
    )
    creator_revision_json: Mapped[dict[str, object] | None] = mapped_column(
        JSONB, nullable=True
    )
    presentation_model_run_ids_json: Mapped[list[object]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    presentation_source_json: Mapped[dict[str, object]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    evidence_ids_json: Mapped[list[object]] = mapped_column(JSONB, nullable=False, default=list)
    schema_version: Mapped[str] = mapped_column(
        String(100), nullable=False, default="ugc_preflight_legacy_v1"
    )
    product_snapshot_json: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    product_context_schema_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    requirements_snapshot_json: Mapped[dict[str, object] | None] = mapped_column(
        JSONB, nullable=True
    )
    analysis_mode: Mapped[str] = mapped_column(String(50), nullable=False)
    pipeline_version: Mapped[str] = mapped_column(
        String(100), nullable=False, default="media_pipeline_v1"
    )
    rubric_version: Mapped[str] = mapped_column(String(100), nullable=False)
    rule_version: Mapped[str] = mapped_column(String(100), nullable=False)
    model_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
