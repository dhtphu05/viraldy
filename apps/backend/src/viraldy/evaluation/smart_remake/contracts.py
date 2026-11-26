from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

Hash = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
Mode = Literal["fixture", "mock", "live"]
Result = Literal["passed", "failed", "needs_review", "insufficient_evidence"]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Protocol(Contract):
    schema_version: Literal["smart_remake_protocol_v1"] = "smart_remake_protocol_v1"
    protocol_id: str = Field(min_length=1)
    status: Literal["pending", "development", "locked"]
    variants: dict[str, str] = Field(default_factory=dict)
    ablations: dict[str, str] = Field(default_factory=dict)
    main_matrix: list[int] = Field(default_factory=lambda: [20, 3])
    ablation_matrix: list[int] = Field(default_factory=lambda: [8, 3])
    rubric_version: str = "remake-human-v1"
    source_record: str | None = None
    disagreement_policy: str = (
        "Retain all ratings; report disagreement; human adjudication required."
    )

    @model_validator(mode="after")
    def official_definitions(self) -> Self:
        if self.main_matrix != [20, 3] or self.ablation_matrix != [8, 3]:
            raise ValueError("official planned matrix is 20x3 plus 8x3; do not relabel runs")
        if self.status == "locked" and (
            set(self.variants) != {"B0", "B1", "B2"}
            or len(self.ablations) != 3
            or not self.source_record
        ):
            raise ValueError(
                "locked official protocol needs authoritative branch/ablation definitions"
            )
        if self.status == "development" and any(key in {"B0", "B1", "B2"} for key in self.variants):
            raise ValueError("development variants must not invent official B0/B1/B2 definitions")
        return self


class Rights(Contract):
    basis: str = Field(min_length=1)
    evidence_note: str = Field(min_length=1)
    declared: bool = True
    revoked: bool = False
    provider_use_allowed: bool = False
    consent_reference: str | None = None
    attribution: str | None = None
    scope: str = "Internal development"


class Artifact(Contract):
    artifact_id: str = Field(min_length=1)
    role: Literal[
        "source", "product", "character", "audio", "raw", "assembly", "export", "image", "evidence"
    ]
    path: str = Field(min_length=1)
    sha256: Hash
    mime_type: str = Field(min_length=1)
    frame_count: int | None = Field(default=None, gt=0)
    fps: int = Field(default=24, gt=0)
    width: int | None = Field(default=None, gt=0)
    height: int | None = Field(default=None, gt=0)
    rights: Rights


class CaseManifest(Contract):
    case_id: str = Field(min_length=1)
    split: Literal["development", "benchmark", "ablation"]
    target_frames: Literal[192, 384]
    input_artifact_ids: list[str] = Field(min_length=2)
    requirement_ids: list[str] = Field(min_length=1)
    requirements: dict[str, object] = Field(default_factory=dict)
    scene_frames: list[int] = Field(min_length=1, max_length=4)
    group_scene_ids: list[list[str]] = Field(min_length=1)
    requires_character: bool = False
    real_person: bool = False
    expected_outcome: Literal["passed", "needs_repair", "blocked"] = "passed"

    @model_validator(mode="after")
    def timeline(self) -> Self:
        if any(frame <= 0 or frame > 192 for frame in self.scene_frames):
            raise ValueError("scenes require 1..192 frames")
        if sum(self.scene_frames) != self.target_frames:
            raise ValueError("scene durations must sum to target frames")
        expected = [f"scene-{index + 1}" for index in range(len(self.scene_frames))]
        flattened = [scene for group in self.group_scene_ids for scene in group]
        if flattened != expected or any(not group for group in self.group_scene_ids):
            raise ValueError("groups must cover scenes exactly once in source order")
        durations = dict(zip(expected, self.scene_frames, strict=True))
        if any(sum(durations[scene] for scene in group) > 192 for group in self.group_scene_ids):
            raise ValueError("group exceeds raw clip capacity")
        return self


class Attempt(Contract):
    attempt_id: str = Field(min_length=1)
    stage: Literal["analysis", "image", "video", "inspection", "compose"]
    purpose: Literal["initial", "repair", "recheck"]
    status: Literal[
        "reserved",
        "submitted",
        "running",
        "completed",
        "succeeded",
        "failed",
        "unknown",
        "cancelled",
        "blocked",
    ]
    request_hash: Hash
    provider_receipt: str | None = None
    provider: str | None = None
    cost_status: Literal["estimated", "actual", "unknown"] = "unknown"
    cost_usd: Decimal | None = Field(default=None, ge=0, allow_inf_nan=False)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    failure_code: str | None = None
    usage: dict[str, int | float | str | None] = Field(default_factory=dict)
    model: str | None = None
    model_version: str | None = None
    prompt_version: str | None = None
    stage_mode: Mode | None = None
    profile: dict[str, object] = Field(default_factory=dict)
    estimated_usd: Decimal | None = Field(default=None, ge=0, allow_inf_nan=False)
    receipt: dict[str, int | float | str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def cost_and_time(self) -> Self:
        if (self.cost_status == "unknown") != (self.cost_usd is None):
            raise ValueError("unknown cost must be null; known costs require an amount")
        if self.started_at and self.completed_at and self.completed_at < self.started_at:
            raise ValueError("attempt completion predates start")
        return self


class SelectedRange(Contract):
    scene_id: str
    version_id: str
    raw_artifact_id: str
    in_frame: int = Field(ge=0)
    out_frame: int = Field(gt=0)
    final_in_frame: int = Field(ge=0)

    @model_validator(mode="after")
    def ordered(self) -> Self:
        if self.out_frame <= self.in_frame:
            raise ValueError("range must be nonempty")
        return self


class Capture(Contract):
    run_id: str = Field(min_length=1)
    case_id: str = Field(min_length=1)
    variant_id: str = Field(min_length=1)
    mode: Mode
    provenance_schema: Literal["smart_remake_provenance_v1"]
    outcome: Literal["accepted", "needs_repair", "failed", "blocked", "cancelled", "unknown"]
    phase: Literal["first_pass", "after_repair"] = "first_pass"
    parent_run_id: str | None = None
    project_id: str | None = None
    workspace_id: str | None = None
    code_version: str | None = None
    config_version: str | None = None
    prompt_versions: dict[str, str]
    model_versions: dict[str, str]
    attempts: list[Attempt] = Field(default_factory=list)
    selected_ranges: list[SelectedRange] = Field(default_factory=list)
    output_artifact_id: str | None = None
    assembly_id: str | None = None
    media_hash: Hash | None = None
    manifest_hash: Hash | None = None
    constraints_hash: Hash | None = None
    checker_labels: dict[str, Result] = Field(default_factory=dict)
    stage_timings_ms: dict[str, Annotated[float, Field(ge=0, allow_inf_nan=False)]] = Field(
        default_factory=dict
    )
    inspections: list[dict[str, object]] = Field(default_factory=list)
    reviews: list[dict[str, object]] = Field(default_factory=list)
    release: dict[str, object] = Field(default_factory=dict)
    failures: list[str] = Field(default_factory=list)
    media_bindings: dict[str, str] = Field(default_factory=dict)
    public_provenance: dict[str, object] = Field(default_factory=dict)


class RuntimeCaptureContext(Contract):
    """Operator manifest mapping, independent of the authenticated runtime export."""

    case_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    variant_id: str = Field(min_length=1)
    mode: Mode
    phase: Literal["first_pass", "after_repair"] = "first_pass"
    parent_run_id: str | None = None
    assembly_id: str | None = None
    code_version: str | None = None
    config_version: str | None = None
    prompt_versions: dict[str, str] = Field(default_factory=dict)


class HumanRating(Contract):
    rating_id: str = Field(min_length=1)
    blind_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    output_hash: Hash
    rubric_version: str = Field(min_length=1)
    reviewer_id: str = Field(min_length=1)
    checked_at: datetime
    scores: dict[str, Annotated[int, Field(ge=1, le=5)]] = Field(default_factory=dict)
    labels: dict[str, Result] = Field(default_factory=dict)


class PilotPreparation(Contract):
    input_only: Literal[True] = True
    status: Literal["inputs_prepared_awaiting_cap_and_disclosure"] = (
        "inputs_prepared_awaiting_cap_and_disclosure"
    )
    cap_usd: Decimal | None = Field(default=None, gt=0, allow_inf_nan=False)
    authorized: bool = False
    provider_disclosure_acknowledged: bool = False


class EvidenceBundle(Contract):
    schema_version: Literal["smart_remake_evidence_v1"] = "smart_remake_evidence_v1"
    bundle_id: str = Field(min_length=1)
    mode: Mode
    protocol: Protocol
    cases: list[CaseManifest]
    artifacts: list[Artifact]
    captures: list[Capture] = Field(default_factory=list)
    ratings: list[HumanRating] = Field(default_factory=list)
    blind_assignments: list[dict[str, str]] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    pilot_preparation: PilotPreparation | None = None
