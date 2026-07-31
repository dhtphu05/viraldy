from __future__ import annotations

import re
from collections.abc import Iterable
from typing import cast
from uuid import UUID

from pydantic import ValidationError

from viraldy.evaluation.tiktok_scorer_contracts import (
    ScorerQualificationIssueV1,
    TikTokScorerCaseEvaluationV1,
    TikTokScorerEvaluationDatasetV1,
    TikTokScorerEvaluationReportV1,
    TikTokScorerEvaluationSampleV1,
    TikTokScorerMetricResultV1,
    TikTokScorerMetricsV1,
)
from viraldy.modules.tiktok_scorer.contracts_v2 import (
    TikTokScoreComparisonV1,
    TikTokScoreResultV2,
)

_GENERIC_FIX_TEXT = {
    "improve the hook",
    "show the product earlier",
    "add a stronger cta",
}
_EDIT_FIX_TYPES = {
    "edit_existing_footage",
    "trim_or_reorder",
    "add_overlay",
    "replace_overlay_copy",
    "replace_spoken_line",
}
_RESHOOT_FIX_TYPES = {"reshoot_scene", "add_missing_scene"}
_UNIVERSAL_PRODUCT_TIMING_MARKERS = {
    "product_before_2s",
    "product before 2s",
    "product before 2 seconds",
}


def evaluate_tiktok_scorer_dataset(
    dataset: TikTokScorerEvaluationDatasetV1,
) -> TikTokScorerEvaluationReportV1:
    cases = [
        _evaluate_case(sample)
        for sample in sorted(dataset.samples, key=lambda item: item.golden_case.case_id)
    ]
    aggregate = _aggregate_metrics([case.metrics for case in cases])
    return TikTokScorerEvaluationReportV1(
        dataset_id=dataset.dataset_id,
        cases=cases,
        aggregate=aggregate,
        qualification_passed=all(not case.qualification_issues for case in cases),
        limitations=[
            "Synthetic evaluation does not establish real-world accuracy.",
            "Precision, recall, agreement, usefulness, and clarity apply only to explicit "
            "labels present in this dataset.",
            "Human-review metrics remain unmeasured when explicit human labels are absent.",
        ],
    )


def _evaluate_case(sample: TikTokScorerEvaluationSampleV1) -> TikTokScorerCaseEvaluationV1:
    candidate = sample.candidate_score
    schema_valid = _score_schema_valid(candidate)
    evidence_refs = _evidence_references(candidate)
    known_evidence = {str(item.evidence_id) for item in sample.golden_case.evidence}
    valid_evidence = sum(_normalized_uuid(item) in known_evidence for item in evidence_refs)
    timestamp_ranges = _timestamp_ranges(candidate)
    in_range = sum(
        _range_is_valid(item, duration_ms=sample.golden_case.duration_ms)
        for item in timestamp_ranges
    )

    expected_dimensions = sample.golden_case.expected_dimension_bands
    observed_dimensions = {
        str(item.get("code")): item
        for item in _dict_items(candidate.get("dimensions"))
        if item.get("code") is not None
    }
    dimension_matches = sum(
        _dimension_band(observed_dimensions.get(code)) == expected_band
        for code, expected_band in expected_dimensions.items()
    )

    expected_blockers = set(sample.golden_case.expected_hard_blocker_codes)
    observed_blockers = _hard_blocker_codes(candidate)
    true_blockers = len(expected_blockers & observed_blockers)
    false_blockers = len(observed_blockers - expected_blockers)

    observed_actions = {
        str(item.get("code")): item
        for item in _dict_items(candidate.get("required_fixes"))
        if item.get("code") is not None
    }
    edit_reshoot_matches = 0
    edit_reshoot_total = 0
    owner_matches = 0
    for expected in sample.golden_case.expected_actions:
        observed = observed_actions.get(expected.action_code)
        expected_family = _fix_family(expected.fix_type)
        if expected_family is not None:
            edit_reshoot_total += 1
            if observed is not None and _fix_family(observed.get("fix_type")) == expected_family:
                edit_reshoot_matches += 1
        if observed is not None and observed.get("owner_role") == expected.owner_role:
            owner_matches += 1

    usefulness_scores = _scores_for_observed_actions(
        sample.human_labels.fix_action_usefulness_scores,
        observed_actions,
    )
    clarity_scores = _scores_for_observed_actions(
        sample.human_labels.seller_clarity_scores,
        observed_actions,
    )
    revision_matches, revision_total = _revision_agreement(sample)
    generic_count = sum(_is_generic_action(action) for action in observed_actions.values())

    metrics = TikTokScorerMetricsV1(
        schema_valid_rate=_rate("schema_valid_rate", int(schema_valid), 1),
        evidence_validity=_rate(
            "evidence_validity",
            valid_evidence,
            len(evidence_refs),
            reason="No evidence references were emitted.",
        ),
        timestamp_accuracy=_rate(
            "timestamp_accuracy",
            in_range,
            len(timestamp_ranges),
            reason="No timestamp ranges were emitted.",
        ),
        out_of_range_timestamp_rate=_rate(
            "out_of_range_timestamp_rate",
            len(timestamp_ranges) - in_range,
            len(timestamp_ranges),
            reason="No timestamp ranges were emitted.",
        ),
        dimension_agreement=_rate(
            "dimension_agreement",
            dimension_matches,
            len(expected_dimensions),
            reason="This case has no explicit dimension labels.",
        ),
        blocker_precision=_rate(
            "blocker_precision",
            true_blockers,
            len(observed_blockers),
            reason="No hard blockers were emitted, so precision is undefined.",
        ),
        blocker_recall=_rate(
            "blocker_recall",
            true_blockers,
            len(expected_blockers),
            reason="This case has no expected hard-blocker labels.",
        ),
        false_hard_blocker_rate=_rate(
            "false_hard_blocker_rate",
            false_blockers,
            len(observed_blockers),
            reason="No hard blockers were emitted.",
        ),
        fix_action_usefulness=_average_score(
            "fix_action_usefulness",
            usefulness_scores,
            reason="No explicit human fix-usefulness labels were provided.",
        ),
        edit_vs_reshoot_agreement=_rate(
            "edit_vs_reshoot_agreement",
            edit_reshoot_matches,
            edit_reshoot_total,
            reason="This case has no explicit edit-versus-reshoot labels.",
        ),
        seller_action_agreement=_rate(
            "seller_action_agreement",
            owner_matches,
            len(sample.golden_case.expected_actions),
            reason="This case has no explicit action-owner labels.",
        ),
        seller_clarity=_average_score(
            "seller_clarity",
            clarity_scores,
            reason="No explicit human seller-clarity labels were provided.",
        ),
        revision_resolution_accuracy=_rate(
            "revision_resolution_accuracy",
            revision_matches,
            revision_total,
            reason="This case has no explicit revision-resolution labels.",
        ),
        latency=_average_runtime(
            "latency",
            sample.latency_ms,
            unit="milliseconds",
            reason="No measured scorer latency was supplied.",
        ),
        cost_per_score=_average_runtime(
            "cost_per_score",
            sample.cost_usd,
            unit="usd",
            reason="No measured scorer cost was supplied.",
        ),
        generic_output_rate=_rate(
            "generic_output_rate",
            generic_count,
            len(observed_actions),
            reason="No fix actions were emitted.",
            target_max=0.05,
        ),
    )
    return TikTokScorerCaseEvaluationV1(
        case_id=sample.golden_case.case_id,
        categories=sample.golden_case.categories,
        metrics=metrics,
        qualification_issues=_qualification_issues(sample, schema_valid=schema_valid),
    )


def _score_schema_valid(candidate: dict[str, object]) -> bool:
    try:
        TikTokScoreResultV2.model_validate(candidate)
    except ValidationError:
        return False
    return True


def _comparison_schema_valid(candidate: dict[str, object]) -> bool:
    try:
        TikTokScoreComparisonV1.model_validate(candidate)
    except ValidationError:
        return False
    return True


def _revision_agreement(sample: TikTokScorerEvaluationSampleV1) -> tuple[int, int]:
    labels = sample.golden_case.expected_revision_labels
    comparison = sample.candidate_comparison
    if not labels or comparison is None or not _comparison_schema_valid(comparison):
        return 0, len(labels) if comparison is not None else 0
    observed = {
        str(item.get("action_code")): str(item.get("status"))
        for item in _dict_items(comparison.get("actions_verified"))
    }
    matches = sum(observed.get(label.action_code) == label.expected_status for label in labels)
    return matches, len(labels)


def _qualification_issues(
    sample: TikTokScorerEvaluationSampleV1,
    *,
    schema_valid: bool,
) -> list[ScorerQualificationIssueV1]:
    candidate = sample.candidate_score
    issues: dict[str, ScorerQualificationIssueV1] = {}

    def add(code: str, message: str) -> None:
        issues[code] = ScorerQualificationIssueV1(code=cast(object, code), message=message)

    if not schema_valid:
        add("schema_invalid", "Candidate does not validate against TikTokScoreResultV2.")

    known_evidence = {str(item.evidence_id) for item in sample.golden_case.evidence}
    refs = _evidence_references(candidate)
    if any(_normalized_uuid(item) not in known_evidence for item in refs):
        add("fabricated_evidence", "Candidate references evidence absent from the golden case.")

    ranges = _timestamp_ranges(candidate)
    if any(
        not _range_is_valid(item, duration_ms=sample.golden_case.duration_ms)
        for item in ranges
    ):
        add("timestamp_out_of_range", "Candidate emits a timestamp outside media duration.")

    fixes = _dict_items(candidate.get("required_fixes"))
    for finding in _dict_items(candidate.get("findings")):
        if finding.get("priority") not in {"P0", "P1"}:
            continue
        matching = [
            fix
            for fix in fixes
            if fix.get("source_finding_id") == finding.get("id")
            or fix.get("source_finding_code") == finding.get("code")
        ]
        if not _non_empty_list(finding.get("evidence_ids")) or any(
            not _non_empty_list(fix.get("evidence_ids")) for fix in matching
        ):
            add("p0_p1_evidence_missing", "Every P0/P1 finding and fix must cite evidence.")
        if not matching or any(
            not _non_empty_list(fix.get("completion_criteria")) for fix in matching
        ):
            add(
                "p0_p1_completion_missing",
                "Every P0/P1 finding must have a fix with completion criteria.",
            )

    expected_actions = {
        action.action_code: action for action in sample.golden_case.expected_actions
    }
    for fix in fixes:
        if fix.get("fix_type") not in _RESHOOT_FIX_TYPES:
            continue
        instructions = " ".join(_strings(fix.get("instructions"))).casefold()
        expected = expected_actions.get(str(fix.get("code")))
        if expected is not None:
            explained = all(
                requirement.casefold() in instructions
                for requirement in expected.capture_requirements
            )
        else:
            explained = any(
                verb in instructions for verb in ("capture", "film", "record", "show")
            )
        if not explained:
            add(
                "reshoot_capture_not_explained",
                "Every reshoot action must explain what physical evidence to capture.",
            )

    if any(
        upgrade.get("affects_score") is not False
        for upgrade in _dict_items(candidate.get("optional_upgrades"))
    ):
        add(
            "optional_upgrade_affects_score",
            "Optional Creative Direction upgrades must set affects_score=false.",
        )

    expected_blockers = set(sample.golden_case.expected_hard_blocker_codes)
    for finding in _dict_items(candidate.get("findings")):
        if finding.get("severity") != "hard":
            continue
        searchable = " ".join(
            str(finding.get(key, "")) for key in ("code", "rule_code", "title")
        ).casefold()
        universal = any(marker in searchable for marker in _UNIVERSAL_PRODUCT_TIMING_MARKERS)
        if universal and str(finding.get("code")) not in expected_blockers:
            add(
                "false_universal_product_timing_blocker",
                "A universal product-before-two-seconds hard blocker is not labeled for this case.",
            )

    return list(issues.values())


def _hard_blocker_codes(candidate: dict[str, object]) -> set[str]:
    return {
        str(item.get("code"))
        for item in _dict_items(candidate.get("findings"))
        if item.get("severity") == "hard" and item.get("applicability") == "applicable"
    }


def _dimension_band(item: dict[str, object] | None) -> str | None:
    if item is None:
        return None
    score = item.get("score")
    if score is None:
        return "not_evaluated"
    if not isinstance(score, int | float):
        return None
    if score < 40:
        return "low"
    if score < 70:
        return "medium"
    return "high"


def _fix_family(value: object) -> str | None:
    if value in _EDIT_FIX_TYPES:
        return "edit"
    if value in _RESHOOT_FIX_TYPES:
        return "reshoot"
    return None


def _scores_for_observed_actions(
    labels: dict[str, int],
    observed: dict[str, dict[str, object]],
) -> list[int]:
    return [score for action_code, score in labels.items() if action_code in observed]


def _is_generic_action(action: dict[str, object]) -> bool:
    values = [str(action.get("title", "")), *_strings(action.get("instructions"))]
    return any(_normalize_text(value) in _GENERIC_FIX_TEXT for value in values)


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().casefold()).rstrip(".!?")


def _evidence_references(candidate: dict[str, object]) -> list[str]:
    refs: list[str] = []
    for item in _walk(candidate):
        if not isinstance(item, dict):
            continue
        for key, value in item.items():
            if "evidence" not in key or not key.endswith(("_id", "_ids")):
                continue
            values = value if isinstance(value, list) else [value]
            refs.extend(str(ref) for ref in values if ref is not None)
    return refs


def _timestamp_ranges(candidate: dict[str, object]) -> list[tuple[object, object]]:
    ranges: list[tuple[object, object]] = []
    for item in _walk(candidate):
        if not isinstance(item, dict):
            continue
        if "start_ms" in item and "end_ms" in item:
            ranges.append((item["start_ms"], item["end_ms"]))
        for key, value in item.items():
            if key.endswith("range_ms") and isinstance(value, list | tuple) and len(value) == 2:
                ranges.append((value[0], value[1]))
            elif key.endswith("_ranges") and isinstance(value, list):
                ranges.extend(
                    (entry[0], entry[1])
                    for entry in value
                    if isinstance(entry, list | tuple) and len(entry) == 2
                )
        target_start = item.get("target_start_ms")
        target_duration = item.get("target_duration_ms")
        if isinstance(target_start, int) and isinstance(target_duration, int):
            ranges.append((target_start, target_start + target_duration))
    return ranges


def _range_is_valid(value: tuple[object, object], *, duration_ms: int) -> bool:
    start, end = value
    return (
        isinstance(start, int)
        and isinstance(end, int)
        and 0 <= start <= end <= duration_ms
    )


def _normalized_uuid(value: str) -> str | None:
    try:
        return str(UUID(value))
    except (ValueError, AttributeError):
        return None


def _rate(
    name: str,
    numerator: int,
    denominator: int,
    *,
    reason: str | None = None,
    target_max: float | None = None,
) -> TikTokScorerMetricResultV1:
    if denominator == 0:
        return _unmeasured(
            name,
            unit="rate",
            reason=reason or "No labeled examples.",
            target_max=target_max,
        )
    value = numerator / denominator
    return TikTokScorerMetricResultV1(
        metric=name,
        status="measured",
        value=round(value, 6),
        unit="rate",
        numerator=numerator,
        denominator=denominator,
        target_max=target_max,
        target_met=value <= target_max if target_max is not None else None,
    )


def _average_score(
    name: str,
    scores: list[int],
    *,
    reason: str,
) -> TikTokScorerMetricResultV1:
    if not scores:
        return _unmeasured(name, unit="score_1_to_5", reason=reason)
    return TikTokScorerMetricResultV1(
        metric=name,
        status="measured",
        value=round(sum(scores) / len(scores), 6),
        unit="score_1_to_5",
        numerator=sum(scores),
        denominator=len(scores),
    )


def _average_runtime(
    name: str,
    value: float | None,
    *,
    unit: str,
    reason: str,
) -> TikTokScorerMetricResultV1:
    if value is None:
        return _unmeasured(name, unit=unit, reason=reason)
    return TikTokScorerMetricResultV1(
        metric=name,
        status="measured",
        value=round(value, 6),
        unit=cast(object, unit),
        numerator=value,
        denominator=1,
    )


def _unmeasured(
    name: str,
    *,
    unit: str,
    reason: str,
    target_max: float | None = None,
) -> TikTokScorerMetricResultV1:
    return TikTokScorerMetricResultV1(
        metric=name,
        status="unmeasured",
        value=None,
        unit=cast(object, unit),
        numerator=None,
        denominator=0,
        reason=reason,
        target_max=target_max,
        target_met=None,
    )


def _aggregate_metrics(cases: list[TikTokScorerMetricsV1]) -> TikTokScorerMetricsV1:
    fields = TikTokScorerMetricsV1.model_fields
    return TikTokScorerMetricsV1.model_validate(
        {
            name: _aggregate_metric([getattr(case, name) for case in cases])
            for name in fields
        }
    )


def _aggregate_metric(
    metrics: list[TikTokScorerMetricResultV1],
) -> TikTokScorerMetricResultV1:
    measured = [metric for metric in metrics if metric.status == "measured"]
    template = metrics[0]
    if not measured:
        reasons = sorted({metric.reason for metric in metrics if metric.reason})
        return _unmeasured(
            template.metric,
            unit=template.unit,
            reason="; ".join(reasons) or "No labeled examples.",
            target_max=template.target_max,
        )
    numerator = sum(cast(float, metric.numerator) for metric in measured)
    denominator = sum(metric.denominator for metric in measured)
    value = numerator / denominator
    return TikTokScorerMetricResultV1(
        metric=template.metric,
        status="measured",
        value=round(value, 6),
        unit=template.unit,
        numerator=round(numerator, 6),
        denominator=denominator,
        target_max=template.target_max,
        target_met=(
            value <= template.target_max if template.target_max is not None else None
        ),
    )


def _walk(value: object) -> Iterable[object]:
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _dict_items(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _non_empty_list(value: object) -> bool:
    return isinstance(value, list) and bool(value)


__all__ = ["evaluate_tiktok_scorer_dataset"]
