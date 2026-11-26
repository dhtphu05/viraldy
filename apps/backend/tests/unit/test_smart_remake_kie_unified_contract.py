"""Published KIE create contract, verified offline against a captured OpenAPI schema."""

import json
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from jsonschema import validate

from viraldy.modules.smart_remake import generation_budget, provider_execution
from viraldy.modules.smart_remake.engine import kie_client
from viraldy.modules.smart_remake.engine.errors import SmartRemakeError
from viraldy.modules.smart_remake.engine.kie_adapter import build_kie_video_request

SCHEMA = Path(__file__).parents[1] / "fixtures/smart_remake/kie_veo_unified_request_schema.json"


def canonical_input():
    return build_kie_video_request(
        scene={"videoPrompt": "Rotate the pink cup, then open the lid."},
        product_image_url="https://8.8.8.8/opening.png",
    )["input"]


@pytest.mark.asyncio
async def test_unified_sent_json_matches_published_schema_and_preserves_complete_input():
    snapshot = json.loads(SCHEMA.read_text())
    original = canonical_input()
    original["image_urls"].append("https://8.8.8.8/ending.png")
    before = json.loads(json.dumps(original))
    calls = []

    def respond(request):
        calls.append(request)
        assert request.method == snapshot["method"] == "POST"
        assert request.url.path == snapshot["path"] == "/api/v1/jobs/createTask"
        assert request.headers["authorization"] == "Bearer test-key"
        sent = json.loads(request.content)
        validate(sent, snapshot["requestSchema"])
        assert sent == {"model": "veo-3-1", "input": before}
        assert sent["input"]["generation_type"] == "FIRST_AND_LAST_FRAMES_2_VIDEO"
        assert sent["input"]["image_urls"] == [
            "https://8.8.8.8/opening.png", "https://8.8.8.8/ending.png",
        ]
        return httpx.Response(200, json={"code": 200, "data": {"taskId": "unified-task"}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as http:
        client = kie_client.KieClient(api_key="test-key", http_client=http)
        assert await client.create_task(input_data=original) == {
            "task_id": "unified-task", "status": "queued",
        }
        assert client.api_contract == "kie-unified-v1"
    assert original == before and len(calls) == 1


@pytest.mark.asyncio
async def test_unified_submit_failure_never_retries_or_falls_back_to_another_paid_route():
    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(200, json={"code": 500, "msg": "Server exception", "data": None})

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as http:
        with pytest.raises(SmartRemakeError) as caught:
            await kie_client.KieClient(api_key="test-key", http_client=http).create_task(
                input_data=canonical_input(),
            )
    assert caught.value.code == "KIE_SUBMISSION_UNCERTAIN" and len(calls) == 1
    assert calls[0].url.path == "/api/v1/jobs/createTask"


@pytest.mark.asyncio
async def test_unified_physical_create_response_binds_proof_to_canonical_model(monkeypatch):
    calls = []
    monkeypatch.setattr(provider_execution, "_verified_tls", lambda response, host: True)

    @asynccontextmanager
    async def owned_transport(self):
        def respond(request):
            calls.append(request)
            assert request.url.path == "/api/v1/jobs/createTask"
            return httpx.Response(200, json={"code": 200, "data": {"taskId": "unified-task"}})

        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as http:
            yield http

    monkeypatch.setattr(kie_client.KieClient, "_client", owned_transport)
    client = kie_client.KieClient(api_key="test-key")
    await client.create_task(input_data=canonical_input())
    proof = generation_budget.generation_execution_receipt(
        client, attempt_id=str(uuid4()), request_hash="a" * 64, provider="kie",
        model="veo-3-1", operation="kie.tasks.create", task_id="unified-task",
    )
    assert proof["executionEvidence"]["model"] == "veo-3-1"
    assert proof["executionEvidence"]["operation"] == "kie.tasks.create"
    assert len(calls) == 1
