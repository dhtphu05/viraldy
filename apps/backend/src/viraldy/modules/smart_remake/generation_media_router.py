"""Workspace-scoped fresh download links for retained generation images."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path

from viraldy.api.dependencies.auth import CurrentUserDep, DbSession, require_workspace_permission
from viraldy.api.dependencies.request import get_request_id
from viraldy.api.responses.envelope import Envelope, success
from viraldy.platform.auth.policy import Permission

from .generation_media import generated_image_download
from .intake_router import SettingsDep, service_for

router = APIRouter()


@router.get(
    "/projects/{project_id}/generation/{operation_id}/images/{request_hash}/download",
    response_model=Envelope,
)
async def download_generated_image(
    workspace_id: UUID,
    project_id: UUID,
    operation_id: UUID,
    request_hash: Annotated[str, Path(pattern=r"^[a-f0-9]{64}$")],
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.WORKSPACE_READ, current_user, db)
    result = await generated_image_download(
        service_for(db, settings, workspace_id),
        workspace_id,
        project_id,
        operation_id,
        request_hash,
    )
    return success(result, request_id)
