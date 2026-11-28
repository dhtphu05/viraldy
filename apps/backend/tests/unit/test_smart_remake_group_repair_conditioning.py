# ruff: noqa: F811 -- shared offline pytest fixtures are resolved by name.
"""Provider-group repair prepares only its two frozen bookends with the same actor."""

from __future__ import annotations

import copy

import pytest
from test_smart_remake_image_workflow import setup  # noqa: F401
from test_smart_remake_presenter_conditioning import prepare_unit, presenter_setup  # noqa: F401

from tests.unit.test_smart_remake_boundary_conditioning import twelve_seconds
from viraldy.modules.smart_remake import image_workflow as module
from viraldy.modules.smart_remake.generation_expectations import expectations_hash
from viraldy.modules.smart_remake.repair_intent import GROUP_NORMALIZER_VERSION
from viraldy.shared.errors.base import AppError


async def group_repair(value, *, multiple_units=False):
    twelve_seconds(value)
    repair, row, operation, client, _, _, _ = value
    if multiple_units:
        plan = row.context_json["renderPlan"]
        plan["units"][1]["targetDurationFrames"] = 72
        plan["units"].append(
            {
                **plan["units"][1],
                "id": "unit-three",
                "sceneIndex": 2,
                "sourceSceneId": "source-three",
            }
        )
        plan["groups"][1]["renderUnitIds"].append("unit-three")
        row.context_json["sceneMap"]["scenes"].append(
            {
                **copy.deepcopy(row.context_json["sceneMap"]["scenes"][1]),
                "id": "unit-three",
            }
        )
        row.context_json["sourceSceneMap"]["scenes"].append(
            {
                "id": "source-three",
                "startFrame": 192,
                "endFrame": 264,
            }
        )
        row.context_json["sourceOpeningFrames"]["source-three"] = {
            **row.context_json["sourceOpeningFrames"]["source-two"],
            "frame": 192,
        }
    anchor = await prepare_unit(value)
    frozen = copy.deepcopy(row.context_json["generationExpectations"])
    for scene in frozen["scenes"][1:]:
        scene["userEdits"] = "NORMALIZED: keep the pink handle facing the viewer"
    group = copy.deepcopy(row.context_json["renderPlan"]["groups"][1])
    operation.result_json = {
        "kind": "repair",
        "request": {"repairScope": "provider_group"},
        "repairGroup": {
            "group": group,
            "anchorSceneId": group["renderUnitIds"][0],
            "baseVersions": [],
        },
        "renderPlan": copy.deepcopy(row.context_json["renderPlan"]),
        "generationExpectations": frozen,
        "expectationsHash": expectations_hash(frozen),
        "conditioningPolicy": "source-frame-authority-v1",
        "tasks": {},
    }
    client.calls.clear()
    return anchor


async def prepare_boundary(value, index, role):
    repair, row, operation, client, _, save, _ = value
    return await module.prepare_scene_image(
        repair=repair,
        row=row,
        operation=operation,
        index=index,
        compiled_scene={"imagePrompt": "UNFROZEN CALLER TEXT"},
        image_client=client,
        save=save,
        ensure_active=lambda: None,
        frame_role=role,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("last_index", [1, 2])
async def test_group_repair_uses_two_normalized_bookends_and_retained_actor(
    presenter_setup, last_index
):
    anchor = await group_repair(presenter_setup, multiple_units=last_index == 2)
    repair, _, operation, client, _, _, _ = presenter_setup
    first = await prepare_boundary(presenter_setup, 1, "opening")
    last = await prepare_boundary(presenter_setup, last_index, "ending")
    assert len(client.calls) == 2
    assert set(operation.result_json["images"]) == {"1", f"{last_index}:ending"}
    for call in client.calls:
        assert "NORMALIZED: keep the pink handle facing the viewer" in call["prompt"]
        assert "UNFROZEN CALLER TEXT" not in call["prompt"]
        assert "source frame is authoritative" in call["prompt"]
        assert call["character"].bytes == repair.media.objects[anchor["storageKey"]]
        assert "continuity_frame" not in call
    assert (
        first["expectationsHash"]
        == last["expectationsHash"]
        == operation.result_json["expectationsHash"]
    )
    assert first["referenceFrame"]["frame"] == 120
    assert last["referenceFrame"]["frame"] == (263 if last_index == 2 else 191)
    await prepare_boundary(presenter_setup, 1, "opening")
    await prepare_boundary(presenter_setup, last_index, "ending")
    if last_index == 2:
        with pytest.raises(AppError, match="SMART_REMAKE_REPAIR_SCOPE_INVALID"):
            await prepare_boundary(presenter_setup, 1, "ending")
    assert len(client.calls) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("index,role", [(0, "opening"), (0, "ending")])
async def test_group_repair_cannot_prepare_other_group_images(presenter_setup, index, role):
    await group_repair(presenter_setup)
    _, _, _, client, _, _, _ = presenter_setup
    with pytest.raises(AppError, match="SMART_REMAKE_REPAIR_SCOPE_INVALID"):
        await prepare_boundary(presenter_setup, index, role)
    assert client.calls == []


def accepted_terminal(operation):
    identities = operation.result_json["repairGroup"]["group"]["renderUnitIds"]
    operation.result_json["repairBaseScenes"] = [
        copy.deepcopy(scene)
        for scene in operation.result_json["generationExpectations"]["scenes"]
        if scene["renderUnitId"] in identities
    ]
    scene = operation.result_json["generationExpectations"]["scenes"][1]
    scene["shotPlan"] = {
        "shots": [{"stateBefore": "closed", "action": "VALIDATED_OPEN_CAP", "stateAfter": "open"}]
    }
    operation.result_json["expectationsHash"] = expectations_hash(
        operation.result_json["generationExpectations"]
    )
    operation.result_json["request"]["repairIntent"] = {
        "schemaVersion": 1,
        "issues": ["action"],
        "instruction": "Open the cap",
    }
    operation.result_json["compiledScenes"] = [copy.deepcopy(scene)]
    operation.result_json["repairNormalization"] = {
        "version": GROUP_NORMALIZER_VERSION,
        "phase": "resolved",
        "validationError": False,
        "result": {
            "status": "accepted",
            "reason": "Validated terminal action",
            "scenePatches": [
                {
                    "unitIndex": 0,
                    "scenePatch": {
                        **{key: scene[key] for key in ("prompt", "imagePrompt", "videoPrompt")},
                        "shots": [
                            {"shotIndex": 0, "action": "VALIDATED_OPEN_CAP", "stateAfter": "open"}
                        ],
                    },
                }
            ],
        },
    }


@pytest.mark.asyncio
async def test_validated_group_repair_changes_ending_state_while_opening_stays_source_bound(
    presenter_setup,
):
    await group_repair(presenter_setup)
    _, _, operation, client, _, _, _ = presenter_setup
    accepted_terminal(operation)
    await prepare_boundary(presenter_setup, 1, "opening")
    await prepare_boundary(presenter_setup, 1, "ending")
    opening, ending = [call["prompt"] for call in client.calls]
    assert "source frame is authoritative for physical state" in opening
    assert "VALIDATED_OPEN_CAP" not in opening
    assert "VALIDATED_OPEN_CAP" in ending and '"stateAfter": "open"' in ending
    assert "validated terminal action" in ending
    assert "source frame is authoritative for physical state" not in ending
    assert "source camera, background and panel layout remain fixed" in ending


@pytest.mark.asyncio
async def test_group_repair_cannot_override_ending_with_a_compiled_scene_outside_frozen_snapshot(
    presenter_setup,
):
    await group_repair(presenter_setup)
    _, _, operation, client, _, _, _ = presenter_setup
    accepted_terminal(operation)
    operation.result_json["compiledScenes"][0]["shotPlan"]["shots"][0]["stateAfter"] = "unvalidated"
    with pytest.raises(AppError, match="SMART_REMAKE_INPUT_CHANGED"):
        await prepare_boundary(presenter_setup, 1, "ending")
    assert client.calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "field,value",
    [
        ("version", "unvalidated"),
        ("validationError", True),
        ("phase", "invoking"),
    ],
)
async def test_unvalidated_group_result_cannot_override_source_ending(
    presenter_setup, field, value
):
    await group_repair(presenter_setup)
    _, _, operation, client, _, _, _ = presenter_setup
    accepted_terminal(operation)
    operation.result_json["repairNormalization"][field] = value
    await prepare_boundary(presenter_setup, 1, "ending")
    assert "VALIDATED_OPEN_CAP" not in client.calls[0]["prompt"]
    assert "source frame is authoritative for physical state" in client.calls[0]["prompt"]


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["empty", "earlier_unit", "earlier_shot", "unchanged"])
async def test_group_repair_without_a_changed_terminal_shot_keeps_source_ending(
    presenter_setup,
    change,
):
    await group_repair(presenter_setup, multiple_units=change == "earlier_unit")
    _, _, operation, client, _, _, _ = presenter_setup
    accepted_terminal(operation)
    result = operation.result_json
    scenes = result["generationExpectations"]["scenes"][1:]
    patches = result["repairNormalization"]["result"]["scenePatches"]
    if change == "empty":
        result["repairNormalization"]["result"]["scenePatches"] = []
    elif change == "earlier_shot":
        terminal = copy.deepcopy(result["repairBaseScenes"][0]["shotPlan"]["shots"][-1])
        scenes[0]["shotPlan"]["shots"].append(terminal)
        result["repairBaseScenes"][0]["shotPlan"]["shots"].append(copy.deepcopy(terminal))
        patches[0]["scenePatch"]["shots"].append({"shotIndex": 1, **terminal})
    elif change == "unchanged":
        result["repairBaseScenes"][0]["shotPlan"] = copy.deepcopy(scenes[0]["shotPlan"])
    result["compiledScenes"] = copy.deepcopy(scenes)
    result["expectationsHash"] = expectations_hash(result["generationExpectations"])
    await prepare_boundary(presenter_setup, 2 if change == "earlier_unit" else 1, "ending")
    prompt = client.calls[0]["prompt"]
    assert "VALIDATED TERMINAL REPAIR" not in prompt
    assert "source frame is authoritative for physical state" in prompt


@pytest.mark.asyncio
async def test_changed_terminal_action_does_not_reintroduce_unchanged_old_state(presenter_setup):
    await group_repair(presenter_setup)
    _, _, operation, client, _, _, _ = presenter_setup
    accepted_terminal(operation)
    result = operation.result_json
    scene = result["generationExpectations"]["scenes"][1]
    scene["shotPlan"]["shots"][0]["stateAfter"] = result["repairBaseScenes"][0]["shotPlan"][
        "shots"
    ][0]["stateAfter"]
    result["repairNormalization"]["result"]["scenePatches"][0]["scenePatch"]["shots"][0].pop(
        "stateAfter"
    )
    result["compiledScenes"] = [copy.deepcopy(scene)]
    result["expectationsHash"] = expectations_hash(result["generationExpectations"])
    await prepare_boundary(presenter_setup, 1, "ending")
    prompt = client.calls[0]["prompt"]
    assert "VALIDATED_OPEN_CAP" in prompt
    assert "contradictory top-down cup on coaster" not in prompt
    assert "preserve its actual state/pose for unspecified" in prompt
