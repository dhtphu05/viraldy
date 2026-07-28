from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


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

    model_config = {"from_attributes": True}
