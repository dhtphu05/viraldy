from __future__ import annotations

from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class GenerationOperation(StrEnum):
    STORYBOARD_IMAGE_GENERATE = "storyboard_image_generate"
    CONCEPT_VIDEO_PREVIEW_GENERATE = "concept_video_preview_generate"


class GenerationStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class GenerationContractBase(BaseModel):
    model_config = ConfigDict(extra="forbid")


class GenerationArtifactV1(GenerationContractBase):
    id: UUID
    artifact_kind: Literal["storyboard_image", "concept_video_preview"]
    scene_id: str | None = Field(default=None, max_length=120)
    storage_key: str | None = None
    media_type: str
    width: int | None = Field(default=None, ge=1)
    height: int | None = Field(default=None, ge=1)
    duration_ms: int | None = Field(default=None, ge=1)
    payload_json: dict[str, object] = Field(default_factory=dict)

    @model_validator(mode="after")
    def reject_signed_urls(self) -> GenerationArtifactV1:
        values = [self.storage_key, *self._payload_strings(self.payload_json)]
        if any(value and value.lower().startswith(("http://", "https://")) for value in values):
            raise ValueError("generation artifacts must not persist signed or remote URLs")
        return self

    @classmethod
    def _payload_strings(cls, value: object) -> list[str]:
        if isinstance(value, str):
            return [value]
        if isinstance(value, dict):
            strings: list[str] = []
            for item in value.values():
                strings.extend(cls._payload_strings(item))
            return strings
        if isinstance(value, list):
            strings = []
            for item in value:
                strings.extend(cls._payload_strings(item))
            return strings
        return []


class GenerationProviderResultV1(GenerationContractBase):
    provider: str
    model: str
    provider_request_id: str | None = None
    latency_ms: int | None = Field(default=None, ge=0)
    attempt_count: int = Field(default=1, ge=1)
    artifacts: list[GenerationArtifactV1] = Field(min_length=1)
    usage_json: dict[str, object] = Field(default_factory=dict)
    output_summary: dict[str, object] = Field(default_factory=dict)

    @model_validator(mode="after")
    def reject_duplicate_artifacts(self) -> GenerationProviderResultV1:
        artifact_ids = [artifact.id for artifact in self.artifacts]
        if len(artifact_ids) != len(set(artifact_ids)):
            raise ValueError("generation provider returned duplicate artifact IDs")
        return self
