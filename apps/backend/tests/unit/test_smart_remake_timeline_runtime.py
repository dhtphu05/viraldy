from __future__ import annotations

import copy
from contextlib import asynccontextmanager
from types import SimpleNamespace
from uuid import uuid4

import pytest

from viraldy.modules.smart_remake import timeline_service as module
from viraldy.modules.smart_remake.repair_schemas import SaveTimelineRequest
from viraldy.modules.smart_remake.repair_service import RepairService
from viraldy.shared.errors.base import AppError


def project(durations=(48, 144)):
    scenes, units, items, sources = [], [], [], []
    offset = 0
    for index, duration in enumerate(durations):
        sid, uid, vid = (str(uuid4()) for _ in range(3))
        sources.append(
            dict(
                id=sid, startFrame=offset, endFrame=offset + duration, targetDurationFrames=duration
            )
        )
        units.append(
            dict(
                id=uid,
                sourceSceneId=sid,
                sceneIndex=index,
                rawDurationFrames=192,
                targetDurationFrames=duration,
                prompt="p",
                imagePrompt="i",
                videoPrompt="v",
            )
        )
        scenes.append(
            dict(
                id=uid,
                index=index,
                activeVersionId=vid,
                prompt="p",
                imagePrompt="i",
                videoPrompt="v",
                versions=[
                    dict(
                        id=vid,
                        storageKey=vid,
                        mediaHash="hash",
                        parentVersionId=None,
                        usedByRevision=1,
                        technicalCheck={"status": "passed"},
                    )
                ],
            )
        )
        items.append(
            dict(
                id=str(uuid4()),
                sourceSceneId=sid,
                renderUnitId=uid,
                targetStartFrame=offset,
                targetDurationFrames=duration,
                versionId=vid,
                inFrame=0,
                outFrame=duration,
                reviewed=False,
            )
        )
        offset += duration
    source = dict(fps=24, sourceStartFrame=0, sourceFrameCount=offset, scenes=sources)
    plan = dict(fps=24, provider="kie", units=units)
    timeline = dict(fps=24, totalFrames=offset, items=items)
    return SimpleNamespace(
        id=uuid4(),
        workspace_id=uuid4(),
        revision=1,
        state_json=dict(
            id=str(uuid4()),
            schemaVersion=2,
            revision=1,
            status="incomplete",
            targetDuration=offset / 24,
            provider="kie",
            sourceSceneMap=source,
            renderPlan=plan,
            draftTimeline=timeline,
            publishedTimeline=None,
            finalStorageKey="old-output",
            scenes=scenes,
        ),
        context_json=dict(
            schemaVersion=2,
            sourceSceneMap=source,
            renderPlan=plan,
            audioRequired=False,
            projectName="test",
            productKey="product",
            sourceKey="source",
        ),
    )


class Repo:
    def __init__(self, row):
        self.row, self.operations = row, {}

    async def project(self, wid, pid, **kwargs):
        assert wid == self.row.workspace_id and pid == self.row.id
        return self.row

    async def start(self, wid, pid, key, request_hash):
        if key in self.operations:
            op = self.operations[key]
            if op.request_hash != request_hash:
                raise AppError("CONFLICT", "conflict")
            return self.row, op, False
        op = SimpleNamespace(
            id=uuid4(), status="running", result_json={}, request_hash=request_hash
        )
        self.operations[key] = op
        return self.row, op, True

    async def complete(self, row, state, op, result):
        row.state_json = copy.deepcopy(state)
        row.revision = state["revision"]
        await self.finish(op, "completed", result)

    async def finish(self, op, status, result):
        op.status, op.result_json = status, copy.deepcopy(result)

    async def running(self, pid):
        return next((op for op in self.operations.values() if op.status == "running"), None)

    async def latest_operation(self, pid):
        return next(reversed(self.operations.values()), None)

    async def operation(self, wid, pid, oid):
        return next(op for op in self.operations.values() if op.id == oid)

    @asynccontextmanager
    async def execution_guard(self, oid):
        yield True


class Media:
    async def url(self, key):
        return f"https://media.test/{key}"

    async def download_url(self, key, filename):
        return await self.url(key)

    async def read(self, key):
        return b"clip"

    async def put(self, prefix, data, mime):
        return "new-output"


@pytest.fixture
def runtime(monkeypatch):
    row = project()
    repo = Repo(row)
    service = RepairService(repo, Media(), row.workspace_id)

    async def validate(*args, **kwargs):
        return None

    monkeypatch.setattr(module, "validate_selection_media", validate)
    return service, row, repo


def request(row):
    item = row.state_json["draftTimeline"]["items"][0]
    return SaveTimelineRequest(
        expectedRevision=row.state_json["revision"],
        idempotencyKey="save",
        items=[
            dict(
                renderUnitId=item["renderUnitId"],
                versionId=item["versionId"],
                inFrame=24,
                outFrame=24 + item["targetDurationFrames"],
                reviewed=True,
            )
        ],
    )


@pytest.mark.asyncio
async def test_trim_saves_review_only_and_preserves_published_output(runtime):
    service, row, repo = runtime
    result = await module.save_timeline(service, row.id, request(row))
    item = row.state_json["draftTimeline"]["items"][0]
    assert (item["inFrame"], item["outFrame"], item["reviewed"]) == (24, 72, True)
    assert row.state_json["revision"] == 2
    assert row.state_json["finalStorageKey"] == "old-output"
    assert result["status"] == "completed"


@pytest.mark.asyncio
async def test_idempotent_trim_replay_does_not_increment_revision(runtime):
    service, row, repo = runtime
    payload = request(row)
    await module.save_timeline(service, row.id, payload)
    await module.save_timeline(service, row.id, payload)
    assert row.state_json["revision"] == 2


@pytest.mark.asyncio
async def test_trim_cannot_change_planned_duration(runtime):
    service, row, repo = runtime
    payload = request(row)
    payload.items[0].outFrame = 73
    with pytest.raises(AppError, match="SMART_REMAKE_TRIM_INVALID"):
        await module.save_timeline(service, row.id, payload)
    assert row.state_json["revision"] == 1


@pytest.mark.asyncio
async def test_stale_trim_rejected(runtime):
    service, row, repo = runtime
    payload = request(row)
    payload.expectedRevision = 2
    with pytest.raises(AppError, match="SMART_REMAKE_REVISION_CONFLICT"):
        await module.save_timeline(service, row.id, payload)


@pytest.mark.asyncio
async def test_foreign_version_rejected(runtime):
    service, row, repo = runtime
    payload = request(row)
    payload.items[0].versionId = uuid4()
    with pytest.raises(AppError, match="SMART_REMAKE_VERSION_NOT_FOUND"):
        await module.save_timeline(service, row.id, payload)


@pytest.mark.parametrize("durations", [(48, 144), (72, 120, 96, 96), (24, 24, 24, 24, 96)])
def test_manifest_keeps_variable_duration_and_distinct_ids(durations):
    module.validate_manifest(project(durations))


@pytest.mark.parametrize("durations", [(216, 168)])
def test_manifest_rejects_excess_or_long_shots(durations):
    with pytest.raises(AppError, match="SMART_REMAKE_TIMELINE_INVALID"):
        module.validate_manifest(project(durations))


def test_manifest_validation_stays_enabled_with_python_optimization():
    import json
    import os
    import subprocess
    import sys
    from pathlib import Path

    row = project((216, 168))
    payload = json.dumps({"state_json": row.state_json, "context_json": row.context_json})
    code = (
        "import json\n"
        "from types import SimpleNamespace\n"
        "from viraldy.modules.smart_remake.timeline_service import validate_manifest\n"
        "from viraldy.shared.errors.base import AppError\n"
        f"row = SimpleNamespace(**json.loads({payload!r}))\n"
        "try:\n"
        "    validate_manifest(row)\n"
        "except AppError as exc:\n"
        "    raise SystemExit(0 if exc.code == 'SMART_REMAKE_TIMELINE_INVALID' else 2)\n"
        "raise SystemExit(1)\n"
    )
    result = subprocess.run(  # noqa: S603 - fixed interpreter/code and synthetic fixture data
        [sys.executable, "-O", "-c", code],
        env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[2] / "src")},
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr


def test_default_v2_provider_payload_keeps_original_speed_and_opening_direction():
    from viraldy.modules.smart_remake.engine.kie_adapter import build_kie_video_request

    scene = dict(
        prompt="Show the product",
        imagePrompt="Open on the product handle",
        videoPrompt="Lift the cup naturally, then continue holding it",
        promptEdited=True,
        originalPrompt="Show the product",
        originalImagePrompt="Open on the product handle",
        originalVideoPrompt="Lift the cup naturally, then continue holding it",
        targetDurationFrames=48,
        rawDurationFrames=192,
        shotPlan={"shots": [{"start": 0, "end": 2, "action": "lift cup"}]},
    )
    payload = build_kie_video_request(scene=scene, product_image_url="https://example.com/cup.jpg")
    prompt = payload["input"]["prompt"]
    assert "first 2 seconds" in prompt
    assert "original speed" in prompt
    assert "Open on the product handle" in prompt
    assert "then continue holding it" in prompt


@pytest.mark.asyncio
async def test_compose_failure_preserves_draft_and_published_output(runtime, monkeypatch):
    service, row, repo = runtime
    for item in row.state_json["draftTimeline"]["items"]:
        item["reviewed"] = True
    _, op, _ = await repo.start(row.workspace_id, row.id, "publish", "hash")
    op.result_json = dict(
        kind="compose",
        expectedRevision=1,
        timeline=copy.deepcopy(row.state_json["draftTimeline"]),
        mediaManifest=frozen_media(row),
    )
    before = copy.deepcopy(row.state_json)

    async def fail(*args, **kwargs):
        raise AppError("ASSEMBLY_FAILED", "failed")

    monkeypatch.setattr(module, "compose_timeline", fail)
    with pytest.raises(AppError):
        await module.TimelineWorkflow(service).execute(row.id, op.id)
    assert row.state_json == before
    assert op.status == "failed"


@pytest.mark.asyncio
async def test_compose_success_publishes_frozen_snapshot(runtime, monkeypatch):
    service, row, repo = runtime
    for item in row.state_json["draftTimeline"]["items"]:
        item["reviewed"] = True
    _, op, _ = await repo.start(row.workspace_id, row.id, "publish", "hash")
    op.result_json = dict(
        kind="compose",
        expectedRevision=1,
        timeline=copy.deepcopy(row.state_json["draftTimeline"]),
        mediaManifest=frozen_media(row),
    )

    async def compose(*args, **kwargs):
        return b"output", {"status": "passed", "frameCount": 192}

    monkeypatch.setattr(module, "compose_timeline", compose)
    await module.TimelineWorkflow(service).execute(row.id, op.id)
    assert row.state_json["publishedTimeline"] == op.result_json["timeline"]
    assert row.state_json["finalStorageKey"] == "new-output"
    assert row.state_json["revision"] == 2
    assert op.status == "completed"


def frozen_media(row):
    return [
        dict(
            versionId=s["versions"][0]["id"],
            storageKey=s["versions"][0]["storageKey"],
            mediaHash=s["versions"][0]["mediaHash"],
        )
        for s in row.state_json["scenes"]
    ]


def test_kie_worker_capacity_covers_four_raw_scene_poll_windows():
    from viraldy.modules.jobs.registry import JobType, get_job_definition

    definition = get_job_definition(JobType.SMART_REMAKE_KIE)
    assert definition.hard_timeout_seconds >= 4 * 900 + 60
    assert definition.soft_timeout_seconds < definition.hard_timeout_seconds


@pytest.mark.asyncio
async def test_compose_requires_complete_frozen_media_manifest(runtime, monkeypatch):
    service, row, repo = runtime
    for item in row.state_json["draftTimeline"]["items"]:
        item["reviewed"] = True
    _, op, _ = await repo.start(row.workspace_id, row.id, "publish", "hash")
    op.result_json = dict(
        kind="compose",
        expectedRevision=1,
        timeline=copy.deepcopy(row.state_json["draftTimeline"]),
        mediaManifest=[],
    )

    async def compose(*args, **kwargs):
        return b"output", {"status": "passed", "frameCount": 192}

    monkeypatch.setattr(module, "compose_timeline", compose)
    with pytest.raises(AppError, match="SMART_REMAKE_MEDIA_CHANGED"):
        await module.TimelineWorkflow(service).execute(row.id, op.id)
    assert row.state_json["finalStorageKey"] == "old-output"
