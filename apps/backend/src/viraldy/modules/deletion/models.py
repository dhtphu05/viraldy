from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from viraldy.platform.database.base import Base


class DeletionAuditRecordModel(Base):
    __tablename__ = "deletion_audit_records"
    __table_args__ = (
        CheckConstraint(
            "resource_type IN ("
            "'workspace', 'product', 'asset', 'reference', 'creative_dna', "
            "'pattern_kit', 'viral_kit', 'campaign_pack'"
            ")",
            name="ck_deletion_audit_resource_type",
        ),
        CheckConstraint(
            "status IN ('processing', 'storage_cleanup_pending', 'succeeded', 'failed')",
            name="ck_deletion_audit_status",
        ),
        Index(
            "ix_deletion_audit_workspace_created",
            "workspace_id",
            "created_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    initiated_by_user_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    deleted_object_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    deleted_row_counts_json: Mapped[dict[str, int]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    safe_error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    safe_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class StorageDeletionBatchModel(Base):
    __tablename__ = "storage_deletion_batches"
    __table_args__ = (
        CheckConstraint(
            "source_type IN ('hard_delete', 'retention')",
            name="ck_storage_deletion_batch_source_type",
        ),
        CheckConstraint(
            "status IN ('pending', 'succeeded')",
            name="ck_storage_deletion_batch_status",
        ),
        Index(
            "ix_storage_deletion_batches_status_created",
            "status",
            "created_at",
        ),
        Index(
            "ix_storage_deletion_batches_workspace_status",
            "workspace_id",
            "status",
        ),
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    object_keys_json: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    deleted_object_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    safe_error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    safe_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
