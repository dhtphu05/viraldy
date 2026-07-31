from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from viraldy.api.dependencies.auth import CurrentUserDep, DbSession, require_workspace_permission
from viraldy.api.dependencies.request import get_request_id
from viraldy.api.responses.envelope import Envelope, success
from viraldy.modules.campaign_packs.schemas import (
    CreateCampaignPackRequest,
    CreateCampaignPackVersionRequest,
    ExportCampaignPackRequest,
    UpdateCampaignPackRequest,
)
from viraldy.modules.campaign_packs.service import CampaignPackService
from viraldy.modules.deletion.public import DeletionResourceType, DeletionService
from viraldy.platform.auth.policy import Permission
from viraldy.platform.config.settings import Settings, get_settings
from viraldy.platform.storage.s3 import S3StorageAdapter

router = APIRouter(prefix="/workspaces/{workspace_id}/campaign-packs", tags=["campaign-packs"])
SettingsDep = Annotated[Settings, Depends(get_settings)]


@router.post("", status_code=status.HTTP_201_CREATED, response_model=Envelope)
async def create_pack(
    workspace_id: UUID,
    payload: CreateCampaignPackRequest,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(
        workspace_id, Permission.CAMPAIGN_PACK_WRITE, current_user, db
    )
    pack = await CampaignPackService(db, settings).create(
        workspace_id,
        current_user.id,
        payload,
    )
    return success(pack.model_dump(mode="json"), request_id)


@router.get("", response_model=Envelope)
async def list_packs(
    workspace_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.WORKSPACE_READ, current_user, db)
    packs = await CampaignPackService(db, settings).list_packs(workspace_id)
    return success([pack.model_dump(mode="json") for pack in packs], request_id)


@router.get("/{campaign_pack_id}", response_model=Envelope)
async def get_pack(
    workspace_id: UUID,
    campaign_pack_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.WORKSPACE_READ, current_user, db)
    pack = await CampaignPackService(db, settings).get(workspace_id, campaign_pack_id)
    return success(pack.model_dump(mode="json"), request_id)


@router.patch("/{campaign_pack_id}", response_model=Envelope)
async def update_pack(
    workspace_id: UUID,
    campaign_pack_id: UUID,
    payload: UpdateCampaignPackRequest,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(
        workspace_id, Permission.CAMPAIGN_PACK_WRITE, current_user, db
    )
    pack = await CampaignPackService(db, settings).update(
        workspace_id,
        campaign_pack_id,
        payload,
    )
    return success(pack.model_dump(mode="json"), request_id)


@router.post(
    "/{campaign_pack_id}/versions", status_code=status.HTTP_201_CREATED, response_model=Envelope
)
async def create_pack_version(
    workspace_id: UUID,
    campaign_pack_id: UUID,
    payload: CreateCampaignPackVersionRequest,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(
        workspace_id, Permission.CAMPAIGN_PACK_WRITE, current_user, db
    )
    version = await CampaignPackService(db, settings).create_version(
        workspace_id, campaign_pack_id, current_user.id, payload
    )
    return success(version.model_dump(mode="json"), request_id)


@router.get("/{campaign_pack_id}/versions", response_model=Envelope)
async def list_pack_versions(
    workspace_id: UUID,
    campaign_pack_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.WORKSPACE_READ, current_user, db)
    versions = await CampaignPackService(db, settings).list_versions(
        workspace_id,
        campaign_pack_id,
    )
    return success([version.model_dump(mode="json") for version in versions], request_id)


@router.post("/{campaign_pack_id}/exports", response_model=Envelope)
async def export_pack(
    workspace_id: UUID,
    campaign_pack_id: UUID,
    payload: ExportCampaignPackRequest,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.DATA_EXPORT, current_user, db)
    export = await CampaignPackService(db, settings).export(
        workspace_id,
        campaign_pack_id,
        current_user.id,
        payload,
    )
    return success(export.model_dump(mode="json"), request_id)


@router.delete("/{campaign_pack_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pack(
    workspace_id: UUID,
    campaign_pack_id: UUID,
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
        resource_type=DeletionResourceType.CAMPAIGN_PACK,
        resource_id=campaign_pack_id,
        user_id=current_user.id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
