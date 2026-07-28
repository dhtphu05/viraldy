from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from viraldy.modules.assets.repository import AssetRepository
from viraldy.modules.assets.schemas import (
    AssetResponse,
    CreateUploadSessionRequest,
    UploadSessionResponse,
)
from viraldy.modules.assets.validators import validate_upload_declaration
from viraldy.modules.jobs.public import JobResponse, request_process_asset
from viraldy.modules.products.public import ProductLookupPort
from viraldy.platform.config.settings import Settings
from viraldy.platform.storage.keys import asset_source_key
from viraldy.platform.storage.ports import StoragePort
from viraldy.shared.errors.base import AppError, NotFoundError


class AssetService:
    def __init__(
        self,
        session: AsyncSession,
        storage: StoragePort,
        product_lookup: ProductLookupPort,
        settings: Settings,
    ) -> None:
        self._session = session
        self._repository = AssetRepository(session)
        self._storage = storage
        self._product_lookup = product_lookup
        self._settings = settings

    async def create_upload_session(
        self,
        workspace_id: UUID,
        user_id: UUID,
        data: CreateUploadSessionRequest,
    ) -> UploadSessionResponse:
        validate_upload_declaration(
            filename=data.filename,
            declared_mime_type=data.declared_mime_type,
            declared_size_bytes=data.declared_size_bytes,
            asset_type=data.asset_type,
            allowed_mime_types=self._settings.allowed_upload_mime_types,
            max_size_bytes=self._settings.max_declared_upload_bytes,
        )
        if data.product_id and not await self._product_lookup.exists_in_workspace(
            workspace_id, data.product_id
        ):
            raise NotFoundError("PRODUCT_NOT_FOUND", "Product was not found.")

        asset_id = uuid4()
        version_id = uuid4()
        storage_key = asset_source_key(workspace_id, asset_id, version_id)
        _, version = await self._repository.create_pending_upload(
            workspace_id=workspace_id,
            product_id=data.product_id,
            asset_type=data.asset_type,
            filename=data.filename,
            declared_mime_type=data.declared_mime_type,
            declared_size_bytes=data.declared_size_bytes,
            storage_key=storage_key,
            created_by_user_id=user_id,
            asset_id=asset_id,
            version_id=version_id,
        )
        upload = self._storage.create_presigned_upload(version.storage_key, data.declared_mime_type)
        await self._session.commit()
        return UploadSessionResponse(
            asset_id=asset_id,
            asset_version_id=version_id,
            upload_url=upload.url,
            upload_method=upload.method,
            required_headers=upload.required_headers,
            expires_at=upload.expires_at,
        )

    async def complete_upload(self, workspace_id: UUID, asset_id: UUID) -> AssetResponse:
        asset = await self._repository.get(workspace_id, asset_id)
        if asset is None:
            raise NotFoundError("ASSET_NOT_FOUND", "Asset was not found.")

        version = await self._repository.get_current_version(asset_id)
        if version is None:
            raise AppError("ASSET_VERSION_NOT_FOUND", "Asset version was not found.")
        if not self._storage.object_exists(version.storage_key):
            raise AppError("UPLOAD_OBJECT_NOT_FOUND", "Uploaded object was not found.")

        metadata = self._storage.get_object_metadata(version.storage_key)
        if metadata.size_bytes != version.size_bytes:
            raise AppError(
                "UPLOAD_SIZE_MISMATCH", "Uploaded object size does not match declaration."
            )

        result = await self._repository.mark_uploaded(
            workspace_id,
            asset_id,
            size_bytes=metadata.size_bytes,
            detected_mime_type=metadata.content_type,
            checksum_sha256=metadata.checksum_sha256,
        )
        if result is None:
            raise NotFoundError("ASSET_NOT_FOUND", "Asset was not found.")

        await self._session.commit()
        return AssetResponse.model_validate(result[0])

    async def list_assets(self, workspace_id: UUID) -> list[AssetResponse]:
        assets = await self._repository.list_assets(workspace_id)
        return [AssetResponse.model_validate(asset) for asset in assets]

    async def get_asset(self, workspace_id: UUID, asset_id: UUID) -> AssetResponse:
        asset = await self._repository.get(workspace_id, asset_id)
        if asset is None:
            raise NotFoundError("ASSET_NOT_FOUND", "Asset was not found.")
        return AssetResponse.model_validate(asset)

    async def request_processing(
        self,
        workspace_id: UUID,
        asset_id: UUID,
        idempotency_key: str | None,
    ) -> JobResponse:
        asset = await self._repository.get(workspace_id, asset_id)
        if asset is None:
            raise NotFoundError("ASSET_NOT_FOUND", "Asset was not found.")
        if asset.status != "uploaded":
            raise AppError("ASSET_NOT_READY", "Asset must be uploaded before processing.")

        version = await self._repository.get_current_version(asset_id)
        if version is None:
            raise AppError("ASSET_VERSION_NOT_FOUND", "Asset version was not found.")

        return await request_process_asset(
            session=self._session,
            workspace_id=workspace_id,
            asset_id=asset_id,
            asset_version_id=version.id,
            idempotency_key=idempotency_key,
        )
