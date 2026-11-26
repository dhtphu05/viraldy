from __future__ import annotations

from typing import Any, Literal, cast
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SerializerFunctionWrapHandler,
    model_serializer,
    model_validator,
)


class RepairApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class RepairAdvancedEdits(RepairApiModel):
    prompt: str | None = Field(default=None, min_length=1, max_length=12000)
    imagePrompt: str | None = Field(default=None, min_length=1, max_length=12000)
    videoPrompt: str | None = Field(default=None, min_length=1, max_length=12000)


class RepairIntent(RepairApiModel):
    schemaVersion: Literal[1] = 1
    issues: list[Literal["product_fidelity", "action", "presentation", "alternate_take"]] = Field(
        default_factory=list, max_length=4
    )
    instruction: str = Field(default="", max_length=4000)
    advancedEdits: RepairAdvancedEdits | None = None


class RepairSceneRequest(RepairApiModel):
    baseVersionId: UUID | None = None
    expectedRevision: int = Field(ge=1)
    prompt: str | None = Field(default=None, min_length=1, max_length=12000)
    imagePrompt: str | None = Field(default=None, min_length=1, max_length=12000)
    videoPrompt: str | None = Field(default=None, min_length=1, max_length=12000)
    repairIntent: RepairIntent | None = None
    idempotencyKey: str = Field(min_length=1, max_length=200)

    @model_validator(mode="after")
    def exclusive_directions(self) -> RepairSceneRequest:
        prompts = (self.prompt, self.imagePrompt, self.videoPrompt)
        if self.repairIntent is not None:
            if any(prompt is not None for prompt in prompts):
                raise ValueError("Use repairIntent or the three legacy prompts, not both.")
        elif not all(prompt is not None for prompt in prompts):
            raise ValueError("A repair requires repairIntent or all three legacy prompts.")
        return self

    @model_serializer(mode="wrap")
    def compatible_payload(self, handler: SerializerFunctionWrapHandler) -> dict[str, Any]:
        payload = cast(dict[str, Any], handler(self))
        # Persisted legacy hashes include baseVersionId=None but no repairIntent.
        # Do not globally exclude None, which would alter idempotency on replay.
        if self.repairIntent is None:
            payload.pop("repairIntent", None)
        else:
            for field in ("prompt", "imagePrompt", "videoPrompt"):
                payload.pop(field, None)
        return payload


class AcceptSceneVersion(RepairApiModel):
    sceneId: UUID
    versionId: UUID
    expectedRevision: int = Field(ge=1)
    idempotencyKey: str = Field(min_length=1, max_length=200)


class TimelineSelection(RepairApiModel):
    renderUnitId: UUID
    versionId: UUID
    inFrame: int = Field(ge=0, strict=True)
    outFrame: int = Field(gt=0, strict=True)
    reviewed: bool = True


class SaveTimelineRequest(RepairApiModel):
    expectedRevision: int = Field(ge=1)
    idempotencyKey: str = Field(min_length=1, max_length=200)
    items: list[TimelineSelection] = Field(min_length=1)


class PublishTimelineRequest(RepairApiModel):
    expectedRevision: int = Field(ge=1)
    idempotencyKey: str = Field(min_length=1, max_length=200)
