"""Optional early observations stay separate from the authoritative scene analysis."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from viraldy.modules.smart_remake.analysis_progress import (
    checkpoint_analysis,
    public_analysis_progress,
    publish_quick_summary,
)


def state():
    operation = SimpleNamespace(
        id=uuid4(),
        status="running",
        idempotency_key="compile-current",
        created_at=datetime(2026, 11, 26, tzinfo=UTC),
        result_json={},
    )
    session = SimpleNamespace(commit=AsyncMock(), refresh=AsyncMock())
    return session, operation


@pytest.mark.asyncio
async def test_early_summary_survives_main_stage_writes_and_does_not_create_scene_facts():
    session, operation = state()
    await checkpoint_analysis(session, operation, "analyzing_source", request_key="compile-current")
    await publish_quick_summary(
        session,
        operation,
        {
            "status": "completed",
            "summary": "Một chiếc hộp cam đang được di chuyển trên bàn.",
            "observations": [
                {"label": "Hành động", "detail": "Sản phẩm di chuyển qua các vị trí."}
            ],
            "rawSecret": {"storageKey": "omit"},
        },
    )
    await checkpoint_analysis(session, operation, "resolving_scenes", request_key="compile-current")
    progress = public_analysis_progress(operation)
    assert progress["quickSummary"]["summary"].startswith("Một chiếc hộp")
    assert progress["scenes"] == [] and "sceneCount" not in progress and "product" not in progress
    assert "omit" not in str(progress)
    assert all(call.kwargs.get("with_for_update") for call in session.refresh.await_args_list)


@pytest.mark.asyncio
async def test_completed_compile_freezes_response_and_rejects_late_optional_summary():
    session, operation = state()
    await checkpoint_analysis(session, operation, "analyzing_source", request_key="compile-current")
    await publish_quick_summary(session, operation, {"status": "pending"})
    await checkpoint_analysis(
        session,
        operation,
        "completed",
        request_key="compile-current",
        result_updates={"compileResult": {"projectId": "retained"}},
    )
    assert operation.status == "completed"
    assert operation.result_json["compileResult"] == {"projectId": "retained"}
    assert public_analysis_progress(operation)["quickSummary"] == {"status": "unavailable"}
    assert not await publish_quick_summary(
        session, operation, {"status": "completed", "summary": "Late"}
    )
    assert public_analysis_progress(operation)["quickSummary"] == {"status": "unavailable"}


@pytest.mark.asyncio
async def test_source_checkpoint_merges_without_replacing_optional_summary():
    session, operation = state()
    await checkpoint_analysis(session, operation, "analyzing_source", request_key="compile-current")
    await publish_quick_summary(
        session,
        operation,
        {"status": "completed", "summary": "Sản phẩm trên bàn.", "observations": []},
    )
    await checkpoint_analysis(
        session,
        operation,
        "resolving_scenes",
        request_key="compile-current",
        result_updates={"sourceAnalysisCheckpoint": {"analysis": {"raw": "private"}}},
    )
    assert operation.result_json["sourceAnalysisCheckpoint"]["analysis"] == {"raw": "private"}
    public = public_analysis_progress(operation)
    assert public["quickSummary"]["summary"] == "Sản phẩm trên bàn."
    assert "private" not in str(public)


@pytest.mark.asyncio
async def test_finishing_does_not_wait_indefinitely_for_cancelled_request_receipt():
    import asyncio
    import time

    from viraldy.modules.smart_remake import loading_summary

    release = asyncio.Event()
    started = asyncio.Event()
    settled = asyncio.Event()

    async def optional():
        try:
            started.set()
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            await release.wait()
            settled.set()
            raise

    task = asyncio.create_task(optional())
    await started.wait()
    before = time.monotonic()
    await loading_summary.finish_loading_summary(task)
    assert time.monotonic() - before < 1.5
    assert task in loading_summary._RECEIPT_SETTLEMENTS and not task.done()
    release.set()
    await asyncio.gather(task, return_exceptions=True)
    await asyncio.sleep(0)
    assert settled.is_set() and task not in loading_summary._RECEIPT_SETTLEMENTS


@pytest.fixture
def summary_harness(monkeypatch):
    from contextlib import asynccontextmanager

    from viraldy.modules.smart_remake import loading_summary
    from viraldy.modules.smart_remake.engine.schemas import UploadedMedia
    from viraldy.modules.smart_remake.quick_preview_media import QuickPreviewMedia

    session, operation = state()
    operation.result_json = {
        "kind": "compile",
        "analysisProgress": {"schemaVersion": 1, "stage": "analyzing_source", "scenes": []},
    }
    session.scalar = AsyncMock(return_value=None)
    project = SimpleNamespace(context_json={"p0": {"budgetPolicy": {"mode": "unlimited"}}})
    harness = SimpleNamespace(
        session=session,
        operation=operation,
        project=project,
        constructors=[],
        http=[],
        result={
            "summary": "Video cho thấy một chiếc hộp cam di chuyển trên bàn.",
            "observations": [{"label": "Hành động", "detail": "Hộp đi qua các vị trí."}],
        },
        error=None,
        workspace=uuid4(),
        project_id=uuid4(),
        source=UploadedMedia(bytes=b"original-video", mime_type="video/mp4"),
        get_model="gemini-2.5-flash",
        started=None,
        release=None,
    )

    @asynccontextmanager
    async def factory():
        yield session

    class Client:
        def __init__(self, **kwargs):
            harness.http.append(kwargs)

    class Ledger:
        def __init__(self, *args, **kwargs):
            harness.constructors.append((args, kwargs))

        async def generate_json(self, **kwargs):
            harness.request = kwargs
            assert operation.result_json["analysisProgress"]["quickSummary"] == {
                "status": "pending"
            }
            if harness.started:
                harness.started.set()
                await harness.release.wait()
            if harness.error:
                raise harness.error
            return harness.result

    harness.factory = factory
    monkeypatch.setattr(
        loading_summary,
        "RepairRepository",
        lambda _: SimpleNamespace(
            project=AsyncMock(return_value=project), operation=AsyncMock(return_value=operation)
        ),
    )
    monkeypatch.setattr(loading_summary, "LedgerGeminiClient", Ledger)
    monkeypatch.setattr(loading_summary, "HttpGeminiClient", Client)
    monkeypatch.setattr(loading_summary, "get_gemini_model", lambda: harness.get_model)
    monkeypatch.setattr(
        loading_summary, "prepare_quick_preview",
        lambda source, duration: QuickPreviewMedia(
            (UploadedMedia(bytes=b"small-preview", mime_type="video/mp4"),),
            "video_proxy", True, duration, "a" * 64,
        ),
    )
    return harness


async def run_summary(harness, *, mode="live"):
    from viraldy.modules.smart_remake import loading_summary

    await loading_summary._run_summary(
        harness.factory,
        harness.workspace,
        harness.project_id,
        harness.operation.id,
        None,
        harness.source,
        30,
        mode,
    )


@pytest.mark.asyncio
async def test_short_source_observation_is_accounted_once_and_is_not_a_scene_plan(summary_harness):
    h = summary_harness
    await run_summary(h)
    assert len(h.constructors) == len(h.http) == 1
    args, options = h.constructors[0]
    assert args[0] is h.session
    assert options["purpose"] == options["attempt_namespace"] == "loading_summary"
    assert options["profile"] == {
        "maxOutputTokens": 1280, "timeoutSeconds": 30, "thinkingBudget": 0,
    }
    assert h.http == [
        {
            "max_attempts": 1,
            "repair_json": False,
            "max_output_tokens": 1280,
            "timeout_seconds": 30,
            "thinking_budget": 0,
        }
    ]
    assert h.request["media"] == [{"bytes": b"small-preview", "mime_type": "video/mp4"}]
    assert options["metadata"]["preview"]["sourceMediaHash"] == "a" * 64
    assert options["metadata"]["preview"]["byteLength"] == len(b"small-preview")
    assert "SMART_REMAKE_LOADING_SUMMARY_V1" in h.request["system_instruction"]
    assert "tiếng Việt" in h.request["system_instruction"]
    progress = public_analysis_progress(h.operation)
    assert progress["quickSummary"]["summary"] == h.result["summary"]
    assert "sceneCount" not in progress and "product" not in progress and progress["scenes"] == []


@pytest.mark.asyncio
async def test_other_configured_model_omits_unverified_thinking_override(summary_harness):
    h = summary_harness
    h.get_model = "gemini-3-flash"
    await run_summary(h)
    assert h.http[0]["thinking_budget"] is None
    assert "thinkingBudget" not in h.constructors[0][1]["profile"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "policy,mode",
    [
        ({"capUsd": "1", "maxAttempts": 3, "maxDurationSeconds": 300}, "live"),
        ({"mode": "unlimited"}, "fixture"),
        ({"mode": "unlimited"}, "mock"),
    ],
)
async def test_legacy_limited_budget_and_offline_mode_keep_all_mandatory_headroom(
    summary_harness, policy, mode
):
    h = summary_harness
    h.project.context_json["p0"]["budgetPolicy"] = policy
    await run_summary(h, mode=mode)
    assert not h.constructors and not h.http
    assert public_analysis_progress(h.operation)["quickSummary"] == {"status": "unavailable"}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "failure,reason", [
        (TimeoutError("optional timed out"), "timeout"),
        (ValueError("optional malformed JSON"), "invalid_response"),
    ]
)
async def test_optional_provider_failure_does_not_fail_or_repeat_the_deep_compile(
    summary_harness, failure, reason
):
    h = summary_harness
    h.error = failure
    await run_summary(h)
    assert len(h.constructors) == 1 and h.operation.status == "running"
    assert h.operation.result_json["analysisProgress"]["quickSummary"] == {
        "status": "unavailable", "reason": reason,
    }


@pytest.mark.asyncio
async def test_invalid_summary_schema_is_unavailable_without_a_repair_call(summary_harness):
    h = summary_harness
    h.result = {"sourceShots": [{"action": "not summary output"}]}
    await run_summary(h)
    assert len(h.constructors) == 1
    assert h.operation.result_json["analysisProgress"]["quickSummary"] == {
        "status": "unavailable", "reason": "invalid_response",
    }


@pytest.mark.asyncio
async def test_preview_failure_stops_before_reserving_or_creating_provider_client(
    summary_harness, monkeypatch,
):
    from viraldy.modules.smart_remake import loading_summary

    h = summary_harness

    def failed(*args):
        raise RuntimeError("private media path must stay private")

    monkeypatch.setattr(loading_summary, "prepare_quick_preview", failed)
    await run_summary(h)
    assert not h.constructors and not h.http and h.operation.status == "running"
    assert h.operation.result_json["analysisProgress"]["quickSummary"] == {
        "status": "unavailable", "reason": "unavailable",
    }


@pytest.mark.asyncio
async def test_main_completion_during_preparation_prevents_late_optional_call(
    summary_harness, monkeypatch,
):
    from viraldy.modules.smart_remake import loading_summary

    h = summary_harness
    prepare = loading_summary.prepare_quick_preview

    def completed(*args):
        h.operation.status = "completed"
        return prepare(*args)

    monkeypatch.setattr(loading_summary, "prepare_quick_preview", completed)
    await run_summary(h)
    assert not h.constructors and not h.http


@pytest.mark.asyncio
async def test_image_only_fallback_does_not_invent_audio_or_submit_another_call(
    summary_harness, monkeypatch,
):
    from viraldy.modules.smart_remake import loading_summary
    from viraldy.modules.smart_remake.engine.schemas import UploadedMedia
    from viraldy.modules.smart_remake.quick_preview_media import QuickPreviewMedia

    h = summary_harness
    monkeypatch.setattr(
        loading_summary, "prepare_quick_preview", lambda *args: QuickPreviewMedia(
            tuple(
                UploadedMedia(bytes=f"image-{i}".encode(), mime_type="image/jpeg") for i in range(6)
            ),
            "sampled_frames", False, 30, "a" * 64,
        ),
    )
    h.result["sourceAudio"] = {
        "schemaVersion": 1, "speech": "present", "transcript": "Do not invent this.",
        "music": "present",
    }
    await run_summary(h)
    assert len(h.constructors) == len(h.http) == 1 and len(h.request["media"]) == 6
    assert all(media["mime_type"] == "image/jpeg" for media in h.request["media"])
    assert "sourceAudio" not in h.operation.result_json["analysisProgress"]["quickSummary"]
    assert "sáu khung hình" in h.request["prompt"]
    assert "Không có âm thanh" in h.request["system_instruction"]


@pytest.mark.parametrize("cause,reason", [
    (TimeoutError("private timeout"), "timeout"),
    (ValueError("private model JSON"), "invalid_response"),
    (RuntimeError("private provider secret"), "unavailable"),
])
def test_failure_reason_retains_only_allowlisted_enum_through_ledger_wrapper(cause, reason):
    from viraldy.modules.smart_remake.loading_summary import _failure_reason
    from viraldy.shared.errors.base import AppError

    error = AppError("SMART_REMAKE_MODEL_ATTEMPT_UNCERTAIN", "Reconcile")
    error.__cause__ = cause
    assert _failure_reason(error) == reason


def test_truncated_provider_output_is_invalid_response_without_copying_provider_message():
    from viraldy.modules.smart_remake.engine.errors import SmartRemakeError
    from viraldy.modules.smart_remake.loading_summary import _failure_reason

    error = SmartRemakeError("private body", "SMART_REMAKE_GEMINI_OUTPUT_TRUNCATED")
    assert _failure_reason(error) == "invalid_response"


@pytest.mark.asyncio
async def test_terminal_operation_does_not_start_a_late_paid_summary(summary_harness):
    h = summary_harness
    h.operation.status = "completed"
    await run_summary(h)
    assert not h.constructors


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status", [None, "reserved", "submitted", "unknown", "completed", "failed"]
)
async def test_cancellation_retains_exact_summary_receipt_without_refunding_submitted(
    summary_harness, monkeypatch, status
):
    from viraldy.modules.smart_remake import loading_summary

    h = summary_harness
    attempt = None if status is None else SimpleNamespace(id=uuid4(), status=status)
    h.session.scalar.return_value = attempt
    failed, unknown = AsyncMock(), AsyncMock()
    monkeypatch.setattr(loading_summary, "fail_attempt", failed)
    monkeypatch.setattr(loading_summary, "unknown_attempt", unknown)
    await loading_summary._settle_cancelled_summary(
        h.factory, h.workspace, h.project_id, h.operation.id
    )
    assert failed.await_count == int(status == "reserved")
    assert unknown.await_count == int(status in {"submitted", "unknown"})
    if status == "reserved":
        assert failed.await_args.kwargs["definitely_not_submitted"] is True
    if status in {"submitted", "unknown"}:
        assert "actual_usd" not in unknown.await_args.kwargs
    query = str(h.session.scalar.await_args.args[0])
    assert "idempotency_key" in query and "purpose" in query and "workspace_id" in query


@pytest.mark.asyncio
async def test_cancelling_inflight_optional_call_books_unknown_in_a_fresh_session(
    summary_harness, monkeypatch
):
    import asyncio

    from viraldy.modules.smart_remake import loading_summary

    h = summary_harness
    h.started, h.release = asyncio.Event(), asyncio.Event()
    h.session.scalar.return_value = SimpleNamespace(id=uuid4(), status="submitted")
    unknown = AsyncMock()
    monkeypatch.setattr(loading_summary, "unknown_attempt", unknown)
    task = asyncio.create_task(run_summary(h))
    await h.started.wait()
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)
    unknown.assert_awaited_once()


@pytest.mark.asyncio
async def test_summary_start_is_scoped_to_its_own_engine_session(monkeypatch):
    from sqlalchemy.ext.asyncio import create_async_engine

    from viraldy.modules.smart_remake import loading_summary
    from viraldy.modules.smart_remake.engine.schemas import UploadedMedia

    engine = create_async_engine("postgresql+asyncpg://example:example@127.0.0.1/example")
    factory = object()
    maker = []

    async def runner(*args):
        assert args[0] is factory

    monkeypatch.setattr(loading_summary, "_run_summary", runner)
    monkeypatch.setattr(
        loading_summary,
        "async_sessionmaker",
        lambda *args, **kwargs: maker.append((args, kwargs)) or factory,
    )
    try:
        task = loading_summary.start_loading_summary(
            SimpleNamespace(bind=engine),
            workspace_id=uuid4(),
            project_id=uuid4(),
            operation_id=uuid4(),
            actor_id=None,
            source=UploadedMedia(bytes=b"source", mime_type="video/mp4"),
            duration=30,
            mode="live",
        )
        assert task is not None and maker[0][0] == (engine,)
        await task
        await loading_summary.finish_loading_summary(task)
        await loading_summary.finish_loading_summary(None)
        assert (
            loading_summary.start_loading_summary(
                SimpleNamespace(),
                workspace_id=uuid4(),
                project_id=uuid4(),
                operation_id=uuid4(),
                actor_id=None,
                source=UploadedMedia(bytes=b"source", mime_type="video/mp4"),
                duration=30,
                mode="live",
            )
            is None
        )
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_unavailable_status_write_failure_is_optional_and_redacted(
    summary_harness, monkeypatch
):
    from viraldy.modules.smart_remake import loading_summary

    h = summary_harness
    h.error = RuntimeError("provider-secret-should-not-be-logged")
    monkeypatch.setattr(
        loading_summary, "_publish", AsyncMock(side_effect=RuntimeError("database unavailable"))
    )
    await run_summary(h)
    assert h.operation.status == "running" and len(h.constructors) == 1


@pytest.mark.asyncio
async def test_malformed_saved_optional_summary_never_breaks_project_reads():
    session, operation = state()
    await checkpoint_analysis(session, operation, "analyzing_source", request_key="compile-current")
    for value in ([], {"status": {}}, {"status": "wrong"}):
        operation.result_json["analysisProgress"]["quickSummary"] = value
        assert "quickSummary" not in public_analysis_progress(operation)
    operation.result_json["analysisProgress"]["quickSummary"] = {
        "status": "completed",
        "summary": "",
    }
    assert public_analysis_progress(operation)["quickSummary"] == {"status": "unavailable"}
