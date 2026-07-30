from __future__ import annotations

import importlib.util
import json
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import cast
from uuid import UUID

import pytest

from viraldy.evaluation.contracts import (
    AdaptationReviewerLabelV1,
    BooleanJudgmentV1,
    CampaignPackCompileInputV1,
    CategoricalAgreementV1,
    EvaluationDatasetV1,
    GeneralizationJudgmentV1,
    PatternKitMetricInputV1,
    PreflightCompileInputV1,
    ViralKitMetricInputV1,
)
from viraldy.evaluation.harness import evaluate_dataset
from viraldy.evaluation.reporting import render_json_report, render_markdown_report
from viraldy.modules.campaign_packs.contracts import CampaignPackBriefV1
from viraldy.modules.campaign_packs.requirements import (
    CompiledRequirementsSnapshotV2,
    CompiledRequirementV2,
)
from viraldy.modules.products.contracts import build_minimal_product_context

PATTERN_VERSION_ID = UUID("00000000-0000-0000-0000-000000000101")
RESOLVED_EVIDENCE_ID = UUID("00000000-0000-0000-0000-000000000201")
MISSING_EVIDENCE_ID = UUID("00000000-0000-0000-0000-000000000202")


@pytest.mark.parametrize("mode", ["fixture", "mock", "live"])
def test_dataset_accepts_all_evaluation_modes(mode: str) -> None:
    dataset = EvaluationDatasetV1(
        dataset_id=f"{mode}-dataset",
        mode=mode,
        pattern_kit_cases=[],
        viral_kit_cases=[],
    )

    assert dataset.mode == mode


def test_pattern_kit_metrics_use_structured_rubrics() -> None:
    case = PatternKitMetricInputV1(
        case_id="pattern-case",
        candidate={
            "sequence": [{"beat_type": "hook"}, {"beat_type": "demo"}],
            "opening": {
                "evidence_refs": [
                    {"evidence_id": str(RESOLVED_EVIDENCE_ID)},
                    {"evidence_id": str(MISSING_EVIDENCE_ID)},
                ]
            },
            "adaptation_instructions": [
                {"element_path": "opening.hook", "instruction_type": "keep"},
                {"element_path": "demo.mechanism", "instruction_type": "change"},
            ],
            "summary": "A kitchen-only pattern leaks into a beauty source.",
        },
        resolvable_evidence_ids=[RESOLVED_EVIDENCE_ID],
        source_field_checks=[
            CategoricalAgreementV1(key="hook_type", expected="problem", observed="problem"),
            CategoricalAgreementV1(key="demo_type", expected="reveal", observed="tutorial"),
        ],
        expected_sequence=["hook", "proof"],
        applicability_checks=[
            CategoricalAgreementV1(key="market", expected="US", observed="US"),
            CategoricalAgreementV1(
                key="category", expected="beauty_accessory", observed="home_organization"
            ),
        ],
        adaptation_reviewer_labels=[
            AdaptationReviewerLabelV1(element_path="opening.hook", decision="keep"),
            AdaptationReviewerLabelV1(element_path="demo.mechanism", decision="avoid"),
        ],
        forbidden_category_terms=["kitchen", "pet"],
        generalization_checks=[
            GeneralizationJudgmentV1(statement_id="g1", supported=True),
            GeneralizationJudgmentV1(statement_id="g2", supported=False),
        ],
    )

    metrics = evaluate_dataset(_dataset(pattern_cases=[case])).pattern_kit_cases[0].metrics

    assert metrics.schema_validity.value == 0
    assert metrics.evidence_resolution.value == 0.5
    assert metrics.source_field_agreement.value == 0.5
    assert metrics.sequence_agreement.value == 0.5
    assert metrics.applicability_agreement.value == 0.5
    assert metrics.keep_change_avoid_agreement.value == 0.5
    assert metrics.cross_category_leakage.value == 1
    assert metrics.unsupported_generalization.value == 1


def test_viral_kit_metrics_cover_grounding_preservation_and_compilation() -> None:
    valid_brief = _campaign_pack_brief()
    valid_snapshot = CompiledRequirementsSnapshotV2(
        requirements=[
            CompiledRequirementV2(
                id="product_visible",
                requirement_type="product",
                source_path="must_show[0]",
                description="Show the product.",
                severity="hard",
                matcher_type="product_visibility",
                expected_semantics="presence",
            )
        ]
    )
    case = ViralKitMetricInputV1(
        case_id="viral-case",
        candidate={
            "concepts": [
                _concept("busy buyer", "creator", claims=True, disclosures=True, traced=True),
                _concept(
                    "busy buyer", "busy buyer", claims=True, disclosures=False, traced=False
                ),
                _concept("busy buyer", "expert", claims=False, disclosures=True, traced=True),
            ],
            "provenance": {"pattern_kit_version_ids": [str(PATTERN_VERSION_ID)]},
        },
        product_grounding_checks=[
            BooleanJudgmentV1(key="product_name", passed=True),
            BooleanJudgmentV1(key="demo_mechanism", passed=False),
        ],
        constraint_preservation_checks=[
            BooleanJudgmentV1(key="max_duration", passed=True),
            BooleanJudgmentV1(key="product_tag", passed=True),
        ],
        diversity_checks=[
            BooleanJudgmentV1(key="concepts_1_2", passed=True),
            BooleanJudgmentV1(key="concepts_1_3", passed=False),
        ],
        expected_prohibited_claims=["cure acne"],
        expected_required_disclosures=["#ad"],
        expected_pattern_kit_version_ids=[PATTERN_VERSION_ID],
        campaign_pack_briefs=[
            CampaignPackCompileInputV1(key="valid", brief=valid_brief.model_dump(mode="json")),
            CampaignPackCompileInputV1(key="invalid", brief={"schema_version": "invalid"}),
        ],
        preflight_snapshots=[
            PreflightCompileInputV1(
                key="valid", snapshot=valid_snapshot.model_dump(mode="json")
            ),
            PreflightCompileInputV1(
                key="invalid",
                snapshot={"schema_version": "compiled_requirements_v2", "requirements": "bad"},
            ),
        ],
        human_usefulness_scores=[5, 3],
    )

    metrics = evaluate_dataset(_dataset(viral_cases=[case])).viral_kit_cases[0].metrics

    assert metrics.schema_validity.value == 0
    assert metrics.product_grounding.value == 0.5
    assert metrics.constraint_preservation.value == 1
    assert metrics.diversity_pass_rate.value == 0.5
    assert metrics.buyer_creator_separation.value == pytest.approx(2 / 3)
    assert metrics.claim_disclosure_preservation.value == pytest.approx(4 / 6)
    assert metrics.pattern_kit_traceability.value == 0.75
    assert metrics.campaign_pack_compile.value == 0.5
    assert metrics.preflight_compile.value == 0.5
    assert metrics.human_usefulness.value == 4


def test_reports_are_deterministic_and_cli_writes_both_formats(
    tmp_path: Path,
) -> None:
    dataset = _dataset()
    report = evaluate_dataset(dataset)

    assert render_json_report(report) == render_json_report(report)
    assert render_markdown_report(report) == render_markdown_report(report)

    dataset_path = tmp_path / "dataset.json"
    output_dir = tmp_path / "reports"
    dataset_path.write_text(
        json.dumps(dataset.model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )

    script = Path(__file__).parents[2] / "scripts" / "run_evaluation.py"
    spec = importlib.util.spec_from_file_location("run_evaluation", script)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    main = cast(Callable[[Sequence[str] | None], int], module.main)

    assert main([str(dataset_path), "--output-dir", str(output_dir)]) == 0
    first_json = (output_dir / "evaluation-report.json").read_bytes()
    first_markdown = (output_dir / "evaluation-report.md").read_bytes()
    assert main([str(dataset_path), "--output-dir", str(output_dir)]) == 0

    assert first_json == (output_dir / "evaluation-report.json").read_bytes()
    assert first_markdown == (output_dir / "evaluation-report.md").read_bytes()
    assert json.loads(first_json)["dataset_id"] == "evaluation-dataset"
    assert b"# Viraldy Evaluation Report" in first_markdown


def _dataset(
    *,
    pattern_cases: list[PatternKitMetricInputV1] | None = None,
    viral_cases: list[ViralKitMetricInputV1] | None = None,
) -> EvaluationDatasetV1:
    return EvaluationDatasetV1(
        dataset_id="evaluation-dataset",
        mode="fixture",
        pattern_kit_cases=pattern_cases or [],
        viral_kit_cases=viral_cases or [],
    )


def _concept(
    buyer: str,
    creator: str,
    *,
    claims: bool,
    disclosures: bool,
    traced: bool,
) -> dict[str, object]:
    return {
        "buyer_persona_label": buyer,
        "creator_persona": creator,
        "claims_to_avoid": ["cure acne"] if claims else [],
        "required_disclosures": ["#ad"] if disclosures else [],
        "source_pattern_kit_version_ids": [str(PATTERN_VERSION_ID)] if traced else [],
    }


def _campaign_pack_brief() -> CampaignPackBriefV1:
    product = build_minimal_product_context(
        name="Counter Shelf",
        description="Organizes a counter.",
        market="US",
    )
    return CampaignPackBriefV1(
        product_snapshot=product,
        objective={
            "objective_type": "affiliate_test",
            "primary_action": "product_click",
            "channel": "tiktok_shop",
        },
        audience={"persona_label": "busy buyer"},
        angle={
            "name": "Counter reset",
            "promise": "Organize visible clutter.",
            "mechanism": "Stacked storage.",
            "emotional_driver": "relief",
        },
        creator_direction={"persona": "organizer", "delivery_style": "demonstration"},
        hooks=[],
        script_beats=[],
        storyboard=[],
        must_show=[],
        cta={"cta_type": "product_click", "product_tag_required": True},
        claim_guardrails={},
        rights_note={"note": "Seller-owned footage only."},
        source_concept_id="concept-1",
    )
