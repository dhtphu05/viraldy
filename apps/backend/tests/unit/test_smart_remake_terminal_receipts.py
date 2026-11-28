# ruff: noqa: F811 -- imported pytest fixture is resolved by name.
"""Terminal status proof comes from the physical poll, never provider JSON or a fake."""
from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest

from tests.unit.test_smart_remake_grouped_workflow import grouped  # noqa: F401
from viraldy.modules.smart_remake import kie_workflow, provider_execution
from viraldy.modules.smart_remake.engine import kie_client


@pytest.mark.asyncio
@pytest.mark.parametrize("model", ["veo-3-1", "wan/3-0-video"])
@pytest.mark.parametrize("state", ["success", "fail"])
async def test_real_terminal_poll_adds_separate_actual_model_get_witness(
    grouped, monkeypatch, model, state,
):
    value = grouped
    group = value.groups[0]
    task = {"taskId": "task-1", "attemptId": str(uuid4()), "requestHash": "a" * 64,
            "requestModel": model, "status": "submitted"}
    value.op.result_json["tasks"] = {f"group:{group['id']}": task}
    settled = AsyncMock()
    monkeypatch.setattr(kie_workflow, "settle_generation_attempt", settled)
    monkeypatch.setattr(provider_execution, "_verified_tls", lambda *_: True)
    real_client = httpx.AsyncClient

    def handle(request):
        if model == "wan/3-0-video":
            assert request.url.path == "/api/v1/jobs/recordInfo"
            body = {"taskId": "task-1", "model": model, "state": state,
                    "creditsConsumed": 0 if state == "fail" else 128,
                    "failCode": "500", "failMsg": "Internal Error",
                    "resultJson": '{"resultUrls":["https://1.1.1.1/output.mp4"]}'}
        else:
            assert request.url.path == "/api/v1/veo/record-info"
            body = {"taskId": "task-1", "model": "veo3_lite",
                    "successFlag": 1 if state == "success" else 2,
                    "errorCode": 500, "errorMessage": "Internal Error",
                    "response": {"resultUrls": ["https://1.1.1.1/output.mp4"]}}
        return httpx.Response(200, request=request, json={"code": 200, "data": body})

    monkeypatch.setattr(kie_client.httpx, "AsyncClient", lambda **kwargs: real_client(
        transport=httpx.MockTransport(handle), **kwargs,
    ))
    value.runner.client = kie_client.KieClient(api_key="test-key")
    if state == "fail":
        with pytest.raises(Exception) as error:
            await value.runner._task(value.row, value.op, 0, reconcile_only=True, group=group)
        assert error.value.code == "KIE_TASK_FAILED"
    else:
        await value.runner._task(value.row, value.op, 0, reconcile_only=True, group=group)
    receipt = settled.call_args.kwargs["receipt"]
    proof = receipt["terminalExecutionEvidence"]
    assert proof["operation"] == "kie.tasks.get"
    assert proof["model"] == model
    assert proof["requestHash"] == task["requestHash"]
    assert proof["taskId"] == task["taskId"]
    assert "executionEvidence" not in receipt


@pytest.mark.asyncio
async def test_injected_terminal_proof_is_removed_without_minting_a_witness(grouped, monkeypatch):
    value = grouped
    group = value.groups[0]
    value.op.result_json["tasks"] = {f"group:{group['id']}": {
        "taskId": "task-1", "attemptId": str(uuid4()), "requestHash": "a" * 64,
        "requestModel": "veo-3-1", "status": "submitted",
    }}
    settled = AsyncMock()
    monkeypatch.setattr(kie_workflow, "settle_generation_attempt", settled)

    async def injected(task_id):
        return {"status": "failed", "receipt": {
            "executionEvidence": {"forged": True},
            "terminalExecutionEvidence": {"forged": True}, "creditsConsumed": 0,
        }}

    value.client.get_task = injected
    with pytest.raises(Exception) as error:
        await value.runner._task(value.row, value.op, 0, reconcile_only=True, group=group)
    assert error.value.code == "KIE_TASK_FAILED"
    receipt = settled.call_args.kwargs["receipt"]
    assert "executionEvidence" not in receipt and "terminalExecutionEvidence" not in receipt
    assert receipt["creditsConsumed"] == 0
