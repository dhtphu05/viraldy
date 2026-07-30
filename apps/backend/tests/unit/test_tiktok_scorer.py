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
    end_ms: int | None = None
    confidence: float | None = 0.85
    source: str = "vision"


def test_tiktok_rubric_weights_are_valid() -> None:
    TIKTOK_STRUCTURE_RUBRIC.validate()
    assert sum(TIKTOK_STRUCTURE_RUBRIC.weights.values()) == 1.0


def test_strong_structure_scores_deterministically() -> None:
    result = score_tiktok_structure(_evidence(first_product_ms=1200, include_cta=True))

    assert result["schema_version"] == "tiktok_score_v2"
    assert result["structural_score"] >= 80
    assert result["action"] in {"organic_ready_or_small_test", "approve_structure"}
    assert result["blockers"] == []
    assert result["rubric_version"] == TIKTOK_STRUCTURE_RUBRIC.version
    assert result["dimensions"]["hook_clarity"]["signals"]


def test_missing_cta_creates_rule_backed_fix() -> None:
    result = score_tiktok_structure(_evidence(first_product_ms=1200, include_cta=False))

    assert result["dimensions"]["cta_readiness"]["score"] == 0
    assert any(fix["code"] == "MISSING_CTA" for fix in result["fixes"])


def test_late_product_reveal_creates_rule_backed_fix() -> None:
    result = score_tiktok_structure(_evidence(first_product_ms=6500, include_cta=True))

    assert result["dimensions"]["product_visibility"]["score"] <= 70
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


def test_offer_after_cta_loses_timing_credit() -> None:
    evidence = _evidence(first_product_ms=1200, include_cta=True, include_offer=True)
    result = score_tiktok_structure(evidence)

    offer_timing = next(
        signal
        for signal in result["dimensions"]["offer_clarity"]["signals"]
        if signal["code"] == "offer_timing_before_cta"
    )
    assert offer_timing["contribution"] == 0


def test_cta_too_late_loses_timing_credit() -> None:
    result = score_tiktok_structure(
        _evidence(first_product_ms=1200, include_cta=True, cta_start_ms=9500),
        media_duration_ms=10000,
    )

    cta_timing = next(
        signal
        for signal in result["dimensions"]["cta_readiness"]["signals"]
        if signal["code"] == "cta_timing"
    )
    assert cta_timing["contribution"] == 0
    assert "cta_timing" in result["dimensions"]["cta_readiness"]["missing_signals"]


def test_no_risky_claim_with_incomplete_evidence_lowers_confidence() -> None:
    result = score_tiktok_structure(
        cast(
            list[EvidenceItemModel],
            [
                FakeEvidence(
                    "hook_signal",
                    {
                        "hook_type": "problem_first",
                        "spoken_text": "Quick demo",
                        "visual_description": "product context",
                        "confidence": 0.8,
                    },
                    start_ms=0,
                    end_ms=1000,
                )
            ],
        )
    )

    assert result["dimensions"]["claim_safety"]["confidence"] != "high"
    assert result["dimensions"]["claim_safety"]["missing_signals"]


def test_product_mismatch_requires_product_context() -> None:
    generic = score_tiktok_structure(
        _evidence(first_product_ms=1200, include_cta=True, product_match_confidence=0.2)
    )
    contextual = score_tiktok_structure(
        _evidence(first_product_ms=1200, include_cta=True, product_match_confidence=0.2),
        product_context_present=True,
    )

    assert not any(blocker["code"] == "PRODUCT_MISMATCH" for blocker in generic["blockers"])
    assert any(blocker["code"] == "PRODUCT_MISMATCH" for blocker in contextual["blockers"])


def test_preflight_scores_actual_requirement_satisfaction() -> None:
    structural = score_tiktok_structure(_evidence(first_product_ms=None, include_cta=True))
    result = calculate_preflight_result(structural, {"must_show": ["product close-up"]})
    expected = round((0.8 * int(structural["structural_score"])) + (0.2 * 0))

    assert result["preflight_score"] == expected
    assert result["brief_alignment_score"] == 0
    assert result["brief_alignment"]["schema_version"] == "ugc_preflight_v2"
    assert result["brief_alignment"]["requirements"][0]["status"] == "missing"
    assert result["rubric_version"] == "ugc_preflight_rubric_v2"
    assert any(blocker["code"] == "MISSING_MUST_SHOW_SCENE" for blocker in result["blockers"])


def _evidence(
    first_product_ms: int | None,
    include_cta: bool,
    claim_risk: str | None = None,
    product_match_confidence: float = 0.82,
    cta_start_ms: int = 3200,
    include_offer: bool = False,
) -> list[EvidenceItemModel]:
    items: list[FakeEvidence] = [
        FakeEvidence(
            "hook_signal",
            {
                "hook_type": "problem_first",
                "spoken_text": "My counter was always a mess.",
                "visual_description": "messy counter",
                "buyer_pain": "limited space",
                "clarity": "clear",
                "confidence": 0.9,
                "start_ms": 0,
                "end_ms": 1000,
            },
            start_ms=0,
            end_ms=1000,
        ),
        FakeEvidence(
            "demo_summary",
            {
                "detected": True,
                "demo_type": "before_after",
                "before_state_visible": True,
                "after_state_visible": True,
                "mechanism_clarity": "clear",
                "continuity": "edited_but_clear",
                "confidence": 0.88,
            },
            start_ms=1200,
        ),
        FakeEvidence(
            "demo_step",
            {
                "step_index": 1,
                "action": "show product creating visible result",
                "product_visible": True,
                "mechanism_visible": True,
                "result_visible": True,
                "confidence": 0.86,
                "start_ms": 1200,
                "end_ms": 3000,
            },
            start_ms=1200,
            end_ms=3000,
        ),
        FakeEvidence(
            "proof_signal",
            {
                "proof_type": "before_after",
                "description": "visible before after result",
                "verifiability": "observable",
                "confidence": 0.84,
                "start_ms": 2500,
                "end_ms": 3300,
            },
            start_ms=2500,
            end_ms=3300,
        ),
        FakeEvidence(
            "creator_signal",
            {
                "face_present": True,
                "speaking_present": True,
                "delivery_style": "authentic_review",
                "creator_persona": "home organizer",
                "emotion": "relieved",
                "pacing": "fast",
                "sales_language_intensity": "low",
                "authenticity_cues": ["first person", "visible demo"],
                "confidence": 0.82,
            },
        ),
        FakeEvidence(
            "editing_signal",
            {
                "cut_count": 4,
                "average_shot_duration_ms": 900,
                "first_three_second_cut_count": 3,
                "caption_density": "medium",
                "visual_pacing": "fast",
                "transition_types": ["jump_cut"],
                "confidence": 0.78,
            },
        ),
        FakeEvidence(
            "platform_signal",
            {
                "aspect_ratio": "9:16",
                "vertical": True,
                "native_signals": ["first_person", "jump_cuts"],
                "shop_signals": ["tiktok_shop_mention"],
                "caption_style": ["short_overlay"],
                "visual_safe_zone_risk": False,
                "confidence": 0.86,
            },
        ),
        FakeEvidence("on_screen_text", {"text": "tiny kitchen reset"}, start_ms=0, source="ocr"),
    ]
    if first_product_ms is not None:
        items.append(
            FakeEvidence(
                "product_visibility_summary",
                {
                    "first_appearance_ms": first_product_ms,
                    "total_visible_ms": 2500,
                    "screen_time_ratio": 0.62,
                    "clear_close_up_present": True,
                    "usage_present": True,
                },
                start_ms=None,
                source="derived",
            )
        )
        items.append(
            FakeEvidence(
                "product_appearance",
                {
                    "visibility": "clear",
                    "shot_type": "close_up",
                    "usage_visible": True,
                    "product_match_confidence": product_match_confidence,
                    "confidence": 0.88,
                    "start_ms": first_product_ms,
                    "end_ms": first_product_ms + 900,
                },
                start_ms=first_product_ms,
                end_ms=first_product_ms + 900,
            )
        )
    if include_cta:
        items.append(
            FakeEvidence(
                "cta_signal",
                {
                    "modality": "spoken",
                    "cta_type": "link_in_shop",
                    "text": "Linked in my TikTok Shop",
                    "product_tag_visible": True,
                    "confidence": 0.86,
                    "start_ms": cta_start_ms,
                    "end_ms": cta_start_ms + 700,
                },
                start_ms=cta_start_ms,
                end_ms=cta_start_ms + 700,
            )
        )
    if include_offer:
        items.append(
            FakeEvidence(
                "offer_signal",
                {
                    "offer_type": "discount",
                    "text": "Today only",
                    "price_text": None,
                    "urgency_present": True,
                    "confidence": 0.8,
                    "start_ms": cta_start_ms + 1000,
                    "end_ms": cta_start_ms + 1500,
                },
                start_ms=cta_start_ms + 1000,
                end_ms=cta_start_ms + 1500,
            )
        )
    if claim_risk is not None:
        items.append(
            FakeEvidence(
                "claim_signal",
                {
                    "text": "best ever",
                    "source": "spoken",
                    "category": "superlative",
                    "risk": claim_risk,
                    "qualification_present": False,
                    "confidence": 0.8,
                    "start_ms": 2200,
                    "end_ms": 2600,
                },
                start_ms=2200,
                end_ms=2600,
            )
        )
    return cast(list[EvidenceItemModel], items)
