from __future__ import annotations

from viraldy.modules.ai_gateway.schemas import AiCapabilities, AiReadiness
from viraldy.platform.config.settings import Settings


def ai_readiness(settings: Settings, *, live_qualified: bool = False) -> AiReadiness:
    mode = settings.ai_mode
    provider = settings.ai_provider
    missing: list[str] = []

    if mode == "fixture":
        return AiReadiness(
            mode=mode,
            provider=provider,
            state="configured",
            configured=True,
            capabilities=AiCapabilities(),
            missing=[],
        )

    if mode not in {"mock", "live"}:
        return AiReadiness(
            mode=mode,
            provider=provider,
            state="configuration_invalid",
            configured=False,
            capabilities=AiCapabilities(),
            missing=["AI_MODE"],
        )

    if provider == "openai":
        capabilities = AiCapabilities(
            text_chat=bool(settings.openai_text_model),
            vision_chat=bool(settings.openai_vision_model),
            audio_transcription=bool(settings.openai_transcription_model),
            json_schema=True,
            image_url=False,
            base64_image=settings.openai_image_transport == "base64",
        )
        if mode == "live" and not settings.openai_api_key:
            missing.append("OPENAI_API_KEY")
        configured = not missing
        state = (
            "qualified"
            if configured and live_qualified
            else "not_yet_qualified"
            if configured and mode == "live"
            else "configured"
            if configured
            else "not_configured"
        )
        return AiReadiness(
            mode=mode,
            provider=provider,
            state=state,
            configured=configured,
            capabilities=capabilities,
            missing=missing,
        )

    capabilities = AiCapabilities(
        text_chat=bool(settings.ai_text_model),
        vision_chat=bool(settings.ai_vision_model),
        audio_transcription=bool(settings.asr_model),
        json_schema=settings.ai_supports_json_schema,
        image_url=settings.ai_supports_image_url,
        base64_image=True,
    )
    if provider != "openai_compatible":
        missing.append("AI_PROVIDER")
    if settings.asr_provider != "openai_compatible":
        missing.append("ASR_PROVIDER")
    required: dict[str, object | None] = {
        "AI_BASE_URL": settings.ai_base_url,
        "AI_TEXT_MODEL": settings.ai_text_model,
        "AI_VISION_MODEL": settings.ai_vision_model,
        "ASR_MODEL": settings.asr_model,
    }
    if mode == "live":
        required["AI_API_KEY"] = settings.ai_api_key
    for name, value in required.items():
        if not value:
            missing.append(name)
    state = (
        "configured"
        if not missing
        else "configuration_invalid"
        if "AI_PROVIDER" in missing
        else "not_configured"
    )
    return AiReadiness(
        mode=mode,
        provider=provider,
        state=state,
        configured=not missing,
        capabilities=capabilities,
        missing=missing,
    )
