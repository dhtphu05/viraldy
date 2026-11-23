from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any
from uuid import UUID

import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession

from viraldy.modules.assets.repository import AssetRepository
from viraldy.modules.jobs.public import request_mvp_job
from viraldy.modules.product_events.public import ProductEventPublisher
from viraldy.modules.products.public import ProductQueries
from viraldy.modules.reference_boards.public import ReferenceBoardRepository
from viraldy.modules.references.repository import ReferenceRepository
from viraldy.modules.tiktok_commercial_content.mapper import (
    PROVIDER,
    map_ad_result,
    map_commercial_content,
    redact_media_urls,
)
from viraldy.modules.tiktok_commercial_content.provider import (
    TikTokCommercialContentClient,
    decode_cursor,
    encode_cursor,
    stable_query_hash,
)
from viraldy.modules.tiktok_commercial_content.repository import TikTokCommercialRepository
from viraldy.modules.tiktok_commercial_content.schemas import (
    AdReportRequest,
    AdSearchRequest,
    AdvertiserSearchRequest,
    CommercialContentResult,
    CommercialContentSearchRequest,
    CommercialContentSearchResponse,
    CursorPage,
    SaveReferenceRequest,
    SaveReferenceResponse,
    TikTokAdResult,
    TikTokAdSearchResponse,
    TikTokAdvertiserResult,
    TikTokAdvertiserSearchResponse,
)
from viraldy.platform.config.settings import Settings
from viraldy.shared.errors.base import AppError, NotFoundError

AD_FIELDS = ",".join(
    [
        "ad.id",
        "ad.first_shown_date",
        "ad.last_shown_date",
        "ad.status",
        "ad.status_statement",
        "ad.videos",
        "ad.image_urls",
        "ad.reach",
        "advertiser.business_id",
        "advertiser.business_name",
        "advertiser.paid_for_by",
    ]
)
DETAIL_FIELDS = ",".join(
    [
        "ad.id",
        "ad.first_shown_date",
        "ad.last_shown_date",
        "ad.status",
        "ad.status_statement",
        "ad.videos",
        "ad.image_urls",
        "ad.reach",
        "ad.title",
        "ad.external_url",
        "ad.download_url",
        "ad.call_to_action",
        "ad.advertising_objective",
        "advertiser.business_id",
        "advertiser.business_name",
        "advertiser.paid_for_by",
        "advertiser.follower_count",
        "advertiser.avatar_url",
        "advertiser.profile_url",
        "ad_group.targeting_info",
    ]
)
ADVERTISER_FIELDS = "business_id,business_name,country_code"
COMMERCIAL_CONTENT_FIELDS = "id,create_date,label,brand_names,creator,videos"


class TikTokCommercialContentService:
    def __init__(
        self, session: AsyncSession, settings: Settings, request_id: str | None = None
    ) -> None:
        self._session = session
        self._settings = settings
        self._client = TikTokCommercialContentClient(settings, request_id=request_id)
        self._sources = TikTokCommercialRepository(session)

    def ensure_enabled(self) -> None:
        if not (
            self._settings.tiktok_commercial_api_enabled
            and self._settings.tiktok_market_intelligence
        ):
            raise AppError(
                "TIKTOK_COMMERCIAL_DISABLED",
                "TikTok Commercial Content API is disabled by configuration or rollout flag.",
                status_code=503,
            )

    async def search_ads(self, request: AdSearchRequest) -> TikTokAdSearchResponse:
        self.ensure_enabled()
        body = _ad_body(request)
        query_hash = stable_query_hash(body)
        search_id = None
        if request.cursor:
            cursor_hash, search_id = decode_cursor(request.cursor)
            if cursor_hash != query_hash:
                raise AppError(
                    "TIKTOK_CURSOR_STALE", "TikTok search cursor does not match the filters."
                )
            body["search_id"] = search_id
        cached = await self._cached_response("ads", {**body, "max_count": request.max_count})
        if cached is not None and not request.cursor:
            return _redact_search_response(TikTokAdSearchResponse.model_validate(cached))
        data = await self._client.query_ads(body, AD_FIELDS)
        results: list[TikTokAdResult] = []
        for item in _list(data.get("ads")):
            raw = _object(item)
            raw_ad = _object(raw.get("ad"))
            entity_id = str(raw_ad.get("id") or "")
            if not entity_id:
                continue
            record = await self._sources.upsert_source_record(
                workspace_id=None,
                entity_type="ad",
                entity_id=entity_id,
                raw_payload=raw,
                fetched_at=_now(),
                request_context=_safe_context(body),
                provider_log_id=_response_log_id(data),
            )
            mapped = await self._ensure_market_asset(record.id, raw)
            results.append(mapped)
        response = TikTokAdSearchResponse(
            results=[redact_media_urls(result) for result in results],
            page=CursorPage(
                has_more=bool(data.get("has_more")),
                next_cursor=(
                    encode_cursor(query_hash, str(data["search_id"]))
                    if data.get("has_more") and data.get("search_id")
                    else None
                ),
            ),
        )
        await self._cache_response(
            "ads", {**body, "max_count": request.max_count}, response.model_dump(mode="json")
        )
        await self._session.commit()
        return response

    async def search_advertisers(
        self, request: AdvertiserSearchRequest
    ) -> TikTokAdvertiserSearchResponse:
        self.ensure_enabled()
        body = {"search_term": request.search_term, "max_count": request.max_count}
        cached = await self._cached_response("advertisers", body)
        if cached is not None:
            return TikTokAdvertiserSearchResponse.model_validate(cached)
        data = await self._client.query_advertisers(body, ADVERTISER_FIELDS)
        results: list[TikTokAdvertiserResult] = []
        for raw in _list(data.get("advertisers")):
            item = _object(raw)
            business_id = str(item.get("business_id") or "")
            if not business_id:
                continue
            await self._sources.upsert_source_record(
                workspace_id=None,
                entity_type="advertiser",
                entity_id=business_id,
                raw_payload=item,
                fetched_at=_now(),
                request_context={"search_term": request.search_term},
                provider_log_id=_response_log_id(data),
            )
            results.append(
                TikTokAdvertiserResult(
                    business_id=business_id,
                    business_name=item.get("business_name")
                    if isinstance(item.get("business_name"), str)
                    else None,
                    country_code=item.get("country_code")
                    if isinstance(item.get("country_code"), str)
                    else None,
                )
            )
        await self._session.commit()
        response = TikTokAdvertiserSearchResponse(results=results)
        await self._cache_response("advertisers", body, response.model_dump(mode="json"))
        return response

    async def get_ad_detail(self, source_id: UUID) -> TikTokAdResult:
        self.ensure_enabled()
        return redact_media_urls(await self._get_ad_detail_raw(source_id))

    async def _get_ad_detail_raw(self, source_id: UUID) -> TikTokAdResult:
        source = await self._sources.get_source_record(source_id)
        if source is None or source.provider != PROVIDER or source.provider_entity_type != "ad":
            raise NotFoundError("TIKTOK_SOURCE_NOT_FOUND", "TikTok source record was not found.")
        data = await self._client.get_ad_detail(source.provider_entity_id, DETAIL_FIELDS)
        raw = {
            "ad": _object(data.get("ad")),
            "advertiser": _object(data.get("advertiser")),
            "ad_group": _object(data.get("ad_group")),
        }
        source = await self._sources.upsert_source_record(
            workspace_id=None,
            entity_type="ad",
            entity_id=source.provider_entity_id,
            raw_payload=raw,
            fetched_at=_now(),
            request_context={"operation": "detail"},
            provider_log_id=_response_log_id(data),
        )
        await self._session.commit()
        return await self._ensure_market_asset(source.id, raw)

    async def get_media_url(self, source_id: UUID, media_index: int = 0) -> tuple[str, str]:
        self.ensure_enabled()
        result = await self._get_ad_detail_raw(source_id)
        media_url, media_type = _select_media(result, media_index)
        if media_url is None or media_type is None:
            raise NotFoundError("TIKTOK_MEDIA_NOT_FOUND", "This TikTok creative has no media.")
        return media_url, media_type

    async def search_commercial_content(
        self, request: CommercialContentSearchRequest
    ) -> CommercialContentSearchResponse:
        self.ensure_enabled()
        body = _commercial_content_body(request)
        query_hash = stable_query_hash(body)
        if request.cursor:
            cursor_hash, search_id = decode_cursor(request.cursor)
            if cursor_hash != query_hash:
                raise AppError(
                    "TIKTOK_CURSOR_STALE", "TikTok search cursor does not match the filters."
                )
            body["search_id"] = search_id
        data = await self._client.query_commercial_content(body, COMMERCIAL_CONTENT_FIELDS)
        results: list[CommercialContentResult] = []
        for item in _list(data.get("commercial_contents")):
            raw = _object(item)
            entity_id = str(raw.get("id") or "")
            if not entity_id:
                continue
            source = await self._sources.upsert_source_record(
                workspace_id=None,
                entity_type="commercial_content",
                entity_id=entity_id,
                raw_payload=raw,
                fetched_at=_now(),
                request_context=_safe_context(body),
                provider_log_id=_response_log_id(data),
            )
            results.append(map_commercial_content(source.id, raw))
        await self._session.commit()
        return CommercialContentSearchResponse(
            results=results,
            page=CursorPage(
                has_more=bool(data.get("has_more")),
                next_cursor=(
                    encode_cursor(query_hash, str(data["search_id"]))
                    if data.get("has_more") and data.get("search_id")
                    else None
                ),
            ),
        )

    async def get_ad_report(self, request: AdReportRequest) -> dict[str, object]:
        self.ensure_enabled()
        filters: dict[str, object] = {
            "ad_published_date_range": _date_range(request.date_range.min, request.date_range.max),
        }
        if request.country_code:
            filters["country_code"] = request.country_code.upper()
        if request.advertiser_business_ids:
            filters["advertiser_business_ids"] = request.advertiser_business_ids
        data = await self._client.get_ad_report(
            {"filters": filters}, "count_time_series_by_country"
        )
        return {"data": data, "scope": "public_market", "provider": PROVIDER}

    async def save_reference(
        self, workspace_id: UUID, user_id: UUID, source_id: UUID, request: SaveReferenceRequest
    ) -> SaveReferenceResponse:
        self.ensure_enabled()
        source = await self._sources.get_source_record(source_id)
        if source is None or source.provider_entity_type != "ad":
            raise NotFoundError("TIKTOK_SOURCE_NOT_FOUND", "TikTok source record was not found.")
        if (
            await ReferenceBoardRepository(self._session).get(workspace_id, request.board_id)
            is None
        ):
            raise NotFoundError("REFERENCE_BOARD_NOT_FOUND", "Reference board was not found.")
        if request.product_id and not await ProductQueries(self._session).exists_in_workspace(
            workspace_id, request.product_id
        ):
            raise NotFoundError("PRODUCT_NOT_FOUND", "Product was not found.")
        detail = await self._get_ad_detail_raw(source.id)
        media_url, media_type = _select_media(detail)
        metadata_only = (
            not self._settings.tiktok_commercial_media_persistence_allowed
            or media_url is None
            or media_type is None
        )
        filename = f"tiktok-{detail.ad.id}.{'mp4' if media_type == 'video' else 'jpg'}"
        asset, version = await AssetRepository(self._session).get_or_create_market_asset(
            source_provider=PROVIDER,
            source_entity_type="ad",
            source_entity_id=detail.provider_entity_id,
            asset_type="reference",
            filename=filename,
            declared_mime_type="video/mp4" if media_type == "video" else "image/jpeg",
            media_type=media_type,
            metadata_json={
                "source_provider": PROVIDER,
                "source_record_id": str(source.id),
                "provider_entity_id": detail.provider_entity_id,
                "media_type": media_type or "metadata_only",
                "compliance_state": "metadata_only"
                if metadata_only
                else "media_persistence_approved",
                "market_signal": detail.market_signal.model_dump(mode="json"),
            },
        )
        asset.processing_status = "NOT_ANALYZED"
        await self._sources.link_asset(
            asset_id=asset.id,
            entity_type="ad",
            entity_id=detail.provider_entity_id,
            source_url=media_url or detail.ad.external_url,
            source_metadata=detail.model_dump(mode="json"),
            seen_at=_now(),
        )
        reference_repository = ReferenceRepository(self._session)
        reference = await reference_repository.get_by_asset(workspace_id, asset.id)
        if reference is None:
            reference = await reference_repository.create(
                workspace_id=workspace_id,
                user_id=user_id,
                board_id=request.board_id,
                asset_id=asset.id,
                product_id=request.product_id,
                source_platform="TikTok Official",
                source_url=detail.ad.external_url,
                title=detail.ad.title or f"TikTok ad {detail.ad.id}",
                notes=request.notes,
            )
        elif request.product_id is not None and reference.product_id is None:
            reference.product_id = request.product_id
        job = None
        if metadata_only:
            asset.status = "metadata_only"
            version.validation_status = "metadata_only"
        else:
            job = await request_mvp_job(
                self._session,
                workspace_id,
                "asset",
                asset.id,
                "tiktok_media_import",
                {
                    "asset_id": str(asset.id),
                    "asset_version_id": str(version.id),
                    "source_url": media_url,
                    "media_type": media_type,
                    "source_record_id": str(source.id),
                    "reference_id": str(reference.id),
                    "actor_user_id": str(user_id),
                },
                f"tiktok-save:{workspace_id}:{source.id}",
            )
        await ProductEventPublisher(self._session).record(
            event_type="tiktok_ad_saved_reference",
            workspace_id=workspace_id,
            actor_user_id=user_id,
            subject_type="reference",
            subject_id=reference.id,
            payload_json={
                "asset_id": str(asset.id),
                "source_id": str(source.id),
                "status": "metadata_only" if metadata_only else "importing",
            },
        )
        await self._session.commit()
        return SaveReferenceResponse(
            reference_id=reference.id,
            asset_id=asset.id,
            asset_version_id=version.id,
            import_job_id=job.id if job else None,
            media_type=media_type,
            status="metadata_only" if metadata_only else "importing",
        )

    async def _ensure_market_asset(self, source_id: UUID, raw: dict[str, Any]) -> TikTokAdResult:
        mapped = map_ad_result(source_id, raw)
        media_type = "video" if mapped.ad.videos else "image" if mapped.ad.image_urls else None
        media_url = (
            mapped.ad.videos[0].url
            if mapped.ad.videos
            else (mapped.ad.image_urls[0] if mapped.ad.image_urls else mapped.ad.external_url)
        )
        asset, _ = await AssetRepository(self._session).get_or_create_market_asset(
            source_provider=PROVIDER,
            source_entity_type="ad",
            source_entity_id=mapped.provider_entity_id,
            asset_type="reference",
            filename=(
                f"tiktok-{mapped.provider_entity_id}."
                f"{'mp4' if media_type == 'video' else 'jpg'}"
            ),
            declared_mime_type="video/mp4" if media_type == "video" else "image/jpeg",
            media_type=media_type,
            metadata_json={
                "source_record_id": str(source_id),
                "source_url": media_url,
                "title": mapped.ad.title,
                "advertiser_business_id": (
                    mapped.advertiser.business_id if mapped.advertiser else None
                ),
                "market_signal": mapped.market_signal.model_dump(mode="json"),
            },
        )
        await self._sources.link_asset(
            asset_id=asset.id,
            entity_type="ad",
            entity_id=mapped.provider_entity_id,
            source_url=media_url,
            source_metadata=mapped.model_dump(mode="json"),
            seen_at=_now(),
        )
        media_state = (
            "READY"
            if asset.status in {"uploaded", "ready"}
            else "DIRECT_STREAM_AVAILABLE"
            if self._settings.tiktok_commercial_direct_stream_allowed and media_type
            else "AVAILABLE_ON_SAVE"
            if self._settings.tiktok_commercial_media_persistence_allowed and media_type
            else "METADATA_ONLY"
        )
        return mapped.model_copy(
            update={
                "asset_id": asset.id,
                "intelligence_status": asset.processing_status,
                "media_state": media_state,
            }
        )

    async def _cached_response(
        self, operation: str, context: dict[str, object]
    ) -> dict[str, object] | None:
        key = f"viraldy:tiktok-commercial:search:{operation}:{stable_query_hash(context)}"
        try:
            client = redis.from_url(  # type: ignore[no-untyped-call]
                self._settings.redis_url, decode_responses=True
            )
            value = await client.get(key)
            await client.aclose()
            if value:
                parsed = json.loads(value)
                return parsed if isinstance(parsed, dict) else None
        except Exception:
            return None
        return None

    async def _cache_response(
        self, operation: str, context: dict[str, object], payload: dict[str, object]
    ) -> None:
        key = f"viraldy:tiktok-commercial:search:{operation}:{stable_query_hash(context)}"
        try:
            client = redis.from_url(  # type: ignore[no-untyped-call]
                self._settings.redis_url, decode_responses=True
            )
            await client.set(
                key, json.dumps(payload), ex=self._settings.tiktok_commercial_cache_ttl_seconds
            )
            await client.aclose()
        except Exception:
            return


def _ad_body(request: AdSearchRequest) -> dict[str, object]:
    body: dict[str, object] = {"max_count": request.max_count}
    if request.search_term:
        body["search_term"] = request.search_term.strip()
        body["search_type"] = request.search_type
    filters: dict[str, object] = {
        "ad_published_date_range": _date_range(
            request.date_range.min,
            request.date_range.max,
        )
    }
    if request.country_code:
        filters["country_code"] = request.country_code
    if request.advertiser_business_ids:
        filters["advertiser_business_ids"] = request.advertiser_business_ids
    if request.reach_range:
        filters["unique_users_seen_size_range"] = request.reach_range.model_dump(exclude_none=True)
    body["filters"] = filters
    return body


def _commercial_content_body(request: CommercialContentSearchRequest) -> dict[str, object]:
    body: dict[str, object] = {"max_count": request.max_count}
    filters: dict[str, object] = {
        "content_published_date_range": _date_range(
            request.date_range.min,
            request.date_range.max,
        )
    }
    if request.creator_country_code:
        filters["creator_country_code"] = request.creator_country_code.upper()
    if request.creator_usernames:
        filters["creator_usernames"] = request.creator_usernames
    body["filters"] = filters
    return body


def _date_range(start: date, end: date) -> dict[str, str]:
    return {"min": start.strftime("%Y%m%d"), "max": end.strftime("%Y%m%d")}


def _select_media(result: TikTokAdResult, media_index: int = 0) -> tuple[str | None, str | None]:
    if media_index < 0:
        return None, None
    if media_index < len(result.ad.videos):
        return result.ad.videos[media_index].url, "video"
    image_index = media_index - len(result.ad.videos)
    if image_index < len(result.ad.image_urls):
        return result.ad.image_urls[image_index], "image"
    return None, None


def _redact_search_response(response: TikTokAdSearchResponse) -> TikTokAdSearchResponse:
    return response.model_copy(
        update={"results": [redact_media_urls(result) for result in response.results]}
    )


def _list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def _object(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_context(payload: dict[str, object]) -> dict[str, object]:
    return {key: value for key, value in payload.items() if key not in {"search_id"}}


def _response_log_id(payload: dict[str, object]) -> str | None:
    internal = payload.get("__provider_log_id")
    if isinstance(internal, str):
        return internal
    error = _object(payload.get("error"))
    value = error.get("log_id")
    return value if isinstance(value, str) else None


def _now() -> datetime:
    from viraldy.platform.clock.utc import utc_now

    return utc_now()
