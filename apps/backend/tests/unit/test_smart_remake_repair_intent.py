from __future__ import annotations

import copy
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from tests.smart_remake_expectations import install_expectations
from viraldy.modules.smart_remake.repair_schemas import RepairSceneRequest

INTENT = {"schemaVersion": 1, "issues": ["action"], "instruction": "Pour more slowly"}


def request(**fields):
    return RepairSceneRequest.model_validate(
        {"expectedRevision": 2, "idempotencyKey": "repair-once", **fields}
    )


def test_structured_repair_does_not_require_prompts():
    result = request(repairIntent=INTENT)
    assert result.repairIntent.instruction == "Pour more slowly"
    assert "prompt" not in result.model_dump(mode="json")


def test_legacy_request_serialization_is_byte_shape_compatible():
    payload = {
        "baseVersionId": None,
        "expectedRevision": 2,
        "prompt": "scene",
        "imagePrompt": "opening",
        "videoPrompt": "motion",
        "idempotencyKey": "repair-once",
    }
    assert (
        request(prompt="scene", imagePrompt="opening", videoPrompt="motion").model_dump(mode="json")
        == payload
    )


@pytest.mark.parametrize(
    "fields",
    [
        {},
        {"prompt": "only one"},
        {"repairIntent": INTENT, "prompt": "conflicting input"},
        {"repairIntent": {**INTENT, "instruction": "x" * 4001}},
        {"repairIntent": {**INTENT, "issues": ["unknown"]}},
    ],
)
def test_repair_rejects_ambiguous_or_invalid_contract(fields):
    with pytest.raises(ValidationError):
        request(**fields)


def prepared():
    scene_id, version_id = str(uuid4()), str(uuid4())
    state = {
        "revision": 2,
        "draftTimeline": {
            "items": [
                {
                    "renderUnitId": scene_id,
                    "sourceSceneId": "source",
                    "versionId": version_id,
                    "inFrame": 24,
                    "outFrame": 96,
                    "targetDurationFrames": 72,
                }
            ]
        },
        "scenes": [
            {
                "id": scene_id,
                "index": 0,
                "activeVersionId": version_id,
                "versions": [{"id": version_id}],
            }
        ],
    }
    context = {"sourceKey": "source", "productKey": "product", "productMimeType": "image/png"}
    install_expectations(context, state=state)
    shot = {
        "shotIndex": 0,
        "startSecond": 0,
        "endSecond": 3,
        "durationSeconds": 3,
        "action": "open and pour",
        "stateBefore": "closed",
        "stateAfter": "open",
        "physicalAction": {"movement": "open cap"},
    }
    context["sceneMap"]["scenes"][0]["shotPlan"] = {"shots": [shot], "targetDuration": 3}
    install_expectations(context, state=state)
    return SimpleNamespace(state_json=state, context_json=context), state["scenes"][0]


def accepted():
    return {
        "status": "accepted",
        "reason": "The request preserves identity and opening state.",
        "scenePatch": {
            "prompt": "Slow pour",
            "imagePrompt": "Closed bottle opening",
            "videoPrompt": "Slowly open and pour",
            "shots": [
                {
                    "shotIndex": 0,
                    "action": "slowly open and pour",
                    "physicalAction": {"movement": "slowly open cap"},
                    "stateAfter": "open",
                }
            ],
        },
    }


def test_repair_without_generated_base_is_not_reported_as_stale_expectations():
    from viraldy.modules.smart_remake.repair_intent import repair_base_scene
    from viraldy.shared.errors.base import AppError

    row, scene = prepared()
    scene.update(activeVersionId=None, versions=[])
    with pytest.raises(AppError) as error:
        repair_base_scene(row, scene)
    assert error.value.code == "SMART_REMAKE_BASE_VERSION_REQUIRED"


def test_normalizer_rebases_on_active_snapshot_and_preserves_timing_opening_and_product():
    from viraldy.modules.smart_remake.repair_intent import apply_repair_result, repair_base_scene

    row, scene = prepared()
    retained = scene["versions"][0]["generationExpectations"]
    retained["scenes"][0]["videoPrompt"] = "Previously accepted camera edit"
    from viraldy.modules.smart_remake.generation_expectations import expectations_hash

    version = scene["versions"][0]
    version["expectationsHash"] = expectations_hash(retained)
    original = copy.deepcopy(row.context_json)
    compiled = repair_base_scene(row, scene)
    assert compiled["videoPrompt"] == "Previously accepted camera edit"
    result = apply_repair_result(compiled, accepted(), row.context_json)
    assert result["shotPlan"]["shots"][0]["action"] == "slowly open and pour"
    assert result["shotPlan"]["shots"][0]["stateBefore"] == "closed"
    assert result["shotPlan"]["shots"][0]["startSecond"] == 0
    assert result["shotPlan"]["shots"][0]["endSecond"] == 3
    assert result["videoPrompt"] == "Slowly open and pour"
    assert row.context_json == original


@pytest.mark.parametrize(
    "field,value",
    [("stateBefore", "open"), ("startSecond", 1), ("productLock", {"productName": "different"})],
)
def test_normalizer_rejects_model_patch_outside_creative_allowlist(field, value):
    from viraldy.modules.smart_remake.repair_intent import apply_repair_result, repair_base_scene
    from viraldy.shared.errors.base import AppError

    row, scene = prepared()
    response = accepted()
    response["scenePatch"]["shots"][0][field] = value
    with pytest.raises(AppError, match="SMART_REMAKE_REPAIR_INTENT_INVALID"):
        apply_repair_result(repair_base_scene(row, scene), response, row.context_json)


def test_later_shot_state_can_follow_updated_action_without_changing_opening():
    from viraldy.modules.smart_remake.repair_intent import apply_repair_result, repair_base_scene

    row, scene = prepared()
    compiled = repair_base_scene(row, scene)
    compiled["shotPlan"]["shots"].append(
        {
            "shotIndex": 1,
            "startSecond": 1.5,
            "endSecond": 3,
            "action": "finish pouring",
            "stateBefore": "full",
            "stateAfter": "empty",
        }
    )
    response = accepted()
    response["scenePatch"]["shots"].append(
        {
            "shotIndex": 1,
            "action": "finish a small pour",
            "stateBefore": "partly full",
            "stateAfter": "mostly full",
        }
    )
    repaired = apply_repair_result(compiled, response, row.context_json)
    assert repaired["shotPlan"]["shots"][1]["stateBefore"] == "partly full"
    assert repaired["shotPlan"]["shots"][0]["stateBefore"] == "closed"


@pytest.mark.parametrize("status", ["conflict", "insufficient_evidence"])
def test_rejected_repair_returns_clear_reason_without_compiled_payload(status):
    from viraldy.modules.smart_remake.repair_intent import apply_repair_result
    from viraldy.shared.errors.base import AppError

    with pytest.raises(AppError, match="SMART_REMAKE_REPAIR_INTENT_REJECTED") as error:
        apply_repair_result({}, {"status": status, "reason": "Keep the closed opening."}, {})
    assert error.value.details["reason"] == "Keep the closed opening."


def test_normalizer_prompt_contains_only_canonical_scene_data():
    from viraldy.modules.smart_remake.repair_intent import repair_base_scene
    from viraldy.modules.smart_remake.repair_intent_workflow import normalization_prompt
    from viraldy.modules.smart_remake.repair_schemas import RepairIntent

    row, scene = prepared()
    compiled = repair_base_scene(row, scene)
    compiled.update(storageKey="private-storage", sourceImageUrl="https://private.test/source")
    _, prompt = normalization_prompt(row, compiled, RepairIntent.model_validate(INTENT), {})
    assert "private-storage" not in prompt and "private.test" not in prompt


def test_normalizer_binds_real_timeline_compiled_scene_without_an_id():
    from viraldy.modules.smart_remake.repair_intent import repair_base_scene
    from viraldy.modules.smart_remake.repair_intent_workflow import normalization_prompt
    from viraldy.modules.smart_remake.repair_schemas import RepairIntent

    row, scene = prepared()
    row.context_json["sceneMap"]["scenes"][0].pop("id", None)
    compiled = repair_base_scene(row, scene)
    _, prompt = normalization_prompt(row, compiled, RepairIntent.model_validate(INTENT), {})
    assert scene["id"] in prompt


@pytest.mark.asyncio
async def test_fixture_repair_uses_same_canonical_contract_without_model_or_prompt_input(
    monkeypatch,
):
    from viraldy.modules.smart_remake import repair_service

    row, scene = prepared()
    row.id, row.workspace_id = uuid4(), uuid4()
    row.context_json.update(referenceAnalysis={}, projectName="Offline", audioRequired=False)
    row.state_json["provider"] = "unifically"
    operation = SimpleNamespace(id=uuid4(), status="running", result_json={})

    class Repository:
        async def start(self, *args):
            return row, operation, True

        async def finish(self, op, status, result):
            op.status, op.result_json = status, copy.deepcopy(result)

        async def project(self, *args, **kwargs):
            return row

        async def running(self, *args):
            return operation

        async def refresh(self, *args):
            return None

        async def complete(self, row, state, op, result):
            row.state_json = state
            await self.finish(op, "completed", result)

    class Media:
        async def read(self, key):
            return b"product"

        async def put(self, *args):
            return "candidate-key"

    captured = []

    async def render(input_data, *, on_scene_output, **kwargs):
        captured.append(input_data)
        await on_scene_output(0, b"candidate", {})
        return {"status": "completed"}

    async def operation_result(*args):
        return operation.result_json

    monkeypatch.setattr(repair_service, "render_smart_remake", render)
    monkeypatch.setattr(repair_service, "technical_check", lambda *args, **kwargs: {})
    service = repair_service.RepairService(
        Repository(), Media(), row.workspace_id, settings=SimpleNamespace(ai_mode="fixture")
    )
    monkeypatch.setattr(service, "_operation_result", operation_result)
    result = await service.repair(
        row.id,
        scene["id"],
        request(
            baseVersionId=scene["activeVersionId"],
            repairIntent=INTENT,
        ),
    )
    assert result["repairNormalization"]["phase"] == "resolved"
    assert "Pour more slowly" in captured[0].sceneMap["scenes"][0]["videoPrompt"]
    candidate = row.state_json["scenes"][0]["versions"][-1]
    assert "Pour more slowly" in candidate["videoPrompt"]
    assert candidate["expectationsHash"] == result["expectationsHash"]
