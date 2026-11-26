from __future__ import annotations

import base64
import json
from io import BytesIO
from types import SimpleNamespace

import httpx
import pytest
from PIL import Image
from pydantic import SecretStr

from viraldy.modules.smart_remake.engine.openai_images import OpenAIImageClient
from viraldy.modules.smart_remake.engine.schemas import UploadedMedia
from viraldy.shared.errors.base import AppError


def image_bytes(size: tuple[int, int] = (20, 30)) -> bytes:
    output = BytesIO()
    Image.new("RGB", size, "pink").save(output, format="PNG")
    return output.getvalue()


def media() -> UploadedMedia:
    return UploadedMedia(bytes=image_bytes(), mime_type="image/png")


def configured_client(http: httpx.AsyncClient) -> OpenAIImageClient:
    settings = SimpleNamespace(ai_mode="live", openai_api_key=SecretStr("test-only-secret"))
    return OpenAIImageClient(settings, http_client=http)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error,code,classification,safe_fields",
    [
        (
            {"code": "insufficient_quota", "type": "insufficient_quota"},
            "OPENAI_IMAGE_CREDITS_EXHAUSTED",
            "credits_exhausted",
            {"providerErrorCode": "insufficient_quota", "providerErrorType": "insufficient_quota"},
        ),
        (
            {"code": "billing_hard_limit_reached", "type": "invalid_request_error"},
            "OPENAI_IMAGE_CREDITS_EXHAUSTED",
            "credits_exhausted",
            {
                "providerErrorCode": "billing_hard_limit_reached",
                "providerErrorType": "invalid_request_error",
            },
        ),
        (
            {"type": "billing_hard_limit_reached"},
            "OPENAI_IMAGE_CREDITS_EXHAUSTED",
            "credits_exhausted",
            {"providerErrorType": "billing_hard_limit_reached"},
        ),
        *[
            (
                {"code": code}, "OPENAI_IMAGE_CREDITS_EXHAUSTED", "credits_exhausted",
                {"providerErrorCode": code},
            )
            for code in (
                "credit_balance_exhausted", "project_spend_limit_exceeded",
                "organization_spend_limit_exceeded", "organization_usage_limit_exceeded",
            )
        ],
        (
            {"code": "slow_down"}, "OPENAI_IMAGE_RATE_LIMITED", "rate_limit",
            {"providerErrorCode": "slow_down"},
        ),
        (
            {"code": "rate_limit_exceeded", "type": "rate_limit_error"},
            "OPENAI_IMAGE_RATE_LIMITED",
            "rate_limit",
            {"providerErrorCode": "rate_limit_exceeded", "providerErrorType": "rate_limit_error"},
        ),
        ({}, "OPENAI_IMAGE_RATE_LIMITED", "ambiguous", {}),
        (
            {"code": "private-key=https://private.invalid", "type": {"secret": "private"}},
            "OPENAI_IMAGE_RATE_LIMITED",
            "ambiguous",
            {},
        ),
    ],
)
async def test_rate_rejections_keep_only_safe_metadata(error, code, classification, safe_fields):
    calls = []
    payload = {
        "error": {**error, "message": "PRIVATE prompt and test-only-secret", "url": "private"},
    }
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: calls.append(request) or httpx.Response(429, json=payload)
        )
    ) as http:
        client = configured_client(http)
        assert client.last_rejection_receipt is None
        with pytest.raises(AppError) as raised:
            await client.edit(prompt="PRIVATE", product=media(), layout=media())
    assert raised.value.code == code
    assert raised.value.status_code == 429
    assert len(calls) == 1
    assert client.last_rejection_receipt == {
        "requestOutcome": "rejected",
        "httpStatus": 429,
        "classification": classification,
        **safe_fields,
    }
    serialized = json.dumps(client.last_rejection_receipt)
    assert "PRIVATE" not in serialized and "test-only-secret" not in serialized
    assert "private" not in serialized


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "retry_after,expected",
    [("0", 0), ("1.5", 2), ("2.5", 3), ("86400", 86400), ("9999999999", 86400),
     ("-1", None), ("NaN", None), ("Infinity", None),
     ("Wed, 21 Oct 2015 07:28:00 GMT", None), ("private-secret", None)],
)
async def test_retry_after_is_numeric_finite_and_bounded(retry_after, expected):
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(429, headers={"Retry-After": retry_after}, json={})
        )
    ) as http:
        client = configured_client(http)
        with pytest.raises(AppError):
            await client.edit(prompt="layout", product=media(), layout=media())
    receipt = client.last_rejection_receipt
    if expected is None:
        assert "retryAfterSeconds" not in receipt
    else:
        assert receipt["retryAfterSeconds"] == expected


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", [None, [], {"error": []}, {"error": "private"}])
async def test_malformed_error_shapes_remain_ambiguous(payload):
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(429, json=payload))
    ) as http:
        client = configured_client(http)
        with pytest.raises(AppError) as raised:
            await client.edit(prompt="layout", product=media(), layout=media())
    assert raised.value.code == "OPENAI_IMAGE_RATE_LIMITED"
    assert client.last_rejection_receipt == {
        "requestOutcome": "rejected", "httpStatus": 429, "classification": "ambiguous",
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [400, 401, 403, 404, 413, 422])
async def test_other_known_rejections_retain_status_without_claiming_rate_or_quota(status):
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(status, text="PRIVATE upstream")
        )
    ) as http:
        client = configured_client(http)
        with pytest.raises(AppError):
            await client.edit(prompt="layout", product=media(), layout=media())
    assert client.last_rejection_receipt == {"requestOutcome": "rejected", "httpStatus": status}


@pytest.mark.asyncio
@pytest.mark.parametrize("next_outcome", ["success", "timeout", "server_error", "invalid_input"])
async def test_rejection_receipt_is_reset_before_each_edit(next_outcome):
    calls = []

    def handle(request):
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(429, json={"error": {"code": "insufficient_quota"}})
        if next_outcome == "timeout":
            raise httpx.ReadTimeout("PRIVATE", request=request)
        if next_outcome == "server_error":
            return httpx.Response(500)
        return httpx.Response(200, json={
            "data": [{"b64_json": base64.b64encode(image_bytes((720, 1280))).decode()}],
        })

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as http:
        client = configured_client(http)
        with pytest.raises(AppError):
            await client.edit(prompt="layout", product=media(), layout=media())
        assert client.last_rejection_receipt["classification"] == "credits_exhausted"
        if next_outcome == "success":
            await client.edit(prompt="layout", product=media(), layout=media())
        else:
            with pytest.raises(AppError):
                await client.edit(
                    prompt="" if next_outcome == "invalid_input" else "layout",
                    product=media(), layout=media(),
                )
        assert client.last_rejection_receipt is None
    assert len(calls) == (1 if next_outcome == "invalid_input" else 2)


@pytest.mark.asyncio
async def test_oversized_error_body_is_not_used_for_classification():
    payload = {"error": {"code": "insufficient_quota", "message": "PRIVATE" * 12000}}
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(429, json=payload))
    ) as http:
        client = configured_client(http)
        with pytest.raises(AppError) as raised:
            await client.edit(prompt="layout", product=media(), layout=media())
    assert raised.value.code == "OPENAI_IMAGE_RATE_LIMITED"
    assert client.last_rejection_receipt == {
        "requestOutcome": "rejected", "httpStatus": 429, "classification": "ambiguous",
    }
