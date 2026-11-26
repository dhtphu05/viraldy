from __future__ import annotations

import json
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest

from tests.unit.test_smart_remake_lifecycle_compile import compile_arguments, owned_compile
from tests.unit.test_smart_remake_unlimited_ledger import stored_ledger as _stored_ledger
from viraldy.modules.smart_remake import budgeted_analysis, timeline_compile
from viraldy.modules.smart_remake.engine import gemini_client
from viraldy.modules.smart_remake.engine.errors import SmartRemakeError
from viraldy.shared.errors.base import AppError, ConflictError

stored_ledger = _stored_ledger


@pytest.mark.asyncio
@pytest.mark.parametrize("text", ['{"partial":', '{"valid":true}'])
async def test_max_tokens_is_explicit_and_never_repairs_or_submits_again(monkeypatch, text):
    monkeypatch.setenv("GEMINI_API_KEY", "offline-test")
    calls = []
    original = httpx.AsyncClient

    def handle(request):
        calls.append(request)
        return httpx.Response(200, json={
            "responseId": "response-truncated",
            "usageMetadata": {"candidatesTokenCount": 8511, "thoughtsTokenCount": 7859},
            "candidates": [{"finishReason": "MAX_TOKENS",
                            "content": {"parts": [{"text": text}]}}],
        })

    monkeypatch.setattr(
        gemini_client.httpx, "AsyncClient",
        lambda **kwargs: original(transport=httpx.MockTransport(handle), **kwargs),
    )
    client = gemini_client.HttpGeminiClient(max_attempts=1, repair_json=True)
    with pytest.raises(SmartRemakeError) as rejected:
        await client.generate_json(system_instruction="JSON", prompt="Observe")
    assert rejected.value.code == "SMART_REMAKE_GEMINI_OUTPUT_TRUNCATED"
    assert client.last_finish_reason == "MAX_TOKENS"
    assert client.last_usage["thoughtsTokenCount"] == 7859
    assert client.last_request_id == "response-truncated"
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_finish_reason_is_allowlisted_and_cleared_on_next_request(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "offline-test")
    original = httpx.AsyncClient
    reasons = iter(["STOP", "https://private.example/secret", None])

    def handle(request):
        reason = next(reasons)
        return httpx.Response(200, json={"candidates": [{
            **({"finishReason": reason} if reason else {}),
            "content": {"parts": [{"text": '{"valid":true}'}]},
        }]})

    monkeypatch.setattr(
        gemini_client.httpx, "AsyncClient",
        lambda **kwargs: original(transport=httpx.MockTransport(handle), **kwargs),
    )
    client = gemini_client.HttpGeminiClient(max_attempts=1, repair_json=False)
    for expected in ("STOP", None, None):
        assert await client.generate_json(system_instruction="JSON", prompt="Observe")
        assert client.last_finish_reason == expected


@pytest.mark.asyncio
@pytest.mark.parametrize("cause", [
    "SMART_REMAKE_GEMINI_OUTPUT_TRUNCATED", "SMART_REMAKE_GEMINI_ERROR", "PRIVATE_MODEL_VALUE",
])
async def test_model_failure_diagnostic_preserves_unknown_receipt_and_replay_fence(
    stored_ledger, monkeypatch, cause,
):
    stored, calls = stored_ledger, []

    class Client:
        last_finish_reason = "MAX_TOKENS"
        last_usage = {"candidatesTokenCount": 8511}

        async def generate_json(self, **kwargs):
            calls.append(kwargs)
            raise SmartRemakeError("private model text https://private.example/key", cause)

    client = budgeted_analysis.LedgerGeminiClient(
        stored.session, stored.workspace, stored.project.id, uuid4(), None, client=Client(),
    )
    monkeypatch.setattr(client, "_project", AsyncMock(return_value=stored.project))
    monkeypatch.setattr(client, "_preflight", AsyncMock(return_value=stored.project))
    with pytest.raises(AppError) as failed:
        await client.generate_json(system_instruction="system", prompt="source")
    assert failed.value.code == "SMART_REMAKE_MODEL_ATTEMPT_UNCERTAIN"
    attempt = stored.rows[0]
    assert attempt.status == "unknown" and attempt.actual_usd is None
    assert attempt.usage_json == {"candidatesTokenCount": 8511}
    if cause.startswith("SMART_REMAKE_GEMINI_"):
        assert attempt.error_json["causeCode"] == cause
        assert failed.value.details["causeCode"] == cause
    else:
        assert "causeCode" not in attempt.error_json
    assert attempt.error_json["providerFinishReason"] == "MAX_TOKENS"
    assert "private" not in json.dumps(attempt.error_json)
    with pytest.raises(ConflictError) as replay:
        await client.generate_json(system_instruction="system", prompt="source")
    assert replay.value.code == "SMART_REMAKE_ATTEMPT_RECONCILIATION_REQUIRED"
    assert len(calls) == len(stored.rows) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("model,thinking", [("gemini-2.5-flash", 1024), ("other-model", None)])
async def test_owned_compile_bounds_thinking_in_actual_transport_and_ledger(
    monkeypatch, model, thinking,
):
    monkeypatch.setenv("SMART_REMAKE_GEMINI_MODEL", model)
    owned_compile(monkeypatch)
    monkeypatch.setattr(timeline_compile, "probe_media_bytes", lambda _: {
        "hasVideo": True, "durationSeconds": 8,
    })
    monkeypatch.setattr(timeline_compile, "measure_video_frames", lambda _: 192)
    monkeypatch.setattr(timeline_compile, "extract_source_excerpt", lambda source, **kwargs: source)
    captured = []

    async def analyze(**kwargs):
        captured.append(kwargs["gemini"])
        raise AppError("OFFLINE_CHECK_COMPLETE", "Stop before any provider call")

    monkeypatch.setattr(timeline_compile, "analyze_reference_video", analyze)
    with pytest.raises(AppError) as stopped:
        await timeline_compile.compile_timeline_request(**compile_arguments())
    assert stopped.value.code == "OFFLINE_CHECK_COMPLETE"
    client = captured[0]
    assert client.client.thinking_budget == thinking
    assert client.client.max_attempts == 1 and client.client.repair_json is False
    assert client.profile["maxOutputTokens"] == 16384
    assert client.profile.get("thinkingBudget") == thinking
    assert budgeted_analysis.PROFILE.get("thinkingBudget") is None
