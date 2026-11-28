"""One normalization repairs one provider window and retains every member binding."""
from __future__ import annotations

import copy
import hashlib
import json
from types import SimpleNamespace
from uuid import uuid4

import pytest

from tests.smart_remake_expectations import install_expectations
from tests.unit.test_smart_remake_repair_intent import accepted
from viraldy.modules.smart_remake import repair_intent, repair_intent_media, repair_intent_workflow
from viraldy.shared.errors.base import AppError


def group_fixture():
    units = [{"id": str(uuid4()), "sceneIndex": index, "sourceSceneId": f"source-{index}",
              "targetDurationFrames": 72, "rawDurationFrames": 144} for index in range(4)]
    group = {"id": "group-one", "renderUnitIds": [unit["id"] for unit in units[:2]],
             "rawDurationFrames": 144, "targetDurationFrames": 144,
             "segments": [{"renderUnitId": unit["id"], "inFrame": index * 72,
                           "outFrame": (index + 1) * 72} for index, unit in enumerate(units[:2])]}
    clip = b"owned-six-second-clip"
    state = {"revision": 3, "scenes": [{
        "id": unit["id"], "index": index, "activeVersionId": f"version-{index}",
        "versions": [{"id": f"version-{index}", "storageKey": "active",
                      "mediaHash": hashlib.sha256(clip).hexdigest(),
                      "technicalCheck": {"status": "passed"}}],
    } for index, unit in enumerate(units)], "draftTimeline": {"items": [{
        "renderUnitId": unit["id"], "sourceSceneId": unit["sourceSceneId"],
        "versionId": f"version-{index}", "inFrame": (index % 2) * 72,
        "outFrame": (index % 2 + 1) * 72, "targetDurationFrames": 72,
    } for index, unit in enumerate(units)]}}
    context = {"productKey": "product", "productMimeType": "image/png", "sourceKey": "source",
               "renderPlan": {"units": units, "groups": [group], "videoModel": "wan/3-0-video"},
               "sceneMap": {"scenes": [{
                   **unit, "prompt": f"Scene {index}", "imagePrompt": f"Opening {index}",
                   "videoPrompt": f"Move {index}", "shotPlan": {"shots": [{
                       "action": f"Action {index}", "startSecond": 0, "endSecond": 3,
                       "stateBefore": "closed", "stateAfter": "open",
                   }]},
               } for index, unit in enumerate(units)]}}
    row = SimpleNamespace(id=uuid4(), workspace_id=uuid4(), state_json=state, context_json=context)
    install_expectations(context, state=state)
    bases = [repair_intent.repair_base_scene(row, scene) for scene in state["scenes"][:2]]
    manifest = [{"sceneId": scene["id"], "baseVersionId": scene["activeVersionId"],
                 "inFrame": index * 72, "outFrame": (index + 1) * 72,
                 "mediaHash": scene["versions"][0]["mediaHash"], "storageKey": "active",
                 "expectationsHash": scene["versions"][0]["expectationsHash"]}
                for index, scene in enumerate(state["scenes"][:2])]
    operation = SimpleNamespace(id=uuid4(), result_json={
        "kind": "repair", "sceneIndex": 0, "sceneId": units[0]["id"],
        "request": {"repairScope": "provider_group", "baseVersionId": "version-0",
                    "repairIntent": {"issues": ["action"], "instruction": "Move more slowly"}},
        "repairGroup": {"group": copy.deepcopy(group), "baseVersions": manifest,
                        "anchorSceneId": units[0]["id"]},
        "repairBaseScenes": copy.deepcopy(bases),
    })
    repair = SimpleNamespace(workspace_id=row.workspace_id,
                             repository=SimpleNamespace(session=object()))
    async def save(op, result):
        op.result_json = copy.deepcopy(result)
    return repair, row, operation, bases, save, clip


def response(index=1):
    return {"status": "accepted", "reason": "Compatible change", "scenePatches": [
        {"unitIndex": index, "scenePatch": accepted()["scenePatch"]},
    ]}


def test_group_patch_updates_only_requested_units_without_changing_ranges_or_ids():
    _, row, _, bases, _, _ = group_fixture()
    before = copy.deepcopy(bases)
    result = repair_intent.apply_group_repair_result(bases, response(), row.context_json)
    assert result[0] == before[0]
    assert result[1]["videoPrompt"] == "Slowly open and pour"
    assert [scene["renderUnitId"] for scene in result] == [scene["renderUnitId"] for scene in bases]
    assert result[1]["shotPlan"]["shots"][0]["startSecond"] == 0
    assert result[1]["shotPlan"]["shots"][0]["endSecond"] == 3
    assert result[1]["shotPlan"]["shots"][0]["stateBefore"] == "closed"
    assert bases == before


def test_alternate_take_can_keep_all_group_directions_unchanged():
    _, row, _, bases, _, _ = group_fixture()
    result = repair_intent.apply_group_repair_result(bases, {
        "status": "accepted", "reason": "Alternate take", "scenePatches": [],
    }, row.context_json)
    assert result == bases and result is not bases


@pytest.mark.parametrize("indices", [[2], [1, 1], [1, 0]])
def test_group_patch_rejects_wrong_duplicate_or_reordered_units(indices):
    _, row, _, bases, _, _ = group_fixture()
    value = response()
    value["scenePatches"] = [{"unitIndex": index, "scenePatch": accepted()["scenePatch"]}
                             for index in indices]
    with pytest.raises(AppError, match="SMART_REMAKE_REPAIR_INTENT_INVALID"):
        repair_intent.apply_group_repair_result(bases, value, row.context_json)


@pytest.mark.parametrize("field,value", [("renderUnitId", "other"), ("sourceRange", {}),
                                       ("productLock", {}), ("openingFrame", {})])
def test_group_normalizer_cannot_patch_immutable_metadata(field, value):
    _, row, _, bases, _, _ = group_fixture()
    result = response()
    result["scenePatches"][0]["scenePatch"][field] = value
    with pytest.raises(AppError, match="SMART_REMAKE_REPAIR_INTENT_INVALID"):
        repair_intent.apply_group_repair_result(bases, result, row.context_json)


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["accepted", "conflict", "insufficient_evidence", "invalid"])
async def test_group_resolver_uses_one_durable_call_and_replays_all_compiled_scenes(
    monkeypatch, status,
):
    repair, row, op, bases, save, _ = group_fixture()
    calls = []
    async def evidence(*args):
        return [{"bytes": b"clip", "mime_type": "video/mp4"}], {"fps": 24}
    class Ledger:
        def __init__(self, *args, **kwargs):
            assert kwargs["purpose"] == "repair"
        async def generate_json(self, **kwargs):
            calls.append(kwargs)
            data = json.loads(kwargs["prompt"])
            assert len(data["scenes"]) == 2
            assert "storageKey" not in kwargs["prompt"]
            if status == "accepted":
                return response()
            return {"status": status, "reason": "Keep product"} if status != "invalid" else {}
    monkeypatch.setattr(repair_intent_workflow, "group_repair_evidence", evidence)
    monkeypatch.setattr(repair_intent_workflow, "LedgerGeminiClient", Ledger)
    for _ in range(2):
        if status == "accepted":
            assert await repair_intent_workflow.resolve_repair_intent(repair, row, op, save=save)
            assert op.result_json["compiledScenes"][0] == bases[0]
            assert op.result_json["compiledScenes"][1]["videoPrompt"] == "Slowly open and pour"
        else:
            with pytest.raises(AppError, match="SMART_REMAKE_REPAIR_INTENT_"):
                await repair_intent_workflow.resolve_repair_intent(repair, row, op, save=save)
    assert len(calls) == 1
    assert op.result_json["repairNormalization"]["phase"] == "resolved"


@pytest.mark.asyncio
async def test_group_reconciliation_does_not_read_evidence_or_start_analysis(monkeypatch):
    repair, row, op, _, save, _ = group_fixture()
    monkeypatch.setattr(
        repair_intent_workflow, "group_repair_evidence", lambda *args: pytest.fail("read"),
    )
    assert not await repair_intent_workflow.resolve_repair_intent(
        repair, row, op, save=save, reconcile_only=True,
    )


@pytest.mark.asyncio
async def test_changed_member_version_or_base_directions_stop_before_analysis(monkeypatch):
    repair, row, op, _, save, _ = group_fixture()
    row.state_json["scenes"][1]["activeVersionId"] = "replacement"
    monkeypatch.setattr(
        repair_intent_workflow, "group_repair_evidence", lambda *args: pytest.fail("read"),
    )
    with pytest.raises(AppError, match="SMART_REMAKE_BASE_VERSION_CONFLICT"):
        await repair_intent_workflow.resolve_repair_intent(repair, row, op, save=save)


@pytest.mark.asyncio
async def test_uncertain_group_analysis_keeps_receipt_on_read_only_refresh(monkeypatch):
    repair, row, op, _, save, _ = group_fixture()
    calls = []
    async def evidence(*args):
        return [], {"fps": 24}
    class Ledger:
        def __init__(self, *args, **kwargs):
            pass
        async def generate_json(self, **kwargs):
            calls.append(kwargs)
            raise AppError("SMART_REMAKE_MODEL_ATTEMPT_UNCERTAIN", "Reconcile old request", 409)
    monkeypatch.setattr(repair_intent_workflow, "group_repair_evidence", evidence)
    monkeypatch.setattr(repair_intent_workflow, "LedgerGeminiClient", Ledger)
    with pytest.raises(AppError, match="SMART_REMAKE_MODEL_ATTEMPT_UNCERTAIN"):
        await repair_intent_workflow.resolve_repair_intent(repair, row, op, save=save)
    assert op.result_json["repairNormalization"]["phase"] == "invoking"
    assert not await repair_intent_workflow.resolve_repair_intent(
        repair, row, op, save=save, reconcile_only=True,
    )
    assert len(calls) == 1 and "compiledScenes" not in op.result_json


@pytest.mark.parametrize("tamper", ["trim", "hash", "storage", "missing_version"])
def test_group_bases_reject_any_changed_selected_member_binding(tamper):
    _, row, op, _, _, _ = group_fixture()
    version = row.state_json["scenes"][1]["versions"][0]
    if tamper == "trim":
        row.state_json["draftTimeline"]["items"][1]["inFrame"] += 1
    elif tamper == "hash":
        version["mediaHash"] = "a" * 64
    elif tamper == "storage":
        version["storageKey"] = "replacement"
    else:
        row.state_json["scenes"][1]["versions"] = []
    with pytest.raises(AppError):
        repair_intent.group_repair_bases(row, op.result_json["repairGroup"])


def test_second_group_repair_keeps_previously_accepted_member_directions():
    from viraldy.modules.smart_remake.generation_expectations import expectations_hash

    _, row, op, _, _, _ = group_fixture()
    version = row.state_json["scenes"][0]["versions"][0]
    version["generationExpectations"]["scenes"][0]["videoPrompt"] = (
        "Previously accepted camera edit"
    )
    version["expectationsHash"] = expectations_hash(version["generationExpectations"])
    op.result_json["repairGroup"]["baseVersions"][0]["expectationsHash"] = (
        version["expectationsHash"]
    )
    bases = repair_intent.group_repair_bases(row, op.result_json["repairGroup"])
    result = repair_intent.apply_group_repair_result(bases, response(), row.context_json)
    assert result[0]["videoPrompt"] == "Previously accepted camera edit"
    assert result[1]["videoPrompt"] == "Slowly open and pour"


@pytest.mark.asyncio
@pytest.mark.parametrize("mixed", [False, True])
async def test_group_media_assembles_current_ranges_with_both_source_frames(monkeypatch, mixed):
    from tests.smart_remake_expectations import fixture_opening_bytes
    from viraldy.modules.smart_remake.engine.schemas import UploadedMedia

    repair, row, op, _, _, clip = group_fixture()
    other = b"different-owned-six-second-clip"
    if mixed:
        row.state_json["scenes"][1]["versions"][0].update(
            storageKey="other", mediaHash=hashlib.sha256(other).hexdigest(),
        )
        op.result_json["repairGroup"]["baseVersions"][1].update(
            storageKey="other", mediaHash=hashlib.sha256(other).hexdigest(),
        )
    frames, assembled = [], []
    async def references(service, owned, index, *, frame_role="opening"):
        frames.append((index, frame_role))
        source_id = row.context_json["renderPlan"]["units"][index]["sourceSceneId"]
        return UploadedMedia(bytes=b"product", mime_type="image/png"), UploadedMedia(
            bytes=fixture_opening_bytes(source_id), mime_type="image/png",
        )
    async def read(key):
        return other if key == "other" else clip
    def assemble(clips, items, **kwargs):
        assembled.append((clips, items))
        return b"group-six-second-evidence"
    repair.media = SimpleNamespace(read=read)
    monkeypatch.setattr(repair_intent_media, "_references", references)
    monkeypatch.setattr(repair_intent_media, "probe_timeline_media", lambda _: {"frameCount": 144})
    monkeypatch.setattr(repair_intent_media, "_assemble", assemble)
    media, evidence = await repair_intent_media.group_repair_evidence(
        repair, row, op.result_json["repairGroup"],
    )
    assert frames == [(0, "opening"), (1, "ending")]
    assert assembled[0][0] == [clip, other if mixed else clip]
    assert [(item["inFrame"], item["outFrame"]) for item in assembled[0][1]] == [(0, 72), (72, 144)]
    assert len(media) == 4 and media[-1]["bytes"] == b"group-six-second-evidence"
    assert evidence["frameCount"] == 144
    assert evidence["evidenceHashes"] == [
        hashlib.sha256(item["bytes"]).hexdigest() for item in media
    ]
    assert "storageKey" not in json.dumps(evidence)
