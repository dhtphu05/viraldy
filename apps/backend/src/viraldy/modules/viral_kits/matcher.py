from __future__ import annotations

from viraldy.modules.pattern_kits.public import PatternKitVersionSnapshot
from viraldy.modules.products.contracts import ProductContextV1
from viraldy.modules.viral_kits.contracts import (
    PatternApplicabilityStatusV1,
    ViralKitPatternMatchV1,
)
from viraldy.modules.viral_kits.schemas import CreateViralKitRequest


def match_patterns(
    *,
    product_context: ProductContextV1,
    patterns: list[PatternKitVersionSnapshot],
    request: CreateViralKitRequest,
) -> list[ViralKitPatternMatchV1]:
    return [
        match_pattern(product_context=product_context, pattern=snapshot, request=request)
        for snapshot in patterns
    ]


def match_pattern(
    *,
    product_context: ProductContextV1,
    pattern: PatternKitVersionSnapshot,
    request: CreateViralKitRequest,
) -> ViralKitPatternMatchV1:
    applicability = pattern.pattern.applicability
    product_traits = _product_traits(product_context)
    conflicts: list[str] = []
    matched: list[str] = []
    score = 0.0

    category = product_context.identity.category
    if category in applicability.unsuitable_categories:
        conflicts.append(f"category:{category}")
    elif category in applicability.suitable_categories:
        score += 0.25
        matched.append(f"category:{category}")
    elif not applicability.suitable_categories or category == "unknown":
        score += 0.1
        matched.append("category:unknown_or_unrestricted")
    else:
        conflicts.append(f"category_not_listed:{category}")

    if request.platform in applicability.platforms:
        score += 0.15
        matched.append(f"platform:{request.platform}")
    elif applicability.platforms:
        conflicts.append(f"platform_not_listed:{request.platform}")
    else:
        score += 0.05

    if request.target_market in applicability.markets:
        score += 0.15
        matched.append(f"market:{request.target_market}")
    elif applicability.markets:
        conflicts.append(f"market_not_listed:{request.target_market}")
    else:
        score += 0.05

    if request.objective in applicability.objectives:
        score += 0.15
        matched.append(f"objective:{request.objective}")
    elif applicability.objectives:
        conflicts.append(f"objective_not_listed:{request.objective}")
    else:
        score += 0.05

    required_traits = [trait.lower() for trait in applicability.required_product_traits]
    missing_traits = [trait for trait in required_traits if trait not in product_traits]
    if missing_traits:
        conflicts.extend(f"required_trait_missing:{trait}" for trait in missing_traits)
    else:
        score += 0.1

    preferred_matches = [
        trait
        for trait in applicability.preferred_product_traits
        if trait.lower() in product_traits
    ]
    if preferred_matches:
        score += min(0.1, len(preferred_matches) * 0.05)
        matched.extend(f"trait:{trait}" for trait in preferred_matches)

    if _has_visual_demo(product_context):
        score += 0.1
        matched.append("visual_demo")

    if product_context.governance.required_disclosures:
        matched.append("required_disclosures_present")

    status = _status_for(score, conflicts, request.applicability_override_reason)
    return ViralKitPatternMatchV1(
        pattern_kit_version_id=pattern.pattern_kit_version_id,
        match_score=round(min(score, 1.0), 3),
        applicability_status=status,
        matched_product_traits=matched,
        conflicts=conflicts,
        selection_reason=_selection_reason(status, matched, conflicts),
        evidence_summary=_evidence_summary(pattern),
    )


def _status_for(
    score: float,
    conflicts: list[str],
    override_reason: str | None,
) -> PatternApplicabilityStatusV1:
    if conflicts and score < 0.55:
        return "override" if override_reason else "rejected"
    if score >= 0.65 and not conflicts:
        return "matched"
    if score >= 0.35:
        return "partial"
    return "override" if override_reason else "rejected"


def _selection_reason(
    status: PatternApplicabilityStatusV1,
    matched: list[str],
    conflicts: list[str],
) -> str:
    if status == "rejected":
        return "PatternKit has hard applicability conflicts for this product context."
    if status == "override":
        return "PatternKit is included by explicit human override despite conflicts."
    if conflicts:
        return "PatternKit partially fits but carries documented conflicts."
    if matched:
        return "PatternKit matches product, platform, market, or objective constraints."
    return "PatternKit has no hard conflict and limited applicability metadata."


def _evidence_summary(pattern: PatternKitVersionSnapshot) -> list[str]:
    values: list[str] = []
    for beat in pattern.pattern.sequence[:3]:
        values.append(f"{beat.beat_type}:{len(beat.evidence_refs)} evidence refs")
    return values


def _product_traits(context: ProductContextV1) -> set[str]:
    values = {
        context.identity.category.lower(),
        context.identity.market.lower(),
    }
    values.update(feature.label.lower() for feature in context.features)
    values.update(benefit.label.lower() for benefit in context.benefits)
    values.update(context.creative.demonstration_mechanisms)
    if _has_visual_demo(context):
        values.add("observable product presence")
        values.add("clear buyer context")
        values.add("visual_demo")
    return {value.strip().lower() for value in values if value and value.strip()}


def _has_visual_demo(context: ProductContextV1) -> bool:
    if context.creative.demonstration_mechanisms:
        return True
    return any(feature.visual_demo_possible for feature in context.features)
