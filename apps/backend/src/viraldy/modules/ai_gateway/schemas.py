from __future__ import annotations

from pydantic import BaseModel, Field


class AiCapabilities(BaseModel):
    text_chat: bool = False
    vision_chat: bool = False
    audio_transcription: bool = False
    json_schema: bool = False
    image_url: bool = False
    base64_image: bool = False


class AiReadiness(BaseModel):
    mode: str
    provider: str
    configured: bool
    capabilities: AiCapabilities
    missing: list[str] = Field(default_factory=list)


class ProviderResponse(BaseModel):
    payload: dict[str, object]
    http_status: int
    provider_request_id: str | None
    latency_ms: int
