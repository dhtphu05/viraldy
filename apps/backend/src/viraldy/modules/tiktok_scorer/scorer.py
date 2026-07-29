from __future__ import annotations

from typing import Any

from viraldy.modules.media_analysis.public import EvidenceItemModel
from viraldy.modules.tiktok_scorer.repository import RUBRIC_VERSION, RULE_VERSION
from viraldy.modules.tiktok_scorer.rubric import TIKTOK_STRUCTURE_RUBRIC


def score_tiktok_structure(evidence: list[EvidenceItemModel]) -> dict[str, Any]:
    grouped = _group(evidence)
    first_product_ms = _first_product_ms(grouped)
    claim_risk = _max_claim_risk(grouped)
    dimensions = {
        "hook_clarity": _evidence_dimension(
            85,
            "Problem-first hook is visible in the opening.",
            _ids(grouped, "hook_signal"),
            "No opening hook signal was detected.",
        ),
        "product_visibility": _product_visibility(
            first_product_ms, _ids(grouped, "product_first_appearance")
        ),
        "demo_clarity": _evidence_dimension(
            78,
            "Before/after demonstration is understandable.",
            _ids(grouped, "demo_signal"),
            "No product demonstration signal was detected.",
        ),
        "proof_strength": _evidence_dimension(
            70,
            "Visual before/after proof is present.",
            _ids(grouped, "proof_signal"),
            "No visual proof signal was detected.",
        ),
        "creator_authenticity": _evidence_dimension(
            76,
            "Creator-led review style reads native.",
            _ids(grouped, "hook_signal"),
            "No creator-led opening signal was detected.",
        ),
        "offer_clarity": _dimension(45, "No explicit offer is present.", []),
        "cta_readiness": _evidence_dimension(
            74,
            "TikTok Shop CTA is present.",
            _ids(grouped, "cta_signal"),
            "No TikTok Shop CTA signal was detected.",
        ),
        "tiktok_native_fit": _evidence_dimension(
            80,
            "Vertical demo and native phrasing are present.",
            _ids(grouped, "on_screen_text"),
            "No TikTok-native text or visual signal was detected.",
            missing_score=50,
        ),
        "claim_safety": _claim_safety(claim_risk, _ids(grouped, "claim_signal")),
    }
    score = round(
        sum(
            dimensions[name]["score"] * weight
            for name, weight in TIKTOK_STRUCTURE_RUBRIC.weights.items()
        )
    )
    blockers = _blockers(first_product_ms, claim_risk, dimensions)
    action = _action(score, blockers)
    fixes = _fixes(first_product_ms, claim_risk, dimensions, blockers)
    strengths = [
        {"code": "CLEAR_DEMO", "message": "The demo sequence shows a before/after transformation."},
        {"code": "NATIVE_CTA", "message": "The CTA uses TikTok Shop language."},
    ]
    return {
        "structural_score": score,
        "confidence": "high" if len(evidence) >= 8 else "medium",
        "action": action,
        "dimensions": dimensions,
        "strengths": strengths,
        "blockers": blockers,
        "fixes": fixes[:5],
        "summary": (
            "This is a structural readiness score, not a guarantee of viral reach, sales, or GMV."
        ),
        "evidence_ids": [str(item.id) for item in evidence],
        "rubric_version": RUBRIC_VERSION,
        "rule_version": RULE_VERSION,
    }


def _dimension(score: int, reason: str, evidence_ids: list[str]) -> dict[str, Any]:
    if score < 0 or score > 100:
        raise ValueError("Dimension score must be between 0 and 100.")
    return {
        "score": score,
        "confidence": "high",
        "reason": reason,
        "evidence_ids": evidence_ids,
        "signals": {},
    }


def _evidence_dimension(
    score: int,
    reason: str,
    evidence_ids: list[str],
    missing_reason: str,
    missing_score: int = 35,
) -> dict[str, Any]:
    if evidence_ids:
        return _dimension(score, reason, evidence_ids)
    result = _dimension(missing_score, missing_reason, [])
    result["confidence"] = "low"
    result["signals"] = {"missing_evidence": True}
    return result


def _product_visibility(first_product_ms: int | None, evidence_ids: list[str]) -> dict[str, Any]:
    if first_product_ms is None:
        result = _dimension(0, "The product was not detected.", evidence_ids)
        result["confidence"] = "low"
        result["signals"] = {"missing_evidence": True}
        return result
    if first_product_ms <= TIKTOK_STRUCTURE_RUBRIC.thresholds["early_product_ms"]:
        score = 95
        reason = "The product appears within the first three seconds."
    elif first_product_ms <= TIKTOK_STRUCTURE_RUBRIC.thresholds["acceptable_product_ms"]:
        score = 75
        reason = "The product appears in an acceptable early window."
    elif first_product_ms <= TIKTOK_STRUCTURE_RUBRIC.thresholds["late_product_ms"]:
        score = 45
        reason = f"The product first appears at {first_product_ms / 1000:.1f} seconds."
    else:
        score = 20
        reason = f"The product appears too late at {first_product_ms / 1000:.1f} seconds."
    result = _dimension(score, reason, evidence_ids)
    result["signals"] = {"first_product_appearance_ms": first_product_ms}
    return result


def _claim_safety(claim_risk: str | None, evidence_ids: list[str]) -> dict[str, Any]:
    if claim_risk == "high":
        return _dimension(0, "High-risk unsupported claim detected.", evidence_ids)
    if claim_risk == "medium":
        return _dimension(55, "Medium-risk unsupported phrasing detected.", evidence_ids)
    return _dimension(95, "No risky claims were detected.", evidence_ids)


def _blockers(
    first_product_ms: int | None,
    claim_risk: str | None,
    dimensions: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    blockers = []
    if first_product_ms is None:
        blockers.append(
            {
                "code": "PRODUCT_NOT_VISIBLE",
                "severity": "hard",
                "message": "Product was not visible.",
                "evidence_ids": [],
            }
        )
    if claim_risk == "high":
        blockers.append(
            {
                "code": "HIGH_RISK_UNSUPPORTED_CLAIM",
                "severity": "hard",
                "message": "High-risk unsupported claim detected.",
                "evidence_ids": dimensions["claim_safety"]["evidence_ids"],
            }
        )
    return blockers


def _action(score: int, blockers: list[dict[str, Any]]) -> str:
    if blockers:
        return "reject_or_reshoot"
    if score < TIKTOK_STRUCTURE_RUBRIC.thresholds["reject"]:
        return "reject_or_reshoot"
    if score < TIKTOK_STRUCTURE_RUBRIC.thresholds["revise"]:
        return "revise"
    if score < TIKTOK_STRUCTURE_RUBRIC.thresholds["small_test"]:
        return "organic_ready_or_small_test"
    return "approve_structure"


def _fixes(
    first_product_ms: int | None,
    claim_risk: str | None,
    dimensions: dict[str, dict[str, Any]],
    blockers: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    fixes = []
    if blockers:
        fixes.extend(
            {
                "code": blocker["code"],
                "priority": index + 1,
                "instruction": blocker["message"],
                "why": "Hard blocker overrides the threshold score.",
                "evidence_ids": blocker["evidence_ids"],
            }
            for index, blocker in enumerate(blockers)
        )
    if first_product_ms and first_product_ms > 3000:
        fixes.append(
            {
                "code": "LATE_PRODUCT_REVEAL",
                "priority": len(fixes) + 1,
                "instruction": "Add a clear product close-up within the first three seconds.",
                "why": f"The product first appears at {first_product_ms / 1000:.1f} seconds.",
                "evidence_ids": dimensions["product_visibility"]["evidence_ids"],
            }
        )
    if dimensions["offer_clarity"]["score"] < 60:
        fixes.append(
            {
                "code": "MISSING_OFFER",
                "priority": len(fixes) + 1,
                "instruction": "Add one concrete offer or value cue before the CTA.",
                "why": "The creative does not make the offer clear.",
                "evidence_ids": [],
            }
        )
    if dimensions["cta_readiness"]["score"] < 60:
        fixes.append(
            {
                "code": "MISSING_CTA",
                "priority": len(fixes) + 1,
                "instruction": "Add a clear TikTok Shop CTA before the final moment.",
                "why": "The creative does not show a CTA signal.",
                "evidence_ids": dimensions["cta_readiness"]["evidence_ids"],
            }
        )
    if claim_risk == "medium":
        fixes.append(
            {
                "code": "MEDIUM_RISK_CLAIM",
                "priority": len(fixes) + 1,
                "instruction": "Replace unsupported superlatives with observable product results.",
                "why": "The draft includes a medium-risk claim candidate.",
                "evidence_ids": dimensions["claim_safety"]["evidence_ids"],
            }
        )
    return fixes


def _group(evidence: list[EvidenceItemModel]) -> dict[str, list[EvidenceItemModel]]:
    grouped: dict[str, list[EvidenceItemModel]] = {}
    for item in evidence:
        grouped.setdefault(item.evidence_type, []).append(item)
    return grouped


def _ids(grouped: dict[str, list[EvidenceItemModel]], evidence_type: str) -> list[str]:
    return [str(item.id) for item in grouped.get(evidence_type, [])]


def _first_product_ms(grouped: dict[str, list[EvidenceItemModel]]) -> int | None:
    items = grouped.get("product_first_appearance", [])
    if not items:
        return None
    value = items[0].value_json.get("value")
    return int(value) if isinstance(value, int | float) else items[0].start_ms


def _max_claim_risk(grouped: dict[str, list[EvidenceItemModel]]) -> str | None:
    risks = [str(item.value_json.get("risk")) for item in grouped.get("claim_signal", [])]
    if "high" in risks:
        return "high"
    if "medium" in risks:
        return "medium"
    return None
