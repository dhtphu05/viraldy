# ruff: noqa: F811 -- pytest fixture imports are intentionally injected by name.
from __future__ import annotations

import base64
import hashlib
from types import SimpleNamespace

import httpx
import pytest
from pydantic import SecretStr
from test_smart_remake_grouped_workflow import grouped  # noqa: F401
from test_smart_remake_image_workflow import image, prepare, setup  # noqa: F401

from tests.smart_remake_expectations import install_expectations
from viraldy.modules.smart_remake.engine.kie_adapter import build_kie_group_request
from viraldy.modules.smart_remake.engine.openai_images import OpenAIImageClient
from viraldy.modules.smart_remake.engine.schemas import UploadedMedia
from viraldy.shared.errors.base import AppError


@pytest.mark.asyncio
async def test_character_is_a_real_third_multipart_image():
    character = image((35, 45), "blue")
    calls = []
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: calls.append(request)
            or httpx.Response(
                200, json={"data": [{"b64_json": base64.b64encode(image()).decode()}]}
            )
        )
    ) as http:
        media = UploadedMedia(bytes=image((20, 30)), mime_type="image/png")
        await OpenAIImageClient(
            SimpleNamespace(ai_mode="live", openai_api_key=SecretStr("unit-only")), http_client=http
        ).edit(
            prompt="Use the actor in image 3",
            product=media,
            layout=media,
            character=UploadedMedia(bytes=character, mime_type="image/png"),
        )
    assert len(calls) == 1
    assert calls[0].content.count(b'name="image[]"') == 3
    assert character in calls[0].content and b"character-reference" in calls[0].content


@pytest.mark.asyncio
async def test_character_reference_and_hash_are_bound_to_image_cache(setup):
    repair, row, operation, client, _, _, _ = setup
    first = await prepare(setup)
    character = image((35, 45), "blue")
    repair.media.objects["character"] = character
    row.context_json.update(
        characterKey="character",
        characterMimeType="image/png",
        characterMediaHash=hashlib.sha256(character).hexdigest(),
    )
    operation.result_json = {}
    second = await prepare(setup)
    assert first["requestHash"] != second["requestHash"]
    assert client.calls[-1]["character"].bytes == character
    assert "Image 3" in client.calls[-1]["prompt"]
    operation.result_json = {}
    await prepare(setup)
    assert len(client.calls) == 2


@pytest.mark.asyncio
async def test_changed_character_bytes_block_before_image_submission(setup):
    repair, row, _, client, _, _, _ = setup
    repair.media.objects["character"] = image((35, 45), "blue")
    row.context_json.update(
        characterKey="character",
        characterMimeType="image/png",
        characterMediaHash="wrong",
    )
    with pytest.raises(AppError, match="SMART_REMAKE_IMAGE_ASSET_INVALID"):
        await prepare(setup)
    assert client.calls == []


@pytest.mark.asyncio
async def test_character_group_uses_product_character_and_one_layout(grouped):
    value = grouped
    value.row.context_json.update(
        characterKey="character",
        characterMimeType="image/png",
        characterMediaHash=hashlib.sha256(b"character").hexdigest(),
    )
    install_expectations(value.row.context_json)
    await value.runner._freeze_plan(value.row, value.op)
    request, references = await value.runner._request(value.row, value.op, 0, value.groups[0])
    assert value.images == [0]
    assert value.client.uploads == [b"product", b"character", b"image-0"]
    assert len(request["input"]["image_urls"]) == 3 and len(references) == 1
    assert value.requests[0]["has_character_reference"] is True


def test_character_reference_role_is_explicit_in_kie_prompt():
    request = build_kie_group_request(
        scenes=[{"targetDurationFrames": 192, "videoPrompt": "Show cup"}],
        segments=[{"inFrame": 0, "outFrame": 192}],
        reference_image_urls=[f"https://1.1.1.1/{i}.png" for i in range(3)],
        has_character_reference=True,
    )
    assert "SECOND reference image" in request["input"]["prompt"]
    assert "character identity" in request["input"]["prompt"]


@pytest.mark.asyncio
async def test_openai_receipt_keeps_request_id_without_response_body():
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                headers={"x-request-id": "req-unit-1"},
                json={
                    "data": [{"b64_json": base64.b64encode(image()).decode()}],
                    "private": "not retained",
                },
            )
        )
    ) as http:
        media = UploadedMedia(bytes=image((20, 30)), mime_type="image/png")
        result = await OpenAIImageClient(
            SimpleNamespace(ai_mode="live", openai_api_key=SecretStr("unit-only")), http_client=http
        ).edit(prompt="frame", product=media, layout=media)
    assert result["providerRequestId"] == "req-unit-1"
    assert "private" not in result
