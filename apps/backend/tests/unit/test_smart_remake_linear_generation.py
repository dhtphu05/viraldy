from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from tests.smart_remake_expectations import install_expectations
from tests.unit.test_smart_remake_grouped_workflow import grouped as _grouped
from viraldy.shared.errors.base import AppError

grouped = _grouped


@pytest.mark.asyncio
@pytest.mark.parametrize("duration,video_calls,image_count", [(8, 1, 2), (16, 2, 4)])
async def test_linear_generation_never_calls_image_inspector_and_uses_native_video_windows(
    grouped,
    monkeypatch,
    duration,
    video_calls,
    image_count,
):
    from viraldy.modules.smart_remake import conditioning_inspection

    value = grouped
    if duration == 8:
        value.row.context_json["renderPlan"]["groups"] = value.groups[:1]
        value.row.context_json["renderPlan"]["units"] = value.row.context_json["renderPlan"][
            "units"
        ][:2]
        value.row.context_json["sceneMap"]["scenes"] = value.row.context_json["sceneMap"]["scenes"][
            :2
        ]
        value.row.state_json["scenes"] = value.row.state_json["scenes"][:2]
        install_expectations(value.row.context_json, state=value.row.state_json)
    inspector = AsyncMock(side_effect=AssertionError("Automatic image inspection was removed"))
    monkeypatch.setattr(conditioning_inspection, "check_conditioning_images", inspector)
    await value.runner.execute(value.row.id, value.op.id)
    assert len(value.client.submits) == video_calls
    assert len(value.images) == image_count
    assert value.op.result_json["referencePreparation"] == "direct"
    inspector.assert_not_awaited()


@pytest.mark.asyncio
async def test_unknown_video_receipt_keeps_its_original_task_and_never_replaces_generation(
    grouped,
    monkeypatch,
):
    from viraldy.modules.smart_remake import conditioning_inspection

    value = grouped
    inspector = AsyncMock(side_effect=AssertionError("Do not inspect image or replace old work"))
    monkeypatch.setattr(conditioning_inspection, "check_conditioning_images", inspector)
    value.client.fail_submit = True
    for _ in range(2):
        with pytest.raises(AppError) as unresolved:
            await value.runner.execute(value.row.id, value.op.id)
        assert unresolved.value.code == "SMART_REMAKE_SUBMISSION_UNRESOLVED"
    assert len(value.client.submits) == 1
    assert len(value.images) == 2
    assert value.op.result_json["needsReconciliation"] is True
    inspector.assert_not_awaited()


@pytest.mark.parametrize("duration,expected", [(8, (2, 1, 0, 3)), (16, (4, 2, 0, 6))])
def test_render_preflight_no_longer_reserves_automatic_image_inspections(duration, expected):
    from tests.unit.test_smart_remake_preflight import project, run

    row = project(
        groups=[
            {"id": "first", "renderUnitIds": ["s0", "s1"]},
            *([{"id": "second", "renderUnitIds": ["s2", "s3"]}] if duration == 16 else []),
        ]
    )
    row.state_json["targetDuration"] = duration
    value = run(row=row)
    assert (
        value.calls.image,
        value.calls.video,
        value.calls.inspection,
        value.calls.total,
    ) == expected


def test_structured_repair_preflight_reserves_two_bookends_and_normalizer_without_image_checks():
    from tests.unit.test_smart_remake_preflight import run

    value = run(
        "repair",
        sceneId="s0",
        baseVersionId="v0",
        repairIntent={"schemaVersion": 1, "issues": [], "instruction": ""},
    )
    assert (
        value.calls.analysis,
        value.calls.image,
        value.calls.video,
        value.calls.inspection,
        value.calls.total,
    ) == (1, 2, 1, 0, 4)
