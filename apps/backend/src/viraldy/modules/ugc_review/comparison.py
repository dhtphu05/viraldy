from __future__ import annotations

from collections.abc import Iterable

from viraldy.modules.ugc_review.schemas import (
    UGCComparisonFinding,
    UGCRecommendation,
    UGCReviewResultResponse,
    UGCRevisionComparisonResponse,
)


def compare_review_results(
    parent: UGCReviewResultResponse,
    revision: UGCReviewResultResponse,
) -> UGCRevisionComparisonResponse:
    """Compare actual recommendation identities without deriving a synthetic score."""

    parent_by_identity = _recommendations_by_identity(_all_recommendations(parent))
    revision_by_identity = _recommendations_by_identity(_all_recommendations(revision))
    parent_identities = set(parent_by_identity)
    revision_identities = set(revision_by_identity)

    resolved = [
        _comparison_finding(identity, parent_by_identity[identity], None)
        for identity in sorted(parent_identities - revision_identities)
    ]
    still_open = [
        _comparison_finding(
            identity,
            parent_by_identity[identity],
            revision_by_identity[identity],
        )
        for identity in sorted(parent_identities & revision_identities)
    ]
    new_findings = [
        _comparison_finding(identity, None, revision_by_identity[identity])
        for identity in sorted(revision_identities - parent_identities)
    ]
    strengths_preserved = _preserved_strengths(parent, revision)
    return UGCRevisionComparisonResponse(
        parent_review_id=parent.review_id,
        revision_review_id=revision.review_id,
        summary=_summary(len(resolved), len(still_open), len(new_findings)),
        resolved=resolved,
        still_open=still_open,
        new_findings=new_findings,
        strengths_preserved=strengths_preserved,
    )


def recommendation_identity(recommendation: UGCRecommendation) -> str:
    return f"recommendation:{recommendation.id}"


def _all_recommendations(result: UGCReviewResultResponse) -> Iterable[UGCRecommendation]:
    yield from result.fix_first
    yield from result.improvements
    yield from result.confirmations


def _recommendations_by_identity(
    recommendations: Iterable[UGCRecommendation],
) -> dict[str, UGCRecommendation]:
    by_identity: dict[str, UGCRecommendation] = {}
    for recommendation in recommendations:
        identity = recommendation_identity(recommendation)
        if identity in by_identity:
            raise ValueError(f"duplicate recommendation identity: {identity}")
        by_identity[identity] = recommendation
    return by_identity


def _comparison_finding(
    identity: str,
    parent: UGCRecommendation | None,
    revision: UGCRecommendation | None,
) -> UGCComparisonFinding:
    finding = revision or parent
    if finding is None:
        raise ValueError("comparison requires a parent or revision recommendation")
    return UGCComparisonFinding(
        identity=identity,
        rule_code=finding.rule_code,
        mistake_code=finding.mistake_code,
        title=finding.title,
        parent_recommendation_id=parent.id if parent is not None else None,
        revision_recommendation_id=revision.id if revision is not None else None,
        parent_evidence=list(parent.evidence) if parent is not None else [],
        revision_evidence=list(revision.evidence) if revision is not None else [],
    )


def _preserved_strengths(
    parent: UGCReviewResultResponse,
    revision: UGCReviewResultResponse,
) -> list[str]:
    revision_strengths = {_normalize_strength(item) for item in revision.strengths_to_keep}
    return [
        strength
        for strength in parent.strengths_to_keep
        if _normalize_strength(strength) in revision_strengths
    ]


def _normalize_strength(value: str) -> str:
    return " ".join(value.casefold().split())


def _summary(resolved: int, still_open: int, new: int) -> str:
    return (
        f"Revision comparison: {resolved} resolved, {still_open} still open, "
        f"and {new} new finding{'s' if new != 1 else ''}."
    )


__all__ = ["compare_review_results", "recommendation_identity"]
