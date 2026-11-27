# ruff: noqa: F811 -- pytest fixture imports are intentionally injected by name.
"""Offline identity replacement and source-bound conditioning bookend regressions."""

from __future__ import annotations

import copy
import hashlib
from unittest.mock import AsyncMock

import pytest
from test_smart_remake_image_workflow import (  # noqa: F401
    image,
    refresh_expectations,
    setup,
)

from viraldy.modules.smart_remake import image_workflow as module
from viraldy.shared.errors.base import AppError


@pytest.fixture
def presenter_setup(setup):
    repair, row, op, client, scene, _, _ = setup
    second = {**copy.deepcopy(scene), "id": "unit-two"}
    row.context_json["renderPlan"]["units"].append(
        {"id": "unit-two", "sceneIndex": 1, "sourceSceneId": "source-two"}
    )
    row.context_json["sceneMap"]["scenes"].append(second)
    row.context_json["sourceSceneMap"]["scenes"].append(
        {"id": "source-two", "startFrame": 120, "endFrame": 192}
    )
    row.context_json["sourceOpeningFrames"]["source-two"] = {
        **row.context_json["sourceOpeningFrames"]["source-scene"], "frame": 120,
    }
    row.context_json["referenceAnalysis"] = {
        "subjectPresence": "person",
        "sourceShots": [
            {"startSecond": 2, "endSecond": 5, "subjectPresence": "person"},
            {"startSecond": 5, "endSecond": 8, "subjectPresence": "person"},
        ],
    }

    async def edit(**kwargs):
        assert any(i.get("status") == "submitting" for i in op.result_json["images"].values())
        client.calls.append(kwargs)
        data = image(color="orange")
        return {
            "bytes": data, "mimeType": "image/png",
            "mediaHash": hashlib.sha256(data).hexdigest(), "model": kwargs["model"],
        }

    client.edit = edit
    return setup


async def prepare_unit(value, index=0, frame_role="opening"):
    repair, row, op, client, _, save, _ = value
    refresh_expectations(row)
    op.result_json.update(
        generationExpectations=copy.deepcopy(row.context_json["generationExpectations"]),
        expectationsHash=row.context_json["expectationsHash"],
    )
    return await module.prepare_scene_image(
        repair=repair, row=row, operation=op, index=index,
        compiled_scene=row.context_json["sceneMap"]["scenes"][index],
        image_client=client, save=save, ensure_active=lambda: None, frame_role=frame_role,
    )


def test_default_prompt_replaces_source_face_with_distinct_fictional_vietnamese_adult():
    prompt = module._image_prompt({}, {"imagePrompt": "Person holds a cup"})
    assert "fictional adult Vietnamese presenter" in prompt
    assert "distinct from every person in image 2" in prompt
    assert "Do not infer the source person's ethnicity" in prompt
    assert "pose" in prompt and "camera" in prompt and "sole product identity" in prompt
    assert "Do not add a person or face" in prompt


@pytest.mark.asyncio
async def test_generated_presenter_frame_is_real_third_image_for_later_bookends(presenter_setup):
    repair, row, op, client, _, _, history = presenter_setup
    first = await prepare_unit(presenter_setup)
    second = await prepare_unit(presenter_setup, 1)
    assert "character" not in client.calls[0]
    assert client.calls[1]["character"].bytes == repair.media.objects[first["storageKey"]]
    assert "previously generated target presenter" in client.calls[1]["prompt"]
    assert second["presenterIdentity"]["anchor"]["mediaHash"] == first["mediaHash"]
    assert history[-2]["images"]["1"]["presenterIdentity"] == second["presenterIdentity"]
    assert row.context_json["imageAssets"][second["requestHash"]] == second
    assert op.result_json["images"]["1"]["presenterIdentity"] == second["presenterIdentity"]


@pytest.mark.asyncio
async def test_presenter_anchor_and_first_frame_are_stable_across_restore(presenter_setup):
    _, _, op, client, _, _, _ = presenter_setup
    first = await prepare_unit(presenter_setup)
    second = await prepare_unit(presenter_setup, 1)
    op.result_json = {}
    assert await prepare_unit(presenter_setup) == first
    assert await prepare_unit(presenter_setup, 1) == second
    assert len(client.calls) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("presence", ["none", "hands_only"])
async def test_product_or_hands_only_openings_do_not_become_face_anchors(presenter_setup, presence):
    _, row, _, client, _, _, _ = presenter_setup
    row.context_json["referenceAnalysis"]["sourceShots"][0]["subjectPresence"] = presence
    first = await prepare_unit(presenter_setup)
    await prepare_unit(presenter_setup, 1)
    assert first["presenterIdentity"]["eligibleAnchor"] is False
    assert all("character" not in request for request in client.calls)


@pytest.mark.asyncio
async def test_product_only_shot_keeps_identity_reference_without_adding_a_person(presenter_setup):
    repair, row, _, client, _, _, _ = presenter_setup
    first = await prepare_unit(presenter_setup)
    row.context_json["referenceAnalysis"]["sourceShots"][1]["subjectPresence"] = "none"
    await prepare_unit(presenter_setup, 1)
    assert client.calls[-1]["character"].bytes == repair.media.objects[first["storageKey"]]
    assert "its presence does not require a person in this frame" in client.calls[-1]["prompt"]


@pytest.mark.asyncio
async def test_explicit_character_reference_wins_over_generated_presenter(presenter_setup):
    repair, row, op, client, _, _, _ = presenter_setup
    await prepare_unit(presenter_setup)
    character = image((35, 45), "blue")
    repair.media.objects["character"] = character
    row.context_json.update(
        characterKey="character", characterMimeType="image/png",
        characterMediaHash=hashlib.sha256(character).hexdigest(),
    )
    op.result_json = {}
    result = await prepare_unit(presenter_setup, 1)
    assert client.calls[-1]["character"].bytes == character
    assert "authorized target character" in client.calls[-1]["prompt"]
    assert "fictional adult Vietnamese presenter" not in client.calls[-1]["prompt"]
    assert result["presenterIdentity"]["mode"] == "custom"


@pytest.mark.asyncio
@pytest.mark.parametrize("tamper", ["hash", "ownership", "format", "missing"])
async def test_invalid_presenter_anchor_never_submits_another_image(presenter_setup, tamper):
    repair, row, _, client, _, _, _ = presenter_setup
    first = await prepare_unit(presenter_setup)
    record = row.context_json["imageAssets"][first["requestHash"]]
    if tamper == "hash":
        repair.media.objects[first["storageKey"]] = image(color="blue")
    elif tamper == "ownership":
        record["storageKey"] = "workspaces/other/smart-remake/project/images/anchor"
    elif tamper == "format":
        repair.media.objects[first["storageKey"]] = b"not a png"
        record["mediaHash"] = hashlib.sha256(b"not a png").hexdigest()
    else:
        del repair.media.objects[first["storageKey"]]
    with pytest.raises(AppError, match="SMART_REMAKE_IMAGE_ASSET_INVALID"):
        await prepare_unit(presenter_setup, 1)
    assert len(client.calls) == 1


@pytest.mark.asyncio
async def test_policy_upgrade_invalidates_image_cache_and_ignores_old_face_anchors(
    presenter_setup, monkeypatch,
):
    _, _, op, client, _, _, _ = presenter_setup
    with monkeypatch.context() as scoped:
        scoped.setattr(module, "PRESENTER_IDENTITY_POLICY_VERSION", "old-source-face-policy")
        old = await prepare_unit(presenter_setup)
    op.result_json = {}
    new = await prepare_unit(presenter_setup)
    assert old["requestHash"] != new["requestHash"]
    assert "character" not in client.calls[-1]
    assert new["presenterIdentity"]["policyVersion"] == module.PRESENTER_IDENTITY_POLICY_VERSION


@pytest.mark.asyncio
async def test_unknown_image_intent_cannot_turn_into_replacement_after_policy_change(
    presenter_setup, monkeypatch,
):
    _, _, op, client, _, _, _ = presenter_setup
    client.edit = AsyncMock(side_effect=TimeoutError("accepted response lost"))
    with pytest.raises(AppError, match="OPENAI_IMAGE_SUBMISSION_UNRESOLVED"):
        await prepare_unit(presenter_setup)
    monkeypatch.setattr(module, "PRESENTER_IDENTITY_POLICY_VERSION", "new-presenter-policy")
    with pytest.raises(AppError, match="OPENAI_IMAGE_SUBMISSION_UNRESOLVED"):
        await prepare_unit(presenter_setup)
    assert client.edit.await_count == 1 and op.result_json["needsReconciliation"] is True


@pytest.mark.asyncio
async def test_ending_uses_exact_last_source_frame_and_terminal_state(presenter_setup, monkeypatch):
    repair, row, op, client, scene, _, _ = presenter_setup
    scene["shotPlan"] = {"shots": [{"stateBefore": "lid closed", "stateAfter": "lid open"}]}
    opening, ending = image((30, 20), "white"), image((30, 20), "blue")
    frames = []

    def extract(data, frame):
        assert data == repair.media.objects["source"]
        frames.append(frame)
        return opening if frame == 48 else ending

    monkeypatch.setattr(module, "extract_layout_frame", extract)
    first = await prepare_unit(presenter_setup)
    last = await prepare_unit(presenter_setup, frame_role="ending")
    assert frames == [48, 119]
    assert client.calls[0]["layout"].bytes == opening
    assert client.calls[1]["layout"].bytes == ending
    assert "Render its stateAfter" in client.calls[1]["prompt"]
    assert "Render its stateBefore" not in client.calls[1]["prompt"]
    assert client.calls[1]["character"].bytes == repair.media.objects[first["storageKey"]]
    assert first["requestHash"] != last["requestHash"]
    assert last["frameRole"] == "ending" and last["referenceFrame"]["frame"] == 119
    assert last["referenceFrame"]["layoutHash"] == hashlib.sha256(ending).hexdigest()
    assert last["openingFrame"] == row.context_json["sourceOpeningFrames"]["source-scene"]
    assert op.result_json["images"]["0:ending"]["status"] == "completed"
    assert await prepare_unit(presenter_setup, frame_role="ending") == last
    assert len(client.calls) == 2


@pytest.mark.asyncio
async def test_ending_has_distinct_ledger_slot_and_no_duplicate_after_timeout(
    presenter_setup, monkeypatch,
):
    _, _, _, client, _, _, _ = presenter_setup
    await prepare_unit(presenter_setup)
    reserve = AsyncMock(return_value=(None, True))
    monkeypatch.setattr(module, "reserve_generation_attempt", reserve)
    client.edit = AsyncMock(side_effect=TimeoutError())
    for _ in range(2):
        with pytest.raises(AppError, match="OPENAI_IMAGE_SUBMISSION_UNRESOLVED"):
            await prepare_unit(presenter_setup, frame_role="ending")
    assert reserve.call_args.kwargs["slot"] == "image:0:ending"
    assert client.edit.await_count == reserve.await_count == 1


@pytest.mark.asyncio
async def test_ending_rejects_changed_source_before_submission(presenter_setup):
    repair, _, _, client, _, _, _ = presenter_setup
    repair.media.objects["source"] = b"changed source"
    with pytest.raises(AppError, match="SMART_REMAKE_IMAGE_ASSET_INVALID"):
        await prepare_unit(presenter_setup, frame_role="ending")
    assert client.calls == []


@pytest.mark.asyncio
async def test_repair_retains_the_original_generated_presenter_identity(presenter_setup):
    repair, row, op, client, scene, _, _ = presenter_setup
    first = await prepare_unit(presenter_setup)
    scene["imagePrompt"] = "A closer camera angle, retaining the observed physical state"
    op.result_json = {"kind": "repair"}
    repaired = await prepare_unit(presenter_setup)
    assert client.calls[-1]["character"].bytes == repair.media.objects[first["storageKey"]]
    assert repaired["presenterIdentity"]["anchor"]["requestHash"] == first["requestHash"]
    assert repaired["expectationsHash"] == row.context_json["expectationsHash"]
    assert repaired["requestHash"] != first["requestHash"]


@pytest.mark.parametrize("presence", ["none", "hands_only", "person"])
def test_scene_observation_wins_over_video_wide_subject_presence(presence):
    scene = {
        "sourceRange": {"startFrame": 48, "endFrame": 120},
        "shotPlan": {"shots": [{"subjectPresence": presence}]},
    }
    assert module._frame_subject_presence(
        {"referenceAnalysis": {"subjectPresence": "person"}}, scene, 48,
    ) == presence


def test_video_wide_person_flag_does_not_invent_a_face_in_an_unobserved_frame():
    scene = {"sourceRange": {"startFrame": 48, "endFrame": 120}}
    assert module._frame_subject_presence(
        {"referenceAnalysis": {"subjectPresence": "person"}}, scene, 48,
    ) is None


def test_excerpt_source_shots_use_relative_analysis_clock_for_absolute_reference_frame():
    context = {
        "sourceSceneMap": {"sourceStartFrame": 48},
        "referenceAnalysis": {"sourceShots": [
            {"startSecond": 0, "endSecond": 2, "subjectPresence": "person"},
            {"startSecond": 2, "endSecond": 4, "subjectPresence": "hands_only"},
        ]},
    }
    scene = {"sourceRange": {"startFrame": 48, "endFrame": 96}}
    assert module._frame_subject_presence(context, scene, 48) == "person"
    assert module._frame_subject_presence(context, scene, 95) == "person"
    assert module._frame_subject_presence(context, scene, 96) == "hands_only"


@pytest.mark.asyncio
async def test_unknown_anchor_submission_keeps_original_reference_even_if_cache_changes(
    presenter_setup,
):
    _, row, op, client, _, _, _ = presenter_setup
    first = await prepare_unit(presenter_setup)
    client.edit = AsyncMock(side_effect=TimeoutError())
    with pytest.raises(AppError, match="OPENAI_IMAGE_SUBMISSION_UNRESOLVED"):
        await prepare_unit(presenter_setup, 1)
    assert op.result_json["images"]["1"]["presenterIdentity"]["anchor"]["requestHash"] == (
        first["requestHash"]
    )
    del row.context_json["imageAssets"][first["requestHash"]]
    with pytest.raises(AppError, match="SMART_REMAKE_IMAGE_ASSET_INVALID"):
        await prepare_unit(presenter_setup, 1)
    assert client.edit.await_count == 1


@pytest.mark.asyncio
async def test_anchor_bytes_are_rechecked_after_retained_metadata_validation(
    presenter_setup, monkeypatch,
):
    repair, _, _, client, _, _, _ = presenter_setup
    first = await prepare_unit(presenter_setup)
    original_read = repair.media.read
    reads = 0

    async def changed_between_reads(key):
        nonlocal reads
        if key == first["storageKey"]:
            reads += 1
            if reads > 1:
                return image(color="blue")
        return await original_read(key)

    monkeypatch.setattr(repair.media, "read", changed_between_reads)
    with pytest.raises(AppError, match="SMART_REMAKE_IMAGE_ASSET_INVALID"):
        await prepare_unit(presenter_setup, 1)
    assert len(client.calls) == 1


@pytest.mark.asyncio
async def test_invalid_conditioning_frame_role_never_submits(presenter_setup):
    _, _, _, client, _, _, _ = presenter_setup
    with pytest.raises(AppError, match="SMART_REMAKE_IMAGE_ASSET_INVALID"):
        await prepare_unit(presenter_setup, frame_role="middle")
    assert client.calls == []
