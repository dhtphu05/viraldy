from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from viraldy.modules.ugc_review.comparison import compare_review_results
from viraldy.modules.ugc_review.schemas import (
    ReviewEvidence,
    UGCRecommendation,
    UGCReviewResultResponse,
)


def _recommendation(
    recommendation_id: str,
    *,
    rule_code: str | None,
    mistake_code: str | None = None,
    observed: str = "Observed fact",
    title: str | None = None,
) -> UGCRecommendation:
    return UGCRecommendation(
        id=recommendation_id,
        rule_code=rule_code,
        mistake_code=mistake_code,
        group="improve",
        title=title or f"Recommendation {rule_code or mistake_code or recommendation_id}",
        reason="The observed draft can be clearer.",
        why_it_matters="It helps the viewer understand the draft.",
        owner="editor",
        fix_type="edit_existing_footage",
        instructions=["Tighten the existing scene."],
        strengths_to_preserve=["Natural creator delivery"],
        completion_criteria=["The scene is concise."],
        evidence=[
            ReviewEvidence(
                id=f"evidence-{recommendation_id}",
                source="video",
                observed=observed,
                start_ms=100,
                end_ms=500,
                confidence="high",
            )
        ],
        confidence="high",
    )


def _result(
    review_id: str,
    *,
    recommendations: list[UGCRecommendation],
    strengths: list[str],
) -> UGCReviewResultResponse:
    return UGCReviewResultResponse(
        review_id=review_id,
        asset_id=uuid4(),
        asset_version_id=uuid4(),
        status="completed",
        headline="Useful review",
        summary="Review summary",
        recommended_next_action="revise",
        overall_confidence="high",
        strengths_to_keep=strengths,
        fix_first=[],
        improvements=recommendations,
        confirmations=[],
        creator_revision_message="Keep the natural delivery and tighten the edit.",
        policy_pack_version="v1",
        analysis_provenance={"pipeline": "test"},
        created_at=datetime.now(UTC).isoformat(),
    )


def test_comparison_uses_deterministic_recommendation_identity_and_evidence() -> None:
    parent = _result(
        str(uuid4()),
        recommendations=[
            _recommendation("struct-still-open", rule_code="UGC-STRUCT-001"),
            _recommendation("parent-resolved", rule_code=None, mistake_code="M-DEMO-001"),
        ],
        strengths=["Natural creator delivery", "Clear product close-up"],
    )
    revision = _result(
        str(uuid4()),
        recommendations=[
            _recommendation(
                "struct-still-open",
                rule_code="UGC-STRUCT-001",
                observed="The same issue remains in the new evidence.",
            ),
            _recommendation("child-new", rule_code="UGC-RIGHTS-001"),
        ],
        strengths=["Natural creator delivery"],
    )

    comparison = compare_review_results(parent, revision)

    assert [item.identity for item in comparison.resolved] == [
        "recommendation:parent-resolved"
    ]
    assert [item.identity for item in comparison.still_open] == [
        "recommendation:struct-still-open"
    ]
    assert [item.identity for item in comparison.new_findings] == [
        "recommendation:child-new"
    ]
    assert comparison.still_open[0].parent_recommendation_id == "struct-still-open"
    assert comparison.still_open[0].revision_recommendation_id == "struct-still-open"
    assert comparison.still_open[0].parent_evidence[0].observed == "Observed fact"
    assert comparison.still_open[0].revision_evidence[0].observed.startswith("The same issue")
    assert comparison.strengths_preserved == ["Natural creator delivery"]
    assert "1 resolved" in comparison.summary
    assert "1 still open" in comparison.summary
    assert "1 new" in comparison.summary


def test_comparison_distinguishes_multiple_findings_for_the_same_rule() -> None:
    parent = _result(
        str(uuid4()),
        recommendations=[
            _recommendation(
                "claim-copy",
                rule_code="UGC-CLAIM-001",
                title="Remove the unsupported copy claim",
            ),
            _recommendation(
                "claim-proof",
                rule_code="UGC-CLAIM-001",
                title="Add proof for the visual claim",
            ),
        ],
        strengths=["Natural creator delivery"],
    )
    revision = _result(
        str(uuid4()),
        recommendations=[
            _recommendation(
                "claim-proof",
                rule_code="UGC-CLAIM-001",
                title="Add proof for the visual claim",
            )
        ],
        strengths=["Natural creator delivery"],
    )

    comparison = compare_review_results(parent, revision)

    assert [item.title for item in comparison.resolved] == [
        "Remove the unsupported copy claim"
    ]
    assert [item.title for item in comparison.still_open] == [
        "Add proof for the visual claim"
    ]
    assert comparison.still_open[0].parent_recommendation_id == "claim-proof"
    assert comparison.still_open[0].revision_recommendation_id == "claim-proof"
