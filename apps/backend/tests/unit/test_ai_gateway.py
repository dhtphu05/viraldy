from __future__ import annotations

import asyncio
import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

import viraldy.modules.adaptations.provider as adaptation_provider_module
import viraldy.modules.ai_gateway.http_client as http_client_module
from viraldy.modules.ai_gateway.http_client import OpenAICompatibleClient, extract_message_json
from viraldy.modules.ai_gateway.schemas import ProviderResponse
from viraldy.platform.config.settings import Settings
from viraldy.shared.errors.base import AppError


def _load_mock_provider() -> ModuleType:
    script = Path(__file__).parents[2] / "scripts" / "mock_openai_provider.py"
    spec = importlib.util.spec_from_file_location("mock_openai_provider", script)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load mock_openai_provider.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


mock_openai_provider = _load_mock_provider()


def test_mock_provider_supports_chat_failure_switches(monkeypatch: pytest.MonkeyPatch) -> None:
    client = TestClient(mock_openai_provider.app)

    monkeypatch.setenv("MOCK_AI_FAILURE", "429")
    response = client.post("/v1/chat/completions", headers=_headers(), json=_chat_payload())
    assert response.status_code == 429

    monkeypatch.setenv("MOCK_AI_FAILURE", "500")
    response = client.post("/v1/chat/completions", headers=_headers(), json=_chat_payload())
    assert response.status_code == 500

    monkeypatch.setenv("MOCK_AI_FAILURE", "malformed_json")
    response = client.post("/v1/chat/completions", headers=_headers(), json=_chat_payload())
    assert response.status_code == 200
    assert response.text == "{not-json"


def test_mock_provider_missing_field_breaks_adaptation_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = TestClient(mock_openai_provider.app)
    monkeypatch.setenv("MOCK_AI_FAILURE", "missing_field")

    response = client.post("/v1/chat/completions", headers=_headers(), json=_adaptation_payload())
    content = response.json()["choices"][0]["message"]["content"]

    with pytest.raises(AppError) as exc_info:
        adaptation_provider_module._validate(json.loads(content))

    assert exc_info.value.code == "ADAPTATION_OUTPUT_INVALID"
    assert "concepts" not in content


def test_gateway_maps_rate_limit_server_error_invalid_json_and_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(
        ai_mode="mock",
        ai_base_url="http://mock/v1",
        ai_text_model="mock-text",
        ai_max_retries=0,
    )

    monkeypatch.setattr(http_client_module.httpx, "Client", _client_factory([_response(429)]))
    with pytest.raises(AppError) as exc_info:
        OpenAICompatibleClient(settings).chat_json(_chat_payload())
    assert exc_info.value.code == "AI_PROVIDER_RATE_LIMITED"

    monkeypatch.setattr(http_client_module.httpx, "Client", _client_factory([_response(500)]))
    with pytest.raises(AppError) as exc_info:
        OpenAICompatibleClient(settings).chat_json(_chat_payload())
    assert exc_info.value.code == "AI_PROVIDER_FAILED"

    monkeypatch.setattr(http_client_module.httpx, "Client", _client_factory([_response(200, b"{")]))
    with pytest.raises(AppError) as exc_info:
        OpenAICompatibleClient(settings).chat_json(_chat_payload())
    assert exc_info.value.code == "MODEL_RESPONSE_INVALID"

    monkeypatch.setattr(
        http_client_module.httpx,
        "Client",
        _client_factory([httpx.TimeoutException("timeout")]),
    )
    with pytest.raises(AppError) as exc_info:
        OpenAICompatibleClient(settings).chat_json(_chat_payload())
    assert exc_info.value.code == "AI_PROVIDER_TIMEOUT"


def test_extract_message_json_rejects_malformed_content() -> None:
    response = ProviderResponse(
        payload={"choices": [{"message": {"content": "{bad-json"}}]},
        http_status=200,
        provider_request_id="req",
        latency_ms=1,
    )

    with pytest.raises(AppError) as exc_info:
        extract_message_json(response)

    assert exc_info.value.code == "MODEL_RESPONSE_INVALID"


@pytest.mark.asyncio
async def test_mock_provider_timeout_switch_is_cancellable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MOCK_AI_FAILURE", "timeout")
    task = asyncio.create_task(mock_openai_provider._maybe_fail())
    await asyncio.sleep(0)
    assert not task.done()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task


def _headers() -> dict[str, str]:
    return {"Authorization": "Bearer test"}


def _chat_payload() -> dict[str, Any]:
    return {
        "model": "mock",
        "messages": [{"role": "user", "content": "Extract readable on-screen text"}],
    }


def _adaptation_payload() -> dict[str, Any]:
    return {
        "model": "mock",
        "messages": [{"role": "user", "content": "Adapt this Creative DNA to the product"}],
    }


def _response(status_code: int, content: bytes = b'{"ok": true}') -> httpx.Response:
    return httpx.Response(status_code, content=content)


def _client_factory(items: list[httpx.Response | httpx.TimeoutException]):
    class FakeClient:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        def __enter__(self) -> FakeClient:
            return self

        def __exit__(self, *args: object) -> None:
            pass

        def post(self, *args: object, **kwargs: object) -> httpx.Response:
            item = items.pop(0)
            if isinstance(item, httpx.TimeoutException):
                raise item
            return item

    return FakeClient
