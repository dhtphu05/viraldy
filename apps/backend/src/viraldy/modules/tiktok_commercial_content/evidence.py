from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import delete
from sqlalchemy.orm import Session

from viraldy.modules.media_analysis.models import EvidenceItemModel
from viraldy.modules.tiktok_commercial_content.mapper import PROVIDER


def persist_platform_metadata_evidence(
    session: Session,
    *,
    workspace_id: UUID,
    asset_version_id: UUID,
    source_entity_id: str,
    metadata: dict[str, Any],
    observed_at: datetime,
) -> int:
    session.execute(
        delete(EvidenceItemModel).where(
            EvidenceItemModel.workspace_id == workspace_id,
            EvidenceItemModel.asset_version_id == asset_version_id,
            EvidenceItemModel.source_provider == PROVIDER,
            EvidenceItemModel.source_entity_id == source_entity_id,
        )
    )
    rows: list[EvidenceItemModel] = []
    for field_path, raw_value in _flatten(metadata):
        identity = hashlib.sha256(
            json.dumps(
                [str(asset_version_id), source_entity_id, field_path, raw_value],
                sort_keys=True,
                default=str,
            ).encode()
        ).hexdigest()
        rows.append(
            EvidenceItemModel(
                id=uuid4(),
                workspace_id=workspace_id,
                asset_version_id=asset_version_id,
                analysis_run_type="tiktok_commercial_content",
                evidence_type="platform_metadata",
                evidence_schema_version="evidence_v1",
                identity_hash=identity,
                value_json={
                    "schema_version": "evidence_v1",
                    "evidence_type": "platform_metadata",
                    "field_path": field_path,
                    "raw_value": raw_value,
                    "normalized_value": raw_value,
                },
                confidence=1,
                source="platform_metadata",
                source_type="PLATFORM_METADATA",
                provider=PROVIDER,
                source_provider=PROVIDER,
                source_entity_id=source_entity_id,
                field_path=field_path,
                raw_value_json=raw_value,
                normalized_value_json=raw_value,
                observed_at=observed_at,
            )
        )
    session.add_all(rows)
    session.flush()
    return len(rows)


def _flatten(value: object, prefix: str = "") -> list[tuple[str, object]]:
    if isinstance(value, dict):
        rows: list[tuple[str, object]] = []
        for key, child in value.items():
            if key.startswith("__"):
                continue
            path = f"{prefix}.{key}" if prefix else key
            rows.extend(_flatten(child, path))
        return rows
    if isinstance(value, list):
        return [(prefix, value)] if value else []
    return [(prefix, value)]
