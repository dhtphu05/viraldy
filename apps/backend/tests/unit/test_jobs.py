from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from viraldy.modules.jobs.dispatcher import CeleryJobDispatcher
from viraldy.modules.jobs.models import ProcessingJobModel
from viraldy.modules.jobs.policies import ensure_transition
from viraldy.modules.jobs.registry import (
    JOB_DEFINITIONS,
    JobType,
    get_job_definition,
    normalize_job_type,
)
from viraldy.modules.jobs.repository import WorkerJobRepository
from viraldy.shared.errors.base import AppError


def test_job_state_machine_allows_queued_to_running() -> None:
    ensure_transition("queued", "running")


def test_job_state_machine_rejects_succeeded_to_running() -> None:
    with pytest.raises(AppError, match="INVALID_JOB_TRANSITION"):
        ensure_transition("succeeded", "running")


def test_private_beta_job_registry_contains_required_types() -> None:
    required = {
        "media_analysis",
        "creative_dna_build",
        "pattern_kit_extract",
        "viral_kit_compose",
        "campaign_pack_generate",
        "preflight_run",
        "storyboard_generate",
        "concept_video_generate",
        "retention_cleanup",
    }

    assert required.issubset(JOB_DEFINITIONS)
    assert get_job_definition(JobType.MEDIA_ANALYSIS.value).job_type is JobType.MEDIA_ANALYSIS


@pytest.mark.parametrize(
    ("legacy", "normalized"),
    [
        ("process_asset", "media_analysis"),
        ("analyze_reference", "creative_dna_build"),
        ("score_tiktok_asset", "tiktok_score_run"),
        ("run_ugc_preflight", "preflight_run"),
    ],
)
def test_legacy_job_types_normalize_without_breaking_queued_deliveries(
    legacy: str,
    normalized: str,
) -> None:
    assert normalize_job_type(legacy) == normalized
    assert get_job_definition(legacy) is get_job_definition(normalized)


def test_stale_job_recovery_retries_or_fails_without_duplicate_execution() -> None:
    now = datetime.now(UTC)
    retry_job = _job(now, attempt_count=1, max_attempts=3, heartbeat_age_seconds=600)
    exhausted_job = _job(now, attempt_count=3, max_attempts=3, heartbeat_age_seconds=600)
    session = _RecoverySession([retry_job, exhausted_job])

    retry_ids = WorkerJobRepository(cast(Session, session)).recover_stale_jobs(
        now,
        minimum_stale_seconds=60,
    )

    assert retry_ids == [retry_job.id]
    assert retry_job.status == "retrying"
    assert retry_job.error_code == "STALE_JOB_RECOVERED"
    assert exhausted_job.status == "failed"
    assert exhausted_job.error_code == "STALE_JOB_ATTEMPTS_EXHAUSTED"
    assert len(session.events) == 2


def test_stale_recovery_waits_for_job_hard_timeout_and_safety_margin() -> None:
    now = datetime.now(UTC)
    still_within_video_window = _job(
        now,
        attempt_count=1,
        max_attempts=3,
        heartbeat_age_seconds=960,
        job_type=JobType.CONCEPT_VIDEO_GENERATE.value,
    )
    session = _RecoverySession([still_within_video_window])

    retry_ids = WorkerJobRepository(cast(Session, session)).recover_stale_jobs(
        now,
        minimum_stale_seconds=60,
        timeout_margin_seconds=120,
    )

    assert retry_ids == []
    assert still_within_video_window.status == "running"
    assert session.events == []


def test_stale_recovery_redispatches_stranded_retrying_job() -> None:
    now = datetime.now(UTC)
    stranded = _job(
        now,
        attempt_count=1,
        max_attempts=3,
        heartbeat_age_seconds=600,
    )
    stranded.status = "retrying"
    session = _RecoverySession([stranded])

    retry_ids = WorkerJobRepository(cast(Session, session)).recover_stale_jobs(
        now,
        minimum_stale_seconds=60,
    )

    assert retry_ids == [stranded.id]
    assert stranded.status == "retrying"
    assert stranded.error_code == "STALE_JOB_RECOVERED"


def test_celery_dispatcher_applies_registered_queue_and_time_limits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from viraldy.worker.tasks import process_asset as worker_module

    calls: list[dict[str, object]] = []

    class _TaskResult:
        id = "task-1"

    def fake_apply_async(**kwargs: object) -> _TaskResult:
        calls.append(kwargs)
        return _TaskResult()

    monkeypatch.setattr(worker_module.run_processing_job, "apply_async", fake_apply_async)
    job_id = uuid4()

    result = CeleryJobDispatcher().dispatch_job(
        job_id,
        JobType.CONCEPT_VIDEO_GENERATE.value,
    )

    assert result.task_id == "task-1"
    assert calls == [
        {
            "args": [str(job_id)],
            "queue": "default",
            "soft_time_limit": 840,
            "time_limit": 900,
        }
    ]


def test_superseded_worker_attempt_cannot_commit_terminal_state() -> None:
    now = datetime.now(UTC)
    job = _job(
        now,
        attempt_count=0,
        max_attempts=3,
        heartbeat_age_seconds=0,
    )
    job.status = "queued"
    session = _ClaimSession(job)
    repository = WorkerJobRepository(cast(Session, session))
    claimed = repository.claim_job(job.id)

    assert claimed is job
    assert job.attempt_count == 1

    job.status = "retrying"
    with pytest.raises(AppError, match="JOB_ATTEMPT_SUPERSEDED"):
        repository.mark_succeeded(job, {"late": True})

    assert job.status == "retrying"
    assert job.output_json is None


class _ScalarResult:
    def __init__(self, jobs: list[ProcessingJobModel]) -> None:
        self._jobs = jobs

    def scalars(self) -> list[ProcessingJobModel]:
        return self._jobs


class _RecoverySession:
    def __init__(self, jobs: list[ProcessingJobModel]) -> None:
        self._jobs = jobs
        self.events: list[object] = []

    def execute(self, statement: object) -> _ScalarResult:
        return _ScalarResult(self._jobs)

    def add(self, event: object) -> None:
        self.events.append(event)


class _ClaimScalarResult:
    def __init__(self, job: ProcessingJobModel) -> None:
        self._job = job

    def scalars(self) -> _ClaimScalarResult:
        return self

    def one_or_none(self) -> ProcessingJobModel:
        return self._job


class _ClaimSession:
    def __init__(self, job: ProcessingJobModel) -> None:
        self._job = job
        self.events: list[object] = []

    def execute(self, statement: object) -> _ClaimScalarResult:
        return _ClaimScalarResult(self._job)

    def add(self, event: object) -> None:
        self.events.append(event)


def _job(
    now: datetime,
    *,
    attempt_count: int,
    max_attempts: int,
    heartbeat_age_seconds: int,
    job_type: str = JobType.MEDIA_ANALYSIS.value,
) -> ProcessingJobModel:
    return ProcessingJobModel(
        id=uuid4(),
        workspace_id=uuid4(),
        subject_type="asset",
        subject_id=uuid4(),
        job_type=job_type,
        queue_name="default",
        status="running",
        progress=40,
        stage="probing_media",
        attempt_count=attempt_count,
        max_attempts=max_attempts,
        idempotency_key=None,
        input_json={},
        output_json=None,
        error_code=None,
        error_message=None,
        task_id=None,
        queued_at=now,
        started_at=now - timedelta(minutes=10),
        completed_at=None,
        created_at=now - timedelta(minutes=10),
        updated_at=now - timedelta(seconds=heartbeat_age_seconds),
    )
