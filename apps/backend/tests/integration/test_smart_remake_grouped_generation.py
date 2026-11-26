"""Offline grouped KIE/image journeys with PostgreSQL and real retained media."""

from __future__ import annotations

import asyncio
import copy
import hashlib
import json
from io import BytesIO
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from PIL import Image
from pydantic import SecretStr
from sqlalchemy import select

from tests.integration.test_smart_remake_kie_workflow import FakeKieClient, generation_budget_bounds
from tests.integration.test_smart_remake_timeline import (
    TimelineHarness,
    probe_frames,
)
from tests.integration.test_smart_remake_timeline import (
    timeline_database_url as _timeline_database_url,
)
from tests.integration.test_smart_remake_timeline import (
    timeline_media as _timeline_media,
)
from viraldy.modules.identity.models import UserModel
from viraldy.modules.jobs.models import ProcessingJobModel
from viraldy.modules.smart_remake import (
    conditioning_inspection,
    kie_worker,
    kie_workflow,
    timeline_worker,
)
from viraldy.modules.smart_remake.budget_models import SmartRemakeAttemptModel
from viraldy.modules.smart_remake.budgeted_analysis import LedgerGeminiClient
from viraldy.modules.smart_remake.engine import openai_images
from viraldy.modules.smart_remake.generation_expectations import (
    build_generation_expectations,
    expectations_hash,
)
from viraldy.modules.smart_remake.models import (
    SmartRemakeOperationModel,
    SmartRemakeProjectModel,
)
from viraldy.modules.smart_remake.repair_repository import RepairRepository
from viraldy.modules.smart_remake.repair_schemas import AcceptSceneVersion, RepairSceneRequest
from viraldy.modules.workspaces.models import WorkspaceModel
from viraldy.shared.errors.base import AppError


@pytest.fixture(scope="module")
def grouped_database_url():
    yield from _timeline_database_url.__wrapped__()


@pytest.fixture(scope="module")
def grouped_media(tmp_path_factory):
    return _timeline_media.__wrapped__(tmp_path_factory)


def png(color, size=(720, 1280)):
    output = BytesIO()
    Image.new("RGB", size, color).save(output, "PNG")
    return output.getvalue()


class GroupedHarness(TimelineHarness):
    @property
    def settings(self):
        return SimpleNamespace(
            database_url=self.database_url,
            ai_mode="live",
            openai_api_key=SecretStr("offline-integration-openai-key"),
        )

    async def seed_project(self, durations=(3, 5, 4, 4), start_frame=24):
        row = await super().seed_project(durations, start_frame, grouped=True)
        async with self.sessions() as factory, factory() as session:
            repository = RepairRepository(session)
            row = await repository.project(self.workspace_id, row.id, lock=True)
            context, state = copy.deepcopy(row.context_json), copy.deepcopy(row.state_json)
            context["renderPlan"]["groupingPolicy"] = "fixed_provider_windows"
            state["renderPlan"]["groupingPolicy"] = "fixed_provider_windows"
            product = png("white", (90, 160))
            self.media.objects[context["productKey"]] = product
            context["productMediaHash"] = hashlib.sha256(product).hexdigest()
            for index, unit in enumerate(context["renderPlan"]["units"]):
                direction = f"The exact product on a clean desk, opening angle {index + 1}"
                unit["imagePrompt"] = direction
                context["sceneMap"]["scenes"][index].update(
                    imagePrompt=direction,
                    targetDurationFrames=unit["targetDurationFrames"],
                    rawDurationFrames=192,
                )
                state["renderPlan"]["units"][index]["imagePrompt"] = direction
                state["scenes"][index]["imagePrompt"] = direction
            context["generationExpectations"] = build_generation_expectations(context)
            context["expectationsHash"] = expectations_hash(context["generationExpectations"])
            row.context_json, row.state_json = context, state
            await session.commit()
            return row

    async def operation(self, job):
        async with self.sessions() as factory, factory() as session:
            return await session.get(
                SmartRemakeOperationModel, UUID(job.input_json["operation_id"])
            )


class GroupedKieClient(FakeKieClient):
    def __init__(self, harness, clips):
        super().__init__(harness, clips)
        self.uploads, self.downloads = [], []

    async def upload_file(self, media):
        with Image.open(BytesIO(media.bytes)) as image:
            assert image.format == "PNG"
            image.verify()
        self.uploads.append(hashlib.sha256(media.bytes).hexdigest())
        return f"https://8.8.8.8/reference-{len(self.uploads)}.png"

    async def download_file(self, url):
        self.downloads.append(url)
        return await super().download_file(url)


class FakeImageClient:
    def __init__(self, harness):
        self.harness, self.calls = harness, []
        self.fail_submit = False

    async def edit(self, *, prompt, product, layout, model, quality="max", complexity="high"):
        # An independent transaction must observe intent before the paid boundary.
        async with self.harness.sessions() as factory, factory() as session:
            operations = (
                await session.scalars(
                    select(SmartRemakeOperationModel)
                    .join(SmartRemakeProjectModel)
                    .where(SmartRemakeProjectModel.workspace_id == self.harness.workspace_id)
                )
            ).all()
            assert any(
                image.get("status") == "submitting" and image.get("requestHash")
                for operation in operations
                for image in operation.result_json.get("images", {}).values()
            )
            attempts = (
                await session.scalars(
                    select(SmartRemakeAttemptModel).where(
                        SmartRemakeAttemptModel.workspace_id == self.harness.workspace_id,
                        SmartRemakeAttemptModel.stage == "image",
                        SmartRemakeAttemptModel.status == "submitted",
                    )
                )
            ).all()
            assert attempts and all(attempt.estimated_usd > 0 for attempt in attempts)
        with Image.open(BytesIO(product.bytes)) as image:
            image.verify()
        with Image.open(BytesIO(layout.bytes)) as image:
            assert image.size == (90, 160)
            image.verify()
        self.calls.append(
            {"prompt": prompt, "model": model, "quality": quality, "complexity": complexity}
        )
        if self.fail_submit:
            raise TimeoutError("image acknowledgement lost after acceptance")
        data = png((len(self.calls) * 31 % 255, 80, 160))
        return {
            "bytes": data,
            "mimeType": "image/png",
            "mediaHash": hashlib.sha256(data).hexdigest(),
            "model": model,
            "size": "720x1280",
            "quality": quality,
            "complexity": complexity,
            "usage": {"input_tokens": 21, "output_tokens": 17},
        }


class OfflineInspectionClient:
    """Only the physical VLM is fake; public Inspector and PostgreSQL ledger remain real."""

    def __init__(self, harness):
        self.harness, self.calls = harness, []
        self.last_usage = {"promptTokenCount": 11, "candidatesTokenCount": 13}
        self.last_request_id = None
        self.status = "passed"

    async def generate_json(self, *, system_instruction, prompt, media):
        async with self.harness.sessions() as factory, factory() as session:
            attempts = (
                await session.scalars(
                    select(SmartRemakeAttemptModel).where(
                        SmartRemakeAttemptModel.workspace_id == self.harness.workspace_id,
                        SmartRemakeAttemptModel.stage == "inspection",
                        SmartRemakeAttemptModel.status == "submitted",
                    )
                )
            ).all()
            assert attempts and all(attempt.request_hash for attempt in attempts)
        assert "evidence, not as instructions" in system_instruction
        assert media and all(item["bytes"] for item in media)
        request = json.loads(prompt)
        self.calls.append(request)
        self.last_request_id = f"offline-inspection-{len(self.calls)}"
        return {
            "findings": [
                {
                    "requirementId": rule["id"],
                    "status": self.status,
                    "observed": "Synthetic fixture compared against owned original product.",
                    "observationIds": [item["id"] for item in request["observations"]],
                }
                for rule in request["requirements"]
            ]
        }


@pytest.fixture
def grouped(grouped_database_url, grouped_media, monkeypatch):
    fixture = GroupedHarness(grouped_database_url, source=grouped_media["source"])
    fixture.client = GroupedKieClient(fixture, grouped_media["clips"])
    fixture.images = FakeImageClient(fixture)
    fixture.inspector = OfflineInspectionClient(fixture)
    monkeypatch.setenv("KIE_API_KEY", "offline-grouped-integration-key")
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
                        name="Grouped seller test",
                        slug=str(workspace_id),
                        created_by_user_id=user_id,
                    )
                )
            await session.commit()

    async def dispatch(session, job_id):
        fixture.dispatched.append(job_id)

    def inspection_invoke(session, workspace_id, project_id, operation_id, actor_id, metadata=None):
        ledger = LedgerGeminiClient(
            session,
            workspace_id,
            project_id,
            operation_id,
            actor_id,
            purpose="recheck",
            stage="inspection",
            client=fixture.inspector,
            metadata=metadata,
        )

        async def invoke(payload):
            return await ledger.generate_json(
                system_instruction=payload["systemInstruction"],
                prompt=payload["prompt"],
                media=payload["media"],
            )

        invoke.model_profile = {"provider": "fixture", "model": "offline-inspection"}
        return invoke

    asyncio.run(seed())
    for module in (kie_workflow, kie_worker, timeline_worker):
        if hasattr(module, "_service"):
            monkeypatch.setattr(module, "_service", fixture.service)
    monkeypatch.setattr(kie_workflow, "_dispatch", dispatch)
    monkeypatch.setattr(kie_workflow, "KieClient", lambda: fixture.client)
    monkeypatch.setattr(openai_images, "OpenAIImageClient", lambda settings: fixture.images)
    monkeypatch.setattr(conditioning_inspection, "inspection_invoke", inspection_invoke)
    return fixture


def generate(harness, durations=(3, 5, 4, 4)):
    row = asyncio.run(harness.seed_project(durations))
    response = asyncio.run(harness.render(row.id))
    job = asyncio.run(harness.job(response["processingJobId"]))
    assert harness.run_job(job)["status"] == "completed"
    return row.id, asyncio.run(harness.public(row.id)), job


def reviewed_items(project):
    return [
        {name: item[name] for name in ("renderUnitId", "versionId", "inFrame", "outFrame")}
        | {"reviewed": True}
        for item in project["draftTimeline"]["items"]
    ]


@pytest.mark.parametrize(
    "durations,task_count,image_count", [((3, 5, 4, 4), 2, 4), ((2, 2, 2, 2), 1, 2)]
)
def test_grouped_generation_shares_media_and_compose_creates_no_paid_requests(
    grouped, grouped_media, durations, task_count, image_count
):
    project_id, project, job = generate(grouped, durations)
    assert len(grouped.client.creates) == task_count
    assert len(grouped.images.calls) == image_count
    assert len(grouped.client.uploads) == task_count * 3
    assert all(request["model"] == "veo3_lite" for request in grouped.client.creates)
    assert all(len(request["image_urls"]) == 3 for request in grouped.client.creates)
    assert all(request["duration"] == 8 for request in grouped.client.creates)
    assert not grouped.inspector.calls
    assert project["publishedTimeline"] is None and not project.get("finalVideoUrl")
    assert all(not item["reviewed"] for item in project["draftTimeline"]["items"])
    row = asyncio.run(grouped.project(project_id))
    groups = row.state_json["renderPlan"]["groups"]
    assert len(groups) == task_count
    versions = [scene["versions"][0] for scene in row.state_json["scenes"]]
    assert len({version["id"] for version in versions}) == 4
    assert len({version["storageKey"] for version in versions}) == task_count
    assert len({version["mediaHash"] for version in versions}) == task_count
    expected = (
        [(0, 72), (72, 192), (0, 96), (96, 192)]
        if task_count == 2
        else [(0, 48), (48, 96), (96, 144), (144, 192)]
    )
    assert [
        (item["inFrame"], item["outFrame"]) for item in project["draftTimeline"]["items"]
    ] == expected
    for version, bounds in zip(versions, expected, strict=True):
        assert (version["suggestedInFrame"], version["suggestedOutFrame"]) == bounds
        assert version["providerMetadata"]["renderGroupId"] in {group["id"] for group in groups}
        assert (
            hashlib.sha256(grouped.media.objects[version["storageKey"]]).hexdigest()
            == version["mediaHash"]
        )
    assets = row.context_json["imageAssets"]
    assert len(assets) == image_count
    for request_hash, image in assets.items():
        assert image["requestHash"] == request_hash
        assert image["storageKey"].startswith(
            f"workspaces/{grouped.workspace_id}/smart-remake/{project_id}/images/"
        )
        data = grouped.media.objects[image["storageKey"]]
        assert image["mediaHash"] == hashlib.sha256(data).hexdigest()
        assert image["usage"] == {"input_tokens": 21, "output_tokens": 17}
        assert image["model"] == "gpt-image-2.6-sunburst"
        assert image["quality"] == "max"
        assert image["complexity"] == "high"
    operation = asyncio.run(grouped.operation(job))
    assert set(operation.result_json["tasks"]) == {f"group:{group['id']}" for group in groups}
    assert operation.result_json["renderPlan"] == row.context_json["renderPlan"]
    grouped.run_job(job)
    assert len(grouped.client.creates) == task_count and len(grouped.images.calls) == image_count
    saved = asyncio.run(grouped.save(project_id, project["revision"], reviewed_items(project)))
    _, compose = asyncio.run(grouped.publish(project_id, saved["project"]["revision"]))
    grouped.compose(compose)
    grouped.compose(compose)
    assert len(grouped.client.creates) == task_count and len(grouped.images.calls) == image_count
    published = asyncio.run(grouped.project(project_id)).state_json
    output = grouped.media.objects[published["finalStorageKey"]]
    probe = probe_frames(output, grouped_media["root"])
    video = next(stream for stream in probe["streams"] if stream["codec_type"] == "video")
    assert int(video["nb_read_frames"]) == sum(durations) * 24
    assert video["avg_frame_rate"] == "24/1"
    assert float(video["duration"]) == pytest.approx(sum(durations), abs=1 / 24)


def test_scene_only_repair_binds_new_image_to_changed_expectations_and_preserves_siblings(grouped):
    project_id, generated, _ = generate(grouped)
    before = asyncio.run(grouped.project(project_id)).state_json
    selected = before["scenes"][0]

    async def repair():
        async with grouped.sessions() as factory, factory() as session:
            result = await kie_workflow.enqueue_kie_repair(
                session,
                grouped.settings,
                grouped.workspace_id,
                project_id,
                UUID(selected["id"]),
                RepairSceneRequest(
                    baseVersionId=selected["activeVersionId"],
                    expectedRevision=generated["revision"],
                    prompt=selected["prompt"],
                    imagePrompt=selected["imagePrompt"],
                    videoPrompt="Move the camera slowly around the exact product",
                    idempotencyKey="repair-one-logical-scene",
                ),
            )
            return await session.scalar(
                select(ProcessingJobModel).where(
                    ProcessingJobModel.idempotency_key == f"repair:{result['operationId']}"
                )
            )

    job = asyncio.run(repair())
    grouped.run_job(job)
    grouped.run_job(job)
    candidate_state = asyncio.run(grouped.project(project_id)).state_json
    assert len(grouped.client.creates) == 3
    # The edited video direction creates a new frozen contract, so its image is
    # regenerated and checked against that contract rather than reusing old QA.
    assert len(grouped.images.calls) == 5
    assert len(grouped.client.creates[-1]["image_urls"]) == 2
    assert candidate_state["scenes"][1:] == before["scenes"][1:]
    assert candidate_state["draftTimeline"] == before["draftTimeline"]
    candidate = candidate_state["scenes"][0]["versions"][-1]
    assert (
        candidate["providerMetadata"]["expectationsHash"]
        != selected["versions"][0]["providerMetadata"]["expectationsHash"]
    )
    assert candidate["parentVersionId"] == selected["activeVersionId"]
    assert candidate["id"] != selected["activeVersionId"]

    async def accept():
        async with grouped.sessions() as factory, factory() as session:
            return await grouped.service(session, grouped.settings, grouped.workspace_id).accept(
                project_id,
                AcceptSceneVersion(
                    sceneId=selected["id"],
                    versionId=candidate["id"],
                    expectedRevision=generated["revision"],
                    idempotencyKey="accept-repaired-scene",
                ),
            )

    accepted = asyncio.run(accept())["project"]
    first = accepted["draftTimeline"]["items"][0]
    assert first["versionId"] == candidate["id"] and first["reviewed"] is False
    assert (first["inFrame"], first["outFrame"]) == (0, 72)
    assert accepted["draftTimeline"]["items"][1:] == before["draftTimeline"]["items"][1:]
    retained = asyncio.run(grouped.project(project_id)).state_json
    assert retained["scenes"][1:] == before["scenes"][1:]
    assert len(grouped.images.calls) == 5 and len(grouped.client.creates) == 3


def test_unknown_image_submission_stays_pending_without_duplicate_image_or_video(grouped):
    row = asyncio.run(grouped.seed_project())
    response = asyncio.run(grouped.render(row.id))
    job = asyncio.run(grouped.job(response["processingJobId"]))
    grouped.images.fail_submit = True
    for _ in range(2):
        with pytest.raises(AppError) as unresolved:
            grouped.run_job(job)
        assert unresolved.value.code == "OPENAI_IMAGE_SUBMISSION_UNRESOLVED"
    project = asyncio.run(grouped.public(row.id))
    assert len(grouped.images.calls) == 1 and grouped.client.creates == []
    assert project["pendingOperation"]["needsReconciliation"] is True
    assert project["pendingOperation"]["errorCode"] == "OPENAI_IMAGE_SUBMISSION_UNRESOLVED"
    operation = asyncio.run(grouped.operation(job))
    assert operation.status == "running"
    assert operation.result_json["images"]["0"]["status"] == "submitting"
    assert not operation.result_json["tasks"]


def test_unknown_video_submission_does_not_repeat_images_or_video_on_refresh(grouped):
    row = asyncio.run(grouped.seed_project())
    response = asyncio.run(grouped.render(row.id))
    job = asyncio.run(grouped.job(response["processingJobId"]))
    grouped.client.fail_submit = True
    for _ in range(2):
        with pytest.raises(AppError) as unresolved:
            grouped.run_job(job)
        assert unresolved.value.code == "SMART_REMAKE_SUBMISSION_UNRESOLVED"
    asyncio.run(grouped.public(row.id))
    assert len(grouped.images.calls) == 2 and len(grouped.client.creates) == 1
    operation = asyncio.run(grouped.operation(job))
    group_key = f"group:{row.state_json['renderPlan']['groups'][0]['id']}"
    task = operation.result_json["tasks"][group_key]
    assert task["status"] == "submitting" and task["requestHash"]
    assert task["model"] == "veo3_lite" and operation.result_json["needsReconciliation"]


def test_partial_group_bindings_resume_without_losing_reviewed_sibling(grouped):
    project_id, _, job = generate(grouped)
    before = asyncio.run(grouped.project(project_id)).state_json
    original = copy.deepcopy(before["scenes"][0])
    downloads = len(grouped.client.downloads)

    async def partial_old_binding():
        async with grouped.sessions() as factory, factory() as session:
            repository = RepairRepository(session)
            row = await repository.project(grouped.workspace_id, project_id, lock=True)
            state = copy.deepcopy(row.state_json)
            state["scenes"][1].update(versions=[], activeVersionId=None)
            state["draftTimeline"]["items"][0]["reviewed"] = True
            state["draftTimeline"]["items"][1].update(versionId=None, reviewed=False)
            operation = await session.get(
                SmartRemakeOperationModel, UUID(job.input_json["operation_id"])
            )
            operation.status = "running"
            await repository.save(row, state)

    asyncio.run(partial_old_binding())
    grouped.run_job(job)
    replayed = asyncio.run(grouped.project(project_id)).state_json
    assert replayed["scenes"][0] == original
    assert len(replayed["scenes"][1]["versions"]) == 1
    assert (
        replayed["scenes"][1]["versions"][0]["storageKey"] == original["versions"][0]["storageKey"]
    )
    assert replayed["draftTimeline"]["items"][0]["reviewed"] is True
    assert (
        replayed["draftTimeline"]["items"][1]["inFrame"],
        replayed["draftTimeline"]["items"][1]["outFrame"],
    ) == (72, 192)
    assert len(grouped.client.downloads) == downloads + 1
    assert len(grouped.client.creates) == 2 and len(grouped.images.calls) == 4


def test_cache_committed_before_operation_image_receipt_is_reused_after_crash(grouped, monkeypatch):
    row = asyncio.run(grouped.seed_project())
    response = asyncio.run(grouped.render(row.id))
    job = asyncio.run(grouped.job(response["processingJobId"]))
    finish = RepairRepository.finish
    crashed = False

    class WorkerCrash(BaseException):
        pass

    async def crash_after_cache(repository, operation, status, result):
        nonlocal crashed
        if not crashed and any(
            image.get("status") == "completed" for image in result.get("images", {}).values()
        ):
            crashed = True
            raise WorkerCrash()
        await finish(repository, operation, status, result)

    monkeypatch.setattr(RepairRepository, "finish", crash_after_cache)
    with pytest.raises(WorkerCrash):
        grouped.run_job(job)
    cached = asyncio.run(grouped.project(row.id)).context_json["imageAssets"]
    assert len(cached) == len(grouped.images.calls) == 1
    assert grouped.client.creates == []
    operation = asyncio.run(grouped.operation(job))
    assert operation.result_json["images"]["0"]["status"] == "submitting"
    assert grouped.run_job(job)["status"] == "completed"
    assert len(grouped.images.calls) == 4 and len(grouped.client.creates) == 2
    assert len(asyncio.run(grouped.project(row.id)).context_json["imageAssets"]) == 4


def test_identical_request_cache_cannot_use_another_workspaces_private_image(grouped):
    from viraldy.modules.smart_remake.image_workflow import prepare_scene_image

    project_id, _, job = generate(grouped)
    cached = copy.deepcopy(asyncio.run(grouped.project(project_id)).context_json["imageAssets"])
    for record in cached.values():
        original_key = record["storageKey"]
        foreign_key = original_key.replace(
            str(grouped.workspace_id), str(grouped.foreign_workspace_id)
        )
        grouped.media.objects[foreign_key] = grouped.media.objects[original_key]
        record["storageKey"] = foreign_key

    async def inject_foreign_cache():
        async with grouped.sessions() as factory, factory() as session:
            repository = RepairRepository(session)
            row = await repository.project(grouped.workspace_id, project_id)
            await repository.merge_context(row, {"imageAssets": cached})

    asyncio.run(inject_foreign_cache())
    operation = asyncio.run(grouped.operation(job))

    async def reject_foreign_cache():
        async with grouped.sessions() as factory, factory() as session:
            service = grouped.service(session, grouped.settings, grouped.workspace_id)
            row = await service.repository.project(grouped.workspace_id, project_id)

            async def unexpected_save(*args, **kwargs):
                pytest.fail("A foreign cache must fail before a new submission intent")

            # Keep the exact snapshot/request hash: another project now has its
            # own scene identities and would correctly be a cache miss instead.
            await prepare_scene_image(
                repair=service,
                row=row,
                operation=operation,
                index=0,
                compiled_scene=row.context_json["sceneMap"]["scenes"][0],
                image_client=grouped.images,
                save=unexpected_save,
                ensure_active=lambda: None,
            )

    with pytest.raises(AppError) as denied:
        asyncio.run(reject_foreign_cache())
    assert denied.value.code == "SMART_REMAKE_IMAGE_ASSET_INVALID"
    assert len(grouped.images.calls) == 4 and len(grouped.client.creates) == 2


def test_owned_image_cache_hash_is_verified_before_reuse(grouped):
    from viraldy.modules.smart_remake.image_workflow import prepare_scene_image

    project_id, _, job = generate(grouped)
    row = asyncio.run(grouped.project(project_id))
    operation = asyncio.run(grouped.operation(job))
    reference = operation.result_json["images"]["0"]
    grouped.media.objects[reference["storageKey"]] = png("orange")

    async def reject_changed_image():
        async with grouped.sessions() as factory, factory() as session:
            service = grouped.service(session, grouped.settings, grouped.workspace_id)

            async def unexpected_save(*args, **kwargs):
                pytest.fail("A changed retained cache must fail before another submission intent")

            await prepare_scene_image(
                repair=service,
                row=row,
                operation=operation,
                index=0,
                compiled_scene=row.context_json["sceneMap"]["scenes"][0],
                image_client=grouped.images,
                save=unexpected_save,
                ensure_active=lambda: None,
            )

    with pytest.raises(AppError) as changed:
        asyncio.run(reject_changed_image())
    assert changed.value.code == "SMART_REMAKE_IMAGE_ASSET_INVALID"
    assert len(grouped.images.calls) == 4 and len(grouped.client.creates) == 2


async def paid_attempts(harness, project_id):
    async with harness.sessions() as factory, factory() as session:
        return (
            await session.scalars(
                select(SmartRemakeAttemptModel)
                .where(SmartRemakeAttemptModel.project_id == project_id)
                .order_by(SmartRemakeAttemptModel.created_at, SmartRemakeAttemptModel.id)
            )
        ).all()


def test_grouped_real_ledger_records_every_image_inspection_video_and_replays_once(grouped):
    from collections import Counter
    from decimal import Decimal

    project_id, _, job = generate(grouped)
    attempts = asyncio.run(paid_attempts(grouped, project_id))
    assert Counter(attempt.stage for attempt in attempts) == {
        "image": 4,
        "video": 2,
    }
    assert all(attempt.status == "completed" and attempt.actual_usd is None for attempt in attempts)
    assert all(attempt.submitted_at and attempt.completed_at for attempt in attempts)
    assert all(
        attempt.request_hash and attempt.policy_json["capUsd"] == "50.00" for attempt in attempts
    )
    assert all(attempt.provider_task_id for attempt in attempts if attempt.stage == "video")
    assert not any(attempt.stage == "inspection" for attempt in attempts)
    assert sum(attempt.estimated_usd for attempt in attempts) == Decimal("4.00")
    before = [attempt.id for attempt in attempts]
    grouped.run_job(job)
    asyncio.run(grouped.public(project_id))
    assert [attempt.id for attempt in asyncio.run(paid_attempts(grouped, project_id))] == before
    assert len(grouped.images.calls) == 4 and not grouped.inspector.calls
    assert len(grouped.client.creates) == 2


def test_unknown_image_reservation_survives_worker_redelivery_as_nonzero_exposure(grouped):
    from decimal import Decimal

    row = asyncio.run(grouped.seed_project())
    response = asyncio.run(grouped.render(row.id))
    job = asyncio.run(grouped.job(response["processingJobId"]))
    grouped.images.fail_submit = True
    for _ in range(2):
        with pytest.raises(AppError):
            grouped.run_job(job)
    attempts = asyncio.run(paid_attempts(grouped, row.id))
    assert len(attempts) == 1
    assert attempts[0].stage == "image" and attempts[0].status == "unknown"
    assert attempts[0].actual_usd is None and attempts[0].estimated_usd == Decimal("0.50")
    assert len(grouped.images.calls) == 1 and not grouped.client.creates
    assert not grouped.inspector.calls


def test_budget_cap_rejects_image_before_any_physical_provider_call(grouped):
    from viraldy.modules.smart_remake.budget_ledger import initialize_budget

    row = asyncio.run(grouped.seed_project())

    async def reduce_cap():
        async with grouped.sessions() as factory, factory() as session:
            await initialize_budget(
                session,
                grouped.workspace_id,
                row.id,
                {"capUsd": "0.10", "maxAttempts": 10, "maxDurationSeconds": 3600},
            )

    asyncio.run(reduce_cap())
    response = asyncio.run(grouped.render(row.id))
    job = asyncio.run(grouped.job(response["processingJobId"]))
    with pytest.raises(AppError) as rejected:
        grouped.run_job(job)
    assert rejected.value.code == "SMART_REMAKE_BUDGET_EXCEEDED"
    assert not grouped.images.calls and not grouped.client.creates and not grouped.inspector.calls
    assert not asyncio.run(paid_attempts(grouped, row.id))


def test_uncertain_real_conditioning_report_blocks_video_and_does_not_retry_on_delivery(
    grouped, monkeypatch,
):
    row = asyncio.run(grouped.seed_project())
    response = asyncio.run(grouped.render(row.id))
    job = asyncio.run(grouped.job(response["processingJobId"]))
    grouped.inspector.status = "needs_review"
    direct_request = kie_workflow.KieWorkflow._request

    async def retained_legacy_request(workflow, row, operation, index, group):
        request, references = await direct_request(workflow, row, operation, index, group)
        await workflow._save(operation, {
            key: value for key, value in operation.result_json.items()
            if key != "referencePreparation"
        })
        plan = operation.result_json["renderPlan"]
        units = {unit["id"]: unit for unit in plan["units"]}
        indices = [units[identity]["sceneIndex"] for identity in group["renderUnitIds"]]
        await conditioning_inspection.check_conditioning_images(
            workflow.repair, row, operation, references,
            binding={
                "renderGroupId": group["id"], "sceneIndices": indices,
                "imageSceneIndices": [indices[0], indices[-1]],
                "referencePolicy": plan.get("referencePolicy"),
                "expectations": operation.result_json["generationExpectations"],
                "expectationsHash": operation.result_json["expectationsHash"],
            },
        )
        return request, references

    # Preserve an actual legacy report and cached images before a fresh direct intent.
    with monkeypatch.context() as legacy:
        legacy.setattr(kie_workflow.KieWorkflow, "_request", retained_legacy_request)
        with pytest.raises(AppError) as blocked:
            grouped.run_job(job)
    assert blocked.value.code == "SMART_REMAKE_CONDITIONING_BLOCKED"
    attempts = asyncio.run(paid_attempts(grouped, row.id))
    assert len(grouped.images.calls) == 2 and len(grouped.inspector.calls) == 1
    assert not grouped.client.creates and all(attempt.stage != "video" for attempt in attempts)
    saved = asyncio.run(grouped.project(row.id)).context_json["p0"]
    report = saved["inspections"]["reports"][0]
    assert report["stage"] == "conditioning" and report["status"] == "needs_review"
    assert report["findings"] and report["observations"]
    assert grouped.run_job(job)["status"] == "failed"
    assert [attempt.id for attempt in asyncio.run(paid_attempts(grouped, row.id))] == [
        attempt.id for attempt in attempts
    ]
    assert len(grouped.images.calls) == 2 and len(grouped.inspector.calls) == 1
    assert not grouped.client.creates
    current = asyncio.run(grouped.project(row.id))
    fresh = asyncio.run(
        grouped.render(row.id, revision=current.revision, key="direct-after-legacy")
    )
    fresh_job = asyncio.run(grouped.job(fresh["processingJobId"]))
    assert grouped.run_job(fresh_job)["status"] == "completed"
    fresh_operation = asyncio.run(grouped.operation(fresh_job))
    assert fresh_operation.result_json["referencePreparation"] == "direct"
    assert len(grouped.images.calls) == 4 and len(grouped.client.creates) == 2
    assert len(grouped.inspector.calls) == 1
    after = asyncio.run(paid_attempts(grouped, row.id))
    assert len([attempt for attempt in after if attempt.stage == "inspection"]) == 1
    assert all(attempt.id in {value.id for value in after} for attempt in attempts)
    history = asyncio.run(grouped.project(row.id)).context_json["p0"]["inspections"]["reports"]
    assert history == saved["inspections"]["reports"]
    grouped.run_job(fresh_job)
    assert len(grouped.images.calls) == 4 and len(grouped.client.creates) == 2
    assert len(grouped.inspector.calls) == 1
