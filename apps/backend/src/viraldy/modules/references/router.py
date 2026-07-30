from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Response, status

from viraldy.api.dependencies.auth import CurrentUserDep, DbSession, require_workspace_permission
from viraldy.api.dependencies.request import get_request_id
from viraldy.api.responses.envelope import Envelope, success
from viraldy.modules.deletion.public import DeletionResourceType, DeletionService
from viraldy.modules.products.public import ProductQueries
from viraldy.modules.references.schemas import CreateReferenceRequest
from viraldy.modules.references.service import ReferenceService
from viraldy.platform.auth.policy import Permission
from viraldy.platform.config.settings import Settings, get_settings
from viraldy.platform.storage.s3 import S3StorageAdapter

router = APIRouter(prefix="/workspaces/{workspace_id}/references", tags=["references"])
SettingsDep = Annotated[Settings, Depends(get_settings)]


def _service(db: DbSession) -> ReferenceService:
    return ReferenceService(db, ProductQueries(db))


@router.post("", status_code=status.HTTP_201_CREATED, response_model=Envelope)
async def create_reference(
    workspace_id: UUID,
    payload: CreateReferenceRequest,
    current_user: CurrentUserDep,
    db: DbSession,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.REFERENCE_WRITE, current_user, db)
    reference = await _service(db).create(workspace_id, current_user.id, payload)
    return success(reference.model_dump(mode="json"), request_id)


@router.get("", response_model=Envelope)
async def list_references(
    workspace_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.REFERENCE_READ, current_user, db)
    references = await _service(db).list(workspace_id)
    return success([reference.model_dump(mode="json") for reference in references], request_id)


@router.get("/{reference_id}", response_model=Envelope)
async def get_reference(
    workspace_id: UUID,
    reference_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.REFERENCE_READ, current_user, db)
    reference = await _service(db).get(workspace_id, reference_id)
    return success(reference.model_dump(mode="json"), request_id)


@router.post(
    "/{reference_id}/analyze", status_code=status.HTTP_202_ACCEPTED, response_model=Envelope
)
async def analyze_reference(
    workspace_id: UUID,
    reference_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.ANALYSIS_RUN, current_user, db)
    result = await _service(db).analyze(
        workspace_id, reference_id, current_user.id, idempotency_key
    )
    return success(result.model_dump(mode="json"), request_id)


@router.delete("/{reference_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reference(
    workspace_id: UUID,
    reference_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
) -> Response:
    await require_workspace_permission(
        workspace_id,
        Permission.DATA_DELETE,
        current_user,
        db,
    )
    await DeletionService(db, S3StorageAdapter(settings)).delete(
        workspace_id=workspace_id,
        resource_type=DeletionResourceType.REFERENCE,
        resource_id=reference_id,
        user_id=current_user.id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
