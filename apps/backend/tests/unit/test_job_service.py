from __future__ import annotations

from datetime import UTC, datetime
from typing import cast
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from viraldy.modules.jobs.dispatcher import DispatchResult
from viraldy.modules.jobs.models import ProcessingJobModel
from viraldy.modules.jobs.service import JobService


class FakeSession:
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1


class FakeDispatcher:
    def __init__(self) -> None:
        self.dispatched: list[UUID] = []
        self.mvp_dispatched: list[UUID] = []

    def dispatch_process_asset(self, job_id: UUID) -> DispatchResult:
        self.dispatched.append(job_id)
        return DispatchResult(task_id="task-1", dispatched=True)

    def dispatch_mvp_job(self, job_id: UUID) -> DispatchResult:
        self.mvp_dispatched.append(job_id)
        return DispatchResult(task_id="task-1", dispatched=True)


class FakeJobRepository:
    def __init__(self, session: FakeSession) -> None:
        self.session = session
        self.created = False
        self.job_id = uuid4()
        self.existing_job: ProcessingJobModel | None = None
        self.events: list[str] = []

    async def get_existing_idempotent(
        self, workspace_id: UUID, job_type: str, idempotency_key: str | None
    ) -> ProcessingJobModel | None:
        return self.existing_job

    async def create_process_asset_job(
        self,
        workspace_id: UUID,
        asset_id: UUID,
        asset_version_id: UUID,
        idempotency_key: str | None,
    ) -> ProcessingJobModel:
        self.created = True
        now = datetime.now(UTC)
        return ProcessingJobModel(
            id=self.job_id,
            workspace_id=workspace_id,
            subject_type="asset",
            subject_id=asset_id,
            job_type="process_asset",
            queue_name="default",
            status="queued",
            progress=0,
            stage="queued",
            attempt_count=0,
            max_attempts=3,
            idempotency_key=idempotency_key,
            input_json={
                "asset_id": str(asset_id),
                "asset_version_id": str(asset_version_id),
            },
            output_json=None,
            error_code=None,
            error_message=None,
            task_id=None,
            queued_at=now,
            started_at=None,
            completed_at=None,
            created_at=now,
            updated_at=now,
        )

    async def create_mvp_job(
        self,
        workspace_id: UUID,
        subject_type: str,
        subject_id: UUID,
        job_type: str,
        input_json: dict[str, object],
        idempotency_key: str | None,
    ) -> ProcessingJobModel:
        self.created = True
        now = datetime.now(UTC)
        return ProcessingJobModel(
            id=self.job_id,
            workspace_id=workspace_id,
            subject_type=subject_type,
            subject_id=subject_id,
            job_type=job_type,
            queue_name="default",
            status="queued",
            progress=0,
            stage="queued",
            attempt_count=0,
            max_attempts=3,
            idempotency_key=idempotency_key,
            input_json=input_json,
            output_json=None,
            error_code=None,
            error_message=None,
            task_id=None,
            queued_at=now,
            started_at=None,
            completed_at=None,
            created_at=now,
            updated_at=now,
        )

    async def record_dispatch_requested(self, job: ProcessingJobModel) -> None:
        self.events.append(f"dispatch_requested:{job.id}")

    async def record_dispatch_succeeded(self, job: ProcessingJobModel, task_id: str | None) -> None:
        job.task_id = task_id
        self.events.append(f"dispatch_succeeded:{task_id}")

    async def record_dispatch_failed(self, job: ProcessingJobModel, message: str) -> None:
        self.events.append(f"dispatch_failed:{message}")


@pytest.mark.asyncio
async def test_job_service_commits_before_dispatching_process_asset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import viraldy.modules.jobs.service as service_module

    session = FakeSession()
    dispatcher = FakeDispatcher()
    repository = FakeJobRepository(session)
    monkeypatch.setattr(service_module, "JobRepository", lambda _: repository)

    job = await JobService(cast(AsyncSession, session), dispatcher).request_process_asset(
        workspace_id=uuid4(),
        asset_id=uuid4(),
        asset_version_id=uuid4(),
        idempotency_key="idem-1",
    )

    assert repository.created
    assert session.commits == 3
    assert dispatcher.dispatched == [job.id]
    assert repository.events == [
        f"dispatch_requested:{job.id}",
        "dispatch_succeeded:task-1",
    ]
    assert job.task_id == "task-1"


@pytest.mark.asyncio
async def test_job_service_does_not_dispatch_existing_idempotent_job(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import viraldy.modules.jobs.service as service_module

    session = FakeSession()
    dispatcher = FakeDispatcher()
    repository = FakeJobRepository(session)
    now = datetime.now(UTC)
    existing_job = ProcessingJobModel(
        id=uuid4(),
        workspace_id=uuid4(),
        subject_type="asset",
        subject_id=uuid4(),
        job_type="process_asset",
        queue_name="default",
        status="queued",
        progress=0,
        stage="queued",
        attempt_count=0,
        max_attempts=3,
        idempotency_key="idem-1",
        input_json={"asset_id": str(uuid4()), "asset_version_id": str(uuid4())},
        output_json=None,
        error_code=None,
        error_message=None,
        task_id=None,
        queued_at=now,
        started_at=None,
        completed_at=None,
        created_at=now,
        updated_at=now,
    )
    repository.existing_job = existing_job
    monkeypatch.setattr(service_module, "JobRepository", lambda _: repository)

    job = await JobService(cast(AsyncSession, session), dispatcher).request_process_asset(
        workspace_id=existing_job.workspace_id,
        asset_id=uuid4(),
        asset_version_id=uuid4(),
        idempotency_key="idem-1",
    )

    assert job.id == existing_job.id
    assert not repository.created
    assert session.commits == 1
    assert dispatcher.dispatched == []
