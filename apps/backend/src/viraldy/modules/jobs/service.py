from __future__ import annotations

from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from viraldy.modules.jobs.dispatcher import JobDispatcher
from viraldy.modules.jobs.repository import JobRepository
from viraldy.modules.jobs.schemas import JobResponse
from viraldy.shared.errors.base import NotFoundError


class JobService:
    def __init__(self, session: AsyncSession, dispatcher: JobDispatcher | None = None) -> None:
        self._session = session
        self._repository = JobRepository(session)
        self._dispatcher = dispatcher

    async def request_process_asset(
        self,
        workspace_id: UUID,
        asset_id: UUID,
        asset_version_id: UUID,
        idempotency_key: str | None,
    ) -> JobResponse:
        job = await self._repository.get_existing_idempotent(
            workspace_id, "process_asset", idempotency_key
        )
        created = job is None
        if job is None:
            try:
                job = await self._repository.create_process_asset_job(
                    workspace_id=workspace_id,
                    asset_id=asset_id,
                    asset_version_id=asset_version_id,
                    idempotency_key=idempotency_key,
                )
            except IntegrityError:
                await self._session.rollback()
                job = await self._repository.get_existing_idempotent(
                    workspace_id, "process_asset", idempotency_key
                )
                created = False
                if job is None:
                    raise

        await self._session.commit()
        if created and self._dispatcher is not None:
            await self._dispatch_created_job(job, "process_asset")

        return JobResponse.model_validate(job)

    async def request_mvp_job(
        self,
        workspace_id: UUID,
        subject_type: str,
        subject_id: UUID,
        job_type: str,
        input_json: dict[str, object],
        idempotency_key: str | None,
    ) -> JobResponse:
        job = await self._repository.get_existing_idempotent(
            workspace_id, job_type, idempotency_key
        )
        created = job is None
        if job is None:
            try:
                job = await self._repository.create_mvp_job(
                    workspace_id=workspace_id,
                    subject_type=subject_type,
                    subject_id=subject_id,
                    job_type=job_type,
                    input_json=input_json,
                    idempotency_key=idempotency_key,
                )
            except IntegrityError:
                await self._session.rollback()
                job = await self._repository.get_existing_idempotent(
                    workspace_id, job_type, idempotency_key
                )
                created = False
                if job is None:
                    raise
        await self._session.commit()
        if created and self._dispatcher is not None:
            await self._dispatch_created_job(job, "mvp")
        return JobResponse.model_validate(job)

    async def list_jobs(self, workspace_id: UUID) -> list[JobResponse]:
        jobs = await self._repository.list_jobs(workspace_id)
        return [JobResponse.model_validate(job) for job in jobs]

    async def get_job(self, workspace_id: UUID, job_id: UUID) -> JobResponse:
        job = await self._repository.get_job(workspace_id, job_id)
        if job is None:
            raise NotFoundError("JOB_NOT_FOUND", "Processing job was not found.")
        return JobResponse.model_validate(job)

    async def _dispatch_created_job(self, job, dispatch_kind: str) -> None:
        await self._repository.record_dispatch_requested(job)
        await self._session.commit()
        try:
            if dispatch_kind == "process_asset":
                result = self._dispatcher.dispatch_process_asset(job.id)
            else:
                result = self._dispatcher.dispatch_mvp_job(job.id)
        except Exception as exc:
            await self._repository.record_dispatch_failed(job, str(exc))
            await self._session.commit()
            raise
        await self._repository.record_dispatch_succeeded(job, result.task_id)
        await self._session.commit()
