"""Project intake and policy routes, mounted under the existing Smart Remake router."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from viraldy.api.dependencies.auth import CurrentUserDep, DbSession, require_workspace_permission
from viraldy.api.dependencies.request import get_request_id
from viraldy.api.responses.envelope import Envelope, success
from viraldy.platform.auth.current_user import CurrentUser
from viraldy.platform.auth.policy import Permission
from viraldy.platform.config.settings import Settings, get_settings
from viraldy.platform.storage.s3 import S3StorageAdapter
from viraldy.shared.errors.base import AppError

from .budget_ledger import initialize_budget
from .engine.config import get_max_product_image_bytes, get_max_reference_video_bytes
from .engine.errors import SmartRemakeError
from .engine.schemas import UploadedMedia
from .project_contracts import (
    SmartRemakeBudgetPatch,
    SmartRemakeIntakeRequest,
    SmartRemakeRequirementsPatch,
    SmartRemakeRightsPatch,
    SmartRemakeRightsReviewRequest,
)
from .project_intake import create_intake
from .project_metadata import patch_metadata
from .repair_media import RepairMediaStore
from .repair_repository import RepairRepository
from .repair_service import RepairService
from .service import feature_enabled

router = APIRouter()
SettingsDep = Annotated[Settings, Depends(get_settings)]


def service_for(db: AsyncSession, settings: Settings, workspace_id: UUID) -> RepairService:
    try:
        return RepairService(
            RepairRepository(db),
            RepairMediaStore(S3StorageAdapter(settings)),
            workspace_id,
            settings=settings,
        )
    except Exception as exc:
        raise AppError(
            "SMART_REMAKE_RETENTION_UNAVAILABLE", "Private media storage is unavailable.", 503
        ) from exc


async def authorize(
    workspace_id: UUID, current_user: CurrentUser, db: AsyncSession, settings: Settings
) -> None:
    await require_workspace_permission(workspace_id, Permission.ANALYSIS_RUN, current_user, db)
    if not feature_enabled(settings):
        raise AppError("SMART_REMAKE_DISABLED", "Smart Remake is disabled.", 503)


def _parse_metadata(value: str) -> SmartRemakeIntakeRequest:
    try:
        return SmartRemakeIntakeRequest.model_validate_json(value)
    except ValidationError as exc:
        errors = [
            {"loc": ["body", "metadata", *error["loc"]], "msg": error["msg"], "type": error["type"]}
            for error in exc.errors(include_input=False, include_context=False, include_url=False)
        ]
        raise AppError(
            "VALIDATION_ERROR", "Request validation failed.", 422, {"errors": errors}
        ) from exc


async def _read_upload(upload: UploadFile, maximum: int, default_mime: str) -> UploadedMedia:
    data = await upload.read(maximum + 1)
    if len(data) > maximum:
        raise AppError(
            "SMART_REMAKE_UPLOAD_TOO_LARGE", "Media exceeds the configured size limit.", 413
        )
    return UploadedMedia(
        bytes=data, mime_type=upload.content_type or default_mime, file_name=upload.filename
    )


@router.post("/projects", response_model=Envelope)
async def create_project(
    workspace_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    metadata: Annotated[str, Form(max_length=500000)],
    reference_video: Annotated[UploadFile, File(alias="referenceVideo")],
    product_image: Annotated[UploadFile, File(alias="productImage")],
    character_image: Annotated[UploadFile | None, File(alias="characterImage")] = None,
    additional_product_images: Annotated[
        list[UploadFile] | None, File(alias="additionalProductImages", max_length=13)
    ] = None,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await authorize(workspace_id, current_user, db, settings)
    payload = _parse_metadata(metadata)
    source = await _read_upload(reference_video, get_max_reference_video_bytes(), "video/mp4")
    product = await _read_upload(product_image, get_max_product_image_bytes(), "image/png")
    additional = [
        await _read_upload(upload, get_max_product_image_bytes(), "image/png")
        for upload in additional_product_images or []
    ]
    character = (
        await _read_upload(character_image, get_max_product_image_bytes(), "image/png")
        if character_image is not None
        else None
    )
    repair = service_for(db, settings, workspace_id)
    intake_options: dict[str, Any] = {"additional_products": additional} if additional else {}
    try:
        row = await create_intake(
            repair.repository,
            repair.media,
            workspace_id,
            current_user.id,
            payload,
            source,
            product,
            character,
            **intake_options,
        )
        # Reload under lock so a replay cannot overwrite a cap amended after intake.
        row = await repair.repository.project(workspace_id, row.id, lock=True)
        policy = row.context_json["p0"]["budgetPolicy"]
        if not policy.get("startedAt"):
            await initialize_budget(db, workspace_id, row.id, policy)
        else:
            await db.commit()
    except AppError:
        raise
    except SmartRemakeError as exc:
        raise AppError(exc.code, "Input media is invalid.", 422) from exc
    except Exception as exc:
        raise AppError(
            "SMART_REMAKE_RETENTION_UNAVAILABLE", "Private input retention is unavailable.", 503
        ) from exc
    return success({"project": await repair.present(row)}, request_id)


@router.patch("/projects/{project_id}/requirements", response_model=Envelope)
async def patch_requirements(
    workspace_id: UUID,
    project_id: UUID,
    payload: SmartRemakeRequirementsPatch,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await authorize(workspace_id, current_user, db, settings)
    result = await patch_metadata(
        service_for(db, settings, workspace_id),
        project_id,
        current_user.id,
        payload,
        kind="requirements",
    )
    return success(result, request_id)


@router.patch("/projects/{project_id}/rights", response_model=Envelope)
async def patch_rights(
    workspace_id: UUID,
    project_id: UUID,
    payload: SmartRemakeRightsPatch,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await authorize(workspace_id, current_user, db, settings)
    result = await patch_metadata(
        service_for(db, settings, workspace_id), project_id, current_user.id, payload, kind="rights"
    )
    return success(result, request_id)


@router.patch("/projects/{project_id}/budget", response_model=Envelope)
async def patch_budget(
    workspace_id: UUID,
    project_id: UUID,
    payload: SmartRemakeBudgetPatch,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await authorize(workspace_id, current_user, db, settings)
    result = await patch_metadata(
        service_for(db, settings, workspace_id), project_id, current_user.id, payload, kind="budget"
    )
    return success(result, request_id)


@router.post("/projects/{project_id}/rights/reviews", response_model=Envelope)
async def review_rights(
    workspace_id: UUID,
    project_id: UUID,
    payload: SmartRemakeRightsReviewRequest,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await authorize(workspace_id, current_user, db, settings)
    result = await patch_metadata(
        service_for(db, settings, workspace_id),
        project_id,
        current_user.id,
        payload,
        kind="rights_review",
    )
    return success(result, request_id)
