"""Direct OpenAI image edits with no automatic paid submission retries."""

from __future__ import annotations

import base64
import binascii
import hashlib
import math
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from io import BytesIO
from typing import Any

import httpx
from PIL import Image, UnidentifiedImageError

from viraldy.modules.smart_remake.provider_execution import (
    ProviderExecutionEvidence,
    observe_response,
    safe_provider_identifier,
)
from viraldy.platform.config.settings import Settings
from viraldy.shared.errors.base import AppError

from .schemas import UploadedMedia

IMAGE_MODEL = "gpt-image-2.6-sunburst"
SUPPORTED_IMAGE_MODELS = {IMAGE_MODEL, "gpt-image-2.6-flare"}
IMAGE_SIZE = "720x1280"
IMAGE_EDIT_URL = "https://api.openai.com/v1/images/edits"
MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_RESPONSE_BYTES = 40 * 1024 * 1024
_FORMATS = {"image/png": "PNG", "image/jpeg": "JPEG", "image/webp": "WEBP"}
_QUOTA_ERRORS = {
    "insufficient_quota", "billing_hard_limit_reached", "credit_balance_exhausted",
    "project_spend_limit_exceeded", "organization_spend_limit_exceeded",
    "organization_usage_limit_exceeded",
}
_RATE_ERRORS = {"rate_limit_exceeded", "rate_limit_error", "slow_down"}
_SAFE_ERROR_CODES = _QUOTA_ERRORS | {"rate_limit_exceeded", "slow_down"}
_SAFE_ERROR_TYPES = _QUOTA_ERRORS | _RATE_ERRORS | {
    "invalid_request_error", "authentication_error", "permission_error", "server_error",
}


def _rejection_receipt(response: httpx.Response) -> dict[str, Any]:
    receipt: dict[str, Any] = {"requestOutcome": "rejected", "httpStatus": response.status_code}
    try:
        body = response.json() if len(response.content) <= 64 * 1024 else None
    except ValueError:
        body = None
    error = body.get("error") if isinstance(body, dict) else None
    if isinstance(error, dict):
        for source, target, allowed in (
            ("code", "providerErrorCode", _SAFE_ERROR_CODES),
            ("type", "providerErrorType", _SAFE_ERROR_TYPES),
        ):
            value = error.get(source)
            if isinstance(value, str) and value in allowed:
                receipt[target] = value
    if response.status_code == 429:
        errors = {receipt.get("providerErrorCode"), receipt.get("providerErrorType")}
        receipt["classification"] = (
            "credits_exhausted" if errors & _QUOTA_ERRORS
            else "rate_limit" if errors & _RATE_ERRORS else "ambiguous"
        )
    retry_after = response.headers.get("retry-after")
    if retry_after is not None:
        try:
            seconds = float(retry_after)
        except ValueError:
            seconds = math.nan
        if math.isfinite(seconds) and seconds >= 0:
            receipt["retryAfterSeconds"] = math.ceil(min(seconds, 86400))
    return receipt


def _invalid_input() -> AppError:
    return AppError(
        "OPENAI_IMAGE_VALIDATION_FAILED",
        "Use readable PNG, JPEG or WebP references up to 10 MB and supported image settings.",
    )


def _unresolved() -> AppError:
    return AppError(
        "OPENAI_IMAGE_SUBMISSION_UNRESOLVED",
        "The image request may have been accepted. Reconcile it before trying again.",
        409,
    )


def _validate_input(media: UploadedMedia) -> None:
    if media.mime_type not in _FORMATS or not 0 < len(media.bytes) <= MAX_IMAGE_BYTES:
        raise _invalid_input()
    try:
        with Image.open(BytesIO(media.bytes)) as image:
            if image.format != _FORMATS[media.mime_type]:
                raise _invalid_input()
            image.verify()
    except (OSError, ValueError, UnidentifiedImageError, Image.DecompressionBombError):
        raise _invalid_input() from None


def validate_generated_png(data: bytes) -> None:
    """Inspect the decoded file, not the requested dimensions or provider metadata."""
    if not 0 < len(data) <= MAX_IMAGE_BYTES:
        raise ValueError("Invalid generated image length")
    try:
        with Image.open(BytesIO(data)) as image:
            if image.format != "PNG" or image.size != (720, 1280):
                raise ValueError("Expected one 720x1280 PNG")
            image.load()
    except (OSError, UnidentifiedImageError, Image.DecompressionBombError) as exc:
        raise ValueError("Invalid generated PNG") from exc


def _usage(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    # Retain token counts, never provider text or image payloads in usage metadata.
    return {
        key: _usage(item) if isinstance(item, dict) else item
        for key, item in value.items()
        if isinstance(key, str)
        and (
            isinstance(item, dict) or (isinstance(item, int | float) and not isinstance(item, bool))
        )
    }


class OpenAIImageClient:
    def __init__(self, settings: Settings, *, http_client: httpx.AsyncClient | None = None) -> None:
        if settings.ai_mode.strip().lower() != "live":
            raise AppError("OPENAI_IMAGE_NOT_LIVE", "Image generation requires live AI mode.", 409)
        if not settings.openai_api_key:
            raise AppError(
                "OPENAI_IMAGE_NOT_CONFIGURED", "Configure the direct OpenAI image API first.", 503
            )
        self._api_key = settings.openai_api_key.get_secret_value()
        self.http_client = http_client
        self.last_rejection_receipt: dict[str, Any] | None = None

    @asynccontextmanager
    async def _client(self) -> AsyncIterator[httpx.AsyncClient]:
        if self.http_client is not None:
            yield self.http_client
        else:
            async with httpx.AsyncClient(
                timeout=180, follow_redirects=False, trust_env=False
            ) as client:
                yield client

    async def edit(
        self,
        *,
        prompt: str,
        product: UploadedMedia,
        layout: UploadedMedia,
        character: UploadedMedia | None = None,
        model: str = IMAGE_MODEL,
        quality: str = "max",
        complexity: str = "high",
    ) -> dict[str, Any]:
        self.last_rejection_receipt = None
        self.last_execution_evidence: ProviderExecutionEvidence | None = None
        self.last_request_id: str | None = None
        if (
            model not in SUPPORTED_IMAGE_MODELS
            or quality not in {"low", "medium", "high", "xhigh", "max"}
            or complexity not in {"low", "medium", "high"}
            or not 0 < len(prompt.strip()) <= 32000
        ):
            raise _invalid_input()
        _validate_input(product)
        _validate_input(layout)
        files = [
            ("image[]", ("product-reference", product.bytes, product.mime_type)),
            ("image[]", ("composition-reference", layout.bytes, layout.mime_type)),
        ]
        if character is not None:
            _validate_input(character)
            files.append(("image[]", ("character-reference", character.bytes, character.mime_type)))
        async with self._client() as client:
            try:
                response = await client.post(
                    IMAGE_EDIT_URL,
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    data={
                        "model": model,
                        "prompt": prompt,
                        "n": "1",
                        "size": IMAGE_SIZE,
                        "quality": quality,
                        "complexity": complexity,
                        "output_format": "png",
                    },
                    files=files,
                    follow_redirects=False,
                )
            except httpx.HTTPError:
                raise _unresolved() from None
            self.last_execution_evidence = observe_response(
                response,
                provider="openai",
                model=model,
                operation="openai.images.edit",
                owned_transport=self.http_client is None,
            )
            request_id = response.headers.get("x-request-id")
            self.last_request_id = request_id if safe_provider_identifier(request_id) else None
            if response.status_code in {400, 401, 403, 404, 413, 422, 429}:
                self.last_rejection_receipt = _rejection_receipt(response)
                code = {
                    401: "OPENAI_IMAGE_AUTH_FAILED",
                    403: "OPENAI_IMAGE_PERMISSION_DENIED",
                    429: "OPENAI_IMAGE_RATE_LIMITED",
                }.get(response.status_code, "OPENAI_IMAGE_REQUEST_REJECTED")
                if self.last_rejection_receipt.get("classification") == "credits_exhausted":
                    code = "OPENAI_IMAGE_CREDITS_EXHAUSTED"
                raise AppError(
                    code, "OpenAI rejected this image request.",
                    429 if response.status_code == 429 else 400,
                )
            if response.status_code != 200 or len(response.content) > MAX_RESPONSE_BYTES:
                raise _unresolved()
            try:
                body = response.json()
                entries = body["data"]
                if not isinstance(entries, list) or len(entries) != 1:
                    raise ValueError("Expected one output")
                data = base64.b64decode(entries[0]["b64_json"], validate=True)
                validate_generated_png(data)
            except (KeyError, TypeError, ValueError, binascii.Error):
                raise _unresolved() from None
        return {
            "bytes": data,
            "mimeType": "image/png",
            "mediaHash": hashlib.sha256(data).hexdigest(),
            "model": model,
            "size": IMAGE_SIZE,
            "quality": quality,
            "complexity": complexity,
            "usage": _usage(body.get("usage")),
            **({"providerRequestId": self.last_request_id} if self.last_request_id else {}),
        }


_PHYSICAL_OPENAI_IMAGE_CLIENT = OpenAIImageClient
_PHYSICAL_OPENAI_IMAGE_EDIT = OpenAIImageClient.edit
