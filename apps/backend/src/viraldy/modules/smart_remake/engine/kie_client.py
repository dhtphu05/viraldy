"""KIE requests never automatically retry a paid task submission."""

from __future__ import annotations

import asyncio
import json
import math
import re
import socket
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from io import BytesIO
from typing import Any, cast
from uuid import uuid4

import httpx

from viraldy.modules.product_import.security import Resolver, validate_public_http_url
from viraldy.modules.smart_remake.provider_errors import sanitize_provider_error
from viraldy.modules.smart_remake.provider_execution import (
    ProviderExecutionEvidence,
    observe_response,
    safe_provider_identifier,
)
from viraldy.shared.errors.base import AppError

from .config import get_kie_api_key
from .errors import SmartRemakeError, SmartRemakeValidationError
from .kie_adapter import KIE_MODEL, public_media_url
from .schemas import UploadedMedia
from .video_requests import canonical_video_model, validate_video_input
from .wan_video_adapter import WAN_VIDEO_MODEL

API_ORIGIN = "https://api.kie.ai"
UPLOAD_ORIGIN = "https://kieai.redpandaai.co"
MAX_IMAGE_BYTES = 10 * 1024 * 1024  # Existing Smart Remake input limit.
MAX_OUTPUT_BYTES = 100 * 1024 * 1024  # Local download memory guard.
_IMAGE_EXTENSIONS = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
_STATES = {
    "waiting": "queued",
    "queuing": "queued",
    "generating": "processing",
    "success": "completed",
    "fail": "failed",
}
_NATIVE_STATES = {0: "generating", 1: "success", 2: "fail", 3: "fail"}


class KieClient:
    api_contract = "kie-unified-v1"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.api_key = api_key if api_key is not None else get_kie_api_key()
        self.http_client = http_client
        if not self.api_key:
            raise SmartRemakeError(
                "KIE_API_KEY is required for KIE rendering.", "KIE_NOT_CONFIGURED"
            )

    @asynccontextmanager
    async def _client(self) -> AsyncIterator[httpx.AsyncClient]:
        if self.http_client is not None:
            yield self.http_client
        else:
            async with httpx.AsyncClient(
                timeout=60,
                follow_redirects=False,
                trust_env=False,
                http2=False,
            ) as client:
                yield client

    async def upload_file(self, media: UploadedMedia) -> str:
        if media.mime_type not in _IMAGE_EXTENSIONS or not 0 < len(media.bytes) <= MAX_IMAGE_BYTES:
            raise SmartRemakeValidationError(
                "Use a JPEG, PNG or WebP product image up to 10 MB.",
                "KIE_VALIDATION_FAILED",
            )
        # KIE overwrites identical names. Never reuse the user filename between jobs.
        filename = f"{uuid4().hex}.{_IMAGE_EXTENSIONS[media.mime_type]}"
        # Uploads are free and may safely overwrite this request's exact bytes.
        # Retry one transport failure on a fresh connection, never a paid task.
        for attempt in range(2):
            try:
                # File-like input gives HTTPX bounded multipart writes while
                # preserving Content-Length and the exact verified bytes.
                with BytesIO(media.bytes) as stream:
                    async with self._client() as client:
                        response = await client.post(
                            f"{UPLOAD_ORIGIN}/api/file-stream-upload",
                            headers={"Authorization": f"Bearer {self.api_key}"},
                            files={"file": (filename, stream, media.mime_type)},
                            data={"uploadPath": "smart-remake/products", "fileName": filename},
                            timeout=90,
                            follow_redirects=False,
                        )
                break
            except httpx.TransportError as exc:
                if attempt == 0:
                    await asyncio.sleep(0.5)
                    continue
                raise SmartRemakeError(
                    "KIE image upload is unavailable.", "KIE_UPLOAD_FAILED",
                    {"networkError": type(exc).__name__},
                ) from exc
        data = _response_data(response, "KIE_UPLOAD_FAILED")
        url = data.get("downloadUrl")
        if data.get("success") is False or not isinstance(url, str):
            raise SmartRemakeError(
                "KIE upload did not return an image URL.", "KIE_INVALID_RESPONSE"
            )
        return await asyncio.to_thread(public_media_url, url)

    async def create_task(
        self, *, model: str = KIE_MODEL, input_data: dict[str, Any]
    ) -> dict[str, Any]:
        self.last_execution_evidence: ProviderExecutionEvidence | None = None
        self.last_request_id: str | None = None
        model = canonical_video_model(model)
        await asyncio.to_thread(validate_video_input, model, input_data)
        try:
            data = await self._json(
                "POST",
                "/api/v1/jobs/createTask",
                body={"model": model, "input": input_data},
                code="KIE_TASK_CREATE_FAILED",
                model=model,
            )
        except SmartRemakeError as exc:
            if exc.code in {"KIE_UNAVAILABLE", "KIE_INVALID_RESPONSE", "KIE_SERVER_ERROR"}:
                raise _uncertain_submission(exc.details) from exc
            raise
        task_id = data.get("taskId")
        if not isinstance(task_id, str) or not task_id.strip():
            raise _uncertain_submission({
                "status": 200, "providerCode": 200,
                "providerMessage": "No valid taskId in response; data fields: "
                + ", ".join(str(key)[:40] for key in list(data)[:10]),
            })
        return {"task_id": task_id.strip(), "status": "queued"}

    async def get_task(self, task_id: str, *, model: str = KIE_MODEL) -> dict[str, Any]:
        self.last_execution_evidence = None
        self.last_request_id = None
        model = canonical_video_model(model)
        if not isinstance(task_id, str) or not task_id.strip() or len(task_id) > 256:
            raise SmartRemakeValidationError(
                "A valid KIE task ID is required.", "KIE_VALIDATION_FAILED"
            )
        data = await self._task_data(task_id, model=model)
        state = data.get("state")
        if (
            data.get("taskId") != task_id
            or not isinstance(state, str)
            or state not in _STATES
            or data.get("model", KIE_MODEL if model == KIE_MODEL else None) != model
        ):
            raise SmartRemakeError("KIE returned an unknown task response.", "KIE_INVALID_RESPONSE")
        result: dict[str, Any] = {"task_id": task_id, "status": _STATES[state]}
        receipt = {
            name: value for name in (
                "credits", "consumeCredits", "creditsConsumed", "costCredits", "billedUsd",
            )
            if (value := data.get(name)) is not None and _numeric_receipt(value)
        }
        if receipt:
            result["receipt"] = receipt
        usage = data.get("usage")
        if isinstance(usage, dict):
            result["usage"] = {name: value for name, value in usage.items()
                               if isinstance(name, str) and _numeric_receipt(value)}
        if state == "success":
            url = _result_url(data)
            result["output"] = {"video_url": await asyncio.to_thread(public_media_url, url)}
        elif state == "fail":
            error = sanitize_provider_error({
                "providerCode": data.get("failCode"), "providerMessage": data.get("failMsg"),
            }, secrets=(self.api_key,))
            result["providerError"] = error
            result["error_message"] = error.get("providerMessage", "KIE generation failed.")
        return result

    async def _task_data(self, task_id: str, *, model: str = KIE_MODEL) -> dict[str, Any]:
        if model == WAN_VIDEO_MODEL:
            return await self._json(
                "GET", "/api/v1/jobs/recordInfo", params={"taskId": task_id},
                code="KIE_TASK_STATUS_FAILED", model=model,
            )
        try:
            data = await self._json(
                "GET", "/api/v1/veo/record-info", params={"taskId": task_id},
                code="KIE_TASK_STATUS_FAILED",
            )
        except SmartRemakeError as exc:
            if not _unified_lookup_allowed(exc):
                raise
        else:
            flag = data.get("successFlag")
            if type(flag) is int and flag in _NATIVE_STATES:
                if data.get("taskId") != task_id or data.get("model", KIE_MODEL) not in {
                    KIE_MODEL, "veo3_lite",
                }:
                    raise SmartRemakeError(
                        "KIE returned an unknown task response.", "KIE_INVALID_RESPONSE"
                    )
                return {
                    **data, "state": _NATIVE_STATES[flag], "model": KIE_MODEL,
                    "failMsg": data.get("errorMessage"),
                    "failCode": data.get("errorCode"),
                }
        # Old task IDs may belong to the unified API. This compatibility lookup
        # is read-only; a missing receipt never causes another paid submission.
        return await self._json(
            "GET", "/api/v1/jobs/recordInfo", params={"taskId": task_id},
            code="KIE_TASK_STATUS_FAILED",
        )

    async def _json(
        self,
        method: str,
        path: str,
        *,
        code: str,
        body: dict[str, Any] | None = None,
        params: dict[str, str] | None = None,
        model: str = KIE_MODEL,
    ) -> dict[str, Any]:
        async with self._client() as client:
            try:
                response = await client.request(
                    method,
                    f"{API_ORIGIN}{path}",
                    json=body,
                    params=params,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    follow_redirects=False,
                )
            except httpx.HTTPError as exc:
                raise SmartRemakeError("KIE API is unavailable.", "KIE_UNAVAILABLE") from exc
            self.last_execution_evidence = observe_response(
                response,
                provider="kie",
                model=model,
                operation="kie.tasks.create" if method == "POST" else "kie.tasks.get",
                owned_transport=self.http_client is None,
            )
            request_id = response.headers.get("x-request-id")
            self.last_request_id = request_id if safe_provider_identifier(request_id) else None
            try:
                return _response_data(response, code)
            except SmartRemakeError as exc:
                if method == "GET" and response.status_code in {401, 402, 403, 429}:
                    # A gateway may return HTML. Its auth/rate status still
                    # forbids a second lookup even when no JSON was readable.
                    raise SmartRemakeError(
                        str(exc), exc.code,
                        {**(exc.details or {}), "status": response.status_code},
                    ) from exc
                raise

    async def download_file(self, url: str) -> bytes:
        current_url = url
        async with self._client() as client:
            for _ in range(6):
                original_url, pinned_url = await asyncio.to_thread(_pin_media_url, current_url)
                try:
                    # API credentials belong only to the two fixed KIE API origins.
                    async with _unauthenticated_download(
                        client,
                        original_url,
                        pinned_url,
                    ) as response:
                        if response.is_redirect:
                            location = response.headers.get("location")
                            if not location:
                                break
                            current_url = str(original_url.join(location))
                            continue
                        content_type = response.headers.get("content-type", "").split(";", 1)[0]
                        if response.status_code != 200 or content_type not in {
                            "video/mp4",
                            "video/webm",
                            "video/quicktime",
                            "application/octet-stream",
                        }:
                            break
                        chunks = []
                        size = 0
                        async for chunk in response.aiter_bytes():
                            size += len(chunk)
                            if size > MAX_OUTPUT_BYTES:
                                raise SmartRemakeError(
                                    "KIE output exceeds the download limit.",
                                    "KIE_OUTPUT_DOWNLOAD_FAILED",
                                )
                            chunks.append(chunk)
                        if size:
                            return b"".join(chunks)
                        break
                except httpx.HTTPError as exc:
                    raise SmartRemakeError(
                        "KIE output could not be downloaded.",
                        "KIE_OUTPUT_DOWNLOAD_FAILED",
                    ) from exc
        raise SmartRemakeError("KIE output could not be downloaded.", "KIE_OUTPUT_DOWNLOAD_FAILED")


_PHYSICAL_KIE_CLIENT = KieClient
_PHYSICAL_KIE_CREATE_TASK = KieClient.create_task
_PHYSICAL_KIE_GET_TASK = KieClient.get_task


def _unified_lookup_allowed(error: SmartRemakeError) -> bool:
    details = error.details if isinstance(error.details, dict) else {}
    if details.get("status") in {401, 402, 403, 429}:
        return False
    if error.code == "KIE_INVALID_RESPONSE":
        return True
    if details.get("providerCode") == 404:
        return True
    return details.get("providerCode") == 422 and bool(re.search(
        r"\b(?:not found|does not exist|not exist)\b",
        str(details.get("providerMessage", "")), re.IGNORECASE,
    ))


def _numeric_receipt(value: Any) -> bool:
    try:
        return not isinstance(value, bool) and isinstance(value, int | float | str) and (
            math.isfinite(float(value)) and float(value) >= 0
        )
    except (ValueError, OverflowError):
        return False


@asynccontextmanager
async def _unauthenticated_download(
    client: httpx.AsyncClient,
    original_url: httpx.URL,
    pinned_url: httpx.URL,
) -> AsyncIterator[httpx.Response]:
    request = client.build_request("GET", pinned_url, timeout=120)
    request.headers.pop("authorization", None)
    request.headers.pop("cookie", None)
    request.headers["host"] = original_url.netloc.decode("ascii")
    # A pinned IP can host multiple TLS names. Close each HTTP/1.1 connection so
    # a redirect cannot reuse a TLS session verified for a different hostname.
    request.headers["connection"] = "close"
    request.extensions["sni_hostname"] = original_url.raw_host.decode("ascii")
    response = await client.send(request, stream=True, follow_redirects=False, auth=None)
    try:
        yield response
    finally:
        await response.aclose()


def _pin_media_url(value: str) -> tuple[httpx.URL, httpx.URL]:
    addresses: list[str] = []

    def resolve(*args: Any, **kwargs: Any) -> list[tuple[int, int, int, str, tuple[Any, ...]]]:
        results = cast(Resolver, socket.getaddrinfo)(*args, **kwargs)
        addresses.extend(str(result[4][0]) for result in results if result[4])
        return results

    try:
        # The shared validator checks every returned address. Retain that exact
        # resolution for the connection, rather than resolving the host again.
        original = httpx.URL(validate_public_http_url(value, resolver=resolve))
    except (AppError, ValueError) as exc:
        raise SmartRemakeError(
            "KIE media must use a publicly accessible HTTP or HTTPS URL.",
            "KIE_UNSAFE_MEDIA_URL",
        ) from exc
    address = addresses[0] if addresses else original.host  # Public IP literals skip DNS.
    return original, original.copy_with(host=address)


def _uncertain_submission(provider_error: Any = None) -> SmartRemakeError:
    return SmartRemakeError(
        "KIE may have accepted this render, but no task ID was confirmed. "
        "Check the KIE task history before submitting another paid render.",
        "KIE_SUBMISSION_UNCERTAIN",
        {"submissionUncertain": True,
         **({"providerError": dict(provider_error)} if isinstance(provider_error, dict) else {})},
    )


def _provider_error_details(
    response: httpx.Response, payload: dict[str, Any], provider_code: int
) -> dict[str, Any]:
    details: dict[str, Any] = {"status": response.status_code, "providerCode": provider_code}
    message = payload.get("msg")
    if not isinstance(message, str) or not message.strip():
        return details
    try:
        authorization = response.request.headers.get("authorization", "")
    except RuntimeError:
        authorization = ""
    prompt = ""
    try:
        request_body = json.loads(response.request.content)
        if isinstance(request_body, dict):
            prompt = (request_body.get("input") or {}).get("prompt", "")
    except (RuntimeError, ValueError, TypeError, AttributeError):
        pass
    error = sanitize_provider_error({"providerMessage": message}, secrets=(
        authorization, authorization.removeprefix("Bearer "), prompt,
    ))
    details.update(error)
    return details


def _response_data(response: httpx.Response, fallback: str) -> dict[str, Any]:
    try:
        payload = response.json()
    except ValueError as exc:
        code = "KIE_SERVER_ERROR" if response.status_code >= 500 else "KIE_INVALID_RESPONSE"
        raise SmartRemakeError("KIE returned an invalid response.", code) from exc
    if not isinstance(payload, dict):
        raise SmartRemakeError("KIE returned an invalid response.", "KIE_INVALID_RESPONSE")
    provider_code = response.status_code if response.status_code >= 400 else payload.get("code")
    if type(provider_code) is not int:
        raise SmartRemakeError("KIE returned an invalid response.", "KIE_INVALID_RESPONSE")
    if provider_code != 200 or payload.get("success") is False or response.status_code != 200:
        code = {
            401: "KIE_AUTH_FAILED",
            403: "KIE_AUTH_FAILED",
            402: "KIE_CREDITS_EXHAUSTED",
            429: "KIE_RATE_LIMITED",
            400: "KIE_VALIDATION_FAILED",
            422: "KIE_VALIDATION_FAILED",
        }.get(
            provider_code,
            "KIE_SERVER_ERROR" if provider_code >= 500 or provider_code == 408 else fallback,
        )
        raise SmartRemakeError(
            "KIE rejected the request. Check the provider status and configuration.",
            code,
            _provider_error_details(response, payload, provider_code),
        )
    data = payload.get("data")
    if not isinstance(data, dict):
        raise SmartRemakeError("KIE returned an invalid response.", "KIE_INVALID_RESPONSE")
    return data


def _result_url(data: dict[str, Any]) -> str:
    value = data.get("resultJson", data.get("response"))
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError as exc:
            raise SmartRemakeError(
                "KIE returned invalid result JSON.", "KIE_INVALID_RESPONSE"
            ) from exc
    if isinstance(value, dict):
        nested = value.get("data")
        urls = value.get("resultUrls")
        if urls is None and isinstance(nested, dict):
            urls = nested.get("result_urls") or nested.get("origin_urls")
        if (
            isinstance(urls, list)
            and len(urls) == 1
            and isinstance(urls[0], str)
            and urls[0].strip()
        ):
            return urls[0].strip()
    raise SmartRemakeError("KIE completed without a single video result.", "KIE_INVALID_RESPONSE")
