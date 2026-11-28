# ruff: noqa: F811 -- shared offline fixtures are resolved by pytest.
"""Four real edits preserve source-frame authority and optional generated continuity."""

from __future__ import annotations

import base64
import copy
import hashlib
from unittest.mock import AsyncMock

import httpx
import pytest
from test_smart_remake_image_workflow import image, setup  # noqa: F401
from test_smart_remake_openai_images import media, settings
from test_smart_remake_presenter_conditioning import prepare_unit, presenter_setup  # noqa: F401

from viraldy.modules.smart_remake import image_workflow as module
from viraldy.modules.smart_remake.engine.openai_images import OpenAIImageClient
from viraldy.shared.errors.base import AppError


def twelve_seconds(value):
    _, row, operation, _, _, _, _ = value
    plan = row.context_json["renderPlan"]
    plan["videoModel"] = "wan/3-0-video"
    plan["groups"] = [
        {
            "id": f"group-{i}",
            "renderUnitIds": [unit["id"]],
            "rawDurationFrames": 144,
            "targetDurationFrames": 144,
        }
        for i, unit in enumerate(plan["units"])
    ]
    for unit in plan["units"]:
        unit.update(rawDurationFrames=144, targetDurationFrames=144)
    operation.result_json["renderPlan"] = copy.deepcopy(plan)
    if not operation.result_json.get("images") and not operation.result_json.get("tasks"):
        operation.result_json["conditioningPolicy"] = "source-frame-authority-v1"
    for scene in row.context_json["sceneMap"]["scenes"]:
        scene["shotPlan"] = {"shots": [{"stateAfter": "contradictory top-down cup on coaster"}]}
        scene["videoPrompt"] = "contradictory top-down cup on coaster"


def test_frame_authority_removes_automatic_single_panel_claims_but_keeps_seller_requirements():
    prompt = module._image_prompt(
        {
            "conditioningPolicy": "source-frame-authority-v1",
            "p0": {"requirements": {"intent": "Keep the pink handle visible"}},
        },
        {
            "imagePrompt": "AUTO_SINGLE_PANEL_PRESENTER",
            "videoPrompt": "AUTO_WRONG_END_STATE",
            "shotPlan": {"shots": [{"stateAfter": "AUTO_WRONG_POSE"}]},
            "sourceSegment": {"composition": "AUTO_SINGLE_PANEL_LAYOUT"},
            "userEdits": "SELLER: use a plain blue shirt",
        },
    )
    assert "SELLER: use a plain blue shirt" in prompt
    assert "Keep the pink handle visible" in prompt
    assert "AUTO_" not in prompt
    assert "Preserve the exact panel count and layout from image 2" in prompt
    assert "source frame is authoritative" in prompt


@pytest.mark.asyncio
async def test_fresh_wan12_keeps_four_calls_and_passes_previous_generated_end_to_next_opening(
    presenter_setup,
):
    twelve_seconds(presenter_setup)
    repair, _, operation, client, _, _, _ = presenter_setup
    records = []
    for index, role in [(0, "opening"), (0, "ending"), (1, "opening"), (1, "ending")]:
        records.append(await prepare_unit(presenter_setup, index, role))
    assert len(client.calls) == 4
    assert "Render its stateAfter" not in client.calls[1]["prompt"]
    assert "contradictory top-down cup on coaster" not in client.calls[1]["prompt"]
    assert "source frame is authoritative" in client.calls[1]["prompt"]
    assert (
        client.calls[2]["continuity_frame"].bytes == repair.media.objects[records[1]["storageKey"]]
    )
    assert client.calls[2]["character"].bytes == repair.media.objects[records[0]["storageKey"]]
    binding = records[2]["continuityReference"]
    assert binding["mediaHash"] == records[1]["mediaHash"]
    assert binding["requestHash"] == records[1]["requestHash"]
    assert binding["referenceFrame"] == records[1]["referenceFrame"]
    assert records[2]["referenceFrame"]["frame"] == 120
    assert binding["referenceFrame"]["frame"] == 119
    assert "when compatible" in client.calls[2]["prompt"]
    assert "current source" in client.calls[2]["prompt"]
    assert operation.result_json["conditioningPolicy"] == "source-frame-authority-v1"
    for index, role in [(0, "opening"), (0, "ending"), (1, "opening"), (1, "ending")]:
        await prepare_unit(presenter_setup, index, role)
    assert len(client.calls) == 4


@pytest.mark.asyncio
async def test_unknown_fresh12_opening_does_not_resubmit_after_reference_change(presenter_setup):
    twelve_seconds(presenter_setup)
    repair, _, operation, client, _, _, _ = presenter_setup
    await prepare_unit(presenter_setup)
    await prepare_unit(presenter_setup, frame_role="ending")
    client.edit = AsyncMock(side_effect=TimeoutError())
    with pytest.raises(AppError, match="OPENAI_IMAGE_SUBMISSION_UNRESOLVED"):
        await prepare_unit(presenter_setup, 1)
    assert operation.result_json["images"]["1"]["continuityReference"]["mediaHash"]
    with pytest.raises(AppError, match="OPENAI_IMAGE_SUBMISSION_UNRESOLVED"):
        await prepare_unit(presenter_setup, 1)
    assert client.edit.await_count == 1


@pytest.mark.asyncio
async def test_existing_twelve_second_slots_keep_old_policy(presenter_setup):
    await prepare_unit(presenter_setup)
    twelve_seconds(presenter_setup)
    _, _, operation, _, _, _, _ = presenter_setup
    # Changing the plan's image semantics must reconcile existing submissions, not replace them.
    with pytest.raises(AppError, match="OPENAI_IMAGE_SUBMISSION_UNRESOLVED"):
        await prepare_unit(presenter_setup)
    assert "conditioningPolicy" not in operation.result_json


@pytest.mark.asyncio
async def test_changed_previous_generated_ending_never_reaches_next_paid_edit(presenter_setup):
    twelve_seconds(presenter_setup)
    repair, _, _, client, _, _, _ = presenter_setup
    await prepare_unit(presenter_setup)
    ending = await prepare_unit(presenter_setup, frame_role="ending")
    repair.media.objects[ending["storageKey"]] = image(color="black")
    with pytest.raises(AppError, match="SMART_REMAKE_IMAGE_ASSET_INVALID"):
        await prepare_unit(presenter_setup, 1)
    assert len(client.calls) == 2


@pytest.mark.asyncio
async def test_fourteen_product_views_keep_actor_without_false_continuity_binding(
    presenter_setup,
    monkeypatch,
):
    twelve_seconds(presenter_setup)
    repair, row, _, client, _, _, _ = presenter_setup
    references = []
    for index in range(13):
        key = f"supporting-{index}"
        data = image((24, 36), (index * 10, 90, 150))
        repair.media.objects[key] = data
        references.append(
            {
                "role": "product",
                "storageKey": key,
                "mimeType": "image/png",
                "mediaHash": hashlib.sha256(data).hexdigest(),
            }
        )
    row.context_json["p0"] = {"additionalProductReferences": references}
    monkeypatch.setattr(module, "require_generation_policy", AsyncMock())
    monkeypatch.setattr(module, "reserve_generation_attempt", AsyncMock(return_value=(None, True)))
    await prepare_unit(presenter_setup)
    await prepare_unit(presenter_setup, frame_role="ending")
    opening = await prepare_unit(presenter_setup, 1)
    assert len(client.calls[-1]["additional_products"]) == 13
    assert "character" in client.calls[-1]
    assert "continuity_frame" not in client.calls[-1]
    assert "continuityReference" not in opening
    assert "previous clip's generated ending" not in client.calls[-1]["prompt"]


@pytest.mark.asyncio
@pytest.mark.parametrize("product_count,actor,expected", [(2, True, 5), (14, True, 16)])
async def test_openai_optional_continuity_never_displaces_product_views(
    product_count, actor, expected
):
    calls = []
    products = [media() for _ in range(product_count)]
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: calls.append(request)
            or httpx.Response(
                200,
                json={
                    "data": [{"b64_json": base64.b64encode(image()).decode()}],
                },
            ),
        )
    ) as http:
        await OpenAIImageClient(settings(), http_client=http).edit(
            prompt="Product",
            product=products[0],
            additional_products=products[1:],
            layout=media(),
            character=media() if actor else None,
            continuity_frame=media(),
        )
    assert calls[0].content.count(b'name="image[]"') == expected
    assert (b'filename="continuity-reference"' in calls[0].content) is (expected < 16)
