from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import cast
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import InstrumentedAttribute

from viraldy.modules.domain_intelligence.models import (
    DomainCreativePatternModel,
    DomainMistakeDefinitionModel,
    DomainPolicyPackModel,
    DomainPolicyRuleModel,
    DomainPolicyRuleSourceModel,
    DomainPolicySourceModel,
    DomainUncertaintyModel,
)
from viraldy.modules.domain_intelligence.schemas import (
    DomainRule,
    PolicyPackCounts,
    PolicyPackStatus,
)
from viraldy.shared.errors.base import AppError

UpsertOutcome = str


def _values_match(model: object, values: Mapping[str, object]) -> bool:
    return all(getattr(model, field) == value for field, value in values.items())


def _update_values(model: object, values: Mapping[str, object]) -> None:
    for field, value in values.items():
        setattr(model, field, value)


def _rule_from_model(model: DomainPolicyRuleModel) -> DomainRule:
    return DomainRule(
        code=model.code,
        domain=model.domain,
        title=model.title,
        rule_type=model.rule_type,
        severity=model.severity,
        enabled_for_mvp=model.enabled_for_mvp,
        applicability=list(model.applicability),
        required_conditions=list(model.required_conditions),
        implementation=dict(model.implementation),
        source_ids=[str(value) for value in model.source_ids],
        raw_payload=dict(model.raw_payload),
    )


class SyncDomainIntelligenceRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def upsert_pack(
        self,
        *,
        pack_name: str,
        version: str,
        status: str,
        content_hash: str,
        meta_json: dict[str, object],
        raw_payload: dict[str, object],
    ) -> tuple[DomainPolicyPackModel, UpsertOutcome]:
        existing = self._session.execute(
            select(DomainPolicyPackModel).where(
                DomainPolicyPackModel.pack_name == pack_name,
                DomainPolicyPackModel.version == version,
            )
        ).scalar_one_or_none()
        values: dict[str, object] = {
            "status": status,
            "content_hash": content_hash,
            "meta_json": meta_json,
            "raw_payload": raw_payload,
        }
        if existing is None:
            model = DomainPolicyPackModel(
                pack_name=pack_name,
                version=version,
                **values,
            )
            self._session.add(model)
            self._session.flush()
            return model, "inserted"
        if existing.status == "published" and existing.content_hash != content_hash:
            raise RuntimeError(
                f"published policy pack {pack_name!r} version {version!r} cannot be mutated"
            )
        if _values_match(existing, values):
            return existing, "skipped"
        _update_values(existing, values)
        self._session.flush()
        return existing, "updated"

    def upsert_source(self, record: dict[str, object]) -> UpsertOutcome:
        source_id = str(record["id"])
        existing = self._session.get(DomainPolicySourceModel, source_id)
        values: dict[str, object] = {
            "title": str(record["title"]),
            "publisher": str(record["publisher"]),
            "url": str(record["url"]),
            "source_type": str(record["type"]),
            "source_date": _optional_text(record.get("date")),
            "evidence_strength": int(cast(int, record["strength"])),
            "notes": _optional_text(record.get("notes")),
            "raw_payload": record,
        }
        if existing is None:
            self._session.add(DomainPolicySourceModel(source_id=source_id, **values))
            return "inserted"
        return self._update_or_skip(existing, values)

    def upsert_rule(
        self,
        pack_id: UUID,
        record: dict[str, object],
        *,
        enabled_for_mvp: bool,
    ) -> UpsertOutcome:
        code = str(record["code"])
        existing = self._session.get(DomainPolicyRuleModel, code)
        sources = cast(list[dict[str, object]], record.get("sources") or [])
        source_ids = [str(source["source_id"]) for source in sources]
        values: dict[str, object] = {
            "pack_id": pack_id,
            "domain": str(record["domain"]),
            "title": str(record["title"]),
            "rule_type": str(record["rule_type"]),
            "severity": str(record["severity"]),
            "enabled_for_mvp": enabled_for_mvp,
            "applicability": list(cast(list[object], record.get("applicability") or [])),
            "required_conditions": list(
                cast(list[object], record.get("required_conditions") or [])
            ),
            "implementation": dict(cast(dict[str, object], record.get("implementation") or {})),
            "source_ids": source_ids,
            "raw_payload": record,
        }
        if existing is None:
            self._session.add(DomainPolicyRuleModel(code=code, **values))
            outcome = "inserted"
        else:
            outcome = self._update_or_skip(existing, values)
        self._session.flush()
        self._sync_rule_sources(code, source_ids)
        return outcome

    def upsert_pattern(
        self,
        pack_id: UUID,
        record: dict[str, object],
    ) -> UpsertOutcome:
        code = str(record["code"])
        existing = self._session.get(DomainCreativePatternModel, code)
        values: dict[str, object] = {
            "pack_id": pack_id,
            "name": str(record["name"]),
            "finding_classification": str(record["finding_classification"]),
            "performance_evidence_status": _optional_text(
                record.get("performance_evidence_status")
            ),
            "enabled_for_mvp": False,
            "raw_payload": record,
        }
        if existing is None:
            self._session.add(DomainCreativePatternModel(code=code, **values))
            return "inserted"
        return self._update_or_skip(existing, values)

    def upsert_mistake(
        self,
        pack_id: UUID,
        record: dict[str, object],
    ) -> UpsertOutcome:
        code = str(record["code"])
        existing = self._session.get(DomainMistakeDefinitionModel, code)
        values: dict[str, object] = {
            "pack_id": pack_id,
            "category": str(record["category"]),
            "title": str(record["title"]),
            "severity": str(record["severity"]),
            "editable_or_reshoot": str(record["editable_or_reshoot"]),
            "enabled_for_mvp": code in _MVP_MISTAKE_CODES,
            "raw_payload": record,
        }
        if existing is None:
            self._session.add(DomainMistakeDefinitionModel(code=code, **values))
            return "inserted"
        return self._update_or_skip(existing, values)

    def upsert_uncertainty(
        self,
        pack_id: UUID,
        record: dict[str, object],
    ) -> UpsertOutcome:
        code = str(record["code"])
        existing = self._session.get(DomainUncertaintyModel, code)
        values: dict[str, object] = {
            "pack_id": pack_id,
            "topic": str(record["topic"]),
            "classification": str(record["classification"]),
            "raw_payload": record,
        }
        if existing is None:
            self._session.add(DomainUncertaintyModel(code=code, **values))
            return "inserted"
        return self._update_or_skip(existing, values)

    def list_active_rules(self) -> list[DomainRule]:
        models = self._session.execute(
            select(DomainPolicyRuleModel)
            .join(
                DomainPolicyPackModel,
                DomainPolicyPackModel.id == DomainPolicyRuleModel.pack_id,
            )
            .where(
                DomainPolicyPackModel.status == "active",
                DomainPolicyRuleModel.enabled_for_mvp.is_(True),
            )
            .order_by(DomainPolicyRuleModel.code.asc())
        ).scalars()
        return [_rule_from_model(model) for model in models]

    def get_status(self) -> PolicyPackStatus:
        pack = self._active_pack()
        return PolicyPackStatus(
            pack_name=pack.pack_name,
            version=pack.version,
            content_hash=pack.content_hash,
            status=pack.status,
            counts=self._counts(pack.id),
            active_rule_codes=[rule.code for rule in self.list_active_rules()],
        )

    def _active_pack(self) -> DomainPolicyPackModel:
        pack = self._session.execute(
            select(DomainPolicyPackModel)
            .where(DomainPolicyPackModel.status == "active")
            .order_by(DomainPolicyPackModel.imported_at.desc())
            .limit(1)
        ).scalar_one_or_none()
        if pack is None:
            raise AppError(
                "DOMAIN_POLICY_PACK_NOT_FOUND",
                "No active domain intelligence policy pack is available.",
            )
        return pack

    def _counts(self, pack_id: UUID) -> PolicyPackCounts:
        def count(
            model: type[object],
            pack_column: InstrumentedAttribute[UUID] | None = None,
        ) -> int:
            statement = select(func.count()).select_from(model)
            if pack_column is not None:
                statement = statement.where(pack_column == pack_id)
            return int(self._session.scalar(statement) or 0)

        return PolicyPackCounts(
            policies=count(DomainPolicyRuleModel, DomainPolicyRuleModel.pack_id),
            patterns=count(DomainCreativePatternModel, DomainCreativePatternModel.pack_id),
            mistakes=count(DomainMistakeDefinitionModel, DomainMistakeDefinitionModel.pack_id),
            uncertainties=count(DomainUncertaintyModel, DomainUncertaintyModel.pack_id),
            sources=count(DomainPolicySourceModel),
        )

    def _update_or_skip(
        self,
        existing: object,
        values: Mapping[str, object],
    ) -> UpsertOutcome:
        if _values_match(existing, values):
            return "skipped"
        _update_values(existing, values)
        return "updated"

    def _sync_rule_sources(self, rule_code: str, source_ids: Sequence[str]) -> None:
        current = set(
            self._session.scalars(
                select(DomainPolicyRuleSourceModel.source_id).where(
                    DomainPolicyRuleSourceModel.rule_code == rule_code
                )
            )
        )
        expected = set(source_ids)
        if current == expected:
            return
        self._session.execute(
            delete(DomainPolicyRuleSourceModel).where(
                DomainPolicyRuleSourceModel.rule_code == rule_code
            )
        )
        self._session.add_all(
            [
                DomainPolicyRuleSourceModel(rule_code=rule_code, source_id=source_id)
                for source_id in sorted(expected)
            ]
        )


class DomainIntelligenceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_active_rules(self) -> list[DomainRule]:
        models = (
            await self._session.execute(
                select(DomainPolicyRuleModel)
                .join(
                    DomainPolicyPackModel,
                    DomainPolicyPackModel.id == DomainPolicyRuleModel.pack_id,
                )
                .where(
                    DomainPolicyPackModel.status == "active",
                    DomainPolicyRuleModel.enabled_for_mvp.is_(True),
                )
                .order_by(DomainPolicyRuleModel.code.asc())
            )
        ).scalars()
        return [_rule_from_model(model) for model in models]

    async def get_status(self) -> PolicyPackStatus:
        pack = (
            await self._session.execute(
                select(DomainPolicyPackModel)
                .where(DomainPolicyPackModel.status == "active")
                .order_by(DomainPolicyPackModel.imported_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if pack is None:
            raise AppError(
                "DOMAIN_POLICY_PACK_NOT_FOUND",
                "No active domain intelligence policy pack is available.",
            )

        async def count(
            model: type[object],
            pack_column: InstrumentedAttribute[UUID] | None = None,
        ) -> int:
            statement = select(func.count()).select_from(model)
            if pack_column is not None:
                statement = statement.where(pack_column == pack.id)
            return int(await self._session.scalar(statement) or 0)

        rules = await self.list_active_rules()
        return PolicyPackStatus(
            pack_name=pack.pack_name,
            version=pack.version,
            content_hash=pack.content_hash,
            status=pack.status,
            counts=PolicyPackCounts(
                policies=await count(DomainPolicyRuleModel, DomainPolicyRuleModel.pack_id),
                patterns=await count(
                    DomainCreativePatternModel, DomainCreativePatternModel.pack_id
                ),
                mistakes=await count(
                    DomainMistakeDefinitionModel, DomainMistakeDefinitionModel.pack_id
                ),
                uncertainties=await count(DomainUncertaintyModel, DomainUncertaintyModel.pack_id),
                sources=await count(DomainPolicySourceModel),
            ),
            active_rule_codes=[rule.code for rule in rules],
        )


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


_MVP_MISTAKE_CODES = {
    "M-PROD-001",
    "M-PROD-002",
    "M-DEMO-001",
    "M-PROOF-001",
    "M-OFFER-001",
    "M-OFFER-002",
    "M-CLAIM-001",
    "M-DISC-001",
    "M-CTA-001",
    "M-CREATOR-001",
    "M-REV-001",
    "M-RIGHTS-001",
    "M-POD-001",
    "M-POD-002",
    "M-DROP-001",
    "M-SUP-001",
    "M-EVID-001",
}
