from __future__ import annotations

import re
from collections.abc import Iterable
from uuid import UUID

from pydantic import ValidationError

from viraldy.evaluation.contracts import (
    BooleanJudgmentV1,
    CategoricalAgreementV1,
    EvaluationAggregateV1,
    EvaluationDatasetV1,
    EvaluationReportV1,
    MetricResultV1,
    PatternKitCaseResultV1,
    PatternKitMetricInputV1,
    PatternKitMetricsResultV1,
    ViralKitCaseResultV1,
    ViralKitMetricInputV1,
    ViralKitMetricsResultV1,
)
from viraldy.modules.campaign_packs.contracts import CampaignPackBriefV1
from viraldy.modules.campaign_packs.public import (
    CompiledRequirementsSnapshotV2,
    compile_campaign_requirements,
)
from viraldy.modules.pattern_kits.public import PatternKitV1
from viraldy.modules.viral_kits.public import ViralKitV1


def evaluate_dataset(dataset: EvaluationDatasetV1) -> EvaluationReportV1:
    pattern_cases = [
        PatternKitCaseResultV1(case_id=case.case_id, metrics=evaluate_pattern_kit(case))
        for case in sorted(dataset.pattern_kit_cases, key=lambda item: item.case_id)
    ]
    viral_cases = [
        ViralKitCaseResultV1(case_id=case.case_id, metrics=evaluate_viral_kit(case))
        for case in sorted(dataset.viral_kit_cases, key=lambda item: item.case_id)
    ]
    return EvaluationReportV1(
        dataset_id=dataset.dataset_id,
        mode=dataset.mode,
        pattern_kit_cases=pattern_cases,
        viral_kit_cases=viral_cases,
        aggregate=EvaluationAggregateV1(
            pattern_kit=_aggregate_pattern_metrics(pattern_cases) if pattern_cases else None,
            viral_kit=_aggregate_viral_metrics(viral_cases) if viral_cases else None,
        ),
    )


def evaluate_pattern_kit(case: PatternKitMetricInputV1) -> PatternKitMetricsResultV1:
    evidence_ids = _evidence_ids(case.candidate)
    resolvable = set(case.resolvable_evidence_ids)
    resolved_count = sum(evidence_id in resolvable for evidence_id in evidence_ids)
    sequence = [
        str(beat["beat_type"])
        for beat in _dict_items(case.candidate.get("sequence"))
        if "beat_type" in beat
    ]
    adaptation_labels = {
        str(item["element_path"]): str(item["instruction_type"])
        for item in _dict_items(case.candidate.get("adaptation_instructions"))
        if "element_path" in item and "instruction_type" in item
    }
    adaptation_matches = sum(
        adaptation_labels.get(label.element_path) == label.decision
        for label in case.adaptation_reviewer_labels
    )
    candidate_text = " ".join(_string_values(case.candidate)).casefold()
    forbidden_terms = {
        term.casefold().strip()
        for term in case.forbidden_category_terms
        if term.strip()
    }
    leaked_terms = sum(
        _contains_term(candidate_text, term)
        for term in forbidden_terms
    )
    unsupported = sum(not check.supported for check in case.generalization_checks)

    return PatternKitMetricsResultV1(
        schema_validity=_schema_metric("schema_validity", PatternKitV1, case.candidate),
        evidence_resolution=_rate_metric(
            "evidence_resolution_rate", resolved_count, len(evidence_ids)
        ),
        source_field_agreement=_agreement_metric(
            "source_field_agreement", case.source_field_checks
        ),
        sequence_agreement=_sequence_metric(case.expected_sequence, sequence),
        applicability_agreement=_agreement_metric(
            "applicability_agreement", case.applicability_checks
        ),
        keep_change_avoid_agreement=_rate_metric(
            "keep_change_avoid_reviewer_agreement",
            adaptation_matches,
            len(case.adaptation_reviewer_labels),
        ),
        cross_category_leakage=_count_metric(
            "cross_category_leakage", leaked_terms, len(case.forbidden_category_terms)
        ),
        unsupported_generalization=_count_metric(
            "unsupported_generalization_count",
            unsupported,
            len(case.generalization_checks),
        ),
    )


def evaluate_viral_kit(case: ViralKitMetricInputV1) -> ViralKitMetricsResultV1:
    concepts = _dict_items(case.candidate.get("concepts"))
    separated = sum(
        _normalized(concept.get("buyer_persona_label"))
        != _normalized(concept.get("creator_persona"))
        for concept in concepts
    )
    preserved, preservation_total = _claim_disclosure_preservation(
        concepts,
        case.expected_prohibited_claims,
        case.expected_required_disclosures,
    )
    traced, trace_total = _pattern_traceability(
        case.candidate,
        concepts,
        set(case.expected_pattern_kit_version_ids),
    )
    campaign_compiled = sum(
        _campaign_pack_compiles(item.brief) for item in case.campaign_pack_briefs
    )
    preflight_compiled = sum(
        _preflight_snapshot_compiles(item.snapshot) for item in case.preflight_snapshots
    )
    usefulness_total = sum(case.human_usefulness_scores)

    return ViralKitMetricsResultV1(
        schema_validity=_schema_metric("schema_validity", ViralKitV1, case.candidate),
        product_grounding=_boolean_metric(
            "product_grounding_rate", case.product_grounding_checks
        ),
        constraint_preservation=_boolean_metric(
            "constraint_preservation", case.constraint_preservation_checks
        ),
        diversity_pass_rate=_boolean_metric(
            "concept_diversity_pass_rate", case.diversity_checks
        ),
        buyer_creator_separation=_rate_metric(
            "buyer_creator_separation", separated, len(concepts)
        ),
        claim_disclosure_preservation=_rate_metric(
            "claim_disclosure_preservation", preserved, preservation_total
        ),
        pattern_kit_traceability=_rate_metric(
            "pattern_kit_traceability", traced, trace_total
        ),
        campaign_pack_compile=_rate_metric(
            "campaign_pack_compile_rate",
            campaign_compiled,
            len(case.campaign_pack_briefs),
        ),
        preflight_compile=_rate_metric(
            "preflight_requirement_compile_rate",
            preflight_compiled,
            len(case.preflight_snapshots),
        ),
        human_usefulness=_score_metric(
            "human_concept_usefulness",
            usefulness_total,
            len(case.human_usefulness_scores),
        ),
    )


def _schema_metric(
    name: str,
    contract: type[PatternKitV1] | type[ViralKitV1],
    candidate: dict[str, object],
) -> MetricResultV1:
    try:
        contract.model_validate(candidate)
    except ValidationError:
        return _rate_metric(name, 0, 1)
    return _rate_metric(name, 1, 1)


def _agreement_metric(
    name: str, checks: list[CategoricalAgreementV1]
) -> MetricResultV1:
    matches = sum(
        _normalized(check.expected) == _normalized(check.observed) for check in checks
    )
    return _rate_metric(name, matches, len(checks))


def _boolean_metric(name: str, checks: list[BooleanJudgmentV1]) -> MetricResultV1:
    return _rate_metric(name, sum(check.passed for check in checks), len(checks))


def _sequence_metric(expected: list[str], observed: list[str]) -> MetricResultV1:
    total = max(len(expected), len(observed))
    matches = sum(
        _normalized(expected_item) == _normalized(observed_item)
        for expected_item, observed_item in zip(expected, observed, strict=False)
    )
    return _rate_metric("sequence_agreement", matches, total)


def _rate_metric(name: str, numerator: int, denominator: int) -> MetricResultV1:
    value = numerator / denominator if denominator else 0.0
    return MetricResultV1(
        metric=name,
        value=round(value, 6),
        unit="rate",
        numerator=numerator,
        denominator=denominator,
    )


def _count_metric(name: str, count: int, sample_size: int) -> MetricResultV1:
    return MetricResultV1(
        metric=name,
        value=float(count),
        unit="count",
        numerator=count,
        denominator=sample_size,
    )


def _score_metric(name: str, score_sum: int, ratings: int) -> MetricResultV1:
    value = score_sum / ratings if ratings else 0.0
    return MetricResultV1(
        metric=name,
        value=round(value, 6),
        unit="score_1_to_5",
        numerator=score_sum,
        denominator=ratings,
    )


def _evidence_ids(candidate: dict[str, object]) -> list[UUID]:
    evidence_ids: set[UUID] = set()
    for value in _walk(candidate):
        if not isinstance(value, dict):
            continue
        raw_id = value.get("evidence_id")
        if not isinstance(raw_id, str | UUID):
            continue
        try:
            evidence_ids.add(UUID(str(raw_id)))
        except ValueError:
            continue
    return sorted(evidence_ids, key=str)


def _walk(value: object) -> Iterable[object]:
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _string_values(value: object) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from _string_values(child)
    elif isinstance(value, list):
        for child in value:
            yield from _string_values(child)


def _dict_items(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _contains_term(candidate_text: str, term: str) -> bool:
    if not term:
        return False
    return re.search(rf"(?<!\w){re.escape(term)}(?!\w)", candidate_text) is not None


def _normalized(value: object) -> str:
    return str(value).strip().casefold()


def _claim_disclosure_preservation(
    concepts: list[dict[str, object]],
    prohibited_claims: list[str],
    required_disclosures: list[str],
) -> tuple[int, int]:
    expected_claims = {_normalized(item) for item in prohibited_claims}
    expected_disclosures = {_normalized(item) for item in required_disclosures}
    obligations = expected_claims | expected_disclosures
    if not obligations:
        return 1, 1
    preserved = 0
    for concept in concepts:
        claims = {_normalized(item) for item in _strings(concept.get("claims_to_avoid"))}
        disclosures = {
            _normalized(item) for item in _strings(concept.get("required_disclosures"))
        }
        preserved += len(expected_claims.intersection(claims))
        preserved += len(expected_disclosures.intersection(disclosures))
    return preserved, len(obligations) * len(concepts)


def _pattern_traceability(
    candidate: dict[str, object],
    concepts: list[dict[str, object]],
    expected_ids: set[UUID],
) -> tuple[int, int]:
    if not expected_ids:
        return 0, 0
    traced = sum(
        _uuid_set(concept.get("source_pattern_kit_version_ids")) == expected_ids
        for concept in concepts
    )
    provenance = candidate.get("provenance")
    provenance_ids: object = None
    if isinstance(provenance, dict):
        provenance_ids = provenance.get("pattern_kit_version_ids")
    traced += _uuid_set(provenance_ids) == expected_ids
    return traced, len(concepts) + 1


def _strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _uuid_set(value: object) -> set[UUID]:
    values: set[UUID] = set()
    for item in _strings(value):
        try:
            values.add(UUID(item))
        except ValueError:
            continue
    return values


def _campaign_pack_compiles(payload: dict[str, object]) -> bool:
    try:
        brief = CampaignPackBriefV1.model_validate(payload)
        requirements = compile_campaign_requirements(brief.model_dump(mode="json"))
        CompiledRequirementsSnapshotV2(requirements=requirements)
    except (ValidationError, ValueError, TypeError):
        return False
    return True


def _preflight_snapshot_compiles(payload: dict[str, object]) -> bool:
    try:
        CompiledRequirementsSnapshotV2.model_validate(payload)
    except ValidationError:
        return False
    return True


def _aggregate_pattern_metrics(
    cases: list[PatternKitCaseResultV1],
) -> PatternKitMetricsResultV1:
    return PatternKitMetricsResultV1(
        schema_validity=_aggregate(item.metrics.schema_validity for item in cases),
        evidence_resolution=_aggregate(item.metrics.evidence_resolution for item in cases),
        source_field_agreement=_aggregate(
            item.metrics.source_field_agreement for item in cases
        ),
        sequence_agreement=_aggregate(item.metrics.sequence_agreement for item in cases),
        applicability_agreement=_aggregate(
            item.metrics.applicability_agreement for item in cases
        ),
        keep_change_avoid_agreement=_aggregate(
            item.metrics.keep_change_avoid_agreement for item in cases
        ),
        cross_category_leakage=_aggregate(
            item.metrics.cross_category_leakage for item in cases
        ),
        unsupported_generalization=_aggregate(
            item.metrics.unsupported_generalization for item in cases
        ),
    )


def _aggregate_viral_metrics(
    cases: list[ViralKitCaseResultV1],
) -> ViralKitMetricsResultV1:
    return ViralKitMetricsResultV1(
        schema_validity=_aggregate(item.metrics.schema_validity for item in cases),
        product_grounding=_aggregate(item.metrics.product_grounding for item in cases),
        constraint_preservation=_aggregate(
            item.metrics.constraint_preservation for item in cases
        ),
        diversity_pass_rate=_aggregate(
            item.metrics.diversity_pass_rate for item in cases
        ),
        buyer_creator_separation=_aggregate(
            item.metrics.buyer_creator_separation for item in cases
        ),
        claim_disclosure_preservation=_aggregate(
            item.metrics.claim_disclosure_preservation for item in cases
        ),
        pattern_kit_traceability=_aggregate(
            item.metrics.pattern_kit_traceability for item in cases
        ),
        campaign_pack_compile=_aggregate(
            item.metrics.campaign_pack_compile for item in cases
        ),
        preflight_compile=_aggregate(item.metrics.preflight_compile for item in cases),
        human_usefulness=_aggregate(item.metrics.human_usefulness for item in cases),
    )


def _aggregate(metrics: Iterable[MetricResultV1]) -> MetricResultV1:
    items = list(metrics)
    first = items[0]
    numerator = sum(item.numerator for item in items)
    denominator = sum(item.denominator for item in items)
    value = numerator if first.unit == "count" else numerator / denominator if denominator else 0
    return MetricResultV1(
        metric=first.metric,
        value=round(value, 6),
        unit=first.unit,
        numerator=numerator,
        denominator=denominator,
    )
