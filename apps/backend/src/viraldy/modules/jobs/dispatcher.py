from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class DispatchResult:
    task_id: str | None
    dispatched: bool


class JobDispatcher(Protocol):
    def dispatch_job(self, job_id: UUID, job_type: str) -> DispatchResult:
        raise NotImplementedError


class CeleryJobDispatcher:
    def dispatch_job(self, job_id: UUID, job_type: str) -> DispatchResult:
        from viraldy.modules.jobs.registry import get_job_definition
        from viraldy.worker.tasks.process_asset import run_processing_job

        definition = get_job_definition(job_type)
        result = run_processing_job.apply_async(
            args=[str(job_id)],
            queue=definition.queue,
            soft_time_limit=definition.soft_timeout_seconds,
            time_limit=definition.hard_timeout_seconds,
        )
        return DispatchResult(task_id=str(result.id), dispatched=True)
