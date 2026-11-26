from __future__ import annotations

import copy
import hashlib
import sys
from contextlib import asynccontextmanager
from types import ModuleType, SimpleNamespace
from uuid import uuid4

import pytest

from tests.smart_remake_expectations import install_expectations
from viraldy.modules.smart_remake import kie_workflow, timeline_service
from viraldy.modules.smart_remake.engine import kie_adapter
from viraldy.modules.smart_remake.kie_workflow import KieWorkflow
from viraldy.shared.errors.base import AppError


class Repository:
    def __init__(self, row, op):
        self.row, self.op, self.history = row, op, []

    @asynccontextmanager
    async def execution_guard(self, operation_id):
        yield True

    async def project(self, workspace_id, project_id, **kwargs):
        assert workspace_id == self.row.workspace_id and project_id == self.row.id
        return self.row

    async def operation(self, workspace_id, project_id, operation_id):
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
        return "candidate-video"


class Client:
    def __init__(self, repository):
        self.repository = repository
        self.uploads, self.submits, self.polls = [], [], []
        self.fail_download = self.fail_submit = False
        self.status = "completed"

    async def upload_file(self, media):
        self.uploads.append(media.bytes)
        return f"https://media.test/reference-{len(self.uploads)}.png"

    async def create_task(self, **kwargs):
        intents = self.repository.op.result_json["tasks"]
        assert any(task.get("status") == "submitting" for task in intents.values())
        self.submits.append(kwargs)
        if self.fail_submit:
            raise TimeoutError("lost acknowledgement")
        return {"task_id": f"video-{len(self.submits)}"}

    async def get_task(self, task_id):
        self.polls.append(task_id)
        return {"status": self.status, "output": {"video_url": "https://media.test/video.mp4"}}

    async def download_file(self, url):
        if self.fail_download:
            raise TimeoutError("download unavailable")
        return b"eight-second-video"


@pytest.fixture
def grouped(monkeypatch):
    units = [
        {
            "id": str(uuid4()),
            "sceneIndex": index,
            "targetDurationFrames": length,
            "rawDurationFrames": 192,
            "prompt": f"scene-{index}",
            "imagePrompt": "image",
            "videoPrompt": "motion",
        }
        for index, length in enumerate([72, 120, 96, 96])
    ]
    groups = [
        {
            "id": str(uuid4()),
            "renderUnitIds": [unit["id"] for unit in pair],
            "rawDurationFrames": 192,
            "targetDurationFrames": 192,
            "segments": [
                {
                    "renderUnitId": pair[0]["id"],
                    "inFrame": 0,
                    "outFrame": pair[0]["targetDurationFrames"],
                },
                {
                    "renderUnitId": pair[1]["id"],
                    "inFrame": pair[0]["targetDurationFrames"],
                    "outFrame": 192,
                },
            ],
        }
        for pair in (units[:2], units[2:])
    ]
    row = SimpleNamespace(
        id=uuid4(),
        workspace_id=uuid4(),
        state_json={
            "schemaVersion": 2,
            "status": "rendering",
            "scenes": [
                {**unit, "index": index, "activeVersionId": None, "versions": []}
                for index, unit in enumerate(units)
            ],
        },
        context_json={
            "productKey": "product",
            "productMimeType": "image/png",
            "productLock": {},
            "referenceAnalysis": {},
            "audioRequired": False,
            "sceneMap": {"scenes": units},
            "renderPlan": {
                "units": units,
                "groups": groups,
                "videoModel": "veo3_lite",
                "imageModel": "gpt-image-2.6-flare",
                "imageQuality": "low",
                "imageSize": "720x1280",
            },
        },
    )
    # Positive fresh-work fixture: source/opening extraction is explicitly mocked.
    install_expectations(row.context_json, state=row.state_json)
    op = SimpleNamespace(id=uuid4(), status="running", result_json={"kind": "render", "tasks": {}})
    repo = Repository(row, op)
    repair = SimpleNamespace(
        workspace_id=row.workspace_id,
        repository=repo,
        media=Media(),
        settings=SimpleNamespace(),
        render_project_id=None,
    )
    client = Client(repo)
    images, image_roles, requests, retained = [], [], [], []

    async def prepare_scene_image(**kwargs):
        index = kwargs["index"]
        images.append(index)
        role = kwargs.get("frame_role", "opening")
        image_roles.append(role)
        scene = kwargs["compiled_scene"]
        storage_key = f"image-{index}" + ("-ending" if role == "ending" else "")
        return {
            "storageKey": storage_key,
            "mediaHash": hashlib.sha256(storage_key.encode()).hexdigest(),
            "mimeType": "image/png",
            "model": "gpt-image-2.6-flare",
            "size": "720x1280",
            "quality": "low",
            "usage": {"output_tokens": 8},
            "requestHash": f"image-request-{index}",
            "renderUnitId": scene["renderUnitId"],
            "sourceSceneId": scene["sourceSceneId"],
            "openingFrame": scene["openingFrame"],
            "frameRole": role,
            "expectationsHash": kwargs["operation"].result_json["expectationsHash"],
        }

    async def retain_group(service, project, group, data, metadata):
        retained.append((copy.deepcopy(group), copy.deepcopy(metadata)))
        for unit_id in group["renderUnitIds"]:
            scene = next(scene for scene in row.state_json["scenes"] if scene["id"] == unit_id)
            if not any(
                version["providerMetadata"].get("providerRequestId")
                == metadata["providerRequestId"]
                for version in scene["versions"]
            ):
                scene["versions"].append({"id": str(uuid4()), "providerMetadata": metadata})

    def build_group(**kwargs):
        requests.append(copy.deepcopy(kwargs))
        return {
            "model": "veo-3-1",
            "input": {
                "model": "veo3_lite",
                "generation_type": "FIRST_AND_LAST_FRAMES_2_VIDEO",
                "aspect_ratio": "9:16",
                "duration": 8,
                "resolution": "720p",
                "enable_translation": False,
                "prompt": "timestamped shots",
                "image_urls": kwargs["reference_image_urls"],
            },
        }

    real_adapter = kie_adapter.build_kie_group_request
    helper = ModuleType("viraldy.modules.smart_remake.image_workflow")
    helper.prepare_scene_image = prepare_scene_image
    monkeypatch.setitem(sys.modules, helper.__name__, helper)
    monkeypatch.setattr(timeline_service, "retain_timeline_group_clip", retain_group, raising=False)
    monkeypatch.setattr(kie_adapter, "build_kie_group_request", build_group, raising=False)
    monkeypatch.setattr(kie_workflow, "get_kie_poll_timeout_seconds", lambda: 0)
    return SimpleNamespace(
        runner=KieWorkflow(repair, client=client, image_client=object()),
        repair=repair,
        client=client,
        row=row,
        op=op,
        groups=groups,
        images=images,
        image_roles=image_roles,
        requests=requests,
        retained=retained,
        helper=helper,
        real_adapter=real_adapter,
    )


@pytest.mark.asyncio
async def test_four_logical_scenes_generate_two_paid_groups_and_four_images(grouped):
    value = grouped
    await value.runner.execute(value.row.id, value.op.id)
    assert len(value.client.submits) == 2
    assert value.images == [0, 1, 2, 3]
    assert value.image_roles == ["opening", "ending", "opening", "ending"]
    assert value.client.uploads == [b"image-0", b"image-1-ending", b"image-2", b"image-3-ending"]
    assert [len(request["scenes"]) for request in value.requests] == [2, 2]
    assert all(len(request["reference_image_urls"]) == 2 for request in value.requests)
    assert set(value.op.result_json["tasks"]) == {f"group:{group['id']}" for group in value.groups}
    assert value.op.status == "completed"
    assert all(len(scene["versions"]) == 1 for scene in value.row.state_json["scenes"])
    first_intent = next(
        result
        for result in value.repair.repository.history
        if any(task.get("status") == "submitting" for task in result.get("tasks", {}).values())
    )
    first_task = next(iter(first_intent["tasks"].values()))
    assert first_task["requestHash"] and first_task["model"] == "veo3_lite"
    assert first_task["renderGroupId"] == value.groups[0]["id"]
    assert first_task["group"] == value.groups[0]
    assert [image["usage"] for image in first_task["imageReferences"]] == [{"output_tokens": 8}] * 2


@pytest.mark.asyncio
async def test_expectations_hash_stays_in_receipts_instead_of_video_prompt(grouped):
    value = grouped
    await value.runner.execute(value.row.id, value.op.id)
    expected_hash = value.row.context_json["expectationsHash"]
    assert all(
        expected_hash not in request["input_data"]["prompt"]
        and "GENERATION EXPECTATIONS HASH" not in request["input_data"]["prompt"]
        for request in value.client.submits
    )
    assert all(
        task["expectationsHash"] == expected_hash
        and all(ref["expectationsHash"] == expected_hash for ref in task["imageReferences"])
        for task in value.op.result_json["tasks"].values()
    )


@pytest.mark.asyncio
async def test_singleton_group_generates_opening_and_ending_for_the_same_scene(grouped):
    value = grouped
    value.row.state_json["scenes"] = value.row.state_json["scenes"][:1]
    plan = value.row.context_json["renderPlan"]
    plan["units"] = plan["units"][:1]
    group = {
        **value.groups[0],
        "renderUnitIds": [plan["units"][0]["id"]],
        "targetDurationFrames": 72,
        "segments": [value.groups[0]["segments"][0]],
    }
    plan["groups"] = [group]
    value.row.context_json["sceneMap"]["scenes"] = value.row.context_json["sceneMap"]["scenes"][:1]
    install_expectations(value.row.context_json)
    await value.runner.execute(value.row.id, value.op.id)
    assert value.images == [0, 0]
    assert value.image_roles == ["opening", "ending"]
    assert value.client.uploads == [b"image-0", b"image-0-ending"]
    assert len(value.client.submits) == 1
    assert len(value.requests[0]["reference_image_urls"]) == 2


@pytest.mark.asyncio
async def test_missing_conditioning_model_never_uploads_a_product_packshot_as_a_frame(grouped):
    value = grouped
    value.row.context_json["renderPlan"]["imageModel"] = None
    install_expectations(value.row.context_json)
    with pytest.raises(AppError, match="SMART_REMAKE_CONDITIONING_REQUIRED"):
        await value.runner.execute(value.row.id, value.op.id)
    assert value.images == value.client.uploads == value.client.submits == []


@pytest.mark.asyncio
async def test_four_short_scenes_share_one_task_and_only_first_last_images(grouped):
    value = grouped
    units = value.row.context_json["renderPlan"]["units"]
    for unit in units:
        unit["targetDurationFrames"] = 48
    group = {
        "id": str(uuid4()),
        "renderUnitIds": [unit["id"] for unit in units],
        "rawDurationFrames": 192,
        "targetDurationFrames": 192,
        "segments": [
            {"renderUnitId": unit["id"], "inFrame": index * 48, "outFrame": (index + 1) * 48}
            for index, unit in enumerate(units)
        ],
    }
    value.row.context_json["renderPlan"]["groups"] = [group]
    await value.runner.execute(value.row.id, value.op.id)
    assert len(value.client.submits) == 1
    assert value.images == [0, 3]
    assert len(value.requests[0]["scenes"]) == 4


@pytest.mark.asyncio
async def test_read_only_refresh_does_not_prepare_images_or_submit_missing_group(grouped):
    value = grouped
    await value.runner.execute(value.row.id, value.op.id, reconcile_only=True)
    assert value.images == value.client.uploads == value.client.submits == []
    assert value.op.status == "running"


@pytest.mark.asyncio
async def test_known_group_task_resumes_without_preparing_or_uploading_again(grouped):
    value = grouped
    value.client.fail_download = True
    with pytest.raises(RuntimeError):
        await value.runner.execute(value.row.id, value.op.id)
    assert len(value.client.submits) == 1
    before_images, before_uploads = list(value.images), list(value.client.uploads)
    value.client.fail_download = False
    await value.runner.execute(value.row.id, value.op.id, reconcile_only=True)
    assert len(value.client.submits) == 1
    assert value.images == before_images and value.client.uploads == before_uploads
    assert value.op.status == "running"
    await value.runner.execute(value.row.id, value.op.id)
    assert len(value.client.submits) == 2
    assert value.images == [0, 1, 2, 3]


@pytest.mark.asyncio
async def test_unknown_video_submission_is_never_repeated(grouped):
    value = grouped
    value.client.fail_submit = True
    for reconcile_only in (False, False, True):
        with pytest.raises(AppError, match="SMART_REMAKE_SUBMISSION_UNRESOLVED"):
            await value.runner.execute(value.row.id, value.op.id, reconcile_only=reconcile_only)
    assert len(value.client.submits) == 1
    assert value.images == [0, 1]
    assert value.op.status == "running" and value.op.result_json["needsReconciliation"]


@pytest.mark.asyncio
async def test_legacy_unknown_submission_never_prepares_replacement_generation(grouped):
    value = grouped
    value.row.context_json.pop("generationExpectations")
    value.row.context_json.pop("expectationsHash")
    group = value.groups[0]
    value.op.result_json["tasks"] = {
        f"group:{group['id']}": {
            "status": "submitting",
            "requestHash": "legacy-submission-receipt",
            "group": group,
        }
    }
    for reconcile_only in (False, True):
        with pytest.raises(AppError, match="SMART_REMAKE_SUBMISSION_UNRESOLVED"):
            await value.runner.execute(value.row.id, value.op.id, reconcile_only=reconcile_only)
    assert value.images == value.client.uploads == value.client.submits == []
    assert value.client.polls == []
    assert value.op.status == "running" and value.op.result_json["needsReconciliation"]


@pytest.mark.asyncio
@pytest.mark.parametrize("changed", ["product", "source_range", "opening"])
async def test_changed_expectations_rejected_before_images_or_uploads(grouped, changed):
    value = grouped
    context = value.row.context_json
    if changed == "product":
        context["productLock"]["visualIdentity"]["colors"] = ["green"]
    elif changed == "source_range":
        context["sourceSceneMap"]["scenes"][0]["endFrame"] += 1
    else:
        source_id = context["renderPlan"]["units"][0]["sourceSceneId"]
        context["sourceOpeningFrames"][source_id]["layoutHash"] = hashlib.sha256(
            b"different mock opening"
        ).hexdigest()
    with pytest.raises(AppError, match="SMART_REMAKE_EXPECTATIONS_REQUIRED"):
        await value.runner.execute(value.row.id, value.op.id)
    assert value.images == value.client.uploads == value.client.submits == []
    assert value.op.status == "failed"


@pytest.mark.asyncio
async def test_unknown_image_submission_remains_running_and_never_submits_video(grouped):
    value = grouped

    async def unresolved(**kwargs):
        raise AppError("OPENAI_IMAGE_SUBMISSION_UNRESOLVED", "ambiguous image receipt", 409)

    value.helper.prepare_scene_image = unresolved
    with pytest.raises(AppError, match="OPENAI_IMAGE_SUBMISSION_UNRESOLVED"):
        await value.runner.execute(value.row.id, value.op.id)
    assert value.op.status == "running"
    assert value.client.submits == []
    assert value.op.result_json["needsReconciliation"] is True


@pytest.mark.asyncio
async def test_group_resume_does_not_skip_unretained_sibling_when_first_already_exists(grouped):
    value = grouped
    # This task predates the contract upgrade: only its existing ID may be polled.
    value.row.context_json.pop("generationExpectations")
    value.row.context_json.pop("expectationsHash")
    group = value.groups[0]
    value.row.state_json["scenes"][0]["versions"] = [
        {
            "id": "retained-first",
            "providerMetadata": {"providerRequestId": "known-task", "renderGroupId": group["id"]},
        }
    ]
    value.op.result_json["tasks"] = {
        f"group:{group['id']}": {"taskId": "known-task", "status": "submitted", "group": group}
    }
    await value.runner.execute(value.row.id, value.op.id, reconcile_only=True)
    assert all(len(scene["versions"]) == 1 for scene in value.row.state_json["scenes"][:2])
    assert value.client.submits == [] and value.images == []


@pytest.mark.asyncio
async def test_group_identity_is_frozen_before_image_call(grouped):
    value = grouped
    original = value.helper.prepare_scene_image

    async def checked(**kwargs):
        result = value.op.result_json
        assert result["renderPlan"]["groups"] == value.groups
        assert result["renderPlanHash"]
        assert result["renderPlan"]["videoModel"] == "veo3_lite"
        assert result["generationExpectations"] == value.row.context_json["generationExpectations"]
        assert result["expectationsHash"] == value.row.context_json["expectationsHash"]
        return await original(**kwargs)

    value.helper.prepare_scene_image = checked
    await value.runner.execute(value.row.id, value.op.id)


@pytest.mark.asyncio
async def test_group_provider_failure_is_terminal_without_retaining_scenes(grouped):
    value = grouped
    value.client.status = "failed"
    with pytest.raises(AppError, match="KIE_TASK_FAILED"):
        await value.runner.execute(value.row.id, value.op.id)
    assert value.op.status == "failed" and value.retained == []


@pytest.mark.asyncio
async def test_changed_frozen_plan_rejected_before_paid_work(grouped):
    value = grouped
    plan = copy.deepcopy(value.row.context_json["renderPlan"])
    value.op.result_json.update(renderPlan=plan, renderPlanHash=kie_workflow._fingerprint(plan))
    value.row.context_json["renderPlan"] = {**plan, "imageQuality": "medium"}
    with pytest.raises(AppError, match="SMART_REMAKE_RENDER_PLAN_CHANGED"):
        await value.runner.execute(value.row.id, value.op.id)
    assert value.images == value.client.submits == []
    assert value.op.status == "failed"


@pytest.mark.asyncio
async def test_repair_stays_one_scene_and_generates_its_opening_and_ending(grouped, monkeypatch):
    value = grouped
    scene = value.row.state_json["scenes"][1]
    scene.pop("targetDurationFrames")  # Persisted scenes keep timing in renderPlan/draftTimeline.
    scene["activeVersionId"] = "original"
    scene["versions"] = [{"id": "original", "providerMetadata": {}}]
    value.op.result_json = {
        "kind": "repair",
        "sceneIndex": 1,
        "sceneId": scene["id"],
        "compiledScene": value.row.context_json["sceneMap"]["scenes"][1],
        "request": {"baseVersionId": "original"},
        "tasks": {},
    }
    monkeypatch.setattr(
        kie_workflow,
        "_new_version",
        lambda *args, **kwargs: {
            "id": "candidate",
            "providerMetadata": args[4],
            "usedByRevision": None,
        },
    )
    from viraldy.modules.smart_remake import timeline_media

    monkeypatch.setattr(timeline_media, "probe_timeline_media", lambda data: {"frameCount": 192})
    await value.runner.execute(value.row.id, value.op.id)
    assert value.images == [1, 1] and len(value.client.submits) == 1
    assert value.image_roles == ["opening", "ending"]
    assert set(value.op.result_json["tasks"]) == {"1"}
    assert len(value.requests[0]["scenes"]) == 1
    assert value.requests[0]["segments"] == [
        {"renderUnitId": scene["id"], "inFrame": 0, "outFrame": 120}
    ]
    assert scene["activeVersionId"] == "original"
    candidate = value.row.state_json["scenes"][1]["versions"][-1]
    assert candidate["providerMetadata"]["suggestedInFrame"] == 0
    assert candidate["providerMetadata"]["suggestedOutFrame"] == 120
    assert value.op.result_json["candidateVersionId"] == "candidate"


@pytest.mark.asyncio
async def test_saved_v2_without_expectations_requires_updated_plan_before_new_work(grouped):
    value = grouped
    plan = value.row.context_json["renderPlan"]
    for field in ("groups", "imageModel", "imageQuality", "imageSize", "videoModel"):
        plan.pop(field, None)
    value.row.context_json.pop("generationExpectations")
    value.row.context_json.pop("expectationsHash")
    with pytest.raises(AppError, match="SMART_REMAKE_EXPECTATIONS_REQUIRED"):
        await value.runner.execute(value.row.id, value.op.id)
    assert value.client.submits == value.client.uploads == value.images == []
    assert value.op.status == "failed"
    assert value.op.result_json["tasks"] == {}


@pytest.mark.asyncio
async def test_new_repair_checks_openai_configuration_before_queueing(grouped, monkeypatch):
    from viraldy.modules.smart_remake import service
    from viraldy.modules.smart_remake.repair_schemas import RepairSceneRequest

    value = grouped
    value.row.state_json["revision"] = 1
    value.row.context_json["productLock"] = {}

    async def start(*args):
        return value.row, value.op, True

    def not_configured(settings):
        raise AppError("OPENAI_IMAGES_NOT_CONFIGURED", "missing OpenAI image configuration", 503)

    value.repair.repository.start = start
    monkeypatch.setattr(kie_workflow, "_service", lambda *args: value.repair)
    monkeypatch.setattr(service, "require_kie_renderer", lambda settings: None)
    monkeypatch.setattr(service, "require_openai_images", not_configured)
    request = RepairSceneRequest(
        expectedRevision=1,
        prompt="new",
        imagePrompt="image",
        videoPrompt="motion",
        idempotencyKey="repair-new",
    )
    with pytest.raises(AppError, match="OPENAI_IMAGES_NOT_CONFIGURED"):
        await kie_workflow.enqueue_kie_repair(
            None,
            value.repair.settings,
            value.row.workspace_id,
            value.row.id,
            value.row.state_json["scenes"][0]["id"],
            request,
        )
    assert value.op.status == "failed"
    assert value.client.submits == value.images == []


@pytest.mark.asyncio
async def test_reconciliation_of_pending_group_only_polls_the_recorded_id(grouped):
    value = grouped
    # Legacy paid task remains reconcilable without silently upgrading its plan.
    value.row.context_json.pop("generationExpectations")
    value.row.context_json.pop("expectationsHash")
    group = value.groups[0]
    value.op.result_json["tasks"] = {
        f"group:{group['id']}": {
            "taskId": "already-paid",
            "status": "submitted",
            "model": "veo3_lite",
            "group": group,
        }
    }
    value.client.status = "processing"
    await value.runner.execute(value.row.id, value.op.id, reconcile_only=True)
    assert value.client.polls == ["already-paid"]
    assert value.images == value.client.uploads == value.client.submits == []


@pytest.mark.asyncio
async def test_missing_group_output_keeps_task_for_retrieval_retry(grouped):
    value = grouped

    async def missing_output(task_id):
        return {"status": "completed", "output": {}}

    value.client.get_task = missing_output
    with pytest.raises(RuntimeError, match="without a new generation"):
        await value.runner.execute(value.row.id, value.op.id)
    assert value.op.status == "running"
    assert value.op.result_json["errorCode"] == "KIE_OUTPUT_PENDING"
    assert len(value.client.submits) == 1


@pytest.mark.asyncio
async def test_complete_member_bindings_skip_download_and_do_not_duplicate_versions(grouped):
    value = grouped
    await value.runner.execute(value.row.id, value.op.id)
    retained = len(value.retained)
    value.op.status = "running"
    value.client.fail_download = True
    await value.runner.execute(value.row.id, value.op.id, reconcile_only=True)
    assert len(value.retained) == retained
    assert all(len(scene["versions"]) == 1 for scene in value.row.state_json["scenes"])
    assert len(value.client.submits) == 2


@pytest.mark.asyncio
async def test_claim_fence_runs_before_gpt_image_preparation(grouped):
    value = grouped

    def superseded():
        raise AppError("JOB_ATTEMPT_SUPERSEDED", "another worker owns the attempt", 409)

    value.runner.ensure_active = superseded
    with pytest.raises(AppError, match="JOB_ATTEMPT_SUPERSEDED"):
        await value.runner.execute(value.row.id, value.op.id)
    assert value.images == value.client.submits == []
    assert value.op.status == "running"


@pytest.mark.asyncio
async def test_missing_openai_settings_does_not_instantiate_or_submit_any_generation(grouped):
    value = grouped
    value.runner.image_client = None
    value.repair.settings = None
    with pytest.raises(AppError, match="OPENAI_IMAGES_NOT_CONFIGURED"):
        await value.runner.execute(value.row.id, value.op.id)
    assert value.op.status == "failed"
    assert value.images == value.client.submits == []


@pytest.mark.asyncio
async def test_long_group_prompts_preserve_all_scene_directions_in_two_provider_calls(
    grouped, monkeypatch
):
    value = grouped
    monkeypatch.setattr(kie_adapter, "build_kie_group_request", value.real_adapter)
    monkeypatch.setattr(kie_adapter, "public_media_url", lambda url: url)
    for index, scene in enumerate(value.row.context_json["sceneMap"]["scenes"]):
        scene.update(
            prompt=f"Direction {index}: " + "direction " * 1000,
            imagePrompt=f"Opening {index}: " + "opening " * 1000,
            videoPrompt=f"Action {index}: " + "motion " * 1000,
        )
    install_expectations(value.row.context_json)
    await value.runner.execute(value.row.id, value.op.id)
    assert len(value.client.submits) == 2
    assert all(request["input_data"]["duration"] == 8 for request in value.client.submits)
    assert all(len(request["input_data"]["prompt"]) > 20000 for request in value.client.submits)
    for index, scene in enumerate(value.row.context_json["sceneMap"]["scenes"]):
        prompt = value.client.submits[index // 2]["input_data"]["prompt"]
        assert all(scene[key].strip() in prompt for key in ("prompt", "imagePrompt", "videoPrompt"))
    assert value.op.status == "completed"
    await value.runner.execute(value.row.id, value.op.id)
    assert len(value.client.submits) == 2
