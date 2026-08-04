from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Sequence
from typing import Literal
from uuid import NAMESPACE_URL, UUID, uuid5

from viraldy.modules.media_analysis.public import EvidenceItemModel
from viraldy.modules.products.public import ProductContextSnapshot
from viraldy.modules.tiktok_scorer.contracts_v2 import (
    ConfidenceV2,
    CreativeDirectionContextV1,
    CreativeUpgradeSuggestionV1,
    IntendedUseV1,
    ProfileSelectionV1,
    SceneInventoryV1,
    ScoreModeV2,
    TikTokDimensionResultV2,
    TikTokFindingV2,
    TikTokScoreComputationV2,
    TikTokScoreResultV2,
    TikTokStrengthV1,
)
from viraldy.modules.tiktok_scorer.direction_enrichment import (
    build_optional_upgrade,
    creative_direction_context_from_viral_kit,
)
from viraldy.modules.tiktok_scorer.evidence_analysis_v2 import (
    build_auxiliary_signals,
    build_dimension_results,
    build_evidence_findings,
    critical_evidence_unavailable,
)
from viraldy.modules.tiktok_scorer.fix_planner import compile_fix_actions
from viraldy.modules.tiktok_scorer.policy_packs import (
    HARD_BLOCK_RULE_CLASSES,
    REQUIRED_POLICY_PACKS,
)
from viraldy.modules.tiktok_scorer.profiles import TikTokScoreProfileV1, get_profile
from viraldy.modules.tiktok_scorer.scene_inventory import build_scene_inventory_from_evidence
from viraldy.modules.viral_kits.public import ViralKitVersionSnapshot

DirectionContextLoader = Callable[[], CreativeDirectionContextV1 | None]
ScoringStageV2 = Literal[
    "building_scene_inventory",
    "scoring",
    "compiling_fixes",
    "enriching_direction",
]
StageCallback = Callable[[ScoringStageV2], None]


def aggregate_dimension_score(
    dimensions: Sequence[TikTokDimensionResultV2],
    profile: TikTokScoreProfileV1,
) -> int | None:
    eligible = [
        dimension
        for dimension in dimensions
        if dimension.applicability == "applicable"
        and dimension.evidence_status != "insufficient"
        and dimension.score is not None
        and dimension.code in profile.weights
    ]
    if not eligible:
        return None
    total_weight = sum(profile.weights[dimension.code] for dimension in eligible)
    if total_weight <= 0:
        return None
    weighted_score = sum(
        (dimension.score or 0) * profile.weights[dimension.code] for dimension in eligible
    )
    return round(weighted_score / total_weight)


def aggregate_dimension_confidence(
    dimensions: Sequence[TikTokDimensionResultV2],
) -> ConfidenceV2:
    eligible = [
        dimension
        for dimension in dimensions
        if dimension.applicability == "applicable"
        and dimension.evidence_status != "insufficient"
        and dimension.score is not None
    ]
    if not eligible:
        return "low"
    confidence_value = {"low": 1, "medium": 2, "high": 3}
    average = sum(confidence_value[item.confidence] for item in eligible) / len(eligible)
    if average >= 2.5:
        return "high"
    if average >= 1.5:
        return "medium"
    return "low"


def evaluate_product_reveal_timing(
    inventory: SceneInventoryV1,
    profile: TikTokScoreProfileV1,
) -> TikTokFindingV2 | None:
    if not profile.requires_early_product_grounding:
        return None
    deadline_ms = profile.product_grounding_deadline_ms
    if deadline_ms is None:
        return None
    product_scenes = [scene for scene in inventory.scenes if scene.product_visible is True]
    if not product_scenes:
        return None
    first_scene = min(product_scenes, key=lambda scene: scene.start_ms)
    if first_scene.start_ms <= deadline_ms:
        return None
    return TikTokFindingV2(
        id=uuid5(
            NAMESPACE_URL,
            (
                "viraldy:tiktok-finding:product-grounding:"
                f"{inventory.asset_version_id}:{profile.code}:{first_scene.scene_id}"
            ),
        ),
        code="PROFILE_PRODUCT_GROUNDING_LATE",
        rule_code=f"{profile.code.upper()}_PRODUCT_GROUNDING",
        rule_class="contextual_guideline",
        source_dimension="product_visibility",
        severity="high",
        priority="P1",
        applicability="applicable",
        evidence_status="sufficient",
        title="Product grounding arrives late for this format",
        reason=(
            f"The selected {profile.label} profile relies on product grounding by "
            f"{deadline_ms}ms, while the first verified product scene starts at "
            f"{first_scene.start_ms}ms."
        ),
        expected={
            "profile_code": profile.code,
            "target_start_ms": deadline_ms,
            "product_grounded_by_ms": deadline_ms,
        },
        observed={
            "first_product_scene_id": str(first_scene.scene_id),
            "first_product_start_ms": first_scene.start_ms,
        },
        target_time_range_ms=(first_scene.start_ms, first_scene.end_ms),
        evidence_ids=list(first_scene.evidence_ids),
        uncertainty=[],
        requires_seller_truth=False,
        can_be_resolved_by_edit=first_scene.reusable_for_edit,
        requires_physical_reshoot=False,
    )


def score_tiktok_v2(
    computation: TikTokScoreComputationV2,
    *,
    direction_context_loader: DirectionContextLoader | None = None,
    stage_callback: StageCallback | None = None,
) -> TikTokScoreResultV2:
    profile = get_profile(computation.profile_selection.profile_code)
    overall_score = aggregate_dimension_score(computation.dimensions, profile)
    findings = _with_profile_findings(computation, profile)
    _emit_stage(stage_callback, "compiling_fixes")
    required_fixes = compile_fix_actions(findings, computation.scene_inventory)
    critical_evidence_unavailable = (
        computation.critical_evidence_unavailable
        or computation.scene_inventory.duration_ms is None
        or (overall_score is None and computation.scene_inventory.coverage_status == "insufficient")
    )
    decision = _decision(
        overall_score=overall_score,
        structurally_ready_threshold=profile.structurally_ready_threshold,
        findings=findings,
        has_p0_required_fix=any(
            action.priority == "P0" and action.recommendation_class == "required_fix"
            for action in required_fixes
        ),
        critical_evidence_unavailable=critical_evidence_unavailable,
    )
    uncertainty: list[str] = []
    optional_upgrades: list[CreativeUpgradeSuggestionV1] = []
    if direction_context_loader is not None:
        _emit_stage(stage_callback, "enriching_direction")
        try:
            context = direction_context_loader()
            if context is not None:
                suggestion = build_optional_upgrade(context, computation)
                if suggestion is not None:
                    optional_upgrades = [suggestion]
        except Exception:
            uncertainty.append("optional creative direction unavailable")
    confidence = _confidence_with_inventory(
        aggregate_dimension_confidence(computation.dimensions),
        computation.scene_inventory,
    )
    return TikTokScoreResultV2(
        asset_version_id=computation.asset_version_id,
        profile_selection=computation.profile_selection,
        intended_use=computation.intended_use,
        market=computation.market,
        objective=computation.objective,
        product_snapshot_hash=computation.product_snapshot_hash,
        policy_pack_versions=(
            computation.policy_pack_versions
            or {code: pack.version for code, pack in REQUIRED_POLICY_PACKS.items()}
        ),
        scene_inventory=computation.scene_inventory,
        overall_score=overall_score,
        overall_confidence=confidence,
        creative_structure_decision=decision,
        paid_use_rights_status=_rights_status(computation),
        final_paid_readiness=_paid_readiness(computation, decision),
        dimensions=list(computation.dimensions),
        findings=findings,
        required_fixes=required_fixes,
        strengths=_strengths(computation.dimensions),
        auxiliary_signals=computation.auxiliary_signals,
        optional_upgrades=optional_upgrades,
        evidence_ids=list(computation.scene_inventory.evidence_ids),
        uncertainty=uncertainty,
    )


def analyze_tiktok_evidence_v2(
    evidence: list[EvidenceItemModel],
    *,
    asset_version_id: UUID,
    duration_ms: int | None,
    score_mode: ScoreModeV2,
    profile_selection: ProfileSelectionV1,
    intended_use: IntendedUseV1,
    audio_available: bool | None,
    product_context_snapshot: ProductContextSnapshot | None = None,
    direction_snapshot: ViralKitVersionSnapshot | None = None,
    direction_context: CreativeDirectionContextV1 | None = None,
    market: str | None = None,
    objective: str | None = None,
    asr_coverage: float | None = None,
    ocr_coverage: float | None = None,
    target_query: str | None = None,
    target_buyer_question: str | None = None,
    selected_search_topic: str | None = None,
    content_gap_topic: str | None = None,
    stage_callback: StageCallback | None = None,
) -> TikTokScoreResultV2:
    """Run the complete deterministic V2 domain pipeline over persisted evidence."""

    _validate_analysis_inputs(
        evidence,
        asset_version_id=asset_version_id,
        score_mode=score_mode,
        product_context_snapshot=product_context_snapshot,
    )
    _emit_stage(stage_callback, "building_scene_inventory")
    inventory = build_scene_inventory_from_evidence(
        asset_version_id=asset_version_id,
        duration_ms=duration_ms,
        evidence=evidence,
        audio_available=audio_available,
        asr_coverage=asr_coverage,
        ocr_coverage=ocr_coverage,
    )
    _emit_stage(stage_callback, "scoring")
    dimensions = build_dimension_results(
        evidence,
        product_context_snapshot=product_context_snapshot,
    )
    findings = build_evidence_findings(
        evidence,
        inventory=inventory,
        profile_code=profile_selection.profile_code,
        intended_use=intended_use,
        product_context_snapshot=product_context_snapshot,
    )
    product_snapshot_hash = _product_snapshot_hash(product_context_snapshot)
    resolved_market = market or _product_market(product_context_snapshot)
    computation = TikTokScoreComputationV2(
        asset_version_id=asset_version_id,
        profile_selection=profile_selection,
        intended_use=intended_use,
        market=resolved_market,
        objective=objective,
        product_snapshot_hash=product_snapshot_hash,
        direction_governance_conflicts=_direction_governance_conflicts(
            direction_context,
            product_context_snapshot,
        ),
        policy_pack_versions={code: pack.version for code, pack in REQUIRED_POLICY_PACKS.items()},
        scene_inventory=inventory,
        dimensions=dimensions,
        findings=findings,
        critical_evidence_unavailable=critical_evidence_unavailable(evidence, inventory),
        auxiliary_signals=build_auxiliary_signals(
            evidence,
            target_query=target_query,
            target_buyer_question=target_buyer_question,
            selected_search_topic=selected_search_topic,
            content_gap_topic=content_gap_topic,
        ),
    )

    loader = _direction_loader(
        direction_context=direction_context,
        direction_snapshot=direction_snapshot,
        product_snapshot_hash=product_snapshot_hash,
    )
    return score_tiktok_v2(
        computation,
        direction_context_loader=loader,
        stage_callback=stage_callback,
    )


def _with_profile_findings(
    computation: TikTokScoreComputationV2,
    profile: TikTokScoreProfileV1,
) -> list[TikTokFindingV2]:
    findings = list(computation.findings)
    timing = evaluate_product_reveal_timing(computation.scene_inventory, profile)
    if timing is not None and not any(item.code == timing.code for item in findings):
        findings.append(timing)
    return findings


def _decision(
    *,
    overall_score: int | None,
    structurally_ready_threshold: int,
    findings: Sequence[TikTokFindingV2],
    has_p0_required_fix: bool,
    critical_evidence_unavailable: bool,
) -> str:
    if critical_evidence_unavailable:
        return "request_better_media"
    verified_hard_blocker = any(
        finding.applicability == "applicable"
        and finding.evidence_status == "sufficient"
        and finding.severity == "hard"
        and finding.rule_class in HARD_BLOCK_RULE_CLASSES
        for finding in findings
    )
    if verified_hard_blocker:
        return "blocked"
    if has_p0_required_fix:
        return "revise"
    if overall_score is not None and overall_score >= structurally_ready_threshold:
        return "structurally_ready"
    return "usable_with_improvements"


def _confidence_with_inventory(
    dimension_confidence: ConfidenceV2,
    inventory: SceneInventoryV1,
) -> ConfidenceV2:
    rank = {"low": 1, "medium": 2, "high": 3}
    value = min(rank[dimension_confidence], rank[inventory.overall_confidence])
    if inventory.coverage_status == "partial":
        value = min(value, 2)
    if inventory.coverage_status == "insufficient":
        value = 1
    if value == 3:
        return "high"
    if value == 2:
        return "medium"
    return "low"


def _strengths(
    dimensions: Sequence[TikTokDimensionResultV2],
) -> list[TikTokStrengthV1]:
    return [
        TikTokStrengthV1(
            code=f"PRESERVE_{dimension.code.upper()}",
            title=f"Preserve {dimension.label.lower()}",
            source_dimension=dimension.code,
            evidence_ids=list(dimension.evidence_ids),
        )
        for dimension in dimensions
        if dimension.applicability == "applicable"
        and dimension.evidence_status != "insufficient"
        and dimension.score is not None
        and dimension.score >= 80
        and dimension.evidence_ids
    ]


def _rights_status(computation: TikTokScoreComputationV2) -> str:
    if computation.intended_use == "tiktok_organic":
        return "not_applicable"
    return computation.paid_use_rights_status


def _paid_readiness(computation: TikTokScoreComputationV2, decision: str) -> str:
    if computation.intended_use == "tiktok_organic":
        return "not_applicable"
    if decision in {"request_better_media", "blocked", "revise"}:
        return "not_ready"
    if computation.paid_use_rights_status == "confirmed_externally":
        return "externally_confirmed"
    return "pending_rights_confirmation"


def _validate_analysis_inputs(
    evidence: Sequence[EvidenceItemModel],
    *,
    asset_version_id: UUID,
    score_mode: ScoreModeV2,
    product_context_snapshot: ProductContextSnapshot | None,
) -> None:
    if score_mode == "product_aware" and product_context_snapshot is None:
        raise ValueError("Product-Aware Score requires an immutable Product Context snapshot")
    mismatched = [
        item.id
        for item in evidence
        if getattr(item, "asset_version_id", asset_version_id) != asset_version_id
    ]
    if mismatched:
        raise ValueError("all evidence must reference the requested immutable asset version")


def _product_snapshot_hash(snapshot: ProductContextSnapshot | None) -> str | None:
    if snapshot is None:
        return None
    canonical = json.dumps(
        snapshot.product_context.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _product_market(snapshot: ProductContextSnapshot | None) -> str | None:
    if snapshot is None:
        return None
    market = snapshot.product_context.identity.market.strip()
    return None if not market or market.casefold() == "unknown" else market


def _direction_governance_conflicts(
    context: CreativeDirectionContextV1 | None,
    snapshot: ProductContextSnapshot | None,
) -> list[str]:
    if context is None or snapshot is None:
        return []
    prohibited_claims = {
        " ".join(rule.text.casefold().split())
        for rule in snapshot.product_context.governance.claims
        if rule.rule_type == "prohibited"
    }
    return [
        claim
        for claim in context.allowed_claims
        if " ".join(claim.casefold().split()) in prohibited_claims
    ]


def _direction_loader(
    *,
    direction_context: CreativeDirectionContextV1 | None,
    direction_snapshot: ViralKitVersionSnapshot | None,
    product_snapshot_hash: str | None,
) -> DirectionContextLoader | None:
    if direction_context is not None:
        return lambda: direction_context
    if direction_snapshot is None:
        return None
    return lambda: creative_direction_context_from_viral_kit(
        direction_snapshot,
        product_snapshot_hash=product_snapshot_hash,
    )


def _emit_stage(callback: StageCallback | None, stage: ScoringStageV2) -> None:
    if callback is not None:
        callback(stage)


__all__ = [
    "ScoringStageV2",
    "StageCallback",
    "aggregate_dimension_confidence",
    "aggregate_dimension_score",
    "analyze_tiktok_evidence_v2",
    "evaluate_product_reveal_timing",
    "score_tiktok_v2",
]
