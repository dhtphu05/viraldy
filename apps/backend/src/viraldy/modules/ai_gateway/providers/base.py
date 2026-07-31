from __future__ import annotations

import base64
from collections.abc import Callable
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Literal, Protocol, runtime_checkable
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from viraldy.modules.ai_gateway.usage import ProviderUsage


class ProviderErrorCode(StrEnum):
    NOT_CONFIGURED = "OPENAI_NOT_CONFIGURED"
    UNAUTHORIZED = "OPENAI_UNAUTHORIZED"
    MODEL_NOT_AVAILABLE = "OPENAI_MODEL_NOT_AVAILABLE"
    RATE_LIMITED = "OPENAI_RATE_LIMITED"
    WORKSPACE_BUSY = "OPENAI_WORKSPACE_BUSY"
    GUARDRAIL_UNAVAILABLE = "OPENAI_GUARDRAIL_UNAVAILABLE"
    TIMEOUT = "OPENAI_TIMEOUT"
    REFUSED = "OPENAI_REFUSED"
    INCOMPLETE = "OPENAI_INCOMPLETE"
    OUTPUT_INVALID = "OPENAI_OUTPUT_INVALID"
    EVIDENCE_INVALID = "OPENAI_EVIDENCE_INVALID"
    DOMAIN_VALIDATION_FAILED = "OPENAI_DOMAIN_VALIDATION_FAILED"


class ProviderEndpointFamily(StrEnum):
    RESPONSES = "responses"
    CHAT_COMPLETIONS = "chat_completions"
    AUDIO_TRANSCRIPTIONS = "audio_transcriptions"


class InputTextPart(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["input_text"] = "input_text"
    text: str = Field(min_length=1)


class InputImagePart(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["input_image"] = "input_image"
    media_type: Literal["image/jpeg", "image/png", "image/webp", "image/gif"]
    image_base64: str = Field(min_length=1, repr=False)
    detail: Literal["auto", "low", "high", "original"] = "auto"

    @field_validator("image_base64")
    @classmethod
    def validate_base64(cls, value: str) -> str:
        try:
            base64.b64decode(value, validate=True)
        except ValueError as exc:
            raise ValueError("image_base64 must be valid base64 data.") from exc
        return value

    @property
    def data_url(self) -> str:
        return f"data:{self.media_type};base64,{self.image_base64}"


InputContentPart = Annotated[InputTextPart | InputImagePart, Field(discriminator="type")]
OutputValidator = Callable[[BaseModel], None]


def _default_timestamp_granularities() -> list[Literal["segment", "word"]]:
    return ["segment"]


class StructuredGenerationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    operation: str = Field(min_length=1, max_length=120)
    model: str = Field(min_length=1)
    system_prompt: str = Field(min_length=1)
    developer_prompt: str = Field(min_length=1)
    user_content: list[InputContentPart] = Field(min_length=1)
    output_model: type[BaseModel] = Field(repr=False)
    prompt_version: str = Field(min_length=1)
    schema_version: str = Field(min_length=1)
    reasoning_effort: Literal["none", "minimal", "low", "medium", "high", "xhigh", "max"] | None = (
        None
    )
    max_output_tokens: int | None = Field(default=None, ge=1)
    request_id: str = Field(min_length=1, max_length=255)
    input_hash: str = Field(min_length=1, max_length=128)
    request_hash: str | None = Field(default=None, min_length=64, max_length=64)
    workspace_id: UUID | None = None
    idempotency_key: str | None = Field(default=None, min_length=1, max_length=255)
    output_validator: OutputValidator | None = Field(default=None, exclude=True, repr=False)
    max_repair_attempts: Literal[0, 1] = 1

    @model_validator(mode="after")
    def require_request_identity_for_workspace(self) -> StructuredGenerationRequest:
        if self.workspace_id is not None and self.request_hash is None:
            raise ValueError("request_hash is required for workspace-scoped requests")
        return self


class StructuredGenerationResult(BaseModel):
    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    parsed_output: BaseModel
    provider: str
    endpoint_family: Literal[
        ProviderEndpointFamily.RESPONSES,
        ProviderEndpointFamily.CHAT_COMPLETIONS,
    ]
    model: str
    provider_request_id: str | None
    http_status: int | None
    latency_ms: int = Field(ge=0)
    usage: ProviderUsage
    response_status: str
    refusal: str | None = None
    incomplete_reason: str | None = None
    repair_attempt_count: int = Field(ge=0, le=1)
    input_hash: str | None = Field(default=None, min_length=1, max_length=128)
    request_hash: str | None = Field(default=None, min_length=64, max_length=64)

    @property
    def input_tokens(self) -> int | None:
        return self.usage.input_tokens

    @property
    def output_tokens(self) -> int | None:
        return self.usage.output_tokens

    @property
    def total_tokens(self) -> int | None:
        return self.usage.total_tokens

    @property
    def cached_input_tokens(self) -> int | None:
        return self.usage.cached_input_tokens


class AudioTranscriptionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operation: str = "audio_transcription"
    audio_path: Path
    model: str = Field(min_length=1)
    request_id: str = Field(min_length=1, max_length=255)
    input_hash: str = Field(min_length=1, max_length=128)
    request_hash: str | None = Field(default=None, min_length=64, max_length=64)
    workspace_id: UUID | None = None
    language: str | None = Field(default=None, min_length=2, max_length=35)
    prompt: str | None = Field(default=None, max_length=1000)
    response_format: Literal["verbose_json"] = "verbose_json"
    timestamp_granularities: list[Literal["segment", "word"]] = Field(
        default_factory=_default_timestamp_granularities, min_length=1
    )
    idempotency_key: str | None = Field(default=None, min_length=1, max_length=255)

    @model_validator(mode="after")
    def require_request_identity_for_workspace(self) -> AudioTranscriptionRequest:
        if self.workspace_id is not None and self.request_hash is None:
            raise ValueError("request_hash is required for workspace-scoped requests")
        return self


class AudioTranscriptSegment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start_ms: int = Field(ge=0)
    end_ms: int = Field(ge=0)
    text: str = Field(min_length=1)


class AudioTranscriptionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str
    endpoint_family: Literal[ProviderEndpointFamily.AUDIO_TRANSCRIPTIONS]
    model: str
    provider_request_id: str | None
    http_status: int | None
    latency_ms: int = Field(ge=0)
    usage: ProviderUsage
    response_status: Literal["completed"] = "completed"
    language: str
    duration_ms: int = Field(ge=0)
    full_text: str
    segments: list[AudioTranscriptSegment]
    input_hash: str | None = Field(default=None, min_length=1, max_length=128)
    request_hash: str | None = Field(default=None, min_length=64, max_length=64)


class ProviderErrorInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: ProviderErrorCode
    message: str
    provider: str = "openai"
    operation: str
    endpoint_family: ProviderEndpointFamily
    http_status: int | None = None
    provider_request_id: str | None = None
    response_status: str | None = None
    incomplete_reason: str | None = None
    repair_attempt_count: int = Field(default=0, ge=0, le=1)
    retryable: bool = False


class AiProviderError(Exception):
    def __init__(self, info: ProviderErrorInfo) -> None:
        self.info = info
        super().__init__(f"{info.code.value}: {info.message}")

    @property
    def code(self) -> str:
        return self.info.code.value

    @property
    def safe_message(self) -> str:
        return self.info.message

    def __repr__(self) -> str:
        return f"{type(self).__name__}(code={self.code!r}, " f"operation={self.info.operation!r})"


@runtime_checkable
class AiProvider(Protocol):
    provider_name: str

    def generate_structured(
        self, request: StructuredGenerationRequest
    ) -> StructuredGenerationResult: ...

    def transcribe_audio(self, request: AudioTranscriptionRequest) -> AudioTranscriptionResult: ...
