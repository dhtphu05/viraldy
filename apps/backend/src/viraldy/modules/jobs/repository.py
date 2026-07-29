from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from viraldy.modules.jobs.models import ProcessingJobEventModel, ProcessingJobModel
from viraldy.modules.jobs.registry import JobType, get_job_definition
from viraldy.platform.clock.utc import utc_now


class JobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_process_asset_job(
        self,
        workspace_id: UUID,
        asset_id: UUID,
        asset_version_id: UUID,
        idempotency_key: str | None,
    ) -> ProcessingJobModel:
        definition = get_job_definition(JobType.PROCESS_ASSET.value)
        job = ProcessingJobModel(
            workspace_id=workspace_id,
            subject_type="asset",
            subject_id=asset_id,
            job_type=definition.job_type.value,
            queue_name=definition.queue,
            status="queued",
            progress=0,
            stage="queued",
            max_attempts=definition.max_attempts,
            idempotency_key=idempotency_key,
            input_json={
                "asset_id": str(asset_id),
                "asset_version_id": str(asset_version_id),
            },
        )
        self._session.add(job)
        await self._session.flush()
        self.add_event(job, "job_created", "Job created.")
        return job

    async def create_mvp_job(
        self,
        workspace_id: UUID,
        subject_type: str,
        subject_id: UUID,
        job_type: str,
        input_json: dict[str, object],
        idempotency_key: str | None,
    ) -> ProcessingJobModel:
        definition = get_job_definition(job_type)
        job = ProcessingJobModel(
            workspace_id=workspace_id,
            subject_type=subject_type,
            subject_id=subject_id,
            job_type=definition.job_type.value,
            queue_name=definition.queue,
            status="queued",
            progress=0,
            stage="queued",
            max_attempts=definition.max_attempts,
            idempotency_key=idempotency_key,
            input_json=input_json,
        )
        self._session.add(job)
        await self._session.flush()
        self.add_event(job, "job_created", "Job created.")
        return job

    def add_event(
        self,
        job: ProcessingJobModel,
        event_type: str,
        message: str | None = None,
        details: dict[str, object] | None = None,
    ) -> ProcessingJobEventModel:
        event = ProcessingJobEventModel(
            workspace_id=job.workspace_id,
            processing_job_id=job.id,
            event_type=event_type,
            status=job.status,
            stage=job.stage,
            progress=job.progress,
            message=message,
            details_json=details or {},
        )
        self._session.add(event)
        return event

    async def record_dispatch_requested(self, job: ProcessingJobModel) -> None:
        self.add_event(job, "dispatch_requested", "Dispatch requested.")

    async def record_dispatch_succeeded(self, job: ProcessingJobModel, task_id: str | None) -> None:
        job.task_id = task_id
        self.add_event(
            job,
            "dispatch_succeeded",
            "Dispatch succeeded.",
            {"task_id": task_id} if task_id else {},
        )

    async def record_dispatch_failed(self, job: ProcessingJobModel, message: str) -> None:
        self.add_event(job, "dispatch_failed", "Dispatch failed.", {"error": message})

    async def get_existing_idempotent(
        self, workspace_id: UUID, job_type: str, idempotency_key: str | None
    ) -> ProcessingJobModel | None:
        if not idempotency_key:
            return None
        result = await self._session.execute(
            select(ProcessingJobModel).where(
                ProcessingJobModel.workspace_id == workspace_id,
                ProcessingJobModel.job_type == job_type,
                ProcessingJobModel.idempotency_key == idempotency_key,
            )
        )
        return result.scalar_one_or_none()

    async def list_jobs(self, workspace_id: UUID) -> list[ProcessingJobModel]:
        result = await self._session.execute(
            select(ProcessingJobModel)
            .where(ProcessingJobModel.workspace_id == workspace_id)
            .order_by(ProcessingJobModel.created_at.desc())
        )
        return list(result.scalars())

    async def get_job(self, workspace_id: UUID, job_id: UUID) -> ProcessingJobModel | None:
        result = await self._session.execute(
            select(ProcessingJobModel).where(
                ProcessingJobModel.workspace_id == workspace_id,
                ProcessingJobModel.id == job_id,
            )
        )
        return result.scalar_one_or_none()


class WorkerJobRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def load_job(self, job_id: UUID) -> ProcessingJobModel | None:
        return self._session.get(ProcessingJobModel, job_id)

    def add_event(
        self,
        job: ProcessingJobModel,
        event_type: str,
        message: str | None = None,
        details: dict[str, object] | None = None,
    ) -> ProcessingJobEventModel:
        event = ProcessingJobEventModel(
            workspace_id=job.workspace_id,
            processing_job_id=job.id,
            event_type=event_type,
            status=job.status,
            stage=job.stage,
            progress=job.progress,
            message=message,
            details_json=details or {},
        )
        self._session.add(event)
        return event

    def claim_job(self, job_id: UUID) -> ProcessingJobModel | None:
        job = (
            self._session.execute(
                select(ProcessingJobModel).where(ProcessingJobModel.id == job_id).with_for_update()
            )
            .scalars()
            .one_or_none()
        )
        if job is None:
            return None
        if job.status in {"completed", "failed", "cancelled"}:
            self.add_event(job, "job_claimed", "Terminal job delivery ignored.")
            return None
        if job.status not in {"queued", "retrying"}:
            self.add_event(job, "job_claimed", "Non-claimable job delivery ignored.")
            return None
        self.mark_running(job)
        self.add_event(job, "job_claimed", "Job claimed by worker.")
        return job

    def mark_running(self, job: ProcessingJobModel) -> None:
        job.status = "running"
        job.stage = "loading_job"
        job.progress = 10
        job.attempt_count += 1
        job.started_at = utc_now()

    def update_progress(self, job: ProcessingJobModel, progress: int, stage: str) -> None:
        if progress < job.progress:
            progress = job.progress
        job.progress = progress
        job.stage = stage
        self.add_event(job, "stage_started", f"Stage started: {stage}.")

    def mark_completed(self, job: ProcessingJobModel, output_json: dict[str, object]) -> None:
        job.status = "completed"
        job.stage = "completed"
        job.progress = 100
        job.output_json = output_json
        job.completed_at = utc_now()
        self.add_event(job, "job_completed", "Job completed.")

    def mark_failed(self, job: ProcessingJobModel, code: str, message: str) -> None:
        job.status = "failed"
        job.stage = "failed"
        job.error_code = code
        job.error_message = message
        job.completed_at = utc_now()
        self.add_event(job, "job_failed", message, {"code": code})

    def mark_retrying(self, job: ProcessingJobModel, code: str, message: str) -> None:
        job.status = "retrying"
        job.stage = "retrying"
        job.error_code = code
        job.error_message = message
        self.add_event(job, "retry_scheduled", message, {"code": code})
