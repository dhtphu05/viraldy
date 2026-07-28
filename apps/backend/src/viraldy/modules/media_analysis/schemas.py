from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class MediaArtifactResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    asset_version_id: UUID
    artifact_type: str
    storage_key: str | None
    payload_json: dict[str, object] | None
    provider: str
    model_version: str | None
    analysis_mode: str
    created_at: datetime

    model_config = {"from_attributes": True}


class EvidenceItemResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    asset_version_id: UUID
    analysis_run_type: str
    analysis_run_id: UUID | None
    evidence_type: str
    start_ms: int | None
    end_ms: int | None
    frame_storage_key: str | None
    value_json: dict[str, object]
    confidence: float | None
    source: str
    provider: str | None
    model_version: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
