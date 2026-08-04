from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from viraldy.modules.domain_intelligence.schemas import (
    DomainRule,
    EvaluationCandidate,
    NormalizedEvidenceBundle,
    UGCReviewContext,
)


class SemanticEvaluator(Protocol):
    @property
    def provider_name(self) -> str: ...

    def evaluate(
        self,
        *,
        context: UGCReviewContext,
        evidence: NormalizedEvidenceBundle,
        rules: Sequence[DomainRule],
    ) -> list[EvaluationCandidate]: ...


class DeterministicSemanticFallback:
    provider_name = "deterministic_fallback"

    def evaluate(
        self,
        *,
        context: UGCReviewContext,
        evidence: NormalizedEvidenceBundle,
        rules: Sequence[DomainRule],
    ) -> list[EvaluationCandidate]:
        return []


def evaluate_semantically_bounded(
    evaluator: SemanticEvaluator | None,
    *,
    context: UGCReviewContext,
    evidence: NormalizedEvidenceBundle,
    rules: Sequence[DomainRule],
) -> tuple[list[EvaluationCandidate], str]:
    active_codes = {rule.code for rule in rules}
    evidence_ids = {item.id for item in evidence.items}
    provider = evaluator or DeterministicSemanticFallback()
    try:
        candidates = provider.evaluate(context=context, evidence=evidence, rules=rules)
    except Exception:
        return [], "deterministic_fallback"
    bounded = [
        candidate
        for candidate in candidates
        if (candidate.rule_code is None or candidate.rule_code in active_codes)
        and set(candidate.evidence_ids).issubset(evidence_ids)
        and not _contains_unsupported_language(candidate)
    ]
    return bounded, provider.provider_name


def _contains_unsupported_language(candidate: EvaluationCandidate) -> bool:
    text = " ".join(
        [
            candidate.title,
            candidate.reason,
            candidate.why_it_matters,
            *candidate.instructions,
            *candidate.completion_criteria,
        ]
    ).lower()
    prohibited = (
        "viral probability",
        "guaranteed performance",
        "predicted gmv",
        "predicted roas",
        "guaranteed to win",
        "winning creative",
    )
    return any(phrase in text for phrase in prohibited)
