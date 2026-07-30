from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from viraldy.modules.jobs.public import JobResponse


class CreateGenerationRequest(BaseModel):
    viral_kit_id: UUID
    viral_kit_version: int | None = Field(default=None, ge=1)
    concept_id: str = Field(min_length=1, max_length=120)
    source_asset_ids: list[UUID] = Field(min_length=1)
    rights_confirmed: bool = False

    model_config = ConfigDict(extra="forbid")


class GenerationArtifactResponse(BaseModel):
    id: UUID
    generation_run_id: UUID
    artifact_kind: str
    scene_id: str | None
    storage_key: str | None
    media_type: str
    width: int | None
    height: int | None
    duration_ms: int | None
    payload_json: dict[str, object]
    provider: str
    model: str
    provider_request_id: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GenerationRunResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    viral_kit_id: UUID
    viral_kit_version_id: UUID
    viral_kit_version: int
    concept_id: str
    operation: str
    status: str
    prompt_version: str
    schema_version: str
    source_asset_ids_json: list[str]
    input_hash: str
    idempotency_key: str | None
    processing_job_id: UUID | None
    model_run_id: UUID | None
    output_json: dict[str, object] | None
    safe_error_code: str | None
    safe_error_message: str | None
    created_by_user_id: UUID
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    artifacts: list[GenerationArtifactResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class CreateGenerationResponse(BaseModel):
    generation_run: GenerationRunResponse
    job: JobResponse
