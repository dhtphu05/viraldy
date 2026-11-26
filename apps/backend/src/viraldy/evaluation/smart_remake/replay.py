from __future__ import annotations

import random
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path
from statistics import mean, pstdev
from typing import Any

from .capture import canonical_hash, sha256_bytes
from .contracts import Attempt, CaseManifest, EvidenceBundle, Protocol


def _unique(values: list[str], label: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"duplicate {label}")


def validate_bundle(bundle: EvidenceBundle, root: Path) -> None:
    if bundle.pilot_preparation is not None and bundle.captures:
        raise ValueError("input-only pilot preparation cannot contain captured outputs")
    _unique([case.case_id for case in bundle.cases], "case IDs")
    _unique([artifact.artifact_id for artifact in bundle.artifacts], "artifact IDs")
    _unique([capture.run_id for capture in bundle.captures], "run IDs")
    _unique([rating.rating_id for rating in bundle.ratings], "rating IDs")
    artifacts = {artifact.artifact_id: artifact for artifact in bundle.artifacts}
    cases = {case.case_id: case for case in bundle.cases}
    runs = {run.run_id: run for run in bundle.captures}
    if bundle.protocol.status == "locked" and (
        sum(case.split == "benchmark" for case in bundle.cases) != 20
        or sum(case.split == "ablation" for case in bundle.cases) != 8
        or any(case.split == "development" for case in bundle.cases)
    ):
        raise ValueError("locked protocol requires 20 benchmark pairs and 8 ablation pairs")
    for artifact in bundle.artifacts:
        candidate = Path(artifact.path)
        path = (root / candidate).resolve()
        if candidate.is_absolute() or not path.is_relative_to(root.resolve()):
            raise ValueError(f"artifact path escapes bundle: {artifact.artifact_id}")
        if not path.is_file():
            raise ValueError(f"missing artifact: {artifact.artifact_id}")
        if sha256_bytes(path.read_bytes()) != artifact.sha256:
            raise ValueError(f"artifact hash mismatch: {artifact.artifact_id}")
    for case in bundle.cases:
        _validate_case(case, artifacts, bundle.mode == "live")
    for run in bundle.captures:
        if run.case_id not in cases:
            raise ValueError(f"unknown case in capture: {run.run_id}")
        selectors = (
            bundle.protocol.ablations
            if cases[run.case_id].split == "ablation"
            else bundle.protocol.variants
        )
        if run.variant_id not in selectors:
            raise ValueError(f"undefined protocol variant: {run.variant_id}")
        if run.mode != bundle.mode:
            raise ValueError("fixture/mock/live captures must not be mixed")
        if cases[run.case_id].expected_outcome == "blocked" and (
            run.outcome != "blocked"
            or run.attempts
            or run.output_artifact_id
            or run.assembly_id
            or run.release
        ):
            raise ValueError(
                "blocked negative-control cases cannot contain generation or acceptance"
            )
        _unique([attempt.attempt_id for attempt in run.attempts], "attempt IDs within run")
        if run.phase == "after_repair":
            parent = runs.get(run.parent_run_id or "")
            if (
                parent is None
                or parent.run_id == run.run_id
                or (parent.case_id != run.case_id or parent.variant_id != run.variant_id)
            ):
                raise ValueError("repair requires a distinct parent in the same case and variant")
        if run.output_artifact_id:
            output = artifacts.get(run.output_artifact_id)
            if output is None or output.role != "assembly" or output.sha256 != run.media_hash:
                raise ValueError(f"output artifact/hash mismatch: {run.run_id}")
            if output.frame_count != cases[run.case_id].target_frames:
                raise ValueError("assembly frames do not match planned case")
            if output.fps != 24:
                raise ValueError("assembly timing requires 24 fps")
        if run.outcome == "accepted" and not all(
            (run.output_artifact_id, run.assembly_id, run.manifest_hash, run.constraints_hash)
        ):
            raise ValueError("accepted capture requires bound assembly")
        _validate_ranges(run.selected_ranges, cases[run.case_id], artifacts)
        if bundle.mode == "live":
            _validate_live_run(run, artifacts, cases[run.case_id], root)
        elif run.outcome == "accepted" and (run.inspections or run.release):
            _validate_release_binding(run, artifacts, cases[run.case_id], root)
    _all_attempts(bundle)
    _validate_ratings(bundle, runs)


def _validate_case(case: CaseManifest, artifacts: dict[str, Any], live: bool) -> None:
    if any(key not in artifacts for key in case.input_artifact_ids):
        raise ValueError(f"missing case input artifact: {case.case_id}")
    inputs = [artifacts[key] for key in case.input_artifact_ids]
    roles = {artifact.role for artifact in inputs}
    if not {"source", "product"}.issubset(roles):
        raise ValueError("case requires source and product artifacts")
    if case.requires_character and "character" not in roles:
        raise ValueError("case requires original character artifact")
    for artifact in inputs:
        if case.expected_outcome != "blocked" and (
            not artifact.rights.declared or artifact.rights.revoked
        ):
            raise ValueError(f"case lacks declared rights: {case.case_id}")
        if live and (
            not artifact.rights.provider_use_allowed
            or not artifact.rights.declared
            or artifact.rights.revoked
        ):
            raise ValueError("live case lacks provider-use rights")
        if (
            live
            and case.real_person
            and artifact.role == "character"
            and (not artifact.rights.consent_reference)
        ):
            raise ValueError("real-person live case requires consent reference")


def _validate_ranges(ranges: list[Any], case: CaseManifest, artifacts: dict[str, Any]) -> None:
    if not ranges:
        return
    if len(ranges) != len(case.scene_frames):
        raise ValueError("selected ranges must cover every planned scene")
    final_start = 0
    for index, selected in enumerate(ranges):
        raw = artifacts.get(selected.raw_artifact_id)
        if raw is None or raw.frame_count is None or raw.role != "raw":
            raise ValueError("selected range requires raw artifact")
        if selected.out_frame > raw.frame_count:
            raise ValueError("selected range exceeds raw media")
        if raw.fps != 24:
            raise ValueError("raw clock mapping requires 24 fps normalized media")
        if selected.scene_id != f"scene-{index + 1}" or (
            selected.out_frame - selected.in_frame != case.scene_frames[index]
            or selected.final_in_frame != final_start
        ):
            raise ValueError("scene/raw/final clock mapping differs from plan")
        final_start += case.scene_frames[index]


def _validate_live_run(run: Any, artifacts: dict[str, Any], case: CaseManifest, root: Path) -> None:
    if not run.project_id or not run.workspace_id or not run.attempts:
        raise ValueError("live provenance requires owned project/workspace and attempts")
    for attempt in run.attempts:
        if attempt.stage != "compose" and attempt.provider in {"fixture", "mock", "fake"}:
            raise ValueError("live attempts cannot use fixture/mock/fake provider provenance")
        if (
            attempt.stage != "compose"
            and attempt.status in {"completed", "succeeded"}
            and (
                not attempt.provider_receipt
                or attempt.provider in {None, "fixture", "mock", "fake"}
            )
        ):
            raise ValueError("completed live attempt requires genuine provider receipt")
    if run.outcome == "accepted" and (
        not run.selected_ranges or not run.inspections or not run.release
    ):
        raise ValueError("live accepted capture requires ranges, inspections and release records")
    if run.outcome == "accepted":
        _validate_release_binding(run, artifacts, case, root)


def _validate_release_binding(
    run: Any, artifacts: dict[str, Any], case: CaseManifest, root: Path
) -> None:
    # This schema is provider-independent; do not import Inspector execution or gateway modules.
    from viraldy.modules.smart_remake.inspection.contracts import InspectionReport
    from viraldy.modules.smart_remake.inspection.validation import validate_report_binding

    approval = run.release
    expected = {
        "status": "approved",
        "assemblyId": run.assembly_id,
        "mediaHash": run.media_hash,
        "manifestHash": run.manifest_hash,
        "constraintsHash": run.constraints_hash,
    }
    if any(approval.get(key) != value for key, value in expected.items()) or not all(
        approval.get(key)
        for key in (
            "actorId",
            "approvedAt",
            "reportId",
            "inspectionHash",
            "policyHash",
            "checkerVersion",
            "rubricVersion",
        )
    ):
        raise ValueError(
            "live release approval must bind the exact assembly and inspection context"
        )
    raw_report = next(
        (item for item in run.inspections if item.get("id") == approval["reportId"]), None
    )
    # A appends these documented lifecycle fields after validating the Inspector model.
    runtime_extensions = {"operationId", "actorId", "contextHash", "subjectRequest"}
    report = (
        InspectionReport.model_validate(
            {key: value for key, value in raw_report.items() if key not in runtime_extensions}
        )
        if raw_report is not None
        else None
    )
    if report is None or (
        report.subject.kind != "assembly"
        or report.subject.projectId != run.project_id
        or report.subject.assemblyId != run.assembly_id
        or report.subject.mediaHash != run.media_hash
        or report.manifestHash != run.manifest_hash
        or report.constraintsHash != run.constraints_hash
        or report.checkerVersion != approval["checkerVersion"]
        or report.rubricVersion != approval["rubricVersion"]
        or not report.coverage
        or not report.findings
        or report.status == "insufficient_evidence"
    ):
        raise ValueError("live inspection report is stale or incomplete")
    if canonical_hash(raw_report) != approval["inspectionHash"]:
        raise ValueError("live inspection content hash differs from approval")
    if report.subject.range is None or (
        report.subject.range.timebase != "final"
        or report.subject.range.inFrame != 0
        or report.subject.range.outFrame != case.target_frames
    ):
        raise ValueError("live final inspection must cover the exact assembly frame range")
    if not set(case.requirement_ids).issubset({item.requirementId for item in report.findings}):
        raise ValueError("live report omits confirmed case requirements")
    bindings = run.media_bindings or {key: key for key in artifacts}
    resolved: dict[str, dict[str, Any]] = {}
    for identity, artifact_id in bindings.items():
        artifact = artifacts.get(artifact_id)
        if artifact is None:
            raise ValueError("inspection media binding refers to missing retained artifact")
        asset = {
            "id": identity,
            "mediaHash": artifact.sha256,
            "bytes": (root / artifact.path).read_bytes(),
            "mimeType": artifact.mime_type,
        }
        if artifact.mime_type.startswith("video/"):
            asset.update(frameCount=artifact.frame_count, fps=artifact.fps)
        if artifact.role in {"source", "product", "character"}:
            asset["role"] = artifact.role
        if artifact_id == run.output_artifact_id:
            asset["range"] = report.subject.range.model_dump(mode="json")
        resolved[identity] = asset
    outputs = [value for key, value in resolved.items() if bindings[key] == run.output_artifact_id]
    if len(outputs) != 1:
        raise ValueError("inspection needs exactly one output media identity")
    references = [
        value
        for key, value in resolved.items()
        if bindings[key] in case.input_artifact_ids
        and value["mimeType"].startswith(("video/", "image/"))
    ]
    validate_report_binding(
        report,
        report.subject,
        outputs[0],
        references,
        {
            "constraintsHash": run.constraints_hash,
            "manifestHash": run.manifest_hash,
            "requirements": case.requirements,
            "frameCount": case.target_frames,
        },
    )
    for finding in report.findings:
        if not finding.evidence or finding.status == "insufficient_evidence":
            raise ValueError("live finding lacks usable retained evidence")
        if finding.status == "passed":
            continue
        if finding.hardBlocking or finding.category in {"technical", "rights", "consent", "policy"}:
            raise ValueError("live hard failure cannot be accepted by review")
        review: dict[str, Any] = next(
            (
                item
                for item in reversed(run.reviews)
                if item.get("reportId") == report.id and item.get("findingId") == finding.id
            ),
            {},
        )
        if review.get("decision") != "accept" or not all(
            review.get(key) for key in ("reason", "actorId", "reviewedAt")
        ):
            raise ValueError("live semantic uncertainty requires recorded reasoned human review")


def _validate_ratings(bundle: EvidenceBundle, runs: dict[str, Any]) -> None:
    assignments: dict[str, dict[str, str]] = {}
    for item in bundle.blind_assignments:
        if item.get("blind_id") in assignments:
            raise ValueError("duplicate blind assignment")
        assignments[item.get("blind_id", "")] = item
    seen: set[tuple[str, str]] = set()
    for rating in bundle.ratings:
        run = runs.get(rating.run_id)
        assignment = assignments.get(rating.blind_id)
        if (
            run is None
            or run.media_hash != rating.output_hash
            or assignment is None
            or (
                assignment.get("run_id") != rating.run_id
                or assignment.get("output_hash") != rating.output_hash
                or rating.rubric_version != bundle.protocol.rubric_version
            )
        ):
            raise ValueError("rating must bind exact blinded output/hash/rubric")
        key = (rating.run_id, rating.reviewer_id)
        if key in seen:
            raise ValueError("duplicate reviewer rating for output")
        seen.add(key)
        case = next(case for case in bundle.cases if case.case_id == run.case_id)
        if not case.requires_character and (
            "character" in rating.scores or "character" in rating.labels
        ):
            raise ValueError("character is N/A for this case")


def _all_attempts(bundle: EvidenceBundle) -> list[Attempt]:
    attempts: dict[str, Attempt] = {}
    owners: dict[str, str] = {}
    runs = {run.run_id: run for run in bundle.captures}
    for run in bundle.captures:
        ancestor = run
        visited = {run.run_id}
        while ancestor.parent_run_id:
            if ancestor.parent_run_id in visited or ancestor.parent_run_id not in runs:
                raise ValueError("repair ancestry is cyclic or incomplete")
            visited.add(ancestor.parent_run_id)
            ancestor = runs[ancestor.parent_run_id]
        for attempt in run.attempts:
            previous = attempts.get(attempt.attempt_id)
            if previous is not None and previous != attempt:
                raise ValueError("shared attempt ID has conflicting provenance")
            if previous is not None and owners[attempt.attempt_id] != ancestor.run_id:
                raise ValueError("shared attempt ID requires common repair ancestry")
            attempts[attempt.attempt_id] = attempt
            owners[attempt.attempt_id] = ancestor.run_id
    return [attempts[key] for key in sorted(attempts)]


def guard_live_pilot(
    protocol: Protocol,
    cases: list[CaseManifest],
    *,
    cap_usd: Decimal | None,
    authorized: bool,
) -> None:
    if not authorized:
        raise ValueError("explicit live-run authorization is required")
    if cap_usd is None or not cap_usd.is_finite() or cap_usd <= 0:
        raise ValueError("a positive explicit USD cap is required; there is no default spend")
    if protocol.status == "pending":
        raise ValueError("protocol definitions are pending")
    if not cases:
        raise ValueError("at least one rights-backed case is required")
    if any(case.split != "development" for case in cases):
        raise ValueError("this pilot guard accepts development cases only; no official batch")
    if any(case.expected_outcome == "blocked" for case in cases):
        raise ValueError("blocked rights controls are offline only and cannot be submitted live")


def blind_assignments(bundle: EvidenceBundle, *, seed: str) -> list[dict[str, str]]:
    eligible = sorted(
        (run for run in bundle.captures if run.output_artifact_id), key=lambda run: run.run_id
    )
    random.Random(seed).shuffle(eligible)  # noqa: S311 - reproducible blinded order, not security
    return [
        {
            "blind_id": canonical_hash([seed, run.run_id, run.media_hash])[:16],
            "run_id": run.run_id,
            "output_hash": run.media_hash or "",
        }
        for run in eligible
    ]


def replay_bundle(bundle: EvidenceBundle, root: Path) -> dict[str, Any]:
    validate_bundle(bundle, root)
    attempts = _all_attempts(bundle)
    accepted = len(
        {(run.assembly_id, run.media_hash) for run in bundle.captures if run.outcome == "accepted"}
    )
    known = sum(
        (attempt.cost_usd or Decimal(0) for attempt in attempts if attempt.cost_status == "actual"),
        Decimal(0),
    )
    estimated_amount = sum(
        (
            attempt.cost_usd or Decimal(0)
            for attempt in attempts
            if attempt.cost_status == "estimated"
        ),
        Decimal(0),
    )
    unknown = sum(attempt.cost_status == "unknown" for attempt in attempts)
    estimated = sum(attempt.cost_status == "estimated" for attempt in attempts)
    ratings = [score for rating in bundle.ratings for score in rating.scores.values()]
    categories = sorted({category for rating in bundle.ratings for category in rating.scores})
    comparison = _checker_metrics(bundle)
    planned_keys = {
        f"{case.case_id}/{variant}"
        for case in bundle.cases
        for variant in (
            bundle.protocol.ablations if case.split == "ablation" else bundle.protocol.variants
        )
    }
    captured_keys = {
        f"{run.case_id}/{run.variant_id}" for run in bundle.captures if run.phase == "first_pass"
    }
    stage_timings: dict[str, list[float]] = defaultdict(list)
    for run in bundle.captures:
        for stage, timing in run.stage_timings_ms.items():
            stage_timings[stage].append(timing)
    return {
        "schema_version": "smart_remake_report_v1",
        "bundle_id": bundle.bundle_id,
        "bundle_hash": canonical_hash(bundle.model_dump(mode="json")),
        "mode": bundle.mode,
        "live_verified": False,
        "pilot_preparation": bundle.pilot_preparation.model_dump(mode="json")
        if bundle.pilot_preparation is not None
        else None,
        "mode_meaning": "intended future execution; input-only with zero captures"
        if bundle.pilot_preparation is not None
        else "provenance of retained captured candidates",
        "notes": bundle.notes,
        "protocol": {
            "id": bundle.protocol.protocol_id,
            "status": bundle.protocol.status,
            "official_main_matrix": [20, 3],
            "official_ablation_matrix": [8, 3],
        },
        "planned_runs": len(planned_keys),
        "captured_runs": len(bundle.captures),
        "missing_runs": len(planned_keys - captured_keys),
        "missing_run_keys": sorted(planned_keys - captured_keys),
        "missing_metadata": [
            {
                "run_id": run.run_id,
                "fields": [
                    field
                    for field in (
                        "code_version",
                        "config_version",
                        "prompt_versions",
                        "model_versions",
                    )
                    if not getattr(run, field)
                ],
            }
            for run in bundle.captures
            if not all(
                (run.code_version, run.config_version, run.prompt_versions, run.model_versions)
            )
        ],
        "accepted_outputs": accepted,
        "attempts": len(attempts),
        "outcomes": dict(sorted(Counter(run.outcome for run in bundle.captures).items())),
        "attempt_statuses": dict(sorted(Counter(attempt.status for attempt in attempts).items())),
        "failures": [
            {"run_id": run.run_id, "codes": run.failures}
            for run in sorted(bundle.captures, key=lambda item: item.run_id)
            if run.failures
        ],
        "attempt_failures": [
            {"attempt_id": attempt.attempt_id, "code": attempt.failure_code}
            for attempt in attempts
            if attempt.failure_code
        ],
        "cost": {
            "known_usd": str(known),
            "estimated_usd": str(estimated_amount),
            "unreconciled_reserve_estimates_usd": str(
                sum(
                    (
                        attempt.estimated_usd or Decimal(0)
                        for attempt in attempts
                        if attempt.cost_status == "unknown"
                    ),
                    Decimal(0),
                )
            ),
            "unknown_attempts": unknown,
            "estimated_attempts": estimated,
            "actual_attempts": len(attempts) - unknown - estimated,
            "per_accepted_output_usd": str(known / accepted)
            if accepted and not unknown and not estimated
            else None,
        },
        "human_ratings": {
            "status": "measured" if ratings else "unmeasured",
            "ratings": len(bundle.ratings),
            "mean": mean(ratings) if ratings else None,
            "dispersion": pstdev(ratings) if ratings else None,
            "missing_output_labels": sum(
                bool(run.output_artifact_id)
                and not any(rating.run_id == run.run_id for rating in bundle.ratings)
                for run in bundle.captures
            ),
            "categories": {
                category: _summary(
                    [
                        rating.scores[category]
                        for rating in bundle.ratings
                        if category in rating.scores
                    ]
                )
                for category in categories
            },
        },
        "checker": comparison,
        "stage_timings_ms": {
            stage: _summary(values) for stage, values in sorted(stage_timings.items())
        },
        "paired_differences": _paired_differences(bundle),
        "phases": dict(sorted(Counter(run.phase for run in bundle.captures).items())),
        "limitations": [
            "Fixture/mock results do not establish live provider quality.",
            "Semantic labels are observations, never correctness probabilities.",
            "Official B0/B1/B2 and ablations pending until authoritative protocol lock."
            if bundle.protocol.status != "locked"
            else "Results apply only to this locked dataset and retained judgments.",
        ],
    }


def _summary(values: list[Any]) -> dict[str, Any]:
    return {
        "status": "measured" if values else "unmeasured",
        "n": len(values),
        "mean": mean(values) if values else None,
        "dispersion": pstdev(values) if values else None,
    }


def _rate(numerator: int, denominator: int) -> dict[str, Any]:
    return {
        "status": "measured" if denominator else "unmeasured",
        "numerator": numerator,
        "denominator": denominator,
        "value": numerator / denominator if denominator else None,
    }


def _checker_metrics(bundle: EvidenceBundle) -> dict[str, Any]:
    runs = {run.run_id: run for run in bundle.captures}
    fp = fn = negative = positive = 0
    labels: dict[tuple[str, str], set[str]] = defaultdict(set)
    for rating in bundle.ratings:
        for category, expected in rating.labels.items():
            labels[(rating.run_id, category)].add(expected)
            observed = runs[rating.run_id].checker_labels.get(category)
            if observed not in {"passed", "failed"}:
                continue
            if expected == "passed":
                negative += 1
                fp += observed == "failed"
            elif expected == "failed":
                positive += 1
                fn += observed == "passed"
    return {
        "false_positive_rate": _rate(fp, negative),
        "false_negative_rate": _rate(fn, positive),
        "disagreement_pairs": sum(len(values) > 1 for values in labels.values()),
        "label_units": "individual reviewer/category judgments; conflicts need adjudication",
    }


def _paired_differences(bundle: EvidenceBundle) -> list[dict[str, Any]]:
    runs = {run.run_id: run for run in bundle.captures}
    values: dict[tuple[str, str, str, str], list[int]] = defaultdict(list)
    for rating in bundle.ratings:
        run = runs[rating.run_id]
        for category, score in rating.scores.items():
            values[(run.case_id, run.variant_id, run.phase, category)].append(score)
    variants = sorted(bundle.protocol.variants)
    strata = sorted(
        {
            (runs[rating.run_id].phase, category)
            for rating in bundle.ratings
            for category in rating.scores
        }
    )
    result = []
    for index, left in enumerate(variants):
        for right in variants[index + 1 :]:
            for phase, category in strata:
                differences = [
                    mean(values[(case.case_id, right, phase, category)])
                    - mean(values[(case.case_id, left, phase, category)])
                    for case in bundle.cases
                    if values[(case.case_id, right, phase, category)]
                    and values[(case.case_id, left, phase, category)]
                ]
                result.append(
                    {
                        "left": left,
                        "right": right,
                        "phase": phase,
                        "category": category,
                        "direction": "right minus left",
                        **_summary(differences),
                    }
                )
    return result
