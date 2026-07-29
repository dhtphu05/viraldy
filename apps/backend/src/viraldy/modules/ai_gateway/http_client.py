from __future__ import annotations

import json
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import httpx

from viraldy.modules.ai_gateway.schemas import ProviderResponse
from viraldy.platform.config.settings import Settings
from viraldy.shared.errors.base import AppError


class OpenAICompatibleClient:
    def __init__(self, settings: Settings, request_id: str | None = None) -> None:
        self._settings = settings
        self._base_url = (settings.ai_base_url or "").rstrip("/")
        self._asr_base_url = (settings.asr_base_url or settings.ai_base_url or "").rstrip("/")
        secret = settings.ai_api_key.get_secret_value() if settings.ai_api_key else "mock-key"
        asr_secret = settings.asr_api_key.get_secret_value() if settings.asr_api_key else secret
        self._headers = {"Authorization": f"Bearer {secret}"}
        self._asr_headers = {"Authorization": f"Bearer {asr_secret}"}
        if request_id:
            self._headers["X-Request-ID"] = request_id
            self._asr_headers["X-Request-ID"] = request_id

    def chat_json(self, payload: Mapping[str, Any]) -> ProviderResponse:
        if not self._base_url:
            raise AppError("AI_PROVIDER_NOT_CONFIGURED", "AI_BASE_URL is required.")
        return self._post_json(f"{self._base_url}/chat/completions", payload)

    def transcribe(self, audio_path: Path, data: Mapping[str, Any]) -> ProviderResponse:
        if not self._asr_base_url:
            raise AppError("AI_PROVIDER_NOT_CONFIGURED", "ASR_BASE_URL or AI_BASE_URL is required.")
        started = time.monotonic()
        for attempt in range(self._settings.ai_max_retries + 1):
            try:
                with (
                    audio_path.open("rb") as audio_file,
                    httpx.Client(timeout=self._settings.ai_request_timeout_seconds) as client,
                ):
                    response = client.post(
                        f"{self._asr_base_url}/audio/transcriptions",
                        headers=self._asr_headers,
                        files={"file": (audio_path.name, audio_file, "audio/wav")},
                        data=data,
                    )
            except httpx.TimeoutException as exc:
                if attempt >= self._settings.ai_max_retries:
                    raise AppError("AI_PROVIDER_TIMEOUT", "AI provider request timed out.") from exc
                continue
            except httpx.HTTPError as exc:
                raise AppError("ASR_PROVIDER_FAILED", "ASR provider request failed.") from exc
            if _retryable(response) and attempt < self._settings.ai_max_retries:
                _sleep_retry_after(response)
                continue
            return _response_or_error(response, started, "ASR_PROVIDER_FAILED")
        raise AppError("ASR_PROVIDER_FAILED", "ASR provider request failed.")

    def _post_json(self, url: str, payload: Mapping[str, Any]) -> ProviderResponse:
        started = time.monotonic()
        for attempt in range(self._settings.ai_max_retries + 1):
            try:
                with httpx.Client(timeout=self._settings.ai_request_timeout_seconds) as client:
                    response = client.post(
                        url,
                        headers={**self._headers, "Content-Type": "application/json"},
                        json=payload,
                    )
            except httpx.TimeoutException as exc:
                if attempt >= self._settings.ai_max_retries:
                    raise AppError("AI_PROVIDER_TIMEOUT", "AI provider request timed out.") from exc
                continue
            except httpx.HTTPError as exc:
                raise AppError("VISION_PROVIDER_FAILED", "AI provider request failed.") from exc
            if _retryable(response) and attempt < self._settings.ai_max_retries:
                _sleep_retry_after(response)
                continue
            return _response_or_error(response, started, "VISION_PROVIDER_FAILED")
        raise AppError("VISION_PROVIDER_FAILED", "AI provider request failed.")


def extract_message_json(response: ProviderResponse) -> dict[str, Any]:
    choices = response.payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise AppError("MODEL_RESPONSE_INVALID", "AI provider response is missing choices.")
    first = choices[0]
    if not isinstance(first, dict):
        raise AppError("MODEL_RESPONSE_INVALID", "AI provider response choice is invalid.")
    message = first.get("message")
    if not isinstance(message, dict):
        raise AppError("MODEL_RESPONSE_INVALID", "AI provider response is missing a message.")
    content = message.get("content")
    if not isinstance(content, str):
        raise AppError("MODEL_RESPONSE_INVALID", "AI provider response content is invalid.")
    try:
        payload = json.loads(content)
    except ValueError as exc:
        raise AppError("MODEL_RESPONSE_INVALID", "AI provider returned invalid JSON.") from exc
    if not isinstance(payload, dict):
        raise AppError("MODEL_RESPONSE_INVALID", "AI provider JSON must be an object.")
    return payload


def _response_or_error(
    response: httpx.Response, started: float, fallback_code: str
) -> ProviderResponse:
    latency_ms = round((time.monotonic() - started) * 1000)
    request_id = response.headers.get("x-request-id") or response.headers.get("openai-request-id")
    if response.status_code in {401, 403}:
        raise AppError("AI_PROVIDER_UNAUTHORIZED", "AI provider rejected credentials.")
    if response.status_code == 429:
        raise AppError("AI_PROVIDER_RATE_LIMITED", "AI provider rate limit was reached.")
    if response.status_code >= 500:
        raise AppError("AI_PROVIDER_FAILED", "AI provider returned a server error.")
    if response.status_code >= 400:
        raise AppError(fallback_code, "AI provider request failed.")
    try:
        payload = response.json()
    except ValueError as exc:
        raise AppError("MODEL_RESPONSE_INVALID", "AI provider returned invalid JSON.") from exc
    if not isinstance(payload, dict):
        raise AppError("MODEL_RESPONSE_INVALID", "AI provider response must be a JSON object.")
    return ProviderResponse(
        payload=payload,
        http_status=response.status_code,
        provider_request_id=request_id,
        latency_ms=latency_ms,
    )


def _retryable(response: httpx.Response) -> bool:
    return response.status_code == 429 or response.status_code >= 500


def _sleep_retry_after(response: httpx.Response) -> None:
    retry_after = response.headers.get("retry-after")
    if retry_after is None:
        return
    try:
        delay = min(float(retry_after), 2.0)
    except ValueError:
        return
    time.sleep(delay)
