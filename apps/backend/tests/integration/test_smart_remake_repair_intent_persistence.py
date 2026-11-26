"""Real ledger and retained-media repair, with all provider traffic replaced offline."""

from __future__ import annotations

import asyncio
import json
from uuid import UUID

import pytest
from sqlalchemy import select

from tests.integration import test_smart_remake_kie_workflow as workflow_fixture
from viraldy.modules.jobs.models import ProcessingJobModel
from viraldy.modules.smart_remake import kie_workflow, repair_intent_workflow
from viraldy.modules.smart_remake.budget_models import SmartRemakeAttemptModel
from viraldy.modules.smart_remake.budgeted_analysis import LedgerGeminiClient
from viraldy.modules.smart_remake.models import SmartRemakeOperationModel
from viraldy.modules.smart_remake.repair_schemas import RepairSceneRequest
from viraldy.shared.errors.base import AppError

kie_database_url = workflow_fixture.kie_database_url
vertical_clips = workflow_fixture.vertical_clips
harness = workflow_fixture.harness


@pytest.mark.parametrize("outcome", ["accepted", "conflict"])
def test_structured_repair_uses_one_analysis_and_recovers_saved_normalization(
    harness, monkeypatch, outcome
):
    monkeypatch.setenv("SMART_REMAKE_P0_MAX_ANALYSIS_USD", "0.10")
    response = asyncio.run(harness.enqueue())
    harness.run_job(asyncio.run(harness.job(response["processingJobId"])))
    before = asyncio.run(harness.project(response["repairProjectId"]))
    scene = before.state_json["scenes"][1]
    calls = []

    class Model:
        async def generate_json(self, **kwargs):
            calls.append(kwargs)
            payload = json.loads(kwargs["prompt"])
            assert len(kwargs["media"]) == 3
            assert payload["evidence"]["versionId"] == scene["activeVersionId"]
            if outcome == "conflict":
                return {"status": "conflict", "reason": "Giữ nguyên nhận diện sản phẩm."}
            return {
                "status": "accepted",
                "reason": "Giữ đúng sản phẩm và khung mở đầu.",
                "scenePatch": {
                    "prompt": "Orbit the exact seller product",
                    "imagePrompt": "The exact seller product in its source opening",
                    "videoPrompt": "Orbit smoothly around the exact seller product",
                    "shots": [],
                },
            }

    model = Model()

    def ledger(*args, **kwargs):
        kwargs["client"] = model
        return LedgerGeminiClient(*args, **kwargs)

    monkeypatch.setattr(repair_intent_workflow, "LedgerGeminiClient", ledger)
    request = RepairSceneRequest(
        expectedRevision=before.state_json["revision"],
        baseVersionId=scene["activeVersionId"],
        repairIntent={"issues": ["presentation"], "instruction": "Camera orbit"},
        idempotencyKey="structured-exact-request",
    )

    async def enqueue():
        async with harness.sessions() as factory, factory() as session:
            result = await kie_workflow.enqueue_kie_repair(
                session,
                harness.settings,
                harness.workspace_id,
                before.id,
                UUID(scene["id"]),
                request,
                actor_id=harness.actor_id,
            )
            job = await session.scalar(
                select(ProcessingJobModel).where(
                    ProcessingJobModel.idempotency_key == f"repair:{result['operationId']}"
                )
            )
            return job

    job = asyncio.run(enqueue())
    if outcome == "accepted":
        original_task = kie_workflow.KieWorkflow._task
        interrupted = []

        async def stop_after_normalization(self, row, operation, index, **kwargs):
            if not interrupted:
                interrupted.append(True)
                raise AppError("JOB_ATTEMPT_SUPERSEDED", "Offline worker interruption", 409)
            return await original_task(self, row, operation, index, **kwargs)

        monkeypatch.setattr(kie_workflow.KieWorkflow, "_task", stop_after_normalization)
        with pytest.raises(AppError, match="JOB_ATTEMPT_SUPERSEDED"):
            harness.run_job(job)
        assert harness.run_job(job)["status"] == "completed"
        assert harness.run_job(job)["status"] == "completed"
    else:
        with pytest.raises(AppError, match="SMART_REMAKE_REPAIR_INTENT_REJECTED"):
            harness.run_job(job)
        assert harness.run_job(job)["status"] == "failed"
    assert len(calls) == 1
    assert len(harness.client.creates) == (3 if outcome == "accepted" else 2)

    async def retained():
        async with harness.sessions() as factory, factory() as session:
            operation = await session.get(
                SmartRemakeOperationModel, UUID(job.input_json["operation_id"])
            )
            attempts = (
                await session.scalars(
                    select(SmartRemakeAttemptModel).where(
                        SmartRemakeAttemptModel.project_id == before.id,
                        SmartRemakeAttemptModel.stage == "analysis",
                    )
                )
            ).all()
            assert len(attempts) == 1 and attempts[0].purpose == "repair"
            assert attempts[0].status == "completed"
            assert operation.result_json["request"] == request.model_dump(
                mode="json", exclude={"idempotencyKey"}
            )
            assert operation.result_json["repairNormalization"]["phase"] == "resolved"
            if outcome == "accepted":
                row = await harness.service(
                    session, harness.settings, harness.workspace_id
                ).repository.project(harness.workspace_id, before.id)
                candidate = row.state_json["scenes"][1]["versions"][-1]
                assert candidate["videoPrompt"] == "Orbit smoothly around the exact seller product"
                assert candidate["expectationsHash"] == operation.result_json["expectationsHash"]
                assert row.state_json["scenes"][1]["activeVersionId"] == scene["activeVersionId"]

    asyncio.run(retained())
