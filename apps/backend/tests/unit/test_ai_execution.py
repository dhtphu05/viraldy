from __future__ import annotations

import json
from uuid import uuid4

import pytest
from pydantic import BaseModel, ConfigDict

from viraldy.modules.ai_gateway.context import ViraldyOperationContextV1
from viraldy.modules.ai_gateway.execution import execute_structured_operation
from viraldy.modules.ai_gateway.operations import AiOperationName
from viraldy.modules.ai_gateway.prompt_content.examples import (
    MAX_RUNTIME_FEW_SHOT_EXAMPLES,
)
from viraldy.modules.ai_gateway.prompt_packages import get_prompt_package
from viraldy.modules.ai_gateway.providers.base import (
    AiProviderError,
    AudioTranscriptionRequest,
    AudioTranscriptionResult,
    InputImagePart,
    ProviderEndpointFamily,
    ProviderErrorCode,
    ProviderErrorInfo,
    StructuredGenerationRequest,
    StructuredGenerationResult,
)
from viraldy.modules.ai_gateway.structured_output import (
    StructuredOutputValidationError,
    validate_structured_output,
)
from viraldy.modules.ai_gateway.usage import ProviderUsage
from viraldy.platform.config.settings import Settings
from viraldy.shared.errors.base import AppError


class ExampleOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: str


class FakeProvider:
    provider_name = "openai"

    def __init__(self) -> None:
        self.request: StructuredGenerationRequest | None = None

    def generate_structured(
        self, request: StructuredGenerationRequest
    ) -> StructuredGenerationResult:
        self.request = request
        return StructuredGenerationResult(
            parsed_output=ExampleOutput(value="grounded"),
            provider="openai",
            endpoint_family=ProviderEndpointFamily.RESPONSES,
            model=request.model,
            provider_request_id="req-provider-1",
            http_status=200,
            latency_ms=12,
            usage=ProviderUsage(
                input_tokens=100,
                output_tokens=20,
                total_tokens=120,
                cached_input_tokens=50,
            ),
            response_status="completed",
            repair_attempt_count=0,
        )

    def transcribe_audio(self, request: AudioTranscriptionRequest) -> AudioTranscriptionResult:
        raise NotImplementedError


def _context() -> ViraldyOperationContextV1:
    prompt = get_prompt_package(AiOperationName.PATTERN_KIT_EXTRACT)
    return ViraldyOperationContextV1(
        operation=AiOperationName.PATTERN_KIT_EXTRACT,
        request_id="req-operation-1",
        workspace_id=uuid4(),
        operation_payload={"source_count": 2},
        schema_version=prompt.output_schema_version,
        prompt_version=prompt.prompt_version,
    )


def test_executor_uses_registered_prompt_model_and_stable_context() -> None:
    provider = FakeProvider()
    context = _context()
    settings = Settings(
        ai_mode="live",
        ai_provider="openai",
        openai_api_key="test-openai-key",
        openai_model_pattern_kit="gpt-pattern-test",
    )

    result = execute_structured_operation(
        settings,
        context,
        ExampleOutput,
        provider=provider,
    )

    assert result.parsed_output == ExampleOutput(value="grounded")
    assert provider.request is not None
    assert provider.request.model == "gpt-pattern-test"
    assert (
        provider.request.system_prompt
        == get_prompt_package(AiOperationName.PATTERN_KIT_EXTRACT).system_prompt
    )
    assert provider.request.user_content[0].type == "input_text"
    assert provider.request.max_repair_attempts == 1
    assert len(provider.request.input_hash) == 64
    assert len(provider.request.request_hash) == 64
    assert provider.request.workspace_id == context.workspace_id


def test_executor_request_identity_changes_with_source_version_and_image() -> None:
    settings = Settings(
        ai_mode="live",
        ai_provider="openai",
        openai_api_key="test-openai-key",
    )
    original_context = _context()
    original_context = original_context.model_copy(update={"source_version_ids": [uuid4()]})
    original_provider = FakeProvider()
    changed_source_provider = FakeProvider()
    changed_image_provider = FakeProvider()

    execute_structured_operation(
        settings,
        original_context,
        ExampleOutput,
        image_parts=[InputImagePart(media_type="image/jpeg", image_base64="ZnJhbWUtMQ==")],
        provider=original_provider,
    )
    execute_structured_operation(
        settings,
        original_context.model_copy(update={"source_version_ids": [uuid4()]}),
        ExampleOutput,
        image_parts=[InputImagePart(media_type="image/jpeg", image_base64="ZnJhbWUtMQ==")],
        provider=changed_source_provider,
    )
    execute_structured_operation(
        settings,
        original_context,
        ExampleOutput,
        image_parts=[InputImagePart(media_type="image/jpeg", image_base64="ZnJhbWUtMg==")],
        provider=changed_image_provider,
    )

    assert original_provider.request is not None
    assert changed_source_provider.request is not None
    assert changed_image_provider.request is not None
    assert original_provider.request.input_hash != changed_source_provider.request.input_hash
    assert original_provider.request.request_hash != (changed_source_provider.request.request_hash)
    assert original_provider.request.input_hash != changed_image_provider.request.input_hash
    assert original_provider.request.request_hash != changed_image_provider.request.request_hash


def test_executor_allows_explicit_compatible_mock_route() -> None:
    provider = FakeProvider()
    settings = Settings(
        _env_file=None,
        ai_mode="mock",
        ai_provider="openai_compatible",
        ai_base_url="http://127.0.0.1:8787/v1",
        ai_api_key="mock-key",
        ai_text_model="mock-text",
    )

    result = execute_structured_operation(
        settings,
        _context(),
        ExampleOutput,
        provider=provider,
    )

    assert result.parsed_output == ExampleOutput(value="grounded")


def test_executor_injects_selected_examples_separately_with_request_ids() -> None:
    provider = FakeProvider()
    context_payload = _context().model_dump(mode="python")
    context_payload["seller_constraints"] = {
        "commerce_domain": "dropshipping",
    }
    context = ViraldyOperationContextV1.model_validate(context_payload)

    execute_structured_operation(
        Settings(
            ai_mode="live",
            ai_provider="openai",
            openai_api_key="test-openai-key",
        ),
        context,
        ExampleOutput,
        provider=provider,
    )

    assert provider.request is not None
    assert len(provider.request.user_content) == 2
    stable_context_part, runtime_examples_part = provider.request.user_content
    assert stable_context_part.type == "input_text"
    assert stable_context_part.text == context.stable_json()
    assert runtime_examples_part.type == "input_text"
    runtime_payload = json.loads(runtime_examples_part.text)
    assert runtime_payload["kind"] == "runtime_few_shot_examples"
    assert 1 <= len(runtime_payload["selected_example_ids"]) <= (MAX_RUNTIME_FEW_SHOT_EXAMPLES)
    assert runtime_payload["selected_example_ids"] == [
        example["example_id"] for example in runtime_payload["examples"]
    ]
    assert set(runtime_payload["selected_example_ids"]) <= set(
        get_prompt_package(context.operation).example_ids
    )
    assert "Rechargeable Mini Bag Sealer" not in runtime_examples_part.text
    assert "expected_output" not in runtime_examples_part.text


def test_executor_rejects_unregistered_prompt_version() -> None:
    context_payload = _context().model_dump(mode="python")
    context_payload["prompt_version"] = "unregistered"

    with pytest.raises(AppError) as exc_info:
        execute_structured_operation(
            Settings(
                ai_mode="live",
                ai_provider="openai",
                openai_api_key="test-openai-key",
            ),
            ViraldyOperationContextV1.model_validate(context_payload),
            ExampleOutput,
            provider=FakeProvider(),
        )

    assert exc_info.value.code == "OPENAI_DOMAIN_VALIDATION_FAILED"


def test_executor_maps_provider_errors_without_raw_payloads() -> None:
    class FailedProvider(FakeProvider):
        def generate_structured(
            self, request: StructuredGenerationRequest
        ) -> StructuredGenerationResult:
            raise AiProviderError(
                ProviderErrorInfo(
                    code=ProviderErrorCode.RATE_LIMITED,
                    message="OpenAI rate limits prevented the request from completing.",
                    operation=request.operation,
                    endpoint_family=ProviderEndpointFamily.RESPONSES,
                    http_status=429,
                    provider_request_id="req-safe",
                    repair_attempt_count=1,
                    retryable=True,
                )
            )

    with pytest.raises(AppError) as exc_info:
        execute_structured_operation(
            Settings(
                ai_mode="live",
                ai_provider="openai",
                openai_api_key="test-openai-key",
            ),
            _context(),
            ExampleOutput,
            provider=FailedProvider(),
        )

    assert exc_info.value.code == "OPENAI_RATE_LIMITED"
    assert exc_info.value.status_code == 429
    assert exc_info.value.details["provider_request_id"] == "req-safe"
    assert len(str(exc_info.value.details["input_hash"])) == 64
    assert len(str(exc_info.value.details["request_hash"])) == 64
    assert "key" not in exc_info.value.message.lower()


def test_domain_validation_reason_is_bounded_for_repair() -> None:
    reason = "Evidence IDs must belong to the supplied catalog. " + ("x" * 3000)

    with pytest.raises(StructuredOutputValidationError) as exc_info:
        validate_structured_output(
            ExampleOutput(value="grounded"),
            ExampleOutput,
            validator=lambda _output: (_ for _ in ()).throw(ValueError(reason)),
        )

    assert exc_info.value.issue.code == ProviderErrorCode.DOMAIN_VALIDATION_FAILED
    assert "Evidence IDs must belong to the supplied catalog." in (exc_info.value.issue.summary)
    assert "\n" not in exc_info.value.issue.summary
    assert len(exc_info.value.issue.summary) == 2000
