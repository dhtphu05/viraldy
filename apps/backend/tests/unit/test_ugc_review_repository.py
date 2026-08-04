from __future__ import annotations

from datetime import UTC, datetime
from typing import cast
from uuid import UUID, uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from viraldy.modules.ugc_review.models import UGCReviewComparisonModel
from viraldy.modules.ugc_review.repository import (
    UGCReviewRepository,
    comparison_to_model,
    map_result_to_models,
    result_response_from_model,
)
from viraldy.modules.ugc_review.schemas import (
    ReviewEvidence,
    UGCRecommendation,
    UGCReviewResultResponse,
    UGCRevisionComparisonResponse,
)


class ConcurrentComparisonSession:
    def __init__(self, concurrent: UGCReviewComparisonModel) -> None:
        self.concurrent = concurrent
        self.scalar_calls = 0
        self.rollbacks = 0

    async def scalar(self, statement: object) -> UGCReviewComparisonModel | None:
        _ = statement
        self.scalar_calls += 1
        return None if self.scalar_calls == 1 else self.concurrent

    def add(self, model: object) -> None:
        _ = model

    async def flush(self) -> None:
        raise IntegrityError("insert", {}, RuntimeError("duplicate"))

    async def rollback(self) -> None:
        self.rollbacks += 1


def test_result_persistence_maps_contract_and_finding_payloads_without_losing_evidence() -> None:
    workspace_id = uuid4()
    review_id = uuid4()
    asset_id = uuid4()
    asset_version_id = uuid4()
    recommendation = UGCRecommendation(
        id="recommendation-demo",
        rule_code="UGC-DEMO-001",
        mistake_code="M-DEMO-001",
        group="fix_first",
        title="Make the demo result visible",
        reason="The result leaves frame too quickly.",
        why_it_matters="The viewer needs to see the actual result.",
        owner="editor",
        fix_type="edit_existing_footage",
        instructions=["Hold the existing close-up for one second."],
        strengths_to_preserve=["Natural delivery"],
        completion_criteria=["The result stays visible for one second."],
        evidence=[
            ReviewEvidence(
                id="video-1",
                source="video",
                observed="The result is visible from 800ms to 950ms.",
                start_ms=800,
                end_ms=950,
                confidence="high",
            )
        ],
        confidence="high",
    )
    response = UGCReviewResultResponse(
        review_id=str(review_id),
        asset_id=asset_id,
        asset_version_id=asset_version_id,
        status="completed",
        headline="One high-value edit",
        summary="Keep the delivery and lengthen the close-up.",
        recommended_next_action="revise",
        overall_confidence="high",
        strengths_to_keep=["Natural delivery"],
        fix_first=[recommendation],
        improvements=[],
        confirmations=[],
        creator_revision_message="Keep the delivery and hold the close-up longer.",
        policy_pack_version="v1",
        analysis_provenance={"applicable_rule_codes": ["UGC-DEMO-001"]},
        created_at=datetime.now(UTC).isoformat(),
    )

    result_model, findings = map_result_to_models(
        workspace_id=workspace_id,
        processing_job_id=review_id,
        request_context={"market": "US"},
        response=response,
    )

    assert result_model.processing_job_id == review_id
    assert result_model.asset_id == asset_id
    assert result_model.asset_version_id == asset_version_id
    assert result_model.request_context == {"market": "US"}
    assert result_model.result_payload["review_id"] == str(review_id)
    assert len(findings) == 1
    finding = findings[0]
    assert finding.recommendation_id == "recommendation-demo"
    assert finding.recommendation_group == "fix_first"
    assert finding.rule_code == "UGC-DEMO-001"
    assert finding.mistake_code == "M-DEMO-001"
    assert finding.evidence == [
        {
            "id": "video-1",
            "source": "video",
            "observed": "The result is visible from 800ms to 950ms.",
            "start_ms": 800,
            "end_ms": 950,
            "confidence": "high",
        }
    ]
    assert result_response_from_model(result_model) == response


@pytest.mark.asyncio
async def test_comparison_persistence_recovers_when_a_concurrent_insert_wins() -> None:
    workspace_id = uuid4()
    comparison = UGCRevisionComparisonResponse(
        parent_review_id=str(uuid4()),
        revision_review_id=str(uuid4()),
        summary="Revision comparison complete.",
        resolved=[],
        still_open=[],
        new_findings=[],
        strengths_preserved=["Natural delivery"],
    )
    concurrent = comparison_to_model(workspace_id, comparison)
    session = ConcurrentComparisonSession(concurrent)
    repository = UGCReviewRepository(cast(AsyncSession, session))

    persisted = await repository.persist_comparison(workspace_id, comparison)

    assert persisted is concurrent
    assert session.rollbacks == 1
    assert persisted.workspace_id == workspace_id
    assert persisted.parent_processing_job_id == UUID(comparison.parent_review_id)
