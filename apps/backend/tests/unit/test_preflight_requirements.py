from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID, uuid4

from viraldy.modules.campaign_packs.contracts import (
    CampaignAngleV1,
    CampaignAudienceV1,
    CampaignObjectiveV1,
    CampaignPackBriefV1,
    ClaimGuardrailsV1,
    CreatorDirectionV1,
    CtaDirectionV1,
    MustShowRequirementV1,
    RightsNoteV1,
)
from viraldy.modules.campaign_packs.requirements import (
    CompiledRequirementV2,
    compile_requirements,
    compiled_requirements_to_json,
)
from viraldy.modules.media_analysis.public import EvidenceItemModel
from viraldy.modules.preflight.schemas import PreflightRunResponse
from viraldy.modules.preflight.service import calculate_preflight_result
from viraldy.modules.products.contracts import (
    PersonalizationFieldV1,
    ProductPersonalizationV1,
    build_minimal_product_context,
)


@dataclass(slots=True)
class FakeEvidence:
    evidence_type: str
    value_json: dict[str, Any]
    id: UUID = field(default_factory=uuid4)
    start_ms: int | None = None
    end_ms: int | None = None
    confidence: float | None = 0.85
    source: str = "vision"


def test_compile_requirements_reads_typed_campaign_pack_brief() -> None:
    product_context = build_minimal_product_context(
        name="Portable Steamer",
        description=None,
        market="US",
        metadata_json={"category": "beauty_tool"},
    )
    brief = CampaignPackBriefV1(
        product_snapshot=product_context,
        objective=CampaignObjectiveV1(
            objective_type="tiktok_shop_conversion",
            primary_action="create_ugc_revision",
            channel="tiktok_shop",
        ),
        audience=CampaignAudienceV1(
            persona_label="busy traveler",
            pain_points=["wrinkled clothes"],
            desired_outcomes=["ready-to-wear outfit"],
        ),
        angle=CampaignAngleV1(
            name="Fast refresh",
            promise="outfit looks ready quickly",
            mechanism="show steam removing wrinkles",
            emotional_driver="avoid looking unprepared",
        ),
        creator_direction=CreatorDirectionV1(
            persona="busy traveler",
            delivery_style="faceless_demo",
        ),
        hooks=[],
        script_beats=[],
        storyboard=[],
        must_show=[
            MustShowRequirementV1(
                id="must_show_product",
                requirement_type="product",
                description="Product must be visible in a clear close-up.",
                severity="hard",
                expected_before_ms=3000,
                source_path="concepts[concept_1].must_show[0]",
            ),
            MustShowRequirementV1(
                id="must_show_demo",
                requirement_type="demo",
                description="Demo must show steam removing wrinkles.",
                severity="high",
                source_path="concepts[concept_1].must_show[1]",
            ),
            MustShowRequirementV1(
                id="concept_1_disclosure_1",
                requirement_type="claim",
                description="Results vary by fabric.",
                severity="hard",
                source_path="concepts[concept_1].must_show[2].disclosure",
            ),
        ],
        cta=CtaDirectionV1(
            cta_type="product_tag",
            product_tag_required=True,
        ),
        claim_guardrails=ClaimGuardrailsV1(
            prohibited=["guaranteed instant results"],
            required_disclosures=["results vary by fabric"],
        ),
        rights_note=RightsNoteV1(note="Rights pending."),
        source_adaptation_run_id=uuid4(),
        source_concept_id="concept_1",
    )

    requirements = compile_requirements(brief.model_dump(mode="json"))

    by_id = {item.id: item for item in requirements}
    assert by_id["must_show_product"].matcher_type == "product_visibility_timing"
    assert by_id["must_show_product"].expected_semantics == "timing"
    assert by_id["must_show_product"].severity == "hard"
    assert by_id["must_show_product"].matcher_config["before_ms"] == 3000
    assert by_id["must_show_demo"].matcher_type == "demo_mechanism_match"
    assert by_id["concept_1_disclosure_1"].matcher_type == "required_disclosure_presence"
    assert by_id["cta_presence"].matcher_type == "cta_presence"
    assert by_id["cta_type_match"].matcher_type == "cta_type_match"
    assert by_id["product_tag_presence"].severity == "hard"
    assert by_id["prohibited_claim_1"].matcher_type == "prohibited_claim_absence"
    assert by_id["prohibited_claim_1"].expected_semantics == "absence"
    assert by_id["required_disclosure_1"].matcher_type == "required_disclosure_presence"
    assert by_id["required_disclosure_1"].expected_semantics == "presence"
    assert "claim_safety" not in [item.matcher_type for item in requirements]


def test_preflight_response_allows_pending_empty_alignment() -> None:
    response = PreflightRunResponse.model_validate(
        {
            "id": uuid4(),
            "workspace_id": uuid4(),
            "ugc_asset_version_id": uuid4(),
            "campaign_pack_version_id": uuid4(),
            "structural_score_run_id": None,
            "status": "queued",
            "schema_version": "ugc_preflight_v2",
            "structural_score": 0,
            "brief_alignment_score": 0,
            "preflight_score": 0,
            "confidence": "low",
            "action_label": "pending",
            "dimension_scores_json": {},
            "brief_alignment_json": {},
            "strengths_json": [],
            "blockers_json": [],
            "fixes_json": [],
            "revision_message": "",
            "evidence_ids_json": [],
            "product_snapshot_json": None,
            "product_context_schema_version": None,
            "requirements_snapshot_json": None,
            "analysis_mode": "fixture",
            "rubric_version": "ugc_preflight_rubric_v2",
            "rule_version": "ugc_preflight_rules_v2",
            "model_version": None,
            "created_at": datetime.now(UTC),
        }
    )

    assert response.brief_alignment_json.score == 0
    assert response.brief_alignment_json.requirements == []


def test_optional_hooks_compile_as_one_of_group() -> None:
    brief = _brief(
        hooks=[
            {
                "id": "hook_a",
                "spoken_text": "Busy mornings need this shortcut",
                "opening_visual": "show product",
                "hook_type": "problem_first",
                "target_time_ms": 0,
                "mandatory": False,
            },
            {
                "id": "hook_b",
                "spoken_text": "Here is the result",
                "opening_visual": "show result",
                "hook_type": "result_first",
                "target_time_ms": 0,
                "mandatory": False,
            },
        ],
    )

    hooks = [
        item for item in compile_requirements(brief) if item.matcher_type == "hook_semantic_match"
    ]

    assert len(hooks) == 2
    assert {item.requirement_group_id for item in hooks} == {"optional_hooks"}
    assert {item.minimum_satisfied for item in hooks} == {1}


def test_script_scene_beats_compile_to_observable_requirement_matchers() -> None:
    brief = _brief(
        script_beats=[
            {
                "id": "show_product",
                "sequence": 1,
                "beat_type": "scene",
                "instruction": "Show the product clearly.",
                "required": True,
            },
            {
                "id": "show_proof",
                "sequence": 2,
                "beat_type": "scene",
                "instruction": "Show the same item before and after use.",
                "required": True,
            },
            {
                "id": "show_disclosure",
                "sequence": 3,
                "beat_type": "scene",
                "instruction": "Results vary by fabric.",
                "required": True,
            },
            {
                "id": "show_product_tag",
                "sequence": 4,
                "beat_type": "scene",
                "instruction": "Include the TikTok Shop product tag.",
                "required": True,
            },
            {
                "id": "spoken_line",
                "sequence": 5,
                "beat_type": "spoken",
                "instruction": "This is the exact spoken line.",
                "required": True,
            },
        ],
        claim_guardrails={
            "allowed": [],
            "allowed_with_qualification": [],
            "prohibited": [],
            "required_disclosures": ["Results vary by fabric."],
        },
    )

    by_id = {item.id: item for item in compile_requirements(brief)}

    assert by_id["show_product"].matcher_type == "product_visibility"
    assert by_id["show_proof"].matcher_type == "proof_type_match"
    assert by_id["show_disclosure"].matcher_type == "required_disclosure_presence"
    assert by_id["show_product_tag"].matcher_type == "cta_presence"
    assert by_id["spoken_line"].matcher_type == "spoken_text_presence"


def test_missing_medium_requirement_is_an_optional_fix_not_a_blocker() -> None:
    requirement = CompiledRequirementV2(
        id="optional_spoken_line",
        requirement_type="spoken",
        source_path="cta.spoken",
        description="Optional spoken CTA refinement.",
        severity="medium",
        matcher_type="spoken_text_presence",
        matcher_config={"text": "Check the product tag."},
        expected_semantics="presence",
    )

    result = calculate_preflight_result(
        {**_structural(), "structural_score": 90},
        _brief(),
        compiled_requirements_to_json([requirement]),
        cast(list[EvidenceItemModel], [_transcript("This line does not contain the CTA.")]),
    )

    assert _requirement(result, "optional_spoken_line")["status"] == "missing"
    assert result["blockers"] == []
    assert result["action"] == "organic_ready_or_small_paid_test"
    assert result["fixes"][0]["code"] == "FIX_BRIEF_REQUIREMENT"


def test_prohibited_claim_absent_and_present_are_distinct() -> None:
    brief = _brief(
        claim_guardrails={
            "prohibited": ["guaranteed instant results"],
            "required_disclosures": [],
        }
    )
    absent = _calculate(brief, [_transcript("This shows a visible result over time.")])
    present = _calculate(brief, [_transcript("This gives guaranteed instant results.")])

    assert _requirement(absent, "prohibited_claim_1")["status"] == "satisfied"
    assert _requirement(present, "prohibited_claim_1")["status"] == "violated"


def test_required_disclosure_matches_transcript_and_ocr_but_not_similar_text() -> None:
    brief = _brief(
        claim_guardrails={
            "prohibited": [],
            "required_disclosures": ["results vary by fabric"],
        }
    )

    transcript = _calculate(brief, [_transcript("Results vary by fabric and garment condition.")])
    ocr = _calculate(brief, [_ocr("Results vary by fabric")])
    similar = _calculate(brief, [_transcript("Fabric care may vary.")])

    assert _requirement(transcript, "required_disclosure_1")["status"] == "satisfied"
    assert _requirement(ocr, "required_disclosure_1")["status"] == "satisfied"
    assert _requirement(similar, "required_disclosure_1")["status"] == "missing"


def test_product_context_compiles_reveal_proof_and_personalization_requirements() -> None:
    product_context = build_minimal_product_context(
        name="Personalized Dog Mom Crewneck",
        description=None,
        market="US",
        metadata_json={"category": "pod_personalized_apparel"},
    ).model_copy(
        update={
            "creative": build_minimal_product_context(
                name="Personalized Dog Mom Crewneck",
                description=None,
                market="US",
            ).creative.model_copy(
                update={
                    "required_product_reveal_before_ms": 2000,
                    "required_proof_mechanisms": ["same item before and after"],
                }
            ),
            "personalization": ProductPersonalizationV1(
                required=True,
                fields=[
                    PersonalizationFieldV1(
                        key="pet_name",
                        label="Pet name",
                        expected_value="Milo",
                        visual_verification_required=True,
                    )
                ],
                physical_sample_required=True,
            ),
        }
    )
    brief = _brief(product_snapshot=product_context.model_dump(mode="json"))

    by_id = {item.id: item for item in compile_requirements(brief)}

    assert by_id["product_required_reveal_timing"].matcher_type == ("product_visibility_timing")
    assert by_id["product_required_reveal_timing"].matcher_config["before_ms"] == 2000
    assert by_id["product_required_proof_1"].matcher_type == "proof_type_match"
    assert by_id["personalization_pet_name"].matcher_type == ("personalization_exact_match")
    assert by_id["personalization_pet_name"].severity == "hard"
    assert by_id["personalization_pet_name"].matcher_config["expected_value"] == "Milo"


def test_personalization_exact_match_distinguishes_match_mismatch_and_missing() -> None:
    product_context = build_minimal_product_context(
        name="Personalized Dog Mom Crewneck",
        description=None,
        market="US",
    ).model_copy(
        update={
            "personalization": ProductPersonalizationV1(
                required=True,
                fields=[
                    PersonalizationFieldV1(
                        key="pet_name",
                        label="Pet name",
                        expected_value="Milo",
                    )
                ],
            )
        }
    )
    brief = _brief(product_snapshot=product_context.model_dump(mode="json"))

    matched = _calculate(brief, [_ocr("Pet name: Milo")])
    mismatched = _calculate(
        brief,
        [_ocr("Pet name: Miles. Recipient: Dog Mom.")],
    )
    missing = _calculate(brief, [])

    matched_result = _requirement(matched, "personalization_pet_name")
    mismatched_result = _requirement(mismatched, "personalization_pet_name")
    missing_result = _requirement(missing, "personalization_pet_name")
    assert matched_result["status"] == "satisfied"
    assert matched_result["observed"]["observed_value"] == "Milo"
    assert mismatched_result["status"] == "violated"
    assert mismatched_result["observed"]["observed_value"] == "Miles"
    assert missing_result["status"] == "unknown"


def test_allowed_claim_without_qualification_is_violated() -> None:
    requirement = CompiledRequirementV2(
        id="qualified_claim",
        requirement_type="claim",
        source_path="test",
        description="Allowed claim requires qualification.",
        severity="hard",
        matcher_type="allowed_claim_qualification",
        matcher_config={"claim_text": "smoother finish", "qualification_text": "results vary"},
        expected_semantics="qualified_presence",
    )
    result = calculate_preflight_result(
        _structural(),
        _brief(),
        compiled_requirements_to_json([requirement]),
        [_claim("smoother finish", qualification_present=False)],
    )

    evaluation = _requirement(result, "qualified_claim")
    assert evaluation["status"] == "violated"
    assert evaluation["observed"]["qualification_present"] is False


def _brief(**overrides: object) -> dict[str, object]:
    product_context = build_minimal_product_context(
        name="Portable Steamer",
        description=None,
        market="US",
        metadata_json={"category": "beauty_tool"},
    ).model_dump(mode="json")
    brief = {
        "schema_version": "campaign_pack_brief_v1",
        "product_snapshot": product_context,
        "objective": {
            "objective_type": "tiktok_shop_conversion",
            "primary_action": "create_ugc_revision",
            "channel": "tiktok_shop",
        },
        "audience": {
            "persona_label": "busy traveler",
            "pain_points": ["wrinkled clothes"],
            "desired_outcomes": ["ready-to-wear outfit"],
            "objections": [],
            "awareness_stage": "unknown",
        },
        "angle": {
            "name": "Fast refresh",
            "promise": "outfit looks ready quickly",
            "mechanism": "show steam removing wrinkles",
            "emotional_driver": "avoid looking unprepared",
        },
        "creator_direction": {"persona": "beauty reviewer", "delivery_style": "faceless_demo"},
        "hooks": [],
        "script_beats": [],
        "storyboard": [],
        "must_show": [],
        "talking_points": [],
        "text_overlays": [],
        "proof_direction": [],
        "offer_direction": [],
        "cta": {"cta_type": "product_tag", "product_tag_required": True},
        "claim_guardrails": {
            "allowed": [],
            "allowed_with_qualification": [],
            "prohibited": [],
            "required_disclosures": [],
        },
        "do": [],
        "dont": [],
        "rights_note": {"note": "Rights pending."},
        "revision_checklist": [],
        "source_adaptation_run_id": str(uuid4()),
        "source_concept_id": "concept_1",
    }
    brief.update(overrides)
    return brief


def _calculate(brief: dict[str, object], evidence: list[FakeEvidence]) -> dict[str, Any]:
    return calculate_preflight_result(
        _structural(),
        brief,
        None,
        cast(list[EvidenceItemModel], evidence),
        cast(dict[str, object], brief["product_snapshot"]),
    )


def _structural() -> dict[str, Any]:
    return {
        "structural_score": 80,
        "confidence": "high",
        "action": "approve_structure",
        "dimensions": {},
        "strengths": [],
        "blockers": [],
        "fixes": [],
        "evidence_ids": [],
    }


def _transcript(text: str) -> FakeEvidence:
    return FakeEvidence(
        "transcript_segment",
        {"text": text, "start_ms": 0, "end_ms": 1000},
        start_ms=0,
        end_ms=1000,
        source="asr",
    )


def _ocr(text: str) -> FakeEvidence:
    return FakeEvidence(
        "on_screen_text",
        {"text": text, "start_ms": 0, "end_ms": 1000},
        start_ms=0,
        end_ms=1000,
        source="ocr",
    )


def _claim(text: str, *, qualification_present: bool) -> FakeEvidence:
    return FakeEvidence(
        "claim_signal",
        {
            "text": text,
            "source": "spoken",
            "category": "performance",
            "risk": "low",
            "qualification_present": qualification_present,
            "confidence": 0.9,
        },
        start_ms=0,
        end_ms=1000,
    )


def _requirement(result: dict[str, Any], requirement_id: str) -> dict[str, Any]:
    return next(
        item
        for item in result["brief_alignment"]["requirements"]
        if item["requirement_id"] == requirement_id
    )
