from __future__ import annotations

import pytest
from pydantic import ValidationError

from viraldy.evaluation.golden import (
    GoldenSemanticOutputV1,
    load_all_golden_fixtures,
    load_golden_fixture,
    validate_golden_semantics,
)
from viraldy.evaluation.golden.loader import REQUIRED_GOLDEN_ASSET_IDS


def _semantic_output(scenario_id: str) -> GoldenSemanticOutputV1:
    fixture = load_golden_fixture(scenario_id)
    return GoldenSemanticOutputV1(
        scenario_id=fixture.scenario_id,
        product_name=fixture.product_name,
        objective=fixture.objective,
        pattern_name=fixture.pattern_name,
        concepts=fixture.concepts,
        preflight_results=fixture.preflight_expectations,
        performance_evidence_attached=False,
        performance_label=None,
    )


def test_all_authoritative_golden_fixtures_are_loadable_and_complete() -> None:
    fixtures = load_all_golden_fixtures()
    asset_ids = {asset.asset_id for fixture in fixtures for asset in fixture.assets}

    assert [fixture.scenario_id for fixture in fixtures] == [
        "home_travel_steamer",
        "pod_dog_mom_crewneck",
        "dropshipping_bag_sealer",
    ]
    assert REQUIRED_GOLDEN_ASSET_IDS.issubset(asset_ids)
    assert all(len(fixture.concepts) == 3 for fixture in fixtures)
    no_audio = next(
        asset
        for fixture in fixtures
        for asset in fixture.assets
        if asset.asset_id == "no_audio_video"
    )
    assert no_audio.has_audio is False
    assert no_audio.observations["transcript_segments"] == 0


def test_steamer_fixture_preserves_authoritative_semantics() -> None:
    fixture = load_golden_fixture("home_travel_steamer")

    assert fixture.product_name == "SwiftPress Mini Garment Steamer"
    assert (
        fixture.pattern_name
        == "Deadline Pressure \u2192 Fast Product Reveal \u2192 Same-Fabric Proof"
    )
    assert [concept.name for concept in fixture.concepts] == [
        "Late for Class Rescue",
        "Carry-On Clothing Rescue",
        "Small-Space Iron Alternative",
    ]
    draft = next(
        result
        for result in fixture.preflight_expectations
        if result.asset_id == "ugc_missing_product_timing"
    )
    assert draft.product_first_appearance_ms == 4200
    assert draft.product_required_before_ms == 2000
    assert draft.disclosure_status == "missing"
    assert draft.proof_status == "missing"
    assert draft.product_tag_status == "satisfied"
    assert draft.action == "revise"
    revision = next(
        result
        for result in fixture.preflight_expectations
        if result.asset_id == "ugc_revision_resolves_all"
    )
    assert revision.action == "small_paid_test"
    assert revision.hard_blocker_codes == []


@pytest.mark.parametrize(
    "scenario_id",
    [
        "home_travel_steamer",
        "pod_dog_mom_crewneck",
        "dropshipping_bag_sealer",
    ],
)
def test_canonical_semantic_projections_pass(scenario_id: str) -> None:
    fixture = load_golden_fixture(scenario_id)

    report = validate_golden_semantics(fixture, _semantic_output(scenario_id))

    assert report.passed
    assert report.checks
    assert all(check.passed for check in report.checks)


def test_semantic_validator_rejects_product_and_preflight_drift() -> None:
    fixture = load_golden_fixture("home_travel_steamer")
    output_payload = _semantic_output(fixture.scenario_id).model_dump(mode="json")
    output_payload["product_name"] = "Generic Steamer"
    draft = output_payload["preflight_results"][0]
    assert isinstance(draft, dict)
    draft["product_first_appearance_ms"] = 1900
    output = GoldenSemanticOutputV1.model_validate(output_payload)

    report = validate_golden_semantics(fixture, output)

    assert report.passed is False
    failed = {check.check for check in report.checks if not check.passed}
    assert "product_grounding" in failed
    assert (
        "preflight_product_first_appearance_ms:ugc_missing_product_timing"
        in failed
    )


def test_semantic_validator_accepts_equivalent_paraphrased_concepts() -> None:
    fixture = load_golden_fixture("pod_dog_mom_crewneck")
    payload = _semantic_output(fixture.scenario_id).model_dump(mode="json")
    payload["pattern_name"] = (
        "Dog-mom identity hook, readable custom name reveal, gift reaction, "
        "then clear ordering inputs"
    )
    replacements = [
        {
            "concept_id": "self_identity",
            "name": "A crewneck for a proud dog mom",
            "strategic_axis": "self purchase identity",
            "buyer_persona": "Dog owner buying for herself",
            "creator_persona": "Pet lifestyle storyteller",
            "spoken_hook": "My dog-mom uniform finally has the right name.",
            "overlay_hook": "Made for Milo's mom",
            "diversity_axes": ["buyer_persona", "hook_mechanism"],
        },
        {
            "concept_id": "recipient_reaction",
            "name": "The personalized gift reaction",
            "strategic_axis": "emotional recipient payoff",
            "buyer_persona": "Friend choosing a personal gift",
            "creator_persona": "Gifting video creator",
            "spoken_hook": "Her reaction started when she read Milo.",
            "overlay_hook": "A personal gift",
            "diversity_axes": ["buyer_persona", "narrative_structure"],
        },
        {
            "concept_id": "ordering_walkthrough",
            "name": "Submit the personalization correctly",
            "strategic_axis": "ordering tutorial",
            "buyer_persona": "Shopper checking custom inputs",
            "creator_persona": "Practical tutorial creator",
            "spoken_hook": "Enter the pet name, preview it, then check spelling.",
            "overlay_hook": "Input, preview, verify",
            "diversity_axes": ["demo_mechanism", "proof_mechanism"],
        },
    ]
    payload["concepts"] = replacements
    output = GoldenSemanticOutputV1.model_validate(payload)

    report = validate_golden_semantics(fixture, output)

    assert report.passed


def test_semantic_validator_rejects_generic_result_problem_proof_set() -> None:
    fixture = load_golden_fixture("pod_dog_mom_crewneck")
    payload = _semantic_output(fixture.scenario_id).model_dump(mode="json")
    payload["pattern_name"] = "Hook, demo, proof, CTA"
    for index, concept in enumerate(payload["concepts"], start=1):
        assert isinstance(concept, dict)
        concept.update(
            {
                "concept_id": f"generic_{index}",
                "name": f"Generic concept {index}",
                "strategic_axis": ("result", "problem", "proof")[index - 1],
                "buyer_persona": "Generic shopper",
                "creator_persona": f"Generic creator {index}",
                "spoken_hook": f"Watch this product demo {index}.",
                "overlay_hook": None,
                "diversity_axes": ["hook_mechanism", "narrative_structure"],
            }
        )
    output = GoldenSemanticOutputV1.model_validate(payload)

    report = validate_golden_semantics(fixture, output)

    failed = {check.check for check in report.checks if not check.passed}
    assert "pattern_semantics" in failed
    assert "concept_role_coverage" in failed


def test_pod_and_dropshipping_hard_blockers_are_not_genericized() -> None:
    pod = load_golden_fixture("pod_dog_mom_crewneck")
    pod_result = pod.preflight_expectations[0]
    assert pod_result.personalization_expected == "Milo"
    assert pod_result.personalization_observed == "Miles"
    assert pod_result.hard_blocker_codes == ["PERSONALIZATION_MISMATCH"]

    dropshipping = load_golden_fixture("dropshipping_bag_sealer")
    claim_result = dropshipping.preflight_expectations[0]
    assert claim_result.prohibited_claims_observed == [
        "This makes every bag completely airtight."
    ]
    assert claim_result.hard_blocker_codes == [
        "PROHIBITED_UNIVERSAL_AIRTIGHT_CLAIM"
    ]


def test_performance_label_requires_attached_evidence() -> None:
    output = _semantic_output("home_travel_steamer").model_dump(mode="json")
    output["performance_label"] = "winner"

    with pytest.raises(ValidationError):
        GoldenSemanticOutputV1.model_validate(output)
