from __future__ import annotations

from uuid import uuid4

from viraldy.modules.campaign_packs.service import _brief_from_concept
from viraldy.modules.products.contracts import (
    BuyerPersonaV1,
    CreativeContextV1,
    ProductContextV1,
    ProductIdentityV1,
)


def test_campaign_pack_preserves_buyer_and_creator_personas_separately() -> None:
    product_context = ProductContextV1(
        identity=ProductIdentityV1(name="Beauty Tool", category="beauty_tool", market="US"),
        personas=[
            BuyerPersonaV1(
                id="buyer_busy_student",
                label="busy college student",
                pain_points=["quick styling before class"],
                desired_outcomes=["polished hair quickly"],
            )
        ],
        creative=CreativeContextV1(creator_personas=["beauty reviewer"]),
    )
    concept = {
        "id": "concept_1",
        "buyer_persona_id": "buyer_busy_student",
        "buyer_persona_label": "busy college student",
        "buyer_pain": "quick styling before class",
        "desired_outcome": "polished hair quickly",
        "creator_persona": "beauty reviewer",
        "delivery_style": "faceless_demo",
        "hook_options": ["Class starts soon, but my hair still looks finished"],
        "demo_sequence": ["show beauty tool in use"],
        "must_show": ["product close-up", "demo in use"],
    }

    brief = _brief_from_concept(
        "tiktok_shop_conversion",
        "US",
        {},
        product_context.model_dump(mode="json"),
        concept,
        uuid4(),
        "concept_1",
    )

    assert brief.audience.persona_id == "buyer_busy_student"
    assert brief.audience.persona_label == "busy college student"
    assert brief.creator_direction.persona == "beauty reviewer"
    assert brief.creator_direction.delivery_style == "faceless_demo"
