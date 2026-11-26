from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from tests.unit.test_smart_remake_evidence_cli import live_bundle
from viraldy.evaluation.smart_remake.capture import canonical_hash
from viraldy.evaluation.smart_remake.cli import main
from viraldy.evaluation.smart_remake.contracts import RuntimeCaptureContext
from viraldy.evaluation.smart_remake.replay import replay_bundle, validate_bundle
from viraldy.evaluation.smart_remake.runtime_adapter import capture_runtime_provenance


def public_export(value):
    run = value.captures[0]
    artifacts = {item.artifact_id: item for item in value.artifacts}
    report = copy.deepcopy(run.inspections[0])
    for item in report["observations"]:
        if item["mediaId"] == "output":
            item["mediaId"] = "subject"
    for item in [*report["findings"], *report["coverage"]]:
        for evidence in item["evidence"]:
            if evidence["mediaId"] == "output":
                evidence["mediaId"] = "subject"
    report.update(
        operationId="inspection-operation",
        actorId="reviewer",
        contextHash="c" * 64,
        subjectRequest={"kind": "assembly", "assemblyId": run.assembly_id},
    )
    approval = {**run.release, "id": "approval-1", "inspectionHash": canonical_hash(report)}
    attempt = run.attempts[0]
    return {
        "schemaVersion": "smart_remake_provenance_v1",
        "project": {"id": "project", "workspaceId": "workspace", "revision": 4, "status": "ready"},
        "run": {
            "caseId": None,
            "runId": None,
            "variant": None,
            "configVersion": None,
            "codeVersion": None,
            "promptVersion": None,
        },
        "inputs": [
            {
                "role": role,
                "assetId": role,
                "mediaHash": artifacts[role].sha256,
                "mimeType": artifacts[role].mime_type,
                "rights": {"declared": True, "revoked": False},
            }
            for role in ("source", "product")
        ],
        "requirements": {},
        "constraintsHash": run.constraints_hash,
        "policyHash": "d" * 64,
        "plan": {"sourceSceneMap": {}, "renderPlan": {}},
        "attempts": [
            {
                "id": attempt.attempt_id,
                "stage": "video",
                "purpose": "initial",
                "status": "completed",
                "provider": "recorded-provider",
                "model": "model-v1",
                "providerTaskId": "receipt-1",
                "requestHash": attempt.request_hash,
                "estimatedUsd": "2",
                "actualUsd": "1.25",
                "reservedUsd": "0",
                "costStatus": "actual",
                "createdAt": "2026-11-25T00:00:00+00:00",
                "submittedAt": "2026-11-25T00:00:01+00:00",
                "completedAt": "2026-11-25T00:00:03+00:00",
                "usage": {"seconds": 8.5},
                "receipt": {"taskId": "receipt-1"},
                "error": {},
            }
        ],
        "budget": {},
        "scenes": [],
        "timeline": {},
        "assemblies": {
            "activeAssemblyId": "assembly-1",
            "history": [],
            "records": [
                {
                    "id": "assembly-1",
                    "mediaHash": run.media_hash,
                    "manifestHash": run.manifest_hash,
                    "constraintsHash": run.constraints_hash,
                    "manifest": {
                        "selections": [
                            {"versionId": f"v{index}", "mediaHash": artifacts["raw"].sha256}
                            for index in range(2)
                        ]
                    },
                    "timeline": {
                        "totalFrames": 192,
                        "items": [
                            {
                                "renderUnitId": f"runtime-scene-{index}",
                                "versionId": f"v{index}",
                                "inFrame": start,
                                "outFrame": end,
                            }
                            for index, (start, end) in enumerate(((0, 48), (48, 192)))
                        ],
                    },
                }
            ],
        },
        "inspections": {"reports": [report], "reviews": run.reviews},
        "release": {"activeApprovalId": "approval-1", "approvals": [approval], "exports": []},
        "deletion": None,
        "stageTimings": [
            {
                "attemptId": attempt.attempt_id,
                "stage": "video",
                "createdAt": "2026-11-25T00:00:00+00:00",
                "submittedAt": "2026-11-25T00:00:01+00:00",
                "completedAt": "2026-11-25T00:00:03+00:00",
            }
        ],
        "failures": [],
    }


def context(mode="mock"):
    return RuntimeCaptureContext(
        case_id="dev-pass", run_id="runtime-run", variant_id="internal-grouped", mode=mode
    )


def test_public_runtime_mapping_preserves_null_versions_ranges_receipts_and_usage(tmp_path: Path):
    value = live_bundle(tmp_path).model_copy(update={"mode": "mock", "captures": []})
    populated = live_bundle(tmp_path)
    payload = public_export(populated)
    run = capture_runtime_provenance(payload, value, context())
    assert run.code_version is None
    assert run.config_version is None
    assert run.prompt_versions == {}
    assert run.selected_ranges[1].final_in_frame == 48
    assert run.attempts[0].usage["seconds"] == 8.5
    assert run.attempts[0].provider_receipt == "receipt-1"
    assert run.media_bindings == {"source": "source", "product": "product", "subject": "output"}
    assert run.stage_timings_ms["video"] == 2000
    validate_bundle(value.model_copy(update={"captures": [run]}), tmp_path)


def test_public_live_capture_requires_authoritative_mode_and_context_match(tmp_path: Path):
    value = live_bundle(tmp_path)
    payload = public_export(value)
    with pytest.raises(ValueError, match="authoritative"):
        capture_runtime_provenance(payload, value, context("live"))
    payload["run"]["mode"] = "live"
    run = capture_runtime_provenance(payload, value, context("live"))
    validate_bundle(value.model_copy(update={"captures": [run]}), tmp_path)
    payload["run"]["caseId"] = "different-case"
    with pytest.raises(ValueError, match="conflicts"):
        capture_runtime_provenance(payload, value, context("live"))


def test_server_configuration_does_not_promote_unverified_execution_to_live(tmp_path: Path):
    value = live_bundle(tmp_path)
    payload = public_export(value)
    payload["mode"] = "live"  # Not part of A's agreed public contract; ignore it.
    payload["run"].update(serverMode="live", providerExecution="unverified_live", mode=None)
    with pytest.raises(ValueError, match="authoritative"):
        capture_runtime_provenance(payload, value, context("live"))


def test_ready_without_current_approval_keeps_unknown_outcome(tmp_path: Path):
    populated = live_bundle(tmp_path)
    value = populated.model_copy(update={"mode": "mock", "captures": []})
    payload = public_export(populated)
    payload["release"]["activeApprovalId"] = None
    payload["inspections"]["reports"] = []
    run = capture_runtime_provenance(payload, value, context())
    assert run.outcome == "unknown"


def test_unapproved_current_report_retains_failed_labels_and_latest_recheck(tmp_path: Path):
    populated = live_bundle(tmp_path)
    value = populated.model_copy(update={"mode": "mock", "captures": []})
    payload = public_export(populated)
    payload["release"]["activeApprovalId"] = None
    failed = copy.deepcopy(payload["inspections"]["reports"][0])
    failed.update(id="failed-current", status="failed")
    failed["findings"][0].update(category="product", status="failed")
    payload["inspections"]["reports"] = [failed]
    run = capture_runtime_provenance(payload, value, context())
    assert run.outcome == "needs_repair"
    assert run.checker_labels["product"] == "failed"

    # An unrelated or historical report cannot replace the current assembly check.
    unrelated = copy.deepcopy(failed)
    unrelated["subject"]["assemblyId"] = "historical-assembly"
    payload["inspections"]["reports"].append(unrelated)
    passed = copy.deepcopy(public_export(populated)["inspections"]["reports"][0])
    passed["id"] = "current-recheck"
    payload["inspections"]["reports"].append(passed)
    run = capture_runtime_provenance(payload, value, context())
    assert run.outcome == "unknown"
    assert run.checker_labels["product"] != "failed"
    stale = copy.deepcopy(failed)
    stale.update(manifestHash="f" * 64, constraintsHash="e" * 64)
    payload["inspections"]["reports"].append(stale)
    wrong_project = copy.deepcopy(failed)
    wrong_project["subject"]["projectId"] = "another-project"
    payload["inspections"]["reports"].append(wrong_project)
    run = capture_runtime_provenance(payload, value, context())
    assert run.outcome == "unknown"
    assert run.checker_labels["product"] != "failed"


def test_runtime_capture_keeps_failed_unknown_receipt_and_estimate_separate(tmp_path: Path):
    populated = live_bundle(tmp_path)
    value = populated.model_copy(update={"mode": "mock", "captures": []})
    payload = public_export(populated)
    failed = {
        **payload["attempts"][0],
        "id": "unresolved",
        "status": "unknown",
        "stage": "image",
        "actualUsd": None,
        "costStatus": "unknown",
        "providerTaskId": None,
        "receipt": {},
        "error": {"code": "SUBMISSION_UNRESOLVED"},
    }
    payload["attempts"].append(failed)
    payload["failures"].append(
        {
            "attemptId": "unresolved",
            "stage": "image",
            "status": "unknown",
            "code": "SUBMISSION_UNRESOLVED",
        }
    )
    run = capture_runtime_provenance(payload, value, context())
    report = replay_bundle(value.model_copy(update={"captures": [run]}), tmp_path)
    assert report["attempts"] == 2
    assert report["cost"]["unknown_attempts"] == 1
    assert report["cost"]["per_accepted_output_usd"] is None
    assert "SUBMISSION_UNRESOLVED" in run.failures
    assert run.public_provenance["attempts"][-1]["actualUsd"] is None


def test_cli_maps_actual_runtime_projection_using_explicit_manifest_context(tmp_path: Path):
    populated = live_bundle(tmp_path)
    value = populated.model_copy(update={"mode": "mock", "captures": []})
    bundle = tmp_path / "bundle.json"
    bundle.write_text(value.model_dump_json())
    export = tmp_path / "public.json"
    export.write_text(json.dumps(public_export(populated)))
    manifest_context = tmp_path / "context.json"
    manifest_context.write_text(context().model_dump_json())
    assert (
        main(
            [
                "capture",
                str(bundle),
                "--provenance",
                str(export),
                "--context",
                str(manifest_context),
                "--output",
                str(tmp_path / "captured.json"),
            ]
        )
        == 0
    )
