from __future__ import annotations

from dataclasses import dataclass

from viraldy.evaluation.golden import load_golden_fixture
from viraldy.evaluation.golden.loader import GOLDEN_SCENARIO_IDS


@dataclass(frozen=True, slots=True)
class QualificationMediaScene:
    start_seconds: float
    end_seconds: float
    text: str


@dataclass(frozen=True, slots=True)
class QualificationMediaStory:
    duration_seconds: float
    scenes: tuple[QualificationMediaScene, ...]
    narration: str


@dataclass(frozen=True, slots=True)
class GoldenApplicationScenario:
    scenario_id: str
    primary_category: str
    viral_objective: str
    product_payload: dict[str, object]
    draft_asset_id: str
    revision_asset_id: str
    draft_story: QualificationMediaStory
    revision_story: QualificationMediaStory


def load_application_scenario(
    scenario_id: str,
    *,
    run_id: str,
) -> GoldenApplicationScenario:
    if scenario_id not in GOLDEN_SCENARIO_IDS:
        raise ValueError(f"unsupported Golden application scenario: {scenario_id}")
    if scenario_id == "home_travel_steamer":
        return _steamer_scenario(run_id)
    if scenario_id == "pod_dog_mom_crewneck":
        return _pod_scenario(run_id)
    return _bag_sealer_scenario(run_id)


def _steamer_scenario(run_id: str) -> GoldenApplicationScenario:
    fixture = load_golden_fixture("home_travel_steamer")
    context: dict[str, object] = {
        "schema_version": "product_context_v1",
        "identity": {
            "name": fixture.product_name,
            "brand": "SwiftPress",
            "category": "home_travel_appliance",
            "subcategory": "mini_garment_steamer",
            "market": "US",
            "currency": "USD",
        },
        "personas": [
            {
                "id": "college_student",
                "label": "College student with rushed mornings",
                "pain_points": ["wrinkled shirt before class", "limited dorm storage"],
                "desired_outcomes": ["wearable shirt without a full-size iron"],
                "objections": ["unclear result on their fabric"],
                "awareness_stage": "problem_aware",
            },
            {
                "id": "carry_on_traveler",
                "label": "Carry-on traveler",
                "pain_points": ["clothes wrinkle in luggage"],
                "desired_outcomes": ["refresh one packed garment"],
                "objections": ["unclear travel fit"],
                "awareness_stage": "solution_aware",
            },
        ],
        "benefits": [
            {
                "id": "visible_fabric_refresh",
                "label": "Observable fabric refresh",
                "description": "Shows the result on the same garment and fabric area.",
                "proof_available": ["same-shirt before and after comparison"],
                "claim_strength": "observed",
            }
        ],
        "features": [
            {
                "id": "compact_steam_head",
                "label": "Compact steam head",
                "description": "A small handheld garment-steaming surface.",
                "visual_demo_possible": True,
                "visual_cues": ["steamer and garment remain visible during use"],
            }
        ],
        "commercial": {
            "price": "29.99",
            "shipping_text": "Use only the current TikTok Shop listing estimate.",
            "margin_band": "unknown",
        },
        "creative": {
            "primary_angles": ["late-for-class rescue", "carry-on clothing rescue"],
            "demonstration_mechanisms": [
                "show the same shirt before steaming, during use, and after"
            ],
            "visual_differentiators": ["same shirt and fabric area remain identifiable"],
            "available_proof": ["same-item before and after result"],
            "creator_personas": ["college lifestyle creator", "travel creator"],
            "preferred_delivery_styles": ["authentic_review", "demonstration"],
            "brand_voice": ["specific", "natural", "evidence-led"],
            "prohibited_visuals": ["switching garments between before and after"],
            "required_product_reveal_before_ms": 2000,
            "required_proof_mechanisms": ["same item before and after"],
        },
        "personalization": {"required": False, "fields": []},
        "governance": {
            "claims": [
                {
                    "id": "no_instant_result",
                    "text": "instant wrinkle removal on every fabric",
                    "rule_type": "prohibited",
                    "severity": "high",
                }
            ],
            "required_disclosures": fixture.required_disclosures,
            "prohibited_content": ["unsupported shipping or offer wording"],
            "rights_notes": ["Use seller-owned qualification media only."],
        },
    }
    return GoldenApplicationScenario(
        scenario_id=fixture.scenario_id,
        primary_category="home_travel_appliance",
        viral_objective="tiktok_shop_affiliate_test",
        product_payload=_product_payload(fixture.product_name, fixture.objective, context, run_id),
        draft_asset_id="ugc_missing_product_timing",
        revision_asset_id="ugc_revision_resolves_all",
        draft_story=QualificationMediaStory(
            duration_seconds=22.7,
            scenes=(
                _scene(0, 4.2, "Rushed before class\nWrinkled blue shirt\nNo product yet"),
                _scene(
                    4.2,
                    8,
                    "SwiftPress Mini Garment Steamer\nProduct first appears at 4.2 seconds",
                ),
                _scene(8, 13, "Steam is visible\nSame-shirt result is not shown"),
                _scene(13, 22.7, "Natural student creator\nTap the product tag to see it"),
            ),
            narration=(
                "I had ten minutes before class and this shirt was still wrinkled. "
                "Here is the SwiftPress Mini Garment Steamer. I used it on this shirt, "
                "but the final same-shirt result is not visible. Tap the product tag to see it."
            ),
        ),
        revision_story=QualificationMediaStory(
            duration_seconds=22.1,
            scenes=(
                _scene(0, 1.4, "SwiftPress Mini Garment Steamer\nProduct shown immediately"),
                _scene(1.4, 6, "BEFORE\nSame blue shirt\nWrinkled fabric area"),
                _scene(6, 12, "DEMO\nSteaming the same blue shirt"),
                _scene(12, 15.2, "AFTER\nSame blue shirt\nVisible smoother result"),
                _scene(15.2, 18, "Results vary by fabric type."),
                _scene(18, 22.1, "Tap the product tag to see it"),
            ),
            narration=(
                "I had ten minutes before class and this shirt was still wrinkled. "
                "Here is the SwiftPress Mini Garment Steamer. This is the same blue shirt "
                "before, during use, and after. Results vary by fabric type. "
                "Tap the product tag to see it."
            ),
        ),
    )


def _pod_scenario(run_id: str) -> GoldenApplicationScenario:
    fixture = load_golden_fixture("pod_dog_mom_crewneck")
    context: dict[str, object] = {
        "schema_version": "product_context_v1",
        "identity": {
            "name": fixture.product_name,
            "brand": "PawThread",
            "category": "pod_personalized_apparel",
            "subcategory": "personalized_crewneck",
            "variant": "Dog Mom / Milo / Golden Retriever",
            "market": "US",
            "currency": "USD",
        },
        "personas": [
            {
                "id": "dog_mom_self_purchase",
                "label": "Dog mom buying an identity crewneck",
                "pain_points": ["generic pet apparel feels impersonal"],
                "desired_outcomes": ["see their own pet name in the design"],
                "objections": ["personalization or ordering could be wrong"],
                "awareness_stage": "product_aware",
            },
            {
                "id": "personalized_gift_buyer",
                "label": "Gift buyer for a dog mom",
                "pain_points": ["generic gifts lack emotional relevance"],
                "desired_outcomes": ["a correct, giftable personalized item"],
                "objections": ["production and delivery timing"],
                "awareness_stage": "solution_aware",
            },
        ],
        "benefits": [
            {
                "id": "personal_identity",
                "label": "Pet-specific identity detail",
                "description": "The physical crewneck shows the selected pet name.",
                "proof_available": ["readable personalization on the physical sample"],
                "claim_strength": "observed",
            }
        ],
        "features": [
            {
                "id": "custom_pet_name",
                "label": "Custom pet name",
                "description": "Pet name is supplied during ordering.",
                "visual_demo_possible": True,
                "visual_cues": ["readable name on the physical garment"],
            }
        ],
        "commercial": {
            "price": "39.00",
            "shipping_text": "Production and delivery estimates come from the current listing.",
            "margin_band": "unknown",
            "offer_notes": ["Do not promise a delivery date not present in the listing."],
        },
        "creative": {
            "primary_angles": [
                "dog mom identity",
                "gift reaction",
                "how personalization works",
            ],
            "demonstration_mechanisms": [
                "show the physical garment and readable personalized name"
            ],
            "visual_differentiators": ["physical product rather than a listing mockup"],
            "available_proof": ["readable personalization on physical crewneck"],
            "creator_personas": ["dog mom lifestyle creator", "gift guide creator"],
            "preferred_delivery_styles": ["storytelling", "authentic_review"],
            "brand_voice": ["warm", "specific", "clear"],
            "prohibited_visuals": ["digital mockup presented as delivered physical product"],
            "required_proof_mechanisms": ["visual result"],
        },
        "personalization": {
            "required": True,
            "fields": [
                {
                    "key": "pet_name",
                    "label": "Pet name",
                    "expected_value": "Milo",
                    "case_sensitive": False,
                    "visual_verification_required": True,
                },
                {
                    "key": "recipient",
                    "label": "Recipient",
                    "expected_value": "Dog Mom",
                    "case_sensitive": False,
                    "visual_verification_required": True,
                },
                {
                    "key": "design_variant",
                    "label": "Design variant",
                    "expected_value": "Golden Retriever",
                    "case_sensitive": False,
                    "visual_verification_required": True,
                },
            ],
            "physical_sample_required": True,
            "ordering_instructions": ["Enter the pet name exactly as it should print."],
            "production_constraints": ["Personalized items require production time."],
            "delivery_constraints": ["Use only the current listing's delivery estimate."],
        },
        "governance": {
            "claims": [],
            "required_disclosures": [],
            "prohibited_content": ["unclear personalization ordering instructions"],
            "rights_notes": ["Use seller-owned qualification media only."],
        },
    }
    return GoldenApplicationScenario(
        scenario_id=fixture.scenario_id,
        primary_category="pod_personalized_apparel",
        viral_objective="pod_gift_campaign",
        product_payload=_product_payload(fixture.product_name, fixture.objective, context, run_id),
        draft_asset_id="pod_personalization_mismatch",
        revision_asset_id="pod_personalization_corrected",
        draft_story=QualificationMediaStory(
            duration_seconds=18.1,
            scenes=(
                _scene(0, 4, "Personalized Dog Mom Crewneck\nGift reveal for a dog mom"),
                _scene(4, 7.2, "Order details\nPet name: Milo\nRecipient: Dog Mom"),
                _scene(
                    7.2,
                    9.6,
                    "Physical crewneck shown\nPet name: Miles\nRecipient: Dog Mom",
                ),
                _scene(
                    9.6,
                    14,
                    "Design variant: Golden Retriever\nNatural creator reaction",
                ),
                _scene(14, 18.1, "Check spelling before ordering\nTap the product tag"),
            ),
            narration=(
                "Tell me you are a dog mom without telling me. This Personalized Dog Mom "
                "Crewneck order says Milo, but the physical sample says Miles. "
                "Check the pet name and spelling before ordering. Tap the product tag."
            ),
        ),
        revision_story=QualificationMediaStory(
            duration_seconds=18.1,
            scenes=(
                _scene(0, 4, "Personalized Dog Mom Crewneck\nCorrect physical sample"),
                _scene(
                    4,
                    10,
                    "Pet name: Milo\nRecipient: Dog Mom\nDesign variant: Golden Retriever",
                ),
                _scene(10, 14, "Physical crewneck close-up\nPersonalization is readable"),
                _scene(14, 18.1, "Check spelling before ordering\nTap the product tag"),
            ),
            narration=(
                "Tell me you are a dog mom without telling me. This physical Personalized "
                "Dog Mom Crewneck correctly shows pet name Milo, recipient Dog Mom, and "
                "the Golden Retriever design. Check spelling before ordering. Tap the product tag."
            ),
        ),
    )


def _bag_sealer_scenario(run_id: str) -> GoldenApplicationScenario:
    fixture = load_golden_fixture("dropshipping_bag_sealer")
    prohibited_claim = "This makes every bag completely airtight."
    context: dict[str, object] = {
        "schema_version": "product_context_v1",
        "identity": {
            "name": fixture.product_name,
            "brand": "SealSnap",
            "category": "kitchen_gadget",
            "subcategory": "rechargeable_bag_sealer",
            "market": "US",
            "currency": "USD",
        },
        "personas": [
            {
                "id": "dorm_snack_buyer",
                "label": "Dorm snack buyer",
                "pain_points": ["open snack bags spill or go stale"],
                "desired_outcomes": ["reclose a supported snack bag"],
                "objections": ["unclear bag compatibility"],
                "awareness_stage": "problem_aware",
            },
            {
                "id": "family_pantry_buyer",
                "label": "Family pantry organizer",
                "pain_points": ["open packages create pantry mess"],
                "desired_outcomes": ["visible seal on a supported package"],
                "objections": ["universal airtight claims feel untrustworthy"],
                "awareness_stage": "solution_aware",
            },
        ],
        "benefits": [
            {
                "id": "visible_reseal",
                "label": "Visible seal on a supported snack bag",
                "description": "Shows the creator's specific bag and visible seal line.",
                "proof_available": ["visible seal line on the demonstrated snack bag"],
                "claim_strength": "observed",
            }
        ],
        "features": [
            {
                "id": "rechargeable_heat_sealer",
                "label": "Rechargeable heat-sealing edge",
                "description": "Used across a compatible thermoplastic snack-bag edge.",
                "visual_demo_possible": True,
                "visual_cues": ["one-handed pass", "visible sealed line"],
            }
        ],
        "commercial": {
            "price": "19.99",
            "shipping_text": "Use only the current listing's shipping language.",
            "margin_band": "unknown",
        },
        "creative": {
            "primary_angles": ["dorm snack fix", "family pantry routine", "travel packing"],
            "demonstration_mechanisms": [
                "show one-handed sealing on the specific supported snack bag"
            ],
            "visual_differentiators": ["visible seal line after the pass"],
            "available_proof": ["visible result on the demonstrated bag"],
            "creator_personas": ["student creator", "pantry organizer"],
            "preferred_delivery_styles": ["demonstration", "authentic_review"],
            "brand_voice": ["specific", "practical", "trustworthy"],
            "prohibited_visuals": ["unsupported bag material presented as compatible"],
            "required_product_reveal_before_ms": None,
            "required_proof_mechanisms": ["visual result"],
        },
        "personalization": {"required": False, "fields": []},
        "governance": {
            "claims": [
                {
                    "id": "no_universal_airtight_claim",
                    "text": prohibited_claim,
                    "rule_type": "prohibited",
                    "severity": "critical",
                }
            ],
            "required_disclosures": [],
            "prohibited_content": [
                "universal bag compatibility",
                "unsupported airtight guarantee",
            ],
            "rights_notes": ["Use seller-owned qualification media only."],
        },
    }
    return GoldenApplicationScenario(
        scenario_id=fixture.scenario_id,
        primary_category="kitchen_gadget",
        viral_objective="dropshipping_demo_test",
        product_payload=_product_payload(fixture.product_name, fixture.objective, context, run_id),
        draft_asset_id="ugc_prohibited_claim",
        revision_asset_id="ugc_supported_claim_revision",
        draft_story=QualificationMediaStory(
            duration_seconds=16.4,
            scenes=(
                _scene(0, 1.1, "Open snack bag spill problem"),
                _scene(1.1, 5, "Rechargeable Mini Bag Sealer\nProduct shown in hand"),
                _scene(5, 8.9, "One-handed demo\nSupported snack bag\nVisible seal line"),
                _scene(8.9, 12.5, prohibited_claim),
                _scene(12.5, 16.4, "Tap the product tag\nShipping details are in the listing"),
            ),
            narration=(
                "I was tired of chips spilling inside my backpack. Here is the Rechargeable "
                "Mini Bag Sealer on this snack bag. This makes every bag completely airtight. "
                "Tap the product tag and check shipping in the listing."
            ),
        ),
        revision_story=QualificationMediaStory(
            duration_seconds=16.4,
            scenes=(
                _scene(0, 1.1, "Open snack bag spill problem"),
                _scene(1.1, 5, "Rechargeable Mini Bag Sealer\nProduct shown in hand"),
                _scene(5, 11, "One-handed demo\nThis supported snack bag\nVisible seal line"),
                _scene(
                    11,
                    16.4,
                    "Shown on this snack bag only\nCheck bag compatibility in the listing",
                ),
            ),
            narration=(
                "I was tired of chips spilling inside my backpack. Here is the Rechargeable "
                "Mini Bag Sealer used one-handed on this supported snack bag. "
                "The seal line is visible on this bag. Check compatibility in the listing."
            ),
        ),
    )


def _product_payload(
    product_name: str,
    objective: str,
    product_context: dict[str, object],
    run_id: str,
) -> dict[str, object]:
    identity = product_context["identity"]
    assert isinstance(identity, dict)
    return {
        "name": product_name,
        "description": objective,
        "market": "US",
        "metadata_json": {
            "category": identity["category"],
            "qualification_scenario": run_id,
        },
        "product_context": product_context,
    }


def _scene(
    start_seconds: float,
    end_seconds: float,
    text: str,
) -> QualificationMediaScene:
    return QualificationMediaScene(start_seconds, end_seconds, text)
