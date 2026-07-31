from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from viraldy.modules.ai_gateway.http_client import (
    OpenAICompatibleClient,
    extract_message_json,
)
from viraldy.modules.ai_gateway.providers.base import (
    AudioTranscriptionRequest,
    AudioTranscriptionResult,
    InputImagePart,
    InputTextPart,
    ProviderEndpointFamily,
    StructuredGenerationRequest,
    StructuredGenerationResult,
)
from viraldy.modules.ai_gateway.usage import ProviderUsage
from viraldy.platform.config.settings import Settings
from viraldy.shared.errors.base import AppError


class OpenAICompatibleStructuredProvider:
    """Strict structured adapter used only by the local mock provider route."""

    provider_name = "openai_compatible"

    def __init__(
        self,
        settings: Settings,
        *,
        client: OpenAICompatibleClient | None = None,
    ) -> None:
        if settings.ai_mode != "mock" or settings.ai_provider != "openai_compatible":
            raise ValueError("OpenAI-compatible structured provider is restricted to mock mode")
        self._settings = settings
        self._client = client or OpenAICompatibleClient(settings)

    def generate_structured(
        self,
        request: StructuredGenerationRequest,
    ) -> StructuredGenerationResult:
        messages = _messages(request)
        repair_attempt_count = 0
        while True:
            response = self._client.chat_json(_payload(request, messages))
            raw = extract_message_json(response)
            try:
                parsed = request.output_model.model_validate(raw)
                if request.output_validator is not None:
                    request.output_validator(parsed)
            except (ValidationError, ValueError) as exc:
                if repair_attempt_count >= request.max_repair_attempts:
                    raise AppError(
                        "MODEL_RESPONSE_INVALID",
                        "Mock AI provider returned invalid structured output.",
                        details={
                            "provider_request_id": response.provider_request_id,
                            "repair_attempt_count": repair_attempt_count,
                        },
                    ) from exc
                repair_attempt_count += 1
                messages.extend(
                    [
                        {
                            "role": "assistant",
                            "content": json.dumps(
                                raw,
                                ensure_ascii=True,
                                separators=(",", ":"),
                                sort_keys=True,
                            ),
                        },
                        {
                            "role": "user",
                            "content": (
                                "Repair the prior output so it satisfies the supplied "
                                "strict JSON schema and deterministic domain rules. "
                                "Return only the corrected JSON object."
                            ),
                        },
                    ]
                )
                continue
            return StructuredGenerationResult(
                parsed_output=parsed,
                provider=self.provider_name,
                endpoint_family=ProviderEndpointFamily.CHAT_COMPLETIONS,
                model=request.model,
                provider_request_id=response.provider_request_id,
                http_status=response.http_status,
                latency_ms=response.latency_ms,
                usage=_usage(response.payload),
                response_status="completed",
                repair_attempt_count=repair_attempt_count,
                input_hash=request.input_hash,
                request_hash=request.request_hash,
            )

    def transcribe_audio(
        self,
        request: AudioTranscriptionRequest,
    ) -> AudioTranscriptionResult:
        raise AppError(
            "AI_PROVIDER_NOT_CONFIGURED",
            (
                "The structured mock adapter does not transcribe audio; media "
                "analysis uses the configured ASR adapter."
            ),
        )


def _messages(
    request: StructuredGenerationRequest,
) -> list[dict[str, Any]]:
    user_content: list[dict[str, Any]] = []
    for part in request.user_content:
        if isinstance(part, InputTextPart):
            user_content.append({"type": "text", "text": part.text})
        elif isinstance(part, InputImagePart):
            user_content.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": part.data_url,
                        "detail": part.detail,
                    },
                }
            )
    return [
        {"role": "system", "content": request.system_prompt},
        {"role": "developer", "content": request.developer_prompt},
        {"role": "user", "content": user_content},
    ]


def _payload(
    request: StructuredGenerationRequest,
    messages: list[dict[str, Any]],
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": request.model,
        "messages": messages,
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": request.output_model.__name__,
                "schema": request.output_model.model_json_schema(),
                "strict": True,
            },
        },
    }
    if request.max_output_tokens is not None:
        payload["max_tokens"] = request.max_output_tokens
    return payload


def _usage(payload: dict[str, Any]) -> ProviderUsage:
    raw = payload.get("usage")
    if not isinstance(raw, dict):
        return ProviderUsage()
    prompt_tokens = _optional_int(raw.get("prompt_tokens"))
    completion_tokens = _optional_int(raw.get("completion_tokens"))
    return ProviderUsage(
        input_tokens=prompt_tokens,
        output_tokens=completion_tokens,
        total_tokens=_optional_int(raw.get("total_tokens")),
        cached_input_tokens=None,
    )


def _optional_int(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None
