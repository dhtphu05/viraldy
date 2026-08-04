from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

import pytest

from viraldy.modules.assets.public import AssetVersionSnapshot
from viraldy.modules.jobs.registry import JobType, get_job_definition
from viraldy.shared.errors.base import AppError
from viraldy.worker.tasks import process_asset as worker


def test_tiktok_score_job_registry_exposes_real_v2_stages() -> None:
    definition = get_job_definition(JobType.TIKTOK_SCORE_RUN.value)

    assert definition.required_stages == (
        "extracting_media",
        "building_evidence",
        "building_scene_inventory",
        "scoring",
        "compiling_fixes",
        "validating_output",
        "persisting",
    )
    assert definition.optional_stages == ("enriching_direction",)
    assert definition.soft_timeout_seconds == 2340
    assert definition.hard_timeout_seconds == 2400


def test_tiktok_score_worker_uses_snapshots_v2_engine_and_normalized_persistence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace_id = uuid4()
    job_id = uuid4()
    run_id = uuid4()
    asset_id = uuid4()
    asset_version_id = uuid4()
    model_run_id = uuid4()
    actor_user_id = uuid4()
    evidence_id = uuid4()
    product_snapshot = object()
    direction_context = object()
    result_payload = {
        "schema_version": "tiktok_diagnostic_v2",
        "overall_score": 82,
        "overall_confidence": "high",
        "creative_structure_decision": "structurally_ready",
        "paid_use_rights_status": "not_applicable",
        "final_paid_readiness": "not_applicable",
        "dimensions": [],
        "findings": [],
        "required_fixes": [],
        "strengths": [],
        "evidence_ids": [str(evidence_id)],
        "scene_inventory": {"asset_version_id": str(asset_version_id)},
        "auxiliary_signals": {},
        "optional_upgrades": [],
        "policy_pack_versions": {"test_pack": "2026.1"},
        "product_snapshot_hash": "product-hash",
    }
    result = _Result(result_payload)
    evidence = [
        SimpleNamespace(
            id=evidence_id,
            provider="fixture",
            model_version="fixture-vision-v2",
            pipeline_version="media-pipeline-v2",
        )
    ]
    run = SimpleNamespace(
        id=run_id,
        workspace_id=workspace_id,
        status="queued",
        asset_id=asset_id,
        asset_version_id=asset_version_id,
        score_mode="product_aware",
        score_profile="product_led_demo_v1",
        profile_selection_mode="user_selected",
        profile_selection_confidence=1,
        alternative_profiles_json=["general_tiktok_v1"],
        profile_evidence_ids_json=[],
        intended_use="tiktok_organic",
        product_context_snapshot_json={"immutable": "product-snapshot"},
        product_context_snapshot_hash="product-hash",
        creative_direction_context_snapshot_json={"immutable": "direction-snapshot"},
        creative_direction_context_version=3,
        creative_direction_lookup_error=None,
        model_provider_versions_json={"request": "snapshotted"},
        prompt_versions_json={"media": "prompt-v1"},
        analysis_mode="fixture",
        media_checksum_sha256="abc123",
    )
    job = SimpleNamespace(
        id=job_id,
        workspace_id=workspace_id,
        subject_type="tiktok_score_run",
        subject_id=run_id,
        job_type=JobType.TIKTOK_SCORE_RUN.value,
        input_json={
            "score_run_id": str(run_id),
            "asset_id": str(asset_id),
            "asset_version_id": str(asset_version_id),
            "actor_user_id": str(actor_user_id),
            "objective": "product demonstration",
            "target_query": "counter organizer",
            "target_buyer_question": None,
            "selected_search_topic": None,
            "content_gap_topic": None,
            "search_context": {
                "target_query": "counter organizer",
                "target_buyer_question": None,
                "selected_search_topic": None,
                "content_gap_topic": None,
            },
        },
    )
    loaded = AssetVersionSnapshot(
        asset_id=asset_id,
        asset_version_id=asset_version_id,
        workspace_id=workspace_id,
        product_id=uuid4(),
        storage_key="assets/video.mp4",
        original_filename="video.mp4",
        declared_mime_type="video/mp4",
        detected_mime_type="video/mp4",
        size_bytes=1234,
        checksum_sha256="abc123",
        metadata_json={
            "media": {
                "duration_ms": 10_000,
                "audio_stream_count": 1,
            }
        },
    )
    session = _Session()
    job_repository = _JobRepository()
    asset_queries = _AssetQueries(loaded)
    score_repository = _ScoreRepository(run)
    publisher = _Publisher()
    analysis_calls: list[dict[str, object]] = []

    def analyze(evidence_arg: list[object], **kwargs: object) -> _Result:
        analysis_calls.append({"evidence": evidence_arg, **kwargs})
        stage_callback = kwargs["stage_callback"]
        assert callable(stage_callback)
        for stage in (
            "building_scene_inventory",
            "scoring",
            "compiling_fixes",
            "enriching_direction",
        ):
            stage_callback(stage)
        return result

    monkeypatch.setattr(worker, "SyncTikTokScoreRepository", lambda _session: score_repository)
    monkeypatch.setattr(
        worker,
        "SyncMediaEvidencePipeline",
        lambda _session, _settings: _Pipeline(
            evidence,
            model_run_id,
            product_snapshot,
        ),
    )
    monkeypatch.setattr(worker, "SyncProductEventPublisher", lambda _session: publisher)
    monkeypatch.setattr(worker, "analyze_tiktok_evidence_v2", analyze)
    monkeypatch.setattr(
        worker.ProductContextSnapshot,
        "model_validate",
        lambda _payload: product_snapshot,
    )
    monkeypatch.setattr(
        worker.CreativeDirectionContextV1,
        "model_validate",
        lambda _payload: direction_context,
    )
    monkeypatch.setattr(
        worker.TikTokScoreResultV2,
        "model_validate",
        lambda value: value,
    )
    monkeypatch.setattr(worker, "get_settings", lambda: SimpleNamespace(ai_mode="fixture"))

    output = worker._score_tiktok_asset(
        job,
        job_repository,
        asset_queries,
        session,
    )

    assert [stage for _, stage in job_repository.progress] == [
        "extracting_media",
        "building_evidence",
        "building_scene_inventory",
        "scoring",
        "compiling_fixes",
        "enriching_direction",
        "validating_output",
        "persisting",
    ]
    assert score_repository.stages == [
        "extracting_media",
        "building_evidence",
        "building_scene_inventory",
        "scoring",
        "compiling_fixes",
        "enriching_direction",
        "validating_output",
        "persisting",
    ]
    assert analysis_calls[0]["evidence"] == evidence
    assert analysis_calls[0]["product_context_snapshot"] is product_snapshot
    assert analysis_calls[0]["direction_context"] is direction_context
    assert analysis_calls[0]["asset_version_id"] == asset_version_id
    assert analysis_calls[0]["duration_ms"] == 10_000
    assert analysis_calls[0]["audio_available"] is True
    assert analysis_calls[0]["target_query"] == "counter organizer"
    profile_selection = analysis_calls[0]["profile_selection"]
    assert profile_selection.profile_code == "product_led_demo_v1"
    assert score_repository.persisted_result == result_payload
    assert score_repository.persist_kwargs["processing_job_id"] == job_id
    assert score_repository.persist_kwargs["primary_model_run_id"] == model_run_id
    assert score_repository.persist_kwargs["model_version"]
    assert score_repository.persist_kwargs["model_provider_versions"] == {
        "request": "snapshotted",
        "scorer": {
            "provider": "deterministic",
            "model_version": "deterministic_tiktok_diagnostic_v2",
        },
        "media_evidence": [
            {
                "provider": "fixture",
                "model_version": "fixture-vision-v2",
                "pipeline_version": "media-pipeline-v2",
            }
        ],
    }
    assert publisher.records[0]["event_type"] == "tiktok_score_completed"
    assert publisher.records[0]["subject_id"] == run_id
    assert publisher.records[0]["payload_json"]["asset_version_id"] == str(
        asset_version_id
    )
    assert output == {
        "score_run_id": str(run_id),
        "asset_version_id": str(asset_version_id),
        "structural_score": 82,
        "action": "structurally_ready",
        "confidence": "high",
        "analysis_mode": "fixture",
        "primary_model_run_id": str(model_run_id),
    }


def test_tiktok_score_worker_returns_completed_immutable_run_without_rescoring(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace_id = uuid4()
    run_id = uuid4()
    comparison_id = uuid4()
    run = SimpleNamespace(
        id=run_id,
        workspace_id=workspace_id,
        asset_version_id=uuid4(),
        status="completed",
        result_json={
            "overall_score": 79,
            "overall_confidence": "medium",
            "creative_structure_decision": "usable_with_improvements",
        },
        structural_score=79,
        confidence="medium",
        creative_structure_decision="usable_with_improvements",
        analysis_mode="fixture",
        primary_model_run_id=None,
    )
    job = SimpleNamespace(
        id=uuid4(),
        workspace_id=workspace_id,
        input_json={
            "score_run_id": str(run_id),
            "comparison_id": str(comparison_id),
        },
    )
    repository = _ScoreRepository(run)
    monkeypatch.setattr(worker, "SyncTikTokScoreRepository", lambda _session: repository)
    monkeypatch.setattr(
        worker,
        "analyze_tiktok_evidence_v2",
        lambda *_args, **_kwargs: pytest.fail("completed run must not be rescored"),
    )

    output = worker._score_tiktok_asset(
        job,
        _JobRepository(),
        object(),
        _Session(),
    )

    assert output == {
        "score_run_id": str(run_id),
        "asset_version_id": str(run.asset_version_id),
        "structural_score": 79,
        "action": "usable_with_improvements",
        "confidence": "medium",
        "analysis_mode": "fixture",
        "primary_model_run_id": None,
        "comparison_id": str(comparison_id),
    }
    assert repository.stages == []


@pytest.mark.parametrize("terminal", [False, True])
def test_tiktok_score_failure_state_tracks_retry_and_terminal_event(
    monkeypatch: pytest.MonkeyPatch,
    terminal: bool,
) -> None:
    workspace_id = uuid4()
    run_id = uuid4()
    job_id = uuid4()
    run = SimpleNamespace(
        id=run_id,
        workspace_id=workspace_id,
        asset_version_id=uuid4(),
        score_mode="quick",
        score_profile="general_tiktok_v1",
        intended_use="tiktok_organic",
    )
    job = SimpleNamespace(
        id=job_id,
        workspace_id=workspace_id,
        subject_id=run_id,
        job_type=JobType.TIKTOK_SCORE_RUN.value,
        input_json={"score_run_id": str(run_id)},
    )
    score_repository = _ScoreRepository(run)
    publisher = _Publisher()
    monkeypatch.setattr(worker, "SyncTikTokScoreRepository", lambda _session: score_repository)
    monkeypatch.setattr(worker, "SyncProductEventPublisher", lambda _session: publisher)

    worker._update_tiktok_score_failure_state(
        job,
        _Session(),
        "TEST_FAILURE",
        terminal=terminal,
    )

    if terminal:
        assert score_repository.failures == [("TEST_FAILURE", job_id)]
        assert score_repository.stages == []
        assert publisher.records[0]["event_type"] == "tiktok_score_failed"
        assert publisher.records[0]["payload_json"]["failure_code"] == "TEST_FAILURE"
    else:
        assert score_repository.failures == []
        assert score_repository.stages == ["retrying"]
        assert publisher.records == []


def test_invalid_snapshotted_direction_is_isolated_and_reported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run = SimpleNamespace(
        id=uuid4(),
        creative_direction_context_snapshot_json={"invalid": "snapshot"},
        creative_direction_context_version=4,
        creative_direction_lookup_error=None,
    )
    monkeypatch.setattr(
        worker.CreativeDirectionContextV1,
        "model_validate",
        lambda _payload: (_ for _ in ()).throw(ValueError("invalid direction")),
    )

    context, uncertainty = worker._direction_context_from_run(run)
    result = worker._append_direction_uncertainty(
        _Result({"uncertainty": []}),
        uncertainty,
    )

    assert context is None
    assert result.uncertainty == ["optional creative direction unavailable"]


def test_revision_worker_completes_comparison_and_persists_verified_actions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace_id = uuid4()
    parent_run_id = uuid4()
    child_run_id = uuid4()
    comparison_id = uuid4()
    accepted_fix_id = uuid4()
    actor_user_id = uuid4()
    run = SimpleNamespace(id=child_run_id, workspace_id=workspace_id)
    comparison = SimpleNamespace(
        id=comparison_id,
        before_score_run_id=parent_run_id,
        after_score_run_id=child_run_id,
        accepted_fix_action_ids_json=[str(accepted_fix_id)],
    )
    job = SimpleNamespace(
        id=uuid4(),
        workspace_id=workspace_id,
        input_json={
            "comparison_id": str(comparison_id),
            "actor_user_id": str(actor_user_id),
        },
    )
    before_result = object()
    after_result = object()
    comparison_result = _ComparisonResult(accepted_fix_id)
    repository = _ScoreRepository(run)
    repository.comparison = comparison
    repository.parent_result_payload = {"schema_version": "tiktok_diagnostic_v2"}
    compare_calls: list[tuple[object, object, list[UUID]]] = []

    def compare(
        before: object,
        after: object,
        accepted_ids: list[UUID],
    ) -> _ComparisonResult:
        compare_calls.append((before, after, accepted_ids))
        return comparison_result

    monkeypatch.setattr(
        worker.TikTokScoreResultV2,
        "model_validate",
        lambda payload: before_result,
    )
    monkeypatch.setattr(worker, "compare_score_results", compare)

    persisted_id = worker._persist_tiktok_comparison_if_requested(
        job,
        run,
        repository,
        after_result,
    )

    assert persisted_id == comparison_id
    assert compare_calls == [(before_result, after_result, [accepted_fix_id])]
    assert repository.persisted_comparison == {
        "schema_version": "tiktok_score_comparison_v1",
    }
    assert repository.verified_action_events == [
        {
            "comparison": comparison,
            "fix_action_id": accepted_fix_id,
            "actor_user_id": actor_user_id,
            "details_json": {
                "comparison_id": str(comparison_id),
                "verification": {
                    "action_id": str(accepted_fix_id),
                    "status": "verified",
                },
            },
        }
    ]


def test_processing_job_terminal_app_error_updates_score_failure_in_same_transaction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    job = _lifecycle_job()
    session = _LifecycleSession()
    repository = _LifecycleJobRepository(job)
    failure_calls: list[tuple[str, bool]] = []
    monkeypatch.setattr(worker, "create_worker_session", lambda: session)
    monkeypatch.setattr(worker, "WorkerJobRepository", lambda _session: repository)
    monkeypatch.setattr(worker, "SyncAssetQueries", lambda _session: object())
    monkeypatch.setattr(
        worker,
        "_execute_job",
        lambda *_args: (_ for _ in ()).throw(AppError("SCORE_INVALID", "Invalid score.")),
    )
    monkeypatch.setattr(
        worker,
        "_update_tiktok_score_failure_state",
        lambda _job, _session, code, *, terminal: failure_calls.append((code, terminal)),
    )

    output = worker.run_processing_job.run(str(job.id))

    assert output == {
        "error_code": "SCORE_INVALID",
        "error_message": "Invalid score.",
    }
    assert repository.failed == [("SCORE_INVALID", "Invalid score.")]
    assert failure_calls == [("SCORE_INVALID", True)]
    assert session.rollback_count == 1
    assert session.closed is True


def test_processing_job_retry_updates_score_stage_without_failure_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    job = _lifecycle_job()
    session = _LifecycleSession()
    repository = _LifecycleJobRepository(job)
    failure_calls: list[tuple[str, bool]] = []
    monkeypatch.setattr(worker, "create_worker_session", lambda: session)
    monkeypatch.setattr(worker, "WorkerJobRepository", lambda _session: repository)
    monkeypatch.setattr(worker, "SyncAssetQueries", lambda _session: object())
    monkeypatch.setattr(
        worker,
        "_execute_job",
        lambda *_args: (_ for _ in ()).throw(RuntimeError("provider unavailable")),
    )
    monkeypatch.setattr(
        worker,
        "_update_tiktok_score_failure_state",
        lambda _job, _session, code, *, terminal: failure_calls.append((code, terminal)),
    )
    monkeypatch.setattr(
        worker.run_processing_job,
        "retry",
        lambda **_kwargs: RuntimeError("retry scheduled"),
    )

    with pytest.raises(RuntimeError, match="retry scheduled"):
        worker.run_processing_job.run(str(job.id))

    assert repository.retrying == [
        ("PROCESS_ASSET_RETRY", "Asset processing retry scheduled.")
    ]
    assert failure_calls == [("PROCESS_ASSET_RETRY", False)]
    assert session.rollback_count == 1
    assert session.closed is True


class _Result:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload
        self.overall_score = payload.get("overall_score")
        self.overall_confidence = payload.get("overall_confidence")
        self.creative_structure_decision = payload.get("creative_structure_decision")
        self.uncertainty = list(payload.get("uncertainty", []))

    def model_dump(self, *, mode: str) -> dict[str, object]:
        assert mode == "json"
        return self._payload

    def model_copy(self, *, update: dict[str, object]) -> _Result:
        return _Result({**self._payload, **update})


class _Verification:
    def __init__(self, action_id: UUID) -> None:
        self.action_id = action_id
        self.status = "verified"

    def model_dump(self, *, mode: str) -> dict[str, object]:
        assert mode == "json"
        return {"action_id": str(self.action_id), "status": self.status}


class _ComparisonResult:
    def __init__(self, accepted_fix_id: UUID) -> None:
        self.actions_verified = [_Verification(accepted_fix_id)]

    def model_dump(self, *, mode: str) -> dict[str, object]:
        assert mode == "json"
        return {"schema_version": "tiktok_score_comparison_v1"}


class _Session:
    def __init__(self) -> None:
        self.commit_count = 0

    def commit(self) -> None:
        self.commit_count += 1


class _LifecycleSession(_Session):
    def __init__(self) -> None:
        super().__init__()
        self.rollback_count = 0
        self.closed = False

    def rollback(self) -> None:
        self.rollback_count += 1

    def close(self) -> None:
        self.closed = True


class _LifecycleJobRepository:
    def __init__(self, job: SimpleNamespace) -> None:
        self._job = job
        self.failed: list[tuple[str, str]] = []
        self.retrying: list[tuple[str, str]] = []

    def claim_job(self, _job_id: UUID) -> SimpleNamespace:
        return self._job

    def load_job(self, _job_id: UUID) -> SimpleNamespace:
        return self._job

    def mark_failed(self, _job: object, code: str, message: str) -> None:
        self.failed.append((code, message))

    def mark_retrying(self, _job: object, code: str, message: str) -> None:
        self.retrying.append((code, message))


def _lifecycle_job() -> SimpleNamespace:
    run_id = uuid4()
    return SimpleNamespace(
        id=uuid4(),
        workspace_id=uuid4(),
        subject_id=run_id,
        subject_type="tiktok_score_run",
        job_type=JobType.TIKTOK_SCORE_RUN.value,
        input_json={"score_run_id": str(run_id)},
        attempt_count=1,
        max_attempts=3,
    )


class _JobRepository:
    def __init__(self) -> None:
        self.progress: list[tuple[int, str]] = []

    def update_progress(self, _job: object, progress: int, stage: str) -> None:
        self.progress.append((progress, stage))


class _AssetQueries:
    def __init__(self, snapshot: AssetVersionSnapshot) -> None:
        self._snapshot = snapshot

    def load_asset_version(
        self,
        asset_id: UUID,
        version_id: UUID,
    ) -> AssetVersionSnapshot | None:
        assert asset_id == self._snapshot.asset_id
        assert version_id == self._snapshot.asset_version_id
        return self._snapshot


class _Pipeline:
    def __init__(
        self,
        evidence: list[object],
        model_run_id: UUID,
        expected_product_snapshot: object,
    ) -> None:
        self._evidence = evidence
        self._model_run_id = model_run_id
        self._expected_product_snapshot = expected_product_snapshot

    def process_with_metadata(
        self,
        snapshot: AssetVersionSnapshot,
        run_type: str,
        _job_id: UUID,
        *,
        product_context_snapshot: object | None = None,
    ) -> SimpleNamespace:
        assert run_type == "tiktok_score_run"
        assert snapshot.product_id is not None
        assert product_context_snapshot is self._expected_product_snapshot
        return SimpleNamespace(
            evidence=self._evidence,
            primary_model_run_id=self._model_run_id,
        )


class _ScoreRepository:
    def __init__(self, run: object) -> None:
        self._run = run
        self.stages: list[str] = []
        self.failures: list[tuple[str, UUID]] = []
        self.persisted_result: dict[str, object] | None = None
        self.persist_kwargs: dict[str, object] = {}
        self.comparison: object | None = None
        self.parent_result_payload: dict[str, object] | None = None
        self.persisted_comparison: dict[str, object] | None = None
        self.verified_action_events: list[dict[str, object]] = []

    def load_run_with_snapshots(self, workspace_id: UUID, score_run_id: UUID) -> object:
        assert workspace_id == self._run.workspace_id
        assert score_run_id == self._run.id
        return self._run

    def update_stage(
        self,
        _run: object,
        stage: str,
        processing_job_id: UUID | None = None,
    ) -> object:
        assert processing_job_id is not None
        self.stages.append(stage)
        return self._run

    def mark_failed(
        self,
        _run: object,
        failure_code: str,
        *,
        processing_job_id: UUID | None = None,
    ) -> object:
        assert processing_job_id is not None
        self.failures.append((failure_code, processing_job_id))
        return self._run

    def persist_v2_result(
        self,
        _run: object,
        result: dict[str, Any],
        **kwargs: object,
    ) -> object:
        self.persisted_result = result
        self.persist_kwargs = kwargs
        return self._run

    def load_comparison(self, workspace_id: UUID, comparison_id: UUID) -> object | None:
        assert workspace_id == self._run.workspace_id
        assert self.comparison is None or comparison_id == self.comparison.id
        return self.comparison

    def load_result_payload(
        self,
        workspace_id: UUID,
        score_run_id: UUID,
    ) -> dict[str, object] | None:
        assert workspace_id == self._run.workspace_id
        assert self.comparison is not None
        assert score_run_id == self.comparison.before_score_run_id
        return self.parent_result_payload

    def persist_comparison_result(
        self,
        _comparison: object,
        result: dict[str, object],
    ) -> object:
        self.persisted_comparison = result
        return _comparison

    def record_verified_action_event(
        self,
        comparison: object,
        fix_action_id: UUID,
        *,
        actor_user_id: UUID | None,
        details_json: dict[str, object],
    ) -> SimpleNamespace:
        self.verified_action_events.append(
            {
                "comparison": comparison,
                "fix_action_id": fix_action_id,
                "actor_user_id": actor_user_id,
                "details_json": details_json,
            }
        )
        return SimpleNamespace(id=uuid4())


class _Publisher:
    def __init__(self) -> None:
        self.records: list[dict[str, Any]] = []

    def record(self, **kwargs: Any) -> SimpleNamespace:
        self.records.append(kwargs)
        return SimpleNamespace(id=uuid4())
