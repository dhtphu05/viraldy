from __future__ import annotations

import time
from collections.abc import Sequence
from contextlib import AbstractContextManager, nullcontext
from typing import cast
from uuid import UUID

import structlog
from openai import (
    APIConnectionError,
    APIResponseValidationError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    ContentFilterFinishReasonError,
    LengthFinishReasonError,
    NotFoundError,
    OpenAI,
    OpenAIError,
    PermissionDeniedError,
    RateLimitError,
    UnprocessableEntityError,
    omit,
)
from openai.types.audio import TranscriptionVerbose
from openai.types.responses import ParsedResponse, ResponseInputParam
from pydantic import BaseModel, ValidationError

from viraldy.modules.ai_gateway.providers.base import (
    AiProviderError,
    AudioTranscriptionRequest,
    AudioTranscriptionResult,
    AudioTranscriptSegment,
    InputContentPart,
    InputImagePart,
    ProviderEndpointFamily,
    ProviderErrorCode,
    ProviderErrorInfo,
    StructuredGenerationRequest,
    StructuredGenerationResult,
)
from viraldy.modules.ai_gateway.structured_output import (
    StructuredOutputIssue,
    StructuredOutputValidationError,
    repair_messages,
    validate_structured_output,
)
from viraldy.modules.ai_gateway.usage import extract_provider_usage
from viraldy.modules.ai_gateway.workspace_limiter import (
    WorkspaceConcurrencyBusy,
    WorkspaceLimiterUnavailable,
    WorkspaceRequestLimiter,
    redis_workspace_request_limiter,
)
from viraldy.platform.config.settings import Settings

logger = structlog.get_logger(__name__)


class OpenAINativeProvider:
    provider_name = "openai"

    def __init__(
        self,
        settings: Settings,
        client: OpenAI | None = None,
        workspace_limiter: WorkspaceRequestLimiter | None = None,
    ) -> None:
        self._settings = settings
        self._workspace_limiter = workspace_limiter or redis_workspace_request_limiter(
            settings.redis_url
        )
        if client is not None:
            self._client = client
            return
        if settings.openai_api_key is None:
            raise _provider_error(
                ProviderErrorCode.NOT_CONFIGURED,
                "OpenAI is not configured. Set OPENAI_API_KEY.",
                operation="provider_initialization",
                endpoint_family=ProviderEndpointFamily.RESPONSES,
            )
        self._client = OpenAI(
            api_key=settings.openai_api_key.get_secret_value(),
            base_url=settings.openai_base_url,
            timeout=settings.openai_request_timeout_seconds,
            max_retries=settings.openai_max_retries,
        )

    def generate_structured(
        self, request: StructuredGenerationRequest
    ) -> StructuredGenerationResult:
        try:
            with self._workspace_slot(
                request.workspace_id,
                repair_attempts=request.max_repair_attempts,
            ):
                return self._generate_structured(request)
        except WorkspaceConcurrencyBusy as exc:
            raise _provider_error(
                ProviderErrorCode.WORKSPACE_BUSY,
                "This workspace already has the maximum number of OpenAI requests in progress.",
                operation=request.operation,
                endpoint_family=ProviderEndpointFamily.RESPONSES,
                retryable=True,
            ) from exc
        except WorkspaceLimiterUnavailable as exc:
            raise _provider_error(
                ProviderErrorCode.GUARDRAIL_UNAVAILABLE,
                "The OpenAI concurrency guardrail is unavailable; the request was not sent.",
                operation=request.operation,
                endpoint_family=ProviderEndpointFamily.RESPONSES,
                retryable=True,
            ) from exc

    def _generate_structured(
        self, request: StructuredGenerationRequest
    ) -> StructuredGenerationResult:
        messages = _response_input(
            request.user_content,
            request.system_prompt,
            request.developer_prompt,
        )
        repair_attempt_count = 0
        incomplete_retry_count = 0
        current_max_output_tokens = (
            request.max_output_tokens or self._settings.openai_max_output_tokens
        )
        started = time.monotonic()

        while True:
            raw_response = None
            try:
                idempotency_key = request.idempotency_key
                if incomplete_retry_count:
                    idempotency_key = (
                        f"{request.idempotency_key or request.request_id}"
                        f"-incomplete-retry-{incomplete_retry_count}"
                    )
                raw_response = self._client.responses.with_raw_response.parse(
                    model=request.model,
                    input=messages,
                    text_format=request.output_model,
                    store=self._settings.openai_store_responses,
                    reasoning={
                        "effort": request.reasoning_effort or self._settings.openai_reasoning_effort
                    },
                    max_output_tokens=current_max_output_tokens,
                    extra_headers=_request_headers(request.request_id, idempotency_key),
                    timeout=self._settings.openai_request_timeout_seconds,
                )
                response = raw_response.parse()
            except (ValidationError, APIResponseValidationError) as exc:
                if isinstance(exc, ValidationError):
                    logger.warning(
                        "openai_structured_output_validation_failed",
                        operation=request.operation,
                        repair_attempt_count=repair_attempt_count,
                        errors=[
                            {
                                "location": [str(item) for item in error["loc"]],
                                "type": error["type"],
                                "message": error["msg"],
                            }
                            for error in exc.errors(include_input=False, include_url=False)
                        ],
                    )
                issue = StructuredOutputIssue(
                    code=ProviderErrorCode.OUTPUT_INVALID,
                    summary="OpenAI returned output that did not match the required schema.",
                )
                if repair_attempt_count >= request.max_repair_attempts:
                    raise _provider_error(
                        issue.code,
                        "OpenAI returned invalid structured output after the repair limit.",
                        operation=request.operation,
                        endpoint_family=ProviderEndpointFamily.RESPONSES,
                        http_status=raw_response.status_code if raw_response else None,
                        provider_request_id=raw_response.request_id if raw_response else None,
                        repair_attempt_count=repair_attempt_count,
                    ) from exc
                repair_attempt_count += 1
                messages = _repair_input(messages, issue, "")
                continue
            except OpenAIError as exc:
                raise _map_openai_error(
                    exc,
                    operation=request.operation,
                    endpoint_family=ProviderEndpointFamily.RESPONSES,
                    repair_attempt_count=repair_attempt_count,
                ) from exc

            provider_request_id = _provider_request_id(response, raw_response.request_id)
            http_status = raw_response.status_code
            refusal = _find_refusal(response)
            if refusal:
                raise _provider_error(
                    ProviderErrorCode.REFUSED,
                    "OpenAI refused the structured generation request.",
                    operation=request.operation,
                    endpoint_family=ProviderEndpointFamily.RESPONSES,
                    http_status=http_status,
                    provider_request_id=provider_request_id,
                    response_status=response.status,
                    repair_attempt_count=repair_attempt_count,
                )

            if response.status != "completed":
                incomplete_reason = _incomplete_reason(response)
                expanded_max_output_tokens = max(
                    current_max_output_tokens,
                    self._settings.openai_max_output_tokens,
                )
                if (
                    response.status == "incomplete"
                    and incomplete_reason == "max_output_tokens"
                    and incomplete_retry_count == 0
                    and expanded_max_output_tokens > current_max_output_tokens
                ):
                    incomplete_retry_count += 1
                    current_max_output_tokens = expanded_max_output_tokens
                    logger.warning(
                        "openai_structured_output_incomplete_retry",
                        operation=request.operation,
                        incomplete_reason=incomplete_reason,
                        retry_attempt_count=incomplete_retry_count,
                        max_output_tokens=current_max_output_tokens,
                    )
                    continue
                raise _provider_error(
                    ProviderErrorCode.INCOMPLETE,
                    "OpenAI did not complete the structured generation request.",
                    operation=request.operation,
                    endpoint_family=ProviderEndpointFamily.RESPONSES,
                    http_status=http_status,
                    provider_request_id=provider_request_id,
                    response_status=response.status or "unknown",
                    incomplete_reason=incomplete_reason,
                    repair_attempt_count=repair_attempt_count,
                    retryable=response.status in {"failed", "in_progress", "queued"},
                )

            try:
                parsed_output = validate_structured_output(
                    response.output_parsed,
                    request.output_model,
                    request.output_validator,
                )
            except StructuredOutputValidationError as exc:
                logger.warning(
                    "openai_structured_output_rejected",
                    operation=request.operation,
                    validation_code=exc.issue.code.value,
                    validation_summary=exc.issue.summary,
                    repair_attempt_count=repair_attempt_count,
                )
                if repair_attempt_count >= request.max_repair_attempts:
                    raise _provider_error(
                        exc.issue.code,
                        "OpenAI returned invalid structured output after the repair limit.",
                        operation=request.operation,
                        endpoint_family=ProviderEndpointFamily.RESPONSES,
                        http_status=http_status,
                        provider_request_id=provider_request_id,
                        response_status=response.status,
                        repair_attempt_count=repair_attempt_count,
                    ) from exc
                repair_attempt_count += 1
                messages = _repair_input(messages, exc.issue, response.output_text)
                continue

            return StructuredGenerationResult(
                parsed_output=parsed_output,
                provider=self.provider_name,
                endpoint_family=ProviderEndpointFamily.RESPONSES,
                model=response.model or request.model,
                provider_request_id=provider_request_id,
                http_status=http_status,
                latency_ms=round((time.monotonic() - started) * 1000),
                usage=extract_provider_usage(response),
                response_status=response.status,
                refusal=None,
                incomplete_reason=None,
                repair_attempt_count=repair_attempt_count,
                input_hash=request.input_hash,
                request_hash=request.request_hash,
            )

    def transcribe_audio(self, request: AudioTranscriptionRequest) -> AudioTranscriptionResult:
        if not request.audio_path.is_file() or request.audio_path.stat().st_size == 0:
            raise _provider_error(
                ProviderErrorCode.EVIDENCE_INVALID,
                "The audio input is missing or empty.",
                operation=request.operation,
                endpoint_family=ProviderEndpointFamily.AUDIO_TRANSCRIPTIONS,
            )

        try:
            with self._workspace_slot(request.workspace_id, repair_attempts=0):
                return self._transcribe_audio(request)
        except WorkspaceConcurrencyBusy as exc:
            raise _provider_error(
                ProviderErrorCode.WORKSPACE_BUSY,
                "This workspace already has the maximum number of OpenAI requests in progress.",
                operation=request.operation,
                endpoint_family=ProviderEndpointFamily.AUDIO_TRANSCRIPTIONS,
                retryable=True,
            ) from exc
        except WorkspaceLimiterUnavailable as exc:
            raise _provider_error(
                ProviderErrorCode.GUARDRAIL_UNAVAILABLE,
                "The OpenAI concurrency guardrail is unavailable; the request was not sent.",
                operation=request.operation,
                endpoint_family=ProviderEndpointFamily.AUDIO_TRANSCRIPTIONS,
                retryable=True,
            ) from exc

    def _transcribe_audio(self, request: AudioTranscriptionRequest) -> AudioTranscriptionResult:
        started = time.monotonic()
        try:
            with request.audio_path.open("rb") as audio_file:
                raw_response = self._client.audio.transcriptions.with_raw_response.create(
                    file=audio_file,
                    model=request.model,
                    language=request.language if request.language is not None else omit,
                    prompt=request.prompt if request.prompt is not None else omit,
                    response_format=request.response_format,
                    timestamp_granularities=request.timestamp_granularities,
                    extra_headers=_request_headers(request.request_id, request.idempotency_key),
                    timeout=self._settings.openai_request_timeout_seconds,
                )
                response = raw_response.parse()
        except OpenAIError as exc:
            raise _map_openai_error(
                exc,
                operation=request.operation,
                endpoint_family=ProviderEndpointFamily.AUDIO_TRANSCRIPTIONS,
            ) from exc
        except OSError as exc:
            raise _provider_error(
                ProviderErrorCode.EVIDENCE_INVALID,
                "The audio input could not be read.",
                operation=request.operation,
                endpoint_family=ProviderEndpointFamily.AUDIO_TRANSCRIPTIONS,
            ) from exc

        if not isinstance(response, TranscriptionVerbose):
            raise _provider_error(
                ProviderErrorCode.OUTPUT_INVALID,
                "OpenAI returned an invalid timestamped transcription.",
                operation=request.operation,
                endpoint_family=ProviderEndpointFamily.AUDIO_TRANSCRIPTIONS,
                http_status=raw_response.status_code,
                provider_request_id=raw_response.request_id,
            )

        segments = [
            AudioTranscriptSegment(
                start_ms=round(segment.start * 1000),
                end_ms=round(segment.end * 1000),
                text=segment.text.strip(),
            )
            for segment in response.segments or []
            if segment.text.strip()
        ]
        return AudioTranscriptionResult(
            provider=self.provider_name,
            endpoint_family=ProviderEndpointFamily.AUDIO_TRANSCRIPTIONS,
            model=request.model,
            provider_request_id=_provider_request_id(response, raw_response.request_id),
            http_status=raw_response.status_code,
            latency_ms=round((time.monotonic() - started) * 1000),
            usage=extract_provider_usage(response),
            language=response.language,
            duration_ms=round(response.duration * 1000),
            full_text=response.text,
            segments=segments,
            input_hash=request.input_hash,
            request_hash=request.request_hash,
        )

    def _workspace_slot(
        self,
        workspace_id: UUID | None,
        *,
        repair_attempts: int,
    ) -> AbstractContextManager[None]:
        if workspace_id is None:
            return nullcontext()
        request_attempts = self._settings.openai_max_retries + 1
        response_attempts = repair_attempts + 1
        lease_seconds = (
            self._settings.openai_request_timeout_seconds * request_attempts * response_attempts
            + 30
        )
        return self._workspace_limiter.slot(
            workspace_id,
            max_parallel=self._settings.openai_max_parallel_requests_per_workspace,
            wait_timeout_seconds=self._settings.openai_request_timeout_seconds,
            lease_seconds=lease_seconds,
        )


def _response_input(
    content: Sequence[InputContentPart],
    system_prompt: str,
    developer_prompt: str,
) -> ResponseInputParam:
    user_content: list[dict[str, object]] = []
    for part in content:
        if isinstance(part, InputImagePart):
            user_content.append(
                {
                    "type": "input_image",
                    "image_url": part.data_url,
                    "detail": part.detail,
                }
            )
        else:
            user_content.append({"type": "input_text", "text": part.text})
    return cast(
        ResponseInputParam,
        [
            {
                "role": "system",
                "content": [{"type": "input_text", "text": system_prompt}],
            },
            {
                "role": "developer",
                "content": [{"type": "input_text", "text": developer_prompt}],
            },
            {"role": "user", "content": user_content},
        ],
    )


def _repair_input(
    original: ResponseInputParam,
    issue: StructuredOutputIssue,
    invalid_output: str,
) -> ResponseInputParam:
    developer_message, user_message = repair_messages(issue, invalid_output)
    return cast(
        ResponseInputParam,
        [
            *original,
            {
                "role": "developer",
                "content": [{"type": "input_text", "text": developer_message}],
            },
            {
                "role": "user",
                "content": [{"type": "input_text", "text": user_message}],
            },
        ],
    )


def _request_headers(request_id: str, idempotency_key: str | None) -> dict[str, str]:
    return {
        "X-Client-Request-Id": request_id,
        "Idempotency-Key": idempotency_key or request_id,
    }


def _find_refusal(response: ParsedResponse[BaseModel]) -> bool:
    for item in response.output:
        if getattr(item, "type", None) != "message":
            continue
        for part in getattr(item, "content", []):
            if getattr(part, "type", None) == "refusal":
                return True
    return False


def _provider_request_id(response: object, fallback: str | None) -> str | None:
    request_id = getattr(response, "_request_id", None)
    return request_id if isinstance(request_id, str) else fallback


def _map_openai_error(
    exc: OpenAIError,
    *,
    operation: str,
    endpoint_family: ProviderEndpointFamily,
    repair_attempt_count: int = 0,
) -> AiProviderError:
    http_status = exc.status_code if isinstance(exc, APIStatusError) else None
    request_id = exc.request_id if isinstance(exc, APIStatusError) else None

    if isinstance(exc, AuthenticationError | PermissionDeniedError):
        return _provider_error(
            ProviderErrorCode.UNAUTHORIZED,
            "OpenAI rejected the configured credentials or project access.",
            operation=operation,
            endpoint_family=endpoint_family,
            http_status=http_status,
            provider_request_id=request_id,
            repair_attempt_count=repair_attempt_count,
        )
    if isinstance(exc, RateLimitError):
        return _provider_error(
            ProviderErrorCode.RATE_LIMITED,
            "OpenAI rate limits prevented the request from completing.",
            operation=operation,
            endpoint_family=endpoint_family,
            http_status=http_status,
            provider_request_id=request_id,
            repair_attempt_count=repair_attempt_count,
            retryable=True,
        )
    if isinstance(exc, APITimeoutError):
        return _provider_error(
            ProviderErrorCode.TIMEOUT,
            "The OpenAI request timed out.",
            operation=operation,
            endpoint_family=endpoint_family,
            repair_attempt_count=repair_attempt_count,
            retryable=True,
        )
    if isinstance(exc, ContentFilterFinishReasonError):
        return _provider_error(
            ProviderErrorCode.REFUSED,
            "OpenAI refused the request.",
            operation=operation,
            endpoint_family=endpoint_family,
            repair_attempt_count=repair_attempt_count,
        )
    if isinstance(exc, LengthFinishReasonError):
        return _provider_error(
            ProviderErrorCode.INCOMPLETE,
            "OpenAI could not complete the response within the output limit.",
            operation=operation,
            endpoint_family=endpoint_family,
            repair_attempt_count=repair_attempt_count,
        )
    if isinstance(exc, NotFoundError) or _is_model_error(exc):
        setting_hint = _model_setting_hint(operation)
        return _provider_error(
            ProviderErrorCode.MODEL_NOT_AVAILABLE,
            f"The OpenAI model for operation {operation!r} is unavailable. "
            f"Change {setting_hint}.",
            operation=operation,
            endpoint_family=endpoint_family,
            http_status=http_status,
            provider_request_id=request_id,
            repair_attempt_count=repair_attempt_count,
        )
    if isinstance(exc, BadRequestError | UnprocessableEntityError | APIResponseValidationError):
        return _provider_error(
            ProviderErrorCode.OUTPUT_INVALID,
            "OpenAI rejected the structured request or returned an invalid response.",
            operation=operation,
            endpoint_family=endpoint_family,
            http_status=http_status,
            provider_request_id=request_id,
            repair_attempt_count=repair_attempt_count,
        )
    return _provider_error(
        ProviderErrorCode.INCOMPLETE,
        "The OpenAI request did not complete.",
        operation=operation,
        endpoint_family=endpoint_family,
        http_status=http_status,
        provider_request_id=request_id,
        response_status="failed",
        repair_attempt_count=repair_attempt_count,
        retryable=isinstance(exc, APIConnectionError) or (http_status or 0) >= 500,
    )


def _is_model_error(exc: OpenAIError) -> bool:
    if not isinstance(exc, APIStatusError) or not isinstance(exc.body, dict):
        return False
    nested_error = exc.body.get("error")
    error = nested_error if isinstance(nested_error, dict) else exc.body
    code = error.get("code")
    return code in {"model_not_found", "model_not_available", "invalid_model"}


def _model_setting_hint(operation: str) -> str:
    operation_settings = {
        "media_observation": "OPENAI_MODEL_MEDIA_OBSERVATION or OPENAI_VISION_MODEL",
        "creative_dna_build": "OPENAI_MODEL_CREATIVE_DNA or OPENAI_TEXT_MODEL",
        "pattern_kit_extract": "OPENAI_MODEL_PATTERN_KIT or OPENAI_TEXT_MODEL",
        "viral_kit_compose": "OPENAI_MODEL_VIRAL_KIT or OPENAI_TEXT_MODEL",
        "adaptation_generate": "OPENAI_MODEL_ADAPTATION or OPENAI_TEXT_MODEL",
        "campaign_pack_generate": "OPENAI_MODEL_CAMPAIGN_PACK or OPENAI_TEXT_MODEL",
        "seller_decision_summary": "OPENAI_MODEL_DECISION_SUMMARY or OPENAI_TEXT_MODEL",
        "revision_message_generate": "OPENAI_MODEL_REVISION_MESSAGE or OPENAI_TEXT_MODEL",
        "ugc_execution_brief_synthesis": (
            "OPENAI_MODEL_UGC_EXECUTION_BRIEF or OPENAI_TEXT_MODEL"
        ),
    }
    return operation_settings.get(operation, "OPENAI_TEXT_MODEL")


def _incomplete_reason(response: ParsedResponse[BaseModel]) -> str | None:
    reason = getattr(response.incomplete_details, "reason", None)
    return reason if isinstance(reason, str) else None


def _provider_error(
    code: ProviderErrorCode,
    message: str,
    *,
    operation: str,
    endpoint_family: ProviderEndpointFamily,
    http_status: int | None = None,
    provider_request_id: str | None = None,
    response_status: str | None = None,
    incomplete_reason: str | None = None,
    repair_attempt_count: int = 0,
    retryable: bool = False,
) -> AiProviderError:
    return AiProviderError(
        ProviderErrorInfo(
            code=code,
            message=message,
            operation=operation,
            endpoint_family=endpoint_family,
            http_status=http_status,
            provider_request_id=provider_request_id,
            response_status=response_status,
            incomplete_reason=incomplete_reason,
            repair_attempt_count=repair_attempt_count,
            retryable=retryable,
        )
    )
