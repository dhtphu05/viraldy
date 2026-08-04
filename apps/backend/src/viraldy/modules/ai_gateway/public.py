from __future__ import annotations

from viraldy.modules.ai_gateway.context import (
    EvidenceItemForModelV1,
    ViraldyOperationContextV1,
)
from viraldy.modules.ai_gateway.execution import (
    execute_structured_operation,
    provider_error_to_app_error,
)
from viraldy.modules.ai_gateway.http_client import OpenAICompatibleClient, extract_message_json
from viraldy.modules.ai_gateway.models import AiModelRunModel
from viraldy.modules.ai_gateway.operations import (
    AI_OPERATION_DEFINITIONS,
    AiOperationDefinition,
    AiOperationName,
    build_ai_operation_fixture,
    get_ai_operation_definition,
)
from viraldy.modules.ai_gateway.prompts import (
    ADAPTATION_PROMPT_NAME,
    ADAPTATION_PROMPT_VERSION,
    ADAPTATION_SCHEMA_VERSION,
    CAMPAIGN_PACK_PROMPT_NAME,
    CAMPAIGN_PACK_PROMPT_VERSION,
    DECISION_SUMMARY_OUTPUT_SCHEMA_VERSION,
    DECISION_SUMMARY_PROMPT_NAME,
    DECISION_SUMMARY_PROMPT_VERSION,
    MEDIA_OBSERVATION_PROMPT_NAME,
    MEDIA_OBSERVATION_PROMPT_VERSION,
    PATTERN_KIT_PROMPT_NAME,
    PATTERN_KIT_PROMPT_VERSION,
    REVISION_MESSAGE_PROMPT_NAME,
    REVISION_MESSAGE_PROMPT_VERSION,
    UGC_EXECUTION_BRIEF_OPERATION,
    UGC_EXECUTION_BRIEF_PROMPT_NAME,
    UGC_EXECUTION_BRIEF_PROMPT_VERSION,
    VIRAL_KIT_PROMPT_NAME,
    VIRAL_KIT_PROMPT_VERSION,
    PromptPackage,
    get_prompt_package,
)
from viraldy.modules.ai_gateway.providers import (
    AiProviderError,
    InputImagePart,
    OpenAINativeProvider,
    ProviderErrorCode,
    StructuredGenerationResult,
)
from viraldy.modules.ai_gateway.repository import (
    AiModelRunRepository,
    SyncAiModelRunRepository,
)
from viraldy.modules.ai_gateway.structured_output import (
    StructuredOutputIssue,
    StructuredOutputValidationError,
)
from viraldy.modules.creative_domain.schema_versions import (
    PATTERN_KIT_SCHEMA_VERSION,
    VIRAL_KIT_SCHEMA_VERSION,
)

__all__ = [
    "ADAPTATION_PROMPT_VERSION",
    "ADAPTATION_PROMPT_NAME",
    "ADAPTATION_SCHEMA_VERSION",
    "CAMPAIGN_PACK_PROMPT_NAME",
    "CAMPAIGN_PACK_PROMPT_VERSION",
    "DECISION_SUMMARY_OUTPUT_SCHEMA_VERSION",
    "DECISION_SUMMARY_PROMPT_NAME",
    "DECISION_SUMMARY_PROMPT_VERSION",
    "AI_OPERATION_DEFINITIONS",
    "AiOperationDefinition",
    "AiOperationName",
    "AiModelRunModel",
    "AiModelRunRepository",
    "AiProviderError",
    "EvidenceItemForModelV1",
    "InputImagePart",
    "MEDIA_OBSERVATION_PROMPT_NAME",
    "MEDIA_OBSERVATION_PROMPT_VERSION",
    "OpenAICompatibleClient",
    "OpenAINativeProvider",
    "PATTERN_KIT_PROMPT_NAME",
    "PATTERN_KIT_PROMPT_VERSION",
    "PATTERN_KIT_SCHEMA_VERSION",
    "REVISION_MESSAGE_PROMPT_NAME",
    "REVISION_MESSAGE_PROMPT_VERSION",
    "UGC_EXECUTION_BRIEF_OPERATION",
    "UGC_EXECUTION_BRIEF_PROMPT_NAME",
    "UGC_EXECUTION_BRIEF_PROMPT_VERSION",
    "VIRAL_KIT_PROMPT_VERSION",
    "VIRAL_KIT_PROMPT_NAME",
    "VIRAL_KIT_SCHEMA_VERSION",
    "SyncAiModelRunRepository",
    "StructuredGenerationResult",
    "ViraldyOperationContextV1",
    "PromptPackage",
    "ProviderErrorCode",
    "StructuredOutputIssue",
    "StructuredOutputValidationError",
    "execute_structured_operation",
    "extract_message_json",
    "build_ai_operation_fixture",
    "get_ai_operation_definition",
    "get_prompt_package",
    "provider_error_to_app_error",
]
