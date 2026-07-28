from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends

from viraldy.api.dependencies.auth import CurrentUserDep, DbSession, require_workspace_permission
from viraldy.api.dependencies.request import get_request_id
from viraldy.api.responses.envelope import Envelope, success
from viraldy.modules.jobs.service import JobService
from viraldy.platform.auth.policy import Permission

router = APIRouter(prefix="/workspaces/{workspace_id}/jobs", tags=["jobs"])


@router.get("", response_model=Envelope)
async def list_jobs(
    workspace_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.READ, current_user, db)
    jobs = await JobService(db).list_jobs(workspace_id)
    return success([job.model_dump(mode="json") for job in jobs], request_id)


@router.get("/{job_id}", response_model=Envelope)
async def get_job(
    workspace_id: UUID,
    job_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.READ, current_user, db)
    job = await JobService(db).get_job(workspace_id, job_id)
    return success(job.model_dump(mode="json"), request_id)
