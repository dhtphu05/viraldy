"""One provider-window repair preserves every logical scene and atomic selection."""

from __future__ import annotations

import copy
import hashlib
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest

from tests.unit.test_smart_remake_twelve_second_windows import state_for, twelve_second_context
from viraldy.modules.smart_remake.repair_schemas import RepairSceneRequest
from viraldy.shared.errors.base import AppError


def ready_group_project():
    context = twelve_second_context()
    state = state_for(context)
    state["revision"] = 4
    for group in context["renderPlan"]["groups"]:
        for segment in group["segments"]:
            scene = next(item for item in state["scenes"] if item["id"] == segment["renderUnitId"])
            version = {
                "id": str(uuid4()),
                "parentVersionId": None,
                "storageKey": group["id"],
                "mediaHash": hashlib.sha256(group["id"].encode()).hexdigest(),
                "expectationsHash": context["expectationsHash"],
                "generationExpectations": copy.deepcopy(context["generationExpectations"]),
                "technicalCheck": {"status": "passed"},
                "frameCount": 144,
                "providerMetadata": {"renderGroupId": group["id"]},
            }
            scene.update(activeVersionId=version["id"], versions=[version])
            item = next(
                item
                for item in state["draftTimeline"]["items"]
                if item["renderUnitId"] == scene["id"]
            )
            item.update(
                versionId=version["id"],
                inFrame=segment["inFrame"],
                outFrame=segment["outFrame"],
                reviewed=False,
            )
    return SimpleNamespace(
        id=uuid4(), workspace_id=uuid4(), revision=4, context_json=context, state_json=state
    )


def test_optional_group_scope_preserves_legacy_request_serialization():
    payload = dict(
        baseVersionId=uuid4(),
        expectedRevision=4,
        prompt="a",
        imagePrompt="b",
        videoPrompt="c",
        idempotencyKey="legacy",
    )
    legacy = RepairSceneRequest(**payload).model_dump(mode="json")
    assert "repairScope" not in legacy
    grouped = RepairSceneRequest(**payload, repairScope="provider_group").model_dump(mode="json")
    assert grouped == {**legacy, "repairScope": "provider_group"}


def test_freeze_group_binds_all_active_versions_and_original_raw_offsets():
    from viraldy.modules.smart_remake.provider_group_repair import freeze_repair_group

    row = ready_group_project()
    group = row.context_json["renderPlan"]["groups"][1]
    binding = freeze_repair_group(row, group["renderUnitIds"][0])
    assert binding["group"] == group
    assert binding["anchorSceneId"] == group["renderUnitIds"][0]
    assert [value["sceneId"] for value in binding["baseVersions"]] == group["renderUnitIds"]
    assert [(value["inFrame"], value["outFrame"]) for value in binding["baseVersions"]] == [
        (value["inFrame"], value["outFrame"]) for value in group["segments"]
    ]
    assert sum(value["outFrame"] - value["inFrame"] for value in binding["baseVersions"]) == 144


@pytest.mark.parametrize("change", ["version", "range", "media", "plan"])
def test_group_binding_detects_changes_in_any_member_before_paid_submission(change):
    from viraldy.modules.smart_remake.provider_group_repair import (
        freeze_repair_group,
        validate_repair_group,
    )

    row = ready_group_project()
    binding = freeze_repair_group(row, row.state_json["scenes"][0]["id"])
    member = row.state_json["scenes"][1]
    if change == "version":
        member["activeVersionId"] = str(uuid4())
    elif change == "range":
        row.state_json["draftTimeline"]["items"][1]["inFrame"] += 1
    elif change == "media":
        member["versions"][0]["mediaHash"] = "f" * 64
    else:
        row.context_json["renderPlan"]["groups"][0]["rawDurationFrames"] = 192
    with pytest.raises(Exception) as error:
        validate_repair_group(row, binding)
    assert error.value.code == "SMART_REMAKE_GROUP_REPAIR_STALE"


def test_group_repair_preflight_counts_one_video_two_images_one_normalization():
    from viraldy.modules.smart_remake.preflight_contracts import PreflightRequest
    from viraldy.modules.smart_remake.preflight_service import calculate_preflight

    row = ready_group_project()
    anchor = row.state_json["scenes"][0]
    result = calculate_preflight(
        PreflightRequest(
            action="repair",
            projectId=str(row.id),
            expectedRevision=4,
            budgetMode="unlimited",
            sceneId=anchor["id"],
            baseVersionId=anchor["activeVersionId"],
            repairScope="provider_group",
            repairIntent={"instruction": "Giữ đúng nắp"},
        ),
        mode="live",
        bounds={},
        row=row,
    )
    assert not result.blockers
    assert result.calls.model_dump() == dict(analysis=1, image=2, video=1, inspection=0, total=4)
    assert result.scope.targetDuration == 6
    assert result.scope.sceneCount == len(
        row.context_json["renderPlan"]["groups"][0]["renderUnitIds"]
    )
    assert result.scope.repairScope == "provider_group"


@pytest.fixture
def candidate_runtime(monkeypatch):
    from viraldy.modules.smart_remake import repair_service, timeline_media
    from viraldy.modules.smart_remake.provider_group_repair import freeze_repair_group

    row = ready_group_project()
    binding = freeze_repair_group(row, row.state_json["scenes"][0]["id"])
    operation = SimpleNamespace(
        id=uuid4(),
        status="running",
        result_json={
            "kind": "repair",
            "sceneId": binding["anchorSceneId"],
            "repairGroup": binding,
            "repairScope": "provider_group",
            "request": {"repairIntent": {"instruction": "Sửa nắp"}},
            "generationExpectations": copy.deepcopy(row.context_json["generationExpectations"]),
            "expectationsHash": row.context_json["expectationsHash"],
            "repairNormalization": {"version": "repair-group-intent-normalizer-v1"},
        },
    )

    async def complete(current, state, op, result):
        current.state_json = copy.deepcopy(state)
        current.revision = state["revision"]
        op.status, op.result_json = "completed", copy.deepcopy(result)

    repository = SimpleNamespace(
        project=AsyncMock(return_value=row),
        complete=AsyncMock(side_effect=complete),
        operation=AsyncMock(return_value=operation),
    )
    media = SimpleNamespace(
        put=AsyncMock(return_value="replacement-group"),
        read=AsyncMock(return_value=b"replacement with sound"),
    )
    service = SimpleNamespace(workspace_id=row.workspace_id, repository=repository, media=media)
    client = SimpleNamespace(download_file=AsyncMock(return_value=b"replacement with sound"))
    monkeypatch.setattr(timeline_media, "probe_timeline_media", lambda data: {"frameCount": 144})
    monkeypatch.setattr(repair_service, "technical_check", lambda *a, **kw: {"status": "passed"})
    task = {
        "taskId": "one-new-wan-task",
        "url": "https://media.test/clip.mp4",
        "group": copy.deepcopy(binding["group"]),
        "model": "wan/3-0-video",
    }
    operation.result_json["tasks"] = {f"group:{binding['group']['id']}": copy.deepcopy(task)}
    return SimpleNamespace(row=row, op=operation, service=service, client=client, task=task)


@pytest.mark.asyncio
async def test_retention_commits_one_candidate_set_without_changing_active_versions(
    candidate_runtime,
):
    from viraldy.modules.smart_remake.provider_group_repair import (
        affected_group_versions,
        retain_group_repair,
    )

    value = candidate_runtime
    before = copy.deepcopy(value.row.state_json)
    await retain_group_repair(value.service, value.row, value.op, value.task, value.client)
    affected = affected_group_versions(value.row.state_json, value.op)
    assert affected and len(affected) == len(value.op.result_json["repairGroup"]["baseVersions"])
    assert value.op.result_json["candidateVersionId"] == affected[0]["candidateVersionId"]
    assert [scene["activeVersionId"] for scene in value.row.state_json["scenes"]] == [
        scene["activeVersionId"] for scene in before["scenes"]
    ]
    assert value.row.state_json["draftTimeline"] == before["draftTimeline"]
    assert value.row.revision == 4
    await retain_group_repair(value.service, value.row, value.op, value.task, value.client)
    assert value.client.download_file.await_count == value.service.media.put.await_count == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "change",
    [
        "media",
        "range",
        "member",
        "operation",
        "snapshot",
        "all_media",
        "all_task",
        "base_timeline",
    ],
)
async def test_receipt_does_not_advertise_partial_or_mismatched_candidates(
    candidate_runtime, change
):
    from viraldy.modules.smart_remake.provider_group_repair import (
        affected_group_versions,
        group_repair_public_fields,
        retain_group_repair,
    )

    value = candidate_runtime
    await retain_group_repair(value.service, value.row, value.op, value.task, value.client)
    candidate = value.row.state_json["scenes"][1]["versions"][-1]
    if change == "media":
        candidate["mediaHash"] = "f" * 64
    elif change == "range":
        candidate["suggestedInFrame"] += 1
    elif change == "member":
        value.row.state_json["scenes"][1]["versions"].pop()
    elif change == "operation":
        candidate["providerMetadata"]["repairOperationId"] = str(uuid4())
    elif change == "snapshot":
        candidate["generationExpectations"]["productLock"]["productName"] = "Changed product"
    elif change == "base_timeline":
        candidate["providerMetadata"]["repairBaseTimeline"][0]["inFrame"] += 1
    else:
        for item in value.op.result_json["affectedVersions"]:
            member = next(
                scene for scene in value.row.state_json["scenes"] if scene["id"] == item["sceneId"]
            )
            if change == "all_media":
                member["versions"][-1]["mediaHash"] = "f" * 64
            else:
                member["versions"][-1]["providerMetadata"]["providerRequestId"] = "another-task"
    assert affected_group_versions(value.row.state_json, value.op) is None
    public = group_repair_public_fields(value.row.state_json, value.op)
    assert public["candidateVersionId"] is None
    assert all(item["candidateVersionId"] is None for item in public["affectedVersions"])
    assert "storageKey" not in str(public)


@pytest.mark.asyncio
async def test_accept_group_updates_all_offsets_once_and_queues_only_local_preview(
    candidate_runtime,
    monkeypatch,
):
    from viraldy.modules.smart_remake import project_preview
    from viraldy.modules.smart_remake.provider_group_repair import (
        accept_group_repair,
        retain_group_repair,
    )

    value = candidate_runtime
    value.row.context_json["p0"].update(inputHash="a" * 64, actorId=str(uuid4()))
    await retain_group_repair(value.service, value.row, value.op, value.task, value.client)
    untouched = copy.deepcopy(value.row.state_json["scenes"][12:])
    accept = SimpleNamespace(id=uuid4(), status="running", result_json={})
    queue = AsyncMock()
    monkeypatch.setattr(project_preview, "queue_automatic_preview", queue)
    candidate = value.row.state_json["scenes"][0]["versions"][-1]
    await accept_group_repair(
        value.service, value.row, copy.deepcopy(value.row.state_json), accept, candidate
    )
    assert accept.status == "completed" and value.row.revision == 5
    assert value.row.state_json["scenes"][12:] == untouched
    for affected, segment in zip(
        accept.result_json["affectedVersions"],
        value.op.result_json["repairGroup"]["group"]["segments"],
        strict=True,
    ):
        scene = next(
            scene for scene in value.row.state_json["scenes"] if scene["id"] == affected["sceneId"]
        )
        item = next(
            item
            for item in value.row.state_json["draftTimeline"]["items"]
            if item["renderUnitId"] == scene["id"]
        )
        assert scene["activeVersionId"] == item["versionId"] == affected["candidateVersionId"]
        assert (item["inFrame"], item["outFrame"]) == (segment["inFrame"], segment["outFrame"])
        assert item["reviewed"] is False
    marker = value.row.context_json["p0"]["preview"]
    assert marker["status"] == "pending" and marker["revision"] == 5
    assert marker["requestKey"].startswith(f"preview:{accept.id}:")
    queue.assert_awaited_once()
    assert not value.row.context_json["p0"].get("release", {}).get("activeApprovalId")


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["base", "range", "candidate", "technical", "blob"])
async def test_accept_group_rejects_all_members_atomically_if_any_binding_changed(
    candidate_runtime,
    change,
):
    from viraldy.modules.smart_remake.provider_group_repair import (
        accept_group_repair,
        retain_group_repair,
    )

    value = candidate_runtime
    await retain_group_repair(value.service, value.row, value.op, value.task, value.client)
    member = value.row.state_json["scenes"][1]
    if change == "base":
        member["activeVersionId"] = str(uuid4())
    elif change == "range":
        value.row.state_json["draftTimeline"]["items"][1]["inFrame"] += 1
    elif change == "candidate":
        member["versions"][-1]["mediaHash"] = "f" * 64
    elif change == "technical":
        member["versions"][-1]["technicalCheck"]["status"] = "failed"
    else:
        value.service.media.read = AsyncMock(return_value=b"changed bytes")
    before = copy.deepcopy(value.row.state_json)
    accept = SimpleNamespace(id=uuid4(), status="running", result_json={})
    with pytest.raises(AppError):
        await accept_group_repair(
            value.service,
            value.row,
            copy.deepcopy(before),
            accept,
            value.row.state_json["scenes"][0]["versions"][-1],
        )
    assert value.row.state_json == before and accept.status == "running"


@pytest.mark.asyncio
async def test_enqueue_group_repair_freezes_every_base_before_dispatch(
    candidate_runtime, monkeypatch
):
    from viraldy.modules.smart_remake import kie_workflow
    from viraldy.modules.smart_remake import service as boundary

    value = candidate_runtime
    value.service._operation_result = AsyncMock(return_value={"queued": True})
    value.service.repository.start = AsyncMock(return_value=(value.row, value.op, True))

    async def finish(operation, status, result):
        operation.status, operation.result_json = status, copy.deepcopy(result)

    value.service.repository.finish = AsyncMock(side_effect=finish)
    value.service.repository.attach_processing_job = AsyncMock()
    job = SimpleNamespace(id=uuid4())
    queue = AsyncMock(return_value=job)
    monkeypatch.setattr(kie_workflow, "_service", lambda *args: value.service)
    monkeypatch.setattr(kie_workflow, "_dispatch", AsyncMock())
    monkeypatch.setattr(
        kie_workflow, "JobService", lambda *args: SimpleNamespace(request_mvp_job=queue)
    )
    monkeypatch.setattr(boundary, "require_kie_renderer", lambda *args: None)
    monkeypatch.setattr(boundary, "require_openai_images", lambda *args: None)
    anchor = value.row.state_json["scenes"][0]
    request = RepairSceneRequest(
        expectedRevision=4,
        baseVersionId=anchor["activeVersionId"],
        idempotencyKey="one-window",
        repairScope="provider_group",
        repairIntent={"instruction": "Sửa nắp"},
    )
    await kie_workflow.enqueue_kie_repair(
        object(),
        SimpleNamespace(),
        value.row.workspace_id,
        value.row.id,
        UUID(anchor["id"]),
        request,
    )
    result = value.op.result_json
    assert result["repairGroup"]["anchorSceneId"] == anchor["id"]
    assert [scene["renderUnitId"] for scene in result["repairBaseScenes"]] == (
        result["repairGroup"]["group"]["renderUnitIds"]
    )
    assert result["request"]["repairScope"] == result["repairScope"] == "provider_group"
    runtime = queue.call_args.args[4]["kie_runtime"]
    assert runtime["videoCallCount"] == 1 and runtime["conditioningImageCount"] == 2
    assert runtime["analysisCallCount"] == 1


@pytest.mark.asyncio
async def test_worker_repairs_one_whole_window_and_replay_never_submits_more(
    candidate_runtime,
    monkeypatch,
):
    from contextlib import asynccontextmanager
    from types import ModuleType

    from viraldy.modules.smart_remake import kie_workflow, repair_intent_workflow
    from viraldy.modules.smart_remake.kie_workflow import KieWorkflow

    value = candidate_runtime

    @asynccontextmanager
    async def guard(*args):
        yield True

    async def finish(operation, status, result):
        operation.status, operation.result_json = status, copy.deepcopy(result)

    value.service.repository.execution_guard = guard
    value.service.repository.finish = AsyncMock(side_effect=finish)
    value.service.settings = SimpleNamespace()
    value.row.context_json.update(audioRequired=True, productKey="product")
    value.op.result_json.update(sceneIndex=0, tasks={})
    images, submits = [], []

    async def read(key):
        return b"product" if key == value.row.context_json["productKey"] else key.encode()

    value.service.media.read = AsyncMock(side_effect=read)

    async def prepare(**kwargs):
        index, role = kwargs["index"], kwargs["frame_role"]
        images.append((index, role))
        key = f"image-{index}-{role}"
        return {
            "storageKey": key,
            "mediaHash": hashlib.sha256(key.encode()).hexdigest(),
            "mimeType": "image/png",
        }

    helper = ModuleType("viraldy.modules.smart_remake.image_workflow")
    helper.prepare_scene_image = prepare
    monkeypatch.setitem(__import__("sys").modules, helper.__name__, helper)

    async def resolve(repair, row, operation, **kwargs):
        from viraldy.modules.smart_remake.repair_intent import repair_base_scene

        ids = operation.result_json["repairGroup"]["group"]["renderUnitIds"]
        operation.result_json["compiledScenes"] = [
            repair_base_scene(row, scene)
            for scene in row.state_json["scenes"]
            if scene["id"] in ids
        ]
        return True

    monkeypatch.setattr(repair_intent_workflow, "resolve_repair_intent", resolve)
    monkeypatch.setattr(kie_workflow, "require_generation_policy", AsyncMock())
    monkeypatch.setattr(
        kie_workflow, "reserve_generation_attempt", AsyncMock(return_value=(None, True))
    )
    monkeypatch.setattr(kie_workflow, "settle_generation_attempt", AsyncMock())

    async def create(**kwargs):
        submits.append(kwargs)
        return {"task_id": "one-new-wan-task"}

    value.client.create_task = create
    value.client.get_task = AsyncMock(
        return_value={
            "status": "completed",
            "output": {"video_url": value.task["url"]},
        }
    )
    value.client.upload_file = AsyncMock(return_value="https://media.test/conditioning.png")
    runner = KieWorkflow(
        value.service, client=value.client, image_client=object(), poll_timeout_seconds=0
    )
    await runner.execute(value.row.id, value.op.id)
    assert len(submits) == 1
    assert submits[0]["input_data"]["duration"] == 6
    assert submits[0]["input_data"]["audio"] is True
    assert len(images) == 2
    assert images == [
        (0, "opening"),
        (len(value.op.result_json["repairGroup"]["group"]["renderUnitIds"]) - 1, "ending"),
    ]
    assert value.op.status == "completed"
    assert len(value.op.result_json["affectedVersions"]) == len(
        value.op.result_json["repairGroup"]["baseVersions"]
    )
    await runner.execute(value.row.id, value.op.id)
    assert len(submits) == 1 and len(images) == 2


@pytest.mark.asyncio
async def test_second_group_repair_uses_previously_accepted_first_group_handoff(candidate_runtime):
    from viraldy.modules.smart_remake.engine.window_continuity import build_window_context
    from viraldy.modules.smart_remake.generation_expectations import expectations_hash
    from viraldy.modules.smart_remake.kie_workflow import KieWorkflow
    from viraldy.modules.smart_remake.provider_group_repair import freeze_repair_group

    value = candidate_runtime
    first, second = value.row.context_json["renderPlan"]["groups"]
    previous_scene = next(
        scene
        for scene in value.row.state_json["scenes"]
        if scene["id"] == first["renderUnitIds"][-1]
    )
    active = previous_scene["versions"][0]
    snapshot = copy.deepcopy(active["generationExpectations"])
    previous = next(
        scene for scene in snapshot["scenes"] if scene["renderUnitId"] == previous_scene["id"]
    )
    previous["videoPrompt"] = "Accepted repair: hold the closed pink bottle still."
    previous["shotPlan"]["shots"] = [
        {
            "action": "Hold the repaired closed lid still",
            "stateAfter": "Lid is fully closed",
        }
    ]
    active.update(generationExpectations=snapshot, expectationsHash=expectations_hash(snapshot))
    result = {
        "kind": "repair",
        "tasks": {},
        "repairGroup": freeze_repair_group(
            value.row,
            second["renderUnitIds"][0],
        ),
    }
    value.op.result_json = result

    async def finish(operation, status, result):
        operation.status, operation.result_json = status, copy.deepcopy(result)

    value.service.repository.finish = AsyncMock(side_effect=finish)
    await KieWorkflow(value.service, client=object())._freeze_plan(value.row, value.op)
    frozen = value.op.result_json["generationExpectations"]
    context = build_window_context(value.row.context_json["renderPlan"], second, frozen)
    assert context["previousAction"] == "Hold the repaired closed lid still"
    assert (
        next(scene for scene in frozen["scenes"] if scene["renderUnitId"] == previous_scene["id"])[
            "shotPlan"
        ]["shots"][-1]["stateAfter"]
        == "Lid is fully closed"
    )


def test_queued_group_receipt_has_known_base_ids_and_no_storage_locators(candidate_runtime):
    from viraldy.modules.smart_remake.provider_group_repair import group_repair_public_fields

    value = candidate_runtime
    public = group_repair_public_fields(value.row.state_json, value.op)
    assert public["repairScope"] == "provider_group"
    assert all(
        item["baseVersionId"] and item["candidateVersionId"] is None
        for item in public["affectedVersions"]
    )
    assert "storageKey" not in str(public)
