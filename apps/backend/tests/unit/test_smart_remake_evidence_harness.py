from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

from viraldy.evaluation.smart_remake.capture import capture_provenance, redact_private_values
from viraldy.evaluation.smart_remake.contracts import (
    Attempt,
    CaseManifest,
    EvidenceBundle,
    HumanRating,
    Protocol,
)
from viraldy.evaluation.smart_remake.corpus import build_dev_corpus
from viraldy.evaluation.smart_remake.replay import (
    blind_assignments,
    guard_live_pilot,
    replay_bundle,
    validate_bundle,
)
from viraldy.evaluation.smart_remake.reporting import render_json, write_reports


def protocol() -> Protocol:
    return Protocol(
        protocol_id="dev-v1", status="development", variants={"internal-grouped": "Grouped dev"}
    )


def case() -> CaseManifest:
    return CaseManifest(
        case_id="dev-pass",
        split="development",
        target_frames=192,
        input_artifact_ids=["source", "product"],
        requirement_ids=["product-color"],
        scene_frames=[48, 144],
        group_scene_ids=[["scene-1", "scene-2"]],
    )


def bundle(tmp_path: Path) -> EvidenceBundle:
    from viraldy.evaluation.smart_remake.capture import sha256_bytes
    from viraldy.evaluation.smart_remake.contracts import Artifact, Capture, Rights

    assets = []
    for name, role in (("source", "source"), ("product", "product"), ("output", "assembly")):
        data = name.encode()
        (tmp_path / name).write_bytes(data)
        assets.append(
            Artifact(
                artifact_id=name,
                role=role,
                path=name,
                sha256=sha256_bytes(data),
                mime_type="image/png" if role == "product" else "video/mp4",
                frame_count=None if role == "product" else 192,
                rights=Rights(basis="self_authored", evidence_note="Unit fixture authored here"),
            )
        )
    return EvidenceBundle(
        bundle_id="unit-fixture",
        mode="fixture",
        protocol=protocol(),
        cases=[case()],
        artifacts=assets,
        captures=[
            Capture(
                run_id="run-1",
                case_id="dev-pass",
                variant_id="internal-grouped",
                mode="fixture",
                provenance_schema="smart_remake_provenance_v1",
                outcome="accepted",
                code_version="test",
                config_version="test",
                prompt_versions={"inspect": "v1"},
                model_versions={"inspect": "fake"},
                output_artifact_id="output",
                media_hash=assets[-1].sha256,
                assembly_id="assembly-1",
                manifest_hash="a" * 64,
                constraints_hash="b" * 64,
                attempts=[
                    Attempt(
                        attempt_id="a1",
                        stage="video",
                        purpose="initial",
                        status="completed",
                        request_hash="c" * 64,
                        cost_status="actual",
                        cost_usd="1.25",
                    )
                ],
            )
        ],
    )


def test_official_protocol_stays_pending_and_cannot_run_benchmark() -> None:
    pending = Protocol(protocol_id="btc-pending", status="pending")
    assert pending.main_matrix == [20, 3]
    assert pending.ablation_matrix == [8, 3]
    with pytest.raises(ValueError, match="protocol"):
        guard_live_pilot(pending, [], cap_usd=Decimal("2"), authorized=True)


def test_manifest_forbids_undefined_variants_and_bad_joins(tmp_path: Path) -> None:
    value = bundle(tmp_path)
    invalid_capture = value.captures[0].model_copy(update={"variant_id": "B0"})
    with pytest.raises(ValueError, match="variant"):
        validate_bundle(value.model_copy(update={"captures": [invalid_capture]}), tmp_path)
    invalid_case = value.cases[0].model_copy(update={"input_artifact_ids": ["missing"]})
    with pytest.raises(ValueError, match="artifact"):
        validate_bundle(value.model_copy(update={"cases": [invalid_case]}), tmp_path)


def test_replay_checks_bytes_traversal_and_preserves_unknown_cost(tmp_path: Path) -> None:
    value = bundle(tmp_path)
    unknown = Attempt(
        attempt_id="failed",
        stage="image",
        purpose="repair",
        status="unknown",
        request_hash="d" * 64,
        cost_status="unknown",
    )
    run = value.captures[0].model_copy(update={"attempts": [*value.captures[0].attempts, unknown]})
    value = value.model_copy(update={"captures": [run]})
    report = replay_bundle(value, tmp_path)
    assert report["attempts"] == 2
    assert report["cost"]["known_usd"] == "1.25"
    assert report["cost"]["unknown_attempts"] == 1
    assert report["cost"]["per_accepted_output_usd"] is None
    (tmp_path / "output").write_bytes(b"altered")
    with pytest.raises(ValueError, match="hash"):
        validate_bundle(value, tmp_path)
    artifact = value.artifacts[-1].model_copy(update={"path": "../output"})
    with pytest.raises(ValueError, match="path"):
        validate_bundle(
            value.model_copy(update={"artifacts": [*value.artifacts[:-1], artifact]}), tmp_path
        )


def test_missing_ratings_and_zero_accepted_are_unmeasured(tmp_path: Path) -> None:
    value = bundle(tmp_path)
    run = value.captures[0].model_copy(update={"outcome": "failed"})
    report = replay_bundle(value.model_copy(update={"captures": [run]}), tmp_path)
    assert report["human_ratings"]["mean"] is None
    assert report["human_ratings"]["status"] == "unmeasured"
    assert report["cost"]["per_accepted_output_usd"] is None
    assert report["checker"]["false_positive_rate"]["value"] is None


def test_ratings_bind_hash_and_blind_assignment_and_calibration(tmp_path: Path) -> None:
    value = bundle(tmp_path)
    assignment = blind_assignments(value, seed="locked-seed")[0]
    rating = HumanRating(
        rating_id="rating-1",
        blind_id=assignment["blind_id"],
        run_id="run-1",
        output_hash=value.artifacts[-1].sha256,
        rubric_version="remake-human-v1",
        reviewer_id="reviewer-a",
        checked_at="2026-11-25T00:00:00Z",
        scores={"product": 2, "usefulness": 3},
        labels={"product": "failed"},
    )
    run = value.captures[0].model_copy(update={"checker_labels": {"product": "passed"}})
    value = value.model_copy(
        update={"captures": [run], "ratings": [rating], "blind_assignments": [assignment]}
    )
    report = replay_bundle(value, tmp_path)
    assert report["checker"]["false_negative_rate"]["value"] == 1.0
    assert report["human_ratings"]["mean"] == 2.5
    bad = rating.model_copy(update={"output_hash": "f" * 64})
    with pytest.raises(ValueError, match="rating"):
        validate_bundle(value.model_copy(update={"ratings": [bad]}), tmp_path)


def test_deterministic_reports_and_replay_never_invokes_provider(tmp_path: Path) -> None:
    value = bundle(tmp_path)
    first = replay_bundle(value, tmp_path)
    assert render_json(first) == render_json(replay_bundle(value, tmp_path))
    paths = write_reports(first, tmp_path / "reports")
    assert json.loads(paths[0].read_text())["mode"] == "fixture"
    assert "unmeasured" in paths[1].read_text()
    assert blind_assignments(value, seed="stable") == blind_assignments(value, seed="stable")


def test_costs_require_explicit_known_or_unknown_state() -> None:
    with pytest.raises(ValidationError):
        Attempt(
            attempt_id="bad",
            stage="video",
            purpose="initial",
            status="failed",
            request_hash="c" * 64,
            cost_status="unknown",
            cost_usd="0",
        )
    with pytest.raises(ValidationError):
        Attempt(
            attempt_id="bad",
            stage="video",
            purpose="initial",
            status="completed",
            request_hash="c" * 64,
            cost_status="actual",
        )


def test_estimated_spend_is_separate_from_known_actual_spend(tmp_path: Path) -> None:
    value = bundle(tmp_path)
    estimate = (
        value.captures[0]
        .attempts[0]
        .model_copy(
            update={
                "cost_status": "estimated",
                "cost_usd": Decimal("2.50"),
            }
        )
    )
    run = value.captures[0].model_copy(update={"attempts": [estimate]})
    report = replay_bundle(value.model_copy(update={"captures": [run]}), tmp_path)
    assert report["cost"]["known_usd"] == "0"
    assert report["cost"]["estimated_usd"] == "2.50"
    assert report["cost"]["per_accepted_output_usd"] is None


def test_capture_adapter_is_versioned_and_redacts_sensitive_values() -> None:
    raw = {"schemaVersion": "unknown", "runs": []}
    with pytest.raises(ValueError, match="provenance"):
        capture_provenance(raw)
    assert redact_private_values({"api_key": "secret", "url": "https://x.test/a?sig=private"}) == {
        "api_key": "[redacted]",
        "url": "https://x.test/a",
    }


def test_live_pilot_requires_authorization_cap_rights_and_ready_protocol() -> None:
    with pytest.raises(ValueError, match="authorization"):
        guard_live_pilot(protocol(), [], cap_usd=Decimal("1"), authorized=False)
    with pytest.raises(ValueError, match="cap"):
        guard_live_pilot(protocol(), [], cap_usd=None, authorized=True)
    with pytest.raises(ValueError, match="case"):
        guard_live_pilot(protocol(), [], cap_usd=Decimal("1"), authorized=True)


def test_dev_corpus_is_authored_and_marks_blocked_and_fixture(tmp_path: Path) -> None:
    value = build_dev_corpus(tmp_path)
    assert value.mode == "fixture"
    assert {item.expected_outcome for item in value.cases} == {"passed", "needs_repair", "blocked"}
    assert all(item.rights.basis == "self_authored" for item in value.artifacts)
    assert any(item.role == "character" for item in value.artifacts)
    validate_bundle(value, tmp_path)
    assert replay_bundle(value, tmp_path)["live_verified"] is False


def test_paired_ratings_compare_matching_category_and_repair_phase_only(tmp_path: Path) -> None:
    value = bundle(tmp_path)
    other_variant = "internal-per-scene"
    paired_protocol = protocol().model_copy(
        update={"variants": {**protocol().variants, other_variant: "Internal per-scene control"}}
    )
    other = value.captures[0].model_copy(
        update={
            "run_id": "run-2",
            "variant_id": other_variant,
            "attempts": [value.captures[0].attempts[0].model_copy(update={"attempt_id": "a2"})],
        }
    )
    repaired = value.captures[0].model_copy(
        update={"run_id": "repair", "phase": "after_repair", "parent_run_id": "run-1"}
    )
    value = value.model_copy(
        update={"protocol": paired_protocol, "captures": [*value.captures, other, repaired]}
    )
    assignments = blind_assignments(value, seed="review-order")
    ratings = [
        HumanRating(
            rating_id=f"rating-{assignment['run_id']}",
            blind_id=assignment["blind_id"],
            run_id=assignment["run_id"],
            output_hash=assignment["output_hash"],
            rubric_version=paired_protocol.rubric_version,
            reviewer_id="reviewer-a",
            checked_at="2026-11-25T00:00:00Z",
            scores={"product": 1, "usefulness": 5}
            if assignment["run_id"] == "run-1"
            else {"product": 4}
            if assignment["run_id"] == "run-2"
            else {"product": 5},
        )
        for assignment in assignments
    ]
    report = replay_bundle(
        value.model_copy(update={"ratings": ratings, "blind_assignments": assignments}), tmp_path
    )
    pairs = report["paired_differences"]
    first_product = next(
        item for item in pairs if item["phase"] == "first_pass" and item["category"] == "product"
    )
    assert first_product["n"] == 1
    assert first_product["mean"] == 3
    assert all(
        item["n"] == 0 and item["mean"] is None
        for item in pairs
        if item["phase"] == "after_repair" or item["category"] == "usefulness"
    )
