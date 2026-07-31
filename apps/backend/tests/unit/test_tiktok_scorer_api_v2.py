from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import ValidationError

from viraldy.modules.tiktok_scorer.schemas import (
    CreateTikTokScoreRequest,
    CreateTikTokScoreRevisionRequest,
    RecordTikTokFixActionRequest,
)


def test_create_score_accepts_canonical_asset_version_without_product() -> None:
    asset_version_id = uuid4()

    request = CreateTikTokScoreRequest(asset_version_id=asset_version_id)

    assert request.asset_version_id == asset_version_id
    assert request.asset_id is None
    assert request.score_mode == "quick"
    assert request.score_profile == "general_tiktok_v1"
    assert request.intended_use == "tiktok_organic"


def test_create_score_keeps_legacy_asset_id_compatibility() -> None:
    asset_id = uuid4()

    request = CreateTikTokScoreRequest(asset_id=asset_id, objective="legacy-objective")

    assert request.asset_id == asset_id
    assert request.asset_version_id is None
    assert request.objective == "legacy-objective"


def test_create_score_requires_an_asset_reference() -> None:
    with pytest.raises(ValidationError):
        CreateTikTokScoreRequest()


def test_product_aware_mode_requires_product() -> None:
    with pytest.raises(ValidationError):
        CreateTikTokScoreRequest(asset_version_id=uuid4(), score_mode="product_aware")


def test_usage_aware_mode_allows_optional_product_context() -> None:
    request = CreateTikTokScoreRequest(asset_version_id=uuid4(), score_mode="usage_aware")

    assert request.product_id is None


def test_revision_accepts_existing_immutable_version_and_auditable_profile_override() -> None:
    asset_version_id = uuid4()

    request = CreateTikTokScoreRevisionRequest(
        asset_version_id=asset_version_id,
        score_profile="story_led_pov_v1",
        profile_override_reason="The revision intentionally changes to a story-led opening.",
    )

    assert request.asset_version_id == asset_version_id
    assert request.score_profile == "story_led_pov_v1"
    assert request.profile_override_reason is not None


@pytest.mark.parametrize(
    "event_type",
    [
        "viewed",
        "accepted",
        "rejected",
        "sent_to_creator",
        "sent_to_editor",
        "marked_completed",
        "verified_after_revision",
    ],
)
def test_fix_action_event_contract_accepts_supported_events(event_type: str) -> None:
    request = RecordTikTokFixActionRequest(event_type=event_type)

    assert request.event_type == event_type


def test_fix_action_event_contract_rejects_unknown_events() -> None:
    with pytest.raises(ValidationError):
        RecordTikTokFixActionRequest(event_type="silently_ignored")
