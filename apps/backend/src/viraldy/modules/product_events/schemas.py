from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from viraldy.modules.product_events.contracts import ProductEventType


class ProductEventResponse(BaseModel):
    id: UUID
    workspace_id: UUID | None
    actor_user_id: UUID | None
    event_type: ProductEventType
    subject_type: str | None
    subject_id: UUID | None
    payload_json: dict[str, object]
    created_at: datetime

    model_config = {"from_attributes": True}


class ListProductEventsQuery(BaseModel):
    event_type: ProductEventType | None = None
    subject_type: str | None = Field(default=None, min_length=1, max_length=100)
    limit: int = Field(default=100, ge=1, le=500)
