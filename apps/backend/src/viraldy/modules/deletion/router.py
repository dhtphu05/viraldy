from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, status

from viraldy.api.dependencies.auth import (
    CurrentUserDep,
    DbSession,
    require_workspace_permission,
)
from viraldy.api.dependencies.request import get_request_id
from viraldy.api.responses.envelope import Envelope, success
from viraldy.modules.deletion.contracts import DeletionResourceType
from viraldy.modules.deletion.service import DeletionService
from viraldy.modules.jobs.public import JobType, request_mvp_job
from viraldy.platform.auth.policy import Permission
from viraldy.platform.config.settings import Settings, get_settings
from viraldy.platform.storage.s3 import S3StorageAdapter

router = APIRouter(
    prefix="/workspaces/{workspace_id}/deletions",
    tags=["deletions"],
)
SettingsDep = Annotated[Settings, Depends(get_settings)]


def _service(db: DbSession, settings: Settings) -> DeletionService:
    return DeletionService(db, S3StorageAdapter(settings))


@router.post("/retention", status_code=status.HTTP_202_ACCEPTED, response_model=Envelope)
async def request_retention_cleanup(
    workspace_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(
        workspace_id,
        Permission.DATA_DELETE,
        current_user,
        db,
    )
    job = await request_mvp_job(
        db,
        workspace_id,
        "workspace",
        workspace_id,
        JobType.RETENTION_CLEANUP.value,
        {"workspace_id": str(workspace_id)},
        idempotency_key,
    )
    return success(job.model_dump(mode="json"), request_id)


@router.delete("", response_model=Envelope)
async def delete_workspace_data(
    workspace_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(
        workspace_id,
        Permission.DATA_DELETE,
        current_user,
        db,
    )
    result = await _service(db, settings).delete(
        workspace_id=workspace_id,
        resource_type=DeletionResourceType.WORKSPACE,
        resource_id=workspace_id,
        user_id=current_user.id,
    )
    return success(result.model_dump(mode="json"), request_id)


@router.delete("/{resource_type}/{resource_id}", response_model=Envelope)
async def delete_resource_data(
    workspace_id: UUID,
    resource_type: DeletionResourceType,
    resource_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(
        workspace_id,
        Permission.DATA_DELETE,
        current_user,
        db,
    )
    result = await _service(db, settings).delete(
        workspace_id=workspace_id,
        resource_type=resource_type,
        resource_id=resource_id,
        user_id=current_user.id,
    )
    return success(result.model_dump(mode="json"), request_id)
