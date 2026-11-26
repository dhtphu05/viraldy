"""Canonical reference binding and the evidence needed for an opening-state comparison."""

from __future__ import annotations

from typing import Any

from .contracts import (
    Evidence,
    Finding,
    InspectionConstraints,
    InspectionSubject,
    Observation,
    Requirement,
    ResolvedMedia,
)


def coverage_bounds(
    rule: Requirement, subject: InspectionSubject, constraints: InspectionConstraints
) -> tuple[int, int] | None:
    if subject.range is None:
        return None
    start, end = subject.range.inFrame, subject.range.outFrame
    if rule.sceneId is not None and subject.kind == "assembly":
        item: dict[str, Any] = next(
            (
                entry
                for entry in constraints.timeline.get("items", [])
                if entry.get("renderUnitId") == rule.sceneId
            ),
            {},
        )
        left, length = item.get("targetStartFrame"), item.get("targetDurationFrames")
        if (
            type(left) is not int
            or type(length) is not int
            or length <= 0
            or not start <= left < left + length <= end
        ):
            raise ValueError("Scene coverage requires its exact retained timeline window.")
        return left, left + length
    return start, end


def coverage_counts(
    finding: Finding,
    rule: Requirement,
    subject: InspectionSubject,
    constraints: InspectionConstraints,
    observations: list[Observation],
    media_id: str,
) -> tuple[list[int], int]:
    bounds = coverage_bounds(rule, subject, constraints)
    if bounds is None:
        return [], 0
    start, end = bounds
    # A scoped finding cannot inherit observations from another scene or a join check.
    observed = finding.evidence if rule.sceneId is not None else observations
    frames = sorted(
        {
            item.inFrame
            for item in observed
            if item.mediaId == media_id
            and item.mediaHash == subject.mediaHash
            and item.inFrame is not None
            and start <= item.inFrame < end
        }
    )
    return frames, end - start - len(frames)


def validate_expectation_references(
    media: ResolvedMedia, references: list[ResolvedMedia], constraints: InspectionConstraints
) -> None:
    if constraints.expectations is None:
        return
    by_role = {item.role: item for item in [media, *references] if item.role}
    for role, expected in constraints.expectations.references.items():
        actual = by_role.get(role)
        if actual is None or actual.mediaHash != expected.mediaHash:
            raise ValueError(
                "Inspection expectations bind unavailable or changed original references."
            )
    source = by_role.get("source")
    if source and any(
        scene.sourceRange.endFrame > (source.frameCount or 0)
        for scene in constraints.expectations.scenes
    ):
        raise ValueError("Inspection expectations exceed retained source frames.")


def opening_evidence_problem(
    rule: Requirement,
    evidence: list[Evidence],
    media: ResolvedMedia,
    references: list[ResolvedMedia],
) -> str | None:
    if rule.sourceFrame is None:
        return None
    by_id = {item.id: item for item in references}
    roles = {"source", "product"}
    if any(item.role == "character" for item in references):
        roles.add("character")
    cited_roles = {by_id[item.mediaId].role for item in evidence if item.mediaId in by_id}
    if not roles <= cited_roles:
        return (
            "Opening-state checks must compare the output, original source and identity references."
        )
    if not any(
        item.mediaId in by_id
        and by_id[item.mediaId].role == "source"
        and item.mediaHash == rule.sourceMediaHash
        and item.timebase == "source"
        and item.inFrame == rule.sourceFrame
        and item.outFrame == rule.sourceFrame + 1
        for item in evidence
    ):
        return "The exact original source opening frame was not compared."
    if not any(
        item.mediaId == media.id and (rule.outputFrame is None or item.inFrame == rule.outputFrame)
        for item in evidence
    ):
        return "The selected output opening was not compared."
    return None
