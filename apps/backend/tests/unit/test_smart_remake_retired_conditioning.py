from __future__ import annotations

import copy
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4, uuid5

import pytest

from tests.unit.test_smart_remake_preflight import project, run
from viraldy.modules.smart_remake.generation_recovery import attempt_needs_reconciliation


def retired_attempt(row):
    parent, context = uuid4(), "a" * 64
    return SimpleNamespace(
        id=uuid4(),
        project_id=row.id,
        status="unknown",
        actual_usd=None,
        estimated_usd=Decimal("0.50"),
        stage="inspection",
        provider="google",
        purpose="recheck",
        provider_task_id=None,
        metadata_json={
            "stage": "conditioning",
            "parentOperationId": str(parent),
            "contextHash": context,
            "operationId": str(uuid5(parent, "conditioning:" + context)),
            "subject": {
                "kind": "image",
                "imageRole": "conditioning",
                "projectId": str(row.id),
                "mediaHash": "b" * 64,
            },
        },
    )


@pytest.mark.parametrize("phase", ["invoking", "unknown"])
def test_removed_automatic_conditioning_marker_does_not_block_generation(phase):
    row = project()
    row.context_json["p0"]["conditioningChecks"] = {"legacy": {"phase": phase}}
    result = run(row=row, budgetMode="unlimited")
    assert not any(block.action == "reconcile" for block in result.blockers)


def test_retired_conditioning_attempt_preserves_unknown_bill_without_control_fence():
    row = project()
    attempt = retired_attempt(row)
    original = copy.deepcopy(vars(attempt))
    assert not attempt_needs_reconciliation(attempt)
    result = run(row=row, rows=[attempt], budgetMode="unlimited")
    assert not any(block.action == "reconcile" for block in result.blockers)
    assert result.budget.reservedUsd == "0.50" and result.budget.exposureUsd == "0.50"
    assert vars(attempt) == original and attempt.actual_usd is None and attempt.status == "unknown"


@pytest.mark.parametrize(
    "change",
    [
        "video",
        "image",
        "analysis",
        "manual",
        "provider",
        "purpose",
        "parent",
        "derived_operation",
        "subject_project",
        "subject_role",
        "context_hash",
        "provider_task",
    ],
)
def test_only_the_bound_retired_automatic_image_inspection_is_exempt(change):
    row = project()
    attempt = retired_attempt(row)
    if change in {"video", "image", "analysis"}:
        attempt.stage = change
    elif change == "manual":
        attempt.metadata_json = {}
    elif change == "provider":
        attempt.provider = "other"
    elif change == "purpose":
        attempt.purpose = "repair"
    elif change == "parent":
        attempt.metadata_json["parentOperationId"] = "invalid"
    elif change == "derived_operation":
        attempt.metadata_json["operationId"] = str(uuid4())
    elif change == "subject_project":
        attempt.metadata_json["subject"]["projectId"] = str(uuid4())
    elif change == "subject_role":
        attempt.metadata_json["subject"]["imageRole"] = "product"
    elif change == "context_hash":
        attempt.metadata_json["contextHash"] = "invalid"
    elif change == "provider_task":
        attempt.provider_task_id = "asynchronous-task"
    assert attempt_needs_reconciliation(attempt)
    assert any(
        block.action == "reconcile"
        for block in run(row=row, rows=[attempt], budgetMode="unlimited").blockers
    )


def test_active_operation_still_serializes_work_even_when_its_inspection_was_retired():
    row = project()
    result = run(
        row=row,
        rows=[retired_attempt(row)],
        budgetMode="unlimited",
        operations=[SimpleNamespace(status="running", result_json={"kind": "render"})],
    )
    assert any(block.action == "reconcile" for block in result.blockers)


def test_retired_check_does_not_turn_a_settled_compile_response_back_into_unknown_control():
    from tests.unit.test_smart_remake_analysis_recovery import failed_compile, returned_attempt
    from viraldy.modules.smart_remake.generation_recovery import analysis_retry_disposition

    attempt = returned_attempt()
    row, operation = failed_compile(attempt)
    row.context_json["p0"]["conditioningChecks"] = {"old": {"phase": "unknown"}}
    assert (
        analysis_retry_disposition(
            row,
            operation,
            [attempt],
            workspace_id=row.workspace_id,
        )
        == "new_analysis"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("phase", ["invoking", "unknown"])
async def test_retired_conditioning_marker_does_not_block_fresh_owned_compile(monkeypatch, phase):
    from unittest.mock import AsyncMock

    from tests.unit.test_smart_remake_lifecycle_compile import compile_arguments, owned_compile
    from viraldy.modules.smart_remake import timeline_compile
    from viraldy.shared.errors.base import AppError

    row, _, _ = owned_compile(monkeypatch)
    row.context_json["p0"]["conditioningChecks"] = {"prior-check": {"phase": phase}}
    monkeypatch.setattr(
        timeline_compile,
        "probe_media_bytes",
        lambda _: {
            "hasVideo": True,
            "durationSeconds": 8,
        },
    )
    monkeypatch.setattr(timeline_compile, "measure_video_frames", lambda _: 192)
    monkeypatch.setattr(timeline_compile, "extract_source_excerpt", lambda source, **_: source)
    model = AsyncMock(side_effect=AppError("OFFLINE_ANALYSIS_REACHED", "Stop before provider"))
    monkeypatch.setattr(timeline_compile, "analyze_reference_video", model)
    with pytest.raises(AppError) as stopped:
        await timeline_compile.compile_timeline_request(**compile_arguments())
    assert stopped.value.code == "OFFLINE_ANALYSIS_REACHED"
    model.assert_awaited_once()
