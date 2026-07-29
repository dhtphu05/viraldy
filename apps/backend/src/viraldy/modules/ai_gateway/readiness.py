from __future__ import annotations

from viraldy.modules.ai_gateway.schemas import AiCapabilities, AiReadiness
from viraldy.platform.config.settings import Settings


def ai_readiness(settings: Settings) -> AiReadiness:
    mode = settings.ai_mode
    provider = settings.ai_provider
    missing: list[str] = []

    capabilities = AiCapabilities(
        text_chat=bool(settings.ai_text_model),
        vision_chat=bool(settings.ai_vision_model),
        audio_transcription=bool(settings.asr_model),
        json_schema=settings.ai_supports_json_schema,
        image_url=settings.ai_supports_image_url,
        base64_image=True,
    )
    if mode == "fixture":
        return AiReadiness(
            mode=mode,
            provider=provider,
            configured=True,
            capabilities=capabilities,
            missing=[],
        )

    if provider != "openai_compatible":
        missing.append("AI_PROVIDER")
    if settings.asr_provider != "openai_compatible":
        missing.append("ASR_PROVIDER")
    required = {
        "AI_BASE_URL": settings.ai_base_url,
        "AI_TEXT_MODEL": settings.ai_text_model,
        "AI_VISION_MODEL": settings.ai_vision_model,
        "ASR_MODEL": settings.asr_model,
    }
    if mode == "live":
        required["AI_API_KEY"] = settings.ai_api_key
    elif mode != "mock":
        missing.append("AI_MODE")
    for name, value in required.items():
        if not value:
            missing.append(name)
    return AiReadiness(
        mode=mode,
        provider=provider,
        configured=not missing,
        capabilities=capabilities,
        missing=missing,
    )
