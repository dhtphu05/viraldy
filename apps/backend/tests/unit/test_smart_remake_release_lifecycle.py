from __future__ import annotations

import copy

import pytest

from tests.smart_remake_expectations import install_expectations
from viraldy.modules.smart_remake.assembly_snapshots import (
    active_assembly,
    assembly_manifest,
    content_hash,
    invalidate_release,
    record_assembly,
    restore_assembly,
)
from viraldy.modules.smart_remake.inspection.public import inspection_profile
from viraldy.modules.smart_remake.release_policy import create_approval, validate_export_approval
from viraldy.shared.errors.base import AppError


def test_current_release_accepts_verified_twelve_second_frame_count():
    from viraldy.modules.smart_remake.release_policy import _current

    timeline = {"fps": 24, "totalFrames": 288, "items": [
        {"targetStartFrame": 0, "targetDurationFrames": 144, "inFrame": 0, "outFrame": 144},
        {"targetStartFrame": 144, "targetDurationFrames": 144, "inFrame": 0, "outFrame": 144},
    ]}
    manifest = {"timeline": timeline}
    assembly = {
        "id": "twelve-second-preview", "timeline": timeline, "manifest": manifest,
        "manifestHash": content_hash(manifest), "constraintsHash": "constraints",
        "mediaHash": "verified-output",
        "technicalCheck": {"status": "passed", "frameCount": 288, "mediaHash": "verified-output"},
    }
    p0 = {"assemblies": {"activeAssemblyId": assembly["id"], "records": [assembly]}}
    assert _current(
        p0, assembly_id=assembly["id"], constraints_hash="constraints",
        current_manifest_hash=assembly["manifestHash"], rights_valid=True,
    ) == assembly


@pytest.fixture
def assembled():
    timeline = {
        "fps": 24,
        "totalFrames": 192,
        "items": [
            {
                "id": "item",
                "renderUnitId": "scene",
                "sourceSceneId": "source",
                "versionId": "v1",
                "targetDurationFrames": 192,
                "targetStartFrame": 0,
                "inFrame": 0,
                "outFrame": 192,
                "reviewed": True,
            },
        ],
    }
    state = {
        "scenes": [
            {
                "id": "scene",
                "versions": [
                    {"id": "v1", "storageKey": "owned/raw", "mediaHash": "rawhash"},
                ],
            }
        ]
    }
    context = {
        "p0": {
            "requirements": {"intent": "Preserve the observed product"},
            "assets": {
                "source": {},
                "product": {},
            },
        }
    }
    install_expectations(context, state={**state, "draftTimeline": timeline})
    p0 = record_assembly(
        {},
        project_id="project",
        timeline=timeline,
        state=state,
        storage_key="owned/final",
        media_hash="finalhash",
        technical_check={"status": "passed", "frameCount": 192, "mediaHash": "finalhash"},
        constraints_hash="constraints",
        context_hash="context",
        revision=3,
        actor_id="actor",
        operation_id="compose",
        context=context,
    )
    assembly = active_assembly(p0)
    evidence = {"mediaHash": "finalhash", "inFrame": 0, "outFrame": 192}
    report = {
        "id": "report",
        "schemaVersion": 1,
        "status": "passed",
        "subject": {
            "kind": "assembly",
            "projectId": "project",
            "assemblyId": assembly["id"],
            "mediaHash": "finalhash",
        },
        "constraintsHash": "constraints",
        "manifestHash": assembly["manifestHash"],
        **inspection_profile(),
        "expectationsHash": assembly["expectationsHash"],
        "checkedAt": "now",
        "coverage": [{"requirementId": "product", "status": "passed", "evidence": [evidence]}],
        "findings": [
            {
                "id": "finding",
                "requirementId": "product",
                "category": "product",
                "status": "passed",
                "severity": "info",
                "evidence": [evidence],
            }
        ],
    }
    p0["inspections"] = {"reports": [report], "reviews": []}
    return p0, timeline, state


def approve(p0):
    assembly = active_assembly(p0)
    return create_approval(
        p0,
        assembly_id=assembly["id"],
        report_id="report",
        actor_id="actor",
        constraints_hash="constraints",
        policy_hash="policy",
        rights_valid=True,
        current_manifest_hash=assembly["manifestHash"],
    )


def validate(p0, **overrides):
    args = dict(
        assembly_id=active_assembly(p0)["id"],
        approval_id=p0["release"]["activeApprovalId"],
        constraints_hash="constraints",
        policy_hash="policy",
        rights_valid=True,
        current_manifest_hash=active_assembly(p0)["manifestHash"],
    )
    return validate_export_approval(p0, **(args | overrides))


def test_immutable_assembly_preserves_media_and_restore_creates_new_decision(assembled):
    p0, timeline, state = assembled
    before = copy.deepcopy(p0)
    manifest = assembly_manifest(timeline, state)
    timeline["items"][0]["inFrame"] = 24
    assert active_assembly(p0)["timeline"]["items"][0]["inFrame"] == 0
    assert content_hash(manifest) == active_assembly(p0)["manifestHash"]
    restored = restore_assembly(
        p0,
        assembly_id=active_assembly(p0)["id"],
        actor_id="other",
        revision=8,
        operation_id="restore",
    )
    assert p0 == before
    assert len(restored["assemblies"]["records"]) == 2
    assert active_assembly(restored)["mediaHash"] == "finalhash"
    assert active_assembly(restored)["id"] != active_assembly(p0)["id"]
    assert active_assembly(restored)["parentAssemblyId"] == active_assembly(p0)["id"]
    assert active_assembly(restored)["restoredFromAssemblyId"] == active_assembly(p0)["id"]
    assert restored["assemblies"]["history"][-1]["actorId"] == "other"
    assert restored["release"]["activeApprovalId"] is None


def test_assembly_rejects_missing_version_and_operation_replay_preserves_id(assembled):
    p0, timeline, state = assembled
    replay = record_assembly(
        p0,
        project_id="project",
        timeline=timeline,
        state=state,
        storage_key="owned/final",
        media_hash="finalhash",
        technical_check={"status": "passed", "frameCount": 192, "mediaHash": "finalhash"},
        constraints_hash="constraints",
        context_hash="context",
        revision=3,
        actor_id="actor",
        operation_id="compose",
    )
    assert replay == p0
    state["scenes"][0]["versions"] = []
    with pytest.raises(AppError):
        assembly_manifest(timeline, state)
    with pytest.raises(AppError):
        restore_assembly(p0, assembly_id="missing", actor_id="actor", revision=4, operation_id="r")


def test_approval_is_bound_to_current_media_report_and_policy(assembled):
    p0, _, _ = assembled
    approved = approve(p0)
    assembly, approval = validate(approved)
    assert approval["assemblyId"] == assembly["id"]
    assert approval["policyHash"] == "policy"
    assert approval["rubricVersion"] == inspection_profile()["rubricVersion"]
    assert "release" not in p0 or not p0["release"].get("approvals")
    for overrides in (
        {"rights_valid": False},
        {"policy_hash": "new"},
        {"constraints_hash": "new"},
        {"current_manifest_hash": "new"},
        {"approval_id": "missing"},
    ):
        with pytest.raises(AppError):
            validate(approved, **overrides)
    invalidated = invalidate_release(approved, "trim_changed")
    with pytest.raises(AppError):
        validate(invalidated)


@pytest.mark.parametrize(
    "change",
    [
        "empty_coverage",
        "missing_evidence",
        "wrong_subject",
        "wrong_manifest",
        "wrong_constraints",
        "insufficient",
        "technical",
        "rights",
        "bad_evidence",
        "failed_unreviewed",
    ],
)
def test_unverified_or_hard_failed_reports_never_release(assembled, change):
    p0, _, _ = assembled
    report = p0["inspections"]["reports"][0]
    finding = report["findings"][0]
    if change == "empty_coverage":
        report["coverage"] = []
    elif change == "missing_evidence":
        finding["evidence"] = []
    elif change == "wrong_subject":
        report["subject"]["mediaHash"] = "different"
    elif change == "wrong_manifest":
        report["manifestHash"] = "different"
    elif change == "wrong_constraints":
        report["constraintsHash"] = "different"
    elif change == "insufficient":
        report["status"] = "insufficient_evidence"
    elif change == "bad_evidence":
        finding["evidence"][0]["outFrame"] = 193
    else:
        finding.update(
            status="failed", category=change if change in {"technical", "rights"} else "product"
        )
        report["status"] = "failed"
        if change != "failed_unreviewed":
            p0["inspections"]["reviews"] = [
                {
                    "reportId": "report",
                    "findingId": "finding",
                    "decision": "accept",
                    "reason": "I reviewed",
                    "actorId": "actor",
                    "reviewedAt": "now",
                }
            ]
    with pytest.raises(AppError):
        approve(p0)


def test_semantic_uncertainty_requires_bound_human_review(assembled):
    p0, _, _ = assembled
    report = p0["inspections"]["reports"][0]
    report["status"] = "needs_review"
    report["findings"][0]["status"] = "needs_review"
    with pytest.raises(AppError):
        approve(p0)
    p0["inspections"]["reviews"] = [
        {
            "reportId": "report",
            "findingId": "finding",
            "decision": "accept",
            "reason": "Product matches owned reference.",
            "actorId": "actor",
            "reviewedAt": "now",
        }
    ]
    approved = approve(p0)
    validate(approved)
    approved["inspections"]["reports"][0]["rubricVersion"] = "new-rubric"
    with pytest.raises(AppError):
        validate(approved)


def test_no_report_or_no_active_assembly_cannot_approve(assembled):
    p0, _, _ = assembled
    with pytest.raises(AppError):
        active_assembly({})
    p0["inspections"]["reports"] = []
    with pytest.raises(AppError):
        approve(p0)


@pytest.mark.parametrize(
    "change",
    [
        "technical_failure",
        "technical_wrong_hash",
        "technical_wrong_count",
        "hard_block",
        "suspended",
        "no_actor",
        "no_policy",
        "wrong_evidence_hash",
        "no_findings",
    ],
)
def test_release_rejects_failed_technical_or_missing_binding(assembled, change):
    p0, _, _ = assembled
    assembly = p0["assemblies"]["records"][0]
    report = p0["inspections"]["reports"][0]
    finding = report["findings"][0]
    if change == "technical_failure":
        assembly["technicalCheck"]["status"] = "failed"
    elif change == "technical_wrong_hash":
        assembly["technicalCheck"]["mediaHash"] = "wrong"
    elif change == "technical_wrong_count":
        assembly["technicalCheck"]["frameCount"] = 191
    elif change == "hard_block":
        finding.update(status="failed", hardBlocking=True)
    elif change == "suspended":
        p0["deletion"] = {"status": "suspended"}
    elif change == "wrong_evidence_hash":
        finding["evidence"][0]["mediaHash"] = "reference-only"
    elif change == "no_findings":
        report["findings"] = []
    args = dict(
        assembly_id=assembly["id"],
        report_id="report",
        actor_id="actor",
        constraints_hash="constraints",
        policy_hash="policy",
        rights_valid=True,
        current_manifest_hash=assembly["manifestHash"],
    )
    if change == "no_actor":
        args["actor_id"] = ""
    elif change == "no_policy":
        args["policy_hash"] = ""
    with pytest.raises(AppError):
        create_approval(p0, **args)


def test_nested_evidence_range_and_reference_evidence_are_valid(assembled):
    p0, _, _ = assembled
    p0["inspections"]["reports"][0]["findings"][0]["evidence"] = [
        {"mediaHash": "source-reference", "assetId": "reference"},
        {"mediaHash": "finalhash", "range": {"inFrame": 24, "outFrame": 72}},
    ]
    validate(approve(p0))


def test_assembly_operation_conflict_and_restore_replay(assembled):
    p0, timeline, state = assembled
    with pytest.raises(AppError):
        record_assembly(
            p0,
            project_id="project",
            timeline=timeline,
            state=state,
            storage_key="owned/final",
            media_hash="different",
            technical_check={"status": "passed"},
            constraints_hash="constraints",
            context_hash="context",
            revision=3,
            actor_id="actor",
            operation_id="compose",
        )
    original = active_assembly(p0)
    restored = restore_assembly(
        p0, assembly_id=original["id"], actor_id="actor", revision=4, operation_id="restore"
    )
    replay = restore_assembly(
        restored, assembly_id=original["id"], actor_id="actor", revision=4, operation_id="restore"
    )
    assert replay == restored
    with pytest.raises(AppError):
        restore_assembly(
            restored,
            assembly_id=active_assembly(restored)["id"],
            actor_id="actor",
            revision=4,
            operation_id="restore",
        )


def test_restore_has_frozen_scene_and_compile_context_after_recompile(assembled):
    p0, timeline, state = assembled
    state.update(sourceSceneMap={"id": "old-source"}, renderPlan={"id": "old-plan"})
    context = {
        "sceneMap": {"id": "old-map"},
        "productLock": {"color": "blue"},
        "sourceSceneMap": {"id": "old-source"},
        "renderPlan": {"id": "old-plan"},
        "referenceAnalysis": {"id": "analysis"},
        "compileResult": {"id": "compile"},
        "p0": p0,
        "sourceKey": "never-copied",
    }
    original = record_assembly(
        p0,
        project_id="project",
        timeline=timeline,
        state=state,
        storage_key="owned/second",
        media_hash="secondhash",
        technical_check={"status": "passed", "frameCount": 192, "mediaHash": "secondhash"},
        constraints_hash="constraints",
        context_hash="context",
        revision=5,
        actor_id="actor",
        operation_id="compose-2",
        context=context,
    )
    old_id = active_assembly(original)["id"]
    state["scenes"] = [{"id": "recompiled-new-scene", "versions": []}]
    context["renderPlan"] = {"id": "new-plan"}
    restored = restore_assembly(
        original, assembly_id=old_id, actor_id="actor", revision=8, operation_id="restore-old"
    )
    record = active_assembly(restored)
    assert record["stateSnapshot"]["scenes"][0]["id"] == "scene"
    assert record["stateSnapshot"]["renderPlan"] == {"id": "old-plan"}
    assert record["contextSnapshot"]["renderPlan"] == {"id": "old-plan"}
    assert "p0" not in record["contextSnapshot"]
    assert "sourceKey" not in record["contextSnapshot"]
    assert record["timeline"] == timeline
