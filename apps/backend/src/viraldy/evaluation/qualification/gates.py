from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping, Sequence
from urllib.parse import parse_qsl, urlsplit

from viraldy.evaluation.golden import (
    GoldenFixtureV1,
    GoldenSemanticOutputV1,
    validate_golden_semantics,
)
from viraldy.evaluation.qualification.contracts import (
    GateCategory,
    GateResultV1,
    OperationExecutionV1,
    QualificationCaseExecutionV1,
    QualificationMode,
    SafeQualificationConfigV1,
)

_SENSITIVE_KEYS = frozenset(
    {
        "api_key",
        "authorization",
        "credential",
        "password",
        "presigned_url",
        "secret",
        "signed_url",
        "token",
    }
)
_SIGNED_QUERY_KEYS = frozenset(
    {
        "awsaccesskeyid",
        "credential",
        "expires",
        "googleaccessid",
        "signature",
        "sig",
        "token",
        "x-amz-credential",
        "x-amz-signature",
    }
)
_SECRET_VALUE = re.compile(r"\bsk-[A-Za-z0-9_-]{8,}\b")


def configuration_gates(
    config: SafeQualificationConfigV1,
) -> list[GateResultV1]:
    live_route_valid = config.mode != "live" or config.provider_route == "openai"
    live_key_valid = config.mode != "live" or config.api_key_configured
    prompts_registered = bool(config.operation_configs) and all(
        operation.prompt_name
        and operation.prompt_version
        and operation.schema_version
        and operation.model
        for operation in config.operation_configs
    )
    return [
        _boolean_gate(
            "provider_route",
            "configuration",
            live_route_valid,
            "live mode must route to the native openai provider",
        ),
        _boolean_gate(
            "live_api_key_configured",
            "configuration",
            live_key_valid,
            "a provider credential is required only in live mode",
        ),
        _boolean_gate(
            "store_responses_disabled",
            "configuration",
            not config.store_responses,
            "OpenAI request storage must remain disabled",
        ),
        _boolean_gate(
            "operation_registry_complete",
            "configuration",
            prompts_registered,
            "every qualified operation needs a model, prompt, and schema version",
        ),
    ]


def case_hard_gates(
    mode: QualificationMode,
    fixture: GoldenFixtureV1,
    execution: QualificationCaseExecutionV1,
) -> list[GateResultV1]:
    operations = execution.operation_results
    observed = execution.semantic_output
    sensitive_findings = list(
        _sensitive_findings(
            {
                "semantic_output": observed.model_dump(mode="json"),
                "operation_results": [
                    result.model_dump(mode="json") for result in operations
                ],
                "application_evidence": execution.application_evidence,
            }
        )
    )
    live_ids = [result.provider_request_id for result in operations]
    if execution.execution_scope == "contract":
        live_ids.append(execution.semantic_provider_request_id)
    live_provider_results = [
        result.provider == "openai" for result in operations
    ]
    application_e2e = execution.execution_scope == "application_e2e"
    return [
        _rate_gate(
            "pydantic_valid_final_outputs",
            "hard",
            sum(result.output_valid for result in operations) + 1,
            len(operations) + 1,
            1.0,
            "all operation and semantic outputs must validate",
        ),
        _rate_gate(
            "source_version_references",
            "hard",
            sum(result.source_version_references_valid for result in operations),
            len(operations),
            1.0,
            "all source and version references must resolve",
        ),
        _rate_gate(
            "evidence_ids",
            "hard",
            sum(result.evidence_ids_valid for result in operations),
            len(operations),
            1.0,
            "all emitted evidence IDs must be valid",
        ),
        _rate_gate(
            "timestamps_inside_media_duration",
            "hard",
            sum(result.timestamps_valid for result in operations)
            + int(_golden_timestamps_valid(fixture, observed)),
            len(operations) + 1,
            1.0,
            "all timestamps must be ordered and inside the asset duration",
        ),
        _count_gate(
            "silent_fixture_fallbacks",
            "hard",
            sum(result.silent_fixture_fallback for result in operations),
            len(operations),
            0,
            "live execution must never return fixture or mock output",
        ),
        _count_gate(
            "sensitive_material_leaks",
            "hard",
            len(sensitive_findings),
            len(operations) + 1,
            0,
            "outputs must not contain keys, tokens, or signed URLs",
        ),
        _boolean_gate(
            "exactly_three_viral_kit_concepts",
            "hard",
            len(observed.concepts) == 3,
            "ViralKit qualification output must contain exactly three concepts",
        ),
        _boolean_gate(
            "required_hard_blockers_enforced",
            "hard",
            _hard_blockers_match(fixture, observed),
            "observed hard blockers must exactly match the Golden expectations",
        ),
        _boolean_gate(
            "application_model_runs_persisted",
            "hard",
            not application_e2e or execution.model_runs_persisted,
            (
                "application qualification requires completed persisted model runs "
                "for every qualified operation"
            ),
        ),
        _boolean_gate(
            "application_workspace_deleted",
            "hard",
            not application_e2e or execution.workspace_deleted,
            (
                "application qualification must verify database and object cleanup "
                "for its isolated workspace"
            ),
        ),
        _boolean_gate(
            "live_provider_request_ids",
            "hard",
            mode != "live" or bool(live_ids) and all(live_ids),
            (
                "every live OpenAI operation must include provider_request_id; "
                "contract-only semantic projections must include one as well"
            ),
        ),
        _boolean_gate(
            "live_native_provider_results",
            "hard",
            mode != "live"
            or bool(live_provider_results)
            and all(live_provider_results),
            "every live operation must be returned by the native openai provider",
        ),
    ]


def aggregate_hard_gates(
    mode: QualificationMode,
    case_gates: Sequence[Sequence[GateResultV1]],
    operation_results: Sequence[OperationExecutionV1] = (),
) -> list[GateResultV1]:
    flattened = [gate for gates in case_gates for gate in gates]
    if flattened:
        names = list(dict.fromkeys(gate.gate for gate in flattened))
        return [
            _aggregate_gate(name, "hard", [gate for gate in flattened if gate.gate == name])
            for name in names
        ]

    sensitive_findings = list(
        _sensitive_findings(
            [result.model_dump(mode="json") for result in operation_results]
        )
    )
    live_ids_valid = mode != "live" or (
        bool(operation_results)
        and all(result.provider_request_id for result in operation_results)
    )
    live_providers_valid = mode != "live" or (
        bool(operation_results)
        and all(result.provider == "openai" for result in operation_results)
    )
    return [
        _rate_gate(
            "pydantic_valid_final_outputs",
            "hard",
            sum(result.output_valid for result in operation_results),
            len(operation_results),
            1.0,
            "all operation outputs must validate",
        ),
        _rate_gate(
            "source_version_references",
            "hard",
            sum(
                result.source_version_references_valid
                for result in operation_results
            ),
            len(operation_results),
            1.0,
            "all source and version references must resolve",
        ),
        _rate_gate(
            "evidence_ids",
            "hard",
            sum(result.evidence_ids_valid for result in operation_results),
            len(operation_results),
            1.0,
            "all emitted evidence IDs must be valid",
        ),
        _rate_gate(
            "timestamps_inside_media_duration",
            "hard",
            sum(result.timestamps_valid for result in operation_results),
            len(operation_results),
            1.0,
            "all timestamps must be valid",
        ),
        _count_gate(
            "silent_fixture_fallbacks",
            "hard",
            sum(result.silent_fixture_fallback for result in operation_results),
            len(operation_results),
            0,
            "live execution must never return fixture or mock output",
        ),
        _count_gate(
            "sensitive_material_leaks",
            "hard",
            len(sensitive_findings),
            len(operation_results),
            0,
            "outputs must not contain keys, tokens, or signed URLs",
        ),
        _boolean_gate(
            "live_provider_request_ids",
            "hard",
            live_ids_valid,
            "every live OpenAI operation must include provider_request_id",
        ),
        _boolean_gate(
            "live_native_provider_results",
            "hard",
            live_providers_valid,
            "every live operation must be returned by the native openai provider",
        ),
    ]


def semantic_gates(
    pairs: Sequence[tuple[GoldenFixtureV1, GoldenSemanticOutputV1]],
) -> list[GateResultV1]:
    total_semantic_checks = 0
    passed_semantic_checks = 0
    expected_blockers: list[str] = []
    observed_blockers: list[str] = []
    action_matches = 0
    action_total = 0
    critical_hallucinations = 0
    disclosure_false_satisfaction = 0
    personalization_misses = 0
    generic_outputs = 0
    creator_scores: list[int] = []
    campaign_scores: list[int] = []

    for fixture, output in pairs:
        validation = validate_golden_semantics(fixture, output)
        total_semantic_checks += len(validation.checks)
        passed_semantic_checks += sum(check.passed for check in validation.checks)
        expected_by_asset = {
            item.asset_id: item for item in fixture.preflight_expectations
        }
        observed_by_asset = {
            item.asset_id: item for item in output.preflight_results
        }
        if output.product_name != fixture.product_name:
            critical_hallucinations += 1
        generic_outputs += int(_is_generic_output(fixture, output))
        creator_scores.append(_creator_usefulness_score(fixture, output))
        campaign_scores.append(_campaign_pack_usability_score(fixture, output))

        for asset_id, expected in expected_by_asset.items():
            observed = observed_by_asset.get(asset_id)
            expected_blockers.extend(expected.hard_blocker_codes)
            if observed is None:
                action_total += 1
                if expected.personalization_expected != expected.personalization_observed:
                    personalization_misses += 1
                continue
            observed_blockers.extend(observed.hard_blocker_codes)
            action_total += 1
            action_matches += int(observed.action == expected.action)
            if (
                expected.disclosure_status != "satisfied"
                and observed.disclosure_status == "satisfied"
            ):
                disclosure_false_satisfaction += 1
            if (
                expected.personalization_expected is not None
                and expected.personalization_expected
                != expected.personalization_observed
                and "PERSONALIZATION_MISMATCH"
                not in observed.hard_blocker_codes
            ):
                personalization_misses += 1

    expected_set = _counted(expected_blockers)
    observed_set = _counted(observed_blockers)
    true_positive = sum(
        min(count, observed_set.get(code, 0))
        for code, count in expected_set.items()
    )
    false_positive = sum(
        max(count - expected_set.get(code, 0), 0)
        for code, count in observed_set.items()
    )
    expected_total = sum(expected_set.values())
    observed_total = sum(observed_set.values())
    return [
        _rate_gate(
            "golden_semantic_equivalence",
            "semantic",
            passed_semantic_checks,
            total_semantic_checks,
            1.0,
            "all authoritative Golden semantic checks must pass",
        ),
        _rate_gate(
            "hard_blocker_recall",
            "semantic",
            true_positive,
            expected_total,
            0.90,
            "required hard blockers must be recalled",
        ),
        _maximum_rate_gate(
            "false_hard_blocker_rate",
            false_positive,
            observed_total,
            0.10,
            "unexpected hard blockers must remain below the allowed rate",
        ),
        _rate_gate(
            "action_label_agreement",
            "semantic",
            action_matches,
            action_total,
            0.80,
            "Preflight action labels must agree with Golden expectations",
        ),
        _count_gate(
            "critical_product_fact_hallucinations",
            "semantic",
            critical_hallucinations,
            len(pairs),
            0,
            "critical product identity hallucinations are not allowed",
        ),
        _count_gate(
            "required_disclosure_false_satisfaction",
            "semantic",
            disclosure_false_satisfaction,
            action_total,
            0,
            "a missing disclosure must never be marked satisfied",
        ),
        _count_gate(
            "personalization_mismatch_misses",
            "semantic",
            personalization_misses,
            action_total,
            0,
            "personalization mismatches must remain hard blockers",
        ),
        _maximum_rate_gate(
            "generic_output_rate",
            generic_outputs,
            len(pairs),
            0.05,
            "outputs must remain product- and objective-specific",
        ),
        _minimum_score_gate(
            "creator_message_usefulness",
            creator_scores,
            4.0,
            "deterministic Golden rubric: exact fixes, preserved strengths, and action",
        ),
        _minimum_score_gate(
            "campaign_pack_usability",
            campaign_scores,
            4.0,
            "deterministic Golden rubric: product, objective, pattern, and concept specificity",
        ),
    ]


def _golden_timestamps_valid(
    fixture: GoldenFixtureV1,
    output: GoldenSemanticOutputV1,
) -> bool:
    durations = {asset.asset_id: asset.duration_ms for asset in fixture.assets}
    for asset in fixture.assets:
        values = _timestamp_values(asset.observations)
        if any(value < 0 or value > asset.duration_ms for value in values):
            return False
        start = asset.observations.get("disclosure_start_ms")
        end = asset.observations.get("disclosure_end_ms")
        if isinstance(start, int) and isinstance(end, int) and end < start:
            return False
    for result in output.preflight_results:
        duration = durations.get(result.asset_id)
        if duration is None:
            return False
        values = [
            value
            for value in (
                result.product_required_before_ms,
                result.product_first_appearance_ms,
            )
            if value is not None
        ]
        if any(value < 0 or value > duration for value in values):
            return False
    return True


def _timestamp_values(value: object, key: str = "") -> Iterable[int]:
    if isinstance(value, Mapping):
        for child_key, child in value.items():
            yield from _timestamp_values(child, str(child_key))
    elif isinstance(value, list):
        for child in value:
            yield from _timestamp_values(child, key)
    elif isinstance(value, int) and key.endswith("_ms"):
        yield value


def _hard_blockers_match(
    fixture: GoldenFixtureV1,
    output: GoldenSemanticOutputV1,
) -> bool:
    expected = {
        item.asset_id: sorted(item.hard_blocker_codes)
        for item in fixture.preflight_expectations
    }
    observed = {
        item.asset_id: sorted(item.hard_blocker_codes)
        for item in output.preflight_results
        if item.asset_id in expected
    }
    return expected == observed


def _is_generic_output(
    fixture: GoldenFixtureV1,
    output: GoldenSemanticOutputV1,
) -> bool:
    serialized = json.dumps(
        output.model_dump(mode="json"),
        ensure_ascii=True,
        sort_keys=True,
    ).casefold()
    if fixture.product_name.casefold() not in serialized:
        return True
    if fixture.objective.casefold() not in serialized:
        return True
    if len(output.concepts) != 3:
        return True
    concept_signatures = {
        (
            concept.strategic_axis.casefold(),
            concept.buyer_persona.casefold(),
            concept.creator_persona.casefold(),
            concept.spoken_hook.casefold(),
        )
        for concept in output.concepts
    }
    return len(concept_signatures) != 3 or any(
        len(set(concept.diversity_axes)) < 2 for concept in output.concepts
    )


def _creator_usefulness_score(
    fixture: GoldenFixtureV1,
    output: GoldenSemanticOutputV1,
) -> int:
    observed = {item.asset_id: item for item in output.preflight_results}
    exact_actions = all(
        observed.get(expected.asset_id) is not None
        and observed[expected.asset_id].action == expected.action
        for expected in fixture.preflight_expectations
    )
    exact_blockers = _hard_blockers_match(fixture, output)
    exact_fixes = all(
        observed.get(expected.asset_id) is not None
        and set(observed[expected.asset_id].high_priority_fix_codes)
        == set(expected.high_priority_fix_codes)
        for expected in fixture.preflight_expectations
    )
    strengths_preserved = all(
        observed.get(expected.asset_id) is not None
        and bool(observed[expected.asset_id].strengths_to_preserve)
        for expected in fixture.preflight_expectations
    )
    product_specific = output.product_name == fixture.product_name
    return sum(
        (
            exact_actions,
            exact_blockers,
            exact_fixes,
            strengths_preserved,
            product_specific,
        )
    )


def _campaign_pack_usability_score(
    fixture: GoldenFixtureV1,
    output: GoldenSemanticOutputV1,
) -> int:
    semantic_checks = validate_golden_semantics(fixture, output).checks
    pattern_semantics = next(
        (
            check.passed
            for check in semantic_checks
            if check.check == "pattern_semantics"
        ),
        False,
    )
    return sum(
        (
            output.product_name == fixture.product_name,
            output.objective == fixture.objective,
            pattern_semantics,
            len(output.concepts) == 3,
            all(len(set(concept.diversity_axes)) >= 2 for concept in output.concepts),
        )
    )


def _sensitive_findings(value: object, path: str = "$") -> Iterable[str]:
    if isinstance(value, Mapping):
        for raw_key, nested in value.items():
            key = str(raw_key)
            if key.casefold() in _SENSITIVE_KEYS:
                yield f"{path}.{key}"
            yield from _sensitive_findings(nested, f"{path}.{key}")
        return
    if isinstance(value, list):
        for index, nested in enumerate(value):
            yield from _sensitive_findings(nested, f"{path}[{index}]")
        return
    if not isinstance(value, str):
        return
    if _SECRET_VALUE.search(value):
        yield path
    parsed = urlsplit(value)
    if parsed.scheme in {"http", "https"}:
        query_keys = {key.casefold() for key, _ in parse_qsl(parsed.query)}
        if query_keys & _SIGNED_QUERY_KEYS:
            yield path


def _counted(values: Iterable[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return counts


def _boolean_gate(
    name: str,
    category: GateCategory,
    passed: bool,
    detail: str,
) -> GateResultV1:
    return GateResultV1(
        gate=name,
        category=category,
        passed=passed,
        value=float(passed),
        threshold="required",
        numerator=float(passed),
        denominator=1,
        detail=detail,
    )


def _rate_gate(
    name: str,
    category: GateCategory,
    numerator: int,
    denominator: int,
    minimum: float,
    detail: str,
) -> GateResultV1:
    value = numerator / denominator if denominator else 0.0
    return GateResultV1(
        gate=name,
        category=category,
        passed=denominator > 0 and value >= minimum,
        value=round(value, 6),
        threshold=f">= {minimum:.2f}",
        numerator=numerator,
        denominator=denominator,
        detail=detail,
    )


def _maximum_rate_gate(
    name: str,
    numerator: int,
    denominator: int,
    maximum: float,
    detail: str,
) -> GateResultV1:
    value = numerator / denominator if denominator else 0.0
    return GateResultV1(
        gate=name,
        category="semantic",
        passed=value <= maximum,
        value=round(value, 6),
        threshold=f"<= {maximum:.2f}",
        numerator=numerator,
        denominator=denominator,
        detail=detail,
    )


def _count_gate(
    name: str,
    category: GateCategory,
    count: int,
    sample_size: int,
    maximum: int,
    detail: str,
) -> GateResultV1:
    return GateResultV1(
        gate=name,
        category=category,
        passed=count <= maximum,
        value=float(count),
        threshold=f"<= {maximum}",
        numerator=count,
        denominator=sample_size,
        detail=detail,
    )


def _minimum_score_gate(
    name: str,
    scores: Sequence[int],
    minimum: float,
    detail: str,
) -> GateResultV1:
    score_sum = sum(scores)
    value = score_sum / len(scores) if scores else 0.0
    return GateResultV1(
        gate=name,
        category="semantic",
        passed=bool(scores) and value >= minimum,
        value=round(value, 6),
        threshold=f">= {minimum:.1f}/5",
        numerator=score_sum,
        denominator=len(scores),
        detail=detail,
    )


def _aggregate_gate(
    name: str,
    category: GateCategory,
    gates: Sequence[GateResultV1],
) -> GateResultV1:
    numerator = sum(gate.numerator for gate in gates)
    denominator = sum(gate.denominator for gate in gates)
    if name in {
        "silent_fixture_fallbacks",
        "sensitive_material_leaks",
    }:
        return _count_gate(
            name,
            category,
            int(numerator),
            denominator,
            0,
            gates[0].detail,
        )
    return GateResultV1(
        gate=name,
        category=category,
        passed=all(gate.passed for gate in gates),
        value=round(numerator / denominator, 6) if denominator else 0.0,
        threshold=gates[0].threshold,
        numerator=numerator,
        denominator=denominator,
        detail=gates[0].detail,
    )
