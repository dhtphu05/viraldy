"""Generated image downloads and submitted KIE prompt evidence stay project-bound."""

import copy
import hashlib
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from tests.unit.test_smart_remake_generation_progress import fixture, image, video
from tests.unit.test_smart_remake_grouped_workflow import grouped  # noqa: F401
from viraldy.modules.smart_remake.generation_progress import present_generation_progress


def use_r2_image(row, op, asset, *, suffix=None):
    key = asset["storageKey"]
    asset["storageKey"] = key.rsplit("/", 1)[0] + "/__r2__/" + (suffix or uuid4().hex)
    slot = next(
        k
        for k, v in op.result_json["images"].items()
        if v.get("requestHash") == asset["requestHash"]
    )
    op.result_json["images"][slot] = {**copy.deepcopy(asset), "status": "completed"}
    return asset


async def test_r2_conditioning_images_have_bound_download_identity_and_frame_role():
    row, op = fixture()
    asset = use_r2_image(row, op, image(row, op, frame_role="opening"))
    media = SimpleNamespace(url=AsyncMock(return_value="https://signed.example/image"))
    value = await present_generation_progress(
        row, op, workspace_id=row.workspace_id, attempts=[], media=media
    )
    assert value["groups"][0]["conditioningImages"] == [
        {
            "renderUnitId": asset["renderUnitId"],
            "url": "https://signed.example/image",
            "requestHash": asset["requestHash"],
            "frameRole": "opening",
        }
    ]


@pytest.mark.parametrize(
    "suffix", ["../escape", "f" * 31, "f" * 33, "other/" + "f" * 32, "f" * 32 + "?token=x"]
)
async def test_r2_image_preview_rejects_invalid_object_suffix(suffix):
    row, op = fixture()
    use_r2_image(row, op, image(row, op), suffix=suffix)
    media = SimpleNamespace(url=AsyncMock())
    result = await present_generation_progress(
        row, op, workspace_id=row.workspace_id, attempts=[], media=media
    )
    assert "conditioningImages" not in result["groups"][0]
    media.url.assert_not_awaited()


def saved_request(row, op, attempt):
    group = op.result_json["renderPlan"]["groups"][0]
    task = op.result_json["tasks"][f"group:{group['id']}"]
    snapshot = {
        "model": "veo3_lite",
        "input": {
            "prompt": "Exact final prompt\n  Preserve this spacing.",
            "model": "veo3_lite",
            "aspect_ratio": "9:16",
            "duration": 8,
            "generation_type": "FIRST_AND_LAST_FRAMES_2_VIDEO",
        },
    }
    task["videoRequest"] = snapshot
    task["imageReferences"] = []
    request_hash = hashlib.sha256(
        json.dumps(
            {
                **snapshot,
                "productHash": row.context_json.get("productMediaHash"),
                "characterHash": row.context_json.get("characterMediaHash"),
                "imageHashes": [],
                "expectationsHash": op.result_json["expectationsHash"],
            },
            sort_keys=True,
            default=str,
        ).encode()
    ).hexdigest()
    task["requestHash"] = attempt.request_hash = request_hash
    attempt.receipt_json["executionEvidence"]["requestHash"] = request_hash
    return task, snapshot


async def test_only_exact_submitted_kie_prompt_is_presented():
    row, op = fixture()
    attempt = video(row, op)
    task, snapshot = saved_request(row, op, attempt)
    result = await present_generation_progress(
        row,
        op,
        workspace_id=row.workspace_id,
        attempts=[attempt],
        media=SimpleNamespace(url=AsyncMock()),
    )
    assert result["groups"][0]["kieRequest"] == {
        "model": snapshot["model"],
        "prompt": snapshot["input"]["prompt"],
        "requestHash": task["requestHash"],
    }
    assert "input" not in result["groups"][0]["kieRequest"]


@pytest.mark.parametrize("change", ["prompt", "proof", "legacy", "unexpected_field", "wrong_model"])
async def test_prompt_is_not_invented_or_exposed_without_a_bound_submission(change):
    row, op = fixture()
    attempt = video(row, op)
    task, _ = saved_request(row, op, attempt)
    if change == "prompt":
        task["videoRequest"]["input"]["prompt"] = "changed after submission"
    elif change == "proof":
        attempt.receipt_json = {}
    elif change == "legacy":
        task.pop("videoRequest")
    elif change == "wrong_model":
        task["videoRequest"]["model"] = "wrong-model"
    else:
        task["videoRequest"]["input"]["authorization"] = "private"
    result = await present_generation_progress(
        row,
        op,
        workspace_id=row.workspace_id,
        attempts=[attempt],
        media=SimpleNamespace(url=AsyncMock()),
    )
    assert "kieRequest" not in result["groups"][0]


async def test_valid_long_veo_prompt_roundtrips_without_truncation():
    row, op = fixture()
    attempt = video(row, op)
    group = op.result_json["renderPlan"]["groups"][0]
    task = op.result_json["tasks"][f"group:{group['id']}"]
    _, snapshot = saved_request(row, op, attempt)
    snapshot["input"]["prompt"] = "Exact direction. " * 2500
    task["requestHash"] = attempt.request_hash = hashlib.sha256(
        json.dumps(
            {
                **snapshot,
                "productHash": row.context_json.get("productMediaHash"),
                "characterHash": row.context_json.get("characterMediaHash"),
                "imageHashes": [],
                "expectationsHash": op.result_json["expectationsHash"],
            },
            sort_keys=True,
            default=str,
        ).encode()
    ).hexdigest()
    attempt.receipt_json["executionEvidence"]["requestHash"] = attempt.request_hash
    result = await present_generation_progress(
        row,
        op,
        workspace_id=row.workspace_id,
        attempts=[attempt],
        media=SimpleNamespace(url=AsyncMock()),
    )
    assert result["groups"][0]["kieRequest"]["prompt"] == snapshot["input"]["prompt"]


async def test_r2_video_preview_requires_exact_bound_clip_ranges():
    row, op = fixture()
    attempt = video(row, op, status="completed")
    group = op.result_json["renderPlan"]["groups"][0]
    key = f"workspaces/{row.workspace_id}/smart-remake/{row.id}/__r2__/{uuid4().hex}"
    for scene, segment in zip(row.state_json["scenes"], group["segments"], strict=False):
        scene["versions"] = [
            {
                "storageKey": key,
                "mediaHash": "a" * 64,
                "frameCount": 192,
                "rawDurationFrames": 192,
                "technicalCheck": {"status": "passed"},
                "expectationsHash": op.result_json["expectationsHash"],
                "suggestedInFrame": segment["inFrame"],
                "suggestedOutFrame": segment["outFrame"],
                "providerMetadata": {
                    "providerRequestId": attempt.provider_task_id,
                    "renderGroupId": group["id"],
                    "requestHash": attempt.request_hash,
                },
            }
        ]
    media = SimpleNamespace(url=AsyncMock(return_value="https://signed.example/video"))
    result = await present_generation_progress(
        row, op, workspace_id=row.workspace_id, attempts=[attempt], media=media
    )
    assert result["groups"][0]["videoUrl"] == "https://signed.example/video"
    row.state_json["scenes"][0]["versions"][0]["storageKey"] = (
        f"workspaces/{uuid4()}/smart-remake/{row.id}/__r2__/{uuid4().hex}"
    )
    media.url.reset_mock()
    result = await present_generation_progress(
        row, op, workspace_id=row.workspace_id, attempts=[attempt], media=media
    )
    assert "videoUrl" not in result["groups"][0]
    media.url.assert_not_awaited()


@pytest.mark.parametrize("kind", ["timeline", "compose", "approval", "export", "repair"])
async def test_generated_media_remains_available_after_non_generation_operations(kind):
    from viraldy.modules.smart_remake.repair_service import RepairService

    row, op = fixture()
    image(row, op)
    op.status = "completed"
    latest = SimpleNamespace(id=uuid4(), status="completed", result_json={"kind": kind})
    session = SimpleNamespace(scalars=AsyncMock(return_value=[]), commit=AsyncMock())
    repository = SimpleNamespace(
        project=AsyncMock(return_value=row),
        running=AsyncMock(return_value=None),
        latest_operation=AsyncMock(return_value=latest),
        latest_render_operation=AsyncMock(return_value=op),
        session=session,
    )
    service = RepairService(
        repository,
        SimpleNamespace(url=AsyncMock(return_value="https://signed.example/image")),
        row.workspace_id,
    )
    service.present = AsyncMock(return_value={"id": str(row.id)})
    result = await service.get(row.id)
    assert result["generationProgress"]["operationId"] == str(op.id)
    assert result["generationProgress"]["groups"][0]["conditioningImages"]
    assert result["lastOperation"]["kind"] == kind
    session.commit.assert_not_awaited()


async def test_new_compile_does_not_project_the_original_generation():
    from viraldy.modules.smart_remake.repair_service import RepairService

    row, op = fixture()
    image(row, op)
    op.status = "completed"
    latest = SimpleNamespace(id=uuid4(), status="completed", result_json={"kind": "compile"})
    repository = SimpleNamespace(
        project=AsyncMock(return_value=row),
        running=AsyncMock(return_value=None),
        latest_operation=AsyncMock(return_value=latest),
        latest_render_operation=AsyncMock(return_value=op),
    )
    service = RepairService(repository, SimpleNamespace(url=AsyncMock()), row.workspace_id)
    service.present = AsyncMock(return_value={"id": str(row.id)})
    result = await service.get(row.id)
    assert "generationProgress" not in result
    repository.latest_render_operation.assert_not_awaited()


async def test_final_prompt_snapshot_is_committed_before_kie_submission(grouped):  # noqa: F811
    await grouped.runner.execute(grouped.row.id, grouped.op.id)
    for group, submitted in zip(grouped.groups, grouped.client.submits, strict=True):
        task = grouped.op.result_json["tasks"][f"group:{group['id']}"]
        assert task["videoRequest"]["model"] == submitted["model"]
        assert task["videoRequest"]["input"]["prompt"] == submitted["input_data"]["prompt"]
        assert (
            not {"image_urls", "first_frame_url", "last_frame_url"}
            & task["videoRequest"]["input"].keys()
        )
        assert any(
            result.get("tasks", {}).get(f"group:{group['id']}", {}).get("videoRequest")
            == task["videoRequest"]
            for result in grouped.repair.repository.history
        )
