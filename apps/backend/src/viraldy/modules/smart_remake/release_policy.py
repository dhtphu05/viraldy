"""Fail-closed approval and export binding for server-validated inspection reports."""

from __future__ import annotations

import copy
import importlib
from typing import Any
from uuid import uuid4

from viraldy.shared.errors.base import AppError

from .assembly_snapshots import active_assembly, content_hash
from .repair_media import now_iso

HARD_CATEGORIES = {"technical", "rights", "consent", "authorization", "policy", "safety"}


def _blocked(message: str, code: str = "SMART_REMAKE_RELEASE_BLOCKED") -> None:
    raise AppError(code, message, 409)


def _current(
    p0: dict[str, Any],
    *,
    assembly_id: str,
    constraints_hash: str,
    current_manifest_hash: str,
    rights_valid: bool,
) -> dict[str, Any]:
    if rights_valid is not True or p0.get("deletion", {}).get("status") not in (
        None,
        "none",
        "cancelled",
    ):
        _blocked(
            "Current asset rights and an active project are required.",
            "SMART_REMAKE_RIGHTS_REQUIRED",
        )
    assembly = active_assembly(p0)
    if (
        assembly["id"] != assembly_id
        or not constraints_hash
        or assembly["constraintsHash"] != constraints_hash
        or assembly["manifestHash"] != current_manifest_hash
        or content_hash(assembly["manifest"]) != current_manifest_hash
    ):
        _blocked("The current assembly or its requirements changed.", "SMART_REMAKE_APPROVAL_STALE")
    technical, frames = assembly["technicalCheck"], assembly["timeline"]["totalFrames"]
    if (
        technical.get("status") != "passed"
        or technical.get("mediaHash") != assembly["mediaHash"]
        or technical.get("frameCount") != frames
        or frames not in (192, 288, 384)
    ):
        _blocked("The final assembly must pass its frame-accurate technical check.")
    return assembly


def _report(p0: dict[str, Any], report_id: str) -> dict[str, Any]:
    reports: list[dict[str, Any]] = p0.get("inspections", {}).get("reports", [])
    for report in reports:
        if report.get("id") == report_id:
            return report
    _blocked("A current final assembly inspection is required.")
    raise AssertionError("unreachable")


def _reviews(p0: dict[str, Any], report_id: str) -> list[dict[str, Any]]:
    return [
        r for r in p0.get("inspections", {}).get("reviews", []) if r.get("reportId") == report_id
    ]


def _evidence_valid(finding: dict[str, Any], assembly: dict[str, Any]) -> bool:
    observed = False
    evidence = finding.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        return False
    for item in evidence:
        if not isinstance(item, dict) or not item.get("mediaHash"):
            return False
        if item["mediaHash"] != assembly["mediaHash"]:
            continue  # Original reference evidence is checked by the Inspector validator.
        selected = item.get("range") or item
        start, end = selected.get("inFrame"), selected.get("outFrame")
        if (
            type(start) is not int
            or type(end) is not int
            or not 0 <= start < end <= assembly["timeline"]["totalFrames"]
        ):
            return False
        observed = True
    return observed


def _inspectable(
    report: dict[str, Any], assembly: dict[str, Any], reviews: list[dict[str, Any]]
) -> None:
    subject = report.get("subject", {})
    if not assembly.get("expectationsHash"):
        _blocked(
            "Assemble and inspect a preview with the current generation expectations.",
            "SMART_REMAKE_ASSEMBLY_EXPECTATIONS_REQUIRED",
        )
    profile = importlib.import_module(
        ".inspection.public", package=__package__
    ).inspection_profile()
    if (
        subject.get("kind") != "assembly"
        or subject.get("projectId") != assembly["projectId"]
        or subject.get("assemblyId") != assembly["id"]
        or subject.get("mediaHash") != assembly["mediaHash"]
        or report.get("constraintsHash") != assembly["constraintsHash"]
        or report.get("manifestHash") != assembly["manifestHash"]
        or report.get("expectationsHash") != assembly.get("expectationsHash")
        or any(report.get(key) != value for key, value in profile.items())
    ):
        _blocked(
            "Inspection must bind the current final assembly.", "SMART_REMAKE_INSPECTION_STALE"
        )
    if (
        report.get("status") not in {"passed", "failed", "needs_review"}
        or not report.get("coverage")
        or not report.get("checkerVersion")
        or not report.get("rubricVersion")
        or not report.get("findings")
    ):
        _blocked("Inspection coverage and evidence are incomplete.")
    unresolved = []
    for finding in report["findings"]:
        status = finding.get("status")
        if status not in {"passed", "failed", "needs_review"} or not _evidence_valid(
            finding, assembly
        ):
            _blocked("Every finding requires valid current media evidence.")
        if status == "passed":
            continue
        if finding.get("category") in HARD_CATEGORIES or finding.get("hardBlocking") is True:
            _blocked("Technical and rights failures cannot be overridden by review.")
        unresolved.append(finding["id"])
        review = next((r for r in reversed(reviews) if r.get("findingId") == finding["id"]), {})
        if (
            review.get("decision") != "accept"
            or not str(review.get("reason", "")).strip()
            or not review.get("actorId")
            or not review.get("reviewedAt")
        ):
            _blocked("A reasoned human review is required for semantic uncertainty.")
    if report["status"] != "passed" and not unresolved:
        _blocked("The report conclusion has no reviewed finding to support release.")


def create_approval(
    p0: dict[str, Any],
    *,
    assembly_id: str,
    report_id: str,
    actor_id: str,
    constraints_hash: str,
    policy_hash: str,
    rights_valid: bool,
    current_manifest_hash: str,
) -> dict[str, Any]:
    assembly = _current(
        p0,
        assembly_id=assembly_id,
        constraints_hash=constraints_hash,
        current_manifest_hash=current_manifest_hash,
        rights_valid=rights_valid,
    )
    if not actor_id or not policy_hash:
        _blocked("An authenticated actor and current policy are required.")
    report, reviews = _report(p0, report_id), _reviews(p0, report_id)
    _inspectable(report, assembly, reviews)
    approval = {
        "id": str(uuid4()),
        "schemaVersion": 1,
        "status": "approved",
        "assemblyId": assembly_id,
        "mediaHash": assembly["mediaHash"],
        "manifestHash": current_manifest_hash,
        "constraintsHash": constraints_hash,
        "contextHash": assembly["contextHash"],
        "expectationsHash": assembly.get("expectationsHash"),
        "policyHash": policy_hash,
        "reportId": report_id,
        "inspectionHash": content_hash(report),
        "reviewsHash": content_hash(reviews),
        "checkerVersion": report["checkerVersion"],
        "rubricVersion": report["rubricVersion"],
        "actorId": str(actor_id),
        "approvedAt": now_iso(),
    }
    result = copy.deepcopy(p0)
    release = result.setdefault("release", {"approvals": [], "exports": []})
    release.setdefault("approvals", []).append(approval)
    release["activeApprovalId"] = approval["id"]
    return result


def validate_export_approval(
    p0: dict[str, Any],
    *,
    assembly_id: str,
    approval_id: str,
    constraints_hash: str,
    policy_hash: str,
    rights_valid: bool,
    current_manifest_hash: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    assembly = _current(
        p0,
        assembly_id=assembly_id,
        constraints_hash=constraints_hash,
        current_manifest_hash=current_manifest_hash,
        rights_valid=rights_valid,
    )
    release = p0.get("release", {})
    approval: dict[str, Any] = next(
        (a for a in release.get("approvals", []) if a["id"] == approval_id), {}
    )
    expected = {
        "assemblyId": assembly_id,
        "mediaHash": assembly["mediaHash"],
        "manifestHash": current_manifest_hash,
        "constraintsHash": constraints_hash,
        "contextHash": assembly["contextHash"],
        "expectationsHash": assembly.get("expectationsHash"),
        "policyHash": policy_hash,
    }
    if (
        not approval
        or release.get("activeApprovalId") != approval_id
        or any(approval.get(key) != value for key, value in expected.items())
    ):
        _blocked("The content approval is missing or stale.", "SMART_REMAKE_APPROVAL_STALE")
    report = _report(p0, approval["reportId"])
    reviews = _reviews(p0, report["id"])
    _inspectable(report, assembly, reviews)
    if approval["inspectionHash"] != content_hash(report) or approval[
        "reviewsHash"
    ] != content_hash(reviews):
        _blocked("The inspection policy or review changed.", "SMART_REMAKE_APPROVAL_STALE")
    return assembly, copy.deepcopy(approval)
