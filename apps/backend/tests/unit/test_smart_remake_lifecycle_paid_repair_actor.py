# ruff: noqa: F811 -- pytest imports the shared offline fixture by name.
from __future__ import annotations

import copy
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from pydantic import SecretStr
from test_smart_remake_kie_workflow_unit import workflow  # noqa: F401

from viraldy.modules.smart_remake import kie_workflow, service
from viraldy.modules.smart_remake.repair_schemas import RepairSceneRequest


@pytest.mark.asyncio
async def test_queued_repair_binds_actor_to_manifest_and_idempotency(workflow, monkeypatch):
    _, repair, _, row, operation = workflow
    row.state_json["revision"] = 1
    base_id = uuid4()
    row.state_json["scenes"][0].update(
        activeVersionId=str(base_id),
        versions=[{"id": str(base_id), "videoUrl": "https://media.test/base.mp4"}],
    )
    repository = repair.repository
    hashes, manifests = [], []

    async def start(workspace, project, key, request_hash):
        hashes.append(request_hash)
        return row, operation, True

    async def present(project, operation):
        return copy.deepcopy(operation.result_json)

    repository.start = start
    repository.attach_processing_job = AsyncMock()
    repair._operation_result = present
    monkeypatch.setattr(service, "require_kie_renderer", lambda _: None)
    monkeypatch.setattr(kie_workflow, "_service", lambda *args: repair)
    monkeypatch.setattr(kie_workflow, "validate_sanitized_compiler_prompts", lambda **kwargs: None)
    monkeypatch.setattr(kie_workflow, "_dispatch", AsyncMock())
    monkeypatch.setattr(
        kie_workflow,
        "JobService",
        lambda _: SimpleNamespace(
            request_mvp_job=AsyncMock(return_value=SimpleNamespace(id=uuid4()))
        ),
    )
    request = RepairSceneRequest(
        baseVersionId=base_id,
        expectedRevision=1,
        idempotencyKey="repair-same-key",
        prompt="Demo",
        imagePrompt="Opening frame",
        videoPrompt="Show cup",
    )
    for actor in (uuid4(), uuid4()):
        result = await kie_workflow.enqueue_kie_repair(
            object(),
            SimpleNamespace(ai_mode="live", openai_api_key=SecretStr("offline-test-key")),
            row.workspace_id,
            row.id,
            UUID(row.state_json["scenes"][0]["id"]),
            request,
            actor_id=actor,
        )
        assert result["actorId"] == str(actor)
        manifests.append(result)
    assert hashes[0] != hashes[1]
    assert manifests[0]["kind"] == manifests[1]["kind"] == "repair"
