from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from viraldy.modules.media_analysis.public import EvidenceItemModel
from viraldy.modules.tiktok_scorer.contracts import (
    BlockerV2,
    DimensionScoreV2,
    FixV2,
    ScoreSignalV2,
    StrengthV2,
    TikTokScoreResultV2,
)
from viraldy.modules.tiktok_scorer.repository import RUBRIC_VERSION, RULE_VERSION
from viraldy.modules.tiktok_scorer.rubric import TIKTOK_STRUCTURE_RUBRIC

DISCLAIMER = "This is a structural readiness score, not a guarantee of viral reach, sales, or GMV."


@dataclass(frozen=True, slots=True)
class EvidenceFacts:
    grouped: dict[str, list[EvidenceItemModel]]
    evidence_ids: list[UUID]
    media_duration_ms: int | None = None


def score_tiktok_structure(
    evidence: list[EvidenceItemModel],
    *,
    media_duration_ms: int | None = None,
    product_context_present: bool = False,
) -> dict[str, Any]:
    facts = EvidenceFacts(_group(evidence), [item.id for item in evidence], media_duration_ms)
    dimensions = {
        "hook_clarity": _hook_clarity(facts),
        "product_visibility": _product_visibility(facts),
        "demo_clarity": _demo_clarity(facts),
        "proof_strength": _proof_strength(facts),
        "creator_authenticity": _creator_authenticity(facts),
        "offer_clarity": _offer_clarity(facts),
        "cta_readiness": _cta_readiness(facts),
        "tiktok_native_fit": _tiktok_native_fit(facts),
        "claim_safety": _claim_safety(facts),
    }
    score = round(
        sum(
            dimensions[name].score * weight
            for name, weight in TIKTOK_STRUCTURE_RUBRIC.weights.items()
        )
    )
    blockers = _blockers(facts, dimensions, product_context_present)
    action = _action(score, blockers)
    fixes = _fixes(facts, dimensions, blockers)
    strengths = _strengths(dimensions)
    result = TikTokScoreResultV2(
        structural_score=score,
        confidence=_overall_confidence(dimensions),
        action=action,
        dimensions=dimensions,
        strengths=strengths,
        blockers=blockers,
        fixes=fixes[:5],
        evidence_ids=facts.evidence_ids,
        rubric_version=RUBRIC_VERSION,
        rule_version=RULE_VERSION,
        disclaimer=DISCLAIMER,
        summary=DISCLAIMER,
    )
    return result.model_dump(mode="json")


def _hook_clarity(facts: EvidenceFacts) -> DimensionScoreV2:
    items = _items(facts, "hook_signal")
    signals: list[ScoreSignalV2] = []
    missing: list[str] = []
    if not items:
        return _dimension(
            "hook_clarity",
            0,
            "No opening hook evidence was detected.",
            [],
            [
                "hook_detected",
                "opening_timing",
                "semantic_proposition",
            ],
        )
    item = items[0]
    value = item.value_json
    signals.append(_signal("hook_detected", True, 20, item, _confidence(item, value)))
    starts = item.start_ms if item.start_ms is not None else int(value.get("start_ms") or 0)
    signals.append(
        _signal("starts_within_1500ms", starts <= 1500, 20 if starts <= 1500 else 0, item)
    )
    clarity = str(value.get("clarity") or "unknown")
    clarity_score = {"clear": 20, "partial": 10, "unclear": 0, "unknown": 0}.get(clarity, 0)
    signals.append(_signal("hook_clarity", clarity, clarity_score, item))
    has_text = bool(value.get("spoken_text") or value.get("overlay_text") or value.get("text"))
    has_visual = bool(value.get("visual_description"))
    signals.append(
        _signal(
            "text_visual_consistency",
            has_text and has_visual,
            15 if has_text and has_visual else 0,
            item,
        )
    )
    pain_present = bool(value.get("buyer_pain") or value.get("spoken_text") or value.get("text"))
    signals.append(_signal("buyer_pain_or_result", pain_present, 15 if pain_present else 0, item))
    signals.append(
        _signal(
            "opening_confidence",
            round(_confidence(item, value), 2),
            10 * _confidence(item, value),
            item,
        )
    )
    return _dimension(
        "hook_clarity",
        _score(signals),
        "Opening hook score is derived from timing, clarity, text/visual support, and confidence.",
        signals,
        missing,
    )


def _product_visibility(facts: EvidenceFacts) -> DimensionScoreV2:
    summary = _first_item(facts, "product_visibility_summary")
    appearances = _items(facts, "product_appearance", "product_first_appearance")
    first_ms = _first_product_ms(facts)
    if first_ms is None:
        return _dimension(
            "product_visibility",
            0,
            "The product was not detected.",
            [],
            ["product_appearance", "first_appearance_timing", "screen_time"],
        )
    evidence_item = summary or appearances[0]
    visibility_value = summary.value_json if summary is not None else {}
    appearance_value = appearances[0].value_json if appearances else {}
    timing_score = _timing_score(first_ms)
    screen_ratio = _float_or_none(visibility_value.get("screen_time_ratio"))
    screen_score = 0 if screen_ratio is None else min(20, round(screen_ratio * 50))
    close_up = bool(
        visibility_value.get("clear_close_up_present")
        or appearance_value.get("shot_type") in {"hero", "close_up"}
    )
    usage_visible = bool(
        visibility_value.get("usage_present") or appearance_value.get("usage_visible")
    )
    match_confidence = _float_or_none(appearance_value.get("product_match_confidence"))
    signals = [
        _signal("first_appearance_timing", first_ms, timing_score, evidence_item),
        _signal("screen_time_ratio", screen_ratio, screen_score, evidence_item),
        _signal("clear_close_up_or_hero", close_up, 15 if close_up else 0, evidence_item),
        _signal("usage_visible", usage_visible, 15 if usage_visible else 0, evidence_item),
        _signal(
            "product_match_confidence",
            match_confidence,
            10 * (match_confidence if match_confidence is not None else 0),
            evidence_item,
        ),
    ]
    return _dimension(
        "product_visibility",
        _score(signals),
        f"Product visibility is derived from first appearance at {first_ms}ms and visibility cues.",
        signals,
        [
            code
            for code, present in {
                "screen_time_ratio": screen_ratio is not None,
                "clear_close_up_or_hero": close_up,
                "usage_visible": usage_visible,
                "product_match_confidence": match_confidence is not None,
            }.items()
            if not present
        ],
    )


def _demo_clarity(facts: EvidenceFacts) -> DimensionScoreV2:
    summary = _first_item(facts, "demo_summary", "demo_signal")
    steps = _items(facts, "demo_step")
    if summary is None and not steps:
        return _dimension(
            "demo_clarity",
            0,
            "No product demonstration evidence was detected.",
            [],
            ["demo_detected"],
        )
    item = summary or steps[0]
    value = item.value_json
    detected = bool(value.get("detected", True))
    step_count = len(steps)
    mechanism_visible = any(bool(step.value_json.get("mechanism_visible")) for step in steps)
    result_visible = bool(value.get("after_state_visible")) or any(
        bool(step.value_json.get("result_visible")) for step in steps
    )
    continuity = str(value.get("continuity") or "unknown")
    continuity_score = {"continuous": 10, "edited_but_clear": 8, "fragmented": 3}.get(continuity, 0)
    confidence = _confidence(item, value)
    signals = [
        _signal("demo_detected", detected, 15 if detected else 0, item),
        _signal("step_completeness", step_count, min(25, step_count * 12.5), item),
        _signal("mechanism_visible", mechanism_visible, 25 if mechanism_visible else 0, item),
        _signal("result_visible", result_visible, 20 if result_visible else 0, item),
        _signal("continuity", continuity, continuity_score, item),
        _signal("demo_confidence", round(confidence, 2), 5 * confidence, item),
    ]
    return _dimension(
        "demo_clarity",
        _score(signals),
        (
            "Demo clarity is derived from visible steps, mechanism, result, "
            "continuity, and confidence."
        ),
        signals,
        [
            code
            for code, present in {
                "demo_steps": bool(steps),
                "mechanism_visible": mechanism_visible,
                "result_visible": result_visible,
            }.items()
            if not present
        ],
    )


def _proof_strength(facts: EvidenceFacts) -> DimensionScoreV2:
    items = _items(facts, "proof_signal")
    if not items:
        return _dimension(
            "proof_strength", 0, "No proof evidence was detected.", [], ["proof_present"]
        )
    item = items[0]
    value = item.value_json
    proof_type = str(value.get("proof_type") or "unknown")
    verifiability = str(value.get("verifiability") or "unknown")
    type_score = {
        "measurement": 20,
        "before_after": 18,
        "visual_result": 16,
        "demonstration": 15,
        "testimonial": 12,
        "review": 12,
    }.get(proof_type, 6)
    observable_score = {"observable": 25, "partially_observable": 13}.get(verifiability, 0)
    specificity = bool(value.get("description") and value.get("description") != "unknown")
    confidence = _confidence(item, value)
    signals = [
        _signal("proof_present", True, 20, item),
        _signal("verifiability", verifiability, observable_score, item),
        _signal("proof_type_strength", proof_type, type_score, item),
        _signal("specificity", specificity, 15 if specificity else 0, item),
            _signal(
                "source_credibility",
                _source(item),
                10 if _source(item) in {"vision", "ocr", "asr"} else 5,
                item,
            ),
        _signal("proof_confidence", round(confidence, 2), 10 * confidence, item),
    ]
    return _dimension(
        "proof_strength",
        _score(signals),
        (
            "Proof strength is derived from verifiability, proof type, specificity, "
            "source, and confidence."
        ),
        signals,
        [],
    )


def _creator_authenticity(facts: EvidenceFacts) -> DimensionScoreV2:
    item = _first_item(facts, "creator_signal") or _first_item(facts, "hook_signal")
    if item is None:
        return _dimension(
            "creator_authenticity",
            0,
            "No creator or delivery evidence was detected.",
            [],
            ["creator_signal"],
        )
    value = item.value_json
    delivery = str(value.get("delivery_style") or "unknown")
    native_delivery = delivery in {
        "authentic_review",
        "testimonial",
        "tutorial",
        "demonstration",
        "storytelling",
        "voiceover",
        "faceless_demo",
    }
    cues = value.get("authenticity_cues")
    cue_count = len(cues) if isinstance(cues, list) else 0
    sales = str(value.get("sales_language_intensity") or "unknown")
    sales_score = {"low": 15, "medium": 8, "high": 0, "unknown": 4}.get(sales, 4)
    pacing = str(value.get("pacing") or "unknown")
    pacing_score = {"moderate": 10, "fast": 8, "mixed": 6, "slow": 4}.get(pacing, 4)
    confidence = _confidence(item, value)
    presence = bool(value.get("speaking_present") or value.get("face_present") is not None)
    signals = [
        _signal("creator_or_voice_presence", presence, 15 if presence else 0, item),
        _signal("native_delivery_style", delivery, 20 if native_delivery else 0, item),
        _signal("authenticity_cues", cue_count, min(20, cue_count * 10), item),
        _signal("sales_language_restraint", sales, sales_score, item),
        _signal(
            "emotion_context_fit",
            value.get("emotion"),
            10 if value.get("emotion") not in {None, "unknown"} else 4,
            item,
        ),
        _signal("pacing", pacing, pacing_score, item),
        _signal("creator_confidence", round(confidence, 2), 10 * confidence, item),
    ]
    return _dimension(
        "creator_authenticity",
        _score(signals),
        "Creator authenticity is derived from delivery style, restraint, pacing, and confidence.",
        signals,
        [],
    )


def _offer_clarity(facts: EvidenceFacts) -> DimensionScoreV2:
    items = _items(facts, "offer_signal")
    if not items:
        return _dimension(
            "offer_clarity",
            35,
            (
                "No explicit offer was detected; this may be acceptable for organic "
                "reference analysis."
            ),
            [],
            ["offer_or_value_present"],
        )
    item = items[0]
    value = item.value_json
    specific = bool(value.get("price_text") or value.get("text"))
    confidence = _confidence(item, value)
    first_offer_ms = _first_start_ms(items)
    first_cta_ms = _first_start_ms(_items(facts, "cta_signal"))
    timing_ok = (
        first_offer_ms is not None
        and first_cta_ms is not None
        and first_offer_ms <= first_cta_ms
    )
    timing_known = first_offer_ms is not None and first_cta_ms is not None
    signals = [
        _signal("offer_present", True, 30, item),
        _signal("offer_specificity", specific, 25 if specific else 0, item),
        _signal(
            "speech_overlay_consistency", value.get("text"), 10 if value.get("text") else 0, item
        ),
        _signal(
            "offer_timing_before_cta",
            first_offer_ms,
            15 if timing_ok else 0,
            item,
        ),
        _signal("commercial_context_match", "unknown", 5, item),
        _signal("offer_confidence", round(confidence, 2), 15 * confidence, item),
    ]
    return _dimension(
        "offer_clarity",
        _score(signals),
        "Offer clarity is derived from observed offer specificity and timing.",
        signals,
        [] if timing_known else ["cta_or_offer_timing"],
    )


def _cta_readiness(facts: EvidenceFacts) -> DimensionScoreV2:
    items = _items(facts, "cta_signal")
    if not items:
        return _dimension("cta_readiness", 0, "No CTA evidence was detected.", [], ["cta_present"])
    item = items[0]
    value = item.value_json
    cta_type = str(value.get("cta_type") or "unknown")
    text_present = bool(value.get("text"))
    product_tag = bool(value.get("product_tag_visible"))
    duration_ms = facts.media_duration_ms or _duration_from_evidence(facts)
    first_cta_ms = item.start_ms
    timing_ok = first_cta_ms is not None and (
        duration_ms is None or first_cta_ms <= round(duration_ms * 0.9)
    )
    signals = [
        _signal("cta_present", True, 30, item),
        _signal("cta_clarity", cta_type, 25 if cta_type != "unknown" or text_present else 0, item),
        _signal("product_tag_or_shop_cue", product_tag, 20 if product_tag else 0, item),
        _signal("cta_timing", first_cta_ms, 15 if timing_ok else 0, item),
        _signal(
            "spoken_overlay_consistency",
            value.get("modality"),
            10 if value.get("modality") in {"mixed", "spoken", "overlay"} else 0,
            item,
        ),
    ]
    return _dimension(
        "cta_readiness",
        _score(signals),
        "CTA readiness is derived from observed CTA type, timing, and product-tag cues.",
        signals,
        [] if timing_ok else ["cta_timing"],
    )


def _tiktok_native_fit(facts: EvidenceFacts) -> DimensionScoreV2:
    platform = _first_item(facts, "platform_signal")
    editing = _first_item(facts, "editing_signal")
    text_items = _items(facts, "on_screen_text")
    item = platform or editing or (text_items[0] if text_items else None)
    if item is None:
        return _dimension(
            "tiktok_native_fit",
            0,
            "No platform-native evidence was detected.",
            [],
            ["platform_signal"],
        )
    platform_value = platform.value_json if platform is not None else {}
    editing_value = editing.value_json if editing is not None else {}
    vertical = bool(platform_value.get("vertical"))
    native_signals = platform_value.get("native_signals")
    native_count = len(native_signals) if isinstance(native_signals, list) else 0
    caption_present = bool(text_items) or bool(platform_value.get("caption_style"))
    pacing = str(editing_value.get("visual_pacing") or "unknown")
    shop_signals = platform_value.get("shop_signals")
    shop_count = len(shop_signals) if isinstance(shop_signals, list) else 0
    signals = [
        _signal("vertical_format", vertical, 15 if vertical else 0, item),
        _signal("opening_pacing", pacing, 20 if pacing in {"fast", "mixed"} else 8, item),
        _signal("caption_or_overlay_use", caption_present, 15 if caption_present else 0, item),
        _signal("native_delivery_signals", native_count, min(20, native_count * 10), item),
        _signal(
            "pattern_interrupts_or_editing",
            editing is not None,
            15 if editing is not None else 0,
            item,
        ),
        _signal("shop_native_cues", shop_count, min(15, shop_count * 15), item),
    ]
    return _dimension(
        "tiktok_native_fit",
        _score(signals),
        "TikTok-native fit is derived from format, captions, delivery, editing, and shop cues.",
        signals,
        [],
    )


def _claim_safety(facts: EvidenceFacts) -> DimensionScoreV2:
    items = _items(facts, "claim_signal")
    if not items:
        coverage_items = _claim_coverage_items(facts)
        signals = [
            _signal(
                "transcript_coverage",
                bool(_items(facts, "transcript_segment")),
                35 if _items(facts, "transcript_segment") else 0,
                item,
            )
            for item in coverage_items[:1]
        ]
        if len(coverage_items) >= 2:
            signals.append(
                _signal(
                    "ocr_coverage",
                    bool(_items(facts, "on_screen_text")),
                    30 if _items(facts, "on_screen_text") else 0,
                    coverage_items[1],
                )
            )
        if len(coverage_items) >= 3:
            vision_present = bool(_items(facts, "platform_signal", "hook_signal", "proof_signal"))
            signals.append(
                _signal(
                    "vision_claim_coverage",
                    vision_present,
                    35 if vision_present else 0,
                    coverage_items[2],
                )
            )
        missing = [
            code
            for code, present in {
                "transcript_coverage": bool(_items(facts, "transcript_segment")),
                "ocr_coverage": bool(_items(facts, "on_screen_text")),
                "vision_claim_coverage": bool(
                    _items(facts, "platform_signal", "hook_signal", "proof_signal")
                ),
            }.items()
            if not present
        ]
        score = 100 if not missing else 85
        return _dimension(
            "claim_safety",
            score,
            "No risky claims were detected; confidence is based on text and visual coverage.",
            signals,
            missing,
        )
    worst = _max_claim_risk(facts)
    penalty = {"critical": 100, "high": 80, "medium": 40, "low": 15}.get(worst or "none", 0)
    score = max(0, 100 - penalty)
    signals = [
        _signal(
            "worst_claim_risk",
            worst,
            -penalty,
            items[0],
            _confidence(items[0], items[0].value_json),
        )
    ]
    return _dimension(
        "claim_safety",
        score,
        f"Claim safety starts from 100 and applies deterministic penalties for {worst} risk.",
        signals,
        [],
    )


def _dimension(
    dimension: str,
    score: int,
    reason: str,
    signals: list[ScoreSignalV2],
    missing_signals: list[str],
) -> DimensionScoreV2:
    evidence_ids = sorted(
        {evidence_id for signal in signals for evidence_id in signal.evidence_ids}
    )
    confidence = _dimension_confidence(signals, missing_signals)
    return DimensionScoreV2(
        dimension=dimension,
        score=max(0, min(100, round(score))),
        confidence=confidence,
        reason=reason,
        signals=signals,
        evidence_ids=evidence_ids,
        missing_signals=missing_signals,
    )


def _signal(
    code: str,
    value: str | int | float | bool | None,
    contribution: float,
    item: EvidenceItemModel,
    confidence: float | None = None,
) -> ScoreSignalV2:
    return ScoreSignalV2(
        code=code,
        value=value,
        contribution=round(float(contribution), 2),
        confidence=_confidence(item, item.value_json) if confidence is None else confidence,
        evidence_ids=[item.id],
    )


def _score(signals: list[ScoreSignalV2]) -> int:
    return max(0, min(100, round(sum(signal.contribution for signal in signals))))


def _timing_score(first_ms: int) -> int:
    if first_ms <= 1500:
        return 40
    if first_ms <= TIKTOK_STRUCTURE_RUBRIC.thresholds["early_product_ms"]:
        return 32
    if first_ms <= TIKTOK_STRUCTURE_RUBRIC.thresholds["acceptable_product_ms"]:
        return 22
    if first_ms <= TIKTOK_STRUCTURE_RUBRIC.thresholds["late_product_ms"]:
        return 12
    return 0


def _blockers(
    facts: EvidenceFacts,
    dimensions: dict[str, DimensionScoreV2],
    product_context_present: bool,
) -> list[BlockerV2]:
    blockers: list[BlockerV2] = []
    if _first_product_ms(facts) is None:
        blockers.append(
            BlockerV2(
                code="PRODUCT_NOT_VISIBLE",
                severity="hard",
                message="Product was not visible.",
                evidence_ids=[],
                remediation_code="ADD_PRODUCT_CLOSE_UP",
            )
        )
    product_match = _product_match_confidence(facts)
    if product_context_present and product_match is not None and product_match < 0.4:
        blockers.append(
            BlockerV2(
                code="PRODUCT_MISMATCH",
                severity="hard",
                message="Detected product has low match confidence against the product context.",
                evidence_ids=dimensions["product_visibility"].evidence_ids,
                remediation_code="RESHOOT_WITH_BRIEFED_PRODUCT",
            )
        )
    claim_risk = _max_claim_risk(facts)
    if claim_risk in {"critical", "high"}:
        blockers.append(
            BlockerV2(
                code="CRITICAL_PROHIBITED_CLAIM"
                if claim_risk == "critical"
                else "HIGH_RISK_UNSUPPORTED_CLAIM",
                severity="hard",
                message=f"{claim_risk.title()}-risk unsupported claim detected.",
                evidence_ids=dimensions["claim_safety"].evidence_ids,
                remediation_code="REWRITE_CLAIM",
            )
        )
    if not _items(facts, "hook_signal") and not _items(facts, "product_appearance"):
        blockers.append(
            BlockerV2(
                code="VISUAL_EVIDENCE_INSUFFICIENT",
                severity="high",
                message="Visual evidence is insufficient for structural approval.",
                evidence_ids=[],
                remediation_code="REUPLOAD_OR_RESAMPLE",
            )
        )
    return blockers


def _action(score: int, blockers: list[BlockerV2]) -> str:
    if any(blocker.severity == "hard" for blocker in blockers):
        return "reject_or_reshoot"
    if score < TIKTOK_STRUCTURE_RUBRIC.thresholds["reject"]:
        return "reject_or_reshoot"
    if score < TIKTOK_STRUCTURE_RUBRIC.thresholds["revise"]:
        return "revise"
    if score < TIKTOK_STRUCTURE_RUBRIC.thresholds["small_test"]:
        return "organic_ready_or_small_test"
    return "approve_structure"


def _fixes(
    facts: EvidenceFacts,
    dimensions: dict[str, DimensionScoreV2],
    blockers: list[BlockerV2],
) -> list[FixV2]:
    fixes: list[FixV2] = []
    for blocker in blockers:
        fixes.append(
            FixV2(
                code=blocker.code,
                priority=len(fixes) + 1,
                instruction=blocker.message,
                why="Hard blocker overrides the threshold score.",
                expected_impact_dimensions=["product_visibility", "claim_safety"],
                evidence_ids=blocker.evidence_ids,
            )
        )
    first_product_ms = _first_product_ms(facts)
    if first_product_ms is not None and first_product_ms > 3000:
        fixes.append(
            FixV2(
                code="LATE_PRODUCT_REVEAL",
                priority=len(fixes) + 1,
                instruction="Add a clear product close-up within the first three seconds.",
                why=f"The product first appears at {first_product_ms / 1000:.1f} seconds.",
                expected_impact_dimensions=["product_visibility", "hook_clarity"],
                evidence_ids=dimensions["product_visibility"].evidence_ids,
            )
        )
    if dimensions["offer_clarity"].score < 60:
        fixes.append(
            FixV2(
                code="MISSING_OFFER",
                priority=len(fixes) + 1,
                instruction="Add one concrete offer or value cue when the campaign requires it.",
                why="The creative does not make an offer or value cue clear.",
                expected_impact_dimensions=["offer_clarity"],
                evidence_ids=dimensions["offer_clarity"].evidence_ids,
            )
        )
    if dimensions["cta_readiness"].score < 60:
        fixes.append(
            FixV2(
                code="MISSING_CTA",
                priority=len(fixes) + 1,
                instruction="Add a clear TikTok Shop CTA before the final moment.",
                why="The creative does not show a CTA signal.",
                expected_impact_dimensions=["cta_readiness"],
                evidence_ids=dimensions["cta_readiness"].evidence_ids,
            )
        )
    if _max_claim_risk(facts) == "medium":
        fixes.append(
            FixV2(
                code="MEDIUM_RISK_CLAIM",
                priority=len(fixes) + 1,
                instruction="Replace unsupported superlatives with observable product results.",
                why="The draft includes a medium-risk claim candidate.",
                expected_impact_dimensions=["claim_safety"],
                evidence_ids=dimensions["claim_safety"].evidence_ids,
            )
        )
    return fixes


def _strengths(dimensions: dict[str, DimensionScoreV2]) -> list[StrengthV2]:
    strengths: list[StrengthV2] = []
    for name, dimension in dimensions.items():
        if dimension.score < 80:
            continue
        strengths.append(
            StrengthV2(
                code=f"STRONG_{name.upper()}",
                message=f"{name.replace('_', ' ').title()} is strongly supported by evidence.",
                dimensions=[name],
                evidence_ids=dimension.evidence_ids,
            )
        )
    return strengths[:4]


def _overall_confidence(dimensions: dict[str, DimensionScoreV2]) -> str:
    lows = sum(1 for dimension in dimensions.values() if dimension.confidence == "low")
    if lows >= 3:
        return "low"
    if lows:
        return "medium"
    return "high"


def _dimension_confidence(
    signals: list[ScoreSignalV2],
    missing_signals: list[str],
) -> str:
    if not signals or len(missing_signals) >= 2:
        return "low"
    average = sum(signal.confidence for signal in signals) / len(signals)
    if average >= 0.75 and not missing_signals:
        return "high"
    if average >= 0.45:
        return "medium"
    return "low"


def _group(evidence: list[EvidenceItemModel]) -> dict[str, list[EvidenceItemModel]]:
    grouped: dict[str, list[EvidenceItemModel]] = {}
    for item in evidence:
        grouped.setdefault(item.evidence_type, []).append(item)
    return grouped


def _items(facts: EvidenceFacts, *evidence_types: str) -> list[EvidenceItemModel]:
    items: list[EvidenceItemModel] = []
    for evidence_type in evidence_types:
        items.extend(facts.grouped.get(evidence_type, []))
    return sorted(items, key=lambda item: (item.start_ms is None, item.start_ms or 0))


def _first_item(facts: EvidenceFacts, *evidence_types: str) -> EvidenceItemModel | None:
    items = _items(facts, *evidence_types)
    return items[0] if items else None


def _first_start_ms(items: list[EvidenceItemModel]) -> int | None:
    starts = [item.start_ms for item in items if item.start_ms is not None]
    return min(starts) if starts else None


def _duration_from_evidence(facts: EvidenceFacts) -> int | None:
    item_ends = [
        item.end_ms
        for item in _items(
            facts,
            "transcript_segment",
            "on_screen_text",
            "hook_signal",
            "product_appearance",
            "demo_step",
            "proof_signal",
            "cta_signal",
            "offer_signal",
        )
        if item.end_ms is not None
    ]
    return max(item_ends) if item_ends else None


def _claim_coverage_items(facts: EvidenceFacts) -> list[EvidenceItemModel]:
    selected: list[EvidenceItemModel] = []
    for evidence_type in (
        "transcript_segment",
        "on_screen_text",
        "platform_signal",
        "hook_signal",
        "proof_signal",
    ):
        item = _first_item(facts, evidence_type)
        if item is not None:
            selected.append(item)
    return selected


def _first_product_ms(facts: EvidenceFacts) -> int | None:
    summary = _first_item(facts, "product_visibility_summary")
    if summary is not None:
        value = summary.value_json.get("first_appearance_ms")
        if isinstance(value, int | float):
            return int(value)
    appearances = _items(facts, "product_appearance")
    if appearances:
        return appearances[0].start_ms
    legacy = _first_item(facts, "product_first_appearance")
    if legacy is None:
        return None
    value = legacy.value_json.get("value")
    return int(value) if isinstance(value, int | float) else legacy.start_ms


def _max_claim_risk(facts: EvidenceFacts) -> str | None:
    rank = {"none": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
    worst: str | None = None
    for item in _items(facts, "claim_signal"):
        risk = str(item.value_json.get("risk") or "none")
        if rank.get(risk, 0) > rank.get(worst or "none", 0):
            worst = risk
    return worst


def _product_match_confidence(facts: EvidenceFacts) -> float | None:
    appearance = _first_item(facts, "product_appearance")
    if appearance is None:
        return None
    return _float_or_none(appearance.value_json.get("product_match_confidence"))


def _confidence(item: EvidenceItemModel, value: dict[str, Any]) -> float:
    raw = value.get("confidence")
    if isinstance(raw, int | float):
        return max(0, min(1, float(raw)))
    item_confidence = getattr(item, "confidence", None)
    if item_confidence is None:
        return 0.5
    return max(0, min(1, float(item_confidence)))


def _source(item: EvidenceItemModel) -> str:
    return str(getattr(item, "source", "unknown"))


def _float_or_none(value: object) -> float | None:
    return float(value) if isinstance(value, int | float) else None
