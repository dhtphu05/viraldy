from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

AiReadinessState = Literal[
    "configured",
    "not_configured",
    "configuration_invalid",
    "not_yet_qualified",
    "qualified",
]


class AiCapabilities(BaseModel):
    text_chat: bool = False
    vision_chat: bool = False
    audio_transcription: bool = False
    json_schema: bool = False
    image_url: bool = False
    base64_image: bool = False


class AiReadiness(BaseModel):
    mode: str
    provider: str
    state: AiReadinessState
    configured: bool
    capabilities: AiCapabilities
    missing: list[str] = Field(default_factory=list)


class ProviderResponse(BaseModel):
    payload: dict[str, object]
    http_status: int
    provider_request_id: str | None
    latency_ms: int


AiModelRunStatus = Literal["pending", "running", "completed", "failed"]


class AiModelRunResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    processing_job_id: UUID | None
    subject_type: str
    subject_id: UUID
    capability: str
    operation: str
    analysis_mode: str
    provider: str
    endpoint_family: str | None
    model: str
    prompt_name: str | None
    prompt_version: str | None
    response_schema_version: str
    schema_version: str
    status: AiModelRunStatus
    attempt: int
    attempt_count: int
    repair_attempt_count: int
    request_id: str
    request_hash: str
    input_hash: str
    input_summary_json: dict[str, object]
    output_summary_json: dict[str, object]
    usage_json: dict[str, object]
    estimated_cost: Decimal | None
    latency_ms: int | None
    http_status: int | None
    provider_request_id: str | None
    error_code: str | None
    safe_error_message: str | None
    started_at: datetime
    completed_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
