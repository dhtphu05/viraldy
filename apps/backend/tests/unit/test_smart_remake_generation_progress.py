from __future__ import annotations

import copy
import hashlib
import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from tests.smart_remake_expectations import install_expectations


def fixture(duration=16):
    workspace, project, operation = uuid4(), uuid4(), uuid4()
    units = [
        {"id": str(uuid4()), "sceneIndex": i, "targetDurationFrames": 96, "rawDurationFrames": 192}
        for i in range(duration // 4)
    ]
    groups = [
        {
            "id": str(uuid4()),
            "renderUnitIds": [u["id"] for u in units[i : i + 2]],
            "rawDurationFrames": 192,
            "targetDurationFrames": 192,
            "segments": [
                {"renderUnitId": u["id"], "inFrame": j * 96, "outFrame": (j + 1) * 96}
                for j, u in enumerate(units[i : i + 2])
            ],
        }
        for i in range(0, len(units), 2)
    ]
    plan = {
        "units": units,
        "groups": groups,
        "groupingPolicy": "fixed_provider_windows",
        "imageModel": "gpt-image-2.6-sunburst",
        "referencePolicy": "product-first-last-layout",
    }
    state = {"targetDuration": duration, "scenes": [{"id": u["id"], "versions": []} for u in units]}
    context = {
        "renderPlan": plan,
        "sourceKey": "source",
        "productKey": "product",
        "p0": {"targetDuration": duration, "requirements": {}},
        "imageAssets": {},
    }
    install_expectations(context, state=state)
    state["renderPlan"] = copy.deepcopy(plan)
    row = SimpleNamespace(
        id=project, workspace_id=workspace, state_json=state, context_json=context
    )
    op = SimpleNamespace(
        id=operation,
        project_id=project,
        status="running",
        created_at=datetime(2026, 11, 26, 12, tzinfo=UTC),
        result_json={
            "kind": "render",
            "tasks": {},
            "images": {},
            "renderPlan": copy.deepcopy(plan),
            "renderPlanHash": hashlib.sha256(
                json.dumps(plan, sort_keys=True, default=str).encode()
            ).hexdigest(),
            "expectationsHash": context["expectationsHash"],
            "generationExpectations": copy.deepcopy(context["generationExpectations"]),
        },
    )
    return row, op


def image(row, op, index=0, frame_role=None):
    unit = op.result_json["renderPlan"]["units"][index]
    scene = next(
        s
        for s in op.result_json["generationExpectations"]["scenes"]
        if s["renderUnitId"] == unit["id"]
    )
    image_key = str(index) if frame_role != "ending" else f"{index}:ending"
    digest = hashlib.sha256((image_key + str(frame_role)).encode()).hexdigest()
    asset = {
        "storageKey": f"workspaces/{row.workspace_id}/smart-remake/{row.id}/images/{uuid4().hex}",
        "requestHash": digest,
        "mediaHash": "c" * 64,
        "mimeType": "image/png",
        "expectationsHash": op.result_json["expectationsHash"],
        **{k: copy.deepcopy(scene[k]) for k in ("renderUnitId", "sourceSceneId", "openingFrame")},
    }
    if frame_role is not None:
        asset["frameRole"] = frame_role
        asset["referenceFrame"] = {
            **scene["openingFrame"],
            **({"frame": scene["sourceRange"]["endFrame"] - 1, "layoutHash": "d" * 64}
               if frame_role == "ending" else {}),
        }
    row.context_json["imageAssets"][digest] = asset
    op.result_json["images"][image_key] = {**copy.deepcopy(asset), "status": "completed"}
    return asset


def check(row, op, asset, phase="completed", status="insufficient_evidence"):
    identity, context_hash = str(uuid4()), "d" * 64
    subject = {
        "kind": "image",
        "imageRole": "conditioning",
        "projectId": str(row.id),
        "mediaHash": asset["mediaHash"],
    }
    row.context_json["p0"]["conditioningChecks"] = {
        context_hash: {
            "operationId": str(op.id),
            "contextHash": context_hash,
            "phase": phase,
            "status": status,
            "subject": subject,
            "reportId": identity,
            "stale": False,
            "startedAt": "2026-11-26T12:01:00+00:00",
            "completedAt": "2026-11-26T12:02:00+00:00",
        }
    }
    row.context_json["p0"]["inspections"] = {
        "reports": [
            {
                "id": identity,
                "operationId": str(op.id),
                "contextHash": context_hash,
                "status": status,
                "subject": subject,
                "stale": False,
                "stage": "conditioning",
                "expectationsHash": op.result_json["expectationsHash"],
                "conditioningImageRequestHash": asset["requestHash"],
            }
        ]
    }
    return identity


def video(row, op, index=0, status="submitted", proof=True):
    group = op.result_json["renderPlan"]["groups"][index]
    identity, task_id = uuid4(), f"kie-task-{index}"
    attempt = SimpleNamespace(
        id=identity,
        project_id=row.id,
        workspace_id=row.workspace_id,
        stage="video",
        provider="kie",
        model="veo3_lite",
        status=status,
        request_hash="e" * 64,
        provider_task_id=task_id,
        metadata_json={"operationId": str(op.id), "slot": f"video:group:{group['id']}"},
        receipt_json={},
        submitted_at=op.created_at + timedelta(minutes=3),
        completed_at=None,
    )
    if proof:
        attempt.receipt_json = {
            "executionEvidence": {
                "version": 1,
                "mode": "live",
                "transport": "verified_tls",
                "provider": "kie",
                "model": attempt.model,
                "attemptId": str(identity),
                "requestHash": attempt.request_hash,
                "operation": "kie.tasks.create",
                "responseHash": "f" * 64,
                "observedAt": "2026-11-26T12:03:00+00:00",
                "taskId": task_id,
            }
        }
    op.result_json["tasks"][f"group:{group['id']}"] = {
        "status": "submitted",
        "attemptId": str(identity),
        "taskId": task_id,
        "requestHash": attempt.request_hash,
        "renderGroupId": group["id"],
        "group": copy.deepcopy(group),
        "expectationsHash": op.result_json["expectationsHash"],
    }
    return attempt


def project(row, op, attempts=()):
    from viraldy.modules.smart_remake.generation_progress import generation_progress

    return generation_progress(
        row,
        op,
        workspace_id=row.workspace_id,
        attempts=None if attempts is None else list(attempts),
    )


@pytest.mark.parametrize("duration,count", [(8, 1), (16, 2)])
def test_progress_uses_provider_windows_not_number_of_scene_units(duration, count):
    row, op = fixture(duration)
    value = project(row, op)
    assert len(value["groups"]) == count
    assert all(g["stage"] == "queued" and g["videoSubmitted"] is False for g in value["groups"])
    assert value["startedAt"] == value["updatedAt"] == op.created_at.isoformat()


def test_preparing_first_group_image_keeps_second_window_queued():
    row, op = fixture()
    op.result_json["images"]["0"] = {"status": "submitting", "requestHash": "a" * 64}
    value = project(row, op)
    assert [g["stage"] for g in value["groups"]] == ["preparing_image", "queued"]
    assert all(g["videoSubmitted"] is False for g in value["groups"])


@pytest.mark.parametrize(
    "phase,status,expected",
    [
        ("invoking", "pending", "checking_image"),
        ("unknown", "pending", "unknown"),
        ("completed", "insufficient_evidence", "blocked"),
        ("completed", "failed", "blocked"),
        ("completed", "passed", "checking_image"),
    ],
)
def test_conditioning_stage_comes_from_owned_image_checks(phase, status, expected):
    row, op = fixture()
    asset = image(row, op)
    image(row, op, 1)
    identity = check(row, op, asset, phase, status)
    if expected == "blocked":
        op.status = "failed"
        op.result_json["errorCode"] = "SMART_REMAKE_CONDITIONING_BLOCKED"
    value = project(row, op)
    assert value["groups"][0]["stage"] == expected
    assert value["groups"][1]["stage"] == "queued"
    assert value["updatedAt"] == "2026-11-26T12:02:00+00:00"
    if phase == "completed":
        assert value["groups"][0]["inspectionReportId"] == identity


def test_failed_image_does_not_look_like_video_generation():
    row, op = fixture()
    op.status = "failed"
    op.result_json["errorCode"] = "OPENAI_IMAGE_CREDITS_EXHAUSTED"
    op.result_json["images"]["0"] = {"status": "rejected"}
    value = project(row, op)
    assert value["groups"][0] == {
        "groupId": op.result_json["renderPlan"]["groups"][0]["id"],
        "stage": "blocked",
        "videoSubmitted": False,
        "errorCode": "OPENAI_IMAGE_CREDITS_EXHAUSTED",
    }
    assert value["groups"][1]["stage"] == "queued"


def test_later_image_failure_is_not_attributed_to_an_earlier_technical_clip_failure():
    row, op = fixture()
    attempt = video(row, op, status="completed")
    group = op.result_json["renderPlan"]["groups"][0]
    for scene in row.state_json["scenes"][:2]:
        scene["versions"] = [
            {
                "technicalCheck": {"status": "failed"},
                "expectationsHash": op.result_json["expectationsHash"],
                "providerMetadata": {
                    "providerRequestId": attempt.provider_task_id,
                    "renderGroupId": group["id"],
                },
            }
        ]
    op.result_json["images"]["2"] = {
        "status": "rejected",
        "errorCode": "OPENAI_IMAGE_CREDITS_EXHAUSTED",
    }
    op.status = "failed"
    op.result_json["errorCode"] = "OPENAI_IMAGE_CREDITS_EXHAUSTED"
    groups = project(row, op, [attempt])["groups"]
    assert [g["stage"] for g in groups] == ["blocked", "blocked"]
    assert "errorCode" not in groups[0]
    assert groups[1]["errorCode"] == "OPENAI_IMAGE_CREDITS_EXHAUSTED"


@pytest.mark.parametrize("status", ["submitting", "submission_unknown", "unknown"])
def test_uncertain_task_never_claims_no_provider_submission(status):
    row, op = fixture()
    group = op.result_json["renderPlan"]["groups"][0]
    op.result_json["tasks"][f"group:{group['id']}"] = {"status": status}
    value = project(row, op)
    assert value["groups"][0]["videoSubmitted"] is None
    assert value["groups"][0]["stage"] in {"submitting_video", "unknown"}


@pytest.mark.parametrize("stage", ["image", "video"])
def test_running_unresolved_receipt_is_unknown_instead_of_an_endless_spinner(stage):
    row, op = fixture()
    if stage == "image":
        op.result_json["images"]["0"] = {"status": "submitting", "requestHash": "a" * 64}
    else:
        group = op.result_json["renderPlan"]["groups"][0]
        op.result_json["tasks"][f"group:{group['id']}"] = {"status": "submitting"}
    op.result_json.update(needsReconciliation=True, errorCode="OPENAI_IMAGE_SUBMISSION_UNRESOLVED")
    groups = project(row, op)["groups"]
    assert [g["stage"] for g in groups] == ["unknown", "queued"]


@pytest.mark.parametrize("proof,submitted", [(True, True), (False, None)])
def test_video_submission_requires_the_matching_durable_provider_receipt(proof, submitted):
    row, op = fixture()
    attempt = video(row, op, proof=proof)
    value = project(row, op, [attempt])
    assert value["groups"][0]["stage"] == "generating"
    assert value["groups"][0]["videoSubmitted"] is submitted
    assert value["groups"][1]["videoSubmitted"] is False


def test_completed_receipt_is_checking_until_all_group_units_have_matching_retained_versions():
    row, op = fixture()
    attempt = video(row, op, status="completed")
    assert project(row, op, [attempt])["groups"][0]["stage"] == "checking"
    group = op.result_json["renderPlan"]["groups"][0]
    for scene in row.state_json["scenes"]:
        if scene["id"] in group["renderUnitIds"]:
            scene["versions"] = [
                {
                    "technicalCheck": {"status": "passed"},
                    "expectationsHash": op.result_json["expectationsHash"],
                    "providerMetadata": {
                        "providerRequestId": attempt.provider_task_id,
                        "renderGroupId": group["id"],
                    },
                }
            ]
    assert project(row, op, [attempt])["groups"][0]["stage"] == "completed"
    row.state_json["scenes"][0]["versions"][0]["technicalCheck"]["status"] = "failed"
    assert project(row, op, [attempt])["groups"][0]["stage"] == "blocked"


def test_legacy_or_unmapped_ledger_keeps_submission_counts_unknown():
    row, op = fixture()
    assert all(g["videoSubmitted"] is None for g in project(row, op, None)["groups"])
    attempt = video(row, op)
    attempt.metadata_json["slot"] = "legacy-unmapped-video"
    op.result_json["tasks"] = {}
    assert all(g["videoSubmitted"] is None for g in project(row, op, [attempt])["groups"])


def test_unmapped_legacy_task_does_not_claim_zero_submissions_in_known_groups():
    row, op = fixture()
    op.result_json["tasks"] = {"legacy-task": {"taskId": "kie-accepted-old", "status": "submitted"}}
    assert all(g["videoSubmitted"] is None for g in project(row, op)["groups"])


@pytest.mark.asyncio
async def test_another_groups_valid_image_cannot_be_presented_under_the_current_group():
    from viraldy.modules.smart_remake.generation_progress import present_generation_progress

    row, op = fixture()
    image(row, op, 2)
    op.result_json["images"]["0"] = copy.deepcopy(op.result_json["images"]["2"])
    media = SimpleNamespace(url=AsyncMock(return_value="https://owned.test/second-window"))
    progress = await present_generation_progress(
        row,
        op,
        workspace_id=row.workspace_id,
        attempts=[],
        media=media,
    )
    assert "conditioningImages" not in progress["groups"][0]
    assert progress["groups"][1]["conditioningImages"]


@pytest.mark.parametrize(
    "condition",
    [
        "foreign_project",
        "foreign_workspace",
        "compile",
        "wrong_hash",
        "stale_plan",
        "stale_expectations",
        "wrong_range",
        "stopped",
    ],
)
def test_progress_omits_foreign_stale_or_invalid_plan_bindings(condition):
    row, op = fixture()
    if condition == "foreign_project":
        op.project_id = uuid4()
    elif condition == "foreign_workspace":
        row.workspace_id = uuid4()
    elif condition == "compile":
        op.result_json["kind"] = "compile"
    elif condition == "wrong_hash":
        op.result_json["renderPlanHash"] = "bad"
    elif condition == "stale_plan":
        row.context_json["renderPlan"]["groups"].reverse()
    elif condition == "stale_expectations":
        row.context_json["expectationsHash"] = "x" * 64
    elif condition == "wrong_range":
        op.result_json["renderPlan"]["groups"][0]["segments"][0]["outFrame"] = 999
    elif condition == "stopped":
        row.context_json["p0"]["status"] = "suspended"
    from viraldy.modules.smart_remake.generation_progress import generation_progress

    original_workspace = op.result_json["generationExpectations"]["references"].get("workspaceId")
    assert (
        generation_progress(
            row,
            op,
            workspace_id=original_workspace
            or (uuid4() if condition == "foreign_workspace" else row.workspace_id),
            attempts=[],
        )
        is None
    )


@pytest.mark.asyncio
async def test_owned_conditioning_thumbnail_is_presigned_without_reads_or_private_metadata():
    from viraldy.modules.smart_remake.generation_progress import present_generation_progress

    row, op = fixture()
    asset = image(row, op)
    media = SimpleNamespace(
        url=AsyncMock(return_value="https://owned.test/image"),
        read=AsyncMock(side_effect=AssertionError("No storage read")),
    )
    value = await present_generation_progress(
        row, op, workspace_id=row.workspace_id, attempts=[], media=media
    )
    assert value["groups"][0]["conditioningImageUrl"] == "https://owned.test/image"
    assert "storageKey" not in json.dumps(value) and "requestHash" not in json.dumps(value)
    media.url.assert_awaited_once_with(asset["storageKey"])
    media.read.assert_not_awaited()


@pytest.mark.asyncio
async def test_every_finished_conditioning_image_is_visible_before_remaining_work_finishes():
    from viraldy.modules.smart_remake.generation_progress import present_generation_progress

    row, op = fixture()
    op.result_json["referencePreparation"] = "direct"
    first = image(row, op)
    op.result_json["images"]["1"] = {"status": "submitting"}
    media = SimpleNamespace(
        url=AsyncMock(side_effect=lambda key: "https://owned.test/" + key[-32:])
    )
    progress = await present_generation_progress(
        row,
        op,
        workspace_id=row.workspace_id,
        attempts=[],
        media=media,
    )
    assert progress["groups"][0]["conditioningImages"] == [
        {
            "renderUnitId": first["renderUnitId"],
            "url": "https://owned.test/" + first["storageKey"][-32:],
        }
    ]
    assert progress["groups"][0]["stage"] == "preparing_image"
    last = image(row, op, 1)
    progress = await present_generation_progress(
        row,
        op,
        workspace_id=row.workspace_id,
        attempts=[],
        media=media,
    )
    assert {item["renderUnitId"] for item in progress["groups"][0]["conditioningImages"]} == {
        first["renderUnitId"],
        last["renderUnitId"],
    }
    assert progress["groups"][0]["stage"] == "submitting_video"
    assert "conditioningImages" not in progress["groups"][1]


@pytest.mark.asyncio
@pytest.mark.parametrize("character", [False, True])
async def test_new_frame_bookends_show_finished_images_and_wait_for_the_ending(character):
    from viraldy.modules.smart_remake.generation_progress import present_generation_progress

    row, op = fixture()
    if character:
        row.context_json["characterKey"] = "authorized-character"
    op.result_json["referencePreparation"] = "direct"
    opening = image(row, op, frame_role="opening")
    op.result_json["images"]["1:ending"] = {"status": "submitting", "frameRole": "ending"}
    media = SimpleNamespace(
        url=AsyncMock(side_effect=lambda key: "https://owned.test/" + key[-32:])
    )
    waiting = await present_generation_progress(
        row, op, workspace_id=row.workspace_id, attempts=[], media=media
    )
    assert waiting["groups"][0]["stage"] == "preparing_image"
    assert len(waiting["groups"][0]["conditioningImages"]) == 1
    ending = image(row, op, 1, frame_role="ending")
    ready = await present_generation_progress(
        row, op, workspace_id=row.workspace_id, attempts=[], media=media
    )
    assert ready["groups"][0]["stage"] == "submitting_video"
    assert ready["groups"][0]["videoSubmitted"] is False
    assert [item["url"] for item in ready["groups"][0]["conditioningImages"]] == [
        "https://owned.test/" + asset["storageKey"][-32:] for asset in (opening, ending)
    ]


@pytest.mark.asyncio
async def test_one_scene_group_presents_both_frame_roles_without_collapsing_the_scene_id():
    from viraldy.modules.smart_remake.generation_progress import present_generation_progress

    row, op = fixture(8)
    plan = row.context_json["renderPlan"]
    unit = {**plan["units"][0], "targetDurationFrames": 192}
    plan["units"] = [unit]
    plan["groups"][0].update(
        renderUnitIds=[unit["id"]],
        segments=[{"renderUnitId": unit["id"], "inFrame": 0, "outFrame": 192}],
    )
    row.context_json["sceneMap"]["scenes"] = [
        {**row.context_json["sceneMap"]["scenes"][0], "targetDurationFrames": 192}
    ]
    row.state_json["scenes"] = row.state_json["scenes"][:1]
    row.state_json["renderPlan"] = copy.deepcopy(plan)
    install_expectations(row.context_json)
    op.result_json.update(
        renderPlan=copy.deepcopy(plan),
        renderPlanHash=hashlib.sha256(
            json.dumps(plan, sort_keys=True, default=str).encode()
        ).hexdigest(),
        generationExpectations=copy.deepcopy(row.context_json["generationExpectations"]),
        expectationsHash=row.context_json["expectationsHash"],
        referencePreparation="direct",
    )
    image(row, op, frame_role="opening")
    image(row, op, frame_role="ending")
    media = SimpleNamespace(
        url=AsyncMock(side_effect=lambda key: "https://owned.test/" + key[-32:])
    )
    progress = await present_generation_progress(
        row, op, workspace_id=row.workspace_id, attempts=[], media=media
    )
    assert progress["groups"][0]["stage"] == "submitting_video"
    assert [item["renderUnitId"] for item in progress["groups"][0]["conditioningImages"]] == [
        unit["id"], unit["id"],
    ]
    assert media.url.await_count == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("changed", ["frame", "sourceMediaHash", "layoutHash", "extractorVersion"])
async def test_ending_preview_requires_a_bound_final_source_frame(changed):
    from viraldy.modules.smart_remake.generation_progress import present_generation_progress

    row, op = fixture()
    op.result_json["referencePreparation"] = "direct"
    image(row, op, frame_role="opening")
    ending = image(row, op, 1, frame_role="ending")
    ending["referenceFrame"][changed] = -1 if changed == "frame" else "invalid"
    op.result_json["images"]["1:ending"].update(copy.deepcopy(ending))
    media = SimpleNamespace(url=AsyncMock(return_value="https://owned.test/opening"))
    progress = await present_generation_progress(
        row, op, workspace_id=row.workspace_id, attempts=[], media=media
    )
    assert len(progress["groups"][0]["conditioningImages"]) == 1
    assert progress["groups"][0]["stage"] == "preparing_image"
    assert media.url.await_count == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "changed", [None, "old_task", "bad_range", "foreign_key", "different_hash"]
)
@pytest.mark.parametrize("frame_count", [192, 193])
async def test_video_preview_requires_current_task_and_all_exact_retained_group_ranges(
    changed,
    frame_count,
):
    from viraldy.modules.smart_remake.generation_progress import present_generation_progress

    row, op = fixture()
    attempt = video(row, op, status="completed")
    group = op.result_json["renderPlan"]["groups"][0]
    key = f"workspaces/{row.workspace_id}/smart-remake/{row.id}/{uuid4().hex}"
    for scene, segment in zip(row.state_json["scenes"], group["segments"], strict=False):
        scene["versions"] = [
            {
                "storageKey": key,
                "mediaHash": "a" * 64,
                "frameCount": frame_count,
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
    version = row.state_json["scenes"][0]["versions"][0]
    if changed == "old_task":
        version["providerMetadata"]["providerRequestId"] = "previous-task"
    elif changed == "bad_range":
        version["suggestedOutFrame"] += 1
    elif changed == "foreign_key":
        version["storageKey"] = "foreign/private/clip"
    elif changed == "different_hash":
        version["mediaHash"] = "b" * 64
    media = SimpleNamespace(url=AsyncMock(return_value="https://owned.test/clip.mp4"))
    progress = await present_generation_progress(
        row,
        op,
        workspace_id=row.workspace_id,
        attempts=[attempt],
        media=media,
    )
    assert (progress["groups"][0].get("videoUrl") == "https://owned.test/clip.mp4") is (
        changed is None
    )
    if changed is not None:
        media.url.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "condition",
    [
        "foreign_key",
        "traversal",
        "foreign_unit",
        "stale_expectations",
        "foreign_asset",
        "changed_opening",
        "not_completed",
        "presign_failure",
    ],
)
async def test_unbound_conditioning_images_never_expose_a_private_media_url(condition):
    from viraldy.modules.smart_remake.generation_progress import present_generation_progress

    row, op = fixture()
    asset = image(row, op)
    saved = op.result_json["images"]["0"]
    if condition == "foreign_key":
        asset["storageKey"] = f"workspaces/{uuid4()}/smart-remake/{row.id}/images/a"
    elif condition == "traversal":
        asset["storageKey"] += "/../private"
    elif condition == "foreign_unit":
        asset["renderUnitId"] = str(uuid4())
    elif condition == "stale_expectations":
        asset["expectationsHash"] = "bad"
    elif condition == "foreign_asset":
        row.context_json["imageAssets"] = {}
    elif condition == "changed_opening":
        asset["openingFrame"]["frame"] += 1
    elif condition == "not_completed":
        saved["status"] = "submitting"
    if condition not in {"foreign_asset", "not_completed"}:
        saved.update(copy.deepcopy(asset))
    media = SimpleNamespace(
        url=AsyncMock(
            side_effect=OSError("Unavailable")
            if condition == "presign_failure"
            else AssertionError("Do not sign an unbound key")
        )
    )
    value = await present_generation_progress(
        row, op, workspace_id=row.workspace_id, attempts=[], media=media
    )
    assert all("conditioningImageUrl" not in group for group in value["groups"])


def test_public_errors_and_report_links_are_allowlisted_and_do_not_read_raw_provider_text():
    row, op = fixture()
    asset = image(row, op)
    check(row, op, asset)
    report = row.context_json["p0"]["inspections"]["reports"][0]
    report["id"] = "https://private.test/token"
    op.status = "failed"
    op.result_json["errorCode"] = "private provider text https://secret.test"
    value = project(row, op)
    assert "inspectionReportId" not in value["groups"][0]
    assert "private" not in json.dumps(value) and "secret" not in json.dumps(value)


@pytest.mark.parametrize("phase,status", [
    ("completed", "insufficient_evidence"), ("completed", "needs_review"), ("unknown", "pending"),
])
def test_direct_reference_preparation_does_not_wait_on_legacy_image_inspection(phase, status):
    row, op = fixture()
    asset = image(row, op)
    image(row, op, 1)
    check(row, op, asset, phase, status)
    op.result_json["referencePreparation"] = "direct"
    groups = project(row, op)["groups"]
    assert [group["stage"] for group in groups] == ["submitting_video", "queued"]
    assert all(group["videoSubmitted"] is False for group in groups)


@pytest.mark.asyncio
async def test_project_get_projects_retained_progress_with_one_scoped_read_and_no_writes():
    from viraldy.modules.smart_remake.repair_service import RepairService

    row, op = fixture()
    image(row, op)
    session = SimpleNamespace(scalars=AsyncMock(return_value=[]), commit=AsyncMock())
    repository = SimpleNamespace(
        project=AsyncMock(return_value=row),
        running=AsyncMock(return_value=op),
        session=session,
    )
    media = SimpleNamespace(
        url=AsyncMock(return_value="https://owned.test/conditioning"),
        read=AsyncMock(side_effect=AssertionError("No storage fetch")),
    )
    service = RepairService(repository, media, row.workspace_id)
    service.present = AsyncMock(return_value={"id": str(row.id)})
    result = await service.get(row.id)
    assert result["generationProgress"]["groups"][0]["conditioningImages"]
    assert result["generationProgress"]["groups"][0]["videoSubmitted"] is False
    query = session.scalars.await_args.args[0]
    assert {row.id, row.workspace_id} <= set(query.compile().params.values())
    session.commit.assert_not_awaited()
    media.read.assert_not_awaited()
