from __future__ import annotations

from dataclasses import dataclass

from viraldy.modules.creative_domain.schema_versions import (
    TIKTOK_RUBRIC_VERSION,
    TIKTOK_RULE_VERSION,
)


@dataclass(frozen=True, slots=True)
class TikTokStructureRubric:
    version: str
    rule_version: str
    weights: dict[str, float]
    thresholds: dict[str, int]

    def validate(self) -> None:
        total = round(sum(self.weights.values()), 6)
        if total != 1.0:
            raise ValueError(f"Rubric weights must sum to 1.0, got {total}.")
        for name, value in self.thresholds.items():
            if name.endswith("_ms"):
                if value < 0:
                    raise ValueError(f"Rubric timing threshold {name} must be non-negative.")
                continue
            if value < 0 or value > 100:
                raise ValueError(f"Rubric threshold {name} must be between 0 and 100.")


TIKTOK_STRUCTURE_RUBRIC = TikTokStructureRubric(
    version=TIKTOK_RUBRIC_VERSION,
    rule_version=TIKTOK_RULE_VERSION,
    weights={
        "hook_clarity": 0.20,
        "product_visibility": 0.15,
        "demo_clarity": 0.15,
        "proof_strength": 0.10,
        "creator_authenticity": 0.10,
        "offer_clarity": 0.10,
        "cta_readiness": 0.10,
        "tiktok_native_fit": 0.05,
        "claim_safety": 0.05,
    },
    thresholds={
        "reject": 50,
        "revise": 70,
        "small_test": 85,
        "early_product_ms": 3000,
        "acceptable_product_ms": 5000,
        "late_product_ms": 8000,
    },
)

TIKTOK_STRUCTURE_RUBRIC.validate()
