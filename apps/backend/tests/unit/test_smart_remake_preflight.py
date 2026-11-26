from __future__ import annotations

import copy
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from viraldy.modules.smart_remake.preflight_contracts import PreflightRequest
from viraldy.modules.smart_remake.preflight_service import calculate_preflight

NOW = datetime(2026, 11, 25, 12, tzinfo=UTC)
BOUNDS = {"analysis": "0.20", "image": "0.50", "video": "1.00", "inspection": "0.10"}


def project(*, character=False, images=True, groups=None):
    scenes = [
        {"id": f"s{i}", "activeVersionId": f"v{i}", "versions": [{"id": f"v{i}"}]} for i in range(3)
    ]
    return SimpleNamespace(
        id=uuid4(),
        revision=4,
        state_json={
            "revision": 4,
            "targetDuration": 16,
            "scenes": scenes,
            "renderPlan": {
                "imageModel": "gpt-image-2.6-sunburst" if images else None,
                "units": [{"id": s["id"]} for s in scenes],
                "groups": groups
                if groups is not None
                else [
                    {"id": "g1", "renderUnitIds": ["s0", "s1"]},
                    {"id": "g2", "renderUnitIds": ["s2"]},
                ],
            },
            "draftTimeline": {
                "items": [
                    {"renderUnitId": s["id"], "versionId": s["activeVersionId"]} for s in scenes
                ]
            },
        },
        context_json={
            "characterKey": "retained-character" if character else None,
            "p0": {
                "requirements": {"requiresCharacter": character},
                "budgetPolicy": {
                    "capUsd": "1",
                    "maxAttempts": 2,
                    "maxDurationSeconds": 1800,
                    "startedAt": NOW.isoformat(),
                },
                "assemblies": {
                    "records": [
                        {
                            "id": "a1",
                            "timeline": {
                                "items": [
                                    {"renderUnitId": s["id"], "versionId": s["activeVersionId"]}
                                    for s in scenes
                                ]
                            },
                        }
                    ]
                },
            },
        },
    )


def attempt(status="completed", actual=None, estimate="0.50"):
    return SimpleNamespace(
        id=uuid4(), status=status, actual_usd=actual, estimated_usd=Decimal(estimate), stage="image"
    )


def run(action="render", *, row=None, rows=(), operations=(), bounds=None, mode="live", **kwargs):
    if row is None and action != "analyze":
        row = project()
    request = PreflightRequest.model_validate(
        {
            "action": action,
            **(
                {"projectId": str(row.id), "expectedRevision": row.revision}
                if row
                else {"targetDuration": 16}
            ),
            **kwargs,
        }
    )
    return calculate_preflight(
        request,
        mode=mode,
        row=row,
        attempts=list(rows),
        operations=list(operations),
        bounds=BOUNDS if bounds is None else bounds,
        now=NOW,
    )


def test_analysis_includes_one_quick_summary_without_input_upload_or_project():
    result = run("analyze")
    assert result.calls.model_dump() == {
        "analysis": 4,
        "image": 0,
        "video": 0,
        "inspection": 0,
        "total": 4,
    }
    assert result.budget.additionalReservationUsd == "0.80"
    assert Decimal(result.budget.recommended.capUsd) == Decimal("0.80")
    assert result.budget.recommended.maxAttempts == 4
    assert result.scope.targetDuration == 16
    assert not result.blockers


def test_full_source_preflight_separates_analysis_span_from_output_duration():
    result = run(
        "analyze", targetDuration=8, analysisScope="full_source", sourceDurationSeconds=30.5
    )
    assert result.scope.targetDuration == 8
    assert (result.scope.sourceStartFrame, result.scope.sourceEndFrame) == (0, 732)
    assert result.scope.analysisScope == "full_source"
    assert result.calls.analysis == 4 and result.calls.video == 0


def test_owned_full_source_preflight_uses_measured_frames_instead_of_browser_duration():
    row = project()
    row.context_json["sourceFrameCount"] = 720
    result = run("reanalyze", row=row, analysisScope="full_source", sourceDurationSeconds=999)
    assert (result.scope.sourceStartFrame, result.scope.sourceEndFrame) == (0, 720)


def test_proven_image_rejection_allows_explicit_new_action_but_retains_unknown_bill():
    from tests.unit.test_smart_remake_generation_recovery import rejected_attempt

    rejected = rejected_attempt()
    result = run(rows=[rejected])
    assert not result.blockers
    assert result.budget.knownActualUsd == "0"
    assert result.budget.reservedUsd == "2"
    assert result.budget.exposureUsd == "2"
    assert rejected.actual_usd is None and rejected.status == "failed"


def test_structured_repair_without_clip_reports_missing_base_not_stale_script():
    row = project()
    row.state_json["scenes"][0].update(activeVersionId=None, versions=[])
    result = run(
        "repair", row=row, sceneId="s0",
        repairIntent={"schemaVersion": 1, "issues": [], "instruction": ""},
    )
    assert [b.code for b in result.blockers] == ["SMART_REMAKE_BASE_VERSION_REQUIRED"]


def test_full_source_scope_requires_zero_offset_and_analysis_action():
    with pytest.raises(ValidationError):
        run(
            "analyze", analysisScope="full_source", sourceDurationSeconds=30, referenceStartFrame=24
        )
    with pytest.raises(ValidationError):
        run("render", analysisScope="full_source", sourceDurationSeconds=30)


def test_render_budget_counts_provider_groups_independently_of_logical_scene_count():
    row = project(groups=[{"id": "one", "renderUnitIds": ["s0", "s1", "s2"]}])
    row.context_json["sourceSceneMap"] = {
        "timingMode": "fit_target",
        "sourceStartFrame": 0,
        "sourceFrameCount": 720,
        "scenes": [{"id": "logical", "startFrame": 0, "endFrame": 720}],
    }
    result = run(row=row)
    assert result.scope.sceneCount == 1
    assert result.scope.groupCount == 1
    assert result.calls.video == 1


def test_unlimited_preflight_needs_no_price_bounds_or_execution_grant():
    result = run("analyze", budgetMode="unlimited", bounds={})
    assert not result.blockers
    assert result.budget.recommended.model_dump() == {"mode": "unlimited"}
    assert result.budget.minimumCapUsd is None
    assert result.budget.minimumMaxAttempts is None
    assert result.budget.minimumDurationSeconds is None
    assert result.budget.additionalReservationUsd is None


def test_unlimited_action_is_not_blocked_by_old_project_limits_or_elapsed_history():
    row = project()
    row.context_json["p0"]["budgetPolicy"]["startedAt"] = (NOW - timedelta(days=30)).isoformat()
    before = copy.deepcopy(row.context_json)
    result = run(row=row, budgetMode="unlimited", bounds={}, rows=[attempt()] * 1001)
    assert not result.blockers
    assert result.budget.recommended.model_dump() == {"mode": "unlimited"}
    assert row.context_json == before


def test_unlimited_preflight_does_not_show_unknown_cost_as_zero():
    unknown = attempt(estimate="0")
    unknown.metadata_json = {"costEstimate": {"status": "unknown"}}
    result = run("analyze", budgetMode="unlimited", bounds={}, rows=[unknown])
    assert not result.blockers
    assert result.budget.knownActualUsd == "0"
    assert result.budget.reservedUsd is None and result.budget.exposureUsd is None
    assert result.budget.unknownCostAttempts == 1


def test_pending_attempt_still_requires_reconciliation_without_project_limits():
    result = run("analyze", budgetMode="unlimited", bounds={}, rows=[attempt("unknown")])
    assert "SMART_REMAKE_ATTEMPT_RECONCILIATION_REQUIRED" in {b.code for b in result.blockers}


@pytest.mark.parametrize(
    "character,images,expected",
    [
        (False, True, (3, 2, 0, "3.50")),
        (True, True, (2, 2, 0, "3.00")),
        (False, False, (0, 2, 0, "2.00")),
    ],
)
def test_render_uses_actual_group_conditioning_not_scene_count(character, images, expected):
    result = run(row=project(character=character, images=images))
    image, video, inspection, cost = expected
    assert (result.calls.image, result.calls.video, result.calls.inspection) == (
        image,
        video,
        inspection,
    )
    assert result.scope.sceneCount == 3 and result.scope.groupCount == 2
    assert result.budget.additionalReservationUsd == cost


def test_legacy_ungrouped_plan_has_one_video_and_conditioning_per_scene():
    result = run(row=project(groups=[]))
    assert (result.calls.image, result.calls.video, result.calls.inspection) == (3, 3, 0)


@pytest.mark.parametrize(
    "policy,count,frames",
    [(None, 4, 96), ("fixed_provider_windows", 4, 96), ("fixed_provider_windows", 2, 96)],
)
def test_old_or_invalid_timeline_provider_windows_require_update(policy, count, frames):
    row = project(
        groups=[
            {"id": f"g{i}", "renderUnitIds": ["s0"], "targetDurationFrames": frames}
            for i in range(count)
        ]
    )
    row.state_json["schemaVersion"] = 2
    row.state_json["renderPlan"]["groupingPolicy"] = policy
    result = run(row=row, budgetMode="unlimited")
    assert [block.code for block in result.blockers] == [
        "SMART_REMAKE_PROVIDER_PLAN_UPDATE_REQUIRED"
    ]
    assert result.calls.total == 0


@pytest.mark.parametrize("seconds", [8, 16])
def test_fixed_provider_window_preflight_counts_exact_output_calls(seconds):
    row = project(
        groups=[
            {
                "id": f"g{i}",
                "renderUnitIds": ["s0"],
                "rawDurationFrames": 192,
                "targetDurationFrames": 192,
            }
            for i in range(seconds // 8)
        ]
    )
    row.state_json.update(schemaVersion=2, targetDuration=seconds)
    row.state_json["renderPlan"]["groupingPolicy"] = "fixed_provider_windows"
    result = run(row=row, budgetMode="unlimited")
    assert not result.blockers
    assert result.calls.video == seconds // 8


def test_old_plan_pending_receipt_only_requires_reconciliation():
    row = project()
    row.state_json["schemaVersion"] = 2
    operation = SimpleNamespace(status="running", result_json={})
    result = run(row=row, operations=[operation], budgetMode="unlimited")
    assert [block.code for block in result.blockers] == [
        "SMART_REMAKE_ATTEMPT_RECONCILIATION_REQUIRED"
    ]


@pytest.mark.parametrize("images,expected", [(True, (1, 1, 0)), (False, (0, 1, 0))])
def test_repair_targets_exact_active_version_and_one_scene(images, expected):
    result = run("repair", row=project(images=images), sceneId="s1", baseVersionId="v1")
    assert (result.calls.image, result.calls.video, result.calls.inspection) == expected
    assert result.scope.sceneId == "s1" and result.scope.baseVersionId == "v1"
    assert result.scope.sceneCount == 1


def test_structured_repair_reserves_one_normalization_call_in_addition_to_generation():
    result = run(
        "repair",
        row=project(),
        sceneId="s1",
        baseVersionId="v1",
        repairIntent={"schemaVersion": 1, "issues": ["action"], "instruction": "Pour slowly"},
    )
    assert result.calls.model_dump() == {
        "analysis": 1,
        "image": 1,
        "video": 1,
        "inspection": 0,
        "total": 3,
    }
    assert result.budget.additionalReservationUsd == "1.70"
    assert "SMART_REMAKE_EXPECTATIONS_REQUIRED" in {b.code for b in result.blockers}


@pytest.mark.parametrize(
    "subject,count",
    [
        ({"kind": "image", "imageRole": "product"}, 1),
        ({"kind": "scene", "sceneId": "s0", "versionId": "v0"}, 2),
        ({"kind": "scene", "sceneId": "s1", "versionId": "v1"}, 3),
        ({"kind": "assembly", "assemblyId": "a1"}, 5),
    ],
)
def test_inspections_reserve_actual_subject_windows(subject, count):
    assert run("inspect", subject=subject).calls.inspection == count


def test_missing_or_duplicate_neighbor_version_is_not_an_extra_inspection():
    row = project()
    row.state_json["draftTimeline"]["items"][0]["versionId"] = "missing"
    assert (
        run(
            "inspect", row=row, subject={"kind": "scene", "sceneId": "s1", "versionId": "v1"}
        ).calls.inspection
        == 2
    )


def test_known_cost_and_completed_unknown_reservation_both_count_without_pending_block():
    rows = [attempt(actual=Decimal("0.12")), attempt()]
    result = run("reanalyze", rows=rows)
    assert result.budget.knownActualUsd == "0.12"
    assert result.budget.reservedUsd == "0.50"
    assert result.budget.exposureUsd == "0.62"
    assert result.budget.minimumCapUsd == "1.42"
    assert result.budget.recommended.maxAttempts == 6
    assert not result.blockers


@pytest.mark.parametrize("status", ["reserved", "submitted", "unknown"])
def test_unfinished_attempts_require_reconciliation(status):
    assert any(b.action == "reconcile" for b in run(rows=[attempt(status)]).blockers)


@pytest.mark.parametrize("status", ["reserved", "submitted", "unknown"])
def test_optional_loading_summary_does_not_block_but_keeps_cost_exposure(status):
    preview = attempt(status, estimate="0.20")
    preview.stage, preview.purpose = "analysis", "loading_summary"
    result = run(rows=[preview])
    assert not result.blockers
    assert result.budget.reservedUsd == "0.20"
    assert result.budget.exposureUsd == "0.20"
    assert result.budget.minimumMaxAttempts == result.calls.total + 1


def test_summary_purpose_does_not_bypass_video_receipt_reconciliation():
    video = attempt("unknown")
    video.stage, video.purpose = "video", "loading_summary"
    assert any(b.action == "reconcile" for b in run(rows=[video]).blockers)


def test_unpriced_optional_summary_remains_unknown_in_unlimited_preflight():
    preview = attempt("unknown", estimate="0")
    preview.stage, preview.purpose = "analysis", "loading_summary"
    preview.metadata_json = {"costEstimate": {"status": "unknown"}}
    result = run(rows=[preview], budgetMode="unlimited", bounds={})
    assert not result.blockers
    assert result.budget.knownActualUsd == "0"
    assert result.budget.reservedUsd is None and result.budget.exposureUsd is None
    assert result.budget.unknownCostAttempts == 1


def test_running_or_uncertain_operation_blocks_without_calling_budget_summary():
    for operation in [
        SimpleNamespace(status="running", result_json={}),
        SimpleNamespace(
            status="failed", result_json={"tasks": {"x": {"status": "submission_unknown"}}}
        ),
    ]:
        assert any(b.action == "reconcile" for b in run(operations=[operation]).blockers)


def test_completed_render_keeps_submitted_task_receipt_without_blocking_new_action():
    operation = SimpleNamespace(
        status="completed",
        result_json={
            "needsReconciliation": False,
            "tasks": {"group:g1": {"status": "submitted", "taskId": "retained-task-id"}},
        },
    )
    assert not run(operations=[operation], rows=[attempt()]).blockers


def test_failed_local_preflight_is_retryable_when_ledger_proves_no_cost():
    operation = SimpleNamespace(
        status="failed",
        result_json={
            "phase": "invoking",
            "needsReconciliation": False,
            "images": {"0": {"status": "submitting"}},
        },
    )
    assert not run(operations=[operation], rows=[attempt("failed", actual=Decimal(0))]).blockers


def test_failed_attempt_without_settlement_stays_fenced_despite_terminal_operation():
    operation = SimpleNamespace(
        status="failed", result_json={"phase": "invoking", "needsReconciliation": False}
    )
    assert any(
        b.action == "reconcile"
        for b in run(operations=[operation], rows=[attempt("failed")]).blockers
    )


def test_recommendation_never_lowers_existing_approval_and_clock_is_not_in_hash():
    row = project()
    row.context_json["p0"]["budgetPolicy"].update(
        capUsd="20",
        maxAttempts=50,
        maxDurationSeconds=7200,
        startedAt=(NOW - timedelta(hours=1)).isoformat(),
    )
    before = copy.deepcopy(row.context_json)
    result = run("reanalyze", row=row)
    assert result.budget.minimumDurationSeconds == 5400
    assert result.budget.recommended.model_dump() == {
        "capUsd": "20",
        "maxAttempts": 50,
        "maxDurationSeconds": 7200,
    }
    request = PreflightRequest(action="reanalyze", projectId=str(row.id), expectedRevision=4)
    later = calculate_preflight(
        request, mode="live", row=row, bounds=BOUNDS, now=NOW + timedelta(seconds=2)
    )
    assert result.contextHash == later.contextHash
    assert row.context_json == before


def test_elapsed_duration_cap_requires_new_project_instead_of_reset():
    row = project()
    row.context_json["p0"]["budgetPolicy"]["startedAt"] = (NOW - timedelta(days=1)).isoformat()
    result = run(row=row)
    assert any(b.action == "new_project" for b in result.blockers)
    assert result.budget is None


def test_missing_live_bound_returns_configure_blocker_and_no_budget():
    result = run(bounds={"video": "1"})
    assert result.budget is None
    assert any(
        b.code == "SMART_REMAKE_COST_BOUND_REQUIRED" and b.action == "configure"
        for b in result.blockers
    )


def test_fixture_is_explicitly_free_with_positive_nominal_intake_policy():
    result = run("analyze", mode="fixture", bounds={})
    assert result.mode == "fixture"
    assert result.budget.additionalReservationUsd == "0"
    assert result.budget.minimumCapUsd == "0.01"


def test_context_hash_changes_for_requirements_scope_ledger_and_server_ceiling():
    row = project()
    first = run(row=row).contextHash
    row.context_json["p0"]["requirements"]["keep"] = ["lid"]
    assert run(row=row).contextHash != first
    assert run(row=row).contextHash != run(row=row, rows=[attempt()]).contextHash
    assert run(row=row).contextHash != run(row=row, bounds={**BOUNDS, "video": "2"}).contextHash


def test_historical_eight_decimal_cap_rounds_up_to_accepted_policy_precision():
    row = project()
    row.context_json["p0"]["budgetPolicy"]["capUsd"] = "2.00000001"
    result = run("reanalyze", row=row)
    assert result.budget.recommended.capUsd == "2.000001"


def test_reanalysis_scope_uses_requested_excerpt_instead_of_previous_plan_duration():
    row = project()
    result = run("reanalyze", row=row, targetDuration=8, referenceStartFrame=48)
    assert result.scope.targetDuration == 8
    assert (result.scope.sourceStartFrame, result.scope.sourceEndFrame) == (48, 240)
    assert (
        result.contextHash
        != run("reanalyze", row=row, targetDuration=8, referenceStartFrame=72).contextHash
    )


def test_changed_owned_intake_duration_requests_fresh_intake_before_compilation():
    row = project()
    row.context_json["p0"]["targetDuration"] = 16
    result = run("reanalyze", row=row, targetDuration=8)
    assert result.scope.targetDuration == 8
    assert any(
        b.code == "SMART_REMAKE_INTAKE_DURATION_CHANGED" and b.action == "new_project"
        for b in result.blockers
    )


def test_render_scope_uses_persisted_source_excerpt_instead_of_browser_range():
    row = project()
    row.context_json["sourceSceneMap"] = {
        "sourceStartFrame": 48,
        "sourceFrameCount": 2000,
        "scenes": [{"startFrame": 48, "endFrame": 432}],
    }
    result = run(row=row, targetDuration=8, referenceStartFrame=0)
    assert result.scope.targetDuration == 16
    assert (result.scope.sourceStartFrame, result.scope.sourceEndFrame) == (48, 432)


def test_repair_describes_raw_generated_duration_instead_of_selected_trimmed_duration():
    row = project()
    row.state_json["renderPlan"]["units"][1].update(targetDurationFrames=72, rawDurationFrames=192)
    result = run("repair", row=row, sceneId="s1", baseVersionId="v1")
    assert result.scope.targetDuration == 8


def test_stale_revision_unknown_scene_or_subject_and_missing_plan_do_not_guess():
    row = project()
    assert any(b.action == "refresh" for b in run(row=row, expectedRevision=3).blockers)
    assert run("repair", row=row, sceneId="missing", baseVersionId="v1").blockers
    assert run("repair", row=row, sceneId="s1", baseVersionId="v0").blockers
    assert run("inspect", row=row, subject={"kind": "assembly", "assemblyId": "missing"}).blockers
    row.state_json.pop("renderPlan")
    assert run(row=row).blockers


@pytest.mark.parametrize(
    "payload",
    [
        {"action": "render"},
        {"action": "analyze"},
        {"action": "analyze", "targetDuration": 16, "calls": 1},
        {"action": "analyze", "targetDuration": 16, "capUsd": "0.01"},
        {"action": "inspect", "projectId": str(uuid4()), "expectedRevision": 1},
    ],
)
def test_request_requires_action_identity_and_rejects_client_prices(payload):
    with pytest.raises(ValidationError):
        PreflightRequest.model_validate(payload)
