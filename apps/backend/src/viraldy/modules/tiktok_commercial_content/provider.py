from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import time
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import httpx
import redis.asyncio as redis
import structlog

from viraldy.platform.config.settings import Settings
from viraldy.shared.errors.base import AppError

logger = structlog.get_logger(__name__)

TIKTOK_API_BASE_URL = "https://open.tiktokapis.com"
TIKTOK_TOKEN_URL = f"{TIKTOK_API_BASE_URL}/v2/oauth/token/"
_TOKEN_CACHE_KEY = "viraldy:tiktok-commercial:client-token"  # noqa: S105


@dataclass(frozen=True, slots=True)
class ClientToken:
    value: str
    expires_at: float


_local_token: ClientToken | None = None
_token_lock = asyncio.Lock()


class TikTokTokenProvider:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def get(self, *, force_refresh: bool = False) -> str:
        global _local_token
        key = self._settings.tiktok_commercial_client_key
        secret = self._settings.tiktok_commercial_client_secret
        if (
            key is None
            or secret is None
            or not key.get_secret_value().strip()
            or not secret.get_secret_value().strip()
        ):
            raise AppError(
                "TIKTOK_COMMERCIAL_NOT_CONFIGURED",
                "TikTok Commercial Content API credentials are not configured.",
                status_code=503,
            )
        if not force_refresh and _local_token and _local_token.expires_at > time.time():
            return _local_token.value
        async with _token_lock:
            if not force_refresh and _local_token and _local_token.expires_at > time.time():
                return _local_token.value
            if not force_refresh:
                cached = await self._redis_get()
                if cached is not None:
                    _local_token = cached
                    return cached.value
            try:
                async with httpx.AsyncClient(
                    timeout=self._settings.tiktok_commercial_request_timeout_seconds
                ) as client:
                    response = await client.post(
                        TIKTOK_TOKEN_URL,
                        headers={
                            "Content-Type": "application/x-www-form-urlencoded",
                            "Cache-Control": "no-cache",
                        },
                        data={
                            "client_key": key.get_secret_value(),
                            "client_secret": secret.get_secret_value(),
                            "grant_type": "client_credentials",
                        },
                    )
            except httpx.TimeoutException as exc:
                raise AppError(
                    "TIKTOK_COMMERCIAL_TIMEOUT", "TikTok token request timed out.", 503
                ) from exc
            except httpx.HTTPError as exc:
                raise AppError(
                    "TIKTOK_COMMERCIAL_AUTH_FAILED", "TikTok token request failed.", 503
                ) from exc
            payload = _json_object(response, "TIKTOK_COMMERCIAL_AUTH_FAILED")
            if response.status_code >= 400 or not isinstance(payload.get("access_token"), str):
                raise AppError(
                    "TIKTOK_COMMERCIAL_AUTH_FAILED",
                    "TikTok rejected the Commercial Content API credentials.",
                    status_code=502,
                    details={"log_id": _log_id(payload)},
                )
            expires_in = payload.get("expires_in")
            if not isinstance(expires_in, int) or expires_in <= 0:
                raise AppError(
                    "TIKTOK_COMMERCIAL_AUTH_INVALID",
                    "TikTok returned an invalid token expiry.",
                    502,
                )
            token = ClientToken(
                value=payload["access_token"],
                expires_at=time.time() + max(30, expires_in - 60),
            )
            _local_token = token
            await self._redis_set(token, expires_in)
            return token.value

    async def _redis_get(self) -> ClientToken | None:
        try:
            client = redis.from_url(  # type: ignore[no-untyped-call]
                self._settings.redis_url, decode_responses=True
            )
            value = await client.get(_TOKEN_CACHE_KEY)
            await client.aclose()
        except Exception:
            return None
        if not value:
            return None
        try:
            payload = json.loads(value)
            token = payload["token"]
            expires_at = float(payload["expires_at"])
            if isinstance(token, str) and expires_at > time.time():
                return ClientToken(token, expires_at)
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            return None
        return None

    async def _redis_set(self, token: ClientToken, expires_in: int) -> None:
        try:
            client = redis.from_url(  # type: ignore[no-untyped-call]
                self._settings.redis_url, decode_responses=True
            )
            ttl = max(30, min(expires_in - 60, expires_in))
            await client.set(
                _TOKEN_CACHE_KEY,
                json.dumps({"token": token.value, "expires_at": token.expires_at}),
                ex=ttl,
            )
            await client.aclose()
        except Exception:
            logger.debug("tiktok_token_cache_unavailable")


class TikTokCommercialContentClient:
    def __init__(self, settings: Settings, request_id: str | None = None) -> None:
        self._settings = settings
        self._token_provider = TikTokTokenProvider(settings)
        self._request_id = request_id

    async def query_ads(self, body: Mapping[str, Any], fields: str) -> dict[str, Any]:
        return await self._post("/v2/research/adlib/ad/query/", body, fields)

    async def query_advertisers(self, body: Mapping[str, Any], fields: str) -> dict[str, Any]:
        return await self._post("/v2/research/adlib/advertiser/query/", body, fields)

    async def get_ad_detail(self, ad_id: str, fields: str) -> dict[str, Any]:
        return await self._post("/v2/research/adlib/ad/detail/", {"ad_id": int(ad_id)}, fields)

    async def get_ad_report(self, body: Mapping[str, Any], fields: str) -> dict[str, Any]:
        return await self._post("/v2/research/adlib/ad/report/", body, fields)

    async def query_commercial_content(
        self, body: Mapping[str, Any], fields: str
    ) -> dict[str, Any]:
        return await self._post("/v2/research/adlib/commercial_content/query/", body, fields)

    async def _post(self, path: str, body: Mapping[str, Any], fields: str) -> dict[str, Any]:
        token = await self._token_provider.get()
        for attempt in range(self._settings.tiktok_commercial_max_retries + 1):
            try:
                async with httpx.AsyncClient(
                    timeout=self._settings.tiktok_commercial_request_timeout_seconds
                ) as client:
                    response = await client.post(
                        f"{TIKTOK_API_BASE_URL}{path}",
                        params={"fields": fields},
                        headers=self._headers(token),
                        json=dict(body),
                    )
            except httpx.TimeoutException as exc:
                if attempt >= self._settings.tiktok_commercial_max_retries:
                    raise AppError(
                        "TIKTOK_COMMERCIAL_TIMEOUT", "TikTok request timed out.", 503
                    ) from exc
                await asyncio.sleep(2**attempt)
                continue
            except httpx.HTTPError as exc:
                if attempt >= self._settings.tiktok_commercial_max_retries:
                    raise AppError(
                        "TIKTOK_COMMERCIAL_PROVIDER_ERROR", "TikTok request failed.", 502
                    ) from exc
                await asyncio.sleep(2**attempt)
                continue
            payload = _json_object(response, "TIKTOK_COMMERCIAL_PROVIDER_ERROR")
            error = payload.get("error")
            error_code = error.get("code") if isinstance(error, dict) else None
            status_code = response.status_code
            if status_code == 401:
                token = await self._token_provider.get(force_refresh=True)
                if attempt == 0:
                    continue
            retryable = status_code == 429 or status_code >= 500
            if retryable and attempt < self._settings.tiktok_commercial_max_retries:
                await asyncio.sleep(_retry_delay(response, attempt))
                continue
            if status_code >= 400 or (error_code and error_code != "ok"):
                raise AppError(
                    "TIKTOK_COMMERCIAL_PROVIDER_ERROR",
                    "TikTok Commercial Content API request failed.",
                    status_code=502 if status_code >= 500 else 400,
                    details={"log_id": _log_id(error), "provider_code": error_code},
                )
            data = payload.get("data")
            if not isinstance(data, dict):
                raise AppError(
                    "TIKTOK_COMMERCIAL_RESPONSE_INVALID", "TikTok response data is invalid.", 502
                )
            error_payload = payload.get("error")
            provider_log_id = _log_id(error_payload)
            if provider_log_id:
                data = {**data, "__provider_log_id": provider_log_id}
            return data
        raise AppError("TIKTOK_COMMERCIAL_PROVIDER_ERROR", "TikTok request failed.", 502)

    def _headers(self, token: str) -> dict[str, str]:
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        if self._request_id:
            headers["X-Request-ID"] = self._request_id
        return headers


def stable_query_hash(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


def encode_cursor(query_hash: str, search_id: str) -> str:
    payload = json.dumps({"query_hash": query_hash, "search_id": search_id}, separators=(",", ":"))
    return base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")


def decode_cursor(cursor: str) -> tuple[str, str]:
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded).decode())
        query_hash = payload["query_hash"]
        search_id = payload["search_id"]
        if not isinstance(query_hash, str) or not isinstance(search_id, str):
            raise ValueError
        return query_hash, search_id
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise AppError("TIKTOK_CURSOR_INVALID", "TikTok search cursor is invalid.") from exc


def _json_object(response: httpx.Response, code: str) -> dict[str, Any]:
    try:
        payload = response.json()
    except ValueError as exc:
        raise AppError(code, "TikTok returned invalid JSON.", 502) from exc
    if not isinstance(payload, dict):
        raise AppError(code, "TikTok returned an invalid response.", 502)
    return payload


def _log_id(payload: object) -> str | None:
    if isinstance(payload, dict) and isinstance(payload.get("log_id"), str):
        return str(payload["log_id"])
    return None


def _retry_delay(response: httpx.Response, attempt: int) -> float:
    retry_after = response.headers.get("retry-after")
    if retry_after and retry_after.isdigit():
        return min(float(retry_after), 30)
    return min(float(2**attempt), 30)
