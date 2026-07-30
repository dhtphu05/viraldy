from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import case, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from viraldy.modules.jobs.models import ProcessingJobEventModel, ProcessingJobModel
from viraldy.modules.jobs.registry import (
    JobType,
    equivalent_job_types,
    get_job_definition,
    normalize_job_type,
)
from viraldy.platform.clock.utc import utc_now
from viraldy.shared.errors.base import AppError


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
        definition = get_job_definition(JobType.MEDIA_ANALYSIS.value)
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
        canonical_job_type = normalize_job_type(job_type)
        result = await self._session.execute(
            select(ProcessingJobModel)
            .where(
                ProcessingJobModel.workspace_id == workspace_id,
                ProcessingJobModel.job_type.in_(equivalent_job_types(job_type)),
                ProcessingJobModel.idempotency_key == idempotency_key,
            )
            .order_by(
                case(
                    (ProcessingJobModel.job_type == canonical_job_type, 0),
                    else_=1,
                ),
                ProcessingJobModel.created_at.desc(),
            )
            .limit(1)
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
        self._claimed_attempts: dict[UUID, int] = {}

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
        if job.status in {"succeeded", "completed", "failed", "cancelled"}:
            self.add_event(job, "job_claimed", "Terminal job delivery ignored.")
            return None
        if job.status not in {"queued", "retrying"}:
            self.add_event(job, "job_claimed", "Non-claimable job delivery ignored.")
            return None
        self.mark_running(job)
        self._claimed_attempts[job.id] = job.attempt_count
        self.add_event(job, "job_claimed", "Job claimed by worker.")
        return job

    def mark_running(self, job: ProcessingJobModel) -> None:
        job.status = "running"
        job.stage = "loading_job"
        job.progress = 10
        job.attempt_count += 1
        job.started_at = utc_now()

    def update_progress(self, job: ProcessingJobModel, progress: int, stage: str) -> None:
        job = self.assert_claim_active(job)
        if progress < job.progress:
            progress = job.progress
        job.progress = progress
        job.stage = stage
        self.add_event(job, "stage_started", f"Stage started: {stage}.")

    def mark_succeeded(self, job: ProcessingJobModel, output_json: dict[str, object]) -> None:
        job = self.assert_claim_active(job)
        job.status = "succeeded"
        job.stage = "succeeded"
        job.progress = 100
        job.output_json = output_json
        job.completed_at = utc_now()
        self.add_event(job, "job_succeeded", "Job succeeded.")

    def mark_failed(self, job: ProcessingJobModel, code: str, message: str) -> None:
        job = self._lock_claimed_attempt_if_present(job)
        job.status = "failed"
        job.stage = "failed"
        job.error_code = code
        job.error_message = message
        job.completed_at = utc_now()
        self.add_event(job, "job_failed", message, {"code": code})

    def mark_retrying(self, job: ProcessingJobModel, code: str, message: str) -> None:
        job = self._lock_claimed_attempt_if_present(job)
        job.status = "retrying"
        job.stage = "retrying"
        job.error_code = code
        job.error_message = message
        self.add_event(job, "retry_scheduled", message, {"code": code})

    def assert_claim_active(self, job: ProcessingJobModel) -> ProcessingJobModel:
        expected_attempt = self._claimed_attempts.get(job.id)
        if expected_attempt is None:
            raise AppError(
                "JOB_ATTEMPT_NOT_CLAIMED",
                "Processing job mutation requires an active worker claim.",
                status_code=409,
            )
        current = (
            self._session.execute(
                select(ProcessingJobModel)
                .where(ProcessingJobModel.id == job.id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            .scalars()
            .one_or_none()
        )
        if (
            current is None
            or current.status != "running"
            or current.attempt_count != expected_attempt
        ):
            raise AppError(
                "JOB_ATTEMPT_SUPERSEDED",
                "Processing job attempt was superseded by recovery or a newer worker.",
                status_code=409,
            )
        return current

    def _lock_claimed_attempt_if_present(
        self,
        job: ProcessingJobModel,
    ) -> ProcessingJobModel:
        if job.id not in self._claimed_attempts:
            return job
        return self.assert_claim_active(job)

    def recover_stale_jobs(
        self,
        now: datetime,
        minimum_stale_seconds: int,
        timeout_margin_seconds: int = 120,
    ) -> list[UUID]:
        stale_before = now - timedelta(seconds=minimum_stale_seconds)
        jobs = list(
            self._session.execute(
                select(ProcessingJobModel)
                .where(
                    ProcessingJobModel.status.in_(("running", "retrying")),
                    ProcessingJobModel.updated_at < stale_before,
                )
                .with_for_update(skip_locked=True)
            ).scalars()
        )
        retry_job_ids: list[UUID] = []
        for job in jobs:
            definition = get_job_definition(job.job_type)
            recovery_age_seconds = max(
                minimum_stale_seconds,
                definition.hard_timeout_seconds + timeout_margin_seconds,
            )
            if job.updated_at >= now - timedelta(seconds=recovery_age_seconds):
                continue
            if job.attempt_count >= job.max_attempts:
                self.mark_failed(
                    job,
                    "STALE_JOB_ATTEMPTS_EXHAUSTED",
                    "Processing job exceeded its recovery attempts.",
                )
                continue
            self.mark_retrying(
                job,
                "STALE_JOB_RECOVERED",
                "Stale processing job was recovered and scheduled for retry.",
            )
            retry_job_ids.append(job.id)
        return retry_job_ids
