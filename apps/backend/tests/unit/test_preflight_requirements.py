from __future__ import annotations

from uuid import uuid4

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
from viraldy.modules.preflight.requirements import compile_requirements
from viraldy.modules.products.contracts import build_minimal_product_context


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
    assert by_id["must_show_product"].matcher_type == "product_visibility"
    assert by_id["must_show_product"].severity == "hard"
    assert by_id["must_show_product"].matcher_config["expected_before_ms"] == 3000
    assert by_id["must_show_demo"].matcher_type == "demo_presence"
    assert by_id["cta_required"].matcher_type == "cta_presence"
    assert by_id["cta_required"].severity == "hard"
    assert [item.matcher_type for item in requirements].count("claim_safety") == 2
