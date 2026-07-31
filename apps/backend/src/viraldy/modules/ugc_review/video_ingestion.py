from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import BinaryIO
from uuid import UUID

from starlette.concurrency import run_in_threadpool

from viraldy.modules.assets.public import AssetRepository, AssetService
from viraldy.modules.assets.schemas import (
    CreateAssetRevisionUploadSessionRequest,
    CreateUploadSessionRequest,
)
from viraldy.modules.products.public import ProductQueries
from viraldy.modules.ugc_review.service import UGCAssetVersion, UGCVideoUpload
from viraldy.platform.config.settings import Settings
from viraldy.platform.database.session import AsyncSessionFactory
from viraldy.platform.storage.s3 import S3StorageAdapter
from viraldy.shared.errors.base import AppError, PayloadTooLargeError

_COPY_CHUNK_BYTES = 1024 * 1024


@dataclass(frozen=True, slots=True)
class _SpooledUpload:
    path: str
    size_bytes: int


class S3UGCVideoIngestion:
    """Compatibility adapter for direct multipart uploads.

    Browser clients should normally use the existing presigned upload flow. This
    adapter keeps the documented single-request multipart contract functional
    without introducing a second asset or media-processing implementation.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def ingest_initial(
        self,
        workspace_id: UUID,
        actor_user_id: UUID,
        upload: UGCVideoUpload,
    ) -> UGCAssetVersion:
        spooled, content_type = await self._prepare(upload)
        try:
            async with AsyncSessionFactory() as session:
                storage = S3StorageAdapter(self._settings)
                service = AssetService(
                    session=session,
                    storage=storage,
                    product_lookup=ProductQueries(session),
                    settings=self._settings,
                )
                created = await service.create_upload_session(
                    workspace_id,
                    actor_user_id,
                    CreateUploadSessionRequest(
                        filename=_safe_filename(upload.filename),
                        declared_mime_type=content_type,
                        declared_size_bytes=spooled.size_bytes,
                        asset_type="ugc",
                    ),
                )
                version = await AssetRepository(session).get_version_in_workspace(
                    workspace_id,
                    created.asset_id,
                    created.asset_version_id,
                )
                if version is None:
                    raise AppError(
                        "ASSET_VERSION_NOT_FOUND",
                        "The direct upload asset version was not created.",
                        status_code=500,
                    )
                await run_in_threadpool(
                    storage.upload_file,
                    spooled.path,
                    version.storage_key,
                    content_type,
                )
                await service.complete_upload(workspace_id, created.asset_id, actor_user_id)
                return UGCAssetVersion(
                    workspace_id=workspace_id,
                    asset_id=created.asset_id,
                    asset_version_id=created.asset_version_id,
                    validation_status="uploaded",
                )
        finally:
            await run_in_threadpool(Path(spooled.path).unlink, missing_ok=True)

    async def ingest_revision(
        self,
        workspace_id: UUID,
        actor_user_id: UUID,
        parent_asset_id: UUID,
        upload: UGCVideoUpload,
    ) -> UGCAssetVersion:
        spooled, content_type = await self._prepare(upload)
        try:
            async with AsyncSessionFactory() as session:
                storage = S3StorageAdapter(self._settings)
                service = AssetService(
                    session=session,
                    storage=storage,
                    product_lookup=ProductQueries(session),
                    settings=self._settings,
                )
                created = await service.create_revision_upload_session(
                    workspace_id,
                    parent_asset_id,
                    CreateAssetRevisionUploadSessionRequest(
                        filename=_safe_filename(upload.filename),
                        declared_mime_type=content_type,
                        declared_size_bytes=spooled.size_bytes,
                    ),
                )
                version = await AssetRepository(session).get_version_in_workspace(
                    workspace_id,
                    parent_asset_id,
                    created.asset_version_id,
                )
                if version is None:
                    raise AppError(
                        "ASSET_VERSION_NOT_FOUND",
                        "The direct upload revision was not created.",
                        status_code=500,
                    )
                await run_in_threadpool(
                    storage.upload_file,
                    spooled.path,
                    version.storage_key,
                    content_type,
                )
                await service.complete_revision_upload(
                    workspace_id,
                    parent_asset_id,
                    created.asset_version_id,
                    actor_user_id,
                )
                return UGCAssetVersion(
                    workspace_id=workspace_id,
                    asset_id=parent_asset_id,
                    asset_version_id=created.asset_version_id,
                    validation_status="uploaded",
                )
        finally:
            await run_in_threadpool(Path(spooled.path).unlink, missing_ok=True)

    async def _prepare(self, upload: UGCVideoUpload) -> tuple[_SpooledUpload, str]:
        content_type = _video_content_type(upload.filename, upload.content_type)
        spooled = await run_in_threadpool(
            _spool_upload,
            upload.file,
            self._settings.max_declared_upload_bytes,
        )
        return spooled, content_type


def _spool_upload(source: BinaryIO, max_size_bytes: int) -> _SpooledUpload:
    temporary_path: str | None = None
    try:
        source.seek(0)
        size_bytes = 0
        with NamedTemporaryFile(prefix="viraldy-ugc-", suffix=".upload", delete=False) as target:
            temporary_path = target.name
            while chunk := source.read(_COPY_CHUNK_BYTES):
                size_bytes += len(chunk)
                if size_bytes > max_size_bytes:
                    raise PayloadTooLargeError(
                        "UPLOAD_TOO_LARGE",
                        "UGC video exceeds the configured upload limit.",
                    )
                target.write(chunk)
        if size_bytes == 0:
            raise AppError("INVALID_UPLOAD_SIZE", "UGC video must not be empty.")
        return _SpooledUpload(path=temporary_path, size_bytes=size_bytes)
    except Exception:
        if temporary_path is not None:
            Path(temporary_path).unlink(missing_ok=True)
        raise


def _video_content_type(filename: str, declared: str) -> str:
    if declared in {"video/mp4", "video/quicktime"}:
        return declared
    suffix = Path(_safe_filename(filename)).suffix.casefold()
    inferred = {".mp4": "video/mp4", ".mov": "video/quicktime"}.get(suffix)
    if inferred is None:
        raise AppError(
            "UNSUPPORTED_MIME_TYPE",
            "UGC Review supports MP4 and QuickTime video files.",
        )
    return inferred


def _safe_filename(filename: str) -> str:
    normalized = filename.replace("\\", "/").rsplit("/", 1)[-1].strip()
    if not normalized:
        raise AppError("UGC_REVIEW_FILENAME_REQUIRED", "Video filename is required.")
    return normalized


__all__ = ["S3UGCVideoIngestion"]
