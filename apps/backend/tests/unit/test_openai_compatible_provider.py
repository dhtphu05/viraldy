from __future__ import annotations

import json
from typing import Any, cast

import pytest
from pydantic import BaseModel, ConfigDict

from viraldy.modules.ai_gateway.providers.base import (
    InputTextPart,
    ProviderEndpointFamily,
    StructuredGenerationRequest,
)
from viraldy.modules.ai_gateway.providers.openai_compatible import (
    OpenAICompatibleStructuredProvider,
)
from viraldy.modules.ai_gateway.schemas import ProviderResponse
from viraldy.platform.config.settings import Settings


class _Output(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: str


class _FakeClient:
    def __init__(self, payloads: list[dict[str, object]]) -> None:
        self._payloads = list(payloads)
        self.requests: list[dict[str, Any]] = []

    def chat_json(self, payload: dict[str, Any]) -> ProviderResponse:
        self.requests.append(payload)
        response_payload = self._payloads.pop(0)
        return ProviderResponse(
            payload={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(response_payload),
                        }
                    }
                ],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 4,
                    "total_tokens": 14,
                },
            },
            http_status=200,
            provider_request_id="mock-provider-request",
            latency_ms=3,
        )


def _settings() -> Settings:
    return Settings(
        _env_file=None,
        ai_mode="mock",
        ai_provider="openai_compatible",
        ai_base_url="http://127.0.0.1:8787/v1",
        ai_api_key="mock-key",
        ai_text_model="mock-text",
    )


def _request() -> StructuredGenerationRequest:
    return StructuredGenerationRequest(
        operation="seller_decision_summary",
        model="mock-text",
        system_prompt="System grounding policy.",
        developer_prompt="Return the requested schema.",
        user_content=[InputTextPart(text='{"product":"Example"}')],
        output_model=_Output,
        prompt_version="test_prompt_v1",
        schema_version="test_schema_v1",
        request_id="test-request",
        input_hash="a" * 64,
        request_hash="b" * 64,
        max_repair_attempts=1,
    )


def test_mock_compatible_provider_validates_output_and_records_chat_family() -> None:
    client = _FakeClient([{"value": "grounded"}])
    provider = OpenAICompatibleStructuredProvider(
        _settings(),
        client=cast(Any, client),
    )

    result = provider.generate_structured(_request())

    assert result.parsed_output == _Output(value="grounded")
    assert result.provider == "openai_compatible"
    assert result.endpoint_family == ProviderEndpointFamily.CHAT_COMPLETIONS
    assert result.provider_request_id == "mock-provider-request"
    assert result.total_tokens == 14
    assert result.repair_attempt_count == 0
    assert result.input_hash == "a" * 64
    assert result.request_hash == "b" * 64
    assert client.requests[0]["response_format"]["type"] == "json_schema"


def test_mock_compatible_provider_repairs_once() -> None:
    client = _FakeClient([{"wrong": "shape"}, {"value": "repaired"}])
    provider = OpenAICompatibleStructuredProvider(
        _settings(),
        client=cast(Any, client),
    )

    result = provider.generate_structured(_request())

    assert result.parsed_output == _Output(value="repaired")
    assert result.repair_attempt_count == 1
    assert len(client.requests) == 2
    assert client.requests[1]["messages"][-1]["role"] == "user"


def test_mock_compatible_provider_cannot_be_used_for_live() -> None:
    with pytest.raises(ValueError, match="restricted to mock mode"):
        OpenAICompatibleStructuredProvider(
            Settings(
                _env_file=None,
                ai_mode="live",
                ai_provider="openai_compatible",
            )
        )
