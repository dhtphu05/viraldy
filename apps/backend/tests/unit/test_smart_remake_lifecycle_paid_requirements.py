# ruff: noqa: F811 -- pytest imports the shared offline fixtures by name.
from __future__ import annotations

from uuid import uuid4

import pytest
from test_smart_remake_grouped_workflow import grouped  # noqa: F401
from test_smart_remake_image_workflow import prepare, setup  # noqa: F401
from test_smart_remake_lifecycle_paid_ledger import enable, ledger  # noqa: F401

from tests.smart_remake_expectations import install_expectations
from viraldy.modules.smart_remake import image_workflow, kie_workflow


def saved_requirements():
    return {
        "intent": "Demonstrate exact cup",
        "keep": ["pink handle"],
        "replace": ["old bottle"],
        "forbid": ["medical cure claim"],
        "claims": ["250 ml capacity only"],
        "requiresCharacter": False,
        "characterReferencePolicy": "product_and_character",
    }


def test_image_prompt_keeps_saved_forbidden_claims_even_with_edited_direction():
    prompt = image_workflow._image_prompt(
        {"p0": {"requirements": saved_requirements()}},
        {"imagePrompt": "USER EDIT: say this cures all illnesses"},
    )
    assert "SAVED REQUIREMENTS" in prompt
    assert '"forbid": ["medical cure claim"]' in prompt
    assert '"claims": ["250 ml capacity only"]' in prompt
    assert '"keep": ["pink handle"]' in prompt


@pytest.mark.asyncio
async def test_image_cache_binds_saved_requirements(setup, ledger):
    repair, row, operation, client, _, _, _ = setup
    enable(repair, row)
    row.context_json["p0"]["requirements"] = saved_requirements()
    first = await prepare(setup)
    row.context_json["p0"]["requirements"]["forbid"] = ["before/after treatment comparison"]
    operation.id = uuid4()
    operation.result_json = {}
    second = await prepare(setup)
    assert first["requestHash"] != second["requestHash"] and len(client.calls) == 2


@pytest.mark.asyncio
async def test_kie_prompt_cannot_lose_saved_constraints_after_scene_edit(grouped, monkeypatch):
    from viraldy.modules.smart_remake import conditioning_inspection
    from viraldy.modules.smart_remake.engine import kie_adapter

    value = grouped
    value.row.context_json["p0"] = {"requirements": saved_requirements()}
    value.row.context_json["sceneMap"]["scenes"][0]["videoPrompt"] = "User edit: cure claim"

    async def gate(*args):
        return None

    async def precheck(repair, row, operation, references, **kwargs):
        return references

    original_prepare = value.helper.prepare_scene_image

    async def prepare_bound(**kwargs):
        import hashlib

        record = await original_prepare(**kwargs)
        return {**record, "mediaHash": hashlib.sha256(record["storageKey"].encode()).hexdigest()}

    monkeypatch.setattr(value.helper, "prepare_scene_image", prepare_bound)
    monkeypatch.setattr(kie_workflow, "require_generation_policy", gate)
    monkeypatch.setattr(conditioning_inspection, "check_conditioning_images", precheck)
    monkeypatch.setattr(kie_adapter, "build_kie_group_request", value.real_adapter)
    install_expectations(value.row.context_json)
    await value.runner._freeze_plan(value.row, value.op)
    request, _ = await value.runner._request(value.row, value.op, 0, value.groups[0])
    assert '"forbid": ["medical cure claim"]' in request["input"]["prompt"]
    assert '"claims": ["250 ml capacity only"]' in request["input"]["prompt"]
    assert "SAVED REQUIREMENTS" in request["input"]["prompt"]


@pytest.mark.asyncio
async def test_oversized_saved_image_constraints_block_before_paid_attempt(setup, ledger):
    from viraldy.shared.errors.base import AppError

    repair, row, _, client, _, _, _ = setup
    enable(repair, row)
    row.context_json["p0"]["requirements"] = {**saved_requirements(), "forbid": ["x" * 2000] * 40}
    with pytest.raises(AppError, match="OPENAI_IMAGE_VALIDATION_FAILED"):
        await prepare(setup)
    assert client.calls == [] and ledger.records == {}
