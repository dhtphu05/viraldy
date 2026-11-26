from __future__ import annotations

import copy
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from viraldy.modules.smart_remake.analysis_progress import (
    checkpoint_analysis,
    public_analysis_progress,
    publish_quick_summary,
)


def operation():
    return SimpleNamespace(
        id=uuid4(), status="running", idempotency_key="observed-source",
        result_json={"kind": "compile"},
    )


def mistimed_analysis():
    return {"sourceShots": [
        {"startSecond": 0, "endSecond": 0.01, "action": "Open the lid"},
        {"startSecond": 0.01, "endSecond": 0.02, "action": "Pour the drink"},
    ], "privateRaw": "private", "sourceKey": "private-source"}


@pytest.mark.asyncio
async def test_mistimed_source_keeps_untimed_facts_without_passing_scene_validation():
    op = operation()
    source = mistimed_analysis()
    before = copy.deepcopy(source)
    await checkpoint_analysis(
        SimpleNamespace(commit=AsyncMock(), refresh=AsyncMock()), op, "resolving_scenes",
        request_key=op.idempotency_key, source_duration=22.75, analysis=source,
    )
    public = public_analysis_progress(op)
    assert public["scenes"] == [] and "sceneCount" not in public
    assert [item["detail"] for item in public["preliminaryObservations"]] == [
        "Open the lid", "Pour the drink",
    ]
    assert all(set(item) == {"label", "detail"} for item in public["preliminaryObservations"])
    assert "private" not in str(public) and "startSecond" not in str(public)
    assert source == before


def test_existing_saved_checkpoint_can_be_projected_without_writing_or_calling_ai():
    op = operation()
    op.result_json.update(
        sourceAnalysisCheckpoint={"analysis": mistimed_analysis()},
        analysisProgress={"schemaVersion": 1, "stage": "resolving_scenes", "scenes": []},
    )
    before = copy.deepcopy(op.result_json)
    public = public_analysis_progress(op)
    assert public["preliminaryObservations"][0]["detail"] == "Open the lid"
    assert op.result_json == before


@pytest.mark.asyncio
async def test_real_facts_survive_empty_semantic_checkpoint_and_terminal_failure():
    op = operation()
    session = SimpleNamespace(commit=AsyncMock(), refresh=AsyncMock())
    await checkpoint_analysis(
        session, op, "resolving_scenes", request_key=op.idempotency_key,
        source_duration=22.75, analysis=mistimed_analysis(),
    )
    await checkpoint_analysis(
        session, op, "resolving_scenes", request_key=op.idempotency_key,
        analysis={"sourceShots": []},
    )
    await checkpoint_analysis(
        session, op, "failed", request_key=op.idempotency_key,
        error_code="SMART_REMAKE_MODEL_ATTEMPT_UNCERTAIN",
    )
    public = public_analysis_progress(op)
    assert public["status"] == "failed"
    assert len(public["preliminaryObservations"]) == 2


@pytest.mark.asyncio
async def test_valid_scenes_take_precedence_and_generic_actions_do_not_become_facts():
    op = operation()
    session = SimpleNamespace(commit=AsyncMock(), refresh=AsyncMock())
    await checkpoint_analysis(
        session, op, "resolving_scenes", request_key=op.idempotency_key,
        source_duration=8,
        analysis={"sourceShots": [{"startSecond": 0, "endSecond": 8, "action": "Open lid"}]},
    )
    assert public_analysis_progress(op)["scenes"]
    assert "preliminaryObservations" not in public_analysis_progress(op)
    op = operation()
    await checkpoint_analysis(
        session, op, "resolving_scenes", request_key=op.idempotency_key,
        source_duration=8, analysis={"sourceShots": [{"action": "show product"}]},
    )
    assert "preliminaryObservations" not in public_analysis_progress(op)


def test_partial_projection_is_bounded_deduplicated_and_scrubs_private_links():
    op = operation()
    op.result_json.update(
        sourceAnalysisCheckpoint={"analysis": {"sourceShots": [
            {"action": f"Action {index} https://private.example/signed?token=secret"}
            for index in range(20)
        ]}},
        analysisProgress={"schemaVersion": 1, "stage": "resolving_scenes", "scenes": []},
    )
    result = public_analysis_progress(op)
    assert len(result["preliminaryObservations"]) <= 8
    assert "private.example" not in str(result) and "secret" not in str(result)
    assert "[liên kết]" in str(result)


@pytest.mark.asyncio
@pytest.mark.parametrize("reason", ["timeout", "invalid_response", "unavailable"])
async def test_quick_summary_exposes_only_a_bounded_unavailable_reason(reason):
    op = operation()
    session = SimpleNamespace(commit=AsyncMock(), refresh=AsyncMock())
    await checkpoint_analysis(session, op, "analyzing_source", request_key=op.idempotency_key)
    await publish_quick_summary(session, op, {"status": "unavailable", "reason": reason})
    assert public_analysis_progress(op)["quickSummary"] == {
        "status": "unavailable", "reason": reason,
    }
    await publish_quick_summary(session, op, {
        "status": "unavailable", "reason": "secret-provider-body",
    })
    assert public_analysis_progress(op)["quickSummary"] == {"status": "unavailable"}
