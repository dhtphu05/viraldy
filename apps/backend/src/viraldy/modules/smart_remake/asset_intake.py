"""Resolve completed private uploads into the canonical owned project intake."""

from __future__ import annotations

import hashlib
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator
from starlette.concurrency import run_in_threadpool

from viraldy.modules.assets.public import AssetModel, AssetRepository, AssetVersionModel
from viraldy.platform.storage.ports import StoragePort
from viraldy.shared.errors.base import AppError, NotFoundError

from .engine.config import get_max_product_image_bytes, get_max_reference_video_bytes
from .engine.media_validation import PRODUCT_IMAGE_MIME_TYPES, REFERENCE_VIDEO_MIME_TYPES
from .engine.schemas import UploadedMedia
from .models import SmartRemakeProjectModel
from .product_references import MAX_PRODUCT_REFERENCE_IMAGES
from .project_contracts import SmartRemakeIntakeRequest
from .project_intake import create_intake
from .project_policy import assert_character_consent
from .repair_media import RepairMediaStore
from .repair_repository import RepairRepository
from .staged_upload_retention import staged_upload_reference


class SmartRemakeAssetIntakeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metadata: SmartRemakeIntakeRequest
    sourceAssetVersionId: UUID
    productAssetVersionId: UUID
    characterAssetVersionId: UUID | None = None
    additionalProductAssetVersionIds: list[UUID] = Field(
        default_factory=list,
        max_length=MAX_PRODUCT_REFERENCE_IMAGES - 1,
    )

    @model_validator(mode="after")
    def unique_product_images(self) -> SmartRemakeAssetIntakeRequest:
        values = [self.productAssetVersionId, *self.additionalProductAssetVersionIds]
        if len(values) != len(set(values)):
            raise ValueError("Each product image asset must be selected once.")
        return self


def _check_size(size: int, maximum: int) -> None:
    if size > maximum:
        raise AppError(
            "SMART_REMAKE_UPLOAD_TOO_LARGE", "Media exceeds the configured size limit.", 413
        )
    if size <= 0:
        raise AppError("INVALID_SMART_REMAKE_INPUT", "Input media is empty.", 422)


def _check_mime(mime: str | None, allowed: set[str]) -> None:
    if mime is not None and mime not in allowed:
        raise AppError(
            "UNSUPPORTED_SMART_REMAKE_MEDIA_TYPE", "Input media type is unsupported.", 422
        )


async def _uploaded_version(
    assets: AssetRepository,
    workspace_id: UUID,
    version_id: UUID,
    maximum: int,
    allowed: set[str],
) -> tuple[AssetModel, AssetVersionModel]:
    result = await assets.get_version_by_id_in_workspace(workspace_id, version_id)
    if result is None:
        raise NotFoundError("SMART_REMAKE_ASSET_NOT_FOUND", "Uploaded asset was not found.")
    asset, version = result
    # The general library lookup also accepts market references; owned intake cannot.
    if (
        asset.workspace_id != workspace_id
        or asset.library_scope != "WORKSPACE"
        or asset.created_by_user_id is None
        or asset.deleted_at is not None
    ):
        raise NotFoundError("SMART_REMAKE_ASSET_NOT_FOUND", "Uploaded asset was not found.")
    if asset.status != "uploaded" or version.validation_status not in {"uploaded", "processed"}:
        raise AppError("SMART_REMAKE_ASSET_NOT_READY", "Complete the media upload first.", 409)
    _check_size(version.size_bytes, maximum)
    _check_mime(version.declared_mime_type, allowed)
    _check_mime(version.detected_mime_type, allowed)
    return asset, version


def _read_version(
    storage: StoragePort, version: AssetVersionModel, maximum: int, allowed: set[str]
) -> UploadedMedia:
    metadata = storage.get_object_metadata(version.storage_key)
    _check_size(metadata.size_bytes, maximum)
    _check_mime(metadata.content_type, allowed)
    if metadata.size_bytes != version.size_bytes:
        raise AppError("SMART_REMAKE_INPUT_CHANGED", "Uploaded media size has changed.", 409)
    # A presigned PUT can still be reused: bound the GET even after a valid HEAD.
    data = storage.read_object_bytes(version.storage_key, maximum)
    _check_size(len(data), maximum)
    if len(data) != version.size_bytes:
        raise AppError("SMART_REMAKE_INPUT_CHANGED", "Uploaded media size has changed.", 409)
    if version.checksum_sha256 and hashlib.sha256(data).hexdigest() != version.checksum_sha256:
        raise AppError("SMART_REMAKE_INPUT_CHANGED", "Uploaded media bytes have changed.", 409)
    return UploadedMedia(
        bytes=data,
        mime_type=metadata.content_type or version.detected_mime_type or version.declared_mime_type,
        file_name=version.original_filename,
    )


async def create_intake_from_assets(
    assets: AssetRepository,
    repository: RepairRepository,
    media: RepairMediaStore,
    workspace_id: UUID,
    actor_id: UUID,
    payload: SmartRemakeAssetIntakeRequest,
) -> SmartRemakeProjectModel:
    metadata = payload.metadata
    if metadata.requirements.requiresCharacter and payload.characterAssetVersionId is None:
        raise AppError(
            "SMART_REMAKE_CHARACTER_REFERENCE_REQUIRED", "Upload a real character reference.", 403
        )
    if payload.characterAssetVersionId is not None:
        assert_character_consent(metadata.rights.model_dump(mode="json"))
    declarations = [
        (payload.sourceAssetVersionId, get_max_reference_video_bytes(), REFERENCE_VIDEO_MIME_TYPES),
        (payload.productAssetVersionId, get_max_product_image_bytes(), PRODUCT_IMAGE_MIME_TYPES),
    ]
    declarations.extend(
        (identity, get_max_product_image_bytes(), PRODUCT_IMAGE_MIME_TYPES)
        for identity in payload.additionalProductAssetVersionIds
    )
    character_index = len(declarations)
    if payload.characterAssetVersionId is not None:
        declarations.append(
            (
                payload.characterAssetVersionId,
                get_max_product_image_bytes(),
                PRODUCT_IMAGE_MIME_TYPES,
            )
        )
    # Validate every role's ownership, completion and declaration before accessing storage.
    records = [
        await _uploaded_version(assets, workspace_id, version_id, maximum, allowed)
        for version_id, maximum, allowed in declarations
    ]
    uploads = [
        await run_in_threadpool(_read_version, media.storage, version, maximum, allowed)
        for (_, version), (_, maximum, allowed) in zip(records, declarations, strict=True)
    ]
    references = [
        reference
        for asset, version in records
        if (reference := staged_upload_reference(asset, version, workspace_id)) is not None
    ]
    row = await create_intake(
        repository,
        media,
        workspace_id,
        actor_id,
        metadata,
        uploads[0],
        uploads[1],
        uploads[character_index] if payload.characterAssetVersionId else None,
        staged_uploads=references,
        additional_products=uploads[2:character_index],
    )
    if references:
        row = await repository.project(workspace_id, row.id, lock=True)
        policy = row.context_json["p0"]
        if policy.get("status") in {"suspended", "deleted"}:
            raise AppError(
                "SMART_REMAKE_USE_STOPPED", "This project's assets are no longer in use.", 403
            )
        staged = list(policy.get("stagedUploads", []))
        known = {reference.get("storageKey") for reference in staged}
        for reference in references:
            if reference["storageKey"] not in known:
                staged.append(reference)
                known.add(reference["storageKey"])
        row.context_json = {**row.context_json, "p0": {**policy, "stagedUploads": staged}}
        if (session := getattr(repository, "session", None)) is not None:
            await session.commit()
    return row
