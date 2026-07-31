from __future__ import annotations

from collections.abc import Callable, Mapping

from openai import OpenAI

from viraldy.modules.ai_gateway.providers.base import (
    AiProvider,
    AiProviderError,
    ProviderEndpointFamily,
    ProviderErrorCode,
    ProviderErrorInfo,
)
from viraldy.modules.ai_gateway.providers.openai_compatible import (
    OpenAICompatibleStructuredProvider,
)
from viraldy.modules.ai_gateway.providers.openai_native import OpenAINativeProvider
from viraldy.platform.config.settings import Settings

ProviderFactory = Callable[[Settings], AiProvider]


def provider_route(settings: Settings) -> str:
    if settings.ai_mode == "fixture":
        return "fixture"
    if settings.ai_mode == "mock":
        return "mock"
    return settings.ai_provider


def build_ai_provider(
    settings: Settings,
    *,
    factories: Mapping[str, ProviderFactory] | None = None,
    openai_client: OpenAI | None = None,
) -> AiProvider:
    route = provider_route(settings)
    if route == "openai":
        return OpenAINativeProvider(settings, client=openai_client)
    if route == "mock" and settings.ai_provider == "openai_compatible":
        return OpenAICompatibleStructuredProvider(settings)
    if factories is not None and route in factories:
        return factories[route](settings)
    raise AiProviderError(
        ProviderErrorInfo(
            code=ProviderErrorCode.NOT_CONFIGURED,
            message=f"No provider factory is registered for AI route {route!r}.",
            provider=route,
            operation="provider_routing",
            endpoint_family=ProviderEndpointFamily.RESPONSES,
        )
    )
