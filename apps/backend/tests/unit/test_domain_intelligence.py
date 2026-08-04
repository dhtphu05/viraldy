from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from typing import cast

import pytest

from viraldy.modules.domain_intelligence.public import (
    ACTIVE_MVP_RULE_CODES,
    DomainRule,
    EvaluationCandidate,
    NormalizedEvidence,
    NormalizedEvidenceBundle,
    UGCExecutionBriefRecommendationPatchV1,
    UGCExecutionBriefSynthesisV1,
    UGCReviewContext,
    adapt_media_evidence,
    apply_execution_brief_synthesis,
    evaluate_review,
    select_applicable_rules,
)
from viraldy.modules.media_analysis.public import EvidenceItemModel


def _rule(code: str, domain: str = "cross_domain") -> DomainRule:
    return DomainRule(
        code=code,
        domain=domain,
        title=code,
        rule_type="official_hard_rule",
        severity="high",
        enabled_for_mvp=True,
        applicability=[],
        required_conditions=[],
        implementation={},
        source_ids=[],
        raw_payload={},
    )


def _evidence(
    evidence_id: str,
    kind: str,
    observed: str,
    *,
    confidence: str = "high",
    start_ms: int | None = None,
    value: dict[str, object] | None = None,
) -> NormalizedEvidence:
    return NormalizedEvidence(
        id=evidence_id,
        kind=kind,
        source="video",
        observed=observed,
        start_ms=start_ms,
        end_ms=start_ms,
        confidence=confidence,
        value=value or {},
    )


def _evaluate(
    context: UGCReviewContext,
    evidence: list[NormalizedEvidence],
):
    rules = [_rule(code) for code in ACTIVE_MVP_RULE_CODES]
    return evaluate_review(
        review_id="review-1",
        context=context,
        evidence=NormalizedEvidenceBundle(
            items=evidence,
            coverage={"visual_observations": bool(evidence)},
        ),
        rules=rules,
        pack_version="test-v1",
        created_at=datetime(2026, 7, 31, tzinfo=UTC),
    )


def test_contextual_timing_is_an_improvement_not_a_platform_violation() -> None:
    result = _evaluate(
        UGCReviewContext(),
        [
            _evidence(
                "appearance",
                "product_appearance",
                "Product first appears at 6.2 seconds.",
                start_ms=6200,
                value={"first_appearance_ms": 6200},
            )
        ],
    )

    assert result.fix_first == []
    assert any(item.mistake_code == "M-PROD-002" for item in result.improvements)
    assert "platform violation" not in result.model_dump_json().lower()


def test_explicit_brief_timing_miss_is_fix_first() -> None:
    result = _evaluate(
        UGCReviewContext(creator_brief="Show the exact product by 2.5 seconds."),
        [
            _evidence(
                "appearance",
                "product_appearance",
                "Product first appears at 6.2 seconds.",
                start_ms=6200,
                value={"first_appearance_ms": 6200},
            )
        ],
    )

    recommendation = next(item for item in result.fix_first if item.rule_code == "PERF-TIME-001")
    assert recommendation.evidence[0].observed == "Product first appears at 6.2 seconds."
    assert "2.5" in recommendation.reason


def test_low_confidence_product_identity_is_confirmation_not_mismatch() -> None:
    result = _evaluate(
        UGCReviewContext(exact_variant_or_sku="GREEN-01"),
        [
            _evidence(
                "identity",
                "product_identity",
                "The visible model may be blue.",
                confidence="low",
                value={"observed_identity": "BLUE-02"},
            )
        ],
    )

    assert not any(item.mistake_code == "M-PROD-001" for item in result.fix_first)
    assert any(item.unknown_state == "insufficient_evidence" for item in result.confirmations)


def test_clear_product_mismatch_recommends_reshoot_without_global_failure() -> None:
    result = _evaluate(
        UGCReviewContext(exact_variant_or_sku="GREEN-01"),
        [
            _evidence(
                "identity",
                "product_identity",
                "Observed BLUE-02 instead of GREEN-01.",
                value={"observed_identity": "BLUE-02"},
            )
        ],
    )

    recommendation = next(item for item in result.fix_first if item.mistake_code == "M-PROD-001")
    assert recommendation.fix_type == "reshoot_scene"
    assert recommendation.strengths_to_preserve
    assert result.status == "completed"
    assert "blocked" not in result.model_dump_json().lower()


def test_missing_rights_for_paid_use_is_confirmation_not_creative_failure() -> None:
    result = _evaluate(UGCReviewContext(intended_use="spark_candidate"), [])

    assert any(item.unknown_state == "rights_incomplete" for item in result.confirmations)
    assert result.status == "completed"


def test_missing_publish_metadata_is_a_typed_publish_check() -> None:
    result = _evaluate(UGCReviewContext(intended_use="affiliate"), [])

    recommendation = next(
        item for item in result.confirmations if item.unknown_state == "publish_check_required"
    )
    assert recommendation.task_kind == "publish_ops_required"
    assert recommendation.exact_action
    assert recommendation.acceptance_criteria


def test_mockup_only_pod_proof_requests_better_media() -> None:
    result = _evaluate(
        UGCReviewContext(
            commerce_domain="pod_personalization",
            approved_personalization="Milo",
            physical_sample_available=False,
        ),
        [
            _evidence(
                "personalization",
                "personalization",
                "Only a digital mockup is visible.",
                value={"observed_personalization": "Milo", "mockup_only": True},
            )
        ],
    )

    recommendation = next(item for item in result.confirmations if item.mistake_code == "M-POD-002")
    assert recommendation.fix_type == "request_better_media"
    assert recommendation.unknown_state == "insufficient_evidence"


def test_unsupported_shipping_language_requests_removal_or_confirmation() -> None:
    result = _evaluate(
        UGCReviewContext(commerce_domain="dropshipping"),
        [
            _evidence(
                "shipping",
                "shipping_claim",
                'Creator says "arrives in two days."',
                value={"shipping_text": "arrives in two days"},
            )
        ],
    )

    recommendation = next(item for item in result.fix_first if item.mistake_code == "M-SUP-001")
    assert recommendation.fix_type == "replace_copy"
    assert any(
        "confirm" in step.lower() or "remove" in step.lower()
        for step in recommendation.instructions
    )


def test_views_never_create_a_winning_or_performance_promise() -> None:
    result = _evaluate(
        UGCReviewContext(),
        [
            _evidence(
                "views",
                "performance_metrics",
                "Reference received one million views.",
                value={"views": 1_000_000},
            )
        ],
    )

    serialized = result.model_dump_json().lower()
    assert "winning" not in serialized
    assert "guaranteed performance" not in serialized
    assert "predicted gmv" not in serialized
    assert "roas" not in serialized


def test_insufficient_evidence_remains_useful_and_never_becomes_failure() -> None:
    result = _evaluate(UGCReviewContext(), [])

    assert result.status == "completed"
    assert result.strengths_to_keep
    assert "fail" not in result.headline.lower()
    assert "fail" not in result.summary.lower()


def test_selector_uses_context_and_observed_signals() -> None:
    rules = [
        _rule("TT-OFFER-001", "tiktok_shop_us"),
        _rule("POD-PERS-001", "pod_personalization"),
        _rule("DROP-SHIP-001", "dropshipping"),
        _rule("UGC-RIGHTS-001", "ugc_creator_operations"),
        _rule("SYS-UNKNOWN-001", "system_governance"),
    ]
    context = UGCReviewContext(
        commerce_domain="dropshipping",
        intended_use="paid_candidate",
    )
    evidence = NormalizedEvidenceBundle(
        items=[
            _evidence(
                "shipping",
                "shipping_claim",
                "Two-day shipping is claimed.",
            )
        ]
    )

    selected = select_applicable_rules(rules, context, evidence)

    assert [rule.code for rule in selected] == [
        "DROP-SHIP-001",
        "SYS-UNKNOWN-001",
        "UGC-RIGHTS-001",
    ]


def test_semantic_evaluator_cannot_invent_rule_or_evidence_references() -> None:
    class UnsafeSemanticEvaluator:
        provider_name = "unsafe-test-provider"

        def evaluate(self, **_kwargs) -> list[EvaluationCandidate]:
            return [
                EvaluationCandidate(
                    rule_code="INVENTED-RULE",
                    group="fix_first",
                    title="Invented finding",
                    reason="Invented seller fact.",
                    why_it_matters="It does not.",
                    owner="seller",
                    instructions=["Do an invented task."],
                    strengths_to_preserve=["Keep the draft."],
                    completion_criteria=["Invented completion."],
                    evidence_ids=["invented-evidence"],
                    confidence="high",
                )
            ]

    result = evaluate_review(
        review_id="bounded-review",
        context=UGCReviewContext(),
        evidence=NormalizedEvidenceBundle(),
        rules=[_rule("SYS-UNKNOWN-001")],
        pack_version="test-v1",
        semantic_evaluator=UnsafeSemanticEvaluator(),
        created_at=datetime(2026, 7, 31, tzinfo=UTC),
    )

    assert "Invented finding" not in result.model_dump_json()
    assert result.analysis_provenance["semantic_provider"] == "unsafe-test-provider"


def test_semantic_provider_failure_uses_deterministic_fallback() -> None:
    class FailingSemanticEvaluator:
        provider_name = "failing-test-provider"

        def evaluate(self, **_kwargs) -> list[EvaluationCandidate]:
            raise RuntimeError("provider unavailable")

    result = evaluate_review(
        review_id="fallback-review",
        context=UGCReviewContext(),
        evidence=NormalizedEvidenceBundle(),
        rules=[_rule("SYS-UNKNOWN-001")],
        pack_version="test-v1",
        semantic_evaluator=FailingSemanticEvaluator(),
        created_at=datetime(2026, 7, 31, tzinfo=UTC),
    )

    assert result.status == "completed"
    assert result.analysis_provenance["semantic_provider"] == "deterministic_fallback"


@pytest.mark.parametrize(
    ("context", "evidence", "expected_mistake_code"),
    [
        (
            UGCReviewContext(),
            _evidence(
                "demo",
                "demo_summary",
                "The mechanism is not understandable.",
                value={"detected": True, "mechanism_clarity": "unclear"},
            ),
            "M-DEMO-001",
        ),
        (
            UGCReviewContext(),
            _evidence(
                "proof",
                "proof_signal",
                "The claimed result is not observable.",
                value={"proof_type": "visual_result", "verifiability": "not_observable"},
            ),
            "M-PROOF-001",
        ),
        (
            UGCReviewContext(),
            _evidence(
                "urgency",
                "offer",
                "Limited time only.",
                value={"offer_type": "limited_time", "urgency_present": True},
            ),
            "M-OFFER-002",
        ),
        (
            UGCReviewContext(),
            _evidence(
                "creator",
                "creator_signal",
                "The delivery reads as a forced sales pitch.",
                value={
                    "delivery_style": "sales_pitch",
                    "sales_language_intensity": "high",
                    "authenticity_cues": [],
                },
            ),
            "M-CREATOR-001",
        ),
        (
            UGCReviewContext(commerce_domain="dropshipping"),
            _evidence(
                "compatibility",
                "claim",
                "Fits every phone model.",
                value={"category": "comparison", "text": "Fits every phone model", "risk": "high"},
            ),
            "M-DROP-001",
        ),
        (
            UGCReviewContext(creator_brief="Keep the revision inside the approved scope."),
            _evidence(
                "brief-miss",
                "expected_vs_observed",
                "Expected the approved revision scope, observed a new unsupported scene.",
                value={
                    "rule_code": "UGC-REV-002",
                    "status": "fail",
                    "expected": "approved revision scope",
                    "observed": "new unsupported scene",
                    "editability": "reshoot",
                },
            ),
            "M-REV-001",
        ),
    ],
)
def test_normalized_semantic_evidence_maps_remaining_required_mistake_codes(
    context: UGCReviewContext,
    evidence: NormalizedEvidence,
    expected_mistake_code: str,
) -> None:
    result = _evaluate(
        context,
        [evidence],
    )

    mapped_codes = [
        item.mistake_code
        for item in [*result.fix_first, *result.improvements, *result.confirmations]
    ]
    assert expected_mistake_code in mapped_codes


def test_review_provenance_preserves_model_run_identity_and_provider_versions() -> None:
    result = evaluate_review(
        review_id="provenance-review",
        context=UGCReviewContext(),
        evidence=NormalizedEvidenceBundle(
            metadata={
                "model_provider_versions": [
                    {"provider": "openai", "model_version": "gpt-example"}
                ]
            }
        ),
        rules=[_rule("SYS-PROV-001")],
        pack_version="test-v1",
        analysis_provenance={"primary_model_run_id": "model-run-1", "analysis_mode": "live"},
        created_at=datetime(2026, 7, 31, tzinfo=UTC),
    )

    assert result.analysis_provenance["primary_model_run_id"] == "model-run-1"
    assert result.analysis_provenance["analysis_mode"] == "live"
    assert result.analysis_provenance["model_provider_versions"] == [
        {"provider": "openai", "model_version": "gpt-example"}
    ]


def test_evidence_adapter_preserves_provider_and_model_version_metadata() -> None:
    evidence = cast(
        EvidenceItemModel,
        SimpleNamespace(
            id="evidence-1",
            evidence_type="demo_summary",
            value_json={"detected": True, "mechanism_clarity": "clear"},
            start_ms=None,
            end_ms=None,
            confidence=Decimal("0.95"),
            provider="openai",
            model_version="gpt-example",
            pipeline_version="media_pipeline_v1",
        ),
    )

    bundle = adapt_media_evidence([evidence])

    assert bundle.metadata["model_provider_versions"] == [
        {"provider": "openai", "model_version": "gpt-example"}
    ]
    assert bundle.pipeline_version == "media_pipeline_v1"


def test_spoken_korean_disclosure_requires_visible_disclosure_without_claiming_absence() -> None:
    transcript = cast(
        EvidenceItemModel,
        SimpleNamespace(
            id="transcript-disclosure",
            evidence_type="transcript_segment",
            value_json={"text": "이 영상은 브랜드 협찬으로 제작되었습니다."},
            start_ms=0,
            end_ms=1800,
            confidence=Decimal("0.95"),
            provider="openai",
            model_version="gpt-example",
            pipeline_version="media_pipeline_v1",
        ),
    )

    bundle = adapt_media_evidence([transcript])
    result = _evaluate(UGCReviewContext(material_connection="yes"), bundle.items)

    assert bundle.coverage["transcript"] is True
    assert bundle.items[0].kind == "disclosure"
    assert bundle.items[0].source == "transcript"
    assert bundle.items[0].value["modality"] == "spoken"
    assert bundle.items[0].value["language"] == "ko"
    assert bundle.items[0].value["translation"] == "This video was made with brand sponsorship."
    recommendation = next(item for item in result.fix_first if item.mistake_code == "M-DISC-001")
    assert recommendation.title == "Add visible disclosure for the target market"
    assert "no clear disclosure" not in recommendation.reason.lower()
    assert recommendation.evidence[0].id == "transcript-disclosure"
    assert recommendation.task_kind == "video_edit_required"
    assert recommendation.exact_action is not None
    assert recommendation.exact_copy == ["seller-approved disclosure copy required"]
    assert recommendation.acceptance_criteria


def test_execution_brief_applies_only_allowed_patch_fields() -> None:
    original = _evaluate(
        UGCReviewContext(material_connection="yes"),
        [_evidence("missing-disclosure", "product_appearance", "Product is visible.")],
    )
    recommendation = original.fix_first[0]
    synthesis = UGCExecutionBriefSynthesisV1(
        recommendation_patches=[
            UGCExecutionBriefRecommendationPatchV1(
                recommendation_id=recommendation.id,
                title="Add a readable opening disclosure",
                exact_action="Place the seller-approved caption over the opening product shot.",
                exact_copy=["seller-approved disclosure copy required"],
                acceptance_criteria=["The caption is readable on mobile before product claims."],
            )
        ],
        creator_revision_message=(
            "Keep the product footage and add the approved opening disclosure."
        ),
    )

    enriched = apply_execution_brief_synthesis(original, synthesis)
    patched = enriched.fix_first[0]

    assert patched.id == recommendation.id
    assert patched.rule_code == recommendation.rule_code
    assert patched.owner == recommendation.owner
    assert patched.task_kind == recommendation.task_kind
    assert patched.title == "Add a readable opening disclosure"
    assert patched.exact_copy == ["seller-approved disclosure copy required"]
    assert enriched.creator_revision_message.startswith("Keep the product footage")


def test_execution_brief_rejects_unknown_or_missing_recommendation_ids() -> None:
    original = _evaluate(
        UGCReviewContext(material_connection="yes"),
        [_evidence("missing-disclosure", "product_appearance", "Product is visible.")],
    )
    synthesis = UGCExecutionBriefSynthesisV1(
        recommendation_patches=[
            UGCExecutionBriefRecommendationPatchV1(
                recommendation_id="unknown-recommendation",
                exact_action="Unsupported replacement.",
            )
        ]
    )

    with pytest.raises(ValueError, match="recommendation IDs"):
        apply_execution_brief_synthesis(original, synthesis)


def test_execution_brief_rejects_prohibited_performance_promises() -> None:
    original = _evaluate(
        UGCReviewContext(material_connection="yes"),
        [_evidence("missing-disclosure", "product_appearance", "Product is visible.")],
    )
    recommendation = original.fix_first[0]
    synthesis = UGCExecutionBriefSynthesisV1(
        recommendation_patches=[
            UGCExecutionBriefRecommendationPatchV1(
                recommendation_id=recommendation.id,
                exact_action="Add this because it is guaranteed performance.",
            )
        ]
    )

    with pytest.raises(ValueError, match="prohibited performance language"):
        apply_execution_brief_synthesis(original, synthesis)
