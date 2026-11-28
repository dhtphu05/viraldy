"""Read-only native Veo receipt compatibility never submits a replacement task."""

import json
from contextlib import asynccontextmanager
from uuid import uuid4

import httpx
import pytest

from viraldy.modules.smart_remake import generation_budget, provider_execution
from viraldy.modules.smart_remake.engine import kie_client
from viraldy.modules.smart_remake.engine.errors import SmartRemakeError

TASK_ID = "native-task-1"
VIDEO_URL = "https://8.8.8.8/video.mp4"


def envelope(data, code=200, message="success"):
    return httpx.Response(200, json={"code": code, "msg": message, "data": data})


@pytest.mark.asyncio
@pytest.mark.parametrize("flag,status", [(0, "processing"), (1, "completed"),
                                         (2, "failed"), (3, "failed")])
async def test_native_status_uses_success_flag_and_existing_result_url(flag, status):
    calls = []

    def respond(request):
        calls.append(request)
        assert request.method == "GET" and request.url.path == "/api/v1/veo/record-info"
        assert request.url.params["taskId"] == TASK_ID
        return envelope({
            "taskId": TASK_ID, "successFlag": flag, "errorMessage": "Upstream failed",
            "response": {"resultUrls": [VIDEO_URL]}, "consumeCredits": 30,
        })

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as http:
        task = await kie_client.KieClient(api_key="test-key", http_client=http).get_task(TASK_ID)
    assert task["status"] == status and len(calls) == 1
    assert task["receipt"] == {"consumeCredits": 30}
    if flag == 1:
        assert task["output"]["video_url"] == VIDEO_URL
    elif flag in (2, 3):
        assert task["error_message"] == "Upstream failed"


@pytest.mark.asyncio
@pytest.mark.parametrize("native_response", [
    envelope({"taskId": TASK_ID, "state": "waiting"}),
    envelope(None, code=404, message="Task not found"),
    envelope(None, code=422, message="Task does not exist"),
])
async def test_existing_unified_task_is_reconciled_only_with_get_fallback(native_response):
    paths = []

    def respond(request):
        assert request.method == "GET"
        paths.append(request.url.path)
        if request.url.path == "/api/v1/veo/record-info":
            return native_response
        return envelope({"taskId": TASK_ID, "model": "veo-3-1", "state": "success",
                         "resultJson": json.dumps({"resultUrls": [VIDEO_URL]})})

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as http:
        task = await kie_client.KieClient(api_key="test-key", http_client=http).get_task(TASK_ID)
    assert task["status"] == "completed"
    assert paths == ["/api/v1/veo/record-info", "/api/v1/jobs/recordInfo"]


@pytest.mark.asyncio
@pytest.mark.parametrize("code", [401, 402, 403, 429, 500])
async def test_native_lookup_errors_do_not_fall_through_to_another_route(code):
    calls = []

    def respond(request):
        calls.append(request)
        return envelope(None, code=code, message="Provider refused request")

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as http:
        with pytest.raises(SmartRemakeError):
            await kie_client.KieClient(api_key="test-key", http_client=http).get_task(TASK_ID)
    assert len(calls) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [401, 402, 403, 429])
async def test_non_json_auth_and_rate_errors_never_trigger_legacy_lookup(status):
    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(status, text="Gateway error")

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as http:
        with pytest.raises(SmartRemakeError):
            await kie_client.KieClient(api_key="test-key", http_client=http).get_task(TASK_ID)
    assert len(calls) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("data", [
    {"taskId": "other", "successFlag": 0},
    {"taskId": TASK_ID, "successFlag": 0, "model": "other"},
    {"taskId": TASK_ID, "successFlag": 1, "response": {"resultUrls": []}},
])
async def test_recognized_native_task_with_wrong_binding_or_missing_output_fails_closed(data):
    calls = []

    def respond(request):
        calls.append(request)
        return envelope(data)

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as http:
        with pytest.raises(SmartRemakeError) as caught:
            await kie_client.KieClient(api_key="test-key", http_client=http).get_task(TASK_ID)
    assert caught.value.code == "KIE_INVALID_RESPONSE"
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_native_physical_status_response_binds_proof_to_canonical_model(monkeypatch):
    calls = []
    monkeypatch.setattr(provider_execution, "_verified_tls", lambda response, host: True)

    @asynccontextmanager
    async def owned_transport(self):
        def respond(request):
            calls.append(request)
            assert request.method == "GET"
            return envelope({"taskId": TASK_ID, "successFlag": 0})

        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as http:
            yield http

    monkeypatch.setattr(kie_client.KieClient, "_client", owned_transport)
    client = kie_client.KieClient(api_key="test-key")
    await client.get_task(TASK_ID)
    proof = generation_budget.generation_execution_receipt(
        client, attempt_id=str(uuid4()), request_hash="a" * 64, provider="kie",
        model="veo-3-1", operation="kie.tasks.get", task_id=TASK_ID,
    )
    assert proof["executionEvidence"]["model"] == "veo-3-1"
    assert proof["executionEvidence"]["operation"] == "kie.tasks.get"
    assert len(calls) == 1
