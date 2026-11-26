from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import ValidationError

from viraldy.modules.tiktok_commercial_content.mapper import map_ad_result, redact_media_urls
from viraldy.modules.tiktok_commercial_content.media_stream import (
    _valid_range_header,
    _validate_provider_url,
)
from viraldy.modules.tiktok_commercial_content.provider import (
    TikTokTokenProvider,
    decode_cursor,
    encode_cursor,
    stable_query_hash,
)
from viraldy.modules.tiktok_commercial_content.schemas import AdSearchRequest, DateRange
from viraldy.modules.tiktok_commercial_content.workflow import _validate_public_payload
from viraldy.modules.tiktok_commercial_content.workflow_schemas import (
    AnalyticsEventRequest,
    SellerResponseRequest,
)
from viraldy.platform.config.settings import Settings
from viraldy.shared.errors.base import AppError


def test_ad_mapping_normalizes_provider_aliases_and_unknowns() -> None:
    result = map_ad_result(
        uuid4(),
        {
            "ad": {"id": "42", "videos": [{"url": "https://cdn.example/video.mp4"}]},
            "advertiser": {
                "buisness_id": "business-7",
                "business_name": "Example advertiser",
                "paid_by": "Example advertiser",
            },
        },
    )

    assert result.provider_entity_id == "42"
    assert result.advertiser is not None
    assert result.advertiser.business_id == "business-7"
    assert result.advertiser.paid_for_by == "Example advertiser"
    assert result.ad.title is None
    assert result.market_signal.label == "MARKET_OBSERVED"


def test_ad_mapping_preserves_null_provider_fields_and_normalized_aliases() -> None:
    result = map_ad_result(
        uuid4(),
        {
            "ad": {"id": "43", "title": "Public signal"},
            "advertiser": {"business_id": "business-8", "paid_for_by": "Brand"},
        },
    )

    assert result.ad.title == "Public signal"
    assert result.ad.call_to_action is None
    assert result.advertiser is not None
    assert result.advertiser.paid_for_by == "Brand"


def test_public_ad_mapping_redacts_signed_media_urls_but_keeps_counts() -> None:
    result = map_ad_result(
        uuid4(),
        {
            "ad": {
                "id": "44",
                "videos": [{"url": "https://v77.tiktokcdn.com/signed-video"}],
                "image_urls": ["https://p16.tiktokcdn.com/signed-image"],
                "download_url": "https://v77.tiktokcdn.com/download",
            }
        },
    )

    public_result = redact_media_urls(result)

    assert public_result.ad.videos[0].url is None
    assert public_result.ad.image_urls == []
    assert public_result.ad.image_count == 1
    assert public_result.ad.download_url is None


def test_search_validation_enforces_date_and_page_limits() -> None:
    with pytest.raises(ValidationError):
        DateRange(min="2022-09-30", max="2022-10-01")
    with pytest.raises(ValidationError):
        AdSearchRequest(search_term="x" * 51)
    with pytest.raises(ValidationError):
        AdSearchRequest(max_count=51)
    with pytest.raises(ValidationError):
        AdSearchRequest(country_code="U1")
    with pytest.raises(ValidationError, match="EU/EEA"):
        AdSearchRequest(
            country_code="US",
            date_range={"min": "2023-01-01", "max": "2023-01-02"},
        )
    with pytest.raises(ValidationError):
        AdSearchRequest(date_range={"min": "2023-01-02", "max": "2023-01-01"})


def test_cursor_is_bound_to_normalized_query() -> None:
    query_hash = stable_query_hash({"country_code": "US", "max_count": 20})
    cursor = encode_cursor(query_hash, "opaque-search-id")

    assert decode_cursor(cursor) == (query_hash, "opaque-search-id")
    assert stable_query_hash({"max_count": 20, "country_code": "US"}) == query_hash


def test_direct_stream_validates_provider_hosts_and_ranges() -> None:
    _validate_provider_url("https://v77.tiktokcdn.com/video.mp4")
    _validate_provider_url("https://v16.tiktokv.com/image.jpg")

    with pytest.raises(AppError, match="host is not allowed"):
        _validate_provider_url("https://example.com/video.mp4")

    assert _valid_range_header("bytes=0-1023")
    assert _valid_range_header("bytes=1024-")
    assert not _valid_range_header("bytes=0-1,4-5")
    assert not _valid_range_header("items=0-1023")


@pytest.mark.asyncio
@pytest.mark.parametrize("empty_value", [None, "", "   "])
async def test_token_provider_fails_without_credentials_without_leaking_values(
    empty_value: str | None, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = Settings(
        _env_file=None,
        tiktok_commercial_client_key=empty_value,
        tiktok_commercial_client_secret=empty_value,
    )
    provider = TikTokTokenProvider(settings)

    async def unexpected_cache_read() -> None:
        pytest.fail("Missing credentials must fail before cache or network access.")

    monkeypatch.setattr(provider, "_redis_get", unexpected_cache_read)

    with pytest.raises(AppError, match="credentials are not configured"):
        await provider.get()


def test_market_snapshot_rejects_private_and_sensitive_fields() -> None:
    with pytest.raises(AppError, match="workspace-private"):
        _validate_public_payload({"workspace_id": "private", "pattern": "most observed"})
    with pytest.raises(AppError, match="workspace-private"):
        _validate_public_payload({"seller_notes": "do not publish", "pattern": "hook"})


def test_seller_decisions_are_normalized_and_analytics_is_whitelisted() -> None:
    request = SellerResponseRequest(
        response="modified", action="FIX", feedback="Reshoot the opening"
    )
    assert request.action == "FIX"
    assert (
        AnalyticsEventRequest(event_type="seller_decision_recorded").event_type
        == "seller_decision_recorded"
    )
    with pytest.raises(ValidationError):
        AnalyticsEventRequest(event_type="checkout_started")


def test_analytics_rejects_media_and_transcript_values() -> None:
    with pytest.raises(AppError, match="restricted value"):
        from viraldy.modules.tiktok_commercial_content.workflow import (
            _validate_analytics_payload,
        )

        _validate_analytics_payload({"transcript": "private audio"})
