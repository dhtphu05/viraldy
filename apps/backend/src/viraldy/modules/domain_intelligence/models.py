from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, Integer, String, Text, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from viraldy.platform.database.base import Base

JSON_TYPE = JSON().with_variant(JSONB(), "postgresql")  # type: ignore[no-untyped-call]


class DomainPolicyPackModel(Base):
    __tablename__ = "domain_policy_packs"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    pack_name: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    meta_json: Mapped[dict[str, object]] = mapped_column("meta", JSON_TYPE, nullable=False)
    raw_payload: Mapped[dict[str, object]] = mapped_column(JSON_TYPE, nullable=False)
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("uq_domain_policy_packs_name_version", "pack_name", "version", unique=True),
        Index("ix_domain_policy_packs_status", "status"),
    )


class DomainPolicySourceModel(Base):
    __tablename__ = "domain_policy_sources"

    source_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    publisher: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(String(100), nullable=False)
    source_date: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_strength: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_payload: Mapped[dict[str, object]] = mapped_column(JSON_TYPE, nullable=False)
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class DomainPolicyRuleModel(Base):
    __tablename__ = "domain_policy_rules"

    code: Mapped[str] = mapped_column(String(100), primary_key=True)
    pack_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("domain_policy_packs.id"), nullable=False
    )
    domain: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    rule_type: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[str] = mapped_column(String(100), nullable=False)
    enabled_for_mvp: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    applicability: Mapped[list[object]] = mapped_column(JSON_TYPE, nullable=False, default=list)
    required_conditions: Mapped[list[object]] = mapped_column(
        JSON_TYPE, nullable=False, default=list
    )
    implementation: Mapped[dict[str, object]] = mapped_column(
        JSON_TYPE, nullable=False, default=dict
    )
    source_ids: Mapped[list[object]] = mapped_column(JSON_TYPE, nullable=False, default=list)
    raw_payload: Mapped[dict[str, object]] = mapped_column(JSON_TYPE, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("ix_domain_policy_rules_pack_active", "pack_id", "enabled_for_mvp"),
        Index("ix_domain_policy_rules_domain", "domain"),
    )


class DomainCreativePatternModel(Base):
    __tablename__ = "domain_creative_patterns"

    code: Mapped[str] = mapped_column(String(100), primary_key=True)
    pack_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("domain_policy_packs.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    finding_classification: Mapped[str] = mapped_column(String(100), nullable=False)
    performance_evidence_status: Mapped[str | None] = mapped_column(Text, nullable=True)
    enabled_for_mvp: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    raw_payload: Mapped[dict[str, object]] = mapped_column(JSON_TYPE, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class DomainMistakeDefinitionModel(Base):
    __tablename__ = "domain_mistake_definitions"

    code: Mapped[str] = mapped_column(String(100), primary_key=True)
    pack_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("domain_policy_packs.id"), nullable=False
    )
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(100), nullable=False)
    editable_or_reshoot: Mapped[str] = mapped_column(String(100), nullable=False)
    enabled_for_mvp: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    raw_payload: Mapped[dict[str, object]] = mapped_column(JSON_TYPE, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class DomainUncertaintyModel(Base):
    __tablename__ = "domain_uncertainties"

    code: Mapped[str] = mapped_column(String(100), primary_key=True)
    pack_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("domain_policy_packs.id"), nullable=False
    )
    topic: Mapped[str] = mapped_column(Text, nullable=False)
    classification: Mapped[str] = mapped_column(String(100), nullable=False)
    raw_payload: Mapped[dict[str, object]] = mapped_column(JSON_TYPE, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class DomainPolicyRuleSourceModel(Base):
    __tablename__ = "domain_policy_rule_sources"

    rule_code: Mapped[str] = mapped_column(
        String(100), ForeignKey("domain_policy_rules.code"), primary_key=True
    )
    source_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("domain_policy_sources.source_id"), primary_key=True
    )

    __table_args__ = (Index("ix_domain_policy_rule_sources_source", "source_id"),)


DOMAIN_INTELLIGENCE_TABLES = (
    DomainPolicyPackModel.__table__,
    DomainPolicySourceModel.__table__,
    DomainPolicyRuleModel.__table__,
    DomainCreativePatternModel.__table__,
    DomainMistakeDefinitionModel.__table__,
    DomainUncertaintyModel.__table__,
    DomainPolicyRuleSourceModel.__table__,
)
