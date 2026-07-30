from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import uuid4

from viraldy.modules.campaign_packs.contracts import CampaignPackBriefV1
from viraldy.modules.campaign_packs.exporter import build_campaign_pack_export
from viraldy.modules.campaign_packs.schemas import CampaignPackVersionResponse
from viraldy.modules.products.contracts import build_minimal_product_context


def _version() -> CampaignPackVersionResponse:
    brief = CampaignPackBriefV1(
        product_snapshot=build_minimal_product_context(
            name="Counter Shelf / Launch",
            description="Organizes a counter.",
            market="US",
        ),
        objective={
            "objective_type": "affiliate_test",
            "primary_action": "product_click",
            "channel": "tiktok_shop",
        },
        audience={
            "persona_label": "busy renter",
            "pain_points": ["visible counter clutter"],
            "desired_outcomes": ["usable counter space"],
        },
        angle={
            "name": "Visible counter reset",
            "promise": "Organize visible clutter.",
            "mechanism": "Show the raised storage surface in use.",
            "emotional_driver": "relief",
        },
        creator_direction={
            "persona": "home organizer",
            "delivery_style": "demonstration",
        },
        hooks=[
            {
                "id": "hook_1",
                "spoken_text": "My counter finally has room again.",
                "opening_visual": "Show the cluttered counter.",
                "hook_type": "problem_first",
                "target_time_ms": 0,
            }
        ],
        script_beats=[
            {
                "id": "beat_1",
                "sequence": 1,
                "beat_type": "demo",
                "instruction": "Show the shelf being placed on the counter.",
                "required": True,
            }
        ],
        storyboard=[],
        must_show=[],
        talking_points=["Keep the product visible during the setup."],
        cta={"cta_type": "product_click", "product_tag_required": True},
        claim_guardrails={"prohibited": ["guaranteed exact space saved"]},
        rights_note={"note": "Seller-owned footage only."},
        revision_checklist=["Product is visible before the CTA."],
        source_concept_id="concept_1",
    )
    return CampaignPackVersionResponse(
        id=uuid4(),
        campaign_pack_id=uuid4(),
        version_number=3,
        brief_json=brief,
        brief_schema_version="campaign_pack_brief_v1",
        product_snapshot_json=brief.product_snapshot,
        compiled_requirements_json={
            "schema_version": "compiled_requirements_v2",
            "requirements": [],
        },
        requirements_schema_version="compiled_requirements_v2",
        change_note="Approved creator brief.",
        source_adaptation_run_id=None,
        source_model_run_id=None,
        source_prompt_version="viral_kit_campaign_pack_v1",
        source_schema_version="viral_kit_v1",
        created_at=datetime(2026, 7, 30, 8, 0, tzinfo=UTC),
    )


def test_json_export_is_a_versioned_canonical_snapshot() -> None:
    version = _version()

    result = build_campaign_pack_export(version, "json")
    payload = json.loads(result.content)

    assert result.campaign_pack_id == version.campaign_pack_id
    assert result.campaign_pack_version_id == version.id
    assert result.version_number == 3
    assert result.filename == "counter-shelf-launch-creator-brief-v3.json"
    assert result.content_type == "application/json"
    assert payload["campaign_pack_id"] == str(version.campaign_pack_id)
    assert payload["campaign_pack_version_id"] == str(version.id)
    assert payload["brief"]["source_concept_id"] == "concept_1"
    assert payload["compiled_requirements"]["schema_version"] == "compiled_requirements_v2"


def test_text_export_contains_creator_instructions_and_traceability() -> None:
    version = _version()

    result = build_campaign_pack_export(version, "text")

    assert result.filename == "counter-shelf-launch-creator-brief-v3.txt"
    assert result.content_type == "text/plain; charset=utf-8"
    assert "COUNTER SHELF / LAUNCH - CREATOR BRIEF" in result.content
    assert "My counter finally has room again." in result.content
    assert "Show the shelf being placed on the counter." in result.content
    assert "guaranteed exact space saved" in result.content
    assert f"Campaign Pack version: {version.id}" in result.content
