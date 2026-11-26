from __future__ import annotations

import copy
import hashlib
from contextlib import asynccontextmanager
from types import SimpleNamespace
from uuid import uuid4

import pytest

from tests.smart_remake_expectations import install_expectations
from viraldy.modules.smart_remake import image_workflow
from viraldy.modules.smart_remake import kie_workflow as module
from viraldy.modules.smart_remake.engine import kie_adapter
from viraldy.modules.smart_remake.kie_workflow import KieWorkflow
from viraldy.shared.errors.base import AppError


class Repository:
    def __init__(self, row, operation):
        self.row, self.op = row, operation
        self.history = []

    @asynccontextmanager
    async def execution_guard(self, operation_id):
        yield True

    async def project(self, workspace_id, project_id, **kwargs):
        assert workspace_id == self.row.workspace_id and project_id == self.row.id
        return self.row

    async def operation(self, workspace_id, project_id, operation_id, **kwargs):
        assert operation_id == self.op.id
        return self.op

    async def finish(self, operation, status, result):
        operation.status, operation.result_json = status, copy.deepcopy(result)
        self.history.append(copy.deepcopy(result))

    async def complete(self, row, state, operation, result):
        row.state_json = copy.deepcopy(state)
        await self.finish(operation, "completed", result)


class Media:
    async def read(self, key):
        return key.encode()

    async def put(self, prefix, data, mime_type):
        return "stored-candidate"


class Repair:
    def __init__(self, row, op):
        self.workspace_id = row.workspace_id
        self.repository = Repository(row, op)
        self.media = Media()
        self.captured = []
        self.render_project_id = None

    async def capture_render_output(self, index, data, metadata):
        self.captured.append(index)
        state = self.repository.row.state_json
        if index == -1:
            state["status"] = "ready"
            state["finalStorageKey"] = "final"
        else:
            state["scenes"][index]["versions"].append(
                {"id": "initial-version", "providerMetadata": metadata}
            )
            state["scenes"][index]["activeVersionId"] = "initial-version"

    async def _compose(self, row, state):
        return b"final", {"status": "passed"}


class Client:
    def __init__(self, repository):
        self.repository = repository
        self.submits, self.polls = [], []
        self.downloads = 0
        self.fail_download = self.fail_submit = False
        self.status = "completed"

    async def upload_file(self, media):
        return "https://media.test/product.png"

    async def create_task(self, **kwargs):
        assert self.repository.op.result_json["tasks"]["0"]["status"] == "submitting"
        self.submits.append(kwargs)
        if self.fail_submit:
            raise TimeoutError("response lost")
        return {"task_id": "paid-once", "status": "queued"}

    async def get_task(self, task_id):
        self.polls.append(task_id)
        return {
            "task_id": task_id,
            "status": self.status,
            "output": {"video_url": "https://media.test/video.mp4"},
        }

    async def download_file(self, url):
        self.downloads += 1
        if self.fail_download:
            raise TimeoutError("download unavailable")
        return b"candidate"


@pytest.fixture
def workflow(monkeypatch):
    scene = {
        "id": str(uuid4()),
        "index": 0,
        "activeVersionId": None,
        "versions": [],
        "prompt": "direction",
        "imagePrompt": "image",
        "videoPrompt": "motion",
    }
    row = SimpleNamespace(
        id=uuid4(),
        workspace_id=uuid4(),
        state_json={"status": "rendering", "scenes": [scene]},
        context_json={
            "productKey": "product",
            "productMimeType": "image/png",
            "sceneMap": {"scenes": [scene]},
            "productLock": {},
            "referenceAnalysis": {},
            "audioRequired": False,
            "renderPlan": {
                "imageModel": "gpt-image-2.6-sunburst",
                "units": [
                    {
                        "id": scene["id"],
                        "sceneIndex": 0,
                        "targetDurationFrames": 192,
                        "rawDurationFrames": 192,
                    }
                ]
            },
        },
    )
    # The source reader/extractor are explicit offline doubles in this workflow test.
    install_expectations(row.context_json, source_bytes=b"product")
    op = SimpleNamespace(id=uuid4(), status="running", result_json={"kind": "render", "tasks": {}})
    repair = Repair(row, op)
    client = Client(repair.repository)
    real_prepare = image_workflow.prepare_scene_image

    async def prepare_scene_image(**kwargs):
        if kwargs["operation"] is not op:
            return await real_prepare(**kwargs)
        frame_role = kwargs.get("frame_role", "opening")
        key = f"conditioned-{frame_role}"
        return {
            "storageKey": key,
            "mimeType": "image/png",
            "mediaHash": hashlib.sha256(key.encode()).hexdigest(),
            "expectationsHash": kwargs["operation"].result_json["expectationsHash"],
            "frameRole": frame_role,
        }

    monkeypatch.setattr(image_workflow, "prepare_scene_image", prepare_scene_image)
    monkeypatch.setattr(
        kie_adapter,
        "build_kie_group_request",
        lambda **kwargs: {
            "model": "veo-3-1",
            "input": {
                "model": "veo3_lite",
                "generation_type": "FIRST_AND_LAST_FRAMES_2_VIDEO",
                "aspect_ratio": "9:16",
                "duration": 8,
                "resolution": "720p",
                "enable_translation": False,
                "prompt": kwargs["scenes"][0]["prompt"],
                "image_urls": kwargs["reference_image_urls"],
            },
        },
    )
    monkeypatch.setattr(module, "get_kie_poll_timeout_seconds", lambda: 0)
    return KieWorkflow(repair, client=client, image_client=object()), repair, client, row, op


@pytest.mark.asyncio
async def test_initial_render_persists_task_and_retains_scene_before_assembly(workflow):
    runner, repair, client, row, op = workflow
    await runner.execute(row.id, op.id)
    assert len(client.submits) == 1
    assert client.polls == ["paid-once"]
    assert repair.captured == [0, -1]
    assert op.status == "completed"
    assert row.state_json["status"] == "ready"
    assert any(
        item["tasks"].get("0", {}).get("taskId") == "paid-once"
        for item in repair.repository.history
    )
    assert op.result_json["expectationsHash"] == row.context_json["expectationsHash"]
    assert (
        row.state_json["scenes"][0]["versions"][0]["providerMetadata"]["expectationsHash"]
        == row.context_json["expectationsHash"]
    )
    await runner.execute(row.id, op.id)
    assert len(client.submits) == 1


@pytest.mark.asyncio
async def test_download_failure_resumes_known_task_without_paid_submit(workflow):
    runner, repair, client, row, op = workflow
    client.fail_download = True
    with pytest.raises(RuntimeError):
        await runner.execute(row.id, op.id)
    assert op.status == "running"
    assert op.result_json["tasks"]["0"]["taskId"] == "paid-once"
    # Simulate restoration after a compiler upgrade without upgrading the paid task.
    row.context_json.pop("generationExpectations")
    row.context_json.pop("expectationsHash")
    client.fail_download = False
    await runner.execute(row.id, op.id)
    assert len(client.submits) == 1
    assert client.downloads == 2


@pytest.mark.asyncio
async def test_unknown_submission_never_posts_again_on_worker_retry(workflow):
    runner, repair, client, row, op = workflow
    client.fail_submit = True
    with pytest.raises(AppError, match="SMART_REMAKE_SUBMISSION_UNRESOLVED"):
        await runner.execute(row.id, op.id)
    # An old ambiguous submission must not become new work after a schema upgrade.
    row.context_json.pop("generationExpectations")
    row.context_json.pop("expectationsHash")
    with pytest.raises(AppError, match="SMART_REMAKE_SUBMISSION_UNRESOLVED"):
        await runner.execute(row.id, op.id)
    assert len(client.submits) == 1
    assert op.result_json["needsReconciliation"] is True


@pytest.mark.asyncio
async def test_provider_failure_is_terminal_but_does_not_replace_scene(workflow):
    runner, repair, client, row, op = workflow
    client.status = "failed"
    with pytest.raises(AppError, match="KIE_TASK_FAILED"):
        await runner.execute(row.id, op.id)
    assert op.status == "failed"
    assert repair.captured == []


@pytest.mark.asyncio
async def test_read_only_reconciliation_never_submits_missing_task(workflow):
    runner, repair, client, row, op = workflow
    await runner.execute(row.id, op.id, reconcile_only=True)
    assert client.submits == []
    assert op.status == "running"


@pytest.mark.asyncio
async def test_worker_claim_fence_runs_before_paid_submit(workflow):
    runner, repair, client, row, op = workflow

    def superseded():
        raise AppError("JOB_ATTEMPT_SUPERSEDED", "superseded")

    runner.ensure_active = superseded
    with pytest.raises(AppError, match="JOB_ATTEMPT_SUPERSEDED"):
        await runner.execute(row.id, op.id)
    assert client.submits == []


@pytest.mark.asyncio
async def test_poll_timeout_and_manual_refresh_use_same_recorded_task(workflow):
    runner, repair, client, row, op = workflow
    client.status = "processing"
    with pytest.raises(RuntimeError):
        await runner.execute(row.id, op.id)
    assert op.result_json["needsReconciliation"] is True
    row.context_json.pop("generationExpectations")
    row.context_json.pop("expectationsHash")
    await runner.execute(row.id, op.id, reconcile_only=True)
    assert len(client.submits) == 1
    client.status = "completed"
    await runner.execute(row.id, op.id, reconcile_only=True)
    assert op.status == "completed"
    assert len(client.submits) == 1


@pytest.mark.asyncio
async def test_failed_technical_check_releases_operation_for_controlled_scene_repair(workflow):
    runner, repair, client, row, op = workflow

    async def invalid_assembly(*args):
        raise AppError("SMART_REMAKE_TECHNICAL_CHECK_FAILED", "invalid media")

    repair._compose = invalid_assembly
    with pytest.raises(AppError):
        await runner.execute(row.id, op.id)
    assert op.status == "failed"
    assert op.result_json["errorCode"] == "SMART_REMAKE_TECHNICAL_CHECK_FAILED"
    assert repair.captured == [0]


@pytest.mark.asyncio
async def test_repair_retains_candidate_without_activating_or_replacing_other_scene(
    workflow, monkeypatch
):
    runner, repair, client, row, op = workflow
    row.state_json["scenes"][0]["activeVersionId"] = "original"
    row.state_json["scenes"][0]["versions"] = [{"id": "original", "providerMetadata": {}}]
    op.result_json = {
        "kind": "repair",
        "sceneIndex": 0,
        "request": {"baseVersionId": "original"},
        "compiledScene": row.state_json["scenes"][0],
        "tasks": {},
    }
    monkeypatch.setattr(
        module,
        "_new_version",
        lambda *args, **kwargs: {
            "id": "candidate",
            "providerMetadata": args[4],
            "usedByRevision": None,
        },
    )
    await runner.execute(row.id, op.id)
    assert op.status == "completed"
    assert op.result_json["candidateVersionId"] == "candidate"
    assert row.state_json["scenes"][0]["activeVersionId"] == "original"
    assert repair.captured == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "code",
    ["KIE_AUTH_FAILED", "KIE_CREDITS_EXHAUSTED", "KIE_RATE_LIMITED", "KIE_VALIDATION_FAILED"],
)
async def test_explicit_provider_rejection_is_retryable_with_new_operation(workflow, code):
    from viraldy.modules.smart_remake.engine.errors import SmartRemakeError

    runner, repair, client, row, op = workflow

    async def rejected(**kwargs):
        raise SmartRemakeError("rejected", code, {"providerCode": 402})

    client.create_task = rejected
    with pytest.raises(AppError) as caught:
        await runner.execute(row.id, op.id)
    assert caught.value.code == code
    assert op.status == "failed"
    assert not op.result_json.get("needsReconciliation")


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["upload", "validation"])
async def test_pre_submit_failures_are_terminal_and_leave_no_paid_task(
    workflow, monkeypatch, failure
):
    from viraldy.modules.smart_remake.engine.errors import SmartRemakeValidationError

    runner, repair, client, row, op = workflow
    if failure == "upload":

        async def failed_upload(media):
            raise TimeoutError("temporary upload failure")

        client.upload_file = failed_upload
    else:

        def invalid(**kwargs):
            raise SmartRemakeValidationError("prompt too long", "KIE_VALIDATION_FAILED")

        monkeypatch.setattr(kie_adapter, "build_kie_group_request", invalid)
    with pytest.raises(AppError):
        await runner.execute(row.id, op.id)
    assert op.status == "failed"
    assert not op.result_json.get("needsReconciliation")
    assert client.submits == []
