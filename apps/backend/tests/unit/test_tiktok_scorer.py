from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, cast
from uuid import UUID, uuid4

from viraldy.modules.media_analysis.public import EvidenceItemModel
from viraldy.modules.preflight.service import calculate_preflight_result
from viraldy.modules.tiktok_scorer.rubric import TIKTOK_STRUCTURE_RUBRIC
from viraldy.modules.tiktok_scorer.scorer import score_tiktok_structure


@dataclass(slots=True)
class FakeEvidence:
    evidence_type: str
    value_json: dict[str, Any]
    id: UUID = field(default_factory=uuid4)
    start_ms: int | None = None


def test_tiktok_rubric_weights_are_valid() -> None:
    TIKTOK_STRUCTURE_RUBRIC.validate()
    assert sum(TIKTOK_STRUCTURE_RUBRIC.weights.values()) == 1.0


def test_strong_structure_scores_deterministically() -> None:
    result = score_tiktok_structure(_evidence(first_product_ms=1200, include_cta=True))

    assert result["structural_score"] == 78
    assert result["action"] == "organic_ready_or_small_test"
    assert result["blockers"] == []
    assert result["rubric_version"] == TIKTOK_STRUCTURE_RUBRIC.version


def test_missing_cta_creates_rule_backed_fix() -> None:
    result = score_tiktok_structure(_evidence(first_product_ms=1200, include_cta=False))

    assert result["dimensions"]["cta_readiness"]["score"] == 35
    assert any(fix["code"] == "MISSING_CTA" for fix in result["fixes"])


def test_late_product_reveal_creates_rule_backed_fix() -> None:
    result = score_tiktok_structure(_evidence(first_product_ms=6500, include_cta=True))

    assert result["dimensions"]["product_visibility"]["score"] == 45
    assert any(fix["code"] == "LATE_PRODUCT_REVEAL" for fix in result["fixes"])


def test_product_absent_hard_blocks_score_action() -> None:
    result = score_tiktok_structure(_evidence(first_product_ms=None, include_cta=True))

    assert result["action"] == "reject_or_reshoot"
    assert any(blocker["code"] == "PRODUCT_NOT_VISIBLE" for blocker in result["blockers"])
    assert result["dimensions"]["product_visibility"]["confidence"] == "low"


def test_high_risk_claim_hard_blocks_score_action() -> None:
    result = score_tiktok_structure(
        _evidence(first_product_ms=1200, include_cta=True, claim_risk="high")
    )

    assert result["action"] == "reject_or_reshoot"
    assert any(blocker["code"] == "HIGH_RISK_UNSUPPORTED_CLAIM" for blocker in result["blockers"])


def test_preflight_keeps_documented_formula_and_brief_blocker() -> None:
    structural = score_tiktok_structure(_evidence(first_product_ms=None, include_cta=True))
    result = calculate_preflight_result(structural, {"must_show": ["product close-up"]})
    expected = round((0.8 * int(structural["structural_score"])) + (0.2 * 60))

    assert result["preflight_score"] == expected
    assert result["rubric_version"] == "ugc_preflight_rubric_v1"
    assert any(blocker["code"] == "MISSING_MUST_SHOW_SCENE" for blocker in result["blockers"])


def _evidence(
    first_product_ms: int | None,
    include_cta: bool,
    claim_risk: str | None = None,
) -> list[EvidenceItemModel]:
    items: list[FakeEvidence] = [
        FakeEvidence("hook_signal", {"text": "problem-first opening"}, start_ms=0),
        FakeEvidence("demo_signal", {"text": "before after"}, start_ms=6500),
        FakeEvidence("proof_signal", {"text": "visual result"}, start_ms=15000),
        FakeEvidence("on_screen_text", {"text": "tiny kitchen reset"}, start_ms=0),
    ]
    if first_product_ms is not None:
        items.append(
            FakeEvidence(
                "product_first_appearance",
                {"value": first_product_ms},
                start_ms=first_product_ms,
            )
        )
    if include_cta:
        items.append(FakeEvidence("cta_signal", {"text": "TikTok Shop CTA"}, start_ms=18200))
    if claim_risk is not None:
        items.append(FakeEvidence("claim_signal", {"risk": claim_risk}, start_ms=9200))
    return cast(list[EvidenceItemModel], items)
