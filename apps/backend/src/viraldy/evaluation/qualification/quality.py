from __future__ import annotations

from collections.abc import Mapping, Sequence

from viraldy.evaluation.qualification.contracts import (
    CaseQualityAssessmentV1,
    GateResultV1,
    ProductReadinessAssessmentV1,
    QualificationCaseResultV1,
    QualificationMode,
)

_BEST_OUTPUT_REQUIRED_SECTIONS = frozenset(
    {"pattern_kit", "viral_kit", "draft_1"}
)
_MEANINGFUL_VALUE_THRESHOLD = 4.0
_LIMITED_VALUE_THRESHOLD = 3.0


def assess_case_quality(
    *,
    mode: QualificationMode,
    passed: bool,
    hard_gates: Sequence[GateResultV1],
    semantic_gates: Sequence[GateResultV1],
    execution_scope: str,
    model_runs_persisted: bool,
    workspace_deleted: bool,
    application_evidence: Mapping[str, object],
) -> CaseQualityAssessmentV1:
    semantic_by_name = {gate.gate: gate for gate in semantic_gates}
    semantic_equivalence = _normalized_gate(
        semantic_by_name.get("golden_semantic_equivalence"),
        maximum=1.0,
    )
    creator_usefulness = _normalized_gate(
        semantic_by_name.get("creator_message_usefulness"),
        maximum=5.0,
    )
    campaign_usability = _normalized_gate(
        semantic_by_name.get("campaign_pack_usability"),
        maximum=5.0,
    )
    action_agreement = _normalized_gate(
        semantic_by_name.get("action_label_agreement"),
        maximum=1.0,
    )
    generic_gate = semantic_by_name.get("generic_output_rate")
    generic_output = generic_gate is None or not generic_gate.passed or generic_gate.value > 0
    specificity = 0.0 if generic_output else 1.0
    value_score = round(
        5
        * (
            semantic_equivalence * 0.30
            + creator_usefulness * 0.25
            + campaign_usability * 0.25
            + action_agreement * 0.10
            + specificity * 0.10
        ),
        2,
    )

    application_verified = (
        execution_scope == "application_e2e"
        and model_runs_persisted
        and workspace_deleted
    )
    if passed and application_verified:
        readiness_status = "qualified_case"
    elif passed:
        readiness_status = "contract_only"
    else:
        readiness_status = "not_ready"

    if value_score >= _MEANINGFUL_VALUE_THRESHOLD and not generic_output:
        value_status = "meaningful"
    elif value_score >= _LIMITED_VALUE_THRESHOLD:
        value_status = "limited"
    else:
        value_status = "weak"

    failed_gates = [
        gate.gate for gate in (*hard_gates, *semantic_gates) if not gate.passed
    ]
    evidence_complete = all(
        _non_empty_mapping(application_evidence.get(section))
        for section in _BEST_OUTPUT_REQUIRED_SECTIONS
    )
    best_output_eligible = (
        mode == "live"
        and readiness_status == "qualified_case"
        and value_status == "meaningful"
        and not generic_output
        and evidence_complete
    )

    strength_signals = [
        label
        for label, condition in (
            ("golden_semantics_match", semantic_equivalence == 1.0),
            ("creator_actions_are_useful", creator_usefulness >= 0.8),
            ("campaign_pack_is_usable", campaign_usability >= 0.8),
            ("preflight_actions_agree", action_agreement >= 0.8),
            ("output_is_product_specific", not generic_output),
            ("application_e2e_persisted_and_cleaned", application_verified),
        )
        if condition
    ]
    blockers = list(failed_gates)
    if passed and not application_verified:
        blockers.append("application_e2e_not_verified")
    if not evidence_complete:
        blockers.append("best_output_evidence_incomplete")

    return CaseQualityAssessmentV1(
        readiness_status=readiness_status,
        value_status=value_status,
        value_score=value_score,
        generic_output=generic_output,
        best_output_eligible=best_output_eligible,
        strength_signals=strength_signals,
        blockers=list(dict.fromkeys(blockers)),
        limitations=[
            "The score measures Golden semantic fit and workflow usefulness, not market lift.",
            "No qualification result guarantees virality, GMV, ROAS, conversion, or sales.",
        ],
    )


def assess_product_readiness(
    *,
    mode: QualificationMode,
    command: str,
    passed: bool,
    case_results: Sequence[QualificationCaseResultV1],
    global_gates: Sequence[GateResultV1],
) -> ProductReadinessAssessmentV1:
    case_count = len(case_results)
    qualified_case_count = sum(
        case.quality_assessment.readiness_status == "qualified_case"
        for case in case_results
    )
    best_output_count = sum(
        case.quality_assessment.best_output_eligible for case in case_results
    )
    value_score = round(
        sum(case.quality_assessment.value_score for case in case_results) / case_count,
        2,
    ) if case_count else 0.0
    generic_count = sum(
        case.quality_assessment.generic_output for case in case_results
    )
    generic_rate = round(generic_count / case_count, 6) if case_count else 0.0
    complete_live_matrix = (
        mode == "live"
        and command == "full_flow:all_cases"
        and case_count == 3
        and qualified_case_count == 3
    )
    product_ready = (
        complete_live_matrix
        and passed
        and value_score >= _MEANINGFUL_VALUE_THRESHOLD
        and generic_rate == 0
    )

    failed_gates = [gate.gate for gate in global_gates if not gate.passed]
    blockers = list(failed_gates)
    if mode != "live":
        blockers.append("real_openai_app_e2e_not_run")
    if command != "full_flow:all_cases" or case_count != 3:
        blockers.append("three_domain_matrix_incomplete")
    if generic_rate > 0:
        blockers.append("generic_outputs_detected")
    if value_score < _MEANINGFUL_VALUE_THRESHOLD and case_count:
        blockers.append("seller_value_below_threshold")

    if product_ready:
        status = "ready_for_limited_beta"
        reasons = [
            "All three Golden domains passed through the live application boundary.",
            (
                "Persisted model runs, semantic gates, cleanup, specificity, "
                "and value thresholds passed."
            ),
        ]
    elif complete_live_matrix:
        status = "not_ready"
        reasons = [
            "The complete live matrix ran, but one or more release gates did not pass."
        ]
    else:
        status = "insufficient_evidence"
        reasons = [
            "A complete three-domain live application qualification is required before readiness."
        ]

    return ProductReadinessAssessmentV1(
        status=status,
        product_ready=product_ready,
        value_score=value_score,
        generic_output_rate=generic_rate,
        qualified_case_count=qualified_case_count,
        best_output_count=best_output_count,
        reasons=reasons,
        blockers=list(dict.fromkeys(blockers)),
        limitations=[
            "Ready means eligible for a limited beta under the tested Golden scope.",
            "Seller validation and observed commercial performance remain separate evidence.",
        ],
    )


def _normalized_gate(gate: GateResultV1 | None, *, maximum: float) -> float:
    if gate is None or maximum <= 0:
        return 0.0
    return min(max(gate.value / maximum, 0.0), 1.0)


def _non_empty_mapping(value: object) -> bool:
    return isinstance(value, Mapping) and bool(value)
