from __future__ import annotations

import re
from collections.abc import Callable
from itertools import permutations

from viraldy.evaluation.golden.contracts import (
    GoldenFixtureV1,
    GoldenSemanticOutputV1,
    GoldenValidationCheckV1,
    GoldenValidationReportV1,
)

_PATTERN_ROLE_MARKERS: dict[str, tuple[tuple[str, ...], ...]] = {
    "home_travel_steamer": (
        ("deadline", "late", "rush", "time pressure", "before class", "urgent"),
        ("product reveal", "show product", "fast reveal", "product present"),
        (
            "same fabric",
            "same shirt",
            "garment proof",
            "before after",
            "observable proof",
            "wrinkle result",
        ),
    ),
    "pod_dog_mom_crewneck": (
        ("identity", "dog mom", "self purchase", "dog owner"),
        ("personalization", "personalized name", "pet name", "custom name"),
        ("emotional", "reaction", "gift", "recipient payoff"),
        ("ordering", "order detail", "input", "submit", "preview", "spelling"),
    ),
    "dropshipping_bag_sealer": (
        ("mess", "spill", "opened snack", "interruption"),
        ("one handed", "one hand", "compact demo", "sealing demo"),
        ("seal proof", "leak proof", "visible seal", "observable proof"),
        ("trust", "supported bag", "claim safe", "compatibility"),
    ),
}

_CONCEPT_ROLE_MARKERS: dict[str, tuple[tuple[str, ...], ...]] = {
    "home_travel_steamer": (
        ("class", "student", "dorm", "deadline", "late", "rush"),
        ("carry on", "travel", "hotel", "luggage", "traveler"),
        (
            "small space",
            "apartment",
            "drawer",
            "ironing board",
            "limited storage",
        ),
    ),
    "pod_dog_mom_crewneck": (
        ("identity", "dog mom", "self purchase", "dog owner"),
        ("gift", "reaction", "recipient", "partner", "friend", "emotional"),
        (
            "personalization",
            "ordering",
            "order",
            "submit",
            "input",
            "preview",
            "how to",
        ),
    ),
    "dropshipping_bag_sealer": (
        ("dorm", "student", "backpack", "college", "portable"),
        ("family", "parent", "pantry", "household", "organization"),
        ("travel", "packing", "carry on", "traveler", "luggage"),
    ),
}


def validate_golden_semantics(
    fixture: GoldenFixtureV1,
    output: GoldenSemanticOutputV1,
) -> GoldenValidationReportV1:
    checks: list[GoldenValidationCheckV1] = []

    def check(name: str, passed: bool, detail: str) -> None:
        checks.append(
            GoldenValidationCheckV1(check=name, passed=passed, detail=detail)
        )

    check(
        "scenario_identity",
        output.scenario_id == fixture.scenario_id,
        f"expected {fixture.scenario_id}; observed {output.scenario_id}",
    )
    check(
        "product_grounding",
        output.product_name == fixture.product_name,
        f"expected {fixture.product_name}; observed {output.product_name}",
    )
    check(
        "objective_grounding",
        output.objective == fixture.objective,
        f"expected {fixture.objective}; observed {output.objective}",
    )
    check(
        "pattern_semantics",
        _pattern_semantics_match(fixture, output),
        f"expected {fixture.pattern_name}; observed {output.pattern_name}",
    )
    check(
        "exactly_three_concepts",
        len(output.concepts) == 3,
        f"observed {len(output.concepts)} concepts",
    )

    check(
        "concept_role_coverage",
        _concept_roles_match(fixture, output),
        "three concepts must cover the domain-specific strategic roles",
    )
    signatures = {
        (
            _normalized(concept.strategic_axis),
            _normalized(concept.buyer_persona),
            _normalized(concept.creator_persona),
            _normalized(concept.spoken_hook),
        )
        for concept in output.concepts
    }
    check(
        "concept_set_diversity",
        len(signatures) == 3,
        "concepts must be strategically distinct rather than renamed duplicates",
    )
    for index, observed_concept in enumerate(output.concepts, start=1):
        concept_label = observed_concept.concept_id or str(index)
        check(
            f"buyer_creator_separation:{concept_label}",
            observed_concept.buyer_persona.casefold()
            != observed_concept.creator_persona.casefold(),
            "buyer and creator personas must remain separate",
        )
        check(
            f"spoken_overlay_separation:{concept_label}",
            (
                observed_concept.overlay_hook is None
                or observed_concept.overlay_hook.casefold()
                != observed_concept.spoken_hook.casefold()
            ),
            "spoken hook must not be copied automatically into overlay",
        )
        check(
            f"concept_diversity:{concept_label}",
            len(set(observed_concept.diversity_axes)) >= 2,
            "each concept must change at least two strategic axes",
        )

    expected_preflight = {
        result.asset_id: result for result in fixture.preflight_expectations
    }
    observed_preflight = {result.asset_id: result for result in output.preflight_results}
    for asset_id, expected_result in expected_preflight.items():
        observed_result = observed_preflight.get(asset_id)
        check(
            f"preflight_present:{asset_id}",
            observed_result is not None,
            "expected persisted preflight semantic projection",
        )
        if observed_result is None:
            continue
        _compare_preflight(expected_result, observed_result, check)

    check(
        "no_unsupported_performance_label",
        output.performance_evidence_attached or output.performance_label is None,
        "a winning or performance label requires attached performance evidence",
    )
    return GoldenValidationReportV1(
        scenario_id=fixture.scenario_id,
        passed=all(item.passed for item in checks),
        checks=checks,
    )


def _pattern_semantics_match(
    fixture: GoldenFixtureV1,
    output: GoldenSemanticOutputV1,
) -> bool:
    expected = _normalized(fixture.pattern_name)
    observed = _normalized(output.pattern_name)
    if expected == observed:
        return True
    role_markers = _PATTERN_ROLE_MARKERS.get(fixture.scenario_id)
    if role_markers is None:
        return False
    matched_roles = sum(
        _contains_any(observed, markers) for markers in role_markers
    )
    return matched_roles >= max(2, len(role_markers) - 1)


def _concept_roles_match(
    fixture: GoldenFixtureV1,
    output: GoldenSemanticOutputV1,
) -> bool:
    if len(output.concepts) != 3:
        return False
    role_markers = _CONCEPT_ROLE_MARKERS.get(fixture.scenario_id)
    if role_markers is None or len(role_markers) != 3:
        return False
    rendered_concepts = [_concept_text(concept) for concept in output.concepts]
    return any(
        all(
            _contains_any(rendered_concepts[concept_index], role_markers[role_index])
            for role_index, concept_index in enumerate(order)
        )
        for order in permutations(range(3))
    )


def _concept_text(concept: object) -> str:
    from viraldy.evaluation.golden.contracts import GoldenConceptV1

    item = GoldenConceptV1.model_validate(concept)
    return _normalized(
        " ".join(
            value
            for value in (
                item.name,
                item.strategic_axis,
                item.buyer_persona,
                item.creator_persona,
                item.spoken_hook,
                item.overlay_hook,
            )
            if value
        )
    )


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(_normalized(marker) in text for marker in markers)


def _normalized(value: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", value.casefold()).split())


def _compare_preflight(
    expected: object,
    observed: object,
    check: Callable[[str, bool, str], None],
) -> None:
    from viraldy.evaluation.golden.contracts import GoldenPreflightV1

    expected_result = GoldenPreflightV1.model_validate(expected)
    observed_result = GoldenPreflightV1.model_validate(observed)
    asset_id = expected_result.asset_id
    fields = (
        "action",
        "product_required_before_ms",
        "product_first_appearance_ms",
        "disclosure_status",
        "proof_status",
        "product_tag_status",
        "personalization_expected",
        "personalization_observed",
    )
    for field in fields:
        expected_value = getattr(expected_result, field)
        observed_value = getattr(observed_result, field)
        check(
            f"preflight_{field}:{asset_id}",
            observed_value == expected_value,
            f"expected {expected_value}; observed {observed_value}",
        )
    check(
        f"preflight_hard_blockers:{asset_id}",
        set(observed_result.hard_blocker_codes)
        == set(expected_result.hard_blocker_codes),
        "hard blocker codes must match the persisted evaluation",
    )
    check(
        f"preflight_priority_fixes:{asset_id}",
        set(observed_result.high_priority_fix_codes)
        == set(expected_result.high_priority_fix_codes),
        "high-priority fix codes must match the persisted evaluation",
    )
    check(
        f"preflight_prohibited_claims:{asset_id}",
        set(observed_result.prohibited_claims_observed)
        == set(expected_result.prohibited_claims_observed),
        "prohibited claims must be preserved exactly",
    )
