from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class DomainEvent:
    event_id: UUID
    event_name: str
    event_version: int
    occurred_at: datetime
    aggregate_type: str
    aggregate_id: UUID
    workspace_id: UUID | None
    payload: dict[str, object]
