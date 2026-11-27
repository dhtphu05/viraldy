# ruff: noqa: F811 -- pytest resolves imported fixtures by name.
"""Canonical presenter identity survives sparse metadata, caches and restore."""

from __future__ import annotations

import copy
from unittest.mock import AsyncMock

import pytest
from test_smart_remake_image_workflow import image, setup  # noqa: F401
from test_smart_remake_presenter_conditioning import (  # noqa: F401
    prepare_unit,
    presenter_setup,
)

from viraldy.modules.smart_remake import image_workflow as module
from viraldy.shared.errors.base import AppError


def anchor(record):
    return {key: record[key] for key in ("requestHash", "mediaHash", "storageKey")}


@pytest.mark.asyncio
async def test_first_presenter_is_committed_with_one_canonical_identity(presenter_setup):
    repair, row, _, _, _, _, _ = presenter_setup
    first = await prepare_unit(presenter_setup)
    identity = row.context_json["presenterIdentityAnchor"]
    assert identity["anchor"] == anchor(first)
    assert identity["policyVersion"] == module.PRESENTER_IDENTITY_POLICY_VERSION
    assert identity["sourceMediaHash"] == first["presenterIdentity"]["sourceMediaHash"]
    committed = [update for update in repair.repository.updates
                 if "presenterIdentityAnchor" in update]
    assert len(committed) == 1 and committed[0]["imageAssets"][first["requestHash"]] == first


@pytest.mark.asyncio
@pytest.mark.parametrize("presence", ["none", "hands_only", None])
async def test_available_identity_is_sent_even_when_frame_presence_is_sparse(
    presenter_setup, presence,
):
    repair, row, _, client, _, _, _ = presenter_setup
    first = await prepare_unit(presenter_setup)
    row.context_json["referenceAnalysis"]["sourceShots"][1]["subjectPresence"] = presence
    second = await prepare_unit(presenter_setup, 1)
    assert client.calls[-1]["character"].bytes == repair.media.objects[first["storageKey"]]
    assert second["presenterIdentity"]["anchor"] == anchor(first)
    assert "Do not add a person or face" in client.calls[-1]["prompt"]


@pytest.mark.asyncio
async def test_new_slot_does_not_reuse_an_independent_cached_actor(presenter_setup):
    repair, row, op, client, _, _, _ = presenter_setup
    independent = await prepare_unit(presenter_setup, 1)
    # Simulate an older cache whose canonical choice has not yet been recorded.
    row.context_json.pop("presenterIdentityAnchor", None)
    row.context_json["imageAssets"].pop(independent["requestHash"])
    op.result_json = {}
    first = await prepare_unit(presenter_setup)
    row.context_json["imageAssets"][independent["requestHash"]] = independent
    op.result_json = {}  # A new operation/slot, not a replay of the independent attempt.
    new = await prepare_unit(presenter_setup, 1)
    assert new["requestHash"] != independent["requestHash"]
    assert client.calls[-1]["character"].bytes == repair.media.objects[first["storageKey"]]
    assert new["presenterIdentity"]["anchor"] == anchor(first)
    assert len(client.calls) == 3


@pytest.mark.asyncio
async def test_canonical_choice_uses_source_frame_then_remains_frozen(presenter_setup):
    _, row, op, _, _, _, _ = presenter_setup
    later = await prepare_unit(presenter_setup, 1)
    row.context_json.pop("presenterIdentityAnchor", None)
    later_cache = row.context_json["imageAssets"].pop(later["requestHash"])
    op.result_json = {}
    earlier = await prepare_unit(presenter_setup)
    row.context_json["imageAssets"][later["requestHash"]] = later_cache
    row.context_json.pop("presenterIdentityAnchor", None)
    identity = earlier["presenterIdentity"]
    selected = await module._presenter_anchor(
        presenter_setup[0], row, identity, {},
    )
    assert selected[1] == anchor(earlier)
    frozen = copy.deepcopy(row.context_json["presenterIdentityAnchor"])
    competing = copy.deepcopy(later)
    competing["requestHash"] = "0" * 64
    competing["referenceFrame"]["frame"] = 0
    row.context_json["imageAssets"][competing["requestHash"]] = competing
    selected = await module._presenter_anchor(presenter_setup[0], row, identity, {})
    assert selected[1] == anchor(earlier)
    assert row.context_json["presenterIdentityAnchor"] == frozen


@pytest.mark.asyncio
async def test_canonical_first_image_restores_without_using_itself_as_reference(presenter_setup):
    _, _, op, client, _, _, _ = presenter_setup
    first = await prepare_unit(presenter_setup)
    await prepare_unit(presenter_setup, 1)
    op.result_json = {}
    assert await prepare_unit(presenter_setup) == first
    assert "character" not in client.calls[0]
    assert len(client.calls) == 2


@pytest.mark.asyncio
async def test_completed_independent_slot_keeps_its_original_inputs(presenter_setup):
    _, row, op, client, _, _, _ = presenter_setup
    previous = await prepare_unit(presenter_setup, 1)
    row.context_json.pop("presenterIdentityAnchor", None)
    saved = row.context_json["imageAssets"].pop(previous["requestHash"])
    previous_operation = copy.deepcopy(op.result_json)
    op.result_json = {}
    await prepare_unit(presenter_setup)
    row.context_json["imageAssets"][previous["requestHash"]] = saved
    op.result_json = previous_operation
    assert await prepare_unit(presenter_setup, 1) == previous
    assert len(client.calls) == 2


@pytest.mark.asyncio
async def test_unknown_independent_slot_does_not_borrow_a_new_identity(presenter_setup):
    _, row, op, client, _, _, _ = presenter_setup
    edit = client.edit
    client.edit = AsyncMock(side_effect=TimeoutError("response lost"))
    with pytest.raises(AppError, match="OPENAI_IMAGE_SUBMISSION_UNRESOLVED"):
        await prepare_unit(presenter_setup, 1)
    retained = copy.deepcopy(op.result_json)
    client.edit = edit
    op.result_json = {}
    await prepare_unit(presenter_setup)
    op.result_json = retained
    client.edit = AsyncMock(side_effect=AssertionError("must not repeat image request"))
    with pytest.raises(AppError, match="OPENAI_IMAGE_SUBMISSION_UNRESOLVED"):
        await prepare_unit(presenter_setup, 1)
    assert client.edit.await_count == 0
    assert op.result_json["images"]["1"]["presenterIdentity"]["mode"] == "synthetic"


@pytest.mark.asyncio
async def test_metadata_only_presence_changes_do_not_rewrite_retained_identity(presenter_setup):
    _, row, _, client, _, _, _ = presenter_setup
    first = await prepare_unit(presenter_setup)
    row.context_json["referenceAnalysis"]["sourceShots"][0]["subjectPresence"] = "hands_only"
    assert await prepare_unit(presenter_setup) == first
    assert len(client.calls) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["submitting", "submitted", "completed"])
async def test_policy_upgrade_never_swaps_retained_slot_to_another_cached_image(
    presenter_setup, monkeypatch, status,
):
    _, _, op, client, _, _, _ = presenter_setup
    with monkeypatch.context() as scoped:
        scoped.setattr(module, "PRESENTER_IDENTITY_POLICY_VERSION", "previous-policy")
        await prepare_unit(presenter_setup)
    retained = copy.deepcopy(op.result_json)
    retained["images"]["0"]["status"] = status
    op.result_json = {}
    await prepare_unit(presenter_setup)
    assert len(client.calls) == 2
    op.result_json = retained
    with pytest.raises(AppError, match="OPENAI_IMAGE_SUBMISSION_UNRESOLVED"):
        await prepare_unit(presenter_setup)
    assert len(client.calls) == 2
    assert op.result_json["images"]["0"]["presenterIdentity"]["policyVersion"] == "previous-policy"


@pytest.mark.asyncio
@pytest.mark.parametrize("field", ["policyVersion", "sourceMediaHash", "productMediaHash"])
async def test_canonical_identity_never_crosses_source_product_or_policy_scope(
    presenter_setup, field,
):
    _, row, op, client, _, _, _ = presenter_setup
    first = await prepare_unit(presenter_setup)
    row.context_json["presenterIdentityAnchor"][field] = "different"
    row.context_json["imageAssets"][first["requestHash"]]["presenterIdentity"][field] = "different"
    op.result_json = {}
    second = await prepare_unit(presenter_setup, 1)
    assert "character" not in client.calls[-1]
    assert row.context_json["presenterIdentityAnchor"]["anchor"] == anchor(second)


def test_synthetic_prompt_locks_hair_and_wardrobe_without_source_graphics():
    prompt = module._image_prompt({}, {"imagePrompt": "Person holds a cup"}, presenter_anchor=True)
    assert "same face, hairstyle and wardrobe" in prompt
    assert "plain unbranded top" in prompt
    assert "source person's clothing or graphic T-shirt" in prompt
    assert "person region" in prompt


@pytest.mark.parametrize("role", ["opening", "ending"])
def test_conditioning_uses_source_panel_layout_not_identity_anchor_layout(role):
    prompt = module._image_prompt({}, {
        "imagePrompt": "Four-panel source intro", "videoPrompt": "Full-frame product close-up",
    }, frame_role=role, presenter_anchor=True)
    assert "without a collage" not in prompt
    assert "panel count and layout from image 2" in prompt
    assert "never copy the anchor's layout" in prompt


def test_product_cutaway_is_a_construction_reference_for_normal_finished_body():
    prompt = module._image_prompt({}, {"imagePrompt": "A person drinks from the cup"})
    assert "cutaway or section diagram" in prompt
    assert "intact finished outer body" in prompt
    assert "explicitly requests a section illustration" in prompt


@pytest.mark.parametrize("product", [
    {"productName": "STAR T-shirt", "productType": "T-shirt",
     "mustPreserve": ["Printed STAR graphic and logo"]},
    {"productName": "Blue jacket", "productType": "Jacket",
     "visualIdentity": {"colors": ["blue"], "branding": "silver chest logo"}},
])
@pytest.mark.parametrize("custom", [False, True])
def test_target_garment_design_takes_priority_over_supporting_or_anchor_wardrobe(product, custom):
    context = {"productLock": product, **({"characterKey": "authorized"} if custom else {})}
    prompt = module._image_prompt(context, {
        "imagePrompt": "The presenter wears the exact uploaded target garment",
    }, presenter_anchor=not custom)
    assert "target garment's design, graphics, colors and branding" in prompt
    assert "take precedence over supporting wardrobe and the identity anchor's outfit" in prompt
    assert product["productName"] in prompt
    if custom:
        assert "authorized target character" in prompt
        assert "fictional adult Vietnamese presenter" not in prompt
    else:
        assert "plain unbranded top as supporting wardrobe only" in prompt


def test_policy_change_invalidates_previous_presenter_conditioning_contract():
    assert module.PRESENTER_IDENTITY_POLICY_VERSION != "fictional-vietnamese-presenter-v1"
