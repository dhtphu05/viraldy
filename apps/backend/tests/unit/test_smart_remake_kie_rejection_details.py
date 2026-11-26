"""Retain actionable provider rejections without exposing credentials or resubmitting."""

import httpx
import pytest

from tests.unit.test_smart_remake_kie_workflow_unit import workflow as workflow_fixture
from viraldy.modules.smart_remake.engine.errors import SmartRemakeError
from viraldy.modules.smart_remake.engine.kie_adapter import build_kie_video_request
from viraldy.modules.smart_remake.engine.kie_client import KieClient
from viraldy.shared.errors.base import AppError


@pytest.fixture(name="workflow")
def setup_workflow(monkeypatch):
    return workflow_fixture.__wrapped__(monkeypatch)


@pytest.mark.asyncio
async def test_kie_rejection_retains_reason_and_redacts_authorization_and_urls():
    calls = []

    def rejected(request):
        calls.append(request)
        return httpx.Response(200, json={
            "code": 422,
            "msg": "prompt is too long; Bearer test-key "
            "https://provider.test/debug?token=private-query",
            "data": None,
        })

    async with httpx.AsyncClient(transport=httpx.MockTransport(rejected)) as http:
        client = KieClient(api_key="test-key", http_client=http)
        with pytest.raises(SmartRemakeError) as caught:
            await client.create_task(input_data=build_kie_video_request(
                scene={"videoPrompt": "A cup on a table."},
                product_image_url="https://8.8.8.8/image.png",
            )["input"])
    assert len(calls) == 1
    assert caught.value.code == "KIE_VALIDATION_FAILED"
    assert caught.value.details["providerCode"] == 422
    assert "prompt is too long" in caught.value.details["providerMessage"]
    assert "test-key" not in str(caught.value.details)
    assert "private-query" not in str(caught.value.details)


@pytest.mark.asyncio
async def test_worker_keeps_rejected_request_reason_and_never_replays_failed_task(workflow):
    runner, repair, client, row, operation = workflow
    calls = []

    async def rejected(**kwargs):
        calls.append(kwargs)
        raise SmartRemakeError("Rejected", "KIE_VALIDATION_FAILED", {
            "status": 200, "providerCode": 422, "providerMessage": "prompt is too long",
        })

    client.create_task = rejected
    with pytest.raises(AppError):
        await runner.execute(row.id, operation.id)
    assert operation.result_json["tasks"]["0"]["status"] == "rejected"
    assert operation.result_json["providerError"] == {
        "httpStatus": 200, "providerCode": 422, "providerMessage": "prompt is too long",
    }
    assert (await runner.execute(row.id, operation.id))["status"] == "failed"
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_uncertain_response_keeps_sanitized_provider_reason_without_retry():
    calls = []

    def unavailable(request):
        calls.append(request)
        return httpx.Response(200, json={
            "code": 500, "msg": "Upstream unavailable; test-key", "data": None,
        })

    async with httpx.AsyncClient(transport=httpx.MockTransport(unavailable)) as http:
        with pytest.raises(SmartRemakeError) as caught:
            await KieClient(api_key="test-key", http_client=http).create_task(
                input_data=build_kie_video_request(
                    scene={"videoPrompt": "A cup on a table."},
                    product_image_url="https://8.8.8.8/image.png",
                )["input"],
            )
    assert len(calls) == 1
    assert caught.value.code == "KIE_SUBMISSION_UNCERTAIN"
    details = caught.value.details["providerError"]
    assert details["providerCode"] == 500
    assert "Upstream unavailable" in details["providerMessage"]
    assert "test-key" not in str(details)


@pytest.mark.asyncio
async def test_unknown_worker_receipt_keeps_response_details_and_never_submits_again(workflow):
    runner, repair, client, row, operation = workflow
    calls = []

    async def uncertain(**kwargs):
        calls.append(kwargs)
        raise SmartRemakeError("Uncertain", "KIE_SUBMISSION_UNCERTAIN", {
            "submissionUncertain": True, "providerError": {
                "status": 200, "providerCode": 500, "providerMessage": "Upstream unavailable",
            },
        })

    client.create_task = uncertain
    for _ in range(2):
        with pytest.raises(AppError):
            await runner.execute(row.id, operation.id)
    assert operation.result_json["needsReconciliation"] is True
    assert operation.result_json["providerError"]["providerMessage"] == "Upstream unavailable"
    assert len(calls) == 1
