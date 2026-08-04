from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime

from viraldy.modules.domain_intelligence.deterministic_evaluator import evaluate_deterministically
from viraldy.modules.domain_intelligence.message_renderer import render_creator_message
from viraldy.modules.domain_intelligence.recommendation_mapper import map_recommendations
from viraldy.modules.domain_intelligence.schemas import (
    Confidence,
    DomainRule,
    NormalizedEvidenceBundle,
    ReviewNextAction,
    UGCRecommendation,
    UGCReviewContext,
    UGCReviewResult,
)
from viraldy.modules.domain_intelligence.selector import select_applicable_rules
from viraldy.modules.domain_intelligence.semantic_evaluator import (
    SemanticEvaluator,
    evaluate_semantically_bounded,
)


def evaluate_review(
    *,
    review_id: str,
    context: UGCReviewContext,
    evidence: NormalizedEvidenceBundle,
    rules: Sequence[DomainRule],
    pack_version: str,
    semantic_evaluator: SemanticEvaluator | None = None,
    analysis_provenance: Mapping[str, object] | None = None,
    created_at: datetime | None = None,
) -> UGCReviewResult:
    applicable = select_applicable_rules(rules, context, evidence)
    deterministic = evaluate_deterministically(context, evidence, applicable)
    semantic, semantic_provider = evaluate_semantically_bounded(
        semantic_evaluator,
        context=context,
        evidence=evidence,
        rules=applicable,
    )
    fix_first, improvements, confirmations = map_recommendations(
        [*deterministic, *semantic], evidence
    )
    strengths = _strengths(evidence)
    next_action = _next_action(fix_first, confirmations)
    creator_message = render_creator_message(strengths, fix_first, improvements)
    timestamp = (created_at or datetime.now(UTC)).astimezone(UTC).isoformat()
    provenance: dict[str, object] = {
        "applicable_rule_codes": [rule.code for rule in applicable],
        "evidence_count": len(evidence.items),
        "analysis_coverage": evidence.coverage,
        "missing_required": evidence.missing_required,
        "pipeline_version": evidence.pipeline_version,
        "semantic_provider": semantic_provider,
        "execution_brief_provider": "deterministic_fallback",
        "performance_evidence_status": "insufficient_evidence",
    }
    model_provider_versions = evidence.metadata.get("model_provider_versions")
    if model_provider_versions:
        provenance["model_provider_versions"] = model_provider_versions
    if analysis_provenance:
        provenance.update(analysis_provenance)
    return UGCReviewResult(
        review_id=review_id,
        headline=_headline(fix_first, confirmations),
        summary=_summary(fix_first, improvements, confirmations),
        recommended_next_action=next_action,
        overall_confidence=_overall_confidence(evidence, fix_first),
        strengths_to_keep=strengths,
        fix_first=fix_first,
        improvements=improvements,
        confirmations=confirmations,
        creator_revision_message=creator_message,
        policy_pack_version=pack_version,
        analysis_provenance=provenance,
        created_at=timestamp,
    )


def _strengths(evidence: NormalizedEvidenceBundle) -> list[str]:
    strengths = list(dict.fromkeys(item.strip() for item in evidence.strengths if item.strip()))
    if strengths:
        return strengths[:5]
    return ["Keep the usable footage and creator delivery that already work."]


def _next_action(
    fix_first: Sequence[UGCRecommendation],
    confirmations: Sequence[UGCRecommendation],
) -> ReviewNextAction:
    if any(item.fix_type == "reshoot_scene" for item in fix_first):
        return "reshoot_scene"
    if fix_first:
        return "revise"
    if confirmations:
        if any(item.fix_type == "request_better_media" for item in confirmations):
            return "request_better_media"
        return "confirm_information"
    return "use_as_is"


def _headline(
    fix_first: Sequence[UGCRecommendation],
    confirmations: Sequence[UGCRecommendation],
) -> str:
    if len(fix_first) == 1:
        return "Strong foundation — one main fix recommended"
    if fix_first:
        return "Useful draft — focused revisions recommended"
    if confirmations:
        return "Review complete — a few details need confirmation"
    return "Strong draft — ready for the seller's next step"


def _summary(
    fix_first: Sequence[UGCRecommendation],
    improvements: Sequence[UGCRecommendation],
    confirmations: Sequence[UGCRecommendation],
) -> str:
    return (
        f"Keep the working footage, address {len(fix_first)} priority recommendation(s), "
        f"consider {len(improvements)} optional improvement(s), and confirm "
        f"{len(confirmations)} material detail(s)."
    )


def _overall_confidence(
    evidence: NormalizedEvidenceBundle,
    fix_first: Sequence[UGCRecommendation],
) -> Confidence:
    if any(item.confidence == "high" for item in fix_first):
        return "high"
    if evidence.items:
        return "medium"
    return "low"
