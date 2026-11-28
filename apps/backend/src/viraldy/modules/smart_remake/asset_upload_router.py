"""Authorized Smart Remake direct-upload session HTTP boundaries."""

from uuid import UUID

from fastapi import APIRouter, Depends

from viraldy.api.dependencies.auth import CurrentUserDep, DbSession
from viraldy.api.dependencies.request import get_request_id
from viraldy.api.responses.envelope import Envelope, success
from viraldy.modules.assets.public import AssetRepository, AssetService
from viraldy.modules.products.public import ProductQueries
from viraldy.platform.storage.s3 import S3StorageAdapter
from viraldy.shared.errors.base import AppError

from .asset_uploads import (
    SmartRemakeUploadRequest,
    _require_r2,
    complete_upload,
    create_upload_session,
)
from .intake_router import SettingsDep, authorize

router = APIRouter()


@router.post("/upload-sessions", status_code=201, response_model=Envelope)
async def create_smart_remake_upload_session(
    workspace_id: UUID,
    payload: SmartRemakeUploadRequest,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await authorize(workspace_id, current_user, db, settings)
    _require_r2(settings)
    try:
        upload = await create_upload_session(
            db,
            AssetRepository(db),
            S3StorageAdapter(settings),
            settings,
            workspace_id,
            current_user.id,
            payload,
        )
    except AppError:
        raise
    except Exception as exc:
        raise AppError(
            "SMART_REMAKE_UPLOAD_UNAVAILABLE", "Private media upload is unavailable.", 503
        ) from exc
    return success(upload.model_dump(mode="json"), request_id)


@router.post("/upload-sessions/{asset_id}/complete", response_model=Envelope)
async def complete_smart_remake_upload(
    workspace_id: UUID,
    asset_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await authorize(workspace_id, current_user, db, settings)
    _require_r2(settings)
    try:
        storage = S3StorageAdapter(settings)
        service = AssetService(db, storage, ProductQueries(db), settings)
        asset = await complete_upload(
            AssetRepository(db),
            storage,
            service,
            settings,
            workspace_id,
            asset_id,
            current_user.id,
        )
    except AppError:
        raise
    except Exception as exc:
        raise AppError(
            "SMART_REMAKE_UPLOAD_UNAVAILABLE", "Private media upload is unavailable.", 503
        ) from exc
    return success(asset.model_dump(mode="json"), request_id)
