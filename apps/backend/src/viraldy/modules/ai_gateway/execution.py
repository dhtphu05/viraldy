from __future__ import annotations

import hashlib
from collections.abc import Sequence

from pydantic import BaseModel

from viraldy.modules.ai_gateway.context import ViraldyOperationContextV1
from viraldy.modules.ai_gateway.prompt_content.examples import (
    render_runtime_few_shot_content,
    select_few_shot_examples,
)
from viraldy.modules.ai_gateway.prompt_packages import get_prompt_package
from viraldy.modules.ai_gateway.providers.base import (
    AiProvider,
    AiProviderError,
    InputContentPart,
    InputImagePart,
    InputTextPart,
    OutputValidator,
    StructuredGenerationRequest,
    StructuredGenerationResult,
)
from viraldy.modules.ai_gateway.providers.router import build_ai_provider
from viraldy.modules.ai_gateway.request_identity import (
    structured_input_hash,
    structured_request_hash,
)
from viraldy.platform.config.settings import Settings
from viraldy.shared.errors.base import AppError


def execute_structured_operation(
    settings: Settings,
    context: ViraldyOperationContextV1,
    output_model: type[BaseModel],
    *,
    image_parts: Sequence[InputImagePart] = (),
    output_validator: OutputValidator | None = None,
    provider: AiProvider | None = None,
) -> StructuredGenerationResult:
    prompt = get_prompt_package(context.operation)
    if context.prompt_version != prompt.prompt_version:
        raise AppError(
            "OPENAI_DOMAIN_VALIDATION_FAILED",
            "Operation context prompt version does not match the registered prompt.",
        )
    if context.schema_version != prompt.output_schema_version:
        raise AppError(
            "OPENAI_DOMAIN_VALIDATION_FAILED",
            "Operation context schema version does not match the registered prompt.",
        )
    native_live = settings.ai_mode == "live" and settings.ai_provider == "openai"
    compatible_mock = settings.ai_mode == "mock" and settings.ai_provider == "openai_compatible"
    if not native_live and not compatible_mock:
        raise AppError(
            "OPENAI_NOT_CONFIGURED",
            (
                "Structured execution requires native OpenAI live mode or the "
                "explicit OpenAI-compatible mock route."
            ),
            status_code=503,
        )

    stable_input = context.stable_json()
    content: list[InputContentPart] = [InputTextPart(text=stable_input)]
    selected_examples = tuple(
        example
        for example in select_few_shot_examples(context)
        if example.example_id in prompt.example_ids
    )
    runtime_examples = (
        render_runtime_few_shot_content(selected_examples) if selected_examples else None
    )
    if runtime_examples is not None:
        content.append(InputTextPart(text=runtime_examples))
    content.extend(image_parts)
    model = settings.resolve_openai_model(
        context.operation.value,
        vision=context.operation.value == "media_observation",
    )
    input_hash = structured_input_hash(
        context_json=stable_input,
        runtime_examples_json=runtime_examples,
        images=[
            {
                "media_type": image.media_type,
                "detail": image.detail,
                "content_sha256": hashlib.sha256(image.image_base64.encode("ascii")).hexdigest(),
            }
            for image in image_parts
        ],
    )
    request_hash = structured_request_hash(
        operation=context.operation.value,
        model=model,
        prompt_version=prompt.prompt_version,
        schema_version=prompt.output_schema_version,
        input_hash=input_hash,
    )
    request = StructuredGenerationRequest(
        operation=context.operation.value,
        model=model,
        system_prompt=prompt.system_prompt,
        developer_prompt=prompt.developer_prompt,
        user_content=content,
        output_model=output_model,
        prompt_version=prompt.prompt_version,
        schema_version=prompt.output_schema_version,
        reasoning_effort=prompt.default_reasoning_effort or settings.openai_reasoning_effort,
        max_output_tokens=prompt.default_max_output_tokens or settings.openai_max_output_tokens,
        request_id=context.request_id,
        input_hash=input_hash,
        request_hash=request_hash,
        workspace_id=context.workspace_id,
        idempotency_key=context.request_id,
        output_validator=output_validator,
        max_repair_attempts=1,
    )
    selected_provider = provider or build_ai_provider(settings)
    try:
        return selected_provider.generate_structured(request)
    except AiProviderError as exc:
        raise provider_error_to_app_error(
            exc,
            input_hash=request.input_hash,
            request_hash=request.request_hash,
        ) from exc


def provider_error_to_app_error(
    error: AiProviderError,
    *,
    input_hash: str | None = None,
    request_hash: str | None = None,
) -> AppError:
    info = error.info
    status_code = {
        "OPENAI_UNAUTHORIZED": 503,
        "OPENAI_NOT_CONFIGURED": 503,
        "OPENAI_MODEL_NOT_AVAILABLE": 503,
        "OPENAI_RATE_LIMITED": 429,
        "OPENAI_WORKSPACE_BUSY": 429,
        "OPENAI_GUARDRAIL_UNAVAILABLE": 503,
        "OPENAI_TIMEOUT": 504,
        "OPENAI_REFUSED": 422,
        "OPENAI_INCOMPLETE": 502,
        "OPENAI_OUTPUT_INVALID": 502,
        "OPENAI_EVIDENCE_INVALID": 422,
        "OPENAI_DOMAIN_VALIDATION_FAILED": 422,
    }.get(error.code, 502)
    details: dict[str, object] = {
        "operation": info.operation,
        "endpoint_family": info.endpoint_family.value,
        "repair_attempt_count": info.repair_attempt_count,
    }
    if info.http_status is not None:
        details["http_status"] = info.http_status
    if info.provider_request_id is not None:
        details["provider_request_id"] = info.provider_request_id
    if info.response_status is not None:
        details["response_status"] = info.response_status
    if info.incomplete_reason is not None:
        details["incomplete_reason"] = info.incomplete_reason
    if input_hash is not None:
        details["input_hash"] = input_hash
    if request_hash is not None:
        details["request_hash"] = request_hash
    return AppError(error.code, error.safe_message, status_code=status_code, details=details)
