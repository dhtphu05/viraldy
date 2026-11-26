"""Offline Timeline v2 journeys with migrated PostgreSQL and real video media."""

from __future__ import annotations

import asyncio
import copy
import hashlib
import json
import math
import struct
import subprocess
from dataclasses import dataclass, field
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from tests.integration.test_smart_remake_kie_workflow import (
    FakeKieClient,
    Harness,
    generation_budget_bounds,
    intake_request,
    offline_kie_request,
    seller_product_lock,
    seller_product_png,
)
from tests.integration.test_smart_remake_kie_workflow import (
    kie_database_url as _kie_database_url,
)
from viraldy.modules.identity.models import UserModel
from viraldy.modules.jobs.models import ProcessingJobModel
from viraldy.modules.smart_remake import kie_worker, kie_workflow
from viraldy.modules.smart_remake.engine.media_binaries import ffmpeg_path, ffprobe_path
from viraldy.modules.smart_remake.engine.media_probe import probe_media_bytes
from viraldy.modules.smart_remake.engine.schemas import UploadedMedia
from viraldy.modules.smart_remake.models import SmartRemakeOperationModel
from viraldy.modules.smart_remake.repair_repository import RepairRepository
from viraldy.modules.smart_remake.repair_schemas import AcceptSceneVersion, RepairSceneRequest
from viraldy.modules.smart_remake.repair_service import RepairService, _request_hash
from viraldy.modules.workspaces.models import WorkspaceModel
from viraldy.shared.errors.base import AppError, ConflictError, NotFoundError


@pytest.fixture(scope="module")
def timeline_database_url():
    yield from _kie_database_url.__wrapped__()


@pytest.fixture(scope="module")
def timeline_media(tmp_path_factory):
    root = tmp_path_factory.mktemp("timeline-real-clips")
    clips = []
    for index, color in enumerate(("red", "blue", "green", "yellow")):
        target = root / f"clip-{index}.mp4"
        subprocess.run(  # noqa: S603 - fixed argv and test-owned media paths
            [
                ffmpeg_path(),
                "-y",
                "-f",
                "lavfi",
                "-i",
                "color=c=black:s=90x160:r=24:d=8",
                "-f",
                "lavfi",
                "-i",
                f"sine=frequency={440 + index * 110}:r=48000:d=8",
                "-vf",
                f"drawbox=color={color}:t=fill:enable='gte(t,4)'",
                "-af",
                "volume=0:enable='lt(t,4)'",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-shortest",
                str(target),
            ],
            check=True,
            capture_output=True,
            timeout=30,
        )
        clips.append(target.read_bytes())
    source = root / "source.mp4"
    subprocess.run(  # noqa: S603 - fixed argv and test-owned media paths
        [
            ffmpeg_path(),
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=gray:s=90x160:r=24:d=20",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-an",
            str(source),
        ],
        check=True,
        capture_output=True,
        timeout=30,
    )
    return {"clips": clips, "source": source.read_bytes(), "root": root}


@dataclass
class TimelineHarness(Harness):
    source: bytes = b""
    render_revisions: dict = field(default_factory=dict)

    def service(self, session, settings, workspace_id):
        return RepairService(RepairRepository(session), self.media, workspace_id, settings=settings)

    async def seed_project(self, durations=(2, 6), start_frame=24, *, grouped=False):
        from viraldy.modules.smart_remake.project_intake import create_intake
        from viraldy.modules.smart_remake.timeline_compile import initialize_timeline_project
        from viraldy.modules.smart_remake.timeline_planner import build_timeline_plan

        boundaries = [0]
        for duration in durations:
            boundaries.append(boundaries[-1] + duration * 24)
        plan = build_timeline_plan(
            target_duration=sum(durations),
            source_frame_count=480,
            reference_start_frame=start_frame,
            cut_frames=boundaries,
        )
        if not grouped:
            # Saved Timeline v2 plans without groups retain their per-scene workflow.
            for field in (
                "groups",
                "renderGroupBreaks",
                "videoModel",
                "imageModel",
                "imageQuality",
                "imageComplexity",
                "imageSize",
            ):
                plan["renderPlan"].pop(field, None)
        scenes = []
        for index, unit in enumerate(plan["renderPlan"]["units"]):
            prompts = {
                "prompt": f"Scene {index + 1}: show the exact seller product",
                "imagePrompt": "The exact product on a clean desk",
                "videoPrompt": f"Show product angle {index + 1}",
            }
            unit.update(prompts)
            scenes.append({"displayOrder": index, "chainType": "ROOT", **prompts})
        compiled = {
            "success": True,
            "schemaVersion": 2,
            "productLock": seller_product_lock(),
            "referenceAnalysis": {"audioPlan": {"mode": "silent"}},
            "sceneMap": {
                "schemaVersion": 2,
                "scenes": scenes,
                "targetDuration": sum(durations),
                "sceneCount": len(scenes),
                "aspectRatio": "9:16",
            },
            **plan,
        }
        async with self.sessions() as factory, factory() as session:
            intake = await create_intake(
                RepairRepository(session),
                self.media,
                self.workspace_id,
                self.actor_id,
                intake_request(self, key=str(uuid4()), duration=sum(durations)),
                UploadedMedia(bytes=self.source, mime_type="video/mp4"),
                UploadedMedia(bytes=seller_product_png(), mime_type="image/png"),
            )
            row = await initialize_timeline_project(
                repository=RepairRepository(session),
                media=self.media,
                workspace_id=self.workspace_id,
                compile_result=compiled,
                source=UploadedMedia(bytes=self.source, mime_type="video/mp4"),
                product=UploadedMedia(bytes=seller_product_png(), mime_type="image/png"),
                source_probe=probe_media_bytes(self.source),
                existing_project=intake,
            )
            return row

    async def seed_historical_render(self, project_id, key="timeline-render"):
        """Model a submitted legacy operation; fresh legacy plans require an update."""
        async with self.sessions() as factory, factory() as session:
            repository = RepairRepository(session)
            row = await repository.project(self.workspace_id, UUID(str(project_id)))
            revision = row.revision
            self.render_revisions[(str(project_id), key)] = revision
            _, operation, created = await repository.start(
                self.workspace_id, row.id, key,
                _request_hash("render", row.id, {
                    "revision": revision,
                    "prompts": None,
                    "projectName": None,
                    "audioRequired": None,
                    "actorId": str(self.actor_id),
                }),
            )
            assert created
            row.state_json = {
                **copy.deepcopy(row.state_json), "status": "incomplete", "revision": revision + 1
            }
            row.revision = revision + 1
            plan = copy.deepcopy(row.context_json["renderPlan"])
            await repository.finish(operation, "running", {
                "kind": "render",
                "actorId": str(self.actor_id),
                "tasks": {},
                "renderPlan": plan,
                "renderPlanHash": kie_workflow._fingerprint(plan),
                "generationExpectations": copy.deepcopy(row.context_json["generationExpectations"]),
                "expectationsHash": row.context_json["expectationsHash"],
            })

    async def render(self, project_id, revision=None, key="timeline-render"):
        from viraldy.modules.smart_remake.timeline_service import enqueue_timeline_render

        async with self.sessions() as factory, factory() as session:
            if revision is None:
                row = await RepairRepository(session).project(
                    self.workspace_id, UUID(str(project_id))
                )
                revision = self.render_revisions.setdefault((str(project_id), key), row.revision)
            return await enqueue_timeline_render(
                session,
                self.settings,
                self.workspace_id,
                UUID(str(project_id)),
                revision,
                key,
                actor_id=self.actor_id,
            )

    async def public(self, project_id, workspace_id=None):
        async with self.sessions() as factory, factory() as session:
            return await self.service(
                session, self.settings, workspace_id or self.workspace_id
            ).get(UUID(str(project_id)))

    async def save(self, project_id, revision, items, key=None, workspace_id=None):
        from viraldy.modules.smart_remake.repair_schemas import SaveTimelineRequest
        from viraldy.modules.smart_remake.timeline_service import save_timeline

        async with self.sessions() as factory, factory() as session:
            return await save_timeline(
                self.service(session, self.settings, workspace_id or self.workspace_id),
                UUID(str(project_id)),
                SaveTimelineRequest(
                    expectedRevision=revision, idempotencyKey=key or str(uuid4()), items=items
                ),
            )

    async def publish(self, project_id, revision, key=None, workspace_id=None):
        from viraldy.modules.smart_remake.repair_schemas import PublishTimelineRequest
        from viraldy.modules.smart_remake.timeline_service import enqueue_publish

        async with self.sessions() as factory, factory() as session:
            result = await enqueue_publish(
                session,
                self.settings,
                workspace_id or self.workspace_id,
                UUID(str(project_id)),
                PublishTimelineRequest(
                    expectedRevision=revision, idempotencyKey=key or str(uuid4())
                ),
                actor_id=self.actor_id,
            )
            operation = await session.get(SmartRemakeOperationModel, UUID(result["operationId"]))
            job = await session.get(
                ProcessingJobModel, UUID(operation.result_json["processingJobId"])
            )
            return result, job

    def compose(self, job):
        from viraldy.modules.smart_remake.timeline_worker import execute_compose_job

        return execute_compose_job(job, self.settings, lambda: None)


def approved_items(project, starts=None):
    starts = starts or [0] * len(project["draftTimeline"]["items"])
    return [
        {
            "renderUnitId": item["renderUnitId"],
            "versionId": item["versionId"],
            "inFrame": start,
            "outFrame": start + item["targetDurationFrames"],
            "reviewed": True,
        }
        for item, start in zip(project["draftTimeline"]["items"], starts, strict=True)
    ]


@pytest.fixture
def timeline_harness(timeline_database_url, timeline_media, monkeypatch):
    from viraldy.modules.smart_remake import timeline_service, timeline_worker

    fixture = TimelineHarness(timeline_database_url, source=timeline_media["source"])
    fixture.client = FakeKieClient(fixture, timeline_media["clips"])
    monkeypatch.setenv("KIE_API_KEY", "offline-timeline-test-key")
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
                        name="Timeline seller test",
                        slug=str(workspace_id),
                        created_by_user_id=user_id,
                    )
                )
            await session.commit()

    async def dispatch(session, job_id):
        fixture.dispatched.append(job_id)

    asyncio.run(seed())
    for module in (kie_workflow, kie_worker, timeline_service, timeline_worker):
        if hasattr(module, "_service"):
            monkeypatch.setattr(module, "_service", fixture.service)
        if hasattr(module, "_dispatch"):
            monkeypatch.setattr(module, "_dispatch", dispatch)
    monkeypatch.setattr(kie_workflow, "KieClient", lambda: fixture.client)
    monkeypatch.setattr(kie_workflow, "build_kie_video_request", offline_kie_request)
    return fixture


def generated_project(harness, durations=(2, 6)):
    row = asyncio.run(harness.seed_project(durations))
    asyncio.run(harness.seed_historical_render(row.id))
    response = asyncio.run(harness.render(row.id))
    job = asyncio.run(harness.job(response["processingJobId"]))
    assert harness.run_job(job)["status"] == "completed"
    return row.id, asyncio.run(harness.public(row.id)), job


def probe_frames(data, root):
    target = root / f"output-{uuid4()}.mp4"
    target.write_bytes(data)
    result = subprocess.run(  # noqa: S603 - fixed argv and test-owned media path
        [
            ffprobe_path(),
            "-v",
            "error",
            "-count_frames",
            "-show_streams",
            "-show_format",
            "-of",
            "json",
            str(target),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return json.loads(result.stdout)


def sample_video_and_audio(data, root, second):
    target = root / f"sample-{uuid4()}.mp4"
    target.write_bytes(data)
    rgb = subprocess.run(  # noqa: S603 - fixed argv and test-owned media paths
        [
            ffmpeg_path(),
            "-v",
            "error",
            "-ss",
            str(second),
            "-i",
            str(target),
            "-frames:v",
            "1",
            "-vf",
            "scale=1:1",
            "-pix_fmt",
            "rgb24",
            "-f",
            "rawvideo",
            "pipe:1",
        ],
        check=True,
        capture_output=True,
        timeout=30,
    ).stdout
    pcm = subprocess.run(  # noqa: S603 - fixed argv and test-owned media paths
        [
            ffmpeg_path(),
            "-v",
            "error",
            "-ss",
            str(second),
            "-i",
            str(target),
            "-t",
            "0.25",
            "-vn",
            "-ac",
            "1",
            "-ar",
            "48000",
            "-f",
            "f32le",
            "pipe:1",
        ],
        check=True,
        capture_output=True,
        timeout=30,
    ).stdout
    samples = [value[0] for value in struct.iter_unpack("<f", pcm)]
    return tuple(rgb), math.sqrt(sum(value * value for value in samples) / len(samples))


@pytest.mark.parametrize(
    "durations,starts", [((2, 6), (120, 24)), ((3, 5, 4, 4), (24, 48, 72, 96))]
)
def test_render_review_publish_exact_frames_without_new_kie_tasks(
    timeline_harness, timeline_media, durations, starts
):
    project_id, generated, initial_job = generated_project(timeline_harness, durations)
    assert len(timeline_harness.client.creates) == len(durations)
    assert all(task["duration"] == 8 for task in timeline_harness.client.creates)
    assert all(task["aspect_ratio"] == "9:16" for task in timeline_harness.client.creates)
    assert generated["schemaVersion"] == 2
    assert generated.get("publishedTimeline") is None
    assert not generated.get("finalVideoUrl")
    assert all(
        item["versionId"] and not item["reviewed"] for item in generated["draftTimeline"]["items"]
    )
    assert timeline_harness.run_job(initial_job)["status"] == "completed"
    assert len(timeline_harness.client.creates) == len(durations)

    with pytest.raises(AppError):
        asyncio.run(timeline_harness.publish(project_id, generated["revision"]))
    saved = asyncio.run(
        timeline_harness.save(
            project_id, generated["revision"], approved_items(generated, starts), "save-all-trims"
        )
    )
    replay = asyncio.run(
        timeline_harness.save(
            project_id, generated["revision"], approved_items(generated, starts), "save-all-trims"
        )
    )
    assert replay["operationId"] == saved["operationId"]
    revision = saved["project"]["revision"]
    published, compose_job = asyncio.run(
        timeline_harness.publish(project_id, revision, "publish-once")
    )
    replay_publish, replay_job = asyncio.run(
        timeline_harness.publish(project_id, revision, "publish-once")
    )
    assert published["operationId"] == replay_publish["operationId"]
    assert replay_job.id == compose_job.id
    assert timeline_harness.compose(compose_job)["status"] == "completed"
    assert timeline_harness.compose(compose_job)["status"] == "completed"
    assert len(timeline_harness.client.creates) == len(durations)
    row = asyncio.run(timeline_harness.project(project_id))
    assert row.state_json["publishedTimeline"] == row.state_json["draftTimeline"]
    assert all(item["reviewed"] for item in row.state_json["publishedTimeline"]["items"])
    data = timeline_harness.media.objects[row.state_json["finalStorageKey"]]
    probe = probe_frames(data, timeline_media["root"])
    video = next(stream for stream in probe["streams"] if stream["codec_type"] == "video")
    audio = next(stream for stream in probe["streams"] if stream["codec_type"] == "audio")
    assert int(video["nb_read_frames"]) == sum(durations) * 24
    assert video["avg_frame_rate"] == "24/1"
    assert int(video["width"]) * 16 == int(video["height"]) * 9
    assert float(video["duration"]) == pytest.approx(sum(durations), abs=1 / 24)
    assert float(audio["duration"]) == pytest.approx(sum(durations), abs=0.08)
    assert abs(float(video["start_time"]) - float(audio["start_time"])) <= 1 / 24
    # Each raw clip is black/silent for four seconds, then colored with a tone.
    # A nonzero trim must move both streams together, rather than keeping the first N seconds.
    second = 0.5 if len(durations) == 2 else 12.5
    rgb, audio_rms = sample_video_and_audio(data, timeline_media["root"], second)
    assert rgb[0] > 200 and rgb[2] < 30
    assert (rgb[1] < 30) if len(durations) == 2 else (rgb[1] > 200)
    assert audio_rms > 0.02
    public = asyncio.run(timeline_harness.public(project_id))
    assert public["finalVideoUrl"] and not public.get("downloadUrl")
    assert "storageKey" not in str(public)


def test_six_scene_legacy_plan_can_review_and_compose_without_resubmitting_kie(
    timeline_harness, timeline_media
):
    durations = (1, 1, 1, 1, 1, 3)
    project_id, generated, initial_job = generated_project(timeline_harness, durations)
    assert len(generated["sourceSceneMap"]["scenes"]) == 6
    assert len(timeline_harness.client.creates) == 6
    saved = asyncio.run(timeline_harness.save(
        project_id, generated["revision"], approved_items(generated), "six-trims"
    ))
    _, compose_job = asyncio.run(timeline_harness.publish(
        project_id, saved["project"]["revision"], "six-compose"
    ))
    assert timeline_harness.compose(compose_job)["status"] == "completed"
    assert timeline_harness.compose(compose_job)["status"] == "completed"
    assert timeline_harness.run_job(initial_job)["status"] == "completed"
    assert len(timeline_harness.client.creates) == 6
    row = asyncio.run(timeline_harness.project(project_id))
    assert len(row.state_json["publishedTimeline"]["items"]) == 6
    data = timeline_harness.media.objects[row.state_json["finalStorageKey"]]
    video = next(
        stream for stream in probe_frames(data, timeline_media["root"])["streams"]
        if stream["codec_type"] == "video"
    )
    assert int(video["nb_read_frames"]) == 192


def test_revision_conflict_foreign_workspace_and_stale_version_are_rejected(timeline_harness):
    project_id, generated, _ = generated_project(timeline_harness)
    items = approved_items(generated)
    saved = asyncio.run(timeline_harness.save(project_id, generated["revision"], items))
    with pytest.raises(ConflictError) as stale:
        asyncio.run(timeline_harness.save(project_id, generated["revision"], items))
    assert stale.value.code == "SMART_REMAKE_REVISION_CONFLICT"
    with pytest.raises(NotFoundError):
        asyncio.run(timeline_harness.public(project_id, timeline_harness.foreign_workspace_id))
    with pytest.raises(NotFoundError):
        asyncio.run(
            timeline_harness.save(
                project_id,
                saved["project"]["revision"],
                items,
                workspace_id=timeline_harness.foreign_workspace_id,
            )
        )
    with pytest.raises(NotFoundError):
        asyncio.run(
            timeline_harness.publish(
                project_id,
                saved["project"]["revision"],
                workspace_id=timeline_harness.foreign_workspace_id,
            )
        )
    items[0] = {**items[0], "versionId": str(uuid4())}
    with pytest.raises(AppError):
        asyncio.run(timeline_harness.save(project_id, saved["project"]["revision"], items))
    current = asyncio.run(timeline_harness.public(project_id))
    assert current["draftTimeline"] == saved["project"]["draftTimeline"]
    assert len(timeline_harness.client.creates) == 2


@pytest.mark.parametrize("in_frame,out_frame", [(-1, 47), (145, 193), (0, 47)])
def test_trim_outside_real_clip_or_fixed_target_is_rejected(timeline_harness, in_frame, out_frame):
    project_id, generated, _ = generated_project(timeline_harness)
    item = {**approved_items(generated)[0], "inFrame": in_frame, "outFrame": out_frame}
    with pytest.raises((AppError, ValueError)):
        asyncio.run(timeline_harness.save(project_id, generated["revision"], [item]))
    current = asyncio.run(timeline_harness.public(project_id))
    assert current["draftTimeline"] == generated["draftTimeline"]
    assert len(timeline_harness.client.creates) == 2


def test_compose_failure_keeps_published_video_and_reviewed_draft(timeline_harness, monkeypatch):
    from viraldy.modules.smart_remake import timeline_service

    project_id, generated, _ = generated_project(timeline_harness)
    saved = asyncio.run(
        timeline_harness.save(project_id, generated["revision"], approved_items(generated))
    )
    _, first_job = asyncio.run(timeline_harness.publish(project_id, saved["project"]["revision"]))
    timeline_harness.compose(first_job)
    original = asyncio.run(timeline_harness.project(project_id)).state_json
    saved = asyncio.run(
        timeline_harness.save(project_id, original["revision"], approved_items(original, [24, 24]))
    )
    _, failed_job = asyncio.run(timeline_harness.publish(project_id, saved["project"]["revision"]))

    async def fail_compose(*args, **kwargs):
        raise RuntimeError("local FFmpeg compose failed")

    monkeypatch.setattr(timeline_service, "compose_timeline", fail_compose)
    with pytest.raises(RuntimeError, match="compose failed"):
        timeline_harness.compose(failed_job)
    failed = asyncio.run(timeline_harness.project(project_id)).state_json
    assert failed["finalStorageKey"] == original["finalStorageKey"]
    assert failed["publishedTimeline"] == original["publishedTimeline"]
    assert failed["draftTimeline"] == saved["project"]["draftTimeline"]
    assert all(item["reviewed"] for item in failed["draftTimeline"]["items"])
    assert len(timeline_harness.client.creates) == 2


def test_worker_restart_reuses_known_render_tasks_and_preserves_review_requirement(
    timeline_harness,
):
    row = asyncio.run(timeline_harness.seed_project((3, 5, 4, 4)))
    asyncio.run(timeline_harness.seed_historical_render(row.id))
    response = asyncio.run(timeline_harness.render(row.id))
    replay = asyncio.run(timeline_harness.render(row.id))
    assert replay["processingJobId"] == response["processingJobId"]
    job = asyncio.run(timeline_harness.job(response["processingJobId"]))
    timeline_harness.client.fail_download = True
    with pytest.raises(RuntimeError, match="without a new generation"):
        timeline_harness.run_job(job)
    assert len(timeline_harness.client.creates) == 1
    timeline_harness.client.fail_download = False
    timeline_harness.run_job(job)
    timeline_harness.run_job(job)
    assert len(timeline_harness.client.creates) == 4
    assert timeline_harness.client.polls[:2] == ["task-1", "task-1"]
    generated = asyncio.run(timeline_harness.public(row.id))
    assert not generated.get("finalVideoUrl")
    assert all(not item["reviewed"] for item in generated["draftTimeline"]["items"])
    assert all(len(scene["versions"]) == 1 for scene in generated["scenes"])


def test_accept_repair_updates_draft_only_and_requires_new_trim_review(timeline_harness):
    project_id, generated, _ = generated_project(timeline_harness)
    saved = asyncio.run(
        timeline_harness.save(project_id, generated["revision"], approved_items(generated))
    )
    _, publish_job = asyncio.run(timeline_harness.publish(project_id, saved["project"]["revision"]))
    timeline_harness.compose(publish_job)
    original = asyncio.run(timeline_harness.project(project_id)).state_json
    selected = original["scenes"][0]

    async def repair():
        async with timeline_harness.sessions() as factory, factory() as session:
            result = await kie_workflow.enqueue_kie_repair(
                session,
                timeline_harness.settings,
                timeline_harness.workspace_id,
                project_id,
                UUID(selected["id"]),
                RepairSceneRequest(
                    baseVersionId=selected["activeVersionId"],
                    expectedRevision=original["revision"],
                    prompt="Show the exact product from the front",
                    imagePrompt="The exact product on a clean desk",
                    videoPrompt="Move the camera slowly around the exact product",
                    idempotencyKey="new-candidate",
                ),
            )
            return await session.scalar(
                select(ProcessingJobModel).where(
                    ProcessingJobModel.idempotency_key == f"repair:{result['operationId']}"
                )
            )

    job = asyncio.run(repair())
    timeline_harness.run_job(job)
    candidate_state = asyncio.run(timeline_harness.project(project_id)).state_json
    candidate = candidate_state["scenes"][0]["versions"][-1]
    assert candidate_state["publishedTimeline"] == original["publishedTimeline"]
    assert candidate_state["draftTimeline"] == original["draftTimeline"]
    candidate_selection = approved_items(candidate_state)
    candidate_selection[0]["versionId"] = candidate["id"]
    with pytest.raises(AppError) as not_accepted:
        asyncio.run(timeline_harness.save(project_id, original["revision"], candidate_selection))
    assert not_accepted.value.code == "SMART_REMAKE_CANDIDATE_NOT_ACCEPTED"

    async def accept():
        async with timeline_harness.sessions() as factory, factory() as session:
            return await timeline_harness.service(
                session, timeline_harness.settings, timeline_harness.workspace_id
            ).accept(
                project_id,
                AcceptSceneVersion(
                    sceneId=selected["id"],
                    versionId=candidate["id"],
                    expectedRevision=original["revision"],
                    idempotencyKey="accept-new-candidate",
                ),
            )

    accepted = asyncio.run(accept())["project"]
    assert accepted["draftTimeline"]["items"][0]["versionId"] == candidate["id"]
    assert accepted["draftTimeline"]["items"][0]["reviewed"] is False
    assert accepted["publishedTimeline"] == original["publishedTimeline"]
    with pytest.raises(AppError):
        asyncio.run(
            timeline_harness.save(project_id, accepted["revision"], approved_items(original))
        )
    retained = asyncio.run(timeline_harness.project(project_id)).state_json
    assert retained["finalStorageKey"] == original["finalStorageKey"]
    assert retained["scenes"][1] == original["scenes"][1]
    assert len(timeline_harness.client.creates) == 3
    source_version = original["scenes"][0]["versions"][0]
    assert (
        hashlib.sha256(timeline_harness.media.objects[source_version["storageKey"]]).hexdigest()
        == source_version["mediaHash"]
    )


def test_two_tabs_saving_same_revision_has_one_winner(timeline_harness):
    project_id, generated, _ = generated_project(timeline_harness)

    async def save_concurrently():
        return await asyncio.gather(
            timeline_harness.save(
                project_id, generated["revision"], approved_items(generated, [0, 0])
            ),
            timeline_harness.save(
                project_id, generated["revision"], approved_items(generated, [24, 24])
            ),
            return_exceptions=True,
        )

    results = asyncio.run(save_concurrently())
    completed = [result for result in results if isinstance(result, dict)]
    conflicts = [result for result in results if isinstance(result, ConflictError)]
    assert len(completed) == len(conflicts) == 1
    assert conflicts[0].code in {"SMART_REMAKE_REVISION_CONFLICT", "SMART_REMAKE_OPERATION_BUSY"}
    current = asyncio.run(timeline_harness.public(project_id))
    assert current["revision"] == generated["revision"] + 1
    assert current["draftTimeline"] == completed[0]["project"]["draftTimeline"]


def test_concurrent_render_replay_queues_one_job_for_saved_project(timeline_harness):
    row = asyncio.run(timeline_harness.seed_project((3, 5, 4, 4)))
    asyncio.run(timeline_harness.seed_historical_render(row.id, key="same-render-key"))

    async def render_concurrently():
        return await asyncio.gather(
            timeline_harness.render(row.id, key="same-render-key"),
            timeline_harness.render(row.id, key="same-render-key"),
        )

    first, second = asyncio.run(render_concurrently())
    assert first["processingJobId"] == second["processingJobId"]
    assert first["repairProjectId"] == second["repairProjectId"] == str(row.id)
    job = asyncio.run(timeline_harness.job(first["processingJobId"]))
    timeline_harness.run_job(job)
    timeline_harness.run_job(job)
    assert len(timeline_harness.client.creates) == 4
    assert [task["scene_index"] for task in timeline_harness.client.creates] == [0, 1, 2, 3]


def test_trim_cannot_exceed_actual_191_frame_clip(timeline_harness, timeline_media):
    source = timeline_media["root"] / "short-source.mp4"
    source.write_bytes(timeline_media["clips"][0])
    short = timeline_media["root"] / "short-191.mp4"
    subprocess.run(  # noqa: S603 - fixed argv and test-owned media paths
        [
            ffmpeg_path(),
            "-y",
            "-i",
            str(source),
            "-frames:v",
            "191",
            "-c:v",
            "libx264",
            "-an",
            str(short),
        ],
        check=True,
        capture_output=True,
        timeout=30,
    )
    timeline_harness.client.clips = [short.read_bytes(), *timeline_media["clips"][1:]]
    project_id, generated, _ = generated_project(timeline_harness)
    item = {
        **approved_items(generated)[0],
        "inFrame": 144,
        "outFrame": 192,
    }
    with pytest.raises(AppError):
        asyncio.run(timeline_harness.save(project_id, generated["revision"], [item]))
    assert len(timeline_harness.client.creates) == 2


def test_compile_retains_source_hash_and_independent_scene_render_timeline_ids(
    timeline_database_url, timeline_media
):
    harness = TimelineHarness(timeline_database_url, source=timeline_media["source"])

    async def persist():
        async with harness.sessions() as factory, factory() as session:
            user_id = uuid4()
            harness.actor_id = user_id
            session.add(
                UserModel(
                    id=user_id, external_auth_id=str(user_id), email=f"{user_id}@example.test"
                )
            )
            await session.flush()
            session.add(
                WorkspaceModel(
                    id=harness.workspace_id,
                    name="Compiled timeline",
                    slug=str(harness.workspace_id),
                    created_by_user_id=user_id,
                )
            )
            await session.commit()
        row = await harness.seed_project((3, 5, 4, 4), start_frame=48)
        return await harness.project(row.id)

    row = asyncio.run(persist())
    state, context = row.state_json, row.context_json
    assert state["schemaVersion"] == context["schemaVersion"] == 2
    assert row.revision == state["revision"] == 2
    assert state["status"] == "draft"
    assert context["sourceMediaHash"] == hashlib.sha256(timeline_media["source"]).hexdigest()
    assert harness.media.objects[context["sourceKey"]] == timeline_media["source"]
    assert context["sourceProbe"]["durationSeconds"] == pytest.approx(20, abs=1 / 24)
    sources = state["sourceSceneMap"]["scenes"]
    units = state["renderPlan"]["units"]
    items = state["draftTimeline"]["items"]
    assert state["sourceSceneMap"]["sourceStartFrame"] == 48
    assert [item["startFrame"] for item in sources] == [48, 120, 240, 336]
    assert sources[-1]["endFrame"] == 432
    assert [item["targetDurationFrames"] for item in sources] == [72, 120, 96, 96]
    assert {unit["id"] for unit in units} == {scene["id"] for scene in state["scenes"]}
    assert {unit["sourceSceneId"] for unit in units} == {scene["id"] for scene in sources}
    assert len({item["id"] for item in [*sources, *units, *items]}) == 12
    assert [item["targetStartFrame"] for item in items] == [0, 72, 192, 288]
    assert all(item["rawDurationFrames"] == 192 for item in units)
    assert not state.get("finalVideoUrl") and state["publishedTimeline"] is None


def test_compose_rejects_changed_retained_media_without_kie_submission(timeline_harness):
    project_id, generated, _ = generated_project(timeline_harness)
    saved = asyncio.run(
        timeline_harness.save(project_id, generated["revision"], approved_items(generated))
    )
    _, job = asyncio.run(timeline_harness.publish(project_id, saved["project"]["revision"]))
    before = asyncio.run(timeline_harness.project(project_id)).state_json
    first = before["scenes"][0]["versions"][0]
    timeline_harness.media.objects[first["storageKey"]] = b"different retained media"
    with pytest.raises(AppError) as changed:
        timeline_harness.compose(job)
    assert changed.value.code == "SMART_REMAKE_MEDIA_CHANGED"
    after = asyncio.run(timeline_harness.project(project_id)).state_json
    assert after["draftTimeline"] == before["draftTimeline"]
    assert after["publishedTimeline"] is None and not after.get("finalStorageKey")
    assert len(timeline_harness.client.creates) == 2


def test_inspection_review_cannot_overwrite_rights_revoked_after_start_commit(timeline_harness):
    """Use separate PostgreSQL sessions at the exact review/revocation transaction boundary."""
    import copy

    from viraldy.modules.smart_remake.inspection_service import (
        InspectionReviewRequest,
        InspectionService,
        InspectionSubjectRequest,
        _context_hash,
        _snapshot,
    )
    from viraldy.modules.smart_remake.project_contracts import SmartRemakeRightsPatch
    from viraldy.modules.smart_remake.project_metadata import patch_metadata

    async def exercise():
        row = await timeline_harness.seed_project()
        subject_request = InspectionSubjectRequest(kind="image", imageRole="product")
        snapshot = _snapshot(row, subject_request, timeline_harness.workspace_id)
        report = {
            "id": str(uuid4()),
            "contextHash": _context_hash(snapshot),
            "subjectRequest": subject_request.model_dump(),
            "findings": [
                {
                    "id": "product",
                    "category": "product",
                    "status": "needs_review",
                    "blocking": True,
                    "hardBlocking": False,
                }
            ],
        }
        async with timeline_harness.sessions() as factory, factory() as session:
            current = await RepairRepository(session).project(timeline_harness.workspace_id, row.id)
            context = copy.deepcopy(current.context_json)
            context["p0"]["inspections"] = {"reports": [report], "reviews": []}
            current.context_json = context
            await session.commit()
        started, revoked = asyncio.Event(), asyncio.Event()

        class PausingRepository(RepairRepository):
            async def start(self, *args, **kwargs):
                result = await super().start(*args, **kwargs)
                started.set()
                await revoked.wait()
                return result

        async def review():
            async with timeline_harness.sessions() as factory, factory() as session:
                return await InspectionService(
                    PausingRepository(session),
                    timeline_harness.media,
                    timeline_harness.workspace_id,
                ).review(
                    row.id,
                    timeline_harness.actor_id,
                    InspectionReviewRequest(
                        expectedRevision=row.revision,
                        idempotencyKey="review-before-revocation",
                        reportId=report["id"],
                        findingId="product",
                        decision="accept",
                        reason="Check selected product",
                    ),
                )

        review_task = asyncio.create_task(review())
        await asyncio.wait_for(started.wait(), timeout=10)
        try:
            rights = intake_request(timeline_harness, key="revoke", duration=8).rights
            rights.product.revoked = True
            async with timeline_harness.sessions() as factory, factory() as session:
                await patch_metadata(
                    timeline_harness.service(
                        session, timeline_harness.settings, timeline_harness.workspace_id
                    ),
                    row.id,
                    timeline_harness.actor_id,
                    SmartRemakeRightsPatch(
                        expectedRevision=row.revision,
                        idempotencyKey="revoke-product",
                        rights=rights,
                    ),
                    kind="rights",
                )
        finally:
            revoked.set()
        with pytest.raises(ConflictError) as rejected:
            await asyncio.wait_for(review_task, timeout=10)
        assert rejected.value.code == "SMART_REMAKE_REVISION_CONFLICT"
        async with timeline_harness.sessions() as factory, factory() as session:
            current = await RepairRepository(session).project(timeline_harness.workspace_id, row.id)
            assert current.context_json["p0"]["rights"]["product"]["revoked"] is True
            assert current.revision == row.revision + 1
            assert not current.context_json["p0"]["inspections"]["reviews"]
            operation = await session.scalar(
                select(SmartRemakeOperationModel).where(
                    SmartRemakeOperationModel.project_id == row.id,
                    SmartRemakeOperationModel.idempotency_key == "review-before-revocation",
                )
            )
            assert operation.status == "failed"
            assert operation.result_json["errorCode"] == "SMART_REMAKE_REVISION_CONFLICT"

    asyncio.run(exercise())
