from __future__ import annotations

import json
from importlib.resources import files

from viraldy.evaluation.golden.contracts import GoldenFixtureV1

GOLDEN_SCENARIO_IDS = (
    "home_travel_steamer",
    "pod_dog_mom_crewneck",
    "dropshipping_bag_sealer",
)
REQUIRED_GOLDEN_ASSET_IDS = frozenset(
    {
        "reference_good_structure",
        "ugc_missing_product_timing",
        "ugc_missing_proof",
        "ugc_missing_disclosure",
        "ugc_prohibited_claim",
        "ugc_revision_resolves_all",
        "no_audio_video",
    }
)


def load_golden_fixture(scenario_id: str) -> GoldenFixtureV1:
    if scenario_id not in GOLDEN_SCENARIO_IDS:
        raise ValueError(f"unknown golden scenario: {scenario_id}")
    resource = files("viraldy.evaluation.golden.fixtures").joinpath(
        f"{scenario_id}.json"
    )
    return GoldenFixtureV1.model_validate(json.loads(resource.read_text("utf-8")))


def load_all_golden_fixtures() -> list[GoldenFixtureV1]:
    fixtures = [load_golden_fixture(scenario_id) for scenario_id in GOLDEN_SCENARIO_IDS]
    asset_ids = {asset.asset_id for fixture in fixtures for asset in fixture.assets}
    missing = REQUIRED_GOLDEN_ASSET_IDS - asset_ids
    if missing:
        missing_list = ", ".join(sorted(missing))
        raise ValueError(f"golden fixture assets missing: {missing_list}")
    return fixtures
