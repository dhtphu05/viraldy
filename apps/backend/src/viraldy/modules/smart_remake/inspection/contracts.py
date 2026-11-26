"""Versioned, provider-independent Inspector inputs and evidence wire contracts."""

from __future__ import annotations

import builtins
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from viraldy.shared.errors.base import AppError

from ..generation_expectations import (
    GenerationExpectations,
    expectations_hash,
    validate_generation_expectations,
)

InspectionStatus = Literal["passed", "failed", "needs_review", "insufficient_evidence"]
Timebase = Literal["source", "raw_group", "scene_local", "final"]
Category = Literal[
    "technical",
    "product",
    "character",
    "action",
    "structure",
    "claims",
    "continuity",
    "constraints",
    "rights",
    "consent",
    "policy",
]
Hash = str


class InspectionModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class FrameRange(InspectionModel):
    inFrame: int = Field(ge=0)
    outFrame: int = Field(gt=0)
    fps: Literal[24] = 24
    timebase: Timebase

    @model_validator(mode="after")
    def positive_range(self) -> FrameRange:
        if self.outFrame <= self.inFrame:
            raise ValueError("Frame ranges must be nonempty and exclusive at outFrame.")
        return self


class InspectionSubject(InspectionModel):
    kind: Literal["image", "scene", "assembly"]
    projectId: str = Field(min_length=1)
    mediaHash: str = Field(pattern=r"^[a-f0-9]{64}$")
    sceneId: str | None = None
    versionId: str | None = None
    assemblyId: str | None = None
    imageRole: Literal["product", "character", "conditioning"] | None = None
    range: FrameRange | None = None
    neighborVersionIds: list[str | None] | None = None

    @model_validator(mode="after")
    def valid_identity(self) -> InspectionSubject:
        identity = {
            key
            for key in ("sceneId", "versionId", "assemblyId", "imageRole")
            if getattr(self, key) is not None
        }
        required = {
            "scene": {"sceneId", "versionId"},
            "assembly": {"assemblyId"},
            "image": {"imageRole"},
        }[self.kind]
        if identity != required or (self.kind == "image") != (self.range is None):
            raise ValueError("Subject identity and frame range must match the media kind.")
        if any(not getattr(self, name) for name in required):
            raise ValueError("Subject identifiers must be nonempty.")
        return self


class ResolvedMedia(InspectionModel):
    id: str = Field(min_length=1)
    mediaHash: str = Field(pattern=r"^[a-f0-9]{64}$")
    bytes: builtins.bytes = Field(min_length=1, repr=False, exclude=True)
    mimeType: Literal[
        "video/mp4", "video/webm", "video/quicktime", "image/png", "image/jpeg", "image/webp"
    ]
    frameCount: int | None = Field(default=None, gt=0)
    fps: int | None = None
    role: Literal["source", "product", "character", "conditioning", "neighbor"] | None = None
    versionId: str | None = None
    range: FrameRange | None = None


class ObservationAnchor(InspectionModel):
    mediaId: str = Field(min_length=1)
    mediaHash: str = Field(pattern=r"^[a-f0-9]{64}$")
    timebase: Timebase
    frame: int = Field(ge=0)


class InspectionConstraints(InspectionModel):
    constraintsHash: str = Field(pattern=r"^[a-f0-9]{64}$")
    manifestHash: str = Field(pattern=r"^[a-f0-9]{64}$")
    requirements: dict[str, Any]
    requirementsHash: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    timeline: dict[str, Any] = Field(default_factory=dict)
    manifest: dict[str, Any] = Field(default_factory=dict)
    sourceSceneMap: dict[str, Any] | None = None
    fps: Literal[24] = 24
    frameCount: int | None = Field(default=None, gt=0)
    technicalCheck: dict[str, Any] | None = None
    maxFramesPerVideo: int = Field(default=12, ge=1, le=120)
    maxFrameLongEdge: int = Field(default=1280, ge=1, le=4096)
    observationAnchors: list[ObservationAnchor] = Field(default_factory=list)
    expectations: GenerationExpectations | None = None
    expectationsHash: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    sceneIds: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def bound_expectations(self) -> InspectionConstraints:
        if (self.expectations is None) != (self.expectationsHash is None):
            raise ValueError("Inspection expectations require their exact hash.")
        if self.expectations is not None:
            try:
                value = validate_generation_expectations(self.expectations, self.expectationsHash)
            except AppError as exc:
                raise ValueError(
                    "Inspection expectations do not match their retained hash."
                ) from exc
            matches = (
                self.requirementsHash == value["requirementsHash"]
                and self.requirements == value["requirements"]
                if self.requirementsHash is not None
                else value["requirementsHash"] == expectations_hash(self.requirements)
            )
            if not matches:
                raise ValueError(
                    "Inspection expectations must retain the saved global requirements."
                )
            ids = {scene["renderUnitId"] for scene in value["scenes"]}
            if len(self.sceneIds) != len(set(self.sceneIds)) or not set(self.sceneIds) <= ids:
                raise ValueError("Inspection scene scope must identify retained expectations.")
        elif self.sceneIds:
            raise ValueError("Inspection scene scope requires retained expectations.")
        return self


class Evidence(InspectionModel):
    mediaId: str = Field(min_length=1)
    mediaHash: str = Field(pattern=r"^[a-f0-9]{64}$")
    inFrame: int | None = Field(default=None, ge=0)
    outFrame: int | None = Field(default=None, gt=0)
    timebase: Timebase | None = None
    sampleId: str | None = None

    @model_validator(mode="after")
    def complete_clock(self) -> Evidence:
        if self.inFrame is None:
            if self.outFrame is not None or self.timebase is not None:
                raise ValueError("Images cannot have a timestamp or partial frame range.")
        elif self.outFrame is None or self.outFrame <= self.inFrame or self.timebase is None:
            raise ValueError("Video evidence needs a complete, nonempty frame range and clock.")
        return self


class Observation(Evidence):
    id: str = Field(min_length=1)
    imageHash: str = Field(pattern=r"^[a-f0-9]{64}$")
    mimeType: Literal["image/jpeg", "image/png", "image/webp"]


class Finding(InspectionModel):
    id: str = Field(min_length=1)
    requirementId: str = Field(min_length=1)
    category: Category
    expected: str = Field(min_length=1)
    observed: str = Field(min_length=1)
    status: InspectionStatus
    severity: Literal["info", "warning", "error"]
    evidence: list[Evidence]
    suggestedAction: str = Field(min_length=1)
    blocking: bool
    hardBlocking: bool


class Coverage(InspectionModel):
    requirementId: str = Field(min_length=1)
    status: InspectionStatus
    evidence: list[Evidence]
    sampledFrames: list[int] = Field(default_factory=list)
    unobservedFrames: int = Field(default=0, ge=0)
    limitations: list[str] = Field(default_factory=list)


class NotApplicableRequirement(InspectionModel):
    requirementId: str
    reason: str


class InspectionReport(InspectionModel):
    id: str = Field(min_length=1)
    schemaVersion: Literal[1] = 1
    subject: InspectionSubject
    status: InspectionStatus
    checkedAt: str = Field(min_length=1)
    checkerVersion: str = Field(min_length=1)
    rubricVersion: str = Field(min_length=1)
    modelProfile: dict[str, Any] = Field(min_length=1)
    constraintsHash: str = Field(pattern=r"^[a-f0-9]{64}$")
    manifestHash: str = Field(pattern=r"^[a-f0-9]{64}$")
    expectationsHash: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    coverage: list[Coverage]
    findings: list[Finding]
    observations: list[Observation] = Field(default_factory=list)
    notApplicableRequirements: list[NotApplicableRequirement] = Field(default_factory=list)


class Requirement(InspectionModel):
    id: str
    category: Category
    expected: str
    sceneId: str | None = None
    sourceSceneId: str | None = None
    sourceFrame: int | None = Field(default=None, ge=0)
    sourceMediaHash: str | None = None
    outputFrame: int | None = Field(default=None, ge=0)


class ModelImage(InspectionModel):
    observationId: str
    mimeType: Literal["image/jpeg", "image/png", "image/webp"]
    data: bytes = Field(min_length=1, repr=False, exclude=True)


class SemanticFinding(InspectionModel):
    requirementId: str
    status: InspectionStatus
    observed: str = Field(min_length=1)
    observationIds: list[str]


class SemanticOutput(InspectionModel):
    findings: list[SemanticFinding]


class InspectionModelRequest(InspectionModel):
    operation: Literal["smart_remake_inspection"] = "smart_remake_inspection"
    schemaVersion: Literal[1] = 1
    promptVersion: Literal["smart-remake-inspection-p0-v2"] = "smart-remake-inspection-p0-v2"
    systemInstruction: str
    prompt: str
    inputHash: str
    subject: InspectionSubject
    requirements: list[Requirement]
    observations: list[Observation]
    images: list[ModelImage]

    @property
    def output_model(self) -> type[SemanticOutput]:
        return SemanticOutput


class InspectionModelResult(InspectionModel):
    output: SemanticOutput
    modelProfile: dict[str, Any] = Field(min_length=1)
