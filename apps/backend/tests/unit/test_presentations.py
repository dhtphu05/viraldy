from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from typing import cast
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from viraldy.modules.campaign_packs.service import _brief_from_concept
from viraldy.modules.preflight.models import PreflightRunModel
from viraldy.modules.presentations.public import (
    CreatorRevisionInputV2,
    GeneratePresentationRequestV1,
    PreflightPresentationService,
    PresentationBlockerV1,
    PresentationFixV1,
    SellerDecisionInputV1,
    build_deterministic_creator_message,
    build_deterministic_seller_summary,
)
from viraldy.modules.products.contracts import (
    BuyerPersonaV1,
    CreativeContextV1,
    ProductContextV1,
    ProductIdentityV1,
)
from viraldy.platform.config.settings import Settings


def test_seller_summary_is_product_specific_and_actionable() -> None:
    summary = build_deterministic_seller_summary(
        SellerDecisionInputV1(
            product_name="SwiftPress Mini Garment Steamer",
            objective="Test the Late for Class concept",
            action_label="revise",
            final_score=71,
            structural_score=74,
            brief_alignment_score=57,
            confidence="high",
            strengths=["Natural creator delivery", "Clear product-tag CTA"],
            blockers=[
                PresentationBlockerV1(
                    code="PRODUCT_REVEAL_LATE",
                    message=(
                        "Product appears at 4.2 seconds; the brief requires "
                        "visibility by 2.0 seconds."
                    ),
                )
            ],
            fixes=[
                PresentationFixV1(
                    code="PRODUCT_REVEAL_LATE",
                    instruction="Move the SwiftPress close-up into the first two seconds.",
                )
            ],
            next_action="Upload a revised version and rerun Preflight.",
        )
    )

    assert "SwiftPress Mini Garment Steamer" in summary.headline
    assert "Test the Late for Class concept" in summary.why_this_matters
    assert summary.next_actions[0].startswith("Move the SwiftPress")
    assert "guarantee" in summary.commercial_guardrail
    assert "viral-ready" not in summary.model_dump_json().lower()


def test_creator_message_preserves_strengths_and_requests_exact_fixes() -> None:
    message = build_deterministic_creator_message(
        CreatorRevisionInputV2(
            product_name="SwiftPress Mini Garment Steamer",
            strengths_to_preserve=[
                "The student setup feels natural",
                "The product-tag ending works well",
            ],
            required_changes=[
                PresentationFixV1(
                    code="PRODUCT_REVEAL_LATE",
                    instruction="Move the product close-up into the opening",
                    target_end_ms=2000,
                ),
                PresentationFixV1(
                    code="SAME_ITEM_PROOF_MISSING",
                    instruction=(
                        "Return to the exact shirt section after steaming and "
                        "hold the result for comparison"
                    ),
                ),
                PresentationFixV1(
                    code="REQUIRED_DISCLOSURE_MISSING",
                    instruction="Add a spoken or on-screen disclosure",
                    required_text="Results vary by fabric type.",
                ),
            ],
            allowed_blocker_codes=[
                "PRODUCT_REVEAL_LATE",
                "SAME_ITEM_PROOF_MISSING",
                "REQUIRED_DISCLOSURE_MISSING",
            ],
            resubmission_request=(
                "Please keep the current tone and CTA, then upload the revised "
                "version for review."
            ),
        )
    )

    assert message.message.startswith("The student setup feels natural.")
    assert "by 2 seconds" in message.message
    assert '"Results vary by fabric type."' in message.message
    assert message.message.endswith("version for review.")
    for jargon in ("rubric", "blocker class", "schema", "confidence score"):
        assert jargon not in message.message.lower()


def test_creator_message_cannot_reference_unsupplied_blocker() -> None:
    with pytest.raises(ValidationError):
        CreatorRevisionInputV2(
            product_name="SwiftPress Mini Garment Steamer",
            strengths_to_preserve=["Natural delivery"],
            required_changes=[
                PresentationFixV1(
                    code="UNSUPPLIED_BLOCKER",
                    instruction="Replace the product.",
                )
            ],
            allowed_blocker_codes=["PRODUCT_REVEAL_LATE"],
            resubmission_request="Upload the revised version for review.",
        )


@pytest.mark.asyncio
async def test_preflight_presentation_service_persists_and_reuses_deterministic_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import viraldy.modules.presentations.service as service_module

    workspace_id = uuid4()
    preflight = PreflightRunModel(
        id=uuid4(),
        workspace_id=workspace_id,
        ugc_asset_version_id=uuid4(),
        campaign_pack_version_id=uuid4(),
        status="completed",
        structural_score=Decimal("74"),
        brief_alignment_score=Decimal("57"),
        preflight_score=Decimal("71"),
        confidence="high",
        action_label="revise",
        dimension_scores_json={},
        brief_alignment_json={},
        strengths_json=[
            {
                "code": "NATURAL_DELIVERY",
                "message": "The student setup feels natural",
                "dimensions": ["creator_authenticity"],
                "evidence_ids": [],
            }
        ],
        blockers_json=[
            {
                "code": "PRODUCT_REVEAL_LATE",
                "severity": "hard",
                "message": "Product appears at 4.2 seconds; visibility is required by 2.0 seconds.",
                "evidence_ids": [],
                "remediation_code": "MOVE_PRODUCT_EARLIER",
            }
        ],
        fixes_json=[
            {
                "code": "MOVE_PRODUCT_EARLIER",
                "priority": 1,
                "instruction": "Move the product close-up into the opening.",
                "why": "The brief requires visibility by 2.0 seconds.",
                "expected_impact_dimensions": ["product_visibility"],
                "evidence_ids": [],
            }
        ],
        revision_message="",
        evidence_ids_json=[],
        schema_version="ugc_preflight_v2",
        product_snapshot_json=None,
        product_context_schema_version=None,
        requirements_snapshot_json=None,
        analysis_mode="fixture",
        rubric_version="ugc_preflight_rubric_v2",
        rule_version="ugc_preflight_rules_v2",
        seller_summary_json=None,
        creator_revision_json=None,
        presentation_model_run_ids_json=[],
        presentation_source_json={},
    )
    product_context = ProductContextV1(
        identity=ProductIdentityV1(
            name="SwiftPress Mini Garment Steamer",
            category="garment_care",
            market="US",
        ),
        personas=[
            BuyerPersonaV1(
                id="college_student",
                label="College student",
                pain_points=["Wrinkled shirt before class"],
                desired_outcomes=["Look presentable quickly"],
            )
        ],
        creative=CreativeContextV1(
            creator_personas=["US college lifestyle creator"]
        ),
    )
    brief = _brief_from_concept(
        "tiktok_shop_conversion",
        "US",
        {},
        product_context.model_dump(mode="json"),
        {
            "id": "late_for_class",
            "buyer_persona_id": "college_student",
            "buyer_persona_label": "College student",
            "buyer_pain": "Wrinkled shirt before class",
            "desired_outcome": "Look presentable quickly",
            "creator_persona": "US college lifestyle creator",
            "delivery_style": "casual demonstration",
            "hook_options": ["I had ten minutes before class."],
            "demo_sequence": ["Show SwiftPress in use."],
            "must_show": ["product close-up"],
        },
        uuid4(),
        "late_for_class",
    )
    brief = brief.model_copy(
        update={
            "must_show": [
                requirement.model_copy(
                    update={
                        "expected_before_ms": (
                            2000
                            if requirement.requirement_type == "product"
                            else requirement.expected_before_ms
                        )
                    }
                )
                for requirement in brief.must_show
            ]
        }
    )

    class FakePreflightRepository:
        def __init__(self, session: object) -> None:
            pass

        async def get(
            self, requested_workspace_id: object, preflight_run_id: object
        ) -> PreflightRunModel:
            assert requested_workspace_id == workspace_id
            assert preflight_run_id == preflight.id
            return preflight

    class FakeCampaignPackRepository:
        def __init__(self, session: object) -> None:
            pass

        async def get_version_in_workspace(
            self, requested_workspace_id: object, version_id: object
        ) -> object:
            assert requested_workspace_id == workspace_id
            assert version_id == preflight.campaign_pack_version_id
            return SimpleNamespace(brief_json=brief.model_dump(mode="json"))

    class FakeSession:
        flush_count = 0
        commit_count = 0

        async def flush(self) -> None:
            self.flush_count += 1

        async def commit(self) -> None:
            self.commit_count += 1

    monkeypatch.setattr(
        service_module,
        "PreflightRepository",
        FakePreflightRepository,
    )
    monkeypatch.setattr(
        service_module,
        "CampaignPackRepository",
        FakeCampaignPackRepository,
    )
    fake_session = FakeSession()
    service = PreflightPresentationService(
        cast(AsyncSession, fake_session),
        Settings(ai_mode="fixture"),
    )

    first = await service.generate(
        workspace_id=workspace_id,
        preflight_run_id=preflight.id,
        actor_user_id=uuid4(),
        request=GeneratePresentationRequestV1(),
    )
    second = await service.generate(
        workspace_id=workspace_id,
        preflight_run_id=preflight.id,
        actor_user_id=uuid4(),
        request=GeneratePresentationRequestV1(),
    )

    assert first == second
    assert first.sources["seller_summary"] == "deterministic"
    assert first.creator_revision is not None
    assert "SwiftPress Mini Garment Steamer" in first.seller_summary.headline
    assert "by 2 seconds" in first.creator_revision.message
    assert preflight.seller_summary_json is not None
    assert preflight.creator_revision_json is not None
    assert fake_session.commit_count == 1
