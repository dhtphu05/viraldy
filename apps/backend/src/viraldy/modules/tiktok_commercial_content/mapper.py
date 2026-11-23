from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from viraldy.modules.tiktok_commercial_content.schemas import (
    CommercialContentResult,
    MarketSignal,
    TikTokAd,
    TikTokAdResult,
    TikTokAdvertiser,
    TikTokMedia,
)

PROVIDER = "tiktok_commercial_content"
SCHEMA_VERSION = "tiktok_commercial_content_v1"


def map_ad_result(source_id: UUID, payload: dict[str, Any]) -> TikTokAdResult:
    raw_ad = _object(payload.get("ad"))
    raw_advertiser = _object(payload.get("advertiser"))
    ad_id = str(raw_ad.get("id") or payload.get("ad_id") or "")
    image_urls = _strings(raw_ad.get("image_urls"))
    ad = TikTokAd(
        id=ad_id,
        first_shown_date=_parse_date(raw_ad.get("first_shown_date")),
        last_shown_date=_parse_date(raw_ad.get("last_shown_date")),
        status=_string(raw_ad.get("status")),
        status_statement=_string(raw_ad.get("status_statement")),
        videos=[TikTokMedia(url=url, media_type="video") for url in _urls(raw_ad.get("videos"))],
        image_urls=image_urls,
        image_count=len(image_urls),
        reach=_reach(raw_ad.get("reach")),
        title=_string(raw_ad.get("title")),
        external_url=_string(raw_ad.get("external_url")),
        download_url=_string(raw_ad.get("download_url")),
        call_to_action=_string(raw_ad.get("call_to_action")),
        advertising_objective=_string(raw_ad.get("advertising_objective")),
        targeting_info=_object_or_none(
            raw_ad.get("targeting_info") or _object(payload.get("ad_group")).get("targeting_info")
        ),
        moderation_metadata=_object_or_none(raw_ad.get("moderation")),
    )
    advertiser = None
    if raw_advertiser:
        advertiser = TikTokAdvertiser(
            business_id=str(
                raw_advertiser.get("business_id") or raw_advertiser.get("buisness_id") or ""
            ),
            business_name=_string(raw_advertiser.get("business_name")),
            country_code=_string(raw_advertiser.get("country_code")),
            paid_for_by=_string(raw_advertiser.get("paid_for_by") or raw_advertiser.get("paid_by")),
            follower_count=_int(raw_advertiser.get("follower_count")),
            avatar_url=_string(raw_advertiser.get("avatar_url")),
            profile_url=_string(raw_advertiser.get("profile_url")),
        )
    return TikTokAdResult(
        source_id=source_id,
        provider_entity_id=ad_id,
        ad=ad,
        advertiser=advertiser,
        market_signal=MarketSignal(
            label="MARKET_OBSERVED",
            limitations=[
                "Public Commercial Content API metadata is not seller-private performance data.",
                "Reach and duration do not establish conversion, ROAS, or GMV impact.",
            ],
        ),
    )


def redact_media_urls(result: TikTokAdResult) -> TikTokAdResult:
    """Keep media counts while preventing short-lived provider URLs leaving the server."""
    return result.model_copy(
        deep=True,
        update={
            "ad": result.ad.model_copy(
                update={
                    "videos": [
                        media.model_copy(update={"url": None}) for media in result.ad.videos
                    ],
                    "image_urls": [],
                    "download_url": None,
                }
            )
        },
    )


def map_commercial_content(source_id: UUID, payload: dict[str, Any]) -> CommercialContentResult:
    raw = payload
    video = _object(raw.get("videos"))
    return CommercialContentResult(
        source_id=source_id,
        provider_entity_id=str(raw.get("id") or ""),
        create_date=_parse_date(raw.get("create_date")),
        label=_string(raw.get("label")),
        brand_names=_strings(raw.get("brand_names")),
        creator_username=_string(_object(raw.get("creator")).get("username"))
        or _string(raw.get("creator_username")),
        video_id=_string(video.get("id")) or _string(raw.get("video_id")),
        video_status=_string(video.get("status")) or _string(raw.get("video_status")),
        video_url=_string(video.get("url")) or _string(raw.get("video_url")),
        cover_image_url=_string(video.get("cover_image_url"))
        or _string(raw.get("cover_image_url")),
        market_signal=MarketSignal(
            label="MARKET_OBSERVED",
            limitations=[
                "Commercial-content history does not establish creator quality, fit, GMV, or ROAS."
            ],
        ),
    )


def source_payload(result: TikTokAdResult) -> dict[str, object]:
    return result.model_dump(mode="json", exclude={"source_id", "market_signal"})


def _object(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _object_or_none(value: object) -> dict[str, object] | None:
    value = _object(value)
    return value or None


def _string(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _int(value: object) -> int | None:
    return value if isinstance(value, int) else None


def _strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item]


def _urls(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    urls: list[str] = []
    for item in value:
        if isinstance(item, str):
            urls.append(item)
        elif isinstance(item, dict) and isinstance(item.get("url"), str):
            urls.append(item["url"])
    return urls


def _reach(value: object) -> str | None:
    if isinstance(value, dict):
        return _string(value.get("unique_users_seen") or value.get("unique_user_seen"))
    return _string(value)


def _parse_date(value: object) -> date | None:
    if isinstance(value, int):
        value = str(value)
    if not isinstance(value, str):
        return None
    try:
        return datetime.strptime(value, "%Y%m%d").date()
    except ValueError:
        return None
