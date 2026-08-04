from __future__ import annotations

import hashlib
from collections.abc import Sequence

from viraldy.modules.domain_intelligence.schemas import (
    EvaluationCandidate,
    NormalizedEvidenceBundle,
    RecommendationPriority,
    RecommendationTaskKind,
    ReviewEvidence,
    ReviewTimeRange,
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
        task_kind = _task_kind(candidate)
        priority = _priority(candidate)
        time_range = candidate.time_range or _time_range(review_evidence)
        exact_action = candidate.exact_action or _exact_action(candidate)
        acceptance_criteria = candidate.acceptance_criteria or candidate.completion_criteria
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
                task_kind=task_kind,
                priority=priority,
                time_range=time_range,
                exact_action=exact_action,
                exact_copy=candidate.exact_copy,
                acceptance_criteria=acceptance_criteria,
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


def _task_kind(candidate: EvaluationCandidate) -> RecommendationTaskKind:
    if candidate.task_kind is not None:
        return candidate.task_kind
    if candidate.group in {"fix_first", "improve"}:
        return "video_edit_required"
    if candidate.unknown_state == "publish_check_required":
        return "publish_ops_required"
    return "seller_input_required"


def _priority(candidate: EvaluationCandidate) -> RecommendationPriority:
    if candidate.priority is not None:
        return candidate.priority
    if candidate.group == "fix_first":
        return "fix_before_publish"
    if candidate.group == "confirm":
        return "confirm_before_publish"
    return "optional_improvement"


def _time_range(evidence: list[ReviewEvidence]) -> ReviewTimeRange | None:
    timestamped = next((item for item in evidence if item.start_ms is not None), None)
    if timestamped is None:
        return None
    return ReviewTimeRange(start_ms=timestamped.start_ms, end_ms=timestamped.end_ms)


def _exact_action(candidate: EvaluationCandidate) -> str:
    if candidate.instructions:
        return candidate.instructions[0]
    return candidate.title
