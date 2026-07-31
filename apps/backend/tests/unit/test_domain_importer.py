from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from viraldy.modules.domain_intelligence.importer import (
    ArtifactValidationError,
    PolicyPackImporter,
    validate_policy_pack,
)
from viraldy.modules.domain_intelligence.models import DOMAIN_INTELLIGENCE_TABLES
from viraldy.modules.domain_intelligence.public import ACTIVE_MVP_RULE_CODES

ROOT = Path(__file__).resolve().parents[2]
RESOURCE_DIR = ROOT / "resources" / "domain_intelligence" / "v1"
PACK_PATH = RESOURCE_DIR / "DomainExpertPolicyPackV1.json"
SCHEMA_PATH = RESOURCE_DIR / "DomainExpertPolicyPackV1.schema.json"
SOURCES_PATH = RESOURCE_DIR / "source_registry_v1.csv"


def test_policy_pack_validates_schema_counts_sources_and_hash() -> None:
    validated = validate_policy_pack(PACK_PATH, SCHEMA_PATH, SOURCES_PATH)

    assert validated.counts.model_dump() == {
        "policies": 58,
        "patterns": 23,
        "mistakes": 20,
        "uncertainties": 15,
        "sources": 66,
    }
    assert validated.content_hash == hashlib.sha256(PACK_PATH.read_bytes()).hexdigest()
    assert validated.pack_name == "Viraldy Domain, Creative and Workflow Research Pack"
    assert validated.version == "1.0.0-research-2026-07-31"


def test_policy_pack_rejects_malformed_json_against_supplied_schema(tmp_path: Path) -> None:
    payload = json.loads(PACK_PATH.read_text(encoding="utf-8"))
    payload.pop("domain_expert_policy_catalog")
    malformed = tmp_path / "malformed.json"
    malformed.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ArtifactValidationError, match="JSON Schema"):
        validate_policy_pack(malformed, SCHEMA_PATH, SOURCES_PATH)


def test_policy_pack_rejects_material_csv_source_mismatch(tmp_path: Path) -> None:
    with SOURCES_PATH.open(encoding="utf-8-sig", newline="") as source_file:
        rows = list(csv.DictReader(source_file))
        fieldnames = list(rows[0])
    rows[0] = {**rows[0], "publisher": "Wrong publisher"}
    mismatched = tmp_path / "sources.csv"
    with mismatched.open("w", encoding="utf-8", newline="") as target_file:
        writer = csv.DictWriter(target_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    with pytest.raises(ArtifactValidationError, match="source registry mismatch"):
        validate_policy_pack(PACK_PATH, SCHEMA_PATH, mismatched)


def test_importer_is_idempotent_and_activates_exact_mvp_rules() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    for table in DOMAIN_INTELLIGENCE_TABLES:
        table.create(engine)

    with Session(engine) as session:
        importer = PolicyPackImporter(session)
        first = importer.import_pack(
            pack_path=PACK_PATH,
            schema_path=SCHEMA_PATH,
            sources_path=SOURCES_PATH,
            activate_mvp=True,
        )
        session.commit()
        second = importer.import_pack(
            pack_path=PACK_PATH,
            schema_path=SCHEMA_PATH,
            sources_path=SOURCES_PATH,
            activate_mvp=True,
        )
        session.commit()
        status = importer.repository.get_status()

    assert first.inserted == 183
    assert second.inserted == 0
    assert second.updated == 0
    assert second.skipped == 183
    assert status.counts.model_dump() == {
        "policies": 58,
        "patterns": 23,
        "mistakes": 20,
        "uncertainties": 15,
        "sources": 66,
    }
    assert status.active_rule_codes == sorted(ACTIVE_MVP_RULE_CODES)


def test_validate_only_does_not_require_database() -> None:
    result = PolicyPackImporter(None).validate(
        pack_path=PACK_PATH,
        schema_path=SCHEMA_PATH,
        sources_path=SOURCES_PATH,
    )

    assert result.counts.policies == 58


def test_import_without_database_fails_clearly() -> None:
    with pytest.raises(RuntimeError, match="database session is required"):
        PolicyPackImporter(None).import_pack(
            pack_path=PACK_PATH,
            schema_path=SCHEMA_PATH,
            sources_path=SOURCES_PATH,
            activate_mvp=True,
        )
