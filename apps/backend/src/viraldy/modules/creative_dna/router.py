from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from viraldy.api.dependencies.auth import CurrentUserDep, DbSession, require_workspace_permission
from viraldy.api.dependencies.request import get_request_id
from viraldy.api.responses.envelope import Envelope, success
from viraldy.modules.creative_dna.service import CreativeDnaService
from viraldy.modules.deletion.public import DeletionResourceType, DeletionService
from viraldy.platform.auth.policy import Permission
from viraldy.platform.config.settings import Settings, get_settings
from viraldy.platform.storage.s3 import S3StorageAdapter

router = APIRouter(prefix="/workspaces/{workspace_id}", tags=["creative-dna"])
SettingsDep = Annotated[Settings, Depends(get_settings)]


@router.get("/creative-dna/{dna_version_id}", response_model=Envelope)
async def get_dna(
    workspace_id: UUID,
    dna_version_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.REFERENCE_READ, current_user, db)
    dna = await CreativeDnaService(db).get(workspace_id, dna_version_id, current_user.id)
    return success(dna.model_dump(mode="json"), request_id)


@router.get("/references/{reference_id}/creative-dna", response_model=Envelope)
async def latest_reference_dna(
    workspace_id: UUID,
    reference_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.REFERENCE_READ, current_user, db)
    dna = await CreativeDnaService(db).latest_for_reference(
        workspace_id, reference_id, current_user.id
    )
    return success(dna.model_dump(mode="json"), request_id)


@router.delete(
    "/creative-dna/{dna_version_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_dna(
    workspace_id: UUID,
    dna_version_id: UUID,
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
        resource_type=DeletionResourceType.CREATIVE_DNA,
        resource_id=dna_version_id,
        user_id=current_user.id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
