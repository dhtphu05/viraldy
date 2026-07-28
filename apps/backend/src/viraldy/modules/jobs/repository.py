from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from viraldy.modules.jobs.models import ProcessingJobModel
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
        job = ProcessingJobModel(
            workspace_id=workspace_id,
            subject_type="asset",
            subject_id=asset_id,
            job_type="process_asset",
            queue_name="default",
            status="queued",
            progress=0,
            stage="queued",
            max_attempts=3,
            idempotency_key=idempotency_key,
            input_json={
                "asset_id": str(asset_id),
                "asset_version_id": str(asset_version_id),
            },
        )
        self._session.add(job)
        await self._session.flush()
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
        job = ProcessingJobModel(
            workspace_id=workspace_id,
            subject_type=subject_type,
            subject_id=subject_id,
            job_type=job_type,
            queue_name="default",
            status="queued",
            progress=0,
            stage="queued",
            max_attempts=3,
            idempotency_key=idempotency_key,
            input_json=input_json,
        )
        self._session.add(job)
        await self._session.flush()
        return job

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

    def mark_running(self, job: ProcessingJobModel) -> None:
        job.status = "running"
        job.stage = "loading_job"
        job.progress = 10
        job.attempt_count += 1
        job.started_at = utc_now()

    def update_progress(self, job: ProcessingJobModel, progress: int, stage: str) -> None:
        job.progress = progress
        job.stage = stage

    def mark_completed(self, job: ProcessingJobModel, output_json: dict[str, object]) -> None:
        job.status = "completed"
        job.stage = "completed"
        job.progress = 100
        job.output_json = output_json
        job.completed_at = utc_now()

    def mark_failed(self, job: ProcessingJobModel, code: str, message: str) -> None:
        job.status = "failed"
        job.stage = "failed"
        job.error_code = code
        job.error_message = message
        job.completed_at = utc_now()
