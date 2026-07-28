from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from viraldy.modules.jobs.dispatcher import CeleryJobDispatcher
from viraldy.modules.jobs.repository import JobRepository
from viraldy.modules.jobs.schemas import JobResponse
from viraldy.modules.jobs.service import JobService

__all__ = [
    "JobResponse",
    "get_existing_idempotent_job",
    "request_mvp_job",
    "request_process_asset",
]


async def get_existing_idempotent_job(
    session: AsyncSession,
    workspace_id: UUID,
    job_type: str,
    idempotency_key: str | None,
) -> JobResponse | None:
    job = await JobRepository(session).get_existing_idempotent(
        workspace_id, job_type, idempotency_key
    )
    if job is None:
        return None
    return JobResponse.model_validate(job)


async def request_process_asset(
    session: AsyncSession,
    workspace_id: UUID,
    asset_id: UUID,
    asset_version_id: UUID,
    idempotency_key: str | None,
) -> JobResponse:
    return await JobService(session, CeleryJobDispatcher()).request_process_asset(
        workspace_id=workspace_id,
        asset_id=asset_id,
        asset_version_id=asset_version_id,
        idempotency_key=idempotency_key,
    )


async def request_mvp_job(
    session: AsyncSession,
    workspace_id: UUID,
    subject_type: str,
    subject_id: UUID,
    job_type: str,
    input_json: dict[str, object],
    idempotency_key: str | None,
) -> JobResponse:
    return await JobService(session, CeleryJobDispatcher()).request_mvp_job(
        workspace_id=workspace_id,
        subject_type=subject_type,
        subject_id=subject_id,
        job_type=job_type,
        input_json=input_json,
        idempotency_key=idempotency_key,
    )
