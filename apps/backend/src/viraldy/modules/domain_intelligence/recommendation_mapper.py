from __future__ import annotations

import hashlib
from collections.abc import Sequence

from viraldy.modules.domain_intelligence.schemas import (
    EvaluationCandidate,
    NormalizedEvidenceBundle,
    ReviewEvidence,
    UGCRecommendation,
)

MAX_PER_GROUP = 3


def map_recommendations(
    candidates: Sequence[EvaluationCandidate],
    evidence: NormalizedEvidenceBundle,
) -> tuple[list[UGCRecommendation], list[UGCRecommendation], list[UGCRecommendation]]:
    evidence_by_id = {item.id: item for item in evidence.items}
    seen: set[tuple[str | None, str | None, str, str]] = set()
    recommendations: list[UGCRecommendation] = []
    for candidate in sorted(candidates, key=_sort_key):
        key = (candidate.rule_code, candidate.mistake_code, candidate.group, candidate.title)
        if key in seen:
            continue
        seen.add(key)
        review_evidence = [
            ReviewEvidence(
                id=item.id,
                source=item.source,
                observed=item.observed,
                start_ms=item.start_ms,
                end_ms=item.end_ms,
                confidence=item.confidence,
            )
            for evidence_id in candidate.evidence_ids
            if (item := evidence_by_id.get(evidence_id)) is not None
        ]
        recommendation_id = hashlib.sha256(
            "|".join(str(part) for part in key).encode()
        ).hexdigest()[:24]
        recommendations.append(
            UGCRecommendation(
                id=recommendation_id,
                rule_code=candidate.rule_code,
                mistake_code=candidate.mistake_code,
                group=candidate.group,
                title=candidate.title,
                reason=candidate.reason,
                why_it_matters=candidate.why_it_matters,
                owner=candidate.owner,
                fix_type=candidate.fix_type,
                instructions=candidate.instructions,
                strengths_to_preserve=candidate.strengths_to_preserve,
                completion_criteria=candidate.completion_criteria,
                evidence=review_evidence,
                confidence=candidate.confidence,
                affected_use=candidate.affected_use,
                unknown_state=candidate.unknown_state,
            )
        )
    fix_first = [item for item in recommendations if item.group == "fix_first"][:MAX_PER_GROUP]
    improvements = [item for item in recommendations if item.group == "improve"][:MAX_PER_GROUP]
    confirmations = [item for item in recommendations if item.group == "confirm"][:MAX_PER_GROUP]
    return fix_first, improvements, confirmations


def _sort_key(candidate: EvaluationCandidate) -> tuple[int, int, str]:
    group_order = {"fix_first": 0, "improve": 1, "confirm": 2}
    confidence_order = {"high": 0, "medium": 1, "low": 2}
    return (
        group_order[candidate.group],
        confidence_order[candidate.confidence],
        candidate.title,
    )
