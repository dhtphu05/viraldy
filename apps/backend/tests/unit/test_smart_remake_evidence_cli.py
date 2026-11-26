from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

from tests.unit.test_smart_remake_evidence_harness import bundle, case, protocol
from viraldy.evaluation.smart_remake.capture import capture_provenance
from viraldy.evaluation.smart_remake.cli import main
from viraldy.evaluation.smart_remake.contracts import Protocol, SelectedRange
from viraldy.evaluation.smart_remake.replay import guard_live_pilot, replay_bundle, validate_bundle


def save_bundle(root: Path) -> Path:
    value = bundle(root)
    path = root / "bundle.json"
    path.write_text(value.model_dump_json())
    return path


def test_cli_validates_replays_reports_and_blinds_without_network(
    tmp_path: Path, monkeypatch
) -> None:
    import socket

    path = save_bundle(tmp_path)

    def no_network(*args, **kwargs):
        raise AssertionError("offline replay attempted network access")

    monkeypatch.setattr(socket, "socket", no_network)
    assert main(["validate", str(path)]) == 0
    for command in ("replay", "report"):
        assert main([command, str(path), "--output-dir", str(tmp_path / command)]) == 0
    assert (
        main(["blind", str(path), "--seed", "locked", "--output", str(tmp_path / "blind.json")])
        == 0
    )
    assert json.loads((tmp_path / "blind.json").read_text())["assignments"]


def test_capture_cli_consumes_public_version_and_preserves_failed_attempt(tmp_path: Path) -> None:
    path = save_bundle(tmp_path)
    original = bundle(tmp_path)
    run = original.captures[0].model_copy(
        update={
            "run_id": "failed-run",
            "outcome": "failed",
            "failures": ["PROVIDER_TIMEOUT"],
            "attempts": [
                original.captures[0]
                .attempts[0]
                .model_copy(update={"attempt_id": "failed-attempt", "status": "failed"})
            ],
        }
    )
    export = {
        "schemaVersion": "smart_remake_capture_v1",
        "captures": [run.model_dump(mode="json")],
    }
    assert capture_provenance(export) == [run]
    provenance = tmp_path / "export.json"
    provenance.write_text(json.dumps(export))
    output = tmp_path / "captured.json"
    assert (
        main(["capture", str(path), "--provenance", str(provenance), "--output", str(output)]) == 0
    )
    captured = json.loads(output.read_text())
    assert len(captured["captures"]) == 2
    assert captured["captures"][-1]["failures"] == ["PROVIDER_TIMEOUT"]
    with pytest.raises(ValueError, match="beside"):
        main(
            [
                "capture",
                str(path),
                "--provenance",
                str(provenance),
                "--output",
                str(tmp_path / "other" / "bundle.json"),
            ]
        )
    with pytest.raises(ValueError, match="captures"):
        capture_provenance({"schemaVersion": "smart_remake_capture_v1"})


def test_pilot_preflight_refuses_offline_or_missing_cap(tmp_path: Path) -> None:
    path = save_bundle(tmp_path)
    with pytest.raises(ValueError, match="cap"):
        main(["pilot-check", str(path), "--authorized"])
    with pytest.raises(ValueError, match="fixture"):
        main(["pilot-check", str(path), "--cap-usd", "1.00", "--authorized"])
    guard_live_pilot(protocol(), [case()], cap_usd=Decimal("1.00"), authorized=True)
    with pytest.raises(ValueError, match="development"):
        guard_live_pilot(
            protocol(),
            [case().model_copy(update={"split": "benchmark"})],
            cap_usd=Decimal("1"),
            authorized=True,
        )


def test_cli_authored_corpus_and_fresh_directory_guard(tmp_path: Path) -> None:
    assert main(["dev-corpus", "--output-dir", str(tmp_path / "new")]) == 0
    with pytest.raises(FileExistsError):
        main(["dev-corpus", "--output-dir", str(tmp_path / "new")])


def test_pilot_input_package_has_rights_and_pending_cap_without_fabricated_outputs(tmp_path: Path):
    from viraldy.evaluation.smart_remake.contracts import EvidenceBundle

    root = tmp_path / "pilot-inputs"
    assert main(["prepare-pilot-inputs", "--output-dir", str(root)]) == 0
    value = EvidenceBundle.model_validate_json((root / "bundle.json").read_text())
    validate_bundle(value, root)
    assert not value.captures
    assert {item.role for item in value.artifacts} == {"source", "product", "character", "audio"}
    assert all(item.rights.provider_use_allowed for item in value.artifacts)
    assert value.pilot_preparation.cap_usd is None
    assert value.pilot_preparation.authorized is False
    assert value.pilot_preparation.provider_disclosure_acknowledged is False
    assert all(not item.real_person for item in value.cases)
    assert replay_bundle(value, root)["live_verified"] is False
    assert replay_bundle(value, root)["pilot_preparation"]["input_only"] is True
    with pytest.raises(ValueError, match="cap"):
        main(["pilot-check", str(root / "bundle.json"), "--authorized"])


def test_live_capture_requires_provider_rights_receipts_and_complete_output_context(
    tmp_path: Path,
) -> None:
    value = bundle(tmp_path)
    live_run = value.captures[0].model_copy(update={"mode": "live"})
    live = value.model_copy(update={"mode": "live", "captures": [live_run]})
    with pytest.raises(ValueError, match="provider-use rights"):
        validate_bundle(live, tmp_path)
    artifacts = [
        item.model_copy(
            update={"rights": item.rights.model_copy(update={"provider_use_allowed": True})}
        )
        for item in live.artifacts
    ]
    live = live.model_copy(update={"artifacts": artifacts})
    with pytest.raises(ValueError, match="owned"):
        validate_bundle(live, tmp_path)
    live_run = live_run.model_copy(update={"project_id": "project", "workspace_id": "workspace"})
    live = live.model_copy(update={"captures": [live_run]})
    with pytest.raises(ValueError, match="receipt"):
        validate_bundle(live, tmp_path)
    attempt = live_run.attempts[0].model_copy(
        update={"provider": "real", "provider_receipt": "r-1"}
    )
    live_run = live_run.model_copy(update={"attempts": [attempt]})
    with pytest.raises(ValueError, match="ranges"):
        validate_bundle(live.model_copy(update={"captures": [live_run]}), tmp_path)


def test_raw_scene_final_range_mapping_rejects_shift_and_overflow(tmp_path: Path) -> None:
    value = bundle(tmp_path)
    raw = value.artifacts[-1].model_copy(update={"artifact_id": "raw", "role": "raw"})
    ranges = [
        SelectedRange(
            scene_id="scene-1",
            version_id="v1",
            raw_artifact_id="raw",
            in_frame=0,
            out_frame=48,
            final_in_frame=0,
        ),
        SelectedRange(
            scene_id="scene-2",
            version_id="v2",
            raw_artifact_id="raw",
            in_frame=48,
            out_frame=192,
            final_in_frame=48,
        ),
    ]
    run = value.captures[0].model_copy(update={"selected_ranges": ranges})
    value = value.model_copy(update={"captures": [run], "artifacts": [*value.artifacts, raw]})
    validate_bundle(value, tmp_path)
    for invalid, message in (
        (ranges[1].model_copy(update={"final_in_frame": 49}), "clock"),
        (ranges[1].model_copy(update={"out_frame": 193}), "exceeds"),
    ):
        bad = run.model_copy(update={"selected_ranges": [ranges[0], invalid]})
        with pytest.raises(ValueError, match=message):
            validate_bundle(value.model_copy(update={"captures": [bad]}), tmp_path)


@pytest.mark.parametrize(
    "update",
    [
        {"scene_frames": [193, -1]},
        {"scene_frames": [48, 48]},
        {"group_scene_ids": [["scene-2", "scene-1"]]},
        {"target_frames": 384, "scene_frames": [192, 192]},
    ],
)
def test_invalid_timeline_contracts_are_rejected(update: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        type(case()).model_validate({**case().model_dump(), **update})


def test_official_protocol_requires_source_and_all_branch_definitions() -> None:
    for update in ({"status": "locked"}, {"main_matrix": [6, 4]}, {"variants": {"B0": "made-up"}}):
        with pytest.raises(ValidationError):
            Protocol.model_validate({**protocol().model_dump(), **update})


def test_shared_attempts_deduplicate_and_conflicts_fail(tmp_path: Path) -> None:
    value = bundle(tmp_path)
    second = value.captures[0].model_copy(
        update={"run_id": "run-2", "phase": "after_repair", "parent_run_id": "run-1"}
    )
    value = value.model_copy(update={"captures": [*value.captures, second]})
    assert replay_bundle(value, tmp_path)["attempts"] == 1
    changed = second.attempts[0].model_copy(update={"cost_usd": Decimal("2")})
    second = second.model_copy(update={"attempts": [changed]})
    with pytest.raises(ValueError, match="conflicting"):
        validate_bundle(
            value.model_copy(update={"captures": [value.captures[0], second]}), tmp_path
        )


def test_repair_does_not_hide_missing_first_pass_case_and_variant(tmp_path: Path) -> None:
    value = bundle(tmp_path)
    second_case = case().model_copy(update={"case_id": "not-yet-attempted"})
    repair = value.captures[0].model_copy(
        update={"run_id": "repair", "phase": "after_repair", "parent_run_id": "run-1"}
    )
    value = value.model_copy(
        update={"cases": [*value.cases, second_case], "captures": [*value.captures, repair]}
    )
    report = replay_bundle(value, tmp_path)
    assert report["missing_runs"] == 1
    assert report["missing_run_keys"] == ["not-yet-attempted/internal-grouped"]


def test_redaction_removes_inline_credentials_but_keeps_token_usage() -> None:
    from viraldy.evaluation.smart_remake.capture import redact_private_values

    safe = redact_private_values(
        {
            "failure": "Authorization: Bearer private api_key=secret",
            "usage": {"input_tokens": 12, "output_tokens": 3},
        }
    )
    assert "private" not in safe["failure"]
    assert "secret" not in safe["failure"]
    assert safe["usage"]["input_tokens"] == 12


def test_non_24fps_assembly_is_not_an_eight_second_result(tmp_path: Path) -> None:
    value = bundle(tmp_path)
    altered = value.artifacts[-1].model_copy(update={"fps": 30})
    with pytest.raises(ValueError, match="24 fps"):
        validate_bundle(
            value.model_copy(update={"artifacts": [*value.artifacts[:-1], altered]}), tmp_path
        )


def test_blocked_rights_control_cannot_be_relabelled_accepted(tmp_path: Path) -> None:
    value = bundle(tmp_path)
    blocked = case().model_copy(update={"expected_outcome": "blocked"})
    with pytest.raises(ValueError, match="blocked"):
        validate_bundle(value.model_copy(update={"cases": [blocked]}), tmp_path)
    disguised = value.captures[0].model_copy(update={"outcome": "blocked", "attempts": []})
    with pytest.raises(ValueError, match="blocked"):
        validate_bundle(
            value.model_copy(update={"cases": [blocked], "captures": [disguised]}), tmp_path
        )


def test_unrelated_cases_cannot_share_attempt_ids_to_reduce_spend(tmp_path: Path) -> None:
    value = bundle(tmp_path)
    independent_case = case().model_copy(update={"case_id": "independent"})
    independent = value.captures[0].model_copy(
        update={"run_id": "independent", "case_id": "independent"}
    )
    with pytest.raises(ValueError, match="ancestry"):
        validate_bundle(
            value.model_copy(
                update={
                    "cases": [*value.cases, independent_case],
                    "captures": [*value.captures, independent],
                }
            ),
            tmp_path,
        )


def test_unknown_attempt_status_cannot_bypass_live_receipt_check() -> None:
    from viraldy.evaluation.smart_remake.contracts import Attempt

    with pytest.raises(ValidationError):
        Attempt(
            attempt_id="bad",
            stage="video",
            purpose="initial",
            status="success",
            request_hash="a" * 64,
            provider="fake",
        )


def live_bundle(tmp_path: Path):
    from viraldy.evaluation.smart_remake.capture import canonical_hash
    from viraldy.modules.smart_remake.inspection.contracts import (
        InspectionConstraints,
        InspectionSubject,
    )
    from viraldy.modules.smart_remake.inspection.requirements import (
        TECHNICAL_REQUIREMENT,
        requirements_for,
    )

    value = bundle(tmp_path)
    assets = [
        item.model_copy(
            update={"rights": item.rights.model_copy(update={"provider_use_allowed": True})}
        )
        for item in value.artifacts
    ]
    raw = assets[-1].model_copy(update={"artifact_id": "raw", "role": "raw"})
    run = value.captures[0].model_copy(
        update={
            "mode": "live",
            "project_id": "project",
            "workspace_id": "workspace",
            "attempts": [
                value.captures[0]
                .attempts[0]
                .model_copy(
                    update={"provider": "recorded-provider", "provider_receipt": "receipt-1"}
                )
            ],
            "selected_ranges": [
                SelectedRange(
                    scene_id=f"scene-{index + 1}",
                    version_id=f"v{index}",
                    raw_artifact_id="raw",
                    in_frame=start,
                    out_frame=end,
                    final_in_frame=start,
                )
                for index, (start, end) in enumerate(((0, 48), (48, 192)))
            ],
        }
    )
    evidence = {
        "mediaId": "output",
        "mediaHash": run.media_hash,
        "inFrame": 0,
        "outFrame": 1,
        "timebase": "final",
        "sampleId": "sample-1",
    }
    report = {
        "id": "report-1",
        "schemaVersion": 1,
        "subject": {
            "kind": "assembly",
            "projectId": "project",
            "mediaHash": run.media_hash,
            "assemblyId": "assembly-1",
            "sceneId": None,
            "versionId": None,
            "imageRole": None,
            "neighborVersionIds": None,
            "range": {"inFrame": 0, "outFrame": 192, "fps": 24, "timebase": "final"},
        },
        "status": "passed",
        "checkedAt": "2026-11-25T00:00:00Z",
        "checkerVersion": "checker-1",
        "rubricVersion": "checker-rubric-1",
        "modelProfile": {"model": "recorded-provider"},
        "constraintsHash": run.constraints_hash,
        "manifestHash": run.manifest_hash,
        "coverage": [
            {
                "requirementId": "product-color",
                "status": "passed",
                "evidence": [evidence],
                "sampledFrames": [0],
                "unobservedFrames": 191,
                "limitations": ["sampled"],
            }
        ],
        "findings": [
            {
                "id": "finding-1",
                "requirementId": "product-color",
                "category": "product",
                "expected": "Blue",
                "observed": "Blue",
                "status": "passed",
                "severity": "info",
                "evidence": [evidence],
                "suggestedAction": "none",
                "blocking": False,
                "hardBlocking": False,
            }
        ],
        "observations": [
            {**evidence, "id": "sample-1", "imageHash": "e" * 64, "mimeType": "image/jpeg"}
        ],
        "notApplicableRequirements": [],
    }
    product_observation = {
        "id": "product-sample",
        "mediaId": "product",
        "mediaHash": assets[1].sha256,
        "inFrame": None,
        "outFrame": None,
        "timebase": None,
        "sampleId": None,
        "imageHash": "f" * 64,
        "mimeType": "image/png",
    }
    product_evidence = {
        key: product_observation[key]
        for key in ("mediaId", "mediaHash", "inFrame", "outFrame", "timebase")
    }
    product_evidence["sampleId"] = "product-sample"
    report["observations"].append(product_observation)
    rules = [
        TECHNICAL_REQUIREMENT,
        *requirements_for(
            InspectionSubject.model_validate(report["subject"]),
            InspectionConstraints(
                constraintsHash=run.constraints_hash,
                manifestHash=run.manifest_hash,
                requirements={},
            ),
        ),
    ]
    report["status"] = "needs_review"
    report["notApplicableRequirements"] = [
        {"requirementId": "character", "reason": "Not requested"}
    ]
    report["findings"] = [
        {
            "id": f"finding-{rule.id}",
            "requirementId": rule.id,
            "category": rule.category,
            "expected": rule.expected,
            "observed": "Recorded observation",
            "status": "passed" if rule.id in {"technical", "product"} else "needs_review",
            "severity": "info" if rule.id in {"technical", "product"} else "warning",
            "evidence": [evidence, product_evidence] if rule.id == "product" else [evidence],
            "suggestedAction": "Human review",
            "blocking": False,
            "hardBlocking": False,
        }
        for rule in rules
    ]
    report["coverage"] = [
        {
            "requirementId": finding["requirementId"],
            "status": finding["status"],
            "evidence": finding["evidence"],
            "sampledFrames": [0],
            "unobservedFrames": 191,
            "limitations": ["Sampled"],
        }
        for finding in report["findings"]
    ]
    approval = {
        "status": "approved",
        "assemblyId": run.assembly_id,
        "mediaHash": run.media_hash,
        "manifestHash": run.manifest_hash,
        "constraintsHash": run.constraints_hash,
        "actorId": "reviewer",
        "approvedAt": "2026-11-25T00:01:00Z",
        "reportId": "report-1",
        "inspectionHash": canonical_hash(report),
        "policyHash": "d" * 64,
        "checkerVersion": "checker-1",
        "rubricVersion": "checker-rubric-1",
    }
    reviews = [
        {
            "reportId": report["id"],
            "findingId": finding["id"],
            "decision": "accept",
            "actorId": "reviewer",
            "reviewedAt": "2026-11-25T00:01:00Z",
            "reason": "Reviewed video",
        }
        for finding in report["findings"]
        if finding["status"] == "needs_review"
    ]
    run = run.model_copy(update={"inspections": [report], "release": approval, "reviews": reviews})
    live_case = value.cases[0].model_copy(update={"requirement_ids": [rule.id for rule in rules]})
    return value.model_copy(
        update={
            "mode": "live",
            "artifacts": [*assets, raw],
            "captures": [run],
            "cases": [live_case],
        }
    )


def test_live_acceptance_validates_public_inspection_and_approval_binding(tmp_path: Path) -> None:
    value = live_bundle(tmp_path)
    validate_bundle(value, tmp_path)
    for field, changed in (
        ("release", {"approved": False}),
        ("release", {**value.captures[0].release, "mediaHash": "f" * 64}),
        ("inspections", [{"fake": True}]),
    ):
        run = value.captures[0].model_copy(update={field: changed})
        with pytest.raises(ValueError):
            validate_bundle(value.model_copy(update={"captures": [run]}), tmp_path)


def test_live_inspection_rejects_out_of_bounds_and_hard_failure(tmp_path: Path) -> None:
    import copy

    from viraldy.evaluation.smart_remake.capture import canonical_hash

    value = live_bundle(tmp_path)
    for update in (
        {
            "category": "technical",
            "status": "failed",
            "hardBlocking": True,
            "blocking": True,
            "severity": "error",
        },
        {
            "evidence": [
                {
                    "mediaId": "output",
                    "mediaHash": "f" * 64,
                    "inFrame": 0,
                    "outFrame": 1,
                    "timebase": "final",
                }
            ]
        },
    ):
        report = copy.deepcopy(value.captures[0].inspections[0])
        report["findings"][0].update(update)
        if report["findings"][0]["status"] == "failed":
            report["status"] = "failed"
            report["coverage"][0]["status"] = "failed"
        approval = {**value.captures[0].release, "inspectionHash": canonical_hash(report)}
        run = value.captures[0].model_copy(update={"inspections": [report], "release": approval})
        with pytest.raises(ValueError):
            validate_bundle(value.model_copy(update={"captures": [run]}), tmp_path)


def test_live_inspection_reuses_media_clock_sample_and_coverage_validation(tmp_path: Path) -> None:
    import copy

    from viraldy.evaluation.smart_remake.capture import canonical_hash

    value = live_bundle(tmp_path)
    for change in ("identity", "clock", "coverage", "requirements"):
        report = copy.deepcopy(value.captures[0].inspections[0])
        if change == "identity":
            report["findings"][0]["evidence"][0]["mediaId"] = "nonexistent-media"
        elif change == "clock":
            report["findings"][0]["evidence"][0]["timebase"] = "source"
        elif change == "coverage":
            report["coverage"][0]["sampledFrames"] = [0, 1, 2, 3, 4]
            report["coverage"][0]["unobservedFrames"] = 0
        else:
            report["findings"][0]["requirementId"] = "invented"
            report["coverage"][0]["requirementId"] = "invented"
        approval = {**value.captures[0].release, "inspectionHash": canonical_hash(report)}
        run = value.captures[0].model_copy(update={"inspections": [report], "release": approval})
        with pytest.raises(ValueError):
            validate_bundle(value.model_copy(update={"captures": [run]}), tmp_path)
