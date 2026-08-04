from __future__ import annotations

from copy import deepcopy
from uuid import NAMESPACE_URL, uuid5

import pytest

from viraldy.evaluation.tiktok_scorer_contracts import (
    ScorerHumanLabelsV1,
    TikTokScorerEvaluationDatasetV1,
    TikTokScorerEvaluationSampleV1,
    TikTokScorerGoldenCaseV1,
)
from viraldy.evaluation.tiktok_scorer_golden import (
    REQUIRED_SCORER_GOLDEN_CATEGORIES,
    load_tiktok_scorer_golden_cases,
)
from viraldy.evaluation.tiktok_scorer_harness import evaluate_tiktok_scorer_dataset
from viraldy.evaluation.tiktok_scorer_reporting import render_tiktok_scorer_markdown


def test_versioned_golden_catalog_covers_every_required_scorer_scenario() -> None:
    catalog = load_tiktok_scorer_golden_cases()
    covered = {category for case in catalog.cases for category in case.categories}

    assert catalog.schema_version == "tiktok_scorer_golden_dataset_v1"
    assert covered == REQUIRED_SCORER_GOLDEN_CATEGORIES
    assert len(catalog.cases) == len({case.case_id for case in catalog.cases})
    assert all(case.synthetic_only for case in catalog.cases)
    assert all(not case.claims_real_world_accuracy for case in catalog.cases)


def test_golden_descriptors_have_bounded_evidence_and_executable_action_labels() -> None:
    catalog = load_tiktok_scorer_golden_cases()

    for case in catalog.cases:
        known_evidence = {item.evidence_id for item in case.evidence}
        assert known_evidence
        assert all(0 <= item.start_ms <= item.end_ms <= case.duration_ms for item in case.evidence)
        for action in case.expected_actions:
            assert set(action.evidence_ids) <= known_evidence
            if action.priority in {"P0", "P1"}:
                assert action.evidence_ids
                assert action.completion_criteria
            if action.fix_type in {"reshoot_scene", "add_missing_scene"}:
                assert action.capture_requirements
        assert all(not upgrade.affects_score for upgrade in case.expected_optional_upgrades)


def test_harness_measures_machine_metrics_and_marks_unlabeled_human_metrics_unmeasured() -> None:
    case = _case("wrong_product_sku")
    report = evaluate_tiktok_scorer_dataset(_dataset(case, _candidate(case)))
    metrics = report.aggregate

    assert metrics.schema_valid_rate.value == 1
    assert metrics.evidence_validity.value == 1
    assert metrics.timestamp_accuracy.value == 1
    assert metrics.out_of_range_timestamp_rate.value == 0
    assert metrics.dimension_agreement.status == "measured"
    assert metrics.blocker_precision.value == 1
    assert metrics.blocker_recall.value == 1
    assert metrics.false_hard_blocker_rate.value == 0
    assert metrics.edit_vs_reshoot_agreement.value == 1
    assert metrics.seller_action_agreement.value == 1
    assert metrics.fix_action_usefulness.status == "unmeasured"
    assert metrics.fix_action_usefulness.value is None
    assert metrics.seller_clarity.status == "unmeasured"
    assert report.qualification_passed


def test_explicit_human_labels_are_the_only_source_of_usefulness_and_clarity_scores() -> None:
    case = _case("wrong_product_sku")
    action_code = case.expected_actions[0].action_code
    sample = TikTokScorerEvaluationSampleV1(
        golden_case=case,
        candidate_score=_candidate(case),
        human_labels=ScorerHumanLabelsV1(
            fix_action_usefulness_scores={action_code: 4},
            seller_clarity_scores={action_code: 5},
        ),
    )

    metrics = evaluate_tiktok_scorer_dataset(
        TikTokScorerEvaluationDatasetV1(dataset_id="human-labels", samples=[sample])
    ).aggregate

    assert metrics.fix_action_usefulness.status == "measured"
    assert metrics.fix_action_usefulness.value == 4
    assert metrics.seller_clarity.status == "measured"
    assert metrics.seller_clarity.value == 5


def test_fabricated_evidence_and_out_of_duration_timestamp_fail_qualification() -> None:
    case = _case("generic_tiktok_video")
    candidate = deepcopy(_candidate(case))
    candidate["evidence_ids"].append("ffffffff-ffff-ffff-ffff-ffffffffffff")
    candidate["scene_inventory"]["scenes"][0]["end_ms"] = case.duration_ms + 1

    result = evaluate_tiktok_scorer_dataset(_dataset(case, candidate))
    metrics = result.cases[0].metrics
    issue_codes = {issue.code for issue in result.cases[0].qualification_issues}

    assert metrics.schema_valid_rate.value == 0
    assert metrics.evidence_validity.value is not None
    assert metrics.evidence_validity.value < 1
    assert metrics.timestamp_accuracy.value is not None
    assert metrics.timestamp_accuracy.value < 1
    assert metrics.out_of_range_timestamp_rate.value is not None
    assert metrics.out_of_range_timestamp_rate.value > 0
    assert {"fabricated_evidence", "timestamp_out_of_range"} <= issue_codes
    assert not result.qualification_passed


def test_p0_p1_fixes_and_reshoots_are_qualified_from_raw_output_invariants() -> None:
    case = _case("wrong_product_sku")
    candidate = deepcopy(_candidate(case))
    candidate["required_fixes"][0]["completion_criteria"] = []
    candidate["required_fixes"][0]["instructions"] = ["Make it better."]

    result = evaluate_tiktok_scorer_dataset(_dataset(case, candidate))
    issue_codes = {issue.code for issue in result.cases[0].qualification_issues}

    assert "p0_p1_completion_missing" in issue_codes
    assert "reshoot_capture_not_explained" in issue_codes


def test_story_led_case_rejects_a_false_universal_product_before_two_seconds_blocker() -> None:
    case = _case("story_led_pov_valid_later_reveal")
    candidate = deepcopy(_candidate(case))
    candidate["findings"].append(
        {
            "id": str(uuid5(NAMESPACE_URL, "false-product-before-2s")),
            "code": "product_before_2s",
            "rule_code": "universal.product_before_2s",
            "rule_class": "contextual_guideline",
            "source_dimension": "product_visibility",
            "severity": "hard",
            "priority": "P0",
            "applicability": "applicable",
            "evidence_status": "sufficient",
            "title": "Product must appear before 2 seconds",
            "reason": "Applied as a universal threshold.",
            "expected": {"product_visible_before_ms": 2000},
            "observed": {"product_visible_at_ms": 4200},
            "target_time_range_ms": [0, 4200],
            "evidence_ids": [str(case.evidence[0].evidence_id)],
            "uncertainty": [],
            "requires_seller_truth": False,
            "can_be_resolved_by_edit": True,
            "requires_physical_reshoot": False,
        }
    )

    result = evaluate_tiktok_scorer_dataset(_dataset(case, candidate))

    assert "false_universal_product_timing_blocker" in {
        issue.code for issue in result.cases[0].qualification_issues
    }
    assert result.aggregate.false_hard_blocker_rate.value == 1


def test_optional_upgrades_must_never_affect_the_core_score() -> None:
    case = _case("compatible_viral_kit_enrichment")
    candidate = deepcopy(_candidate(case))
    candidate["optional_upgrades"][0]["affects_score"] = True

    result = evaluate_tiktok_scorer_dataset(_dataset(case, candidate))

    assert "optional_upgrade_affects_score" in {
        issue.code for issue in result.cases[0].qualification_issues
    }
    assert result.cases[0].metrics.schema_valid_rate.value == 0


def test_revision_resolution_accuracy_uses_explicit_action_status_labels() -> None:
    case = _case("revision_resolving_blockers")
    comparison = _comparison_candidate(case)
    sample = TikTokScorerEvaluationSampleV1(
        golden_case=case,
        candidate_score=_candidate(case),
        candidate_comparison=comparison,
    )

    metrics = evaluate_tiktok_scorer_dataset(
        TikTokScorerEvaluationDatasetV1(dataset_id="revision", samples=[sample])
    ).aggregate

    assert metrics.revision_resolution_accuracy.status == "measured"
    assert metrics.revision_resolution_accuracy.value == 1


def test_latency_cost_generic_output_and_report_disclosures_are_explicit() -> None:
    case = _case("missing_cta")
    candidate = deepcopy(_candidate(case))
    candidate["required_fixes"][0]["title"] = "Add a stronger CTA."
    sample = TikTokScorerEvaluationSampleV1(
        golden_case=case,
        candidate_score=candidate,
        latency_ms=1250,
        cost_usd=0.042,
    )
    report = evaluate_tiktok_scorer_dataset(
        TikTokScorerEvaluationDatasetV1(dataset_id="runtime", samples=[sample])
    )
    markdown = render_tiktok_scorer_markdown(report)

    assert report.aggregate.latency.value == 1250
    assert report.aggregate.cost_per_score.value == pytest.approx(0.042)
    assert report.aggregate.generic_output_rate.value == 1
    assert report.aggregate.generic_output_rate.target_max == 0.05
    assert report.aggregate.generic_output_rate.target_met is False
    assert "UNMEASURED" in markdown
    assert "does not establish real-world accuracy" in markdown
    assert "explicit human labels" in markdown


def _case(category: str) -> TikTokScorerGoldenCaseV1:
    return next(
        case
        for case in load_tiktok_scorer_golden_cases().cases
        if category in case.categories
    )


def _dataset(
    case: TikTokScorerGoldenCaseV1,
    candidate: dict[str, object],
) -> TikTokScorerEvaluationDatasetV1:
    return TikTokScorerEvaluationDatasetV1(
        dataset_id=f"dataset-{case.case_id}",
        samples=[
            TikTokScorerEvaluationSampleV1(
                golden_case=case,
                candidate_score=candidate,
            )
        ],
    )


def _candidate(case: TikTokScorerGoldenCaseV1) -> dict[str, object]:
    evidence_ids = [str(item.evidence_id) for item in case.evidence]
    first_evidence_id = evidence_ids[0]
    asset_version_id = str(uuid5(NAMESPACE_URL, f"asset:{case.case_id}"))
    scenes = [
        {
            "scene_id": str(uuid5(NAMESPACE_URL, f"scene:{case.case_id}:{index}")),
            "start_ms": item.start_ms,
            "end_ms": item.end_ms,
            "summary": item.summary,
            "shot_type": None,
            "product_visible": None,
            "product_match_confidence": None,
            "product_visibility_quality": None,
            "spoken_text": None,
            "overlay_texts": [],
            "demo_step": None,
            "proof_role": None,
            "creator_present": None,
            "visual_quality": "usable",
            "continuity_group_id": None,
            "reusable_for_edit": True,
            "evidence_ids": [str(item.evidence_id)],
        }
        for index, item in enumerate(case.evidence)
    ]
    dimensions = []
    for code, band in case.expected_dimension_bands.items():
        score = {"low": 25, "medium": 60, "high": 85, "not_evaluated": None}[band]
        dimensions.append(
            {
                "code": code,
                "label": code.replace("_", " ").title(),
                "score": score,
                "applicability": "unknown" if score is None else "applicable",
                "evidence_status": "partial" if score is None else "sufficient",
                "confidence": "medium",
                "reason": "Synthetic observation used only for harness qualification.",
                "positive_signals": [],
                "missing_signals": [],
                "uncertainty": ["Synthetic fixture"] if score is None else [],
                "evidence_ids": [] if score is None else [first_evidence_id],
                "contributing_rule_codes": [],
            }
        )

    findings = []
    fixes = []
    for action in case.expected_actions:
        finding_id = str(uuid5(NAMESPACE_URL, f"finding:{case.case_id}:{action.action_code}"))
        hard = action.action_code in case.expected_hard_blocker_codes
        findings.append(
            {
                "id": finding_id,
                "code": action.action_code,
                "rule_code": f"golden.{action.action_code}",
                "rule_class": "product_governance_rule" if hard else "contextual_guideline",
                "source_dimension": next(iter(case.expected_dimension_bands), "hook_clarity"),
                "severity": "hard" if hard else "high",
                "priority": action.priority,
                "applicability": "applicable",
                "evidence_status": "sufficient",
                "title": action.action_code.replace("_", " ").title(),
                "reason": "Synthetic finding for deterministic harness qualification.",
                "expected": {},
                "observed": {},
                "target_time_range_ms": [0, min(1000, case.duration_ms)],
                "evidence_ids": [str(item) for item in action.evidence_ids],
                "uncertainty": [],
                "requires_seller_truth": action.fix_type == "confirm_seller_input",
                "can_be_resolved_by_edit": action.fix_type
                not in {"reshoot_scene", "add_missing_scene"},
                "requires_physical_reshoot": action.fix_type
                in {"reshoot_scene", "add_missing_scene"},
            }
        )
        instruction = "Capture " + ", ".join(action.capture_requirements) + "."
        if not action.capture_requirements:
            instruction = f"Apply the labeled {action.fix_type} correction."
        fixes.append(
            {
                "id": str(uuid5(NAMESPACE_URL, f"fix:{case.case_id}:{action.action_code}")),
                "code": action.action_code,
                "source_finding_id": finding_id,
                "source_finding_code": action.action_code,
                "recommendation_class": "required_fix",
                "basis": "product_governance" if hard else "video_diagnosis",
                "priority": action.priority,
                "severity": "hard" if hard else "high",
                "source_dimension": next(iter(case.expected_dimension_bands), "hook_clarity"),
                "owner_role": action.owner_role,
                "fix_type": action.fix_type,
                "title": action.action_code.replace("_", " ").title(),
                "why_it_matters": "The labeled correction is required for this synthetic case.",
                "expected": {},
                "observed": {},
                "evidence_ids": [str(item) for item in action.evidence_ids],
                "target_time_range_ms": [0, min(1000, case.duration_ms)],
                "video_operations": [],
                "instructions": [instruction],
                "strengths_to_preserve": [],
                "required_inputs": [],
                "estimated_effort": "high" if action.capture_requirements else "low",
                "reshoot_required": action.fix_type in {"reshoot_scene", "add_missing_scene"},
                "completion_criteria": action.completion_criteria,
                "verification_method": "Compare the revision against the labeled evidence.",
            }
        )

    upgrades = [
        {
            "id": str(uuid5(NAMESPACE_URL, f"upgrade:{case.case_id}:{upgrade.code}")),
            "source_type": "viral_kit",
            "source_id": str(uuid5(NAMESPACE_URL, f"direction:{case.case_id}")),
            "source_version": 1,
            "concept_id": str(uuid5(NAMESPACE_URL, f"concept:{case.case_id}")),
            "affects_score": False,
            "recommendation_class": "optional_upgrade",
            "title": upgrade.code.replace("_", " ").title(),
            "why_it_fits": "Compatible synthetic direction context.",
            "keep_from_current_video": [],
            "change_in_current_video": [],
            "additional_footage_needed": [],
            "suggested_hook_mechanism": None,
            "suggested_narrative_sequence": [],
            "suggested_demo_mechanism": None,
            "suggested_proof_mechanism": None,
            "suggested_cta_strategy": None,
            "claim_guardrails": [],
            "evidence_ids": [first_evidence_id],
            "expected_learning": None,
        }
        for upgrade in case.expected_optional_upgrades
    ]
    score = {"low": 25, "medium": 60, "high": 85, "not_scored": None}[
        case.expected_score_band
    ]
    return {
        "schema_version": "tiktok_diagnostic_v2",
        "asset_version_id": asset_version_id,
        "profile_selection": {
            "profile_code": case.profile_code,
            "selection_mode": "user_selected",
            "confidence": 1,
            "alternative_profiles": [],
            "evidence_ids": [first_evidence_id],
        },
        "intended_use": "tiktok_organic",
        "market": "US",
        "objective": None,
        "product_snapshot_hash": None,
        "policy_pack_versions": {"synthetic": "v1"},
        "scene_inventory": {
            "asset_version_id": asset_version_id,
            "duration_ms": case.duration_ms,
            "audio_available": case.audio_available,
            "scenes": scenes,
            "asr_coverage": 0 if case.audio_available is False else 1,
            "ocr_coverage": 1,
            "product_appearance_ranges": [],
            "cta_ranges": [],
            "disclosure_ranges": [],
            "safe_zone_observations": [],
            "continuity_group_ids": [],
            "evidence_ids": evidence_ids,
            "coverage_status": "sufficient",
            "overall_confidence": "medium",
            "extractor_versions": {"synthetic": "v1"},
        },
        "overall_score": score,
        "overall_confidence": "medium",
        "creative_structure_decision": case.expected_decisions[0],
        "paid_use_rights_status": "not_applicable",
        "final_paid_readiness": "not_applicable",
        "dimensions": dimensions,
        "findings": findings,
        "required_fixes": fixes,
        "strengths": [],
        "auxiliary_signals": {
            "search_discovery_readiness": {
                "status": "not_evaluated",
                "reason": "No target query was provided.",
                "evidence_ids": [],
                "market": None,
                "observed_at": None,
                "source": None,
                "expires_at": None,
            },
            "community_conversation_potential": {
                "status": "not_evaluated",
                "reason": "No community context was provided.",
                "evidence_ids": [],
                "market": None,
                "observed_at": None,
                "source": None,
                "expires_at": None,
            },
            "trend_relevance": {
                "status": "not_evaluated",
                "reason": "No trend context was provided.",
                "evidence_ids": [],
                "market": None,
                "observed_at": None,
                "source": None,
                "expires_at": None,
            },
        },
        "optional_upgrades": upgrades,
        "evidence_ids": evidence_ids,
        "uncertainty": ["Synthetic fixture; not a real-world accuracy claim."],
    }


def _comparison_candidate(case: TikTokScorerGoldenCaseV1) -> dict[str, object]:
    label = case.expected_revision_labels[0]
    evidence_ids = [str(item.evidence_id) for item in case.evidence]
    return {
        "schema_version": "tiktok_score_comparison_v1",
        "before_asset_version_id": str(uuid5(NAMESPACE_URL, f"before:{case.case_id}")),
        "after_asset_version_id": str(uuid5(NAMESPACE_URL, f"after:{case.case_id}")),
        "before_score": 45,
        "after_score": 75,
        "resolved_blockers": [],
        "unresolved_blockers": [],
        "new_regressions": [],
        "dimension_changes": [],
        "evidence_before_after": [],
        "strengths_preserved": [],
        "actions_verified": [
            {
                "action_id": str(uuid5(NAMESPACE_URL, f"action:{label.action_code}")),
                "action_code": label.action_code,
                "source_finding_code": label.action_code,
                "status": label.expected_status,
                "before": {},
                "after": {},
                "evidence_before_ids": evidence_ids,
                "evidence_after_ids": evidence_ids,
                "reason": "Synthetic revision label.",
            }
        ],
        "final_next_action": "no_required_changes",
        "like_for_like": True,
        "comparison_warning": None,
    }
