from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status

from viraldy.api.dependencies.auth import CurrentUserDep, DbSession, require_workspace_permission
from viraldy.api.dependencies.request import get_request_id
from viraldy.api.responses.envelope import Envelope, success
from viraldy.modules.campaign_packs.schemas import (
    CreateCampaignPackRequest,
    CreateCampaignPackVersionRequest,
    UpdateCampaignPackRequest,
)
from viraldy.modules.campaign_packs.service import CampaignPackService
from viraldy.platform.auth.policy import Permission

router = APIRouter(prefix="/workspaces/{workspace_id}/campaign-packs", tags=["campaign-packs"])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=Envelope)
async def create_pack(
    workspace_id: UUID,
    payload: CreateCampaignPackRequest,
    current_user: CurrentUserDep,
    db: DbSession,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(
        workspace_id, Permission.CAMPAIGN_PACK_WRITE, current_user, db
    )
    pack = await CampaignPackService(db).create(workspace_id, current_user.id, payload)
    return success(pack.model_dump(mode="json"), request_id)


@router.get("", response_model=Envelope)
async def list_packs(
    workspace_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.WORKSPACE_READ, current_user, db)
    packs = await CampaignPackService(db).list(workspace_id)
    return success([pack.model_dump(mode="json") for pack in packs], request_id)


@router.get("/{campaign_pack_id}", response_model=Envelope)
async def get_pack(
    workspace_id: UUID,
    campaign_pack_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.WORKSPACE_READ, current_user, db)
    pack = await CampaignPackService(db).get(workspace_id, campaign_pack_id)
    return success(pack.model_dump(mode="json"), request_id)


@router.patch("/{campaign_pack_id}", response_model=Envelope)
async def update_pack(
    workspace_id: UUID,
    campaign_pack_id: UUID,
    payload: UpdateCampaignPackRequest,
    current_user: CurrentUserDep,
    db: DbSession,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(
        workspace_id, Permission.CAMPAIGN_PACK_WRITE, current_user, db
    )
    pack = await CampaignPackService(db).update(workspace_id, campaign_pack_id, payload)
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
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(
        workspace_id, Permission.CAMPAIGN_PACK_WRITE, current_user, db
    )
    version = await CampaignPackService(db).create_version(
        workspace_id, campaign_pack_id, current_user.id, payload
    )
    return success(version.model_dump(mode="json"), request_id)


@router.get("/{campaign_pack_id}/versions", response_model=Envelope)
async def list_pack_versions(
    workspace_id: UUID,
    campaign_pack_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.WORKSPACE_READ, current_user, db)
    versions = await CampaignPackService(db).list_versions(workspace_id, campaign_pack_id)
    return success([version.model_dump(mode="json") for version in versions], request_id)
