"""Explicit mapping of Chat A's public smart_remake_provenance_v1 projection."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from .capture import redact_private_values
from .contracts import Attempt, Capture, EvidenceBundle, RuntimeCaptureContext, SelectedRange


def capture_runtime_provenance(
    payload: Mapping[str, Any], bundle: EvidenceBundle, context: RuntimeCaptureContext
) -> Capture:
    if payload.get("schemaVersion") != "smart_remake_provenance_v1":
        raise ValueError("unsupported runtime provenance version")
    if context.mode != bundle.mode:
        raise ValueError("capture context mode must match the evidence bundle")
    if context.mode == "live" and (payload.get("run") or {}).get("mode") != "live":
        raise ValueError("live capture requires an authoritative live mode in public provenance")
    public = redact_private_values(dict(payload))
    runtime = public["run"]
    for key, expected in (
        ("caseId", context.case_id),
        ("runId", context.run_id),
        ("variant", context.variant_id),
    ):
        if runtime.get(key) is not None and runtime[key] != expected:
            raise ValueError(f"runtime {key} conflicts with locked capture context")
    case = next((item for item in bundle.cases if item.case_id == context.case_id), None)
    if case is None:
        raise ValueError("capture context has no registered case")
    bindings = _input_bindings(public["inputs"], bundle, case.input_artifact_ids)
    records = public["assemblies"].get("records", [])
    assembly_id = context.assembly_id or public["assemblies"].get("activeAssemblyId")
    assembly = next((item for item in records if item.get("id") == assembly_id), None)
    output = _artifact_for_hash(bundle, assembly["mediaHash"], "assembly") if assembly else None
    if output:
        bindings = {**bindings, "subject": output}
    approval_id = public["release"].get("activeApprovalId")
    approval: dict[str, Any] = next(
        (
            item
            for item in public["release"].get("approvals", [])
            if item.get("id") == approval_id and item.get("assemblyId") == assembly_id
        ),
        {},
    )
    reports = public["inspections"].get("reports", [])
    current_report = _current_report(
        reports, approval.get("reportId"), assembly, public["project"]["id"]
    )
    attempts = [_attempt(item) for item in public["attempts"]]
    outcome = _outcome(
        approval, public["project"].get("status"), attempts, public["inputs"], current_report
    )
    if outcome == "accepted" and assembly is None:
        raise ValueError("approved provenance has no retained assembly")
    models = {
        f"{attempt.stage}:{attempt.attempt_id}": attempt.model_version or attempt.model
        for attempt in attempts
        if attempt.model_version is not None or attempt.model is not None
    }
    prompts = context.prompt_versions or (
        {"runtime": runtime["promptVersion"]} if runtime.get("promptVersion") else {}
    )
    prompts = {
        **prompts,
        **{
            f"{attempt.stage}:{attempt.attempt_id}": attempt.prompt_version
            for attempt in attempts
            if attempt.prompt_version is not None
        },
    }
    return Capture.model_validate(
        {
            "run_id": context.run_id,
            "case_id": context.case_id,
            "variant_id": context.variant_id,
            "mode": context.mode,
            "provenance_schema": public["schemaVersion"],
            "outcome": outcome,
            "phase": context.phase,
            "parent_run_id": context.parent_run_id,
            "project_id": public["project"]["id"],
            "workspace_id": public["project"]["workspaceId"],
            "code_version": runtime.get("codeVersion") or context.code_version,
            "config_version": runtime.get("configVersion") or context.config_version,
            "prompt_versions": prompts,
            "model_versions": models,
            "attempts": attempts,
            "selected_ranges": _ranges(assembly, bundle) if assembly else [],
            "output_artifact_id": output,
            "assembly_id": assembly_id if assembly else None,
            "media_hash": assembly.get("mediaHash") if assembly else None,
            "manifest_hash": assembly.get("manifestHash") if assembly else None,
            "constraints_hash": assembly.get("constraintsHash")
            if assembly
            else public.get("constraintsHash"),
            "inspections": reports,
            "reviews": public["inspections"].get("reviews", []),
            "release": approval,
            "media_bindings": bindings,
            "failures": [str(item.get("code") or item["status"]) for item in public["failures"]],
            "stage_timings_ms": _timings(public["stageTimings"]),
            "public_provenance": public,
            "checker_labels": _checker_labels(current_report),
        }
    )


def _artifact_for_hash(bundle: EvidenceBundle, digest: str, role: str) -> str:
    matches = [
        artifact.artifact_id
        for artifact in bundle.artifacts
        if artifact.sha256 == digest and artifact.role == role
    ]
    if len(matches) != 1:
        raise ValueError(f"retain exactly one {role} artifact matching the runtime media hash")
    return matches[0]


def _input_bindings(
    inputs: list[dict[str, Any]], bundle: EvidenceBundle, expected: list[str]
) -> dict[str, str]:
    bindings = {}
    for value in inputs:
        role = value["role"]
        matches = [
            artifact.artifact_id
            for artifact in bundle.artifacts
            if artifact.sha256 == value["mediaHash"]
            and artifact.role == role
            and artifact.artifact_id in expected
        ]
        if len(matches) != 1:
            raise ValueError("retain exactly one runtime input matching the locked case inputs")
        artifact_id = matches[0]
        rights = value.get("rights") or {}
        artifact = next(item for item in bundle.artifacts if item.artifact_id == artifact_id)
        if bool(rights.get("declared")) != artifact.rights.declared or (
            bool(rights.get("revoked")) != artifact.rights.revoked
        ):
            raise ValueError("runtime rights declaration differs from case manifest")
        bindings[role] = artifact_id
    if not {"source", "product"}.issubset(bindings):
        raise ValueError("runtime export must bind original source and product")
    return bindings


def _attempt(value: dict[str, Any]) -> Attempt:
    receipt = value.get("receipt") or {}
    return Attempt.model_validate(
        {
            "attempt_id": value["id"],
            "stage": value["stage"],
            "purpose": value["purpose"],
            "status": value["status"],
            "request_hash": value["requestHash"],
            "provider": value.get("provider"),
            "model": value.get("model"),
            "model_version": value.get("modelVersion"),
            "prompt_version": value.get("promptVersion"),
            "stage_mode": value.get("stageMode"),
            "profile": value.get("profile") or {},
            "provider_receipt": value.get("providerTaskId")
            or receipt.get("requestId")
            or receipt.get("taskId"),
            "receipt": receipt,
            "usage": value.get("usage") or {},
            "estimated_usd": value.get("estimatedUsd"),
            "cost_status": value["costStatus"],
            "cost_usd": value.get("actualUsd"),
            "started_at": value.get("submittedAt") or value.get("createdAt"),
            "completed_at": value.get("completedAt"),
            "failure_code": (value.get("error") or {}).get("code"),
        }
    )


def _outcome(
    approval: dict[str, Any],
    status: str | None,
    attempts: list[Attempt],
    inputs: list[dict[str, Any]],
    current_report: dict[str, Any],
) -> str:
    if approval.get("status") == "approved":
        return "accepted"
    if not attempts and any(
        not (item.get("rights") or {}).get("declared") or (item.get("rights") or {}).get("revoked")
        for item in inputs
    ):
        return "blocked"
    if any(attempt.status == "unknown" for attempt in attempts):
        return "unknown"
    if status == "failed" or any(attempt.status == "failed" for attempt in attempts):
        return "failed"
    if current_report.get("status") == "failed":
        return "needs_repair"
    return "unknown"


def _ranges(assembly: dict[str, Any], bundle: EvidenceBundle) -> list[SelectedRange]:
    selections = {item["versionId"]: item for item in assembly["manifest"]["selections"]}
    ranges = []
    final_start = 0
    for index, item in enumerate(assembly["timeline"]["items"]):
        selection = selections[item["versionId"]]
        ranges.append(
            SelectedRange(
                scene_id=f"scene-{index + 1}",
                version_id=item["versionId"],
                raw_artifact_id=_artifact_for_hash(bundle, selection["mediaHash"], "raw"),
                in_frame=item["inFrame"],
                out_frame=item["outFrame"],
                final_in_frame=final_start,
            )
        )
        final_start += item["outFrame"] - item["inFrame"]
    return ranges


def _timings(items: list[dict[str, Any]]) -> dict[str, float]:
    stages: dict[str, float] = {}
    for item in items:
        start, end = item.get("submittedAt") or item.get("createdAt"), item.get("completedAt")
        if start is not None and end is not None:
            delta = (datetime.fromisoformat(end) - datetime.fromisoformat(start)).total_seconds()
            if delta < 0:
                raise ValueError("runtime stage timing ends before it starts")
            stage = item["stage"]
            stages[stage] = stages.get(stage, 0) + delta * 1000
    return stages


def _current_report(
    reports: list[dict[str, Any]],
    report_id: str | None,
    assembly: dict[str, Any] | None,
    project_id: str,
) -> dict[str, Any]:
    if report_id:
        return next((item for item in reports if item.get("id") == report_id), {})
    if assembly is None:
        return {}
    return next(
        (
            report
            for report in reversed(reports)
            if report.get("subject", {}).get("kind") == "assembly"
            and report.get("subject", {}).get("projectId") == project_id
            and report.get("subject", {}).get("assemblyId") == assembly["id"]
            and report.get("subject", {}).get("mediaHash") == assembly["mediaHash"]
            and report.get("manifestHash") == assembly["manifestHash"]
            and report.get("constraintsHash") == assembly["constraintsHash"]
        ),
        {},
    )


def _checker_labels(report: dict[str, Any]) -> dict[str, str]:
    grouped: dict[str, list[str]] = {}
    for finding in report.get("findings", []):
        category = finding["category"]
        grouped[category] = [*grouped.get(category, []), finding["status"]]
    return {
        category: next(
            (
                status
                for status in ("failed", "insufficient_evidence", "needs_review")
                if status in statuses
            ),
            "passed",
        )
        for category, statuses in grouped.items()
    }
