from __future__ import annotations

from uuid import uuid4

from viraldy.modules.assets.models import AssetModel
from viraldy.modules.tiktok_commercial_content.family_engine import compare_assets


def _asset(*, scope: str = "MARKET", metadata: dict[str, object] | None = None) -> AssetModel:
    return AssetModel(
        id=uuid4(),
        workspace_id=None,
        asset_type="reference",
        status="metadata_only",
        metadata_json=metadata or {},
        library_scope=scope,
    )


def test_family_matching_uses_multiple_interpretable_signals() -> None:
    left = _asset(
        metadata={
            "source_url": "https://cdn.example/shared.mp4",
            "advertiser_business_id": "advertiser-1",
            "title": "Three ways to style this bag",
        }
    )
    right = _asset(
        metadata={
            "source_url": "https://cdn.example/shared.mp4",
            "advertiser_business_id": "advertiser-1",
            "title": "Three ways to style this bag today",
        }
    )

    decision = compare_assets(left, right)

    assert decision is not None
    assert decision.relationship == "SAME_FOOTAGE"
    assert decision.confidence == "medium"
    assert decision.signals["shared_media_url"] is True
    assert decision.signals["advertiser"] == "same"


def test_family_matching_does_not_merge_unrelated_assets() -> None:
    left = _asset(metadata={"title": "Kitchen organizer demo"})
    right = _asset(metadata={"title": "Running shoes review"})

    assert compare_assets(left, right) is None


def test_family_matching_keeps_market_and_workspace_scopes_separate() -> None:
    left = _asset(scope="MARKET", metadata={"source_url": "https://cdn.example/a.mp4"})
    right = _asset(scope="WORKSPACE", metadata={"source_url": "https://cdn.example/a.mp4"})

    assert compare_assets(left, right) is None
