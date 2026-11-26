# ruff: noqa: F811 -- pytest imports shared offline workflow fixtures by name.
"""Offline browser seams assert the same committed hashes as production workflows."""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from test_smart_remake_image_workflow import image, prepare, setup  # noqa: F401
from test_smart_remake_kie_workflow_unit import workflow  # noqa: F401

from tests.e2e import smart_remake_providers as seams
from viraldy.modules.smart_remake import image_workflow


@pytest.mark.asyncio
@pytest.mark.parametrize("frame_role", ["opening", "ending"])
@pytest.mark.parametrize("use_anchor", [False, True])
async def test_browser_image_seam_hash_matches_committed_production_image_request(
    setup, tmp_path, monkeypatch, frame_role, use_anchor,
):
    _, row, operation, _, scene, _, _ = setup
    row.context_json["renderPlan"].update(
        imageModel="gpt-image-2.6-sunburst", imageQuality="max", imageComplexity="high",
    )
    if use_anchor:
        row.context_json["referenceAnalysis"] = {"sourceShots": [
            {"startSecond": 2, "endSecond": 5, "subjectPresence": "person"},
        ]}
        await prepare(setup)
        scene["imagePrompt"] = "A different camera framing with the same observed physical state"
        operation.result_json = {}
    (tmp_path / "conditioning.png").write_bytes(image())
    log = tmp_path / "provider.jsonl"
    monkeypatch.setenv("P0_E2E_MEDIA", str(tmp_path))
    monkeypatch.setenv("P0_E2E_PROVIDER_LOG", str(log))
    attempt_id = str(uuid4())
    monkeypatch.setattr(image_workflow, "reserve_generation_attempt", AsyncMock(
        return_value=(SimpleNamespace(id=attempt_id), True),
    ))
    monkeypatch.setattr(image_workflow, "mark_generation_submitted", AsyncMock())
    monkeypatch.setattr(image_workflow, "settle_generation_attempt", AsyncMock())
    image_key = "0" if frame_role == "opening" else "0:ending"

    def committed_bindings(stage):
        assert stage == "image"
        return [{
            "requestHash": operation.result_json["images"][image_key]["requestHash"],
            "context": row.context_json, "result": operation.result_json,
            "attemptId": attempt_id,
        }]

    monkeypatch.setattr(seams, "_submitted_provider_bindings", committed_bindings)

    def assert_committed(stage, request_hash):
        intent = operation.result_json["images"][image_key]
        assert stage == "image" and intent["status"] == "submitting"
        assert request_hash == intent["requestHash"]
        return attempt_id

    monkeypatch.setattr(seams, "_assert_ledger", assert_committed)
    values = (*setup[:3], seams.OfflineImageClient(), *setup[4:])
    record = await prepare(values, frame_role=frame_role)
    logged = json.loads(log.read_text())
    assert logged["requestHash"] == record["requestHash"]
    assert record["expectationsHash"] == operation.result_json["expectationsHash"]


@pytest.mark.asyncio
@pytest.mark.parametrize("tamper", ["product", "layout", "character", "model", "hash"])
async def test_browser_image_seam_rejects_actual_inputs_different_from_committed_intent(
    setup, tmp_path, monkeypatch, tamper,
):
    from viraldy.modules.smart_remake.engine.schemas import UploadedMedia

    _, row, operation, client, _, _, _ = setup
    record = await prepare(setup)
    attempt_id = str(uuid4())
    operation.result_json["images"]["0"].update(status="submitting", attemptId=attempt_id)
    monkeypatch.setattr(seams, "_submitted_provider_bindings", lambda stage: [{
        "requestHash": "0" * 64 if tamper == "hash" else record["requestHash"],
        "context": row.context_json, "result": operation.result_json, "attemptId": attempt_id,
    }])
    ledger = AsyncMock()
    monkeypatch.setattr(seams, "_assert_ledger", ledger)
    log = tmp_path / "provider.jsonl"
    monkeypatch.setenv("P0_E2E_PROVIDER_LOG", str(log))
    request = {**client.calls[0]}
    if tamper in {"product", "layout", "character"}:
        request[tamper] = UploadedMedia(bytes=image(color="blue"), mime_type="image/png")
    elif tamper == "model":
        request["model"] = "gpt-image-2.6-sunburst"
    with pytest.raises(AssertionError, match="Offline image"):
        await seams.OfflineImageClient().edit(**request)
    assert ledger.call_count == 0 and not log.exists()


@pytest.mark.asyncio
@pytest.mark.parametrize("tamper", [None, "prompt", "frames"])
async def test_browser_kie_seam_hash_matches_committed_production_video_request(
    workflow, tmp_path, monkeypatch, tamper,
):
    runner, _, _, row, operation = workflow
    log, scenario = tmp_path / "provider.jsonl", tmp_path / "scenario.json"
    scenario.write_text(json.dumps({"name": "pass"}))
    monkeypatch.setenv("P0_E2E_PROVIDER_LOG", str(log))
    monkeypatch.setenv("P0_E2E_SCENARIO", str(scenario))
    attempt_id = str(uuid4())
    monkeypatch.setattr("viraldy.modules.smart_remake.kie_workflow.reserve_generation_attempt",
        AsyncMock(return_value=(SimpleNamespace(id=attempt_id), True)))
    monkeypatch.setattr("viraldy.modules.smart_remake.kie_workflow.mark_generation_submitted",
        AsyncMock())
    monkeypatch.setattr("viraldy.modules.smart_remake.kie_workflow.settle_generation_attempt",
        AsyncMock())

    def committed_bindings(stage):
        assert stage == "video"
        return [{
            "requestHash": operation.result_json["tasks"]["0"]["requestHash"],
            "context": row.context_json, "result": operation.result_json,
            "attemptId": attempt_id,
        }]

    monkeypatch.setattr(seams, "_submitted_provider_bindings", committed_bindings)

    def assert_committed(stage, request_hash):
        intent = operation.result_json["tasks"]["0"]
        assert stage == "video" and intent["status"] == "submitting"
        assert request_hash == intent["requestHash"]
        return attempt_id

    monkeypatch.setattr(seams, "_assert_ledger", assert_committed)
    runner.client = seams.OfflineKieClient()
    original_create = runner.client.create_task

    async def submit(**kwargs):
        if tamper == "prompt":
            kwargs["input_data"] = {**kwargs["input_data"], "prompt": "Unrelated video"}
        elif tamper == "frames":
            kwargs["input_data"] = {
                **kwargs["input_data"],
                "image_urls": list(reversed(kwargs["input_data"]["image_urls"])),
            }
        return await original_create(**kwargs)

    monkeypatch.setattr(runner.client, "create_task", submit)
    await runner._freeze_plan(row, operation)
    if tamper:
        from viraldy.shared.errors.base import AppError

        with pytest.raises(AppError, match="SMART_REMAKE_SUBMISSION_UNRESOLVED"):
            await runner._task(row, operation, 0, reconcile_only=False)
        assert not log.exists()
        return
    task = await runner._task(row, operation, 0, reconcile_only=False)
    logged = json.loads(log.read_text())
    assert task["requestHash"] == logged["requestHash"]
    assert task["expectationsHash"] == operation.result_json["expectationsHash"]
    assert task["expectationsHash"] not in logged["input"]["prompt"]
