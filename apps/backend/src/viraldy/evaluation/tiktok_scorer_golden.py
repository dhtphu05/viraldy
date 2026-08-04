from __future__ import annotations

from importlib.resources import files
from typing import get_args

from viraldy.evaluation.tiktok_scorer_contracts import (
    ScorerGoldenCategoryV1,
    TikTokScorerGoldenDatasetV1,
)

REQUIRED_SCORER_GOLDEN_CATEGORIES = set(get_args(ScorerGoldenCategoryV1))
_FIXTURE_NAME = "tiktok_scorer_cases_v1.json"


def load_tiktok_scorer_golden_cases() -> TikTokScorerGoldenDatasetV1:
    resource = files("viraldy.evaluation.golden.fixtures").joinpath(_FIXTURE_NAME)
    catalog = TikTokScorerGoldenDatasetV1.model_validate_json(
        resource.read_text(encoding="utf-8")
    )
    covered = {category for case in catalog.cases for category in case.categories}
    missing = REQUIRED_SCORER_GOLDEN_CATEGORIES - covered
    unexpected = covered - REQUIRED_SCORER_GOLDEN_CATEGORIES
    if missing or unexpected:
        raise ValueError(
            "TikTok scorer golden category mismatch: "
            f"missing={sorted(missing)}, unexpected={sorted(unexpected)}"
        )
    return catalog


__all__ = ["REQUIRED_SCORER_GOLDEN_CATEGORIES", "load_tiktok_scorer_golden_cases"]
