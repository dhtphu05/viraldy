# ruff: noqa: F811 -- pytest imports shared offline workflow fixtures by name.
"""Offline browser seams assert the same committed hashes as production workflows."""

from __future__ import annotations

import json

import pytest
from test_smart_remake_image_workflow import image, prepare, setup  # noqa: F401
from test_smart_remake_kie_workflow_unit import workflow  # noqa: F401

from tests.e2e import smart_remake_providers as seams


@pytest.mark.asyncio
async def test_browser_image_seam_hash_matches_committed_production_image_request(
    setup, tmp_path, monkeypatch,
):
    _, row, operation, _, _, _, _ = setup
    row.context_json["renderPlan"].update(
        imageModel="gpt-image-2.6-sunburst", imageQuality="max", imageComplexity="high",
    )
    (tmp_path / "conditioning.png").write_bytes(image())
    log = tmp_path / "provider.jsonl"
    monkeypatch.setenv("P0_E2E_MEDIA", str(tmp_path))
    monkeypatch.setenv("P0_E2E_PROVIDER_LOG", str(log))

    def assert_committed(stage, request_hash):
        intent = operation.result_json["images"]["0"]
        assert stage == "image" and intent["status"] == "submitting"
        assert request_hash == intent["requestHash"]
        return "committed-image-attempt"

    monkeypatch.setattr(seams, "_assert_ledger", assert_committed)
    values = (*setup[:3], seams.OfflineImageClient(), *setup[4:])
    record = await prepare(values)
    logged = json.loads(log.read_text())
    assert logged["requestHash"] == record["requestHash"]
    assert record["expectationsHash"] == operation.result_json["expectationsHash"]


@pytest.mark.asyncio
async def test_browser_kie_seam_hash_matches_committed_production_video_request(
    workflow, tmp_path, monkeypatch,
):
    runner, _, _, row, operation = workflow
    log, scenario = tmp_path / "provider.jsonl", tmp_path / "scenario.json"
    scenario.write_text(json.dumps({"name": "pass"}))
    monkeypatch.setenv("P0_E2E_PROVIDER_LOG", str(log))
    monkeypatch.setenv("P0_E2E_SCENARIO", str(scenario))

    def assert_committed(stage, request_hash):
        intent = operation.result_json["tasks"]["0"]
        assert stage == "video" and intent["status"] == "submitting"
        assert request_hash == intent["requestHash"]
        return "committed-video-attempt"

    monkeypatch.setattr(seams, "_assert_ledger", assert_committed)
    runner.client = seams.OfflineKieClient()
    await runner._freeze_plan(row, operation)
    task = await runner._task(row, operation, 0, reconcile_only=False)
    logged = json.loads(log.read_text())
    assert task["requestHash"] == logged["requestHash"]
    assert task["expectationsHash"] == operation.result_json["expectationsHash"]
