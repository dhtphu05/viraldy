from __future__ import annotations

import copy
from types import SimpleNamespace
from uuid import uuid4

import pytest

from viraldy.modules.smart_remake import repair_service as module
from viraldy.modules.smart_remake.engine.schemas import RenderSmartRemakeInput, UploadedMedia
from viraldy.modules.smart_remake.repair_schemas import AcceptSceneVersion, RepairSceneRequest
from viraldy.modules.smart_remake.repair_service import RepairService
from viraldy.shared.errors.base import ConflictError, NotFoundError


class MemoryRepository:
    def __init__(self):
        self.rows = {}
        self.operations = {}

    async def create(self, row):
        self.rows[row.id] = row

    async def project(self, workspace_id, project_id, **_):
        row = self.rows.get(project_id)
        if not row or row.workspace_id != workspace_id:
            raise NotFoundError("SMART_REMAKE_PROJECT_NOT_FOUND")
        return row

    async def save(self, row, state):
        row.state_json = copy.deepcopy(state)
        row.revision = state["revision"]

    async def start(self, workspace_id, project_id, key, request_hash):
        row = await self.project(workspace_id, project_id)
        if (project_id, key) in self.operations:
            operation = self.operations[project_id, key]
            if operation.request_hash != request_hash:
                raise ConflictError("SMART_REMAKE_IDEMPOTENCY_CONFLICT", "key conflict")
            return row, operation, False
        if any(op.status == "running" for op in self.operations.values()):
            raise ConflictError("SMART_REMAKE_OPERATION_BUSY", "busy")
        operation = SimpleNamespace(
            id=uuid4(), status="running", result_json={}, request_hash=request_hash
        )
        self.operations[project_id, key] = operation
        return row, operation, True

    async def finish(self, operation, status, result):
        operation.status = status
        operation.result_json = result

    async def running(self, project_id):
        return next(
            (
                op
                for (pid, _), op in self.operations.items()
                if pid == project_id and op.status == "running"
            ),
            None,
        )

    async def complete(self, row, state, operation, result):
        await self.save(row, state)
        await self.finish(operation, "completed", result)

    async def refresh(self, operation):
        return None


class MemoryMedia:
    def __init__(self):
        self.objects = {}

    async def put(self, prefix, data, _):
        key = f"{prefix}/{uuid4()}"
        self.objects[key] = data
        return key

    async def read(self, key):
        return self.objects[key]

    async def url(self, key):
        return f"https://storage.test/{key}?signed"

    async def download_url(self, key, filename):
        return f"https://storage.test/{key}?attachment={filename}"


@pytest.fixture
async def project(monkeypatch):
    workspace = uuid4()
    repository, media = MemoryRepository(), MemoryMedia()
    service = RepairService(repository, media, workspace)
    monkeypatch.setattr(
        module,
        "technical_check",
        lambda data, **_: {
            "status": "passed",
            "findings": [],
            "mediaHash": data.hex(),
            "checkedAt": "now",
        },
    )
    compiled = [
        {
            "displayOrder": index,
            "chainType": "ROOT",
            "parentSceneId": None,
            "characterNames": ["Product"],
            "prompt": f"scene {index}",
            "imagePrompt": f"image {index}",
            "videoPrompt": f"video {index}",
        }
        for index in range(2)
    ]
    await service.begin_render(
        RenderSmartRemakeInput(
            productLock={"productReference": {"characterName": "Product"}},
            sceneMap={
                "scenes": compiled,
                "targetDuration": 16,
                "sceneCount": 2,
                "aspectRatio": "9:16",
            },
            referenceAnalysis={"audioPlan": {"mode": "silent"}},
            productImage=UploadedMedia(bytes=b"product", mime_type="image/png"),
            projectName="test",
            provider="unifically",
        )
    )
    await service.capture_render_output(0, b"original scene 0", {})
    await service.capture_render_output(1, b"original scene 1", {})
    await service.capture_render_output(-1, b"original assembly", {})
    row = repository.rows[service.render_project_id]
    return service, repository, media, row


def request_for(row, *, key="repair"):
    scene = row.state_json["scenes"][1]
    return RepairSceneRequest(
        baseVersionId=scene["activeVersionId"],
        expectedRevision=row.revision,
        prompt="edited scene",
        imagePrompt="edited image",
        videoPrompt="CONTROLLED REPAIR MARKER",
        idempotencyKey=key,
    )


@pytest.mark.asyncio
async def test_present_restores_scene_actions_by_display_order_without_private_context(project):
    service, _, _, row = project
    row.context_json["sceneMap"]["scenes"] = [
        {
            "displayOrder": 1,
            "shotPlan": {"shots": [
                {"physicalAction": {"movement": "lift"}, "action": "Lift the bottle."},
                {"action": "Place it on the table."},
            ]},
            "providerMetadata": {"secret": "private-provider-data"},
        },
        {
            "displayOrder": 0,
            "shotPlan": {"shots": [
                {"physicalAction": "Open the lid.", "action": "Ignored alternate action."},
                {"action": "Pour water into the bottle."},
            ]},
        },
    ]
    row.context_json["referenceAnalysis"] = {"secret": "private-analysis-data"}
    row.context_json["compileResult"] = {"secret": "private-compile-data"}
    row.state_json["scenes"].reverse()
    before_state = copy.deepcopy(row.state_json)
    before_context = copy.deepcopy(row.context_json)

    presented = await service.get(row.id)

    assert [scene["description"] for scene in presented["scenes"]] == [
        "Lift the bottle. Place it on the table.",
        "Open the lid. Pour water into the bottle.",
    ]
    assert [scene["videoPrompt"] for scene in presented["scenes"]] == ["video 1", "video 0"]
    assert not {"sceneMap", "referenceAnalysis", "compileResult", "productLock"} & presented.keys()
    assert "private-" not in str(presented)
    assert "storageKey" not in str(presented)
    assert row.state_json == before_state
    assert row.context_json == before_context


@pytest.mark.asyncio
async def test_present_prefers_stable_scene_id_and_existing_description(project):
    service, _, _, row = project
    first, second = row.state_json["scenes"]
    second["description"] = "An existing seller-facing description."
    row.context_json["sceneMap"]["scenes"] = [
        {"id": first["id"], "displayOrder": 1, "description": "The first scene's action."},
        {"id": second["id"], "displayOrder": 0, "description": "An older description."},
    ]

    presented = await service.get(row.id)

    assert presented["scenes"][0]["description"] == "The first scene's action."
    assert presented["scenes"][1]["description"] == "An existing seller-facing description."


@pytest.mark.asyncio
@pytest.mark.parametrize("compiled_scenes", [
    [],
    [{"displayOrder": 0, "prompt": "Do not expose the generation prompt."}],
    [{"id": "a-different-scene", "displayOrder": 0, "description": "Wrong scene."}],
    [
        {"displayOrder": 0, "description": "Ambiguous scene A."},
        {"displayOrder": 0, "description": "Ambiguous scene B."},
    ],
])
async def test_present_omits_description_when_no_unambiguous_scene_actions(
    project, compiled_scenes
):
    service, _, _, row = project
    row.context_json["sceneMap"]["scenes"] = compiled_scenes

    presented = await service.get(row.id)

    assert all("description" not in scene for scene in presented["scenes"])


@pytest.mark.asyncio
@pytest.mark.parametrize("scene_map", [
    None,
    [],
    "legacy scene map",
    {"scenes": None},
    {"scenes": {}},
    {"scenes": [None, "legacy scene", 42]},
    {"scenes": [{"displayOrder": 0, "shotPlan": None}]},
    {"scenes": [{"displayOrder": 0, "shotPlan": 42}]},
    {"scenes": [{"displayOrder": 0, "shotPlan": {"shots": None}}]},
    {"scenes": [{"displayOrder": 0, "shotPlan": {"shots": {}}}]},
    {"scenes": [{"displayOrder": 0, "shotPlan": {"shots": [None, 42, "legacy shot"]}}]},
])
async def test_present_keeps_legacy_project_readable_with_malformed_optional_shots(
    project, scene_map
):
    service, _, _, row = project
    row.context_json["sceneMap"] = scene_map

    presented = await service.get(row.id)

    assert all("description" not in scene for scene in presented["scenes"])
    assert [scene["videoPrompt"] for scene in presented["scenes"]] == ["video 0", "video 1"]


@pytest.mark.asyncio
async def test_present_skips_malformed_shots_but_retains_available_actions(project):
    service, _, _, row = project
    row.context_json["sceneMap"]["scenes"][0]["shotPlan"] = {
        "shots": [None, "legacy shot", {"action": "Open the bottle."}, {"action": 42}]
    }

    presented = await service.get(row.id)

    assert presented["scenes"][0]["description"] == "Open the bottle."


@pytest.mark.asyncio
async def test_regenerate_targets_one_scene_and_does_not_activate_candidate(project, monkeypatch):
    service, _, media, row = project
    before = copy.deepcopy(row.state_json)
    calls = []

    async def render(input_data, *, on_scene_output, on_task_submitted):
        calls.append(input_data)
        assert input_data.sceneMap["targetDuration"] == 8
        assert len(input_data.sceneMap["scenes"]) == 1
        assert input_data.sceneMap["scenes"][0]["displayOrder"] == 1
        assert input_data.sceneMap["scenes"][0]["promptEdited"] is True
        assert input_data.sceneMap["scenes"][0]["videoPrompt"] == "CONTROLLED REPAIR MARKER"
        assert input_data.productImage.bytes == b"product"
        await on_task_submitted(
            {"provider": "unifically", "stage": "video", "requestIds": ["paid-once"]}
        )
        await on_scene_output(0, b"new scene 1", {"providerRequestId": "provider-one-scene"})
        return {"status": "completed"}

    monkeypatch.setattr(module, "render_smart_remake", render)
    selected = row.state_json["scenes"][1]
    request = request_for(row)
    result = await service.repair(row.id, selected["id"], request)
    repeated = await service.repair(row.id, selected["id"], request)
    assert len(calls) == 1
    assert result["candidateVersionId"] == repeated["candidateVersionId"]
    assert row.state_json["scenes"][0] == before["scenes"][0]
    assert row.state_json["scenes"][1]["activeVersionId"] == selected["activeVersionId"]
    assert row.state_json["revision"] == 1
    candidate = row.state_json["scenes"][1]["versions"][-1]
    assert media.objects[candidate["storageKey"]] == b"new scene 1"
    assert candidate["usedByRevision"] is None
    assert "storageKey" not in str(result["project"])
    assert result["project"]["productImageUrl"].endswith("?signed")


@pytest.mark.asyncio
async def test_accept_then_rollback_preserves_other_clip_and_requires_revision(
    project, monkeypatch
):
    service, _, media, row = project
    scene = row.state_json["scenes"][1]
    original_version = scene["activeVersionId"]
    candidate = copy.deepcopy(scene["versions"][0])
    candidate["id"] = str(uuid4())
    candidate["parentVersionId"] = original_version
    candidate["usedByRevision"] = None
    candidate["storageKey"] = await media.put("owned", b"candidate", "video/mp4")
    scene["versions"].append(candidate)
    untouched = copy.deepcopy(row.state_json["scenes"][0])
    compositions = []

    async def compose(current, state):
        compositions.append(
            [
                module._version(item, item["activeVersionId"])["storageKey"]
                for item in state["scenes"]
            ]
        )
        return b"assembled", {"status": "passed"}

    monkeypatch.setattr(service, "_compose", compose)
    result = await service.accept(
        row.id,
        AcceptSceneVersion(
            sceneId=scene["id"],
            versionId=candidate["id"],
            expectedRevision=1,
            idempotencyKey="accept",
        ),
    )
    assert result["project"]["revision"] == 2
    assert row.state_json["scenes"][0] == untouched
    assert row.state_json["scenes"][1]["activeVersionId"] == candidate["id"]
    assert row.state_json["scenes"][1]["versions"][-1]["usedByRevision"] == 2
    with pytest.raises(ConflictError, match="Refresh"):
        await service.accept(
            row.id,
            AcceptSceneVersion(
                sceneId=scene["id"],
                versionId=original_version,
                expectedRevision=1,
                idempotencyKey="stale",
            ),
        )
    result = await service.accept(
        row.id,
        AcceptSceneVersion(
            sceneId=scene["id"],
            versionId=original_version,
            expectedRevision=2,
            idempotencyKey="rollback",
        ),
    )
    assert result["project"]["revision"] == 3
    assert compositions[0][0] == compositions[1][0]
    assert compositions[0][1] != compositions[1][1]


@pytest.mark.asyncio
async def test_assembly_failure_does_not_change_active_video(project, monkeypatch):
    service, _, _, row = project
    before = copy.deepcopy(row.state_json)

    async def fail(*_):
        return b"broken", {"status": "failed"}

    monkeypatch.setattr(service, "_compose", fail)
    scene = row.state_json["scenes"][1]
    with pytest.raises(ConflictError):
        await service.accept(
            row.id,
            AcceptSceneVersion(
                sceneId=scene["id"],
                versionId=scene["activeVersionId"],
                expectedRevision=1,
                idempotencyKey="fail",
            ),
        )
    assert row.state_json == before


@pytest.mark.asyncio
async def test_cross_workspace_project_and_foreign_scene_are_rejected(project):
    service, repository, media, row = project
    foreign = RepairService(repository, media, uuid4())
    with pytest.raises(NotFoundError):
        await foreign.get(row.id)
    with pytest.raises(NotFoundError):
        await service.repair(row.id, uuid4(), request_for(row))


@pytest.mark.asyncio
async def test_stale_never_used_candidate_is_rejected_but_historical_rollback_is_allowed(
    project, monkeypatch
):
    service, _, media, row = project
    scene = row.state_json["scenes"][1]
    original_id = scene["activeVersionId"]
    for label in ["A", "B"]:
        candidate = copy.deepcopy(scene["versions"][0])
        candidate.update(
            id=str(uuid4()),
            parentVersionId=original_id,
            usedByRevision=None,
            storageKey=await media.put("owned", label.encode(), "video/mp4"),
        )
        scene["versions"].append(candidate)
    a, b = scene["versions"][-2:]

    async def compose(*_):
        return b"assembled", {"status": "passed"}

    monkeypatch.setattr(service, "_compose", compose)
    await service.accept(
        row.id,
        AcceptSceneVersion(
            sceneId=scene["id"], versionId=a["id"], expectedRevision=1, idempotencyKey="A"
        ),
    )
    with pytest.raises(ConflictError, match="older scene"):
        await service.accept(
            row.id,
            AcceptSceneVersion(
                sceneId=scene["id"], versionId=b["id"], expectedRevision=2, idempotencyKey="B"
            ),
        )
    result = await service.accept(
        row.id,
        AcceptSceneVersion(
            sceneId=scene["id"],
            versionId=original_id,
            expectedRevision=2,
            idempotencyKey="rollback",
        ),
    )
    assert result["project"]["revision"] == 3


@pytest.mark.asyncio
async def test_invalid_initial_scene_is_retained_but_never_activated_or_published(
    project, monkeypatch
):
    service, _, _, row = project
    monkeypatch.setattr(
        module,
        "technical_check",
        lambda data, **_: {
            "status": "failed",
            "findings": ["Wrong duration"],
            "mediaHash": data.hex(),
            "checkedAt": "now",
        },
    )
    # A separate render session starts with an empty manifest, as in production.
    row.state_json["status"] = "incomplete"
    row.state_json.pop("finalStorageKey", None)
    await service.capture_render_output(1, b"invalid output", {})
    assert row.state_json["scenes"][1]["activeVersionId"] is None
    assert row.state_json["scenes"][1]["versions"][-1]["technicalCheck"]["status"] == "failed"
    with pytest.raises(Exception, match="technical issues"):
        await service.capture_render_output(-1, b"invalid assembly", {})
    projected = await service.get(row.id)
    assert projected["status"] == "incomplete"
    assert projected["finalVideoUrl"] == ""
    assert "downloadUrl" not in projected


@pytest.mark.asyncio
async def test_ambiguous_timeout_blocks_paid_resubmission_and_reconciles_existing_task(
    project, monkeypatch
):
    from viraldy.modules.smart_remake.engine.errors import SmartRemakeError
    from viraldy.shared.errors.base import AppError

    service, repository, _, row = project
    scene = row.state_json["scenes"][1]
    calls = []
    state = {"status": "processing"}

    async def render(input_data, *, on_scene_output, on_task_submitted):
        calls.append(input_data)
        await on_task_submitted(
            {"provider": "unifically", "stage": "video", "requestIds": ["task-once"]}
        )
        raise SmartRemakeError("poll timed out", "UNIFICALLY_POLL_TIMEOUT", {"taskId": "task-once"})

    class Client:
        async def get_task(self, task_id):
            assert task_id == "task-once"
            return state

        async def download_file(self, url):
            assert url == "https://provider.test/scene.mp4"
            return b"reconciled scene"

    monkeypatch.setattr(module, "render_smart_remake", render)
    monkeypatch.setattr(module, "UnificallyClient", Client)
    request = request_for(row)
    with pytest.raises(AppError) as caught:
        await service.repair(row.id, scene["id"], request)
    assert caught.value.details["operationStatus"] == "running"
    # A worker/process can disappear before marking the operation unresolved.
    list(repository.operations.values())[0].result_json["needsReconciliation"] = False
    assert list(repository.operations.values())[0].result_json["providerTasks"][0][
        "requestIds"
    ] == ["task-once"]
    repeated = await service.repair(row.id, scene["id"], request)
    assert repeated["status"] == "running"
    with pytest.raises(ConflictError):
        await service.repair(row.id, scene["id"], request_for(row, key="different-key"))
    assert len(calls) == 1
    state.update(status="completed", output={"video_url": "https://provider.test/scene.mp4"})
    result = await service.get(row.id)
    assert len(result["scenes"][1]["versions"]) == 2
    assert result["scenes"][1]["activeVersionId"] == scene["activeVersionId"]
    assert "pendingOperation" not in result
    await service.get(row.id)
    assert len(row.state_json["scenes"][1]["versions"]) == 2
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_refresh_reconciliation_and_original_request_create_only_one_candidate(
    project, monkeypatch
):
    import asyncio

    service, _, _, row = project
    scene = row.state_json["scenes"][1]
    submitted, release = asyncio.Event(), asyncio.Event()

    async def render(input_data, *, on_scene_output, on_task_submitted):
        await on_task_submitted(
            {"provider": "unifically", "stage": "video", "requestIds": ["task-race"]}
        )
        submitted.set()
        await release.wait()
        await on_scene_output(0, b"scene output", {})
        return {"status": "completed"}

    class Client:
        async def get_task(self, _):
            return {"status": "completed", "output": {"video_url": "https://provider.test/done"}}

        async def download_file(self, _):
            return b"scene output"

    monkeypatch.setattr(module, "render_smart_remake", render)
    monkeypatch.setattr(module, "UnificallyClient", Client)
    task = asyncio.create_task(service.repair(row.id, scene["id"], request_for(row)))
    await submitted.wait()
    await service.get(row.id)
    release.set()
    result = await task
    assert result["status"] == "completed"
    assert len(row.state_json["scenes"][1]["versions"]) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["download", "storage"])
async def test_completed_provider_retrieval_failures_reconcile_without_another_paid_create(
    project, monkeypatch, failure
):
    from viraldy.modules.smart_remake.engine.errors import SmartRemakeError
    from viraldy.shared.errors.base import AppError

    service, repository, media, row = project
    scene = row.state_json["scenes"][1]
    unavailable = {"value": True}
    creates = []
    original_put = media.put

    async def put(prefix, data, mime_type):
        if unavailable["value"] and failure == "storage":
            raise OSError("storage temporarily unavailable")
        return await original_put(prefix, data, mime_type)

    async def render(input_data, *, on_scene_output, on_task_submitted):
        creates.append(input_data)
        await on_task_submitted(
            {
                "provider": "unifically",
                "stage": "video",
                "requestIds": ["completed-once"],
            }
        )
        if failure == "download":
            raise SmartRemakeError(
                "download timed out",
                "UNIFICALLY_OUTPUT_DOWNLOAD_FAILED",
                {"url": "https://provider.test/output", "cause": "timeout"},
            )
        await on_scene_output(0, b"completed output", {})
        return {"status": "completed"}

    class Client:
        async def get_task(self, task_id):
            assert task_id == "completed-once"
            return {"status": "completed", "output": {"video_url": "https://provider.test/output"}}

        async def download_file(self, _):
            if unavailable["value"] and failure == "download":
                raise SmartRemakeError(
                    "download timed out", "UNIFICALLY_OUTPUT_DOWNLOAD_FAILED", {"cause": "timeout"}
                )
            return b"completed output"

    monkeypatch.setattr(media, "put", put)
    monkeypatch.setattr(module, "render_smart_remake", render)
    monkeypatch.setattr(module, "UnificallyClient", Client)
    with pytest.raises(AppError) as caught:
        await service.repair(row.id, scene["id"], request_for(row))
    assert caught.value.details["operationStatus"] == "running"
    assert list(repository.operations.values())[0].status == "running"
    with pytest.raises(ConflictError):
        await service.repair(row.id, scene["id"], request_for(row, key="new-explicit-key"))
    pending = await service.get(row.id)
    assert pending["pendingOperation"]["needsReconciliation"] is True
    unavailable["value"] = False
    recovered = await service.get(row.id)
    assert len(recovered["scenes"][1]["versions"]) == 2
    assert "pendingOperation" not in recovered
    await service.get(row.id)
    assert len(row.state_json["scenes"][1]["versions"]) == 2
    assert len(creates) == 1
