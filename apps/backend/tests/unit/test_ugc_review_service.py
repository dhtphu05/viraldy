from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from io import BytesIO
from typing import cast
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from viraldy.modules.ugc_review.repository import InMemoryUGCReviewRepository
from viraldy.modules.ugc_review.schemas import (
    CreateUGCReviewForm,
    CreateUGCReviewRevisionForm,
    RecordUGCRecommendationActionRequest,
    ReviewEvidence,
    UGCRecommendation,
    UGCReviewResultResponse,
)
from viraldy.modules.ugc_review.service import (
    UGCAssetVersion,
    UGCProcessingJob,
    UGCReviewService,
    UGCVideoUpload,
)
from viraldy.shared.errors.base import AppError, ConflictError, NotFoundError


class FakeSession:
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1


class FakeAssets:
    def __init__(self, references: list[UGCAssetVersion]) -> None:
        self.references = {item.asset_version_id: item for item in references}

    async def get_version(
        self,
        workspace_id: UUID,
        asset_version_id: UUID,
    ) -> UGCAssetVersion | None:
        item = self.references.get(asset_version_id)
        if item is None or item.workspace_id != workspace_id:
            return None
        return item


class FakeJobs:
    def __init__(self) -> None:
        self.jobs: dict[UUID, UGCProcessingJob] = {}
        self.requested_inputs: list[dict[str, object]] = []
        self.idempotent_jobs: dict[tuple[UUID, str], UGCProcessingJob] = {}

    async def request(
        self,
        *,
        workspace_id: UUID,
        subject_id: UUID,
        input_json: dict[str, object],
        idempotency_key: str | None,
    ) -> UGCProcessingJob:
        if idempotency_key is not None:
            existing = self.idempotent_jobs.get((workspace_id, idempotency_key))
            if existing is not None:
                return existing
        self.requested_inputs.append(input_json)
        job = UGCProcessingJob(
            id=uuid4(),
            workspace_id=workspace_id,
            job_type="ugc_review_v1",
            status="queued",
            progress=0,
            stage="queued",
            input_json=input_json,
            error_code=None,
            error_message=None,
        )
        self.jobs[job.id] = job
        if idempotency_key is not None:
            self.idempotent_jobs[(workspace_id, idempotency_key)] = job
        return job

    async def get_idempotent(
        self,
        workspace_id: UUID,
        idempotency_key: str | None,
    ) -> UGCProcessingJob | None:
        if idempotency_key is None:
            return None
        return self.idempotent_jobs.get((workspace_id, idempotency_key))

    async def get(self, workspace_id: UUID, review_id: UUID) -> UGCProcessingJob | None:
        job = self.jobs.get(review_id)
        if job is None or job.workspace_id != workspace_id:
            return None
        return job


class FakeIngestion:
    def __init__(self, asset: UGCAssetVersion) -> None:
        self.asset = asset
        self.initial_calls = 0
        self.revision_calls = 0

    async def ingest_initial(
        self,
        workspace_id: UUID,
        actor_user_id: UUID,
        upload: UGCVideoUpload,
    ) -> UGCAssetVersion:
        _ = workspace_id, actor_user_id, upload
        self.initial_calls += 1
        return self.asset

    async def ingest_revision(
        self,
        workspace_id: UUID,
        actor_user_id: UUID,
        parent_asset_id: UUID,
        upload: UGCVideoUpload,
    ) -> UGCAssetVersion:
        _ = workspace_id, actor_user_id, upload
        assert parent_asset_id == self.asset.asset_id
        self.revision_calls += 1
        return self.asset


@pytest.mark.asyncio
async def test_create_review_uses_processing_job_identity_and_maps_context() -> None:
    workspace_id = uuid4()
    asset = UGCAssetVersion(
        workspace_id=workspace_id,
        asset_id=uuid4(),
        asset_version_id=uuid4(),
    )
    jobs = FakeJobs()
    service = _service(workspace_id, [asset], jobs)

    response = await service.create(
        workspace_id,
        CreateUGCReviewForm(
            asset_id=asset.asset_id,
            asset_version_id=asset.asset_version_id,
            commerce_domain="pod_personalization",
            product_name="Custom mug",
        ),
        idempotency_key="review-1",
    )

    assert response.review_id in jobs.jobs
    assert response.asset_id == asset.asset_id
    assert response.asset_version_id == asset.asset_version_id
    assert response.status == "queued"
    assert response.mode == "ugc_review_v1"
    assert jobs.requested_inputs == [
        {
            "mode": "ugc_review_v1",
            "asset_id": str(asset.asset_id),
            "asset_version_id": str(asset.asset_version_id),
            "request_context": {
                "market": "US",
                "platform": "tiktok_shop",
                "commerce_domain": "pod_personalization",
                "intended_use": "unknown",
                "product_name": "Custom mug",
                "product_category": None,
                "exact_variant_or_sku": None,
                "product_description": None,
                "current_offer": None,
                "verified_shipping_language": None,
                "approved_personalization": None,
                "physical_sample_available": None,
                "creator_brief": None,
                "material_connection": "unknown",
                "seller_notes": None,
            },
        }
    ]


@pytest.mark.asyncio
async def test_create_rejects_idempotency_key_reuse_for_a_different_asset() -> None:
    workspace_id = uuid4()
    first = UGCAssetVersion(workspace_id, uuid4(), uuid4())
    second = UGCAssetVersion(workspace_id, uuid4(), uuid4())
    jobs = FakeJobs()
    service = _service(workspace_id, [first, second], jobs)

    await service.create(
        workspace_id,
        CreateUGCReviewForm(asset_id=first.asset_id, asset_version_id=first.asset_version_id),
        idempotency_key="same-key",
    )

    with pytest.raises(ConflictError) as error:
        await service.create(
            workspace_id,
            CreateUGCReviewForm(
                asset_id=second.asset_id,
                asset_version_id=second.asset_version_id,
            ),
            idempotency_key="same-key",
        )

    assert error.value.code == "UGC_REVIEW_IDEMPOTENCY_CONFLICT"


@pytest.mark.asyncio
async def test_direct_upload_retry_reuses_persisted_asset_without_ingesting_again() -> None:
    workspace_id = uuid4()
    actor_user_id = uuid4()
    asset = UGCAssetVersion(workspace_id, uuid4(), uuid4())
    jobs = FakeJobs()
    ingestion = FakeIngestion(asset)
    service = _service(workspace_id, [], jobs)
    form = CreateUGCReviewForm(product_name="Custom mug")

    first = await service.create_from_video(
        workspace_id,
        actor_user_id,
        form,
        UGCVideoUpload("draft.mp4", "video/mp4", BytesIO(b"first")),
        ingestion,
        idempotency_key="direct-key",
    )
    retried = await service.create_from_video(
        workspace_id,
        actor_user_id,
        form,
        UGCVideoUpload("draft.mp4", "video/mp4", BytesIO(b"retry")),
        ingestion,
        idempotency_key="direct-key",
    )

    assert retried == first
    assert retried.asset_id == asset.asset_id
    assert retried.asset_version_id == asset.asset_version_id
    assert ingestion.initial_calls == 1


@pytest.mark.asyncio
async def test_status_404_does_not_cross_workspace_boundary() -> None:
    workspace_id = uuid4()
    service = _service(workspace_id, [], FakeJobs())

    with pytest.raises(NotFoundError) as error:
        await service.get_status(workspace_id, uuid4())

    assert error.value.code == "UGC_REVIEW_NOT_FOUND"


@pytest.mark.asyncio
async def test_poll_and_get_completed_result_preserve_durable_asset_identity() -> None:
    workspace_id = uuid4()
    asset_id = uuid4()
    asset_version_id = uuid4()
    jobs = FakeJobs()
    repository = InMemoryUGCReviewRepository()
    service = _service(workspace_id, [], jobs, repository)
    job = await jobs.request(
        workspace_id=workspace_id,
        subject_id=asset_version_id,
        input_json={},
        idempotency_key=None,
    )
    jobs.jobs[job.id] = replace(
        job,
        status="completed",
        progress=100,
        stage="completed",
    )
    expected = _result(job.id, asset_id, asset_version_id)
    await repository.persist_response(workspace_id, expected, request_context={})

    status = await service.get_status(workspace_id, job.id)
    result = await service.get_result(workspace_id, job.id)

    assert status.status == "completed"
    assert status.progress == 100
    assert status.stage == "completed"
    assert result == expected
    assert result.asset_id == asset_id
    assert result.asset_version_id == asset_version_id


@pytest.mark.asyncio
async def test_action_persists_api_payload_mapping() -> None:
    workspace_id = uuid4()
    asset_id = uuid4()
    asset_version_id = uuid4()
    jobs = FakeJobs()
    repository = InMemoryUGCReviewRepository()
    service = _service(
        workspace_id,
        [
            UGCAssetVersion(
                workspace_id=workspace_id,
                asset_id=asset_id,
                asset_version_id=asset_version_id,
            )
        ],
        jobs,
        repository,
    )
    job = await jobs.request(
        workspace_id=workspace_id,
        subject_id=asset_version_id,
        input_json={},
        idempotency_key=None,
    )
    result = _result(job.id, asset_id, asset_version_id)
    await repository.persist_response(workspace_id, result, request_context={})

    event = await service.record_action(
        workspace_id,
        job.id,
        "rec-demo",
        RecordUGCRecommendationActionRequest(
            action="not_applicable",
            reason="Different product format",
        ),
    )

    assert event.review_id == job.id
    assert event.recommendation_id == "rec-demo"
    assert event.action == "not_applicable"
    assert event.reason == "Different product format"
    assert repository.events[0].seller_action == "not_applicable"


@pytest.mark.asyncio
async def test_service_rejects_invalid_constructed_action() -> None:
    workspace_id = uuid4()
    service = _service(workspace_id, [], FakeJobs())
    invalid = RecordUGCRecommendationActionRequest.model_construct(action="blocked", reason=None)

    with pytest.raises(AppError) as error:
        await service.record_action(workspace_id, uuid4(), "rec", invalid)

    assert error.value.code == "UGC_REVIEW_ACTION_INVALID"


@pytest.mark.asyncio
async def test_revision_inherits_context_and_records_parent_child_relation() -> None:
    workspace_id = uuid4()
    asset_id = uuid4()
    parent_version_id = uuid4()
    child_version_id = uuid4()
    jobs = FakeJobs()
    repository = InMemoryUGCReviewRepository()
    assets = [
        UGCAssetVersion(workspace_id, asset_id, parent_version_id),
        UGCAssetVersion(workspace_id, asset_id, child_version_id),
    ]
    service = _service(workspace_id, assets, jobs, repository)
    parent_job = await jobs.request(
        workspace_id=workspace_id,
        subject_id=parent_version_id,
        input_json={},
        idempotency_key=None,
    )
    parent_result = _result(parent_job.id, asset_id, parent_version_id)
    await repository.persist_response(
        workspace_id,
        parent_result,
        request_context={"market": "US", "creator_brief": "Show the exact red variant."},
    )
    jobs.jobs[parent_job.id] = replace(parent_job, status="completed", progress=100)

    response = await service.create_revision(
        workspace_id,
        parent_job.id,
        CreateUGCReviewRevisionForm(asset_version_id=child_version_id),
        idempotency_key="revision-1",
    )
    retried = await service.create_revision(
        workspace_id,
        parent_job.id,
        CreateUGCReviewRevisionForm(asset_version_id=child_version_id),
        idempotency_key="revision-1",
    )

    assert response.parent_review_id == parent_job.id
    assert response.asset_id == asset_id
    assert response.asset_version_id == child_version_id
    assert retried.review_id == response.review_id
    assert jobs.requested_inputs[-1] == {
        "mode": "ugc_review_v1",
        "asset_id": str(asset_id),
        "asset_version_id": str(child_version_id),
        "request_context": {
            "market": "US",
            "creator_brief": "Show the exact red variant.",
        },
        "parent_review_id": str(parent_job.id),
    }
    relation = repository.revisions[0]
    assert len(repository.revisions) == 1
    assert relation.parent_processing_job_id == parent_job.id
    assert relation.child_processing_job_id == response.review_id


@pytest.mark.asyncio
async def test_direct_revision_retry_reuses_persisted_version_without_ingesting_again() -> None:
    workspace_id = uuid4()
    actor_user_id = uuid4()
    asset_id = uuid4()
    parent_version_id = uuid4()
    revision = UGCAssetVersion(workspace_id, asset_id, uuid4())
    jobs = FakeJobs()
    repository = InMemoryUGCReviewRepository()
    service = _service(workspace_id, [], jobs, repository)
    parent_job = await jobs.request(
        workspace_id=workspace_id,
        subject_id=parent_version_id,
        input_json={},
        idempotency_key=None,
    )
    await repository.persist_response(
        workspace_id,
        _result(parent_job.id, asset_id, parent_version_id),
        request_context={"market": "US"},
    )
    jobs.jobs[parent_job.id] = replace(parent_job, status="completed", progress=100)
    ingestion = FakeIngestion(revision)

    first = await service.create_revision_from_video(
        workspace_id,
        parent_job.id,
        actor_user_id,
        UGCVideoUpload("revision.mp4", "video/mp4", BytesIO(b"first")),
        ingestion,
        idempotency_key="direct-revision-key",
    )
    retried = await service.create_revision_from_video(
        workspace_id,
        parent_job.id,
        actor_user_id,
        UGCVideoUpload("revision.mp4", "video/mp4", BytesIO(b"retry")),
        ingestion,
        idempotency_key="direct-revision-key",
    )

    assert retried == first
    assert retried.asset_version_id == revision.asset_version_id
    assert ingestion.revision_calls == 1
    assert len(repository.revisions) == 1


def _service(
    workspace_id: UUID,
    assets: list[UGCAssetVersion],
    jobs: FakeJobs,
    repository: InMemoryUGCReviewRepository | None = None,
) -> UGCReviewService:
    _ = workspace_id
    return UGCReviewService(
        cast(AsyncSession, FakeSession()),
        repository=repository or InMemoryUGCReviewRepository(),
        assets=FakeAssets(assets),
        jobs=jobs,
    )


def _result(
    review_id: UUID,
    asset_id: UUID,
    asset_version_id: UUID,
) -> UGCReviewResultResponse:
    recommendation = UGCRecommendation(
        id="rec-demo",
        rule_code="UGC-DEMO-001",
        mistake_code=None,
        group="improve",
        title="Clarify the product demo",
        reason="The result is difficult to see.",
        why_it_matters="A clearer demo helps viewers understand the product.",
        owner="editor",
        fix_type="edit_existing_footage",
        instructions=["Hold the result for longer."],
        strengths_to_preserve=["Natural delivery"],
        completion_criteria=["The result is visible."],
        evidence=[
            ReviewEvidence(
                id="evidence-1",
                source="video",
                observed="The result appears briefly.",
                confidence="high",
            )
        ],
        confidence="high",
    )
    return UGCReviewResultResponse(
        review_id=str(review_id),
        asset_id=asset_id,
        asset_version_id=asset_version_id,
        status="completed",
        headline="Review complete",
        summary="One improvement is available.",
        recommended_next_action="revise",
        overall_confidence="high",
        strengths_to_keep=["Natural delivery"],
        fix_first=[],
        improvements=[recommendation],
        confirmations=[],
        creator_revision_message="Keep the natural delivery and hold the result longer.",
        policy_pack_version="v1",
        analysis_provenance={"pipeline": "test"},
        created_at=datetime.now(UTC).isoformat(),
    )
