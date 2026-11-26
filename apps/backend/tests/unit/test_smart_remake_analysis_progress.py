from __future__ import annotations

import copy
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from viraldy.modules.smart_remake.analysis_progress import (
    checkpoint_analysis,
    public_analysis_progress,
)


def operation(status="running"):
    return SimpleNamespace(
        id=uuid4(),
        status=status,
        idempotency_key="owned-analysis-key",
        created_at=datetime(2026, 11, 26, tzinfo=UTC),
        result_json={"receipt": {"existing": "keep"}},
    )


def analysis():
    return {
        "sourceShots": [
            {
                "startSecond": 0,
                "endSecond": 5,
                "action": "Open the lid",
                "cameraAngle": "close up",
                "cameraMovement": "static",
                "transitionOut": "continuous",
            },
            {
                "startSecond": 5,
                "endSecond": 10,
                "action": "Pour the drink",
                "cameraAngle": "front",
                "cameraMovement": "push in",
                "transitionOut": "cut",
            },
        ],
        "privateRaw": "must not appear",
    }


@pytest.mark.asyncio
async def test_checkpoints_are_real_stages_and_preserve_receipts_without_source_facts():
    op, session = operation(), SimpleNamespace(commit=AsyncMock(), refresh=AsyncMock())
    await checkpoint_analysis(
        session, op, "analyzing_source", request_key=op.idempotency_key, source_duration=10
    )
    public = public_analysis_progress(op)
    assert public["status"] == "running" and public["stage"] == "analyzing_source"
    assert public["sourceDurationSeconds"] == 10
    assert public["scenes"] == [] and "sceneCount" not in public and "product" not in public
    assert public["operationId"] == str(op.id) and public["requestKey"] == op.idempotency_key
    assert public["startedAt"] == "2026-11-26T00:00:00+00:00"
    assert op.result_json["receipt"] == {"existing": "keep"} and op.result_json["kind"] == "compile"
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_validated_observations_appear_without_model_or_storage_payload():
    op = operation()
    original = analysis()
    await checkpoint_analysis(
        SimpleNamespace(commit=AsyncMock(), refresh=AsyncMock()),
        op,
        "resolving_scenes",
        request_key=op.idempotency_key,
        source_duration=10,
        analysis=original,
    )
    public = public_analysis_progress(op)
    assert public["sceneCount"] == 2
    assert public["scenes"][0] == {
        "index": 0,
        "startSecond": 0.0,
        "endSecond": 5.0,
        "action": "Open the lid",
        "camera": "close up · static",
        "transition": "continuous",
    }
    assert "privateRaw" not in str(public)
    assert original == analysis()


@pytest.mark.asyncio
async def test_semantic_fragments_are_presented_as_original_logical_scene():
    op = operation()
    await checkpoint_analysis(
        SimpleNamespace(commit=AsyncMock(), refresh=AsyncMock()),
        op,
        "identifying_product",
        request_key=op.idempotency_key,
        source_duration=10,
        analysis=analysis(),
        source_scenes=[{"startFrame": 0, "endFrame": 240}],
    )
    public = public_analysis_progress(op)
    assert public["sceneCount"] == 1 and len(public["scenes"]) == 1
    assert public["scenes"][0]["action"] == "Open the lid → Pour the drink"
    assert public["scenes"][0]["endSecond"] == 10


@pytest.mark.asyncio
async def test_invalid_or_generic_analysis_never_becomes_recognized_source_content():
    for shots in [
        [],
        [{"startSecond": 0, "endSecond": 10, "action": "show product"}],
        [{"startSecond": 3, "endSecond": 10, "action": "Open lid"}],
    ]:
        op = operation()
        await checkpoint_analysis(
            SimpleNamespace(commit=AsyncMock(), refresh=AsyncMock()),
            op,
            "resolving_scenes",
            request_key=op.idempotency_key,
            source_duration=10,
            analysis={"sourceShots": shots},
        )
        assert public_analysis_progress(op)["scenes"] == []
        assert "sceneCount" not in public_analysis_progress(op)


@pytest.mark.asyncio
async def test_product_identification_only_after_observation_and_survives_terminal_failure():
    op, session = operation(), SimpleNamespace(commit=AsyncMock(), refresh=AsyncMock())
    await checkpoint_analysis(
        session,
        op,
        "building_storyboard",
        request_key=op.idempotency_key,
        product={
            "productName": "Pink tumbler",
            "visualIdentity": {"colors": ["pink", "white"], "shape": "cylinder", "private": "omit"},
            "mustPreserve": ["handle"],
            "providerPayload": {"secret": "omit"},
        },
    )
    await checkpoint_analysis(
        session,
        op,
        "failed",
        request_key=op.idempotency_key,
        error_code="SMART_REMAKE_SOURCE_INVALID",
    )
    op.status = "failed"
    public = public_analysis_progress(op)
    assert public["status"] == public["stage"] == "failed"
    assert public["product"] == {
        "name": "Pink tumbler",
        "details": ["pink", "white", "cylinder", "handle"],
    }
    assert public["errorCode"] == "SMART_REMAKE_SOURCE_INVALID"
    assert "omit" not in str(public)


@pytest.mark.asyncio
async def test_public_projection_is_allowlisted_bounded_and_detached():
    op = operation()
    await checkpoint_analysis(
        SimpleNamespace(commit=AsyncMock(), refresh=AsyncMock()),
        op,
        "analyzing_source",
        request_key=op.idempotency_key,
    )
    op.result_json["analysisProgress"].update(
        {
            "storageKey": "private/object",
            "raw": {"secret": True},
            "scenes": [
                {
                    "index": i,
                    "startSecond": i,
                    "endSecond": i + 1,
                    "action": "Visit https://private.test/a?token=signed " + "a" * 1000,
                    "openingFrame": {"storageKey": "private"},
                }
                for i in range(30)
            ],
            "sceneCount": 30,
            "product": {"name": "Bottle", "details": ["red"] * 30, "storageKey": "private"},
        }
    )
    public = public_analysis_progress(op)
    assert len(public["scenes"]) == 12 and public["sceneCount"] == 30
    assert len(public["product"]["details"]) <= 8
    assert len(public["scenes"][0]["action"]) <= 500
    assert (
        "private" not in str(public) and "signed" not in str(public) and "secret" not in str(public)
    )
    public["scenes"].clear()
    assert len(op.result_json["analysisProgress"]["scenes"]) == 30


@pytest.mark.parametrize(
    "result",
    [{}, {"kind": "render"}, {"kind": "compile", "analysisProgress": {"schemaVersion": 999}}],
)
def test_legacy_and_invalid_progress_is_not_invented(result):
    op = operation()
    op.result_json = copy.deepcopy(result)
    assert public_analysis_progress(op) is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "provider,status", [("kie", "running"), ("unifically", "completed"), ("unifically", "failed")]
)
async def test_project_get_exposes_owned_compile_progress_without_provider_or_writes(
    monkeypatch, provider, status
):
    from viraldy.modules.smart_remake import kie_workflow
    from viraldy.modules.smart_remake.repair_service import RepairService

    workspace, project_id, op = uuid4(), uuid4(), operation(status)
    await checkpoint_analysis(
        SimpleNamespace(commit=AsyncMock(), refresh=AsyncMock()),
        op,
        "analyzing_source",
        request_key=op.idempotency_key,
        source_duration=10,
    )
    row = SimpleNamespace(id=project_id, state_json={"provider": provider}, context_json={"p0": {}})
    repo = SimpleNamespace(
        project=AsyncMock(return_value=row),
        running=AsyncMock(return_value=op if status == "running" else None),
        latest_operation=AsyncMock(return_value=op),
    )
    service = RepairService(repo, object(), workspace)
    service.present = AsyncMock(return_value={"id": str(project_id), "provider": provider})
    paid = AsyncMock(side_effect=AssertionError("GET must not reconcile compile as video"))
    monkeypatch.setattr(kie_workflow, "reconcile_kie_project", paid)
    result = await service.get(project_id)
    assert result["analysisProgress"]["requestKey"] == op.idempotency_key
    assert result["analysisProgress"]["status"] == status
    assert repo.project.await_args.args == (workspace, project_id)
    paid.assert_not_awaited()
    assert "sourceAnalysisCheckpoint" not in result


@pytest.mark.asyncio
async def test_project_progress_does_not_bypass_workspace_or_stop_use():
    from viraldy.modules.smart_remake.repair_service import RepairService
    from viraldy.shared.errors.base import NotFoundError

    op = operation()
    await checkpoint_analysis(
        SimpleNamespace(commit=AsyncMock(), refresh=AsyncMock()),
        op,
        "analyzing_source",
        request_key=op.idempotency_key,
    )
    workspace, project_id = uuid4(), uuid4()
    repo = SimpleNamespace(
        project=AsyncMock(side_effect=NotFoundError("SMART_REMAKE_PROJECT_NOT_FOUND")),
        running=AsyncMock(),
    )
    service = RepairService(repo, object(), workspace)
    with pytest.raises(NotFoundError):
        await service.get(project_id)
    repo.running.assert_not_awaited()
    row = SimpleNamespace(
        state_json={"provider": "kie"}, context_json={"p0": {"status": "suspended"}}
    )
    repo.project = AsyncMock(return_value=row)
    repo.running = AsyncMock(return_value=op)
    service.present = AsyncMock(return_value={"id": str(project_id)})
    assert "analysisProgress" not in await service.get(project_id)


@pytest.mark.asyncio
async def test_unobserved_range_does_not_invent_a_scene_or_break_compilation():
    op = operation()
    await checkpoint_analysis(
        SimpleNamespace(commit=AsyncMock(), refresh=AsyncMock()),
        op,
        "identifying_product",
        request_key=op.idempotency_key,
        source_duration=10,
        analysis=analysis(),
        source_scenes=[{"startFrame": 288, "endFrame": 528}],
    )
    assert public_analysis_progress(op)["scenes"] == []
    assert "sceneCount" not in public_analysis_progress(op)


@pytest.mark.asyncio
async def test_progress_helper_can_be_omitted_for_unowned_legacy_compilation():
    session = SimpleNamespace(commit=AsyncMock(), refresh=AsyncMock())
    await checkpoint_analysis(session, None, "analyzing_source", request_key=None)
    session.commit.assert_not_awaited()


@pytest.mark.parametrize("patch", [{"stage": {}}, {"stage": "unknown"}])
@pytest.mark.asyncio
async def test_invalid_saved_stage_is_ignored(patch):
    op = operation()
    await checkpoint_analysis(
        SimpleNamespace(commit=AsyncMock(), refresh=AsyncMock()),
        op,
        "analyzing_source",
        request_key=op.idempotency_key,
    )
    op.result_json["analysisProgress"].update(patch)
    assert public_analysis_progress(op) is None


@pytest.mark.asyncio
async def test_malformed_saved_optional_preview_fields_are_not_exposed():
    op = operation()
    await checkpoint_analysis(
        SimpleNamespace(commit=AsyncMock(), refresh=AsyncMock()),
        op,
        "analyzing_source",
        request_key=op.idempotency_key,
    )
    for value in (
        None,
        "wrong",
        [{"index": -1, "startSecond": 0, "endSecond": 1, "action": "bad"}],
        [None],
        [{"index": 0, "startSecond": float("inf"), "endSecond": 1, "action": "bad"}],
    ):
        op.result_json["analysisProgress"].update(
            scenes=value,
            sceneCount=-1,
            sourceDurationSeconds=float("nan"),
            product={"name": {}, "details": []},
            errorCode="https://secret.test",
        )
        public = public_analysis_progress(op)
        assert public["scenes"] == []
        assert not {"product", "sourceDurationSeconds", "sceneCount", "errorCode"} & public.keys()


@pytest.mark.asyncio
async def test_new_cuts_wait_for_observed_actions_before_source_preview():
    op = operation()
    coarse = {
        "sourceShots": [
            {"startSecond": 0, "endSecond": 10, "action": "Open the lid then pour the drink"}
        ]
    }
    await checkpoint_analysis(
        SimpleNamespace(commit=AsyncMock(), refresh=AsyncMock()),
        op,
        "resolving_scenes",
        request_key=op.idempotency_key,
        source_duration=10,
        analysis=coarse,
        source_scenes=[{"startFrame": 0, "endFrame": 120}, {"startFrame": 120, "endFrame": 240}],
    )
    assert public_analysis_progress(op)["scenes"] == []
    assert "sceneCount" not in public_analysis_progress(op)
    await checkpoint_analysis(
        SimpleNamespace(commit=AsyncMock(), refresh=AsyncMock()),
        op,
        "identifying_product",
        request_key=op.idempotency_key,
        source_duration=10,
        analysis=analysis(),
        source_scenes=[{"startFrame": 0, "endFrame": 120}, {"startFrame": 120, "endFrame": 240}],
    )
    assert [scene["action"] for scene in public_analysis_progress(op)["scenes"]] == [
        "Open the lid",
        "Pour the drink",
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "raw",
    [
        {},
        {"productName": "Named only"},
        {
            "productName": "Bottle",
            "visualIdentity": {"colors": ["unknown"], "material": "not visible"},
        },
    ],
)
async def test_product_without_observed_identity_never_claims_recognition(raw):
    from viraldy.modules.smart_remake.engine.product_lock_generator import normalize_product_lock

    op = operation()
    lock = normalize_product_lock(
        raw,
        metadata=None,
        prompt=None,
        description=None,
        product_lock=None,
        visual_identity=None,
        product_reference=None,
    )
    await checkpoint_analysis(
        SimpleNamespace(commit=AsyncMock(), refresh=AsyncMock()),
        op,
        "building_storyboard",
        request_key=op.idempotency_key,
        product=lock,
    )
    assert "product" not in public_analysis_progress(op)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "field,value",
    [
        ("material", "stainless steel"),
        ("texture", "matte"),
        ("pattern", "striped"),
        ("visibleBranding", "Seller logo"),
    ],
)
async def test_known_visual_detail_is_shown_even_without_color_or_shape(field, value):
    op = operation()
    await checkpoint_analysis(
        SimpleNamespace(commit=AsyncMock(), refresh=AsyncMock()),
        op,
        "building_storyboard",
        request_key=op.idempotency_key,
        product={"productName": "Bottle", "visualIdentity": {field: value}},
    )
    assert public_analysis_progress(op)["product"] == {"name": "Bottle", "details": [value]}


@pytest.mark.asyncio
async def test_get_during_blank_compile_start_never_enters_video_reconciliation(monkeypatch):
    from viraldy.modules.smart_remake import kie_workflow
    from viraldy.modules.smart_remake.repair_service import RepairService

    op = operation()
    op.result_json = {}
    row = SimpleNamespace(state_json={"provider": "kie"}, context_json={})
    repo = SimpleNamespace(project=AsyncMock(return_value=row), running=AsyncMock(return_value=op))
    service = RepairService(repo, object(), uuid4())
    service.present = AsyncMock(return_value={})
    video = AsyncMock(side_effect=AssertionError("Blank receipt has no video work to reconcile"))
    monkeypatch.setattr(kie_workflow, "reconcile_kie_project", video)
    result = await service.get(uuid4())
    assert result["pendingOperation"]["kind"] is None and "analysisProgress" not in result
    video.assert_not_awaited()
