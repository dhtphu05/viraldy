from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import ValidationError

from viraldy.modules.ugc_review.schemas import (
    CreateUGCReviewForm,
    RecordUGCRecommendationActionRequest,
)


def test_create_form_keeps_context_optional_and_applies_defaults() -> None:
    asset_id = uuid4()
    asset_version_id = uuid4()

    payload = CreateUGCReviewForm(asset_id=asset_id, asset_version_id=asset_version_id)

    assert payload.asset_id == asset_id
    assert payload.asset_version_id == asset_version_id
    assert payload.market == "US"
    assert payload.platform == "tiktok_shop"
    assert payload.commerce_domain == "generic"
    assert payload.intended_use == "unknown"
    assert payload.material_connection == "unknown"
    assert payload.to_context().product_name is None


def test_create_form_is_strict_and_rejects_unknown_context() -> None:
    with pytest.raises(ValidationError):
        CreateUGCReviewForm(
            asset_id=uuid4(),
            asset_version_id=uuid4(),
            unsupported_mode="strict",
        )


def test_recommendation_action_rejects_unknown_action() -> None:
    with pytest.raises(ValidationError):
        RecordUGCRecommendationActionRequest(action="blocked")


def test_action_reason_must_not_be_blank() -> None:
    with pytest.raises(ValidationError):
        RecordUGCRecommendationActionRequest(action="accepted", reason="   ")
