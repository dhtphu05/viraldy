"""P0 model clients cannot hide additional charged requests behind one attempt."""

from unittest.mock import AsyncMock

import httpx
import pytest

from viraldy.modules.smart_remake.engine.errors import SmartRemakeError
from viraldy.modules.smart_remake.engine.gemini_client import HttpGeminiClient


@pytest.mark.asyncio
async def test_p0_invalid_json_is_not_resubmitted(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "offline-test-key")
    client = HttpGeminiClient(max_attempts=1, repair_json=False)
    request = AsyncMock(return_value="not JSON")
    monkeypatch.setattr(client, "_request_text", request)
    with pytest.raises(SmartRemakeError):
        await client.generate_json(system_instruction="JSON", prompt="Inspect")
    assert request.await_count == 1


@pytest.mark.asyncio
async def test_p0_transient_http_failure_is_not_resubmitted(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "offline-test-key")
    calls = []

    class FakeClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, *args, **kwargs):
            calls.append(kwargs)
            return httpx.Response(503, request=httpx.Request("POST", "https://example.test"))

    monkeypatch.setattr(httpx, "AsyncClient", FakeClient)
    client = HttpGeminiClient(max_attempts=1, repair_json=False)
    with pytest.raises(SmartRemakeError):
        await client.generate_json(system_instruction="JSON", prompt="Inspect")
    assert len(calls) == 1
