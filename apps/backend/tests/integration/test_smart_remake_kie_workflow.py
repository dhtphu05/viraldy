"""Offline durable KIE journeys against an isolated, migrated PostgreSQL database."""

from __future__ import annotations

import asyncio
import copy
import hashlib
import subprocess
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from io import BytesIO
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from PIL import Image
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from testcontainers.postgres import PostgresContainer

from alembic import command
from alembic.config import Config
from viraldy.modules.identity.models import UserModel
from viraldy.modules.jobs.models import ProcessingJobModel
from viraldy.modules.smart_remake import kie_worker, kie_workflow
from viraldy.modules.smart_remake.budget_models import SmartRemakeAttemptModel
from viraldy.modules.smart_remake.engine.media_binaries import ffmpeg_path
from viraldy.modules.smart_remake.engine.schemas import RenderSmartRemakeInput, UploadedMedia
from viraldy.modules.smart_remake.generation_expectations import (
    build_generation_expectations,
    expectations_hash,
)
from viraldy.modules.smart_remake.models import (
    SmartRemakeOperationModel,
    SmartRemakeProjectModel,
)
from viraldy.modules.smart_remake.project_contracts import SmartRemakeIntakeRequest
from viraldy.modules.smart_remake.project_policy import (
    constraints_hash,
    rights_snapshot,
    stable_hash,
)
from viraldy.modules.smart_remake.repair_repository import RepairRepository
from viraldy.modules.smart_remake.repair_schemas import AcceptSceneVersion, RepairSceneRequest
from viraldy.modules.smart_remake.repair_service import RepairService
from viraldy.modules.workspaces.models import WorkspaceModel
from viraldy.platform.config.settings import get_settings
from viraldy.shared.errors.base import AppError, ConflictError, NotFoundError


@pytest.fixture(scope="module")
def kie_database_url():
    with PostgresContainer("postgres:16.6-alpine") as postgres:
        sync_url = postgres.get_connection_url().replace(
            "postgresql+psycopg2", "postgresql+psycopg"
        )
        async_url = sync_url.replace("postgresql+psycopg", "postgresql+asyncpg")
        with pytest.MonkeyPatch.context() as patch:
            patch.setenv("DATABASE_SYNC_URL", sync_url)
            patch.setenv("DATABASE_URL", async_url)
            get_settings.cache_clear()
            try:
                command.upgrade(Config("alembic.ini"), "head")
                yield async_url
            finally:
                get_settings.cache_clear()


@pytest.fixture(scope="module")
def vertical_clips(tmp_path_factory):
    """Real media keeps version checks and final assembly inside the integration."""
    root = tmp_path_factory.mktemp("kie-clips")
    clips = []
    for color in ("red", "blue", "green"):
        target = root / f"{color}.mp4"
        subprocess.run(  # noqa: S603 - fixed argv and pytest-owned output path
            [
                ffmpeg_path(),
                "-y",
                "-f",
                "lavfi",
                "-i",
                f"color=c={color}:s=90x160:r=24:d=8",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-an",
                str(target),
            ],
            check=True,
            capture_output=True,
            timeout=30,
        )
        clips.append(target.read_bytes())
    return clips


class MemoryMedia:
    def __init__(self):
        self.objects = {}

    async def put(self, prefix, data, mime_type):
        key = f"{prefix}/{uuid4()}"
        self.objects[key] = data
        return key

    async def read(self, key):
        return self.objects[key]

    async def url(self, key):
        return f"https://storage.example.test/{key}?signed"

    async def download_url(self, key, filename):
        return f"https://storage.example.test/{key}?attachment={filename}"


class FakeKieClient:
    def __init__(self, harness, clips):
        self.harness, self.clips = harness, clips
        self.creates, self.polls = [], []
        self.fail_download = False
        self.fail_submit = False

    async def upload_file(self, media):
        assert media.bytes == seller_product_png()
        return "https://8.8.8.8/product.png"

    async def create_task(self, *, model, input_data):
        # A separate connection must observe the committed intent before paid work.
        async with self.harness.sessions() as factory, factory() as session:
            operations = (
                await session.scalars(
                    select(SmartRemakeOperationModel)
                    .join(SmartRemakeProjectModel)
                    .where(
                        SmartRemakeProjectModel.workspace_id == self.harness.workspace_id,
                        SmartRemakeOperationModel.status == "running",
                    )
                )
            ).all()
            assert any(
                task.get("status") == "submitting"
                for operation in operations
                for task in operation.result_json.get("tasks", {}).values()
            )
            attempts = (
                await session.scalars(
                    select(SmartRemakeAttemptModel).where(
                        SmartRemakeAttemptModel.workspace_id == self.harness.workspace_id,
                        SmartRemakeAttemptModel.stage == "video",
                        SmartRemakeAttemptModel.status == "submitted",
                    )
                )
            ).all()
            assert attempts and all(attempt.estimated_usd > 0 for attempt in attempts)
        marker = "OFFLINE_TEST_SCENE_INDEX="
        prompt = input_data.get("prompt", "")
        scene_index = (
            int(prompt.split(marker)[1].split()[0]) if marker in prompt else len(self.creates)
        )
        self.creates.append({"model": model, **input_data, "scene_index": scene_index})
        if self.fail_submit:
            raise TimeoutError("KIE accepted the request but the response was lost")
        return {"task_id": f"task-{len(self.creates)}", "status": "queued"}

    async def get_task(self, task_id):
        # Restart/polling must use a task ID already visible to another process.
        async with self.harness.sessions() as factory, factory() as session:
            operations = (
                await session.scalars(
                    select(SmartRemakeOperationModel)
                    .join(SmartRemakeProjectModel)
                    .where(SmartRemakeProjectModel.workspace_id == self.harness.workspace_id)
                )
            ).all()
            assert any(
                task.get("taskId") == task_id
                for operation in operations
                for task in operation.result_json.get("tasks", {}).values()
            )
        self.polls.append(task_id)
        return {
            "task_id": task_id,
            "status": "completed",
            "output": {"video_url": f"https://media.example.test/{task_id}.mp4"},
        }

    async def download_file(self, url):
        if self.fail_download:
            raise TimeoutError("output temporarily unavailable")
        number = int(url.rsplit("task-", 1)[1].split(".", 1)[0])
        return self.clips[(number - 1) % len(self.clips)]


@dataclass
class Harness:
    database_url: str
    workspace_id: UUID = field(default_factory=uuid4)
    foreign_workspace_id: UUID = field(default_factory=uuid4)
    media: MemoryMedia = field(default_factory=MemoryMedia)
    dispatched: list = field(default_factory=list)

    @property
    def settings(self):
        return SimpleNamespace(database_url=self.database_url, ai_mode="live")

    @asynccontextmanager
    async def sessions(self):
        engine = create_async_engine(self.database_url)
        try:
            yield async_sessionmaker(engine, expire_on_commit=False)
        finally:
            await engine.dispose()

    def service(self, session, settings, workspace_id):
        return RepairService(RepairRepository(session), self.media, workspace_id, settings=settings)

    async def enqueue(self, key="render-once"):
        async with self.sessions() as factory, factory() as session:
            response = await kie_workflow.enqueue_kie_render(
                session, self.settings, self.workspace_id, render_input(), key
            )
            row = await RepairRepository(session).project(
                self.workspace_id, UUID(response["repairProjectId"]), lock=True
            )
            if not row.context_json.get("p0"):
                await seed_owned_intake_context(self, session, row, self.client.clips[0])
            else:
                await session.commit()
            return response

    async def job(self, job_id):
        async with self.sessions() as factory, factory() as session:
            return await session.get(ProcessingJobModel, UUID(str(job_id)))

    async def project(self, project_id):
        async with self.sessions() as factory, factory() as session:
            return await RepairRepository(session).project(self.workspace_id, UUID(str(project_id)))

    def run_job(self, job):
        return kie_worker.execute_kie_job(job, self.settings, lambda: None)


def render_input():
    scenes = [
        {
            "displayOrder": index,
            "chainType": "ROOT",
            "parentSceneId": None,
            "characterNames": ["Product"],
            "prompt": f"Scene {index + 1}",
            "imagePrompt": "The exact product on a clean desk",
            "videoPrompt": f"Show product angle {index + 1}",
        }
        for index in range(2)
    ]
    return RenderSmartRemakeInput(
        productLock=seller_product_lock(),
        sceneMap={
            "scenes": scenes,
            "targetDuration": 16,
            "sceneCount": 2,
            "aspectRatio": "9:16",
        },
        referenceAnalysis={"audioPlan": {"mode": "silent"}},
        productImage=UploadedMedia(bytes=seller_product_png(), mime_type="image/png"),
        projectName="Seller product video",
        provider="kie",
        audioRequired=False,
    )


def seller_product_png():
    output = BytesIO()
    Image.new("RGB", (90, 160), "white").save(output, "PNG")
    return output.getvalue()


def seller_product_lock():
    return {
        "productName": "Synthetic seller product",
        "productType": "rectangular product",
        "productReference": {"characterName": "Product"},
        "visualIdentity": {"colors": ["white"], "shape": "rectangular", "texture": "smooth"},
        "mustPreserve": ["white color", "rectangular outline"],
    }


def intake_request(harness, *, key, duration):
    declaration = {
        "basis": "owned",
        "declared": True,
        "scope": "Analysis, AI generation, inspection and export of this synthetic test case.",
        "evidenceNote": "Self-authored FFmpeg/Pillow fixture; no real person or third-party media.",
    }
    return SmartRemakeIntakeRequest.model_validate(
        {
            "idempotencyKey": key,
            "projectName": "Owned offline integration fixture",
            "targetDuration": duration,
            "requirements": {"intent": "Preserve the exact product"},
            "rights": {
                "source": declaration,
                "product": declaration,
                "providerDisclosureAcknowledged": True,
            },
            "budget": {"capUsd": "50.00", "maxAttempts": 100, "maxDurationSeconds": 3600},
        }
    )


async def seed_owned_intake_context(harness, session, row, source):
    """Represent a saved v1 plan's real private intake before its first provider boundary."""
    payload = intake_request(harness, key=str(row.id), duration=row.state_json["targetDuration"])
    context = copy.deepcopy(row.context_json)
    source_key = await harness.media.put(
        f"workspaces/{harness.workspace_id}/smart-remake/{row.id}/inputs", source, "video/mp4"
    )
    product = await harness.media.read(context["productKey"])
    assets = {
        role: {
            "id": str(uuid4()),
            "role": role,
            "storageKey": key,
            "mediaHash": hashlib.sha256(data).hexdigest(),
            "mimeType": mime,
            "sizeBytes": len(data),
        }
        for role, data, key, mime in (
            ("source", source, source_key, "video/mp4"),
            ("product", product, context["productKey"], "image/png"),
        )
    }
    hashes = {role: asset["mediaHash"] for role, asset in assets.items()}
    context["p0"] = {
        "schemaVersion": 1,
        "phase": "plan",
        "actorId": str(harness.actor_id),
        "inputHash": stable_hash(hashes),
        "intakeRequestHash": stable_hash(payload.model_dump()),
        "targetDuration": row.state_json["targetDuration"],
        "assets": assets,
        "requirements": payload.requirements.model_dump(),
        "rights": rights_snapshot(payload.rights, actor_id=harness.actor_id),
        "budgetPolicy": payload.budget.model_dump(),
    }
    for role, asset in assets.items():
        context.update(
            {
                f"{role}Key": asset["storageKey"],
                f"{role}MimeType": asset["mimeType"],
                f"{role}MediaHash": asset["mediaHash"],
            }
        )
    from viraldy.modules.smart_remake.timeline_compile import source_opening_bindings
    from viraldy.modules.smart_remake.timeline_media import probe_timeline_media

    source_frames = probe_timeline_media(source)["frameCount"]
    count = len(row.state_json["scenes"])
    units, source_scenes = [], []
    for index, scene in enumerate(row.state_json["scenes"]):
        source_id = f"source-{index}"
        units.append(
            {
                "id": scene["id"],
                "sceneIndex": index,
                "sourceSceneId": source_id,
                "targetDurationFrames": 192,
                "rawDurationFrames": 192,
            }
        )
        source_scenes.append(
            {
                "id": source_id,
                "startFrame": index * source_frames // count,
                "endFrame": (index + 1) * source_frames // count,
            }
        )
    context["renderPlan"] = {"units": units}
    context["sourceSceneMap"] = {"scenes": source_scenes, "sourceFrameCount": source_frames}
    context["sourceOpeningFrames"] = source_opening_bindings(
        UploadedMedia(bytes=source, mime_type="video/mp4"), source_scenes
    )
    context["generationExpectations"] = build_generation_expectations(context)
    context["expectationsHash"] = expectations_hash(context["generationExpectations"])
    context["p0"]["constraintsHash"] = constraints_hash(context)
    row.context_json = context
    await session.commit()


def offline_kie_request(**values):
    from viraldy.modules.smart_remake.engine.kie_adapter import build_kie_video_request

    request = build_kie_video_request(**values)
    index = values["scene"].get("sceneIndex", values["scene"].get("displayOrder", 0))
    request["input"]["prompt"] += f"\nOFFLINE_TEST_SCENE_INDEX={index}"
    return request


def generation_budget_bounds(monkeypatch):
    for stage, ceiling in (("image", "0.50"), ("video", "1.00"), ("inspection", "0.10")):
        monkeypatch.setenv(f"SMART_REMAKE_P0_MAX_{stage.upper()}_USD", ceiling)


@pytest.fixture
def harness(kie_database_url, vertical_clips, monkeypatch):
    fixture = Harness(kie_database_url)
    fixture.client = FakeKieClient(fixture, vertical_clips)
    monkeypatch.setenv("KIE_API_KEY", "offline-integration-key")
    generation_budget_bounds(monkeypatch)

    async def seed():
        async with fixture.sessions() as factory, factory() as session:
            user_id = uuid4()
            fixture.actor_id = user_id
            session.add(
                UserModel(
                    id=user_id, external_auth_id=str(user_id), email=f"{user_id}@example.test"
                )
            )
            await session.flush()
            for workspace_id in (fixture.workspace_id, fixture.foreign_workspace_id):
                session.add(
                    WorkspaceModel(
                        id=workspace_id,
                        name="KIE seller test",
                        slug=str(workspace_id),
                        created_by_user_id=user_id,
                    )
                )
            await session.commit()

    async def dispatch(session, job_id):
        fixture.dispatched.append(job_id)

    asyncio.run(seed())
    monkeypatch.setattr(kie_workflow, "_dispatch", dispatch)
    monkeypatch.setattr(kie_workflow, "_service", fixture.service)
    monkeypatch.setattr(kie_worker, "_service", fixture.service)
    monkeypatch.setattr(kie_workflow, "KieClient", lambda: fixture.client)
    monkeypatch.setattr(kie_workflow, "build_kie_video_request", offline_kie_request)
    return fixture


def test_concurrent_initial_key_keeps_one_project_and_one_create_per_scene(harness, monkeypatch):
    async def enqueue_concurrently():
        barrier = asyncio.Barrier(2)

        class CoordinatedService(RepairService):
            async def begin_render(self, input_data):
                result = await super().begin_render(input_data)
                await barrier.wait()
                return result

        monkeypatch.setattr(
            kie_workflow,
            "_service",
            lambda session, settings, workspace_id: CoordinatedService(
                RepairRepository(session), harness.media, workspace_id
            ),
        )
        first, second = await asyncio.gather(harness.enqueue(), harness.enqueue())
        assert first["processingJobId"] == second["processingJobId"]
        assert first["repairProjectId"] == second["repairProjectId"]
        async with harness.sessions() as factory, factory() as session:
            for model in (ProcessingJobModel, SmartRemakeProjectModel):
                assert (
                    await session.scalar(
                        select(func.count())
                        .select_from(model)
                        .where(model.workspace_id == harness.workspace_id)
                    )
                    == 1
                )
        return first

    response = asyncio.run(enqueue_concurrently())
    job = asyncio.run(harness.job(response["processingJobId"]))
    assert harness.run_job(job)["status"] == "completed"
    assert harness.run_job(job)["status"] == "completed"
    assert [item["scene_index"] for item in harness.client.creates] == [0, 1]
    row = asyncio.run(harness.project(response["repairProjectId"]))
    assert row.state_json["status"] == "ready"
    assert row.state_json["assemblyCheck"]["status"] == "passed"
    assert all(len(scene["versions"]) == 1 for scene in row.state_json["scenes"])


def test_worker_restart_retrieves_known_task_without_resubmitting(harness):
    response = asyncio.run(harness.enqueue())
    job = asyncio.run(harness.job(response["processingJobId"]))
    harness.client.fail_download = True
    with pytest.raises(RuntimeError, match="without a new generation"):
        harness.run_job(job)

    async def pending():
        async with harness.sessions() as factory, factory() as session:
            operation = await session.get(
                SmartRemakeOperationModel, UUID(job.input_json["operation_id"])
            )
            assert operation.status == "running"
            assert operation.result_json["tasks"]["0"]["taskId"] == "task-1"
            assert operation.result_json["needsReconciliation"] is True

    asyncio.run(pending())
    harness.client.fail_download = False
    assert harness.run_job(job)["status"] == "completed"
    assert harness.client.polls == ["task-1", "task-1", "task-2"]
    assert len(harness.client.creates) == 2


def test_scene_two_repair_requires_accept_and_preserves_scene_one_hash(harness):
    response = asyncio.run(harness.enqueue())
    initial_job = asyncio.run(harness.job(response["processingJobId"]))
    harness.run_job(initial_job)
    before = asyncio.run(harness.project(response["repairProjectId"]))
    original = copy.deepcopy(before.state_json)
    selected = original["scenes"][1]
    request = RepairSceneRequest(
        baseVersionId=selected["activeVersionId"],
        expectedRevision=1,
        prompt="Show the exact product from the front",
        imagePrompt="The exact product on a clean desk",
        videoPrompt="Move the camera slowly around the exact product",
        idempotencyKey="repair-scene-two",
    )

    async def enqueue_repair():
        async with harness.sessions() as factory, factory() as session:
            result = await kie_workflow.enqueue_kie_repair(
                session,
                harness.settings,
                harness.workspace_id,
                before.id,
                UUID(selected["id"]),
                request,
            )
            repeated = await kie_workflow.enqueue_kie_repair(
                session,
                harness.settings,
                harness.workspace_id,
                before.id,
                UUID(selected["id"]),
                request,
            )
            assert repeated["operationId"] == result["operationId"]
            job = await session.scalar(
                select(ProcessingJobModel).where(
                    ProcessingJobModel.idempotency_key == f"repair:{result['operationId']}"
                )
            )
            return job

    repair_job = asyncio.run(enqueue_repair())
    harness.run_job(repair_job)
    harness.run_job(repair_job)
    candidate_row = asyncio.run(harness.project(before.id))
    state = candidate_row.state_json
    candidate = state["scenes"][1]["versions"][-1]
    assert len(harness.client.creates) == 3
    assert harness.client.creates[-1]["scene_index"] == 1
    assert state["scenes"][0] == original["scenes"][0]
    assert state["finalStorageKey"] == original["finalStorageKey"]
    assert state["scenes"][1]["activeVersionId"] == selected["activeVersionId"]
    assert candidate["id"] != selected["activeVersionId"]
    assert candidate["parentVersionId"] == selected["activeVersionId"]
    assert candidate["usedByRevision"] is None
    assert candidate["technicalCheck"]["status"] == "passed"
    assert state["revision"] == 1

    async def accept():
        async with harness.sessions() as factory, factory() as session:
            return await harness.service(session, harness.settings, harness.workspace_id).accept(
                before.id,
                AcceptSceneVersion(
                    sceneId=selected["id"],
                    versionId=candidate["id"],
                    expectedRevision=1,
                    idempotencyKey="accept-scene-two",
                ),
            )

    accepted = asyncio.run(accept())["project"]
    assert accepted["revision"] == 2
    assert accepted["scenes"][1]["activeVersionId"] == candidate["id"]
    untouched = accepted["scenes"][0]["versions"][0]
    original_version = original["scenes"][0]["versions"][0]
    assert untouched["mediaHash"] == original_version["mediaHash"]
    assert (
        hashlib.sha256(harness.media.objects[original_version["storageKey"]]).hexdigest()
        == (original_version["mediaHash"])
    )
    assert accepted["assemblyCheck"]["status"] == "passed"
    assert "storageKey" not in str(accepted)


def test_ambiguous_submission_survives_restart_without_second_paid_create(harness):
    response = asyncio.run(harness.enqueue())
    job = asyncio.run(harness.job(response["processingJobId"]))
    harness.client.fail_submit = True
    for _ in range(2):
        with pytest.raises(AppError) as caught:
            harness.run_job(job)
        assert caught.value.code == "SMART_REMAKE_SUBMISSION_UNRESOLVED"
    assert len(harness.client.creates) == 1
    assert harness.client.polls == []


def test_foreign_workspace_cannot_read_repair_or_execute_project(harness):
    response = asyncio.run(harness.enqueue())
    row = asyncio.run(harness.project(response["repairProjectId"]))
    scene = row.state_json["scenes"][0]

    async def denied():
        async with harness.sessions() as factory, factory() as session:
            foreign = harness.service(session, harness.settings, harness.foreign_workspace_id)
            with pytest.raises(NotFoundError):
                await foreign.get(row.id)
            with pytest.raises(NotFoundError):
                await kie_workflow.enqueue_kie_repair(
                    session,
                    harness.settings,
                    harness.foreign_workspace_id,
                    row.id,
                    UUID(scene["id"]),
                    RepairSceneRequest(
                        expectedRevision=1,
                        prompt="Front view",
                        imagePrompt="Exact product",
                        videoPrompt="Slow camera",
                        idempotencyKey="foreign-repair",
                    ),
                )

    asyncio.run(denied())
    job = asyncio.run(harness.job(response["processingJobId"]))
    job.workspace_id = harness.foreign_workspace_id
    with pytest.raises(NotFoundError):
        harness.run_job(job)
    assert harness.client.creates == []


def test_same_key_with_changed_product_does_not_enqueue_another_job(harness):
    asyncio.run(harness.enqueue())

    async def changed():
        altered = render_input()
        altered.productImage = UploadedMedia(bytes=b"different product", mime_type="image/png")
        async with harness.sessions() as factory, factory() as session:
            with pytest.raises(ConflictError):
                await kie_workflow.enqueue_kie_render(
                    session, harness.settings, harness.workspace_id, altered, "render-once"
                )
            assert (
                await session.scalar(
                    select(func.count())
                    .select_from(ProcessingJobModel)
                    .where(ProcessingJobModel.workspace_id == harness.workspace_id)
                )
                == 1
            )

    asyncio.run(changed())
    assert harness.client.creates == []


def test_execution_guard_survives_commit_and_get_cannot_overwrite_task_manifest(harness):
    response = asyncio.run(harness.enqueue())
    job = asyncio.run(harness.job(response["processingJobId"]))
    operation_id = UUID(job.input_json["operation_id"])

    async def contend():
        # The lease must not occupy this sole ORM pool connection while the
        # worker commits and a second API session reads the same operation.
        engine = create_async_engine(
            harness.database_url, pool_size=1, max_overflow=0, pool_timeout=1
        )
        factory = async_sessionmaker(engine, expire_on_commit=False)
        try:
            async with factory() as worker_session, factory() as api_session:
                worker = RepairRepository(worker_session)
                api = RepairRepository(api_session)
                async with worker.execution_guard(operation_id) as acquired:
                    assert acquired is True
                    operation = await worker.operation(
                        harness.workspace_id, job.subject_id, operation_id
                    )
                    manifest = {
                        **operation.result_json,
                        "tasks": {"0": {"status": "submitted", "taskId": "paid-before-restart"}},
                        "needsReconciliation": True,
                    }
                    await worker.finish(operation, "running", manifest)

                    async with api.execution_guard(operation_id) as other_acquired:
                        assert other_acquired is False
                    service = harness.service(api_session, harness.settings, harness.workspace_id)
                    pending = await service.get(job.subject_id)
                    assert pending["pendingOperation"]["status"] == "running"
                    assert pending["pendingOperation"]["needsReconciliation"] is True
                    with pytest.raises(RuntimeError, match="Another executor"):
                        await kie_workflow.KieWorkflow(service).execute(
                            job.subject_id, operation_id
                        )
                    current = await api.operation(
                        harness.workspace_id, job.subject_id, operation_id
                    )
                    assert current.result_json == manifest
                    await api_session.commit()
                async with api.execution_guard(operation_id) as acquired_after_release:
                    assert acquired_after_release is True
        finally:
            await engine.dispose()

    asyncio.run(asyncio.wait_for(contend(), timeout=10))
    assert harness.client.creates == []
    assert harness.client.polls == []


def test_attach_processing_job_merges_into_latest_terminal_manifest(harness):
    response = asyncio.run(harness.enqueue())
    job = asyncio.run(harness.job(response["processingJobId"]))
    operation_id = UUID(job.input_json["operation_id"])

    async def attach_stale_snapshot():
        async with harness.sessions() as factory:
            async with factory() as stale_session, factory() as worker_session:
                stale = RepairRepository(stale_session)
                worker = RepairRepository(worker_session)
                old_operation = await stale.operation(
                    harness.workspace_id, job.subject_id, operation_id
                )
                assert old_operation.status == "running"
                assert old_operation.result_json["tasks"] == {}
                await stale_session.commit()

                current = await worker.operation(harness.workspace_id, job.subject_id, operation_id)
                completed_manifest = {
                    **current.result_json,
                    "tasks": {
                        "0": {"status": "submitted", "taskId": "paid-first-scene"},
                        "1": {"status": "submitted", "taskId": "paid-second-scene"},
                    },
                    "needsReconciliation": False,
                }
                await worker.finish(current, "completed", completed_manifest)
                # This session still holds the earlier ORM state. Job binding
                # must merge only its own field, never resurrect that snapshot.
                assert old_operation.status == "running"
                await stale.attach_processing_job(old_operation, job.id)
                assert old_operation.status == "completed"
                assert old_operation.result_json == {
                    **completed_manifest,
                    "processingJobId": str(job.id),
                }
                await worker_session.refresh(current)
                assert current.status == "completed"
                assert current.result_json == old_operation.result_json

    asyncio.run(attach_stale_snapshot())
    assert harness.client.creates == []


@pytest.mark.parametrize("has_paid_task", [False, True])
def test_worker_fixture_switch_fails_closed_and_preserves_paid_task(
    harness, monkeypatch, has_paid_task
):
    response = asyncio.run(harness.enqueue())
    job = asyncio.run(harness.job(response["processingJobId"]))
    operation_id = UUID(job.input_json["operation_id"])
    tasks = (
        {"0": {"status": "submitted", "taskId": "already-paid-before-config-change"}}
        if has_paid_task
        else {}
    )

    async def record_task():
        async with harness.sessions() as factory, factory() as session:
            repository = RepairRepository(session)
            operation = await repository.operation(
                harness.workspace_id, job.subject_id, operation_id
            )
            await repository.finish(operation, "running", {**operation.result_json, "tasks": tasks})

    def forbidden_client():
        raise AssertionError("Fixture mode must stop before constructing the KIE client")

    asyncio.run(record_task())
    monkeypatch.setattr(kie_workflow, "KieClient", forbidden_client)
    fixture_settings = SimpleNamespace(database_url=harness.database_url, ai_mode="fixture")
    with pytest.raises(AppError) as caught:
        kie_worker.execute_kie_job(job, fixture_settings, lambda: None)
    assert caught.value.code == "SMART_REMAKE_FIXTURE_MODE"

    async def retained_state():
        async with harness.sessions() as factory, factory() as session:
            repository = RepairRepository(session)
            operation = await repository.operation(
                harness.workspace_id, job.subject_id, operation_id
            )
            assert operation.status == ("running" if has_paid_task else "failed")
            assert operation.result_json["tasks"] == tasks
            assert operation.result_json["needsReconciliation"] is has_paid_task
            assert operation.result_json["errorCode"] == "SMART_REMAKE_FIXTURE_MODE"
            service = RepairService(
                repository, harness.media, harness.workspace_id, settings=fixture_settings
            )
            public = await service.get(job.subject_id)
            visible_operation = public["pendingOperation" if has_paid_task else "lastOperation"]
            assert visible_operation["status"] == operation.status
            assert visible_operation["errorCode"] == "SMART_REMAKE_FIXTURE_MODE"

    asyncio.run(retained_state())
    assert harness.client.creates == []
    assert harness.client.polls == []
