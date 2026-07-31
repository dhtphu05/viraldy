from __future__ import annotations

import pytest

from viraldy.evaluation.golden import load_golden_fixture
from viraldy.evaluation.golden.loader import GOLDEN_SCENARIO_IDS
from viraldy.evaluation.qualification.application_scenarios import (
    load_application_scenario,
)
from viraldy.modules.products.contracts import ProductContextV1


@pytest.mark.parametrize("scenario_id", GOLDEN_SCENARIO_IDS)
def test_application_scenario_has_typed_product_and_bounded_media(
    scenario_id: str,
) -> None:
    fixture = load_golden_fixture(scenario_id)
    scenario = load_application_scenario(scenario_id, run_id="unit-test")
    context = ProductContextV1.model_validate(scenario.product_payload["product_context"])

    assert scenario.scenario_id == fixture.scenario_id
    assert context.identity.name == fixture.product_name
    assert scenario.product_payload["description"] == fixture.objective
    assert scenario.draft_asset_id
    assert scenario.revision_asset_id
    for story in (scenario.draft_story, scenario.revision_story):
        assert story.duration_seconds > 0
        assert story.scenes
        assert story.narration.strip()
        assert story.scenes[0].start_seconds == 0
        assert story.scenes[-1].end_seconds == story.duration_seconds
        assert all(
            0 <= scene.start_seconds < scene.end_seconds <= story.duration_seconds
            for scene in story.scenes
        )


def test_pod_scenario_carries_exact_personalization_and_physical_sample() -> None:
    scenario = load_application_scenario(
        "pod_dog_mom_crewneck",
        run_id="unit-test",
    )
    context = ProductContextV1.model_validate(scenario.product_payload["product_context"])
    fields = {field.key: field.expected_value for field in context.personalization.fields}

    assert fields["pet_name"] == "Milo"
    assert fields["recipient"] == "Dog Mom"
    assert fields["design_variant"] == "Golden Retriever"
    assert context.personalization.physical_sample_required is True
    assert "Pet name: Miles" in " ".join(scene.text for scene in scenario.draft_story.scenes)
    assert "Miles" in scenario.draft_story.narration
    assert "Milo" in scenario.revision_story.narration


def test_steamer_and_bag_scenarios_preserve_hard_governance() -> None:
    steamer = load_application_scenario(
        "home_travel_steamer",
        run_id="unit-test",
    )
    bag = load_application_scenario(
        "dropshipping_bag_sealer",
        run_id="unit-test",
    )
    steamer_context = ProductContextV1.model_validate(steamer.product_payload["product_context"])
    bag_context = ProductContextV1.model_validate(bag.product_payload["product_context"])

    assert steamer_context.creative.required_product_reveal_before_ms == 2000
    assert steamer_context.governance.required_disclosures == ["Results vary by fabric type."]
    assert "Results vary by fabric type." not in steamer.draft_story.narration
    assert "Results vary by fabric type." in steamer.revision_story.narration
    assert bag_context.governance.claims[0].rule_type == "prohibited"
    assert "every bag completely airtight" in (bag_context.governance.claims[0].text.casefold())
    assert "every bag completely airtight" in bag.draft_story.narration.casefold()
    assert "every bag completely airtight" not in bag.revision_story.narration.casefold()
