from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class CreativeDnaVersionResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    reference_id: UUID | None
    asset_version_id: UUID
    version_number: int
    status: str
    schema_version: str
    dna_json: dict[str, object]
    confidence: str
    analysis_mode: str
    taxonomy_version: str
    model_version: str | None
    prompt_version: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
