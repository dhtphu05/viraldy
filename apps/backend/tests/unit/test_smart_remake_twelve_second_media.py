"""Six-second receipts retain private media access and existing snapshot identities."""

import copy
import hashlib
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from tests.unit.test_provider_group_planning import context
from tests.unit.test_smart_remake_generated_media import use_r2_image
from tests.unit.test_smart_remake_generation_progress import fixture, image, video
from tests.unit.test_smart_remake_twelve_second_windows import (
    state_for,
    twelve_second_context,
)
from viraldy.modules.smart_remake.generation_expectations import (
    build_generation_expectations,
    expectations_hash,
    require_generation_expectations,
)
from viraldy.modules.smart_remake.generation_media import generated_image_download
from viraldy.modules.smart_remake.generation_progress import present_generation_progress
from viraldy.shared.errors.base import AppError


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def twelve_receipt():
    row, operation = fixture()
    data = twelve_second_context()
    data.update(audioRequired=True, imageAssets={})
    row.context_json, row.state_json = data, state_for(data)
    row.state_json["revision"] = row.revision = 2
    operation.result_json.update(
        renderPlan=copy.deepcopy(data["renderPlan"]),
        renderPlanHash=digest(data["renderPlan"]),
        generationExpectations=copy.deepcopy(data["generationExpectations"]),
        expectationsHash=data["expectationsHash"],
    )
    return row, operation


async def test_twelve_second_images_download_and_proven_prompt_remain_available():
    row, op = twelve_receipt()
    asset = use_r2_image(row, op, image(row, op, frame_role="opening"))
    attempt = video(row, op, status="completed")
    attempt.model = "wan/3-0-video"
    attempt.receipt_json["executionEvidence"]["model"] = attempt.model
    group = op.result_json["renderPlan"]["groups"][0]
    task = op.result_json["tasks"][f"group:{group['id']}"]
    snapshot = {
        "model": attempt.model,
        "input": {
            "prompt": "Exact submitted six-second directions.",
            "duration": 6,
            "audio": True,
            "resolution": "480P",
            "aspect_ratio": "9:16",
        },
    }
    task.update(videoRequest=snapshot, imageReferences=[], requestModel=attempt.model)
    task["requestHash"] = attempt.request_hash = digest(
        {
            **snapshot,
            "productHash": row.context_json["productMediaHash"],
            "characterHash": row.context_json.get("characterMediaHash"),
            "imageHashes": [],
            "expectationsHash": op.result_json["expectationsHash"],
        }
    )
    attempt.receipt_json["executionEvidence"]["requestHash"] = attempt.request_hash
    key = f"workspaces/{row.workspace_id}/smart-remake/{row.id}/__r2__/{uuid4().hex}"
    by_id = {scene["id"]: scene for scene in row.state_json["scenes"]}
    for segment in group["segments"]:
        by_id[segment["renderUnitId"]]["versions"] = [
            {
                "storageKey": key,
                "mediaHash": "a" * 64,
                "frameCount": 144,
                "rawDurationFrames": 144,
                "technicalCheck": {"status": "passed"},
                "expectationsHash": op.result_json["expectationsHash"],
                "suggestedInFrame": segment["inFrame"],
                "suggestedOutFrame": segment["outFrame"],
                "providerMetadata": {
                    "renderGroupId": group["id"],
                    "providerRequestId": attempt.provider_task_id,
                    "requestHash": attempt.request_hash,
                },
            }
        ]
    media = SimpleNamespace(
        url=AsyncMock(return_value="https://signed.example/preview"),
        download_url=AsyncMock(return_value="https://signed.example/original"),
    )
    progress = await present_generation_progress(
        row,
        op,
        workspace_id=row.workspace_id,
        attempts=[attempt],
        media=media,
    )
    assert len(progress["groups"]) == 2
    public = progress["groups"][0]
    assert public["conditioningImages"][0]["requestHash"] == asset["requestHash"]
    assert public["videoUrl"] == "https://signed.example/preview"
    assert public["kieRequest"]["prompt"] == snapshot["input"]["prompt"]
    repair = SimpleNamespace(
        media=media,
        repository=SimpleNamespace(
            project=AsyncMock(return_value=row),
            operation=AsyncMock(return_value=op),
        ),
    )
    result = await generated_image_download(
        repair,
        row.workspace_id,
        row.id,
        op.id,
        asset["requestHash"],
    )
    assert result["url"] == "https://signed.example/original"
    media.download_url.assert_awaited_once_with(asset["storageKey"], result["filename"])
    by_id[group["renderUnitIds"][0]]["versions"][0]["rawDurationFrames"] = 192
    progress = await present_generation_progress(
        row,
        op,
        workspace_id=row.workspace_id,
        attempts=[attempt],
        media=media,
    )
    assert "videoUrl" not in progress["groups"][0]
    row.workspace_id = uuid4()
    with pytest.raises(AppError):
        await generated_image_download(repair, uuid4(), row.id, op.id, asset["requestHash"])


@pytest.mark.parametrize("change", ["model", "audio", "duration"])
async def test_twelve_second_media_rejects_inconsistent_provider_windows(change):
    row, op = twelve_receipt()
    if change == "model":
        row.context_json["renderPlan"]["videoModel"] = "veo3_lite"
    elif change == "audio":
        row.context_json["renderPlan"]["audioRequired"] = False
    else:
        row.context_json["renderPlan"]["groups"][0]["rawDurationFrames"] = 192
    plan = row.context_json["renderPlan"]
    row.state_json["renderPlan"] = copy.deepcopy(plan)
    op.result_json.update(renderPlan=copy.deepcopy(plan), renderPlanHash=digest(plan))
    media = SimpleNamespace(url=AsyncMock())
    assert (
        await present_generation_progress(
            row,
            op,
            workspace_id=row.workspace_id,
            attempts=[],
            media=media,
        )
        is None
    )
    media.url.assert_not_awaited()


@pytest.mark.parametrize("duration", [8, 16])
def test_existing_snapshot_hash_stays_identical_when_product_views_are_present(duration):
    data = context(target_duration=duration)
    before = copy.deepcopy(data["generationExpectations"])
    data["p0"]["additionalProductReferences"] = [{"mediaHash": "c" * 64}]
    assert build_generation_expectations(data) == before
    assert "productReferenceHashes" not in before
    assert expectations_hash(before) == data["expectationsHash"]
    assert require_generation_expectations(data) == before


def test_retained_product_manifest_is_owned_and_preserves_frozen_hash():
    data = twelve_second_context()
    data["p0"]["additionalProductReferences"] = [{"mediaHash": "c" * 64}]
    saved = copy.deepcopy(data["generationExpectations"])
    saved["productReferenceHashes"] = [data["productMediaHash"], "c" * 64]
    data.update(generationExpectations=saved, expectationsHash=expectations_hash(saved))
    assert require_generation_expectations(data) == saved
    assert build_generation_expectations(data) == saved
    original_hash = data["expectationsHash"]
    data["generationExpectations"]["productReferenceHashes"][1] = "d" * 64
    data["expectationsHash"] = expectations_hash(data["generationExpectations"])
    assert data["expectationsHash"] != original_hash
    with pytest.raises(AppError):
        require_generation_expectations(data)


def test_real_owned_product_views_require_refreshing_a_legacy_single_photo_snapshot():
    data = context(target_duration=8)
    before = copy.deepcopy(data["generationExpectations"])
    data["p0"]["additionalProductReferences"] = [{
        "role": "product", "storageKey": "private-owned-view", "mimeType": "image/png",
        "mediaHash": "c" * 64,
    }]
    current = build_generation_expectations(data)
    assert current["productReferenceHashes"] == [data["productMediaHash"], "c" * 64]
    assert data["generationExpectations"] == before
    with pytest.raises(AppError):
        require_generation_expectations(data)
    # An explicit new compile can freeze all views without reusing the old snapshot.
    data.pop("generationExpectations")
    assert build_generation_expectations(data) == current


@pytest.mark.parametrize(
    "provider,scope,owned",
    [
        ("wan/3-0-video", "excerpt", True),
        ("veo3_lite", "full_source", True),
        ("wan/3-0-video", "full_source", False),
    ],
)
async def test_unsupported_twelve_second_analysis_stops_before_assets_or_ai(
    monkeypatch,
    provider,
    scope,
    owned,
):
    from viraldy.modules.smart_remake import timeline_compile

    monkeypatch.setenv("SMART_REMAKE_KIE_VIDEO_MODEL", provider)
    read = AsyncMock(side_effect=AssertionError("No storage or provider work"))
    monkeypatch.setattr(timeline_compile, "read_media", read)
    monkeypatch.setattr(timeline_compile, "feature_enabled", lambda settings: True)
    with pytest.raises(AppError) as caught:
        await timeline_compile.compile_timeline_request(
            session=object(),
            settings=SimpleNamespace(ai_mode="fixture"),
            workspace_id=uuid4(),
            mode="smart_remake",
            target_duration="12",
            aspect_ratio="9:16",
            language=None,
            prompt=None,
            description=None,
            product_url=None,
            product_title=None,
            product_description=None,
            reference_video=None,
            product_image=None,
            project_id=uuid4() if owned else None,
            analysis_scope=scope,
        )
    assert caught.value.code == "SMART_REMAKE_VIDEO_DURATION_INVALID"
    assert caught.value.status_code == 422
    read.assert_not_awaited()


async def test_legacy_compile_twelve_seconds_stops_before_upload_or_ai(monkeypatch):
    from viraldy.modules.smart_remake import service

    read = AsyncMock(side_effect=AssertionError("No storage or provider work"))
    monkeypatch.setattr(service, "read_media", read)
    monkeypatch.setattr(service, "feature_enabled", lambda settings: True)
    with pytest.raises(AppError) as caught:
        await service.compile_request(
            settings=object(),
            mode="smart_remake",
            target_duration="12",
            aspect_ratio="9:16",
            language=None,
            prompt=None,
            description=None,
            product_url=None,
            product_title=None,
            product_description=None,
            reference_video=None,
            product_image=None,
        )
    assert caught.value.status_code == 422
    read.assert_not_awaited()


async def test_veo_twelve_second_intake_stops_before_asset_storage(monkeypatch):
    from tests.unit.test_smart_remake_rights import intake_payload
    from viraldy.modules.smart_remake.project_intake import create_intake

    monkeypatch.setenv("SMART_REMAKE_KIE_VIDEO_MODEL", "veo3_lite")
    with pytest.raises(AppError) as caught:
        await create_intake(
            object(),
            object(),
            uuid4(),
            uuid4(),
            intake_payload(targetDuration=12),
            b"unused-source",
            b"unused-product",
        )
    assert caught.value.status_code == 422


async def test_retention_callback_checks_six_second_audio_and_all_scene_ranges(monkeypatch):
    from viraldy.modules.smart_remake import timeline_service

    row, op = twelve_receipt()
    group = row.context_json["renderPlan"]["groups"][0]
    captured = []

    def version(data, key, prompts, parent, metadata, **options):
        captured.append(options)
        return {"id": str(uuid4()), "technicalCheck": {"status": "passed"}}

    monkeypatch.setattr(timeline_service, "_new_version", version)
    monkeypatch.setattr(timeline_service, "probe_timeline_media", lambda data: {"frameCount": 144})
    monkeypatch.setattr(timeline_service, "_release_reads", AsyncMock())
    finished = AsyncMock()
    monkeypatch.setattr(timeline_service, "_finish_retention", finished)
    service = SimpleNamespace(
        workspace_id=row.workspace_id,
        repository=SimpleNamespace(project=AsyncMock(return_value=row)),
        media=SimpleNamespace(put=AsyncMock(return_value="owned-group-video")),
    )
    await timeline_service.retain_timeline_group_clip(
        service,
        row,
        group,
        b"six-second-video",
        {"providerRequestId": "actual-task"},
    )
    assert len(captured) == len(group["renderUnitIds"])
    assert all(
        options == {"source": "generated", "audio_required": True, "expected_duration": 6}
        for options in captured
    )
    state = finished.await_args.args[3]
    by_id = {scene["id"]: scene for scene in state["scenes"]}
    for segment in group["segments"]:
        version = by_id[segment["renderUnitId"]]["versions"][0]
        assert version["rawDurationFrames"] == version["frameCount"] == 144
        assert version["suggestedInFrame"] == segment["inFrame"]
        assert version["suggestedOutFrame"] == segment["outFrame"]
