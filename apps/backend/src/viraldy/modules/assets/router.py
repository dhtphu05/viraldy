from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Response, status

from viraldy.api.dependencies.auth import CurrentUserDep, DbSession, require_workspace_permission
from viraldy.api.dependencies.request import get_request_id
from viraldy.api.responses.envelope import Envelope, success
from viraldy.modules.assets.schemas import (
    CreateAssetRevisionUploadSessionRequest,
    CreateUploadSessionRequest,
)
from viraldy.modules.assets.service import AssetService
from viraldy.modules.deletion.public import DeletionResourceType, DeletionService
from viraldy.modules.products.public import ProductQueries
from viraldy.platform.auth.policy import Permission
from viraldy.platform.config.settings import Settings, get_settings
from viraldy.platform.storage.s3 import S3StorageAdapter

router = APIRouter(prefix="/workspaces/{workspace_id}/assets", tags=["assets"])
SettingsDep = Annotated[Settings, Depends(get_settings)]


def asset_service(db: DbSession, settings: Settings) -> AssetService:
    return AssetService(
        session=db,
        storage=S3StorageAdapter(settings),
        product_lookup=ProductQueries(db),
        settings=settings,
    )


@router.post("/upload-sessions", status_code=status.HTTP_201_CREATED, response_model=Envelope)
async def create_upload_session(
    workspace_id: UUID,
    payload: CreateUploadSessionRequest,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.REFERENCE_WRITE, current_user, db)
    upload = await asset_service(db, settings).create_upload_session(
        workspace_id,
        current_user.id,
        payload,
    )
    return success(upload.model_dump(mode="json"), request_id)


@router.post("/{asset_id}/complete-upload", response_model=Envelope)
async def complete_upload(
    workspace_id: UUID,
    asset_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.REFERENCE_WRITE, current_user, db)
    asset = await asset_service(db, settings).complete_upload(
        workspace_id,
        asset_id,
        current_user.id,
    )
    return success(asset.model_dump(mode="json"), request_id)


@router.post(
    "/{asset_id}/versions/upload-sessions",
    status_code=status.HTTP_201_CREATED,
    response_model=Envelope,
)
async def create_revision_upload_session(
    workspace_id: UUID,
    asset_id: UUID,
    payload: CreateAssetRevisionUploadSessionRequest,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(
        workspace_id,
        Permission.REFERENCE_WRITE,
        current_user,
        db,
    )
    upload = await asset_service(db, settings).create_revision_upload_session(
        workspace_id,
        asset_id,
        payload,
    )
    return success(upload.model_dump(mode="json"), request_id)


@router.post(
    "/{asset_id}/versions/{asset_version_id}/complete-upload",
    response_model=Envelope,
)
async def complete_revision_upload(
    workspace_id: UUID,
    asset_id: UUID,
    asset_version_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(
        workspace_id,
        Permission.REFERENCE_WRITE,
        current_user,
        db,
    )
    version = await asset_service(db, settings).complete_revision_upload(
        workspace_id,
        asset_id,
        asset_version_id,
        current_user.id,
    )
    return success(version.model_dump(mode="json"), request_id)


@router.get("/{asset_id}/versions", response_model=Envelope)
async def list_asset_versions(
    workspace_id: UUID,
    asset_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(
        workspace_id,
        Permission.REFERENCE_READ,
        current_user,
        db,
    )
    versions = await asset_service(db, settings).list_versions(workspace_id, asset_id)
    return success([version.model_dump(mode="json") for version in versions], request_id)


@router.get("/{asset_id}/versions/{asset_version_id}/playback", response_model=Envelope)
async def get_asset_version_playback(
    workspace_id: UUID,
    asset_id: UUID,
    asset_version_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(
        workspace_id,
        Permission.REFERENCE_READ,
        current_user,
        db,
    )
    playback = await asset_service(db, settings).get_version_playback(
        workspace_id,
        asset_id,
        asset_version_id,
    )
    return success(playback.model_dump(mode="json"), request_id)


@router.get("", response_model=Envelope)
async def list_assets(
    workspace_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.REFERENCE_READ, current_user, db)
    assets = await asset_service(db, settings).list_assets(workspace_id)
    return success([asset.model_dump(mode="json") for asset in assets], request_id)


@router.get("/{asset_id}", response_model=Envelope)
async def get_asset(
    workspace_id: UUID,
    asset_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.REFERENCE_READ, current_user, db)
    asset = await asset_service(db, settings).get_asset(workspace_id, asset_id)
    return success(asset.model_dump(mode="json"), request_id)


@router.post("/{asset_id}/process", status_code=status.HTTP_202_ACCEPTED, response_model=Envelope)
async def process_asset(
    workspace_id: UUID,
    asset_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.ANALYSIS_RUN, current_user, db)
    job = await asset_service(db, settings).request_processing(
        workspace_id, asset_id, idempotency_key
    )
    return success(job.model_dump(mode="json"), request_id)


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_asset(
    workspace_id: UUID,
    asset_id: UUID,
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
        resource_type=DeletionResourceType.ASSET,
        resource_id=asset_id,
        user_id=current_user.id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
