# ruff: noqa: F811 -- shared pytest fixtures are injected by name.
"""Primary-first multi-view evidence stays bound to the exact image request."""

from __future__ import annotations

import base64
import copy
import hashlib
from unittest.mock import AsyncMock

import httpx
import pytest
from test_smart_remake_image_workflow import image, prepare, setup  # noqa: F401
from test_smart_remake_openai_images import media, settings
from test_smart_remake_presenter_conditioning import (  # noqa: F401
    prepare_unit,
    presenter_setup,
)

from viraldy.modules.smart_remake import image_workflow as module
from viraldy.modules.smart_remake.engine.openai_images import OpenAIImageClient
from viraldy.modules.smart_remake.engine.schemas import UploadedMedia
from viraldy.shared.errors.base import AppError


def uploaded(color):
    return UploadedMedia(bytes=image((24, 36), color), mime_type="image/png")


@pytest.mark.asyncio
@pytest.mark.parametrize("character", [None, uploaded("purple")])
async def test_openai_edit_sends_all_product_angles_before_layout_and_presenter(character):
    calls = []
    output = image()
    primary, supporting, layout = uploaded("red"), uploaded("green"), uploaded("blue")
    async with httpx.AsyncClient(transport=httpx.MockTransport(
        lambda request: calls.append(request) or httpx.Response(200, json={
            "data": [{"b64_json": base64.b64encode(output).decode()}],
        }),
    )) as http:
        await OpenAIImageClient(settings(), http_client=http).edit(
            prompt="Use all product views", product=primary, layout=layout,
            additional_products=[supporting], character=character,
        )
    assert len(calls) == 1
    content = calls[0].content
    expected = [primary, supporting, layout, *([character] if character else [])]
    assert content.count(b'name="image[]"') == len(expected)
    positions = [content.index(value.bytes) for value in expected]
    assert positions == sorted(positions)
    assert content.index(b'filename="product-reference"') < content.index(
        b'filename="product-reference-2"'
    ) < content.index(b'filename="composition-reference"')
    if character:
        assert content.index(b'filename="character-reference"') > positions[2]


@pytest.mark.asyncio
async def test_openai_edit_allows_fourteen_product_images_with_layout_and_presenter():
    calls = []
    async with httpx.AsyncClient(transport=httpx.MockTransport(
        lambda request: calls.append(request) or httpx.Response(200, json={
            "data": [{"b64_json": base64.b64encode(image()).decode()}],
        }),
    )) as http:
        await OpenAIImageClient(settings(), http_client=http).edit(
            prompt="All views of the same product", product=media(), layout=media(),
            additional_products=[media() for _ in range(13)], character=media(),
        )
    assert len(calls) == 1
    assert calls[0].content.count(b'name="image[]"') == 16


@pytest.mark.asyncio
@pytest.mark.parametrize("extras", [
    [media() for _ in range(14)],
    [UploadedMedia(bytes=b"not a readable image", mime_type="image/png")],
    [UploadedMedia(bytes=image((24, 36)), mime_type="image/jpeg")],
])
async def test_invalid_or_excess_supporting_product_views_never_post(extras):
    calls = []
    async with httpx.AsyncClient(transport=httpx.MockTransport(
        lambda request: calls.append(request) or httpx.Response(500),
    )) as http:
        with pytest.raises(AppError, match="OPENAI_IMAGE_VALIDATION_FAILED"):
            await OpenAIImageClient(settings(), http_client=http).edit(
                prompt="Product", product=media(), layout=media(), additional_products=extras,
            )
    assert calls == []


@pytest.mark.parametrize("presenter_anchor", [False, True])
@pytest.mark.parametrize("custom_character", [False, True])
def test_multiview_prompt_keeps_product_layout_and_actor_indices_distinct(
    presenter_anchor, custom_character,
):
    prompt = module._image_prompt(
        {"characterKey": "actor"} if custom_character else {},
        {"imagePrompt": "Hold the cup"}, product_reference_count=2,
        presenter_anchor=presenter_anchor,
    )
    assert "Images 1 through 2" in prompt
    assert "same seller product" in prompt
    assert "with the exact product from all product reference images 1 through 2" in prompt
    assert "primary appearance and supporting views' visible geometry" in prompt
    assert "with the exact product from image 1," not in prompt
    assert "Image 3 is the exact source scene opening frame" in prompt
    assert "composition image 3" in prompt
    assert "from image 3" in prompt
    assert "unobserved" in prompt and "intact finished outer body" in prompt
    assert "sole product identity reference" not in prompt
    assert "person or face is visible in image 2" not in prompt
    if custom_character:
        assert "Image 4 is the authorized target character identity" in prompt
    elif presenter_anchor:
        assert "Image 4 is the previously generated target presenter" in prompt
        assert "even if image 4 is a montage" in prompt


def test_single_product_prompt_is_byte_compatible():
    prompt = module._image_prompt({}, {"imagePrompt": "Product on a table"})
    assert hashlib.sha256(prompt.encode()).hexdigest() == (
        "62877753544039fe5864ad78df8237885e4311c853273cfb47615ad2648f9460"
    )


def add_supporting_view(value, monkeypatch):
    repair, row, _, _, _, _, _ = value
    data = image((40, 60), "green")
    repair.media.objects["supporting"] = data
    row.context_json["p0"] = {"additionalProductReferences": [{
        "role": "product", "storageKey": "supporting", "mimeType": "image/png",
        "mediaHash": hashlib.sha256(data).hexdigest(),
    }]}
    # Policy/ledger are independently tested; this fixture isolates the image evidence contract.
    monkeypatch.setattr(module, "require_generation_policy", AsyncMock())
    monkeypatch.setattr(module, "reserve_generation_attempt", AsyncMock(return_value=(None, True)))
    return data


@pytest.mark.asyncio
async def test_conditioning_attaches_supporting_view_and_binds_all_hashes(setup, monkeypatch):
    supporting = add_supporting_view(setup, monkeypatch)
    repair, row, op, client, _, _, _ = setup
    first = await prepare(setup)
    hashes = [row.context_json["productMediaHash"], hashlib.sha256(supporting).hexdigest()]
    assert client.calls[0]["product"].bytes == repair.media.objects["product"]
    assert [value.bytes for value in client.calls[0]["additional_products"]] == [supporting]
    assert "Image 3 is the exact source scene opening frame" in client.calls[0]["prompt"]
    assert first["presenterIdentity"]["productReferenceHashes"] == hashes
    assert op.result_json["generationExpectations"]["productReferenceHashes"] == hashes
    assert await prepare(setup) == first
    assert len(client.calls) == 1


@pytest.mark.asyncio
async def test_single_product_does_not_add_new_request_fields(setup):
    _, _, _, client, _, _, _ = setup
    result = await prepare(setup)
    assert "additional_products" not in client.calls[0]
    assert "productReferenceHashes" not in result["presenterIdentity"]


@pytest.mark.asyncio
async def test_changed_supporting_bytes_fail_before_image_submission(setup, monkeypatch):
    add_supporting_view(setup, monkeypatch)
    repair, _, _, client, _, _, _ = setup
    repair.media.objects["supporting"] = image((40, 60), "orange")
    with pytest.raises(AppError, match="SMART_REMAKE_INPUT_CHANGED"):
        await prepare(setup)
    assert client.calls == []


@pytest.mark.asyncio
async def test_frozen_snapshot_without_supporting_view_cannot_create_new_image(setup, monkeypatch):
    repair, row, op, client, scene, save, _ = setup
    frozen = copy.deepcopy(op.result_json)
    add_supporting_view(setup, monkeypatch)
    from test_smart_remake_image_workflow import refresh_expectations

    refresh_expectations(row)
    op.result_json = frozen
    with pytest.raises(AppError, match="SMART_REMAKE_EXPECTATIONS_CHANGED"):
        await module.prepare_scene_image(
            repair=repair, row=row, operation=op, index=0, compiled_scene=scene,
            image_client=client, save=save, ensure_active=lambda: None,
        )
    assert client.calls == []


@pytest.mark.asyncio
async def test_supporting_view_changes_invalidate_submitted_slot_without_resubmission(
    setup, monkeypatch,
):
    add_supporting_view(setup, monkeypatch)
    repair, row, op, client, _, _, _ = setup
    await prepare(setup)
    changed = image((40, 60), "orange")
    repair.media.objects["supporting"] = changed
    row.context_json["p0"]["additionalProductReferences"][0]["mediaHash"] = (
        hashlib.sha256(changed).hexdigest()
    )
    with pytest.raises(AppError, match="OPENAI_IMAGE_SUBMISSION_UNRESOLVED"):
        await prepare(setup)
    assert len(client.calls) == 1
    assert op.result_json["needsReconciliation"] is True


@pytest.mark.asyncio
async def test_same_multiview_scope_reuses_presenter_and_changed_views_invalidate_anchor(
    presenter_setup, monkeypatch,
):
    supporting = add_supporting_view(presenter_setup, monkeypatch)
    repair, row, op, client, _, _, _ = presenter_setup
    first = await prepare_unit(presenter_setup)
    await prepare_unit(presenter_setup, 1)
    assert client.calls[1]["character"].bytes == repair.media.objects[first["storageKey"]]
    assert "Image 4 is the previously generated target presenter" in client.calls[1]["prompt"]
    assert row.context_json["presenterIdentityAnchor"]["productReferenceHashes"] == [
        row.context_json["productMediaHash"], hashlib.sha256(supporting).hexdigest(),
    ]
    changed = image((40, 60), "orange")
    repair.media.objects["supporting"] = changed
    row.context_json["p0"]["additionalProductReferences"][0]["mediaHash"] = (
        hashlib.sha256(changed).hexdigest()
    )
    op.result_json = {}
    await prepare_unit(presenter_setup)
    assert "character" not in client.calls[-1]
    assert len(client.calls) == 3
