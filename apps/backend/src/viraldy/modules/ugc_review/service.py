from __future__ import annotations

from dataclasses import dataclass
from typing import BinaryIO, Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from viraldy.modules.assets.public import AssetQueries
from viraldy.modules.jobs.public import (
    JobResponse,
    get_existing_idempotent_job,
    get_processing_job,
    request_mvp_job,
)
from viraldy.modules.ugc_review.comparison import compare_review_results
from viraldy.modules.ugc_review.models import (
    UGCReviewFindingModel,
    UGCReviewRecommendationEventModel,
    UGCReviewResultModel,
    UGCReviewRevisionModel,
)
from viraldy.modules.ugc_review.repository import (
    UGCReviewRepository,
    result_response_from_model,
)
from viraldy.modules.ugc_review.schemas import (
    CreateUGCReviewForm,
    CreateUGCReviewRevisionForm,
    RecordUGCRecommendationActionRequest,
    UGCRecommendationActionEventResponse,
    UGCReviewCreateResponse,
    UGCReviewJobStatus,
    UGCReviewResultResponse,
    UGCReviewRevisionResponse,
    UGCReviewStatusResponse,
    UGCRevisionComparisonResponse,
)
from viraldy.shared.errors.base import AppError, ConflictError, NotFoundError

UGC_REVIEW_JOB_TYPE = "ugc_review_v1"
_VALID_ACTIONS = {
    "accepted",
    "ignored",
    "not_applicable",
    "sent_to_creator",
    "marked_completed",
}


@dataclass(frozen=True, slots=True)
class UGCAssetVersion:
    workspace_id: UUID
    asset_id: UUID
    asset_version_id: UUID
    validation_status: str = "uploaded"


@dataclass(frozen=True, slots=True)
class UGCProcessingJob:
    id: UUID
    workspace_id: UUID
    job_type: str
    status: str
    progress: int
    stage: str | None
    input_json: dict[str, object]
    error_code: str | None
    error_message: str | None


@dataclass(frozen=True, slots=True)
class UGCVideoUpload:
    filename: str
    content_type: str
    file: BinaryIO


class UGCAssetVersionPort(Protocol):
    async def get_version(
        self,
        workspace_id: UUID,
        asset_version_id: UUID,
    ) -> UGCAssetVersion | None: ...


class UGCProcessingJobPort(Protocol):
    async def request(
        self,
        *,
        workspace_id: UUID,
        subject_id: UUID,
        input_json: dict[str, object],
        idempotency_key: str | None,
    ) -> UGCProcessingJob: ...

    async def get_idempotent(
        self,
        workspace_id: UUID,
        idempotency_key: str | None,
    ) -> UGCProcessingJob | None: ...

    async def get(self, workspace_id: UUID, review_id: UUID) -> UGCProcessingJob | None: ...


class UGCVideoIngestionPort(Protocol):
    """Adapter seam for callers that submit a video instead of an uploaded version."""

    async def ingest_initial(
        self,
        workspace_id: UUID,
        actor_user_id: UUID,
        upload: UGCVideoUpload,
    ) -> UGCAssetVersion: ...

    async def ingest_revision(
        self,
        workspace_id: UUID,
        actor_user_id: UUID,
        parent_asset_id: UUID,
        upload: UGCVideoUpload,
    ) -> UGCAssetVersion: ...


class UGCReviewRepositoryPort(Protocol):
    async def get_result(
        self,
        workspace_id: UUID,
        processing_job_id: UUID,
    ) -> UGCReviewResultModel | None: ...

    async def get_finding(
        self,
        workspace_id: UUID,
        processing_job_id: UUID,
        recommendation_id: str,
    ) -> UGCReviewFindingModel | None: ...

    async def record_action(
        self,
        *,
        finding: UGCReviewFindingModel,
        seller_action: str,
        reason: str | None,
    ) -> UGCReviewRecommendationEventModel: ...

    async def create_revision(
        self,
        *,
        workspace_id: UUID,
        parent_processing_job_id: UUID,
        child_processing_job_id: UUID,
        parent_asset_version_id: UUID,
        child_asset_version_id: UUID,
    ) -> UGCReviewRevisionModel: ...

    async def get_latest_revision(
        self,
        workspace_id: UUID,
        parent_processing_job_id: UUID,
    ) -> UGCReviewRevisionModel | None: ...

    async def persist_comparison(
        self,
        workspace_id: UUID,
        comparison: UGCRevisionComparisonResponse,
    ) -> object: ...


class UGCReviewService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        repository: UGCReviewRepositoryPort | None = None,
        assets: UGCAssetVersionPort | None = None,
        jobs: UGCProcessingJobPort | None = None,
    ) -> None:
        self._session = session
        self._repository = repository or UGCReviewRepository(session)
        self._assets = assets or AssetVersionAdapter(session)
        self._jobs = jobs or ProcessingJobAdapter(session)

    async def create(
        self,
        workspace_id: UUID,
        data: CreateUGCReviewForm,
        idempotency_key: str | None,
    ) -> UGCReviewCreateResponse:
        if data.asset_id is None or data.asset_version_id is None:
            raise AppError(
                "UGC_REVIEW_VIDEO_REQUIRED",
                "Provide an uploaded asset version or a video file.",
            )
        asset = await self._require_asset_version(workspace_id, data.asset_version_id)
        if asset.asset_id != data.asset_id:
            raise AppError(
                "UGC_REVIEW_ASSET_VERSION_MISMATCH",
                "Asset version must belong to the submitted asset.",
            )
        return await self._request_review(
            workspace_id=workspace_id,
            asset=asset,
            request_context=data.to_context().model_dump(mode="json"),
            idempotency_key=idempotency_key,
        )

    async def create_from_video(
        self,
        workspace_id: UUID,
        actor_user_id: UUID,
        data: CreateUGCReviewForm,
        upload: UGCVideoUpload,
        ingestion: UGCVideoIngestionPort,
        idempotency_key: str | None,
    ) -> UGCReviewCreateResponse:
        if data.asset_id is not None or data.asset_version_id is not None:
            raise AppError(
                "UGC_REVIEW_VIDEO_ASSET_CONFLICT",
                "Submit either a video file or an existing asset version, not both.",
            )
        request_context = data.to_context().model_dump(mode="json")
        existing = await self._jobs.get_idempotent(workspace_id, idempotency_key)
        if existing is not None:
            asset_id, asset_version_id = _require_direct_retry_input(
                existing,
                request_context=request_context,
            )
            return UGCReviewCreateResponse(
                review_id=existing.id,
                status="queued",
                mode=UGC_REVIEW_JOB_TYPE,
                asset_id=asset_id,
                asset_version_id=asset_version_id,
            )
        asset = await ingestion.ingest_initial(workspace_id, actor_user_id, upload)
        return await self._request_review(
            workspace_id=workspace_id,
            asset=asset,
            request_context=request_context,
            idempotency_key=idempotency_key,
        )

    async def get_status(
        self,
        workspace_id: UUID,
        review_id: UUID,
    ) -> UGCReviewStatusResponse:
        job = await self._require_job(workspace_id, review_id)
        return UGCReviewStatusResponse(
            review_id=job.id,
            status=_public_job_status(job.status),
            progress=job.progress,
            stage=job.stage,
            error_code=job.error_code,
            error_message=job.error_message,
        )

    async def get_result(
        self,
        workspace_id: UUID,
        review_id: UUID,
    ) -> UGCReviewResultResponse:
        await self._require_job(workspace_id, review_id)
        result = await self._repository.get_result(workspace_id, review_id)
        if result is None:
            raise ConflictError(
                "UGC_REVIEW_RESULT_NOT_READY",
                "The UGC review result is not ready yet.",
            )
        return result_response_from_model(result)

    async def record_action(
        self,
        workspace_id: UUID,
        review_id: UUID,
        recommendation_id: str,
        data: RecordUGCRecommendationActionRequest,
    ) -> UGCRecommendationActionEventResponse:
        if data.action not in _VALID_ACTIONS:
            raise AppError(
                "UGC_REVIEW_ACTION_INVALID",
                "Recommendation action is not supported.",
            )
        await self._require_job(workspace_id, review_id)
        finding = await self._repository.get_finding(
            workspace_id,
            review_id,
            recommendation_id,
        )
        if finding is None:
            raise NotFoundError(
                "UGC_REVIEW_RECOMMENDATION_NOT_FOUND",
                "Recommendation was not found.",
            )
        event = await self._repository.record_action(
            finding=finding,
            seller_action=data.action,
            reason=data.reason,
        )
        await self._session.commit()
        return UGCRecommendationActionEventResponse(
            id=event.id,
            review_id=review_id,
            recommendation_id=finding.recommendation_id,
            action=data.action,
            reason=event.reason,
            created_at=event.created_at.isoformat(),
        )

    async def create_revision(
        self,
        workspace_id: UUID,
        parent_review_id: UUID,
        data: CreateUGCReviewRevisionForm,
        idempotency_key: str | None,
    ) -> UGCReviewRevisionResponse:
        if data.asset_version_id is None:
            raise AppError(
                "UGC_REVIEW_REVISION_VIDEO_REQUIRED",
                "Provide an uploaded revision asset version or a video file.",
            )
        parent = await self._require_completed_result(workspace_id, parent_review_id)
        asset = await self._require_asset_version(workspace_id, data.asset_version_id)
        return await self._request_revision(
            workspace_id=workspace_id,
            parent_review_id=parent_review_id,
            parent=parent,
            asset=asset,
            idempotency_key=idempotency_key,
        )

    async def create_revision_from_video(
        self,
        workspace_id: UUID,
        parent_review_id: UUID,
        actor_user_id: UUID,
        upload: UGCVideoUpload,
        ingestion: UGCVideoIngestionPort,
        idempotency_key: str | None,
    ) -> UGCReviewRevisionResponse:
        parent = await self._require_completed_result(workspace_id, parent_review_id)
        if parent.asset_id is None:
            raise AppError(
                "UGC_REVIEW_RESULT_ASSET_MISSING",
                "The parent review does not retain its asset identity.",
                status_code=500,
            )
        existing = await self._jobs.get_idempotent(workspace_id, idempotency_key)
        if existing is not None:
            asset_id, asset_version_id = _require_direct_retry_input(
                existing,
                request_context=dict(parent.request_context),
                parent_review_id=parent_review_id,
            )
            if parent.asset_version_id is None or asset_id != parent.asset_id:
                raise ConflictError(
                    "UGC_REVIEW_IDEMPOTENCY_CONFLICT",
                    "Idempotency key was already used for a different UGC review request.",
                )
            await self._repository.create_revision(
                workspace_id=workspace_id,
                parent_processing_job_id=parent_review_id,
                child_processing_job_id=existing.id,
                parent_asset_version_id=parent.asset_version_id,
                child_asset_version_id=asset_version_id,
            )
            await self._session.commit()
            return UGCReviewRevisionResponse(
                review_id=existing.id,
                parent_review_id=parent_review_id,
                status="queued",
                mode=UGC_REVIEW_JOB_TYPE,
                asset_id=asset_id,
                asset_version_id=asset_version_id,
            )
        asset = await ingestion.ingest_revision(
            workspace_id,
            actor_user_id,
            parent.asset_id,
            upload,
        )
        return await self._request_revision(
            workspace_id=workspace_id,
            parent_review_id=parent_review_id,
            parent=parent,
            asset=asset,
            idempotency_key=idempotency_key,
        )

    async def get_latest_comparison(
        self,
        workspace_id: UUID,
        parent_review_id: UUID,
    ) -> UGCRevisionComparisonResponse:
        await self._require_job(workspace_id, parent_review_id)
        relation = await self._repository.get_latest_revision(workspace_id, parent_review_id)
        if relation is None:
            raise NotFoundError(
                "UGC_REVIEW_REVISION_NOT_FOUND",
                "No revision exists for this review.",
            )
        parent = await self._require_completed_result(workspace_id, parent_review_id)
        revision = await self._require_completed_result(
            workspace_id,
            relation.child_processing_job_id,
        )
        comparison = compare_review_results(
            result_response_from_model(parent),
            result_response_from_model(revision),
        )
        await self._repository.persist_comparison(workspace_id, comparison)
        await self._session.commit()
        return comparison

    async def _request_review(
        self,
        *,
        workspace_id: UUID,
        asset: UGCAssetVersion,
        request_context: dict[str, object],
        idempotency_key: str | None,
    ) -> UGCReviewCreateResponse:
        if asset.workspace_id != workspace_id:
            raise NotFoundError("ASSET_VERSION_NOT_FOUND", "Asset version was not found.")
        input_json: dict[str, object] = {
            "mode": UGC_REVIEW_JOB_TYPE,
            "asset_id": str(asset.asset_id),
            "asset_version_id": str(asset.asset_version_id),
            "request_context": request_context,
        }
        job = await self._jobs.request(
            workspace_id=workspace_id,
            subject_id=asset.asset_version_id,
            input_json=input_json,
            idempotency_key=idempotency_key,
        )
        _require_matching_job_input(job, input_json)
        return UGCReviewCreateResponse(
            review_id=job.id,
            status="queued",
            mode=UGC_REVIEW_JOB_TYPE,
            asset_id=asset.asset_id,
            asset_version_id=asset.asset_version_id,
        )

    async def _request_revision(
        self,
        *,
        workspace_id: UUID,
        parent_review_id: UUID,
        parent: UGCReviewResultModel,
        asset: UGCAssetVersion,
        idempotency_key: str | None,
    ) -> UGCReviewRevisionResponse:
        if asset.workspace_id != workspace_id:
            raise NotFoundError("ASSET_VERSION_NOT_FOUND", "Asset version was not found.")
        if parent.asset_id is None or parent.asset_version_id is None:
            raise AppError(
                "UGC_REVIEW_RESULT_ASSET_MISSING",
                "The parent review does not retain its asset identity.",
                status_code=500,
            )
        if asset.asset_id != parent.asset_id:
            raise AppError(
                "UGC_REVIEW_REVISION_ASSET_MISMATCH",
                "Revision asset version must belong to the parent review asset.",
            )
        if asset.asset_version_id == parent.asset_version_id:
            raise ConflictError(
                "UGC_REVIEW_REVISION_VERSION_UNCHANGED",
                "Revision must use a new immutable asset version.",
            )
        input_json: dict[str, object] = {
            "mode": UGC_REVIEW_JOB_TYPE,
            "asset_id": str(asset.asset_id),
            "asset_version_id": str(asset.asset_version_id),
            "request_context": dict(parent.request_context),
            "parent_review_id": str(parent_review_id),
        }
        job = await self._jobs.request(
            workspace_id=workspace_id,
            subject_id=asset.asset_version_id,
            input_json=input_json,
            idempotency_key=idempotency_key,
        )
        _require_matching_job_input(job, input_json)
        await self._repository.create_revision(
            workspace_id=workspace_id,
            parent_processing_job_id=parent_review_id,
            child_processing_job_id=job.id,
            parent_asset_version_id=parent.asset_version_id,
            child_asset_version_id=asset.asset_version_id,
        )
        await self._session.commit()
        return UGCReviewRevisionResponse(
            review_id=job.id,
            parent_review_id=parent_review_id,
            status="queued",
            mode=UGC_REVIEW_JOB_TYPE,
            asset_id=asset.asset_id,
            asset_version_id=asset.asset_version_id,
        )

    async def _require_asset_version(
        self,
        workspace_id: UUID,
        asset_version_id: UUID,
    ) -> UGCAssetVersion:
        asset = await self._assets.get_version(workspace_id, asset_version_id)
        if asset is None:
            raise NotFoundError("ASSET_VERSION_NOT_FOUND", "Asset version was not found.")
        if asset.validation_status not in {"uploaded", "valid"}:
            raise AppError(
                "ASSET_VERSION_NOT_READY",
                "Asset version must finish uploading before review.",
            )
        return asset

    async def _require_job(self, workspace_id: UUID, review_id: UUID) -> UGCProcessingJob:
        job = await self._jobs.get(workspace_id, review_id)
        if job is None or job.job_type != UGC_REVIEW_JOB_TYPE:
            raise NotFoundError("UGC_REVIEW_NOT_FOUND", "UGC review was not found.")
        return job

    async def _require_completed_result(
        self,
        workspace_id: UUID,
        review_id: UUID,
    ) -> UGCReviewResultModel:
        await self._require_job(workspace_id, review_id)
        result = await self._repository.get_result(workspace_id, review_id)
        if result is None:
            raise ConflictError(
                "UGC_REVIEW_RESULT_NOT_READY",
                "The UGC review result is not ready yet.",
            )
        return result


class AssetVersionAdapter:
    def __init__(self, session: AsyncSession) -> None:
        self._queries = AssetQueries(session)

    async def get_version(
        self,
        workspace_id: UUID,
        asset_version_id: UUID,
    ) -> UGCAssetVersion | None:
        reference = await self._queries.get_version_reference(workspace_id, asset_version_id)
        if reference is None:
            return None
        return UGCAssetVersion(
            workspace_id=reference.workspace_id,
            asset_id=reference.asset_id,
            asset_version_id=reference.asset_version_id,
            validation_status=reference.validation_status,
        )


class ProcessingJobAdapter:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def request(
        self,
        *,
        workspace_id: UUID,
        subject_id: UUID,
        input_json: dict[str, object],
        idempotency_key: str | None,
    ) -> UGCProcessingJob:
        job = await request_mvp_job(
            self._session,
            workspace_id,
            "asset_version",
            subject_id,
            UGC_REVIEW_JOB_TYPE,
            input_json,
            idempotency_key,
        )
        return _job_snapshot(job)

    async def get_idempotent(
        self,
        workspace_id: UUID,
        idempotency_key: str | None,
    ) -> UGCProcessingJob | None:
        job = await get_existing_idempotent_job(
            self._session,
            workspace_id,
            UGC_REVIEW_JOB_TYPE,
            idempotency_key,
        )
        return _job_snapshot(job) if job is not None else None

    async def get(self, workspace_id: UUID, review_id: UUID) -> UGCProcessingJob | None:
        job = await get_processing_job(self._session, workspace_id, review_id)
        return _job_snapshot(job) if job is not None else None


def _job_snapshot(job: JobResponse) -> UGCProcessingJob:
    return UGCProcessingJob(
        id=job.id,
        workspace_id=job.workspace_id,
        job_type=job.job_type,
        status=job.status,
        progress=job.progress,
        stage=job.stage,
        input_json=dict(job.input_json),
        error_code=job.error_code,
        error_message=job.error_message,
    )


def _require_matching_job_input(
    job: UGCProcessingJob,
    expected_input: dict[str, object],
) -> None:
    if job.job_type != UGC_REVIEW_JOB_TYPE or job.input_json != expected_input:
        raise ConflictError(
            "UGC_REVIEW_IDEMPOTENCY_CONFLICT",
            "Idempotency key was already used for a different UGC review request.",
        )


def _require_direct_retry_input(
    job: UGCProcessingJob,
    *,
    request_context: dict[str, object],
    parent_review_id: UUID | None = None,
) -> tuple[UUID, UUID]:
    expected_parent = str(parent_review_id) if parent_review_id is not None else None
    actual_parent = job.input_json.get("parent_review_id")
    if (
        job.job_type != UGC_REVIEW_JOB_TYPE
        or job.input_json.get("mode") != UGC_REVIEW_JOB_TYPE
        or job.input_json.get("request_context") != request_context
        or actual_parent != expected_parent
    ):
        raise ConflictError(
            "UGC_REVIEW_IDEMPOTENCY_CONFLICT",
            "Idempotency key was already used for a different UGC review request.",
        )
    try:
        return (
            UUID(str(job.input_json["asset_id"])),
            UUID(str(job.input_json["asset_version_id"])),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise AppError(
            "UGC_REVIEW_JOB_INPUT_INVALID",
            "The existing UGC review job has invalid asset identity.",
            status_code=500,
        ) from exc


def _public_job_status(status: str) -> UGCReviewJobStatus:
    mapping: dict[str, UGCReviewJobStatus] = {
        "pending": "queued",
        "queued": "queued",
        "running": "running",
        "processing": "running",
        "completed": "completed",
        "succeeded": "completed",
        "failed": "failed",
    }
    return mapping.get(status, "running")


__all__ = [
    "UGCAssetVersion",
    "UGCProcessingJob",
    "UGCReviewService",
    "UGCVideoIngestionPort",
    "UGCVideoUpload",
    "UGC_REVIEW_JOB_TYPE",
]
