from __future__ import annotations

from viraldy.modules.ai_gateway.http_client import OpenAICompatibleClient, extract_message_json
from viraldy.modules.ai_gateway.models import AiModelRunModel
from viraldy.modules.ai_gateway.prompts import (
    ADAPTATION_PROMPT_VERSION,
    ADAPTATION_SCHEMA_VERSION,
    PATTERN_KIT_PROMPT_VERSION,
    VIRAL_KIT_PROMPT_VERSION,
)
from viraldy.modules.ai_gateway.repository import AiModelRunRepository
from viraldy.modules.creative_domain.schema_versions import (
    PATTERN_KIT_SCHEMA_VERSION,
    VIRAL_KIT_SCHEMA_VERSION,
)

__all__ = [
    "ADAPTATION_PROMPT_VERSION",
    "ADAPTATION_SCHEMA_VERSION",
    "AiModelRunModel",
    "AiModelRunRepository",
    "OpenAICompatibleClient",
    "PATTERN_KIT_PROMPT_VERSION",
    "PATTERN_KIT_SCHEMA_VERSION",
    "VIRAL_KIT_PROMPT_VERSION",
    "VIRAL_KIT_SCHEMA_VERSION",
    "extract_message_json",
]
