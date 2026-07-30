from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class JobResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    subject_type: str
    subject_id: UUID
    job_type: str
    queue_name: str
    status: str
    progress: int
    stage: str | None
    attempt_count: int
    max_attempts: int
    idempotency_key: str | None
    input_json: dict[str, object]
    output_json: dict[str, object] | None
    error_code: str | None
    error_message: str | None
    task_id: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    progress_percent: int = Field(validation_alias="progress")
    current_stage: str | None = Field(validation_alias="stage")
    safe_error_code: str | None = Field(validation_alias="error_code")
    safe_error_message: str | None = Field(validation_alias="error_message")

    model_config = {"from_attributes": True}
