"""Deterministic report binding; model claims never establish evidence provenance."""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from .anchors import require_observed_anchors, validate_observation_anchors
from .contracts import (
    Evidence,
    InspectionConstraints,
    InspectionReport,
    InspectionStatus,
    InspectionSubject,
    ResolvedMedia,
)
from .expectations import (
    coverage_bounds,
    coverage_counts,
    opening_evidence_problem,
    validate_expectation_references,
)
from .requirements import TECHNICAL_REQUIREMENT, requirements_for, temporal_review_required

HARD_CATEGORIES = {"technical", "rights", "consent", "policy"}


def combined_status(statuses: list[InspectionStatus]) -> InspectionStatus:
    if not statuses:
        return "insufficient_evidence"
    if "failed" in statuses:
        return "failed"
    if "insufficient_evidence" in statuses:
        return "insufficient_evidence"
    if "needs_review" in statuses:
        return "needs_review"
    return "passed"


def resolved_media(value: ResolvedMedia | dict[str, Any]) -> ResolvedMedia:
    media = ResolvedMedia.model_validate(value)
    if hashlib.sha256(media.bytes).hexdigest() != media.mediaHash:
        raise ValueError("Resolved media bytes do not match their retained hash.")
    if media.mimeType.startswith("image/"):
        if media.frameCount is not None or media.fps is not None or media.range is not None:
            raise ValueError("Image media cannot carry video timing.")
    elif media.frameCount is None or media.fps != 24:
        raise ValueError("Video media requires a positive canonical frame count and 24-fps clock.")
    return media


def validate_report_binding(
    report: InspectionReport | dict[str, Any],
    subject: InspectionSubject | dict[str, Any],
    media: ResolvedMedia | dict[str, Any],
    references: Sequence[ResolvedMedia | dict[str, Any]],
    constraints: InspectionConstraints | dict[str, Any],
) -> InspectionReport:
    """Reject stale context and evidence outside real media/observations; return typed report."""
    current = InspectionSubject.model_validate(subject)
    limits = InspectionConstraints.model_validate(constraints)
    value = InspectionReport.model_validate(report)
    owned = resolved_media(media)
    refs = [resolved_media(item) for item in references]
    validate_expectation_references(owned, refs, limits)
    validate_observation_anchors(current, owned, refs, limits.observationAnchors)
    if (
        value.subject != current
        or current.mediaHash != owned.mediaHash
        or value.constraintsHash != limits.constraintsHash
        or value.manifestHash != limits.manifestHash
        or value.expectationsHash != limits.expectationsHash
    ):
        raise ValueError(
            "Inspection report binds different content, trim, neighbors, "
            "constraints or expectations."
        )
    checked_at = datetime.fromisoformat(value.checkedAt.replace("Z", "+00:00"))
    offset = checked_at.utcoffset()
    if offset is None or offset.total_seconds() != 0:
        raise ValueError("Inspection timestamps must include the UTC timezone.")
    if current.range and current.range.outFrame > (owned.frameCount or 0):
        raise ValueError("The subject range exceeds its actual media.")
    by_id: dict[str, ResolvedMedia] = {}
    for asset in [owned, *refs]:
        if asset.id in by_id and by_id[asset.id].mediaHash != asset.mediaHash:
            raise ValueError("Media IDs must identify exactly one retained asset.")
        by_id[asset.id] = asset
    observed = {item.id: item for item in value.observations}
    if len(observed) != len(value.observations):
        raise ValueError("Observation identifiers must be unique.")

    def evidence_valid(item: Evidence, *, require_sample: bool) -> None:
        asset = by_id.get(item.mediaId)
        if asset is None or item.mediaHash != asset.mediaHash:
            raise ValueError("Evidence must identify existing owned media and its current hash.")
        if asset.mimeType.startswith("image/"):
            if item.inFrame is not None:
                raise ValueError("Image evidence cannot contain a frame clock.")
        else:
            if (
                item.inFrame is None
                or item.outFrame is None
                or item.outFrame > (asset.frameCount or 0)
            ):
                raise ValueError("Video evidence must be inside decoded media bounds.")
            expected_clock = (
                current.range.timebase
                if asset.id == owned.id and current.range
                else "source"
                if asset.role == "source"
                else "raw_group"
            )
            if item.timebase != expected_clock:
                raise ValueError("Evidence uses an unrelated media clock.")
            if (
                asset.id == owned.id
                and current.range
                and (item.inFrame < current.range.inFrame or item.outFrame > current.range.outFrame)
            ):
                raise ValueError("Evidence falls outside the selected subject range.")
            if asset.range and (
                item.inFrame < asset.range.inFrame or item.outFrame > asset.range.outFrame
            ):
                raise ValueError("Reference evidence falls outside its selected retained range.")
        if require_sample and not item.sampleId:
            raise ValueError("Semantic evidence must cite an actual observation.")
        if item.sampleId:
            sample = observed.get(item.sampleId)
            if sample is None or any(
                getattr(sample, key) != getattr(item, key)
                for key in ("mediaId", "mediaHash", "inFrame", "outFrame", "timebase")
            ):
                raise ValueError("Evidence does not match its cited observation.")

    for observation in value.observations:
        evidence_valid(observation, require_sample=False)
        if observation.inFrame is not None and observation.outFrame != observation.inFrame + 1:
            raise ValueError("A sampled image observes exactly one frame.")
    require_observed_anchors(
        limits.observationAnchors,
        value.observations,
        allow_missing=all(
            finding.category in HARD_CATEGORIES or finding.status == "insufficient_evidence"
            for finding in value.findings
        )
        and all(
            coverage.requirementId == TECHNICAL_REQUIREMENT.id
            or coverage.status == "insufficient_evidence"
            for coverage in value.coverage
        ),
    )
    ids = [finding.id for finding in value.findings]
    coverage_ids = [item.requirementId for item in value.coverage]
    if len(set(ids)) != len(ids) or len(set(coverage_ids)) != len(coverage_ids):
        raise ValueError("Finding and coverage identifiers must be unique.")
    if not value.findings or not value.coverage:
        raise ValueError("An inspection report requires explicit checks and coverage.")
    findings_by_requirement = {item.requirementId: item for item in value.findings}
    if len(findings_by_requirement) != len(value.findings) or set(coverage_ids) != set(
        findings_by_requirement
    ):
        raise ValueError("Every requirement needs exactly one finding and coverage record.")
    expected_rules = {
        rule.id: rule for rule in [TECHNICAL_REQUIREMENT, *requirements_for(current, limits)]
    }
    if set(findings_by_requirement) != set(expected_rules):
        raise ValueError("The report omitted or renamed required inspection checks.")
    expected_na = set() if limits.requirements.get("requiresCharacter") is True else {"character"}
    not_applicable = [item.requirementId for item in value.notApplicableRequirements]
    if (
        set(not_applicable) != expected_na
        or len(set(not_applicable)) != len(not_applicable)
        or any(not item.reason.strip() for item in value.notApplicableRequirements)
    ):
        raise ValueError("Not-applicable checks must match the saved requirements.")
    for finding in value.findings:
        rule = expected_rules[finding.requirementId]
        if finding.category != rule.category or finding.expected != rule.expected:
            raise ValueError("Finding category and expectation must match the saved requirements.")
        hard = finding.category in HARD_CATEGORIES and finding.status != "passed"
        if (
            finding.blocking != hard
            or finding.hardBlocking != hard
            or finding.severity
            != ("info" if finding.status == "passed" else "error" if hard else "warning")
        ):
            raise ValueError("Finding blocking and severity must follow deterministic rules.")
        if finding.status == "passed" and not finding.evidence:
            raise ValueError("Passing checks require observed evidence.")
        if finding.status == "passed" and not any(
            item.mediaId == owned.id for item in finding.evidence
        ):
            raise ValueError("Passing findings must observe the selected output.")
        if finding.status == "passed" and temporal_review_required(
            rule, is_video=bool(current.range)
        ):
            raise ValueError("Sampled images cannot pass a complete temporal or audio requirement.")
        if finding.status == "passed" and finding.category in {"product", "character"}:
            if not any(
                by_id[item.mediaId].role == finding.category
                for item in finding.evidence
                if item.mediaId in by_id
            ):
                raise ValueError("Identity checks must compare the original reference role.")
        if finding.status == "passed":
            problem = opening_evidence_problem(rule, finding.evidence, owned, refs)
            if problem:
                raise ValueError(problem)
        for item in finding.evidence:
            evidence_valid(item, require_sample=finding.category not in HARD_CATEGORIES)
        bounds = coverage_bounds(rule, current, limits)
        if (
            rule.sceneId is not None
            and bounds is not None
            and any(
                item.mediaId == owned.id
                and item.inFrame is not None
                and (item.inFrame < bounds[0] or item.outFrame is None or item.outFrame > bounds[1])
                for item in finding.evidence
            )
        ):
            raise ValueError("Scene evidence falls outside its retained timeline window.")
    for coverage in value.coverage:
        finding = findings_by_requirement[coverage.requirementId]
        if coverage.status != finding.status or coverage.evidence != finding.evidence:
            raise ValueError("Coverage must describe the matching requirement finding.")
        for item in coverage.evidence:
            evidence_valid(item, require_sample=finding.category not in HARD_CATEGORIES)
        if coverage.sampledFrames != sorted(set(coverage.sampledFrames)):
            raise ValueError("Sampled frame coverage must be sorted and unique.")
        frames, unobserved = coverage_counts(
            finding,
            expected_rules[finding.requirementId],
            current,
            limits,
            value.observations,
            owned.id,
        )
        if coverage.sampledFrames != frames or coverage.unobservedFrames != unobserved:
            raise ValueError("Coverage must count only the actual selected output observations.")
    if value.status != combined_status([item.status for item in value.findings]):
        raise ValueError("Report status must reflect every check, including uncertainty.")
    return value
