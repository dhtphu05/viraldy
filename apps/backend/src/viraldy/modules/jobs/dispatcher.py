from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from viraldy.worker.tasks.process_asset import process_asset_placeholder


@dataclass(frozen=True, slots=True)
class DispatchResult:
    task_id: str | None
    dispatched: bool


class JobDispatcher(Protocol):
    def dispatch_process_asset(self, job_id: UUID) -> DispatchResult:
        raise NotImplementedError


class CeleryJobDispatcher:
    def dispatch_process_asset(self, job_id: UUID) -> DispatchResult:
        result = process_asset_placeholder.delay(str(job_id))
        return DispatchResult(task_id=str(result.id), dispatched=True)
