from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import pytest
from openai import OpenAI
from pydantic import BaseModel, ConfigDict

import viraldy.modules.ai_gateway.providers.openai_native as openai_native_module
from viraldy.modules.ai_gateway.providers import (
    AiProviderError,
    AudioTranscriptionRequest,
    InputImagePart,
    InputTextPart,
    OpenAINativeProvider,
    ProviderErrorCode,
    StructuredGenerationRequest,
    build_ai_provider,
    provider_route,
)
from viraldy.platform.config.settings import Settings


class SampleOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer: str


def test_responses_api_uses_strict_schema_roles_images_and_usage() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return _response_http('{"answer":"evidence grounded"}')

    result = _provider(handler).generate_structured(_generation_request(include_image=True))

    assert len(captured) == 1
    request = captured[0]
    body = json.loads(request.content)
    assert request.url.path == "/v1/responses"
    assert [item["role"] for item in body["input"]] == ["system", "developer", "user"]
    assert body["input"][0]["content"][0]["text"] == "system policy"
    assert body["input"][1]["content"][0]["text"] == "operation rules"
    assert body["input"][2]["content"][1] == {
        "type": "input_image",
        "image_url": "data:image/jpeg;base64,aW1hZ2U=",
        "detail": "high",
    }
    assert body["text"]["format"]["type"] == "json_schema"
    assert body["text"]["format"]["strict"] is True
    assert body["text"]["format"]["schema"]["additionalProperties"] is False
    assert body["store"] is False
    assert body["reasoning"] == {"effort": "medium"}
    assert body["max_output_tokens"] == 321
    assert request.headers["x-client-request-id"] == "client-request-id"
    assert request.headers["idempotency-key"] == "idempotency-key"

    assert result.parsed_output == SampleOutput(answer="evidence grounded")
    assert result.provider_request_id == "provider-request-id"
    assert result.http_status == 200
    assert result.response_status == "completed"
    assert result.input_tokens == 12
    assert result.output_tokens == 5
    assert result.total_tokens == 17
    assert result.cached_input_tokens == 4
    assert result.repair_attempt_count == 0


def test_responses_api_uses_configured_reasoning_and_token_defaults() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return _response_http('{"answer":"configured defaults"}')

    request = _generation_request().model_copy(
        update={"reasoning_effort": None, "max_output_tokens": None}
    )
    result = _provider(handler).generate_structured(request)
    body = json.loads(captured[0].content)

    assert body["reasoning"] == {"effort": "medium"}
    assert body["max_output_tokens"] == 16000
    assert result.parsed_output == SampleOutput(answer="configured defaults")


def test_responses_api_allows_exactly_one_repair_attempt() -> None:
    captured_bodies: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_bodies.append(json.loads(request.content))
        return _response_http('{"wrong":"field"}')

    with pytest.raises(AiProviderError) as exc_info:
        _provider(handler).generate_structured(_generation_request())

    assert exc_info.value.code == ProviderErrorCode.OUTPUT_INVALID.value
    assert exc_info.value.info.repair_attempt_count == 1
    assert exc_info.value.info.http_status == 200
    assert exc_info.value.info.provider_request_id == "provider-request-id"
    assert len(captured_bodies) == 2
    assert len(captured_bodies[0]["input"]) == 3
    assert [item["role"] for item in captured_bodies[1]["input"][-2:]] == [
        "developer",
        "user",
    ]
    assert "OPENAI_OUTPUT_INVALID" in captured_bodies[1]["input"][-1]["content"][0]["text"]


def test_domain_validation_uses_one_repair_then_fails_with_domain_code() -> None:
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return _response_http('{"answer":"schema-valid but unsupported"}')

    def reject_output(output: BaseModel) -> None:
        raise ValueError("private domain detail must not reach provider errors")

    request = _generation_request().model_copy(update={"output_validator": reject_output})
    with pytest.raises(AiProviderError) as exc_info:
        _provider(handler).generate_structured(request)

    assert call_count == 2
    assert exc_info.value.code == ProviderErrorCode.DOMAIN_VALIDATION_FAILED.value
    assert "private domain detail" not in str(exc_info.value)


@pytest.mark.parametrize("status", ["incomplete", "failed", "cancelled"])
def test_non_completed_response_statuses_fail_safely(status: str) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return _response_http(None, status=status)

    with pytest.raises(AiProviderError) as exc_info:
        _provider(handler).generate_structured(_generation_request())

    assert exc_info.value.code == ProviderErrorCode.INCOMPLETE.value
    assert exc_info.value.info.response_status == status
    if status == "incomplete":
        assert exc_info.value.info.incomplete_reason == "max_output_tokens"
    assert "provider failure detail" not in str(exc_info.value)


def test_refusal_is_not_treated_as_structured_output() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return _response_http(None, refusal="private provider refusal")

    with pytest.raises(AiProviderError) as exc_info:
        _provider(handler).generate_structured(_generation_request())

    assert exc_info.value.code == ProviderErrorCode.REFUSED.value
    assert "private provider refusal" not in str(exc_info.value)


@pytest.mark.parametrize(
    ("status_code", "error_code", "expected_code"),
    [
        (401, "invalid_api_key", ProviderErrorCode.UNAUTHORIZED),
        (400, "model_not_found", ProviderErrorCode.MODEL_NOT_AVAILABLE),
        (404, "model_not_found", ProviderErrorCode.MODEL_NOT_AVAILABLE),
        (429, "rate_limit_exceeded", ProviderErrorCode.RATE_LIMITED),
    ],
)
def test_api_status_errors_are_normalized_without_secret_leakage(
    status_code: int,
    error_code: str,
    expected_code: ProviderErrorCode,
) -> None:
    sensitive_value = "sensitive-provider-value-never-log"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code,
            json={
                "error": {
                    "message": f"provider detail containing {sensitive_value}",
                    "type": "provider_error",
                    "code": error_code,
                }
            },
            headers={"x-request-id": "failed-provider-request-id"},
        )

    with pytest.raises(AiProviderError) as exc_info:
        _provider(handler).generate_structured(_generation_request())

    assert exc_info.value.code == expected_code.value
    assert exc_info.value.info.provider_request_id == "failed-provider-request-id"
    if expected_code is ProviderErrorCode.MODEL_NOT_AVAILABLE:
        assert "media_observation" in exc_info.value.safe_message
        assert "OPENAI_MODEL_MEDIA_OBSERVATION" in exc_info.value.safe_message
    serialized = f"{exc_info.value!s} {exc_info.value!r} {exc_info.value.info.model_dump_json()}"
    assert sensitive_value not in serialized


@pytest.mark.parametrize("failure", ["rate_limit", "server_error", "timeout"])
def test_sdk_retries_transient_failures_without_provider_fallback(failure: str) -> None:
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        if call_count == 1 and failure == "rate_limit":
            return httpx.Response(
                429,
                json={"error": {"message": "retry", "type": "rate_limit", "code": None}},
                headers={"retry-after": "0"},
            )
        if call_count == 1 and failure == "server_error":
            return httpx.Response(
                500,
                json={"error": {"message": "retry", "type": "server_error", "code": None}},
            )
        if call_count == 1:
            raise httpx.ReadTimeout("mock timeout", request=request)
        return _response_http('{"answer":"retried"}')

    client = _openai_client(handler, max_retries=1)
    provider = OpenAINativeProvider(_settings(), client=client)
    result = provider.generate_structured(_generation_request())

    assert call_count == 2
    assert result.parsed_output == SampleOutput(answer="retried")


def test_exhausted_timeout_is_normalized() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("mock timeout", request=request)

    with pytest.raises(AiProviderError) as exc_info:
        _provider(handler).generate_structured(_generation_request())

    assert exc_info.value.code == ProviderErrorCode.TIMEOUT.value
    assert exc_info.value.info.retryable is True


def test_audio_transcription_requests_verbose_json_timestamps(
    tmp_path: Path,
) -> None:
    audio_path = tmp_path / "sample.wav"
    audio_path.write_bytes(b"RIFF-mocked-audio")
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(
            200,
            json={
                "duration": 1.25,
                "language": "en",
                "text": "Evidence aligned.",
                "segments": [
                    {
                        "id": 0,
                        "avg_logprob": -0.1,
                        "compression_ratio": 1.0,
                        "end": 1.25,
                        "no_speech_prob": 0.01,
                        "seek": 0,
                        "start": 0.0,
                        "temperature": 0.0,
                        "text": " Evidence aligned. ",
                        "tokens": [1, 2],
                    }
                ],
            },
            headers={"x-request-id": "audio-provider-request-id"},
        )

    result = _provider(handler).transcribe_audio(
        AudioTranscriptionRequest(
            audio_path=audio_path,
            model="whisper-1",
            request_id="audio-client-request-id",
            input_hash="audio-input-hash",
            language="en",
            prompt="Product names only.",
        )
    )

    assert len(captured) == 1
    request = captured[0]
    multipart = request.content.decode("latin1")
    assert request.url.path == "/v1/audio/transcriptions"
    assert request.headers["x-client-request-id"] == "audio-client-request-id"
    assert 'name="model"' in multipart and "whisper-1" in multipart
    assert 'name="response_format"' in multipart and "verbose_json" in multipart
    assert 'name="timestamp_granularities[]"' in multipart and "segment" in multipart
    assert result.provider_request_id == "audio-provider-request-id"
    assert result.language == "en"
    assert result.duration_ms == 1250
    assert result.full_text == "Evidence aligned."
    assert result.segments[0].start_ms == 0
    assert result.segments[0].end_ms == 1250
    assert result.segments[0].text == "Evidence aligned."


def test_empty_audio_is_rejected_before_provider_request(tmp_path: Path) -> None:
    audio_path = tmp_path / "silent.wav"
    audio_path.touch()
    called = False

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal called
        called = True
        return httpx.Response(500)

    with pytest.raises(AiProviderError) as exc_info:
        _provider(handler).transcribe_audio(
            AudioTranscriptionRequest(
                audio_path=audio_path,
                model="whisper-1",
                request_id="audio-request-id",
                input_hash="empty-audio-hash",
            )
        )

    assert exc_info.value.code == ProviderErrorCode.EVIDENCE_INVALID.value
    assert called is False


def test_native_client_configuration_and_router_never_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}
    sentinel_client = object()

    def fake_openai(**kwargs: Any) -> Any:
        captured.update(kwargs)
        return sentinel_client

    monkeypatch.setattr(openai_native_module, "OpenAI", fake_openai)
    settings = _settings(
        ai_mode="live",
        ai_provider="openai",
        openai_api_key="test-client-secret",
        openai_request_timeout_seconds=42,
        openai_max_retries=1,
    )
    provider = OpenAINativeProvider(settings)

    assert provider._client is sentinel_client
    assert captured["api_key"] == "test-client-secret"
    assert captured["base_url"] == "https://api.openai.com/v1"
    assert captured["timeout"] == 42
    assert captured["max_retries"] == 1
    assert "test-client-secret" not in repr(provider)

    fallback_called = False

    def fixture_factory(factory_settings: Settings) -> Any:
        nonlocal fallback_called
        fallback_called = True
        return provider

    routed = build_ai_provider(
        settings,
        factories={"fixture": fixture_factory},
        openai_client=sentinel_client,  # type: ignore[arg-type]
    )
    assert isinstance(routed, OpenAINativeProvider)
    assert fallback_called is False


def test_provider_route_is_explicit_and_missing_key_error_is_safe() -> None:
    assert provider_route(_settings(ai_mode="fixture")) == "fixture"
    assert provider_route(_settings(ai_mode="mock")) == "mock"
    assert provider_route(_settings(ai_mode="live", ai_provider="openai")) == "openai"

    with pytest.raises(AiProviderError) as exc_info:
        OpenAINativeProvider(Settings(_env_file=None))
    assert exc_info.value.code == ProviderErrorCode.NOT_CONFIGURED.value
    assert "OPENAI_API_KEY" in exc_info.value.safe_message


def _provider(
    handler: Callable[[httpx.Request], httpx.Response],
    *,
    max_retries: int = 0,
) -> OpenAINativeProvider:
    return OpenAINativeProvider(
        _settings(),
        client=_openai_client(handler, max_retries=max_retries),
    )


def _openai_client(
    handler: Callable[[httpx.Request], httpx.Response],
    *,
    max_retries: int,
) -> OpenAI:
    return OpenAI(
        api_key="-".join(("test", "sdk", "key")),
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        max_retries=max_retries,
    )


def _settings(**overrides: Any) -> Settings:
    values = {"openai_api_key": "test-settings-key", **overrides}
    return Settings(_env_file=None, **values)


def _generation_request(*, include_image: bool = False) -> StructuredGenerationRequest:
    user_content: list[InputTextPart | InputImagePart] = [
        InputTextPart(text='{"product":"SwiftPress"}')
    ]
    if include_image:
        user_content.append(
            InputImagePart(
                media_type="image/jpeg",
                image_base64="aW1hZ2U=",
                detail="high",
            )
        )
    return StructuredGenerationRequest(
        operation="media_observation",
        model="gpt-5",
        system_prompt="system policy",
        developer_prompt="operation rules",
        user_content=user_content,
        output_model=SampleOutput,
        prompt_version="media_observation_v2",
        schema_version="sample_v1",
        reasoning_effort="medium",
        max_output_tokens=321,
        request_id="client-request-id",
        input_hash="input-hash",
        idempotency_key="idempotency-key",
    )


def _response_http(
    output_text: str | None,
    *,
    status: str = "completed",
    refusal: str | None = None,
) -> httpx.Response:
    content: list[dict[str, object]]
    if refusal is not None:
        content = [{"type": "refusal", "refusal": refusal}]
    elif output_text is not None:
        content = [{"type": "output_text", "text": output_text, "annotations": []}]
    else:
        content = []
    incomplete_details = {"reason": "max_output_tokens"} if status == "incomplete" else None
    return httpx.Response(
        200,
        json={
            "id": "response-id",
            "object": "response",
            "created_at": 0,
            "status": status,
            "error": None,
            "incomplete_details": incomplete_details,
            "instructions": None,
            "model": "gpt-5",
            "output": [
                {
                    "id": "message-id",
                    "type": "message",
                    "status": "completed" if status == "completed" else "incomplete",
                    "role": "assistant",
                    "content": content,
                }
            ],
            "parallel_tool_calls": True,
            "tool_choice": "auto",
            "tools": [],
            "temperature": None,
            "top_p": 1.0,
            "usage": {
                "input_tokens": 12,
                "input_tokens_details": {
                    "cached_tokens": 4,
                    "cache_write_tokens": 0,
                },
                "output_tokens": 5,
                "output_tokens_details": {"reasoning_tokens": 1},
                "total_tokens": 17,
            },
        },
        headers={"x-request-id": "provider-request-id"},
    )
