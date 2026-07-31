from __future__ import annotations

from typing import Annotated, cast
from uuid import UUID

from fastapi import APIRouter, Depends, Form, Header, Path, Request, status
from starlette.datastructures import UploadFile

from viraldy.api.dependencies.auth import CurrentUserDep, DbSession, require_workspace_permission
from viraldy.api.dependencies.request import get_request_id
from viraldy.api.responses.envelope import Envelope, success
from viraldy.modules.ugc_review.schemas import (
    CreateUGCReviewForm,
    CreateUGCReviewRevisionForm,
    RecordUGCRecommendationActionRequest,
)
from viraldy.modules.ugc_review.service import (
    UGCReviewService,
    UGCVideoIngestionPort,
    UGCVideoUpload,
)
from viraldy.platform.auth.policy import Permission
from viraldy.shared.errors.base import AppError

router = APIRouter(
    prefix="/workspaces/{workspace_id}/ugc-reviews",
    tags=["ugc-reviews"],
)


@router.post("", status_code=status.HTTP_202_ACCEPTED, response_model=Envelope)
async def create_review(
    workspace_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    request: Request,
    payload: Annotated[CreateUGCReviewForm, Form(media_type="multipart/form-data")],
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(
        workspace_id,
        Permission.ANALYSIS_RUN,
        current_user,
        db,
    )
    service = UGCReviewService(db)
    if payload.video_file is None:
        result = await service.create(workspace_id, payload, idempotency_key)
    else:
        result = await service.create_from_video(
            workspace_id,
            current_user.id,
            payload,
            _video_upload(payload.video_file),
            _require_ingestion_adapter(request),
            idempotency_key,
        )
    return success(result.model_dump(mode="json"), request_id)


@router.get("/{review_id}/status", response_model=Envelope)
async def get_review_status(
    workspace_id: UUID,
    review_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.WORKSPACE_READ, current_user, db)
    result = await UGCReviewService(db).get_status(workspace_id, review_id)
    return success(result.model_dump(mode="json"), request_id)


@router.get("/{review_id}", response_model=Envelope)
async def get_review_result(
    workspace_id: UUID,
    review_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.WORKSPACE_READ, current_user, db)
    result = await UGCReviewService(db).get_result(workspace_id, review_id)
    return success(result.model_dump(mode="json"), request_id)


@router.post(
    "/{review_id}/recommendations/{recommendation_id}/actions",
    status_code=status.HTTP_201_CREATED,
    response_model=Envelope,
)
async def record_recommendation_action(
    workspace_id: UUID,
    review_id: UUID,
    recommendation_id: Annotated[str, Path(min_length=1, max_length=160)],
    payload: RecordUGCRecommendationActionRequest,
    current_user: CurrentUserDep,
    db: DbSession,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(
        workspace_id,
        Permission.RECOMMENDATION_ACT,
        current_user,
        db,
    )
    result = await UGCReviewService(db).record_action(
        workspace_id,
        review_id,
        recommendation_id,
        payload,
    )
    return success(result.model_dump(mode="json"), request_id)


@router.post(
    "/{review_id}/revisions",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=Envelope,
)
async def create_review_revision(
    workspace_id: UUID,
    review_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    request: Request,
    payload: Annotated[
        CreateUGCReviewRevisionForm,
        Form(media_type="multipart/form-data"),
    ],
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(
        workspace_id,
        Permission.ANALYSIS_RUN,
        current_user,
        db,
    )
    service = UGCReviewService(db)
    if payload.video_file is None:
        result = await service.create_revision(
            workspace_id,
            review_id,
            payload,
            idempotency_key,
        )
    else:
        if payload.asset_version_id is not None:
            raise AppError(
                "UGC_REVIEW_VIDEO_ASSET_CONFLICT",
                "Submit either a video file or an existing asset version, not both.",
            )
        result = await service.create_revision_from_video(
            workspace_id,
            review_id,
            current_user.id,
            _video_upload(payload.video_file),
            _require_ingestion_adapter(request),
            idempotency_key,
        )
    return success(result.model_dump(mode="json"), request_id)


@router.get("/{review_id}/comparisons/latest", response_model=Envelope)
async def get_latest_review_comparison(
    workspace_id: UUID,
    review_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.WORKSPACE_READ, current_user, db)
    result = await UGCReviewService(db).get_latest_comparison(workspace_id, review_id)
    return success(result.model_dump(mode="json"), request_id)


def _video_upload(upload: UploadFile) -> UGCVideoUpload:
    if not upload.filename:
        raise AppError("UGC_REVIEW_FILENAME_REQUIRED", "Video filename is required.")
    return UGCVideoUpload(
        filename=upload.filename,
        content_type=upload.content_type or "application/octet-stream",
        file=upload.file,
    )


def _require_ingestion_adapter(request: Request) -> UGCVideoIngestionPort:
    adapter = getattr(request.app.state, "ugc_review_video_ingestion", None)
    if adapter is None:
        raise AppError(
            "UGC_REVIEW_DIRECT_UPLOAD_UNAVAILABLE",
            "Direct video ingestion is not configured; upload the asset first.",
            status_code=501,
        )
    return cast(UGCVideoIngestionPort, adapter)
