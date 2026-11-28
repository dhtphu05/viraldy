"""Frame-accurate public contracts for the independent source/render/edit domains."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

FPS: Literal[24] = 24
RAW_DURATION_FRAMES: Literal[192] = 192


class TimelineModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class SourceScene(TimelineModel):
    id: str
    startFrame: int = Field(ge=0)
    endFrame: int = Field(gt=0)
    targetDurationFrames: int = Field(gt=0)
    sourceSceneIndex: int | None = Field(default=None, ge=0)
    prompt: str = ""
    imagePrompt: str = ""
    videoPrompt: str = ""
    shotPlan: dict[str, Any] | None = None

    @model_validator(mode="after")
    def valid_duration(self) -> SourceScene:
        if self.endFrame <= self.startFrame:
            raise ValueError("Source duration must have a positive exact frame range.")
        return self


class SourceSceneMap(TimelineModel):
    fps: Literal[24] = FPS
    sourceStartFrame: int = Field(ge=0)
    sourceFrameCount: int = Field(gt=0)
    timingMode: Literal["source_rhythm", "fit_target"] = "source_rhythm"
    scenes: list[SourceScene] = Field(min_length=1)


class RenderUnit(TimelineModel):
    id: str
    sourceSceneId: str
    sceneIndex: int = Field(ge=0)
    sourceSceneIndex: int | None = Field(default=None, ge=0)
    sourceStartFrame: int | None = Field(default=None, ge=0)
    sourceEndFrame: int | None = Field(default=None, gt=0)
    fragmentIndex: int = Field(default=0, ge=0)
    fragmentCount: int = Field(default=1, ge=1)
    rawDurationFrames: Literal[144, 192] = RAW_DURATION_FRAMES
    targetDurationFrames: int = Field(gt=0, le=RAW_DURATION_FRAMES)
    prompt: str = ""
    imagePrompt: str = ""
    videoPrompt: str = ""

    @model_validator(mode="after")
    def valid_source_fragment(self) -> RenderUnit:
        if self.targetDurationFrames > self.rawDurationFrames:
            raise ValueError("A render fragment must fit its saved provider window.")
        if (self.sourceStartFrame is None) != (self.sourceEndFrame is None):
            raise ValueError("A source fragment requires both exact frame bounds.")
        if (
            self.sourceStartFrame is not None
            and self.sourceEndFrame is not None
            and (self.sourceEndFrame <= self.sourceStartFrame)
        ):
            raise ValueError("A source fragment must have positive duration.")
        if self.fragmentIndex >= self.fragmentCount:
            raise ValueError("A fragment index must be within its logical scene.")
        return self


class RenderGroupSegment(TimelineModel):
    renderUnitId: str
    inFrame: int = Field(ge=0, lt=RAW_DURATION_FRAMES)
    outFrame: int = Field(gt=0, le=RAW_DURATION_FRAMES)


class RenderGroup(TimelineModel):
    id: str
    renderUnitIds: list[str] = Field(min_length=1)
    rawDurationFrames: Literal[144, 192] = RAW_DURATION_FRAMES
    targetDurationFrames: int = Field(gt=0, le=RAW_DURATION_FRAMES)
    segments: list[RenderGroupSegment] = Field(min_length=1)


class RenderPlan(TimelineModel):
    fps: Literal[24] = FPS
    provider: Literal["kie"] = "kie"
    units: list[RenderUnit] = Field(min_length=1)
    groups: list[RenderGroup] | None = Field(default=None, min_length=1)
    renderGroupBreaks: list[int] | None = None
    groupingPolicy: Literal["fixed_provider_windows"] | None = None
    videoModel: Literal["veo3_lite", "wan/3-0-video"] | None = None
    videoResolution: Literal["480P", "720P", "1080P"] | None = None
    audioRequired: bool | None = None
    imageModel: Literal["gpt-image-2.6-sunburst", "gpt-image-2.6-flare"] | None = None
    imageQuality: Literal["low", "medium", "high", "xhigh", "max"] | None = None
    imageComplexity: Literal["low", "medium", "high"] | None = None
    imageSize: Literal["720x1280"] | None = None
    referencePolicy: (
        Literal["product-character-first-layout", "product-first-last-layout"] | None
    ) = None


class TimelineItem(TimelineModel):
    id: str
    sourceSceneId: str
    renderUnitId: str
    targetStartFrame: int = Field(ge=0)
    targetDurationFrames: int = Field(gt=0, le=RAW_DURATION_FRAMES)
    versionId: str | None = None
    inFrame: int = Field(ge=0, le=RAW_DURATION_FRAMES)
    outFrame: int = Field(gt=0, le=RAW_DURATION_FRAMES)
    reviewed: bool = False


class DraftTimeline(TimelineModel):
    fps: Literal[24] = FPS
    totalFrames: Literal[192, 288, 384]
    items: list[TimelineItem] = Field(min_length=1)


def provider_window_frames(plan: dict[str, Any]) -> int:
    """Twelve-second Wan plans use six-second windows; saved legacy plans retain eight."""
    if sum(unit["targetDurationFrames"] for unit in plan["units"]) == 288:
        if plan.get("videoModel") != "wan/3-0-video":
            raise ValueError("Twelve-second output requires the Wan provider contract.")
        return 144
    return RAW_DURATION_FRAMES
