from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, cast
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from viraldy.modules.media_analysis.public import EvidenceItemModel
from viraldy.modules.products.contracts import ProductGovernanceV1, build_minimal_product_context
from viraldy.modules.products.public import ProductContextSnapshot
from viraldy.modules.tiktok_scorer.comparison import compare_score_results
from viraldy.modules.tiktok_scorer.contracts_v2 import (
    CreativeDirectionContextV1,
    ProfileSelectionV1,
    SceneInventoryV1,
    TikTokAuxiliarySignalsV1,
    TikTokDimensionResultV2,
    TikTokFindingV2,
    TikTokScoreComputationV2,
    VideoEditOperationV1,
    VideoSceneV1,
)
from viraldy.modules.tiktok_scorer.direction_enrichment import (
    build_optional_upgrade,
)
from viraldy.modules.tiktok_scorer.engine_v2 import (
    aggregate_dimension_confidence,
    aggregate_dimension_score,
    analyze_tiktok_evidence_v2,
    evaluate_product_reveal_timing,
    score_tiktok_v2,
)
from viraldy.modules.tiktok_scorer.fix_planner import compile_fix_actions
from viraldy.modules.tiktok_scorer.policy_packs import (
    REQUIRED_POLICY_PACKS,
    PolicyRuleV1,
    resolve_policy_rules,
)
from viraldy.modules.tiktok_scorer.profiles import PROFILE_CODES, get_profile

ASSET_ID = UUID("00000000-0000-0000-0000-000000000001")
EVIDENCE_ID = UUID("00000000-0000-0000-0000-000000000002")
SECOND_EVIDENCE_ID = UUID("00000000-0000-0000-0000-000000000003")
SCENE_ID = UUID("00000000-0000-0000-0000-000000000004")


def test_unknown_and_not_applicable_dimensions_are_excluded_from_aggregation() -> None:
    dimensions = [
        _dimension("hook_clarity", 80),
        _dimension(
            "offer_clarity",
            None,
            applicability="unknown",
            evidence_status="insufficient",
        ),
        _dimension(
            "claim_safety",
            None,
            applicability="not_applicable",
            evidence_status="insufficient",
        ),
    ]

    assert aggregate_dimension_score(dimensions, get_profile("general_tiktok_v1")) == 80


def test_insufficient_evidence_is_not_a_zero_score() -> None:
    insufficient = _dimension(
        "demo_clarity",
        None,
        evidence_status="insufficient",
        confidence="low",
    )

    assert aggregate_dimension_score([insufficient], get_profile("general_tiktok_v1")) is None
    with pytest.raises(ValidationError):
        _dimension("demo_clarity", 0, evidence_status="insufficient")


def test_confidence_is_separate_from_structural_score() -> None:
    high_confidence = [_dimension("hook_clarity", 72, confidence="high")]
    low_confidence = [_dimension("hook_clarity", 72, confidence="low")]
    profile = get_profile("general_tiktok_v1")

    assert aggregate_dimension_score(high_confidence, profile) == 72
    assert aggregate_dimension_score(low_confidence, profile) == 72
    assert aggregate_dimension_confidence(high_confidence) == "high"
    assert aggregate_dimension_confidence(low_confidence) == "low"


def test_decision_precedence_requests_media_then_blocks_then_revises() -> None:
    hard_finding = _finding(
        code="PRODUCT_MISMATCH",
        severity="hard",
        priority="P0",
        rule_class="product_governance_rule",
        requires_physical_reshoot=True,
    )
    blocked_input = _request(dimensions=[_dimension("hook_clarity", 96)], findings=[hard_finding])

    blocked = score_tiktok_v2(blocked_input)
    unavailable = score_tiktok_v2(
        blocked_input.model_copy(update={"critical_evidence_unavailable": True})
    )
    revise = score_tiktok_v2(
        _request(
            dimensions=[_dimension("hook_clarity", 96)],
            findings=[
                _finding(
                    code="PROFILE_CRITICAL_GAP",
                    severity="high",
                    priority="P0",
                    rule_class="contextual_guideline",
                    requires_physical_reshoot=False,
                )
            ],
        )
    )

    assert unavailable.creative_structure_decision == "request_better_media"
    assert blocked.creative_structure_decision == "blocked"
    assert blocked.overall_score == 96
    assert revise.creative_structure_decision == "revise"


def test_story_led_and_product_led_profiles_apply_different_reveal_timing() -> None:
    inventory = _inventory(product_start_ms=4500)

    story_finding = evaluate_product_reveal_timing(
        inventory,
        get_profile("story_led_pov_v1"),
    )
    product_finding = evaluate_product_reveal_timing(
        inventory,
        get_profile("product_led_demo_v1"),
    )

    assert story_finding is None
    assert product_finding is not None
    assert product_finding.code == "PROFILE_PRODUCT_GROUNDING_LATE"
    assert product_finding.severity != "hard"


def test_no_audio_can_still_produce_valid_visual_diagnostics() -> None:
    result = score_tiktok_v2(
        _request(
            inventory=_inventory(audio_available=False),
            dimensions=[
                _dimension("hook_clarity", 82),
                _dimension("product_visibility", 86),
            ],
        )
    )

    assert result.overall_score is not None
    assert result.creative_structure_decision != "request_better_media"
    assert result.scene_inventory.audio_available is False


def test_product_mismatch_compiles_to_a_physical_reshoot() -> None:
    finding = _finding(
        code="PRODUCT_MISMATCH",
        severity="hard",
        priority="P0",
        rule_class="product_governance_rule",
        requires_physical_reshoot=True,
    )

    action = compile_fix_actions([finding], _inventory())[0]

    assert action.fix_type == "reshoot_scene"
    assert action.reshoot_required is True
    assert action.video_operations == []
    assert action.owner_role == "creator"


def test_missing_seller_truth_requests_confirmation() -> None:
    finding = _finding(
        code="OFFER_TRUTH_MISSING",
        severity="high",
        priority="P0",
        rule_class="product_governance_rule",
        requires_seller_truth=True,
    )

    action = compile_fix_actions([finding], _inventory())[0]

    assert action.fix_type == "confirm_seller_input"
    assert action.owner_role == "seller"
    assert action.required_inputs
    assert action.reshoot_required is False


def test_edit_operation_only_references_a_scene_that_exists() -> None:
    finding = _finding(
        code="PROFILE_PRODUCT_GROUNDING_LATE",
        severity="high",
        priority="P1",
        rule_class="contextual_guideline",
        can_be_resolved_by_edit=True,
        target_time_range_ms=(4500, 5500),
    )

    action = compile_fix_actions([finding], _inventory(product_start_ms=4500))[0]
    scene_ids = {scene.scene_id for scene in _inventory(product_start_ms=4500).scenes}

    assert action.video_operations
    assert all(operation.source_scene_id in scene_ids for operation in action.video_operations)


def test_claim_copy_edit_requires_verified_replacement_and_observed_modality() -> None:
    verified = _finding(
        code="UNSAFE_CLAIM_COPY",
        severity="high",
        priority="P1",
        rule_class="product_governance_rule",
        can_be_resolved_by_edit=True,
        target_time_range_ms=(1000, 2000),
    ).model_copy(
        update={
            "expected": {"approved_replacement_text": "Designed for daily countertop use."},
            "observed": {"modality": "overlay", "claim_text": "Guaranteed result"},
        }
    )
    unverified = verified.model_copy(update={"expected": {"claim_status": "seller approved"}})

    edited = compile_fix_actions([verified], _inventory())[0]
    confirmation = compile_fix_actions([unverified], _inventory())[0]

    assert edited.fix_type == "replace_overlay_copy"
    assert edited.video_operations[0].operation == "replace_overlay"
    assert edited.video_operations[0].text_value == "Designed for daily countertop use."
    assert confirmation.fix_type == "confirm_seller_input"
    assert confirmation.video_operations == []


def test_disclosure_overlay_uses_only_approved_text_and_evidence_range() -> None:
    finding = _finding(
        code="REQUIRED_DISCLOSURE_MISSING",
        severity="hard",
        priority="P0",
        rule_class="official_hard_rule",
        can_be_resolved_by_edit=True,
        target_time_range_ms=(1000, 2000),
    ).model_copy(update={"expected": {"approved_disclosure_text": "Paid partnership"}})

    action = compile_fix_actions([finding], _inventory())[0]

    assert action.fix_type == "add_overlay"
    assert action.video_operations[0].operation == "add_overlay"
    assert action.video_operations[0].target_start_ms == 1000
    assert action.video_operations[0].text_value == "Paid partnership"


def test_result_contract_rejects_unknown_evidence_and_out_of_range_operations() -> None:
    unknown_evidence_finding = _finding(
        code="UNKNOWN_EVIDENCE",
        evidence_ids=[uuid4()],
        severity="high",
        priority="P1",
        rule_class="contextual_guideline",
    )
    with pytest.raises(ValidationError, match="evidence"):
        score_tiktok_v2(
            _request(
                dimensions=[_dimension("hook_clarity", 80)],
                findings=[unknown_evidence_finding],
            )
        )

    with pytest.raises(ValueError, match="duration"):
        VideoEditOperationV1(
            operation="move_clip",
            source_scene_id=SCENE_ID,
            source_range_ms=(9000, 11_000),
            target_start_ms=0,
            target_duration_ms=2000,
            evidence_ids=[EVIDENCE_ID],
            feasibility="verified_possible",
        ).validate_against_inventory(_inventory())


def test_optional_direction_never_changes_score_or_required_fixes() -> None:
    request = _request(
        dimensions=[_dimension("hook_clarity", 76)],
        findings=[
            _finding(
                code="HOOK_NEEDS_CLARITY",
                severity="high",
                priority="P1",
                rule_class="contextual_guideline",
            )
        ],
        product_snapshot_hash="same-product",
    )
    baseline = score_tiktok_v2(request)
    enriched = score_tiktok_v2(request, direction_context_loader=_compatible_direction)

    assert enriched.overall_score == baseline.overall_score
    assert enriched.creative_structure_decision == baseline.creative_structure_decision
    assert enriched.required_fixes == baseline.required_fixes
    assert enriched.optional_upgrades
    assert all(upgrade.affects_score is False for upgrade in enriched.optional_upgrades)


def test_direction_service_failure_does_not_drop_required_fixes() -> None:
    request = _request(
        dimensions=[_dimension("hook_clarity", 76)],
        findings=[
            _finding(
                code="HOOK_NEEDS_CLARITY",
                severity="high",
                priority="P1",
                rule_class="contextual_guideline",
            )
        ],
    )

    def fail() -> CreativeDirectionContextV1:
        raise RuntimeError("direction service unavailable")

    result = score_tiktok_v2(request, direction_context_loader=fail)

    assert result.required_fixes
    assert result.optional_upgrades == []
    assert "optional creative direction unavailable" in result.uncertainty


def test_incompatible_direction_is_ignored() -> None:
    request = _request(
        dimensions=[_dimension("hook_clarity", 76)],
        product_snapshot_hash="different-product",
    )

    assert build_optional_upgrade(_compatible_direction(), request) is None


def test_revision_comparison_verifies_actions_and_detects_regressions() -> None:
    blocker = _finding(
        code="PRODUCT_MISMATCH",
        severity="hard",
        priority="P0",
        rule_class="product_governance_rule",
        requires_physical_reshoot=True,
    )
    before = score_tiktok_v2(
        _request(dimensions=[_dimension("product_visibility", 40)], findings=[blocker])
    )
    regression = _finding(
        code="CTA_UNSAFE_ZONE",
        severity="high",
        priority="P1",
        rule_class="contextual_guideline",
        source_dimension="cta_readiness",
    )
    after = score_tiktok_v2(
        _request(
            asset_version_id=uuid4(),
            inventory=_inventory(asset_version_id=uuid4()),
            dimensions=[_dimension("product_visibility", 82), _dimension("cta_readiness", 55)],
            findings=[regression],
        )
    )

    comparison = compare_score_results(before, after)

    assert [item.code for item in comparison.resolved_blockers] == ["PRODUCT_MISMATCH"]
    assert [item.code for item in comparison.new_regressions] == ["CTA_UNSAFE_ZONE"]
    assert comparison.actions_verified[0].status == "verified"
    assert (
        comparison.dimension_changes[0].before_score != comparison.dimension_changes[0].after_score
    )
    assert comparison.final_next_action == "address_new_regressions"


def test_revision_comparison_filters_verification_to_accepted_actions() -> None:
    first = _finding(
        code="PRODUCT_MISMATCH",
        severity="hard",
        priority="P0",
        rule_class="product_governance_rule",
        requires_physical_reshoot=True,
    )
    second = _finding(
        code="PROOF_SCENE_MISSING",
        severity="high",
        priority="P1",
        rule_class="contextual_guideline",
        requires_physical_reshoot=True,
    )
    before = score_tiktok_v2(
        _request(dimensions=[_dimension("proof_strength", 45)], findings=[first, second])
    )
    after = score_tiktok_v2(
        _request(
            inventory=_inventory(asset_version_id=uuid4()),
            dimensions=[_dimension("proof_strength", 85)],
        )
    )
    accepted_id = before.required_fixes[1].id

    comparison = compare_score_results(
        before,
        after,
        accepted_fix_action_ids={accepted_id},
    )

    assert [verification.action_id for verification in comparison.actions_verified] == [accepted_id]


@pytest.mark.parametrize(
    ("decision", "expected_next_action"),
    [
        ("revise", "resolve_required_actions"),
        ("blocked", "review_unresolved_blockers"),
    ],
)
def test_comparison_never_reports_no_changes_for_revise_or_blocked_decision(
    decision: str,
    expected_next_action: str,
) -> None:
    before = score_tiktok_v2(_request(dimensions=[_dimension("hook_clarity", 90)]))
    after = before.model_copy(update={"creative_structure_decision": decision})

    comparison = compare_score_results(before, after, accepted_fix_action_ids=set())

    assert comparison.final_next_action == expected_next_action


def test_comparison_detects_a_differently_coded_required_fix() -> None:
    finding = _finding(
        code="HOOK_STRUCTURE_GAP",
        severity="high",
        priority="P1",
        rule_class="contextual_guideline",
        source_dimension="hook_clarity",
        requires_physical_reshoot=True,
    )
    before = score_tiktok_v2(
        _request(dimensions=[_dimension("hook_clarity", 75)], findings=[finding])
    )
    changed_fix = before.required_fixes[0].model_copy(update={"code": "FIX_HOOK_STRUCTURE_GAP_V2"})
    after = before.model_copy(
        update={
            "required_fixes": [changed_fix],
            "creative_structure_decision": "structurally_ready",
        }
    )

    comparison = compare_score_results(before, after, accepted_fix_action_ids=set())

    assert comparison.new_regressions == []
    assert comparison.actions_verified == []
    assert comparison.final_next_action == "resolve_required_actions"


def test_accepted_action_is_not_verified_without_revision_evidence() -> None:
    finding = _finding(
        code="PRODUCT_SCENE_GAP",
        severity="high",
        priority="P1",
        rule_class="contextual_guideline",
        requires_physical_reshoot=True,
    )
    before = score_tiktok_v2(
        _request(dimensions=[_dimension("product_visibility", 45)], findings=[finding])
    )
    accepted_id = before.required_fixes[0].id
    after = score_tiktok_v2(
        _request(
            inventory=_inventory(asset_version_id=uuid4()),
            dimensions=[
                _dimension(
                    "product_visibility",
                    None,
                    evidence_status="insufficient",
                    confidence="low",
                )
            ],
        )
    )

    comparison = compare_score_results(
        before,
        after,
        accepted_fix_action_ids={accepted_id},
    )

    assert comparison.actions_verified[0].status == "not_evaluated"
    assert comparison.actions_verified[0].evidence_after_ids == []
    assert comparison.final_next_action == "resolve_required_actions"


def test_all_required_profiles_are_versioned_and_valid() -> None:
    assert PROFILE_CODES == {
        "general_tiktok_v1",
        "product_led_demo_v1",
        "creator_review_v1",
        "story_led_pov_v1",
        "tutorial_howto_v1",
        "unboxing_reaction_v1",
        "comment_reply_faq_v1",
        "offer_led_shop_v1",
    }
    for code in PROFILE_CODES:
        profile = get_profile(code)
        assert profile.version == 1
        assert round(sum(profile.weights.values()), 6) == 1


def test_auxiliary_signals_default_to_not_evaluated_and_do_not_affect_score() -> None:
    request = _request(dimensions=[_dimension("hook_clarity", 83)])
    baseline = score_tiktok_v2(request)
    directional = score_tiktok_v2(
        request.model_copy(
            update={
                "auxiliary_signals": TikTokAuxiliarySignalsV1.directional_defaults(
                    trend_reason="A current format may be relevant, but causality is unverified."
                )
            }
        )
    )

    assert baseline.auxiliary_signals.search_discovery_readiness.status == "not_evaluated"
    assert directional.overall_score == baseline.overall_score
    assert directional.creative_structure_decision == baseline.creative_structure_decision


def test_only_governance_or_operational_rule_classes_can_hard_block() -> None:
    with pytest.raises(ValidationError, match="hard-block"):
        PolicyRuleV1(
            code="BAD_CONTEXTUAL_BLOCKER",
            pack_code="agency_directional_pattern_pack",
            pack_version="2026.1",
            source_tier="C_COMMUNITY_SIGNAL",
            rule_class="contextual_guideline",
            applicability="Any TikTok video",
            required_inputs=[],
            unknown_behavior="not_applicable",
            exceptions=[],
            can_hard_block=True,
            fix_template_code="REVIEW_CONTEXT",
            effective_at=datetime(2026, 1, 1, tzinfo=UTC),
            expires_at=None,
            provenance_source_ids=["community-pattern"],
        )


def test_all_required_policy_packs_are_seeded() -> None:
    assert set(REQUIRED_POLICY_PACKS) == {
        "tiktok_us_official_policy_pack",
        "tiktok_us_creative_guideline_pack",
        "tiktok_2026_trend_overlay",
        "ftc_endorsement_pack",
        "pod_personalization_pack",
        "dropshipping_product_truth_pack",
        "ugc_creator_workflow_pack",
        "agency_directional_pattern_pack",
    }


def test_trend_expiry_is_pinned_for_completed_runs() -> None:
    overlay = REQUIRED_POLICY_PACKS["tiktok_2026_trend_overlay"]
    completed_at = datetime(2026, 7, 1, tzinfo=UTC)
    after_expiry = datetime(2027, 2, 1, tzinfo=UTC)
    original_result = score_tiktok_v2(_request(dimensions=[_dimension("hook_clarity", 83)]))
    original_dump = original_result.model_dump(mode="json")

    active_for_new_run = resolve_policy_rules([overlay], evaluation_at=after_expiry)
    pinned_for_completed_run = resolve_policy_rules(
        [overlay],
        evaluation_at=after_expiry,
        completed_at=completed_at,
    )

    assert active_for_new_run == ()
    assert pinned_for_completed_run
    assert original_result.model_dump(mode="json") == original_dump


def test_evidence_entrypoint_builds_complete_diagnostics_and_real_stages() -> None:
    evidence = _complete_evidence()
    stages: list[str] = []

    result = analyze_tiktok_evidence_v2(
        evidence,
        asset_version_id=ASSET_ID,
        duration_ms=10_000,
        score_mode="quick",
        profile_selection=ProfileSelectionV1(
            profile_code="product_led_demo_v1",
            selection_mode="model_suggested_user_confirmed",
            confidence=0.88,
            alternative_profiles=["general_tiktok_v1"],
            evidence_ids=[evidence[0].id],
        ),
        intended_use="tiktok_organic",
        audio_available=False,
        ocr_coverage=0.9,
        market="US",
        target_query="counter organizer",
        stage_callback=stages.append,
    )

    assert [dimension.code for dimension in result.dimensions] == [
        "hook_clarity",
        "product_visibility",
        "demo_clarity",
        "proof_strength",
        "creator_authenticity",
        "offer_clarity",
        "cta_readiness",
        "tiktok_native_fit",
        "claim_safety",
    ]
    assert all(dimension.score is not None for dimension in result.dimensions)
    assert result.scene_inventory.scenes
    assert result.scene_inventory.audio_available is False
    assert result.overall_score is not None
    assert result.auxiliary_signals.search_discovery_readiness.status == "evaluated"
    assert stages == ["building_scene_inventory", "scoring", "compiling_fixes"]


def test_evidence_entrypoint_compiles_missing_demo_proof_and_cta_actions() -> None:
    evidence = _complete_evidence()
    retained_types = {"hook_signal", "product_appearance", "platform_signal", "on_screen_text"}
    sparse_evidence = [item for item in evidence if item.evidence_type in retained_types]

    result = analyze_tiktok_evidence_v2(
        sparse_evidence,
        asset_version_id=ASSET_ID,
        duration_ms=10_000,
        score_mode="usage_aware",
        profile_selection=ProfileSelectionV1(
            profile_code="product_led_demo_v1",
            selection_mode="user_selected",
            confidence=1,
            alternative_profiles=[],
            evidence_ids=[sparse_evidence[0].id],
        ),
        intended_use="tiktok_shop_affiliate",
        audio_available=False,
        ocr_coverage=0.9,
        market="US",
    )

    finding_codes = {finding.code for finding in result.findings}
    fix_types = {fix.source_finding_code: fix.fix_type for fix in result.required_fixes}
    assert {
        "REQUIRED_DEMO_SCENE_MISSING",
        "OBSERVABLE_PROOF_SCENE_MISSING",
        "CTA_NOT_OBSERVED",
    }.issubset(finding_codes)
    assert fix_types["REQUIRED_DEMO_SCENE_MISSING"] == "reshoot_scene"
    assert fix_types["OBSERVABLE_PROOF_SCENE_MISSING"] == "reshoot_scene"
    assert fix_types["CTA_NOT_OBSERVED"] == "add_missing_scene"


def test_product_context_disclosure_gap_is_recommendation_not_hard_block() -> None:
    evidence = _complete_evidence()
    context = build_minimal_product_context(
        name="Stretch Sofa Cover",
        description="Refreshes a sofa with a visible cover install.",
        market="US",
    ).model_copy(
        update={
            "governance": ProductGovernanceV1(
                required_disclosures=["Show or mention checking size before ordering."]
            )
        }
    )
    snapshot = ProductContextSnapshot(
        product_id=uuid4(),
        workspace_id=uuid4(),
        context_schema_version=context.schema_version,
        product_context_version=1,
        product_context=context,
    )

    result = analyze_tiktok_evidence_v2(
        evidence,
        asset_version_id=ASSET_ID,
        duration_ms=10_000,
        score_mode="product_aware",
        profile_selection=ProfileSelectionV1(
            profile_code="general_tiktok_v1",
            selection_mode="user_selected",
            confidence=1,
            alternative_profiles=[],
            evidence_ids=[evidence[0].id],
        ),
        intended_use="tiktok_organic",
        audio_available=True,
        ocr_coverage=0.9,
        product_context_snapshot=snapshot,
    )

    disclosure = next(
        finding for finding in result.findings if finding.code == "REQUIRED_DISCLOSURE_MISSING"
    )
    action = next(
        fix for fix in result.required_fixes if fix.source_finding_code == disclosure.code
    )
    assert disclosure.severity == "medium"
    assert disclosure.priority == "P2"
    assert disclosure.rule_class == "product_governance_rule"
    assert action.recommendation_class == "high_priority_improvement"
    assert result.creative_structure_decision != "blocked"


def _dimension(
    code: str,
    score: int | None,
    *,
    applicability: str = "applicable",
    evidence_status: str = "sufficient",
    confidence: str = "high",
) -> TikTokDimensionResultV2:
    return TikTokDimensionResultV2(
        code=code,
        label=code.replace("_", " ").title(),
        score=score,
        applicability=applicability,
        evidence_status=evidence_status,
        confidence=confidence,
        reason="Evidence-backed structural observation.",
        positive_signals=["observable signal"] if score is not None else [],
        missing_signals=[] if score is not None else ["responsible evidence"],
        uncertainty=[],
        evidence_ids=[EVIDENCE_ID] if score is not None else [],
        contributing_rule_codes=["TEST_RULE"],
    )


def _finding(
    *,
    code: str,
    severity: str,
    priority: str,
    rule_class: str,
    source_dimension: str = "product_visibility",
    evidence_ids: list[UUID] | None = None,
    requires_seller_truth: bool = False,
    can_be_resolved_by_edit: bool | None = None,
    requires_physical_reshoot: bool | None = None,
    target_time_range_ms: tuple[int, int] | None = (4500, 5500),
) -> TikTokFindingV2:
    return TikTokFindingV2(
        id=uuid4(),
        code=code,
        rule_code=f"RULE_{code}",
        rule_class=rule_class,
        source_dimension=source_dimension,
        severity=severity,
        priority=priority,
        applicability="applicable",
        evidence_status="sufficient",
        title=code.replace("_", " ").title(),
        reason="The observed structure conflicts with the selected context.",
        expected={"state": "verified and clear"},
        observed={"state": "missing or conflicting"},
        target_time_range_ms=target_time_range_ms,
        evidence_ids=evidence_ids if evidence_ids is not None else [EVIDENCE_ID],
        uncertainty=[],
        requires_seller_truth=requires_seller_truth,
        can_be_resolved_by_edit=can_be_resolved_by_edit,
        requires_physical_reshoot=requires_physical_reshoot,
    )


def _inventory(
    *,
    asset_version_id: UUID = ASSET_ID,
    product_start_ms: int = 1000,
    audio_available: bool | None = True,
) -> SceneInventoryV1:
    scene = VideoSceneV1(
        scene_id=SCENE_ID,
        start_ms=product_start_ms,
        end_ms=product_start_ms + 1000,
        summary="Verified product close-up.",
        shot_type="close_up",
        product_visible=True,
        product_match_confidence=0.9,
        product_visibility_quality="clear",
        spoken_text=None,
        overlay_texts=["See how it works"],
        demo_step="Show the mechanism",
        proof_role="demonstration",
        creator_present=False,
        visual_quality="good",
        continuity_group_id=None,
        reusable_for_edit=True,
        evidence_ids=[EVIDENCE_ID],
    )
    return SceneInventoryV1(
        asset_version_id=asset_version_id,
        duration_ms=10_000,
        audio_available=audio_available,
        scenes=[scene],
        asr_coverage=None if audio_available is False else 0.9,
        ocr_coverage=0.8,
        product_appearance_ranges=[(product_start_ms, product_start_ms + 1000)],
        cta_ranges=[],
        disclosure_ranges=[],
        safe_zone_observations=[],
        continuity_group_ids=[],
        evidence_ids=[EVIDENCE_ID, SECOND_EVIDENCE_ID],
        coverage_status="sufficient",
        overall_confidence="high",
        extractor_versions={"vision": "test-v1"},
    )


def _request(
    *,
    asset_version_id: UUID = ASSET_ID,
    inventory: SceneInventoryV1 | None = None,
    dimensions: list[TikTokDimensionResultV2] | None = None,
    findings: list[TikTokFindingV2] | None = None,
    product_snapshot_hash: str | None = None,
) -> TikTokScoreComputationV2:
    inventory = inventory or _inventory(asset_version_id=asset_version_id)
    return TikTokScoreComputationV2(
        asset_version_id=inventory.asset_version_id,
        profile_selection=ProfileSelectionV1(
            profile_code="general_tiktok_v1",
            selection_mode="user_selected",
            confidence=1,
            alternative_profiles=[],
            evidence_ids=[EVIDENCE_ID],
        ),
        intended_use="tiktok_organic",
        market="US",
        product_snapshot_hash=product_snapshot_hash,
        scene_inventory=inventory,
        dimensions=dimensions or [_dimension("hook_clarity", 88)],
        findings=findings or [],
        critical_evidence_unavailable=False,
    )


def _compatible_direction() -> CreativeDirectionContextV1:
    return CreativeDirectionContextV1(
        source_type="viral_kit",
        source_id=uuid4(),
        source_version=1,
        concept_id=uuid4(),
        product_snapshot_hash="same-product",
        objective="tiktok_shop_organic_test",
        market="US",
        buyer_context={"persona": "small-space organizer"},
        message_angle="Make a cramped counter usable.",
        hook_mechanism="Show the cluttered counter first.",
        narrative_sequence=["problem", "mechanism", "result"],
        demo_mechanism="Show installation and use.",
        proof_mechanism="Keep the existing visible result.",
        cta_strategy="Invite the viewer to inspect the product details.",
        keep=["visible result"],
        change=["clarify opening text"],
        avoid=["unverified urgency"],
        allowed_claims=[],
        prohibited_claims=["guaranteed result"],
        required_disclosures=[],
        expected_learning="Whether the problem-first framing is clearer.",
    )


class _FakeEvidence:
    def __init__(
        self,
        evidence_type: str,
        value_json: dict[str, Any],
        *,
        start_ms: int | None = None,
        end_ms: int | None = None,
        confidence: float = 0.9,
        source: str = "vision",
    ) -> None:
        self.id = uuid4()
        self.asset_version_id = ASSET_ID
        self.evidence_type = evidence_type
        self.value_json = value_json
        self.start_ms = start_ms
        self.end_ms = end_ms
        self.confidence = Decimal(str(confidence))
        self.source = source
        self.model_version = "fixture-v1"
        self.pipeline_version = "media-pipeline-v1"


def _complete_evidence() -> list[EvidenceItemModel]:
    items = [
        _FakeEvidence(
            "hook_signal",
            {
                "clarity": "clear",
                "spoken_text": "This counter organizer cleared my workspace.",
                "product_present": False,
            },
            start_ms=0,
            end_ms=800,
        ),
        _FakeEvidence(
            "product_appearance",
            {
                "visibility": "clear",
                "shot_type": "close_up",
                "usage_visible": True,
                "product_match_confidence": 0.9,
            },
            start_ms=1200,
            end_ms=2200,
        ),
        _FakeEvidence(
            "demo_summary",
            {"detected": True, "after_state_visible": True},
        ),
        _FakeEvidence(
            "demo_step",
            {
                "action": "Install and use the organizer",
                "product_visible": True,
                "mechanism_visible": True,
                "result_visible": True,
            },
            start_ms=1500,
            end_ms=2800,
        ),
        _FakeEvidence(
            "proof_signal",
            {
                "proof_type": "visual_result",
                "verifiability": "observable",
                "description": "The counter is visibly clear after use.",
            },
            start_ms=2600,
            end_ms=3400,
        ),
        _FakeEvidence(
            "creator_signal",
            {
                "delivery_style": "authentic_review",
                "authenticity_cues": ["firsthand use", "natural speech"],
            },
        ),
        _FakeEvidence(
            "offer_signal",
            {"offer_type": "value_statement", "text": "Makes this small counter usable."},
            start_ms=3500,
            end_ms=4300,
        ),
        _FakeEvidence(
            "cta_signal",
            {"cta_type": "learn_more", "text": "See the product details."},
            start_ms=7000,
            end_ms=7800,
        ),
        _FakeEvidence(
            "platform_signal",
            {
                "vertical": True,
                "native_signals": ["first_person"],
                "visual_safe_zone_risk": False,
            },
            start_ms=0,
            end_ms=10_000,
        ),
        _FakeEvidence(
            "on_screen_text",
            {"text": "counter organizer", "text_role": "caption"},
            start_ms=0,
            end_ms=1400,
            source="ocr",
        ),
        _FakeEvidence(
            "transcript_segment",
            {"text": "This counter organizer cleared my workspace."},
            start_ms=0,
            end_ms=1200,
            source="asr",
        ),
        _FakeEvidence(
            "claim_signal",
            {"text": "cleared my workspace", "risk": "low", "source": "spoken"},
            start_ms=400,
            end_ms=900,
            source="asr",
        ),
    ]
    return cast(list[EvidenceItemModel], items)
