from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import cast
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from viraldy.modules.domain_intelligence.public import UGCReviewResult
from viraldy.modules.ugc_review.models import (
    UGCReviewComparisonModel,
    UGCReviewFindingModel,
    UGCReviewRecommendationEventModel,
    UGCReviewResultModel,
    UGCReviewRevisionModel,
)
from viraldy.modules.ugc_review.schemas import (
    UGCRecommendation,
    UGCReviewResultResponse,
    UGCRevisionComparisonResponse,
)
from viraldy.shared.errors.base import ConflictError

logger = logging.getLogger(__name__)


class UGCReviewRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def persist_result(
        self,
        *,
        workspace_id: UUID,
        processing_job_id: UUID,
        asset_id: UUID,
        asset_version_id: UUID,
        request_context: dict[str, object],
        result: UGCReviewResult,
    ) -> UGCReviewResultModel:
        existing = await self.get_result(workspace_id, processing_job_id)
        if existing is not None:
            return existing
        response = UGCReviewResultResponse(
            **result.model_dump(),
            asset_id=asset_id,
            asset_version_id=asset_version_id,
        )
        result_model, findings = map_result_to_models(
            workspace_id=workspace_id,
            processing_job_id=processing_job_id,
            request_context=request_context,
            response=response,
        )
        self._session.add(result_model)
        self._session.add_all(findings)
        await self._session.flush()
        return result_model

    async def get_result(
        self,
        workspace_id: UUID,
        processing_job_id: UUID,
    ) -> UGCReviewResultModel | None:
        return cast(
            UGCReviewResultModel | None,
            await self._session.scalar(
                select(UGCReviewResultModel).where(
                    UGCReviewResultModel.workspace_id == workspace_id,
                    UGCReviewResultModel.processing_job_id == processing_job_id,
                )
            ),
        )

    async def get_finding(
        self,
        workspace_id: UUID,
        processing_job_id: UUID,
        recommendation_id: str,
    ) -> UGCReviewFindingModel | None:
        return cast(
            UGCReviewFindingModel | None,
            await self._session.scalar(
                select(UGCReviewFindingModel).where(
                    UGCReviewFindingModel.workspace_id == workspace_id,
                    UGCReviewFindingModel.processing_job_id == processing_job_id,
                    UGCReviewFindingModel.recommendation_id == recommendation_id,
                )
            ),
        )

    async def record_action(
        self,
        *,
        finding: UGCReviewFindingModel,
        seller_action: str,
        reason: str | None,
    ) -> UGCReviewRecommendationEventModel:
        event = UGCReviewRecommendationEventModel(
            workspace_id=finding.workspace_id,
            processing_job_id=finding.processing_job_id,
            finding_id=finding.id,
            seller_action=seller_action,
            reason=reason,
        )
        self._session.add(event)
        await self._session.flush()
        return event

    async def create_revision(
        self,
        *,
        workspace_id: UUID,
        parent_processing_job_id: UUID,
        child_processing_job_id: UUID,
        parent_asset_version_id: UUID,
        child_asset_version_id: UUID,
    ) -> UGCReviewRevisionModel:
        existing = await self._session.scalar(
            select(UGCReviewRevisionModel).where(
                UGCReviewRevisionModel.child_processing_job_id == child_processing_job_id
            )
        )
        if existing is not None:
            return _require_matching_revision(
                existing,
                workspace_id=workspace_id,
                parent_processing_job_id=parent_processing_job_id,
                parent_asset_version_id=parent_asset_version_id,
                child_asset_version_id=child_asset_version_id,
            )
        relation = UGCReviewRevisionModel(
            workspace_id=workspace_id,
            parent_processing_job_id=parent_processing_job_id,
            child_processing_job_id=child_processing_job_id,
            parent_asset_version_id=parent_asset_version_id,
            child_asset_version_id=child_asset_version_id,
        )
        self._session.add(relation)
        try:
            await self._session.flush()
        except IntegrityError:
            # The processing-job request is committed before lineage is written.
            # A concurrent retry can therefore win the unique child-job insert.
            await self._session.rollback()
            concurrent = await self._session.scalar(
                select(UGCReviewRevisionModel).where(
                    UGCReviewRevisionModel.child_processing_job_id
                    == child_processing_job_id
                )
            )
            if concurrent is None:
                raise
            return _require_matching_revision(
                concurrent,
                workspace_id=workspace_id,
                parent_processing_job_id=parent_processing_job_id,
                parent_asset_version_id=parent_asset_version_id,
                child_asset_version_id=child_asset_version_id,
            )
        return relation

    async def get_latest_revision(
        self,
        workspace_id: UUID,
        parent_processing_job_id: UUID,
    ) -> UGCReviewRevisionModel | None:
        return cast(
            UGCReviewRevisionModel | None,
            await self._session.scalar(
                select(UGCReviewRevisionModel)
                .where(
                    UGCReviewRevisionModel.workspace_id == workspace_id,
                    UGCReviewRevisionModel.parent_processing_job_id == parent_processing_job_id,
                )
                .order_by(UGCReviewRevisionModel.created_at.desc())
                .limit(1)
            ),
        )

    async def persist_comparison(
        self,
        workspace_id: UUID,
        comparison: UGCRevisionComparisonResponse,
    ) -> UGCReviewComparisonModel:
        parent_id = UUID(comparison.parent_review_id)
        child_id = UUID(comparison.revision_review_id)
        existing = await self._session.scalar(
            select(UGCReviewComparisonModel).where(
                UGCReviewComparisonModel.workspace_id == workspace_id,
                UGCReviewComparisonModel.parent_processing_job_id == parent_id,
                UGCReviewComparisonModel.child_processing_job_id == child_id,
            )
        )
        if existing is not None:
            return existing
        model = comparison_to_model(workspace_id, comparison)
        self._session.add(model)
        try:
            await self._session.flush()
        except IntegrityError:
            await self._session.rollback()
            concurrent = await self._session.scalar(
                select(UGCReviewComparisonModel).where(
                    UGCReviewComparisonModel.workspace_id == workspace_id,
                    UGCReviewComparisonModel.parent_processing_job_id == parent_id,
                    UGCReviewComparisonModel.child_processing_job_id == child_id,
                )
            )
            if concurrent is None:
                raise
            return concurrent
        return model


class SyncUGCReviewRepository:
    """Worker-side persistence using the same model mapping as the async API path."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def persist_result(
        self,
        *,
        workspace_id: UUID,
        processing_job_id: UUID,
        asset_id: UUID,
        asset_version_id: UUID,
        request_context: dict[str, object],
        result: UGCReviewResult,
    ) -> UGCReviewResultModel:
        existing = self._session.scalar(
            select(UGCReviewResultModel).where(
                UGCReviewResultModel.workspace_id == workspace_id,
                UGCReviewResultModel.processing_job_id == processing_job_id,
            )
        )
        if existing is not None:
            return existing
        response = UGCReviewResultResponse(
            **result.model_dump(),
            asset_id=asset_id,
            asset_version_id=asset_version_id,
        )
        result_model, findings = map_result_to_models(
            workspace_id=workspace_id,
            processing_job_id=processing_job_id,
            request_context=request_context,
            response=response,
        )
        self._session.add(result_model)
        self._session.add_all(findings)
        self._session.flush()
        return result_model

    def get_result(
        self,
        workspace_id: UUID,
        processing_job_id: UUID,
    ) -> UGCReviewResultModel | None:
        return self._session.scalar(
            select(UGCReviewResultModel).where(
                UGCReviewResultModel.workspace_id == workspace_id,
                UGCReviewResultModel.processing_job_id == processing_job_id,
            )
        )


class InMemoryUGCReviewRepository:
    """Explicit non-durable repository for focused local tests."""

    def __init__(self) -> None:
        logger.warning("Using non-durable in-memory UGC review repository")
        self.results: dict[tuple[UUID, UUID], UGCReviewResultModel] = {}
        self.findings: list[UGCReviewFindingModel] = []
        self.events: list[UGCReviewRecommendationEventModel] = []
        self.revisions: list[UGCReviewRevisionModel] = []
        self.comparisons: list[UGCReviewComparisonModel] = []

    async def persist_response(
        self,
        workspace_id: UUID,
        response: UGCReviewResultResponse,
        *,
        request_context: dict[str, object],
    ) -> UGCReviewResultModel:
        processing_job_id = UUID(response.review_id)
        result_model, findings = map_result_to_models(
            workspace_id=workspace_id,
            processing_job_id=processing_job_id,
            request_context=request_context,
            response=response,
        )
        now = datetime.now(UTC)
        result_model.created_at = now
        result_model.updated_at = now
        for finding in findings:
            finding.created_at = now
        self.results[(workspace_id, processing_job_id)] = result_model
        self.findings.extend(findings)
        return result_model

    async def get_result(
        self,
        workspace_id: UUID,
        processing_job_id: UUID,
    ) -> UGCReviewResultModel | None:
        return self.results.get((workspace_id, processing_job_id))

    async def get_finding(
        self,
        workspace_id: UUID,
        processing_job_id: UUID,
        recommendation_id: str,
    ) -> UGCReviewFindingModel | None:
        return next(
            (
                item
                for item in self.findings
                if item.workspace_id == workspace_id
                and item.processing_job_id == processing_job_id
                and item.recommendation_id == recommendation_id
            ),
            None,
        )

    async def record_action(
        self,
        *,
        finding: UGCReviewFindingModel,
        seller_action: str,
        reason: str | None,
    ) -> UGCReviewRecommendationEventModel:
        event = UGCReviewRecommendationEventModel(
            id=uuid4(),
            workspace_id=finding.workspace_id,
            processing_job_id=finding.processing_job_id,
            finding_id=finding.id,
            seller_action=seller_action,
            reason=reason,
            created_at=datetime.now(UTC),
        )
        self.events.append(event)
        return event

    async def create_revision(
        self,
        *,
        workspace_id: UUID,
        parent_processing_job_id: UUID,
        child_processing_job_id: UUID,
        parent_asset_version_id: UUID,
        child_asset_version_id: UUID,
    ) -> UGCReviewRevisionModel:
        existing = next(
            (
                item
                for item in self.revisions
                if item.child_processing_job_id == child_processing_job_id
            ),
            None,
        )
        if existing is not None:
            if (
                existing.workspace_id != workspace_id
                or existing.parent_processing_job_id != parent_processing_job_id
                or existing.parent_asset_version_id != parent_asset_version_id
                or existing.child_asset_version_id != child_asset_version_id
            ):
                raise ConflictError(
                    "UGC_REVIEW_REVISION_RELATION_CONFLICT",
                    "Revision job already belongs to a different parent relation.",
                )
            return existing
        relation = UGCReviewRevisionModel(
            id=uuid4(),
            workspace_id=workspace_id,
            parent_processing_job_id=parent_processing_job_id,
            child_processing_job_id=child_processing_job_id,
            parent_asset_version_id=parent_asset_version_id,
            child_asset_version_id=child_asset_version_id,
            created_at=datetime.now(UTC),
        )
        self.revisions.append(relation)
        return relation

    async def get_latest_revision(
        self,
        workspace_id: UUID,
        parent_processing_job_id: UUID,
    ) -> UGCReviewRevisionModel | None:
        matches = [
            item
            for item in self.revisions
            if item.workspace_id == workspace_id
            and item.parent_processing_job_id == parent_processing_job_id
        ]
        return max(matches, key=lambda item: item.created_at) if matches else None

    async def persist_comparison(
        self,
        workspace_id: UUID,
        comparison: UGCRevisionComparisonResponse,
    ) -> UGCReviewComparisonModel:
        model = comparison_to_model(workspace_id, comparison)
        model.created_at = datetime.now(UTC)
        self.comparisons.append(model)
        return model


def map_result_to_models(
    *,
    workspace_id: UUID,
    processing_job_id: UUID,
    request_context: dict[str, object],
    response: UGCReviewResultResponse,
) -> tuple[UGCReviewResultModel, list[UGCReviewFindingModel]]:
    if UUID(response.review_id) != processing_job_id:
        raise ValueError("result review_id must match processing_job_id")
    payload = response.model_dump(mode="json")
    result_model = UGCReviewResultModel(
        workspace_id=workspace_id,
        processing_job_id=processing_job_id,
        asset_id=response.asset_id,
        asset_version_id=response.asset_version_id,
        headline=response.headline,
        summary=response.summary,
        recommended_next_action=response.recommended_next_action,
        overall_confidence=response.overall_confidence,
        strengths_to_keep=list(response.strengths_to_keep),
        creator_revision_message=response.creator_revision_message,
        policy_pack_version=response.policy_pack_version,
        request_context=request_context,
        analysis_provenance=response.analysis_provenance,
        result_payload=payload,
    )
    findings = [
        _finding_model(workspace_id, processing_job_id, recommendation)
        for recommendation in _all_recommendations(response)
    ]
    return result_model, findings


def result_response_from_model(model: UGCReviewResultModel) -> UGCReviewResultResponse:
    payload = dict(model.result_payload)
    payload.update(
        {
            "review_id": str(model.processing_job_id),
            "asset_id": model.asset_id,
            "asset_version_id": model.asset_version_id,
        }
    )
    return UGCReviewResultResponse.model_validate(payload)


def comparison_to_model(
    workspace_id: UUID,
    comparison: UGCRevisionComparisonResponse,
) -> UGCReviewComparisonModel:
    payload = comparison.model_dump(mode="json")
    return UGCReviewComparisonModel(
        workspace_id=workspace_id,
        parent_processing_job_id=UUID(comparison.parent_review_id),
        child_processing_job_id=UUID(comparison.revision_review_id),
        resolved_findings=payload["resolved"],
        still_open_findings=payload["still_open"],
        new_findings=payload["new_findings"],
        strengths_preserved=payload["strengths_preserved"],
        summary=comparison.summary,
        comparison_payload=payload,
    )


def _finding_model(
    workspace_id: UUID,
    processing_job_id: UUID,
    recommendation: UGCRecommendation,
) -> UGCReviewFindingModel:
    payload = recommendation.model_dump(mode="json")
    return UGCReviewFindingModel(
        workspace_id=workspace_id,
        processing_job_id=processing_job_id,
        rule_code=recommendation.rule_code,
        mistake_code=recommendation.mistake_code,
        recommendation_id=recommendation.id,
        recommendation_group=recommendation.group,
        title=recommendation.title,
        reason=recommendation.reason,
        owner_role=recommendation.owner,
        fix_type=recommendation.fix_type,
        confidence=recommendation.confidence,
        evidence=payload["evidence"],
        recommendation_payload=payload,
    )


def _require_matching_revision(
    revision: UGCReviewRevisionModel,
    *,
    workspace_id: UUID,
    parent_processing_job_id: UUID,
    parent_asset_version_id: UUID,
    child_asset_version_id: UUID,
) -> UGCReviewRevisionModel:
    if (
        revision.workspace_id != workspace_id
        or revision.parent_processing_job_id != parent_processing_job_id
        or revision.parent_asset_version_id != parent_asset_version_id
        or revision.child_asset_version_id != child_asset_version_id
    ):
        raise ConflictError(
            "UGC_REVIEW_REVISION_RELATION_CONFLICT",
            "Revision job already belongs to a different parent relation.",
        )
    return revision


def _all_recommendations(response: UGCReviewResultResponse) -> list[UGCRecommendation]:
    return [*response.fix_first, *response.improvements, *response.confirmations]


__all__ = [
    "InMemoryUGCReviewRepository",
    "SyncUGCReviewRepository",
    "UGCReviewRepository",
    "comparison_to_model",
    "map_result_to_models",
    "result_response_from_model",
]
