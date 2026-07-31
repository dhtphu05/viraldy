from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from jsonschema import Draft202012Validator, FormatChecker  # type: ignore[import-untyped]
from sqlalchemy.orm import Session

from viraldy.modules.domain_intelligence.constants import (
    ACTIVE_MVP_RULE_CODES,
    EXPECTED_PACK_COUNTS,
)
from viraldy.modules.domain_intelligence.repository import SyncDomainIntelligenceRepository
from viraldy.modules.domain_intelligence.schemas import (
    DomainRule,
    ImportSummary,
    PolicyPackCounts,
)


class ArtifactValidationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ValidatedPolicyPack:
    pack_name: str
    version: str
    content_hash: str
    counts: PolicyPackCounts
    payload: dict[str, object]
    sources: list[dict[str, object]]
    policies: list[dict[str, object]]
    patterns: list[dict[str, object]]
    mistakes: list[dict[str, object]]
    uncertainties: list[dict[str, object]]
    active_rules: list[DomainRule]


def validate_policy_pack(
    pack_path: Path | str,
    schema_path: Path | str,
    sources_path: Path | str,
) -> ValidatedPolicyPack:
    pack_file = _required_file(pack_path)
    schema_file = _required_file(schema_path)
    sources_file = _required_file(sources_path)
    payload = _load_json_object(pack_file, "policy pack")
    schema = _load_json_object(schema_file, "policy pack schema")
    errors = sorted(
        Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(payload),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        first = errors[0]
        location = ".".join(str(part) for part in first.absolute_path) or "root"
        raise ArtifactValidationError(
            f"policy pack JSON Schema validation failed at {location}: {first.message}"
        )

    collections = _collections(payload)
    counts = PolicyPackCounts(
        policies=len(collections["policies"]),
        patterns=len(collections["patterns"]),
        mistakes=len(collections["mistakes"]),
        uncertainties=len(collections["uncertainties"]),
        sources=len(collections["sources"]),
    )
    if counts.model_dump() != EXPECTED_PACK_COUNTS:
        raise ArtifactValidationError(
            f"policy pack record counts are invalid: expected {EXPECTED_PACK_COUNTS}, "
            f"received {counts.model_dump()}"
        )
    _validate_unique_codes(collections)
    csv_sources = _load_csv_sources(sources_file)
    _validate_source_registry(collections["sources"], csv_sources)
    _validate_source_references(collections)

    meta = cast(dict[str, object], payload["meta"])
    pack_name = _required_text(meta, "pack_name")
    version = _required_text(meta, "version")
    active_rules = [
        _domain_rule(record, enabled_for_mvp=True)
        for record in collections["policies"]
        if str(record["code"]) in ACTIVE_MVP_RULE_CODES
    ]
    active_codes = {rule.code for rule in active_rules}
    if active_codes != ACTIVE_MVP_RULE_CODES:
        missing = sorted(ACTIVE_MVP_RULE_CODES - active_codes)
        raise ArtifactValidationError(f"policy pack is missing active MVP rules: {missing}")
    return ValidatedPolicyPack(
        pack_name=pack_name,
        version=version,
        content_hash=hashlib.sha256(pack_file.read_bytes()).hexdigest(),
        counts=counts,
        payload=payload,
        sources=collections["sources"],
        policies=collections["policies"],
        patterns=collections["patterns"],
        mistakes=collections["mistakes"],
        uncertainties=collections["uncertainties"],
        active_rules=sorted(active_rules, key=lambda rule: rule.code),
    )


class PolicyPackImporter:
    def __init__(self, session: Session | None) -> None:
        self._session = session
        self.repository = SyncDomainIntelligenceRepository(session) if session else None

    def validate(
        self,
        *,
        pack_path: Path | str,
        schema_path: Path | str,
        sources_path: Path | str,
    ) -> ValidatedPolicyPack:
        return validate_policy_pack(pack_path, schema_path, sources_path)

    def import_pack(
        self,
        *,
        pack_path: Path | str,
        schema_path: Path | str,
        sources_path: Path | str,
        activate_mvp: bool = False,
        dry_run: bool = False,
    ) -> ImportSummary:
        validated = self.validate(
            pack_path=pack_path,
            schema_path=schema_path,
            sources_path=sources_path,
        )
        if dry_run:
            return ImportSummary(
                pack_name=validated.pack_name,
                version=validated.version,
                content_hash=validated.content_hash,
                counts=validated.counts,
                skipped=_total_records(validated),
                dry_run=True,
            )
        if self.repository is None or self._session is None:
            raise RuntimeError("a database session is required to import the domain policy pack")

        outcomes: list[str] = []
        meta = cast(dict[str, object], validated.payload["meta"])
        pack, outcome = self.repository.upsert_pack(
            pack_name=validated.pack_name,
            version=validated.version,
            status="active" if activate_mvp else "imported",
            content_hash=validated.content_hash,
            meta_json=meta,
            raw_payload=validated.payload,
        )
        outcomes.append(outcome)
        outcomes.extend(self.repository.upsert_source(record) for record in validated.sources)
        outcomes.extend(
            self.repository.upsert_rule(
                pack.id,
                record,
                enabled_for_mvp=(activate_mvp and str(record["code"]) in ACTIVE_MVP_RULE_CODES),
            )
            for record in validated.policies
        )
        outcomes.extend(
            self.repository.upsert_pattern(pack.id, record) for record in validated.patterns
        )
        outcomes.extend(
            self.repository.upsert_mistake(pack.id, record) for record in validated.mistakes
        )
        outcomes.extend(
            self.repository.upsert_uncertainty(pack.id, record)
            for record in validated.uncertainties
        )
        self._session.flush()
        return ImportSummary(
            pack_name=validated.pack_name,
            version=validated.version,
            content_hash=validated.content_hash,
            counts=validated.counts,
            inserted=outcomes.count("inserted"),
            updated=outcomes.count("updated"),
            skipped=outcomes.count("skipped"),
        )


def _required_file(path: Path | str) -> Path:
    file_path = Path(path)
    if not file_path.is_file():
        raise ArtifactValidationError(f"required artifact is missing: {file_path}")
    return file_path


def _load_json_object(path: Path, label: str) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ArtifactValidationError(f"{label} is malformed: {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ArtifactValidationError(f"{label} must contain a JSON object: {path}")
    return cast(dict[str, object], payload)


def _collections(payload: dict[str, object]) -> dict[str, list[dict[str, object]]]:
    keys = {
        "policies": "domain_expert_policy_catalog",
        "patterns": "creative_pattern_catalog",
        "mistakes": "real_world_mistake_taxonomy",
        "uncertainties": "disagreements_and_uncertainties",
        "sources": "source_registry",
    }
    collections: dict[str, list[dict[str, object]]] = {}
    for name, key in keys.items():
        value = payload.get(key)
        if not isinstance(value, list) or not all(isinstance(record, dict) for record in value):
            raise ArtifactValidationError(f"policy pack collection {key!r} is malformed")
        collections[name] = cast(list[dict[str, object]], value)
    return collections


def _validate_unique_codes(collections: dict[str, list[dict[str, object]]]) -> None:
    for name in ("policies", "patterns", "mistakes", "uncertainties"):
        codes = [str(record.get("code", "")) for record in collections[name]]
        if any(not code for code in codes) or len(set(codes)) != len(codes):
            raise ArtifactValidationError(f"policy pack {name} contain missing or duplicate codes")
    source_ids = [str(record.get("id", "")) for record in collections["sources"]]
    if any(not source_id for source_id in source_ids) or len(set(source_ids)) != len(source_ids):
        raise ArtifactValidationError("policy pack sources contain missing or duplicate IDs")


def _load_csv_sources(path: Path) -> list[dict[str, object]]:
    try:
        with path.open(encoding="utf-8-sig", newline="") as source_file:
            rows = list(csv.DictReader(source_file))
    except (OSError, csv.Error) as exc:
        raise ArtifactValidationError(f"source registry CSV is malformed: {path}: {exc}") from exc
    if not rows:
        raise ArtifactValidationError(f"source registry CSV is empty: {path}")
    return [cast(dict[str, object], row) for row in rows]


def _material_source(record: dict[str, object]) -> tuple[str, ...]:
    fields = ("id", "title", "publisher", "url", "type", "date", "strength", "notes")
    return tuple(str(record.get(field) or "").strip() for field in fields)


def _validate_source_registry(
    embedded: list[dict[str, object]],
    csv_sources: list[dict[str, object]],
) -> None:
    embedded_by_id = {str(record["id"]): _material_source(record) for record in embedded}
    csv_by_id = {str(record.get("id") or ""): _material_source(record) for record in csv_sources}
    if embedded_by_id != csv_by_id:
        embedded_ids = set(embedded_by_id)
        csv_ids = set(csv_by_id)
        details = {
            "missing_from_csv": sorted(embedded_ids - csv_ids),
            "extra_in_csv": sorted(csv_ids - embedded_ids),
            "changed": sorted(
                source_id
                for source_id in embedded_ids & csv_ids
                if embedded_by_id[source_id] != csv_by_id[source_id]
            ),
        }
        raise ArtifactValidationError(f"source registry mismatch: {details}")


def _validate_source_references(
    collections: dict[str, list[dict[str, object]]],
) -> None:
    source_ids = {str(record["id"]) for record in collections["sources"]}
    unknown: set[str] = set()
    for name in ("policies", "patterns", "mistakes", "uncertainties"):
        for record in collections[name]:
            for source in cast(list[dict[str, object]], record.get("sources") or []):
                source_id = str(source.get("source_id") or "")
                if source_id not in source_ids:
                    unknown.add(source_id)
    if unknown:
        raise ArtifactValidationError(
            f"policy pack records reference unknown source IDs: {sorted(unknown)}"
        )


def _required_text(payload: dict[str, object], field: str) -> str:
    value = str(payload.get(field) or "").strip()
    if not value:
        raise ArtifactValidationError(f"policy pack meta.{field} is required")
    return value


def _domain_rule(record: dict[str, object], *, enabled_for_mvp: bool) -> DomainRule:
    sources = cast(list[dict[str, object]], record.get("sources") or [])
    return DomainRule(
        code=str(record["code"]),
        domain=str(record["domain"]),
        title=str(record["title"]),
        rule_type=str(record["rule_type"]),
        severity=str(record["severity"]),
        enabled_for_mvp=enabled_for_mvp,
        applicability=list(cast(list[object], record.get("applicability") or [])),
        required_conditions=list(cast(list[object], record.get("required_conditions") or [])),
        implementation=dict(cast(dict[str, object], record.get("implementation") or {})),
        source_ids=[str(source["source_id"]) for source in sources],
        raw_payload=record,
    )


def _total_records(validated: ValidatedPolicyPack) -> int:
    return 1 + (
        validated.counts.policies
        + validated.counts.patterns
        + validated.counts.mistakes
        + validated.counts.uncertainties
        + validated.counts.sources
    )
