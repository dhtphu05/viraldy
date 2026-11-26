"""Authorized Inspector and checked release endpoints under the workspace router."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends

from viraldy.api.dependencies.auth import CurrentUserDep, DbSession, require_workspace_permission
from viraldy.api.dependencies.request import get_request_id
from viraldy.api.responses.envelope import Envelope, success
from viraldy.modules.jobs.registry import JobType
from viraldy.platform.auth.policy import Permission
from viraldy.shared.errors.base import AppError

from .inspection_service import InspectionRequest, InspectionReviewRequest, InspectionService
from .intake_router import SettingsDep, authorize, service_for
from .project_lifecycle import (
    ApprovalRequest,
    DeletionRequest,
    ExportRequest,
    ProjectLifecycleService,
    RestoreRequest,
)

router = APIRouter()


@router.post("/projects/{project_id}/inspections", response_model=Envelope)
async def inspect_project(
    workspace_id: UUID,
    project_id: UUID,
    payload: InspectionRequest,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await authorize(workspace_id, current_user, db, settings)
    if settings.ai_mode.strip().lower() in {"fixture", "mock"}:
        raise AppError(
            "SMART_REMAKE_FIXTURE_MODE", "Remote inspection is disabled in fixture mode.", 409
        )
    repair = service_for(db, settings, workspace_id)
    inspector = InspectionService(
        repair.repository, repair.media, workspace_id, settings=settings
    )
    row, operation, _ = await inspector.queue(project_id, current_user.id, payload)
    job = None
    if operation.status == "running":
        from .timeline_service import _queue

        job = await _queue(db, repair, row, operation, JobType.SMART_REMAKE_INSPECT.value)
    return success(
        {
            "project": await repair.get(project_id),
            "operationId": str(operation.id),
            "status": operation.status,
            "processingJobId": str(job.id) if job else None,
        },
        request_id,
    )


@router.post("/projects/{project_id}/inspection-reviews", response_model=Envelope)
async def review_inspection(
    workspace_id: UUID,
    project_id: UUID,
    payload: InspectionReviewRequest,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await authorize(workspace_id, current_user, db, settings)
    repair = service_for(db, settings, workspace_id)
    inspector = InspectionService(
        repair.repository, repair.media, workspace_id, settings=settings
    )
    review = await inspector.review(project_id, current_user.id, payload)
    return success(
        {
            "project": await repair.get(project_id),
            "review": review,
            "status": "completed",
            "operationId": review["operationId"],
        },
        request_id,
    )


@router.post("/projects/{project_id}/approvals", response_model=Envelope)
async def approve_project(
    workspace_id: UUID,
    project_id: UUID,
    payload: ApprovalRequest,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await authorize(workspace_id, current_user, db, settings)
    result = await ProjectLifecycleService(service_for(db, settings, workspace_id)).approve(
        project_id, current_user.id, payload
    )
    return success(result, request_id)


@router.post("/projects/{project_id}/exports", response_model=Envelope)
async def export_project(
    workspace_id: UUID,
    project_id: UUID,
    payload: ExportRequest,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await authorize(workspace_id, current_user, db, settings)
    result = await ProjectLifecycleService(service_for(db, settings, workspace_id)).export(
        project_id, current_user.id, payload
    )
    return success(result, request_id)


@router.post("/projects/{project_id}/restore", response_model=Envelope)
async def restore_project(
    workspace_id: UUID,
    project_id: UUID,
    payload: RestoreRequest,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await authorize(workspace_id, current_user, db, settings)
    result = await ProjectLifecycleService(service_for(db, settings, workspace_id)).restore(
        project_id, current_user.id, payload
    )
    return success(result, request_id)


@router.post("/projects/{project_id}/deletions", response_model=Envelope)
async def delete_project(
    workspace_id: UUID,
    project_id: UUID,
    payload: DeletionRequest,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await authorize(workspace_id, current_user, db, settings)
    result = await ProjectLifecycleService(service_for(db, settings, workspace_id)).delete(
        project_id, current_user.id, payload
    )
    return success(result, request_id)


@router.get("/projects/{project_id}/provenance", response_model=Envelope)
async def project_provenance(
    workspace_id: UUID,
    project_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.WORKSPACE_READ, current_user, db)
    result = await ProjectLifecycleService(service_for(db, settings, workspace_id)).provenance(
        project_id
    )
    return success(result, request_id)
