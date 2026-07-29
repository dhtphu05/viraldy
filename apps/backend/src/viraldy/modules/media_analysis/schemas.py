from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from viraldy.modules.media_analysis.evidence_bundle import EvidenceBundleResponse


class MediaArtifactResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    asset_version_id: UUID
    artifact_type: str
    stage: str | None = None
    ordinal: int | None = None
    storage_key: str | None
    sha256: str | None = None
    payload_json: dict[str, object] | None
    provider: str
    model_version: str | None
    analysis_mode: str
    pipeline_version: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class EvidenceItemResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    asset_version_id: UUID
    analysis_run_type: str
    analysis_run_id: UUID | None
    evidence_type: str
    evidence_schema_version: str
    observation_id: str | None
    stage: str | None = None
    identity_hash: str | None = None
    start_ms: int | None
    end_ms: int | None
    frame_storage_key: str | None
    value_json: dict[str, object]
    confidence: float | None
    source: str
    provider: str | None
    model_version: str | None
    pipeline_version: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class MediaAnalysisResponse(BaseModel):
    asset_version_id: UUID
    artifacts: list[MediaArtifactResponse]
    evidence: list[EvidenceItemResponse]
    evidence_bundle: EvidenceBundleResponse
