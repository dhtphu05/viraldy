from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from urllib.parse import urlsplit

import httpx

from viraldy.shared.errors.base import AppError

_ALLOWED_HOST_SUFFIXES = (".tiktokcdn.com", ".tiktokv.com")
_RANGE_PREFIX = "bytes="


@dataclass(frozen=True, slots=True)
class MediaProxy:
    body: AsyncIterator[bytes]
    status_code: int
    headers: dict[str, str]
    media_type: str


async def open_tiktok_media_stream(
    url: str,
    *,
    range_header: str | None,
    timeout_seconds: float,
) -> MediaProxy:
    _validate_provider_url(url)
    request_headers = {"Accept": "video/*,image/*"}
    if range_header and _valid_range_header(range_header):
        request_headers["Range"] = range_header

    client = httpx.AsyncClient(timeout=timeout_seconds, follow_redirects=False)
    try:
        response = await client.send(
            client.build_request("GET", url, headers=request_headers), stream=True
        )
    except (httpx.TimeoutException, httpx.HTTPError) as exc:
        await client.aclose()
        raise AppError(
            "TIKTOK_MEDIA_STREAM_UNAVAILABLE", "TikTok media is unavailable.", 502
        ) from exc

    content_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
    if response.status_code >= 400 or not content_type.startswith(("video/", "image/")):
        await response.aclose()
        await client.aclose()
        raise AppError("TIKTOK_MEDIA_STREAM_UNAVAILABLE", "TikTok media is unavailable.", 502)

    headers = {
        key: value
        for key in ("content-length", "content-range", "accept-ranges")
        if (value := response.headers.get(key)) is not None
    }
    headers["cache-control"] = "private, no-store"

    async def body() -> AsyncIterator[bytes]:
        try:
            async for chunk in response.aiter_bytes(64 * 1024):
                yield chunk
        finally:
            await response.aclose()
            await client.aclose()

    return MediaProxy(
        body=body(),
        status_code=response.status_code,
        headers=headers,
        media_type=content_type,
    )


def _validate_provider_url(url: str) -> None:
    parsed = urlsplit(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or not host.endswith(_ALLOWED_HOST_SUFFIXES):
        raise AppError("TIKTOK_MEDIA_HOST_NOT_ALLOWED", "TikTok media host is not allowed.", 400)


def _valid_range_header(value: str) -> bool:
    if len(value) > 64 or not value.startswith(_RANGE_PREFIX):
        return False
    range_value = value.removeprefix(_RANGE_PREFIX)
    if "," in range_value or "-" not in range_value:
        return False
    start, end = range_value.split("-", 1)
    return (not start or start.isdigit()) and (not end or end.isdigit()) and bool(start or end)
