"""Private R2 upload sessions scoped to Smart Remake media roles."""

from __future__ import annotations

from typing import Literal, cast
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from viraldy.modules.assets.public import AssetRepository, AssetService
from viraldy.modules.assets.schemas import AssetResponse, UploadSessionResponse
from viraldy.platform.config.settings import Settings
from viraldy.platform.storage.keys import asset_source_key
from viraldy.platform.storage.ports import StoragePort
from viraldy.platform.storage.s3 import R2_OBJECT_MARKER
from viraldy.shared.errors.base import AppError, NotFoundError

from .asset_intake import _check_mime, _check_size
from .engine.config import get_max_product_image_bytes, get_max_reference_video_bytes
from .engine.media_validation import PRODUCT_IMAGE_MIME_TYPES, REFERENCE_VIDEO_MIME_TYPES
from .staged_upload_retention import UPLOAD_EXPIRY_METADATA_KEY

UploadRole = Literal["reference_video", "product_image", "character_image"]


class SmartRemakeUploadRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)

    filename: str = Field(min_length=1, max_length=512)
    declared_mime_type: str = Field(min_length=1, max_length=255)
    declared_size_bytes: int = Field(gt=0)
    role: UploadRole


def _require_r2(settings: Settings) -> None:
    if not settings.r2_configured:
        raise AppError(
            "SMART_REMAKE_R2_NOT_CONFIGURED", "Smart Remake private storage is unavailable.", 503
        )


def _role_limits(role: UploadRole) -> tuple[int, set[str]]:
    if role == "reference_video":
        return get_max_reference_video_bytes(), REFERENCE_VIDEO_MIME_TYPES
    return get_max_product_image_bytes(), PRODUCT_IMAGE_MIME_TYPES


async def create_upload_session(
    db: AsyncSession,
    assets: AssetRepository,
    storage: StoragePort,
    settings: Settings,
    workspace_id: UUID,
    actor_id: UUID,
    payload: SmartRemakeUploadRequest,
) -> UploadSessionResponse:
    _require_r2(settings)
    maximum, allowed = _role_limits(payload.role)
    _check_size(payload.declared_size_bytes, maximum)
    _check_mime(payload.declared_mime_type, allowed)
    asset_id, version_id = uuid4(), uuid4()
    asset, version = await assets.create_pending_upload(
        workspace_id=workspace_id,
        product_id=None,
        asset_type="reference" if payload.role == "reference_video" else "product_media",
        filename=payload.filename,
        declared_mime_type=payload.declared_mime_type,
        declared_size_bytes=payload.declared_size_bytes,
        storage_key=(
            f"{asset_source_key(workspace_id, asset_id, version_id)}"
            f"{R2_OBJECT_MARKER}{version_id.hex}"
        ),
        created_by_user_id=actor_id,
        asset_id=asset_id,
        version_id=version_id,
    )
    upload = await run_in_threadpool(
        storage.create_presigned_upload,
        version.storage_key,
        payload.declared_mime_type,
        content_length=payload.declared_size_bytes,
    )
    asset.metadata_json = {
        **asset.metadata_json,
        "smartRemakeUploadRole": payload.role,
        UPLOAD_EXPIRY_METADATA_KEY: upload.expires_at.isoformat(),
    }
    await db.commit()
    return UploadSessionResponse(
        asset_id=asset_id,
        asset_version_id=version_id,
        version_number=version.version_number,
        upload_url=upload.url,
        upload_method=upload.method,
        required_headers=upload.required_headers,
        expires_at=upload.expires_at,
    )


async def complete_upload(
    assets: AssetRepository,
    storage: StoragePort,
    service: AssetService,
    settings: Settings,
    workspace_id: UUID,
    asset_id: UUID,
    actor_id: UUID,
) -> AssetResponse:
    _require_r2(settings)
    asset = await assets.get(workspace_id, asset_id)
    if (
        asset is None
        or asset.workspace_id != workspace_id
        or asset.library_scope != "WORKSPACE"
        or asset.created_by_user_id is None
        or asset.deleted_at is not None
        or asset.metadata_json.get("smartRemakeUploadRole")
        not in {"reference_video", "product_image", "character_image"}
    ):
        raise NotFoundError("SMART_REMAKE_ASSET_NOT_FOUND", "Uploaded asset was not found.")
    version = await assets.get_current_version(asset_id)
    if version is None or version.storage_key != (
        f"{asset_source_key(workspace_id, asset_id, version.id)}"
        f"{R2_OBJECT_MARKER}{version.id.hex}"
    ):
        raise NotFoundError("SMART_REMAKE_ASSET_NOT_FOUND", "Uploaded asset was not found.")
    maximum, allowed = _role_limits(cast(UploadRole, asset.metadata_json["smartRemakeUploadRole"]))
    _check_size(version.size_bytes, maximum)
    _check_mime(version.declared_mime_type, allowed)
    metadata = await run_in_threadpool(storage.get_object_metadata, version.storage_key)
    _check_size(metadata.size_bytes, maximum)
    _check_mime(metadata.content_type, allowed)
    if metadata.size_bytes != version.size_bytes:
        raise AppError("UPLOAD_SIZE_MISMATCH", "Uploaded object size does not match declaration.")
    return await service.complete_upload(workspace_id, asset_id, actor_id)
