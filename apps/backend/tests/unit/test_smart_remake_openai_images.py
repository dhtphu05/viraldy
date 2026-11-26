from __future__ import annotations

import base64
import hashlib
from io import BytesIO
from types import SimpleNamespace

import httpx
import pytest
from PIL import Image
from pydantic import SecretStr

from viraldy.modules.smart_remake.engine.openai_images import OpenAIImageClient
from viraldy.modules.smart_remake.engine.schemas import UploadedMedia


def png(size: tuple[int, int] = (720, 1280)) -> bytes:
    stream = BytesIO()
    Image.new("RGB", size, "pink").save(stream, format="PNG")
    return stream.getvalue()


def media() -> UploadedMedia:
    return UploadedMedia(bytes=png((20, 30)), mime_type="image/png", file_name="private.png")


def settings(mode: str = "live", key: str | None = "test-secret") -> SimpleNamespace:
    return SimpleNamespace(ai_mode=mode, openai_api_key=SecretStr(key) if key else None)


@pytest.mark.asyncio
@pytest.mark.parametrize("quality", ["low", "medium", "high", "xhigh", "max"])
async def test_edit_uses_fixed_official_origin_and_validated_png_with_usage(quality):
    calls = []
    output = png()
    usage = {"input_tokens": 35, "output_tokens": 90, "input_tokens_details": {"image_tokens": 30}}

    def handle(request):
        calls.append(request)
        assert str(request.url) == "https://api.openai.com/v1/images/edits"
        assert request.headers["authorization"] == "Bearer test-secret"
        assert request.content.count(b'name="image[]"') == 2
        assert b"gpt-image-2.6-sunburst" in request.content
        assert b"720x1280" in request.content and quality.encode() in request.content
        assert b'name="n"\r\n\r\n1\r\n' in request.content
        assert b'name="output_format"\r\n\r\npng\r\n' in request.content
        assert b'name="complexity"\r\n\r\nhigh\r\n' in request.content
        assert b"reasoning_effort" not in request.content
        return httpx.Response(
            200, json={"data": [{"b64_json": base64.b64encode(output).decode()}], "usage": usage}
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as http:
        result = await OpenAIImageClient(settings(), http_client=http).edit(
            prompt="Keep the real product", product=media(), layout=media(), quality=quality
        )
    assert len(calls) == 1
    assert result == {
        "bytes": output,
        "mimeType": "image/png",
        "mediaHash": hashlib.sha256(output).hexdigest(),
        "model": "gpt-image-2.6-sunburst",
        "size": "720x1280",
        "quality": quality,
        "complexity": "high",
        "usage": usage,
    }


@pytest.mark.parametrize(
    "mode,key,code",
    [
        ("fixture", "test", "OPENAI_IMAGE_NOT_LIVE"),
        ("mock", "test", "OPENAI_IMAGE_NOT_LIVE"),
        ("live", None, "OPENAI_IMAGE_NOT_CONFIGURED"),
    ],
)
def test_configuration_fails_closed_before_network(mode, key, code):
    with pytest.raises(Exception) as exc:
        OpenAIImageClient(settings(mode, key))
    assert exc.value.code == code


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status,code",
    [
        (400, "OPENAI_IMAGE_REQUEST_REJECTED"),
        (401, "OPENAI_IMAGE_AUTH_FAILED"),
        (403, "OPENAI_IMAGE_PERMISSION_DENIED"),
        (429, "OPENAI_IMAGE_RATE_LIMITED"),
        (500, "OPENAI_IMAGE_SUBMISSION_UNRESOLVED"),
        (302, "OPENAI_IMAGE_SUBMISSION_UNRESOLVED"),
    ],
)
async def test_rejections_or_uncertain_status_never_retry_or_expose_provider_body(status, code):
    calls = []
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda req: calls.append(req)
            or httpx.Response(status, json={"error": {"message": "PRIVATE-PROMPT test-secret"}})
        )
    ) as http:
        with pytest.raises(Exception) as exc:
            await OpenAIImageClient(settings(), http_client=http).edit(
                prompt="PRIVATE-PROMPT", product=media(), layout=media()
            )
    assert exc.value.code == code and len(calls) == 1
    assert "PRIVATE-PROMPT" not in str(exc.value) and "test-secret" not in str(exc.value)


@pytest.mark.asyncio
async def test_transport_timeout_is_unknown_and_is_not_retried():
    calls = []

    def handle(request):
        calls.append(request)
        raise httpx.ReadTimeout("secret upstream body", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as http:
        with pytest.raises(Exception) as exc:
            await OpenAIImageClient(settings(), http_client=http).edit(
                prompt="layout", product=media(), layout=media()
            )
    assert exc.value.code == "OPENAI_IMAGE_SUBMISSION_UNRESOLVED" and len(calls) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"data": [{"b64_json": "invalid"}]},
        {"data": [{"b64_json": base64.b64encode(png((1280, 720))).decode()}]},
        {"data": [{"b64_json": base64.b64encode(b"not PNG").decode()}]},
    ],
)
async def test_malformed_or_wrong_size_success_is_unresolved(payload):
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda req: httpx.Response(200, json=payload))
    ) as http:
        with pytest.raises(Exception) as exc:
            await OpenAIImageClient(settings(), http_client=http).edit(
                prompt="layout", product=media(), layout=media()
            )
    assert exc.value.code == "OPENAI_IMAGE_SUBMISSION_UNRESOLVED"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "quality,invalid",
    [("ultra", None), ("low", b"not an image"), ("low", b"x" * (10 * 1024 * 1024 + 1))],
)
async def test_invalid_input_never_posts(quality, invalid):
    calls = []
    product = UploadedMedia(bytes=invalid, mime_type="image/png") if invalid else media()
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda req: calls.append(req) or httpx.Response(500))
    ) as http:
        with pytest.raises(Exception) as exc:
            await OpenAIImageClient(settings(), http_client=http).edit(
                prompt="layout", product=product, layout=media(), quality=quality
            )
    assert exc.value.code == "OPENAI_IMAGE_VALIDATION_FAILED" and calls == []


@pytest.mark.asyncio
async def test_defaults_request_sunburst_with_max_quality_and_high_complexity():
    calls = []
    output = png()
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: calls.append(request)
            or httpx.Response(200, json={"data": [{"b64_json": base64.b64encode(output).decode()}]})
        )
    ) as http:
        result = await OpenAIImageClient(settings(), http_client=http).edit(
            prompt="Keep product details", product=media(), layout=media()
        )
    assert len(calls) == 1
    for name, value in (
        ("model", "gpt-image-2.6-sunburst"),
        ("quality", "max"),
        ("complexity", "high"),
    ):
        assert f'name="{name}"\r\n\r\n{value}\r\n'.encode() in calls[0].content
    assert result["model"] == "gpt-image-2.6-sunburst"
    assert result["quality"] == "max" and result["complexity"] == "high"


@pytest.mark.asyncio
async def test_saved_flare_configuration_is_sent_without_changing_its_quality():
    calls = []
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: calls.append(request)
            or httpx.Response(200, json={"data": [{"b64_json": base64.b64encode(png()).decode()}]})
        )
    ) as http:
        result = await OpenAIImageClient(settings(), http_client=http).edit(
            prompt="Legacy saved plan",
            product=media(),
            layout=media(),
            model="gpt-image-2.6-flare",
            quality="low",
            complexity="high",
        )
    assert b'name="model"\r\n\r\ngpt-image-2.6-flare\r\n' in calls[0].content
    assert result["model"] == "gpt-image-2.6-flare" and result["quality"] == "low"


@pytest.mark.asyncio
@pytest.mark.parametrize("overrides", [{"model": "unknown"}, {"complexity": "max"}])
async def test_unsupported_image_model_or_complexity_never_posts(overrides):
    calls = []
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: calls.append(request) or httpx.Response(500))
    ) as http:
        with pytest.raises(Exception) as exc:
            await OpenAIImageClient(settings(), http_client=http).edit(
                prompt="layout", product=media(), layout=media(), **overrides
            )
    assert exc.value.code == "OPENAI_IMAGE_VALIDATION_FAILED" and calls == []
