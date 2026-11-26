"""Celery bridge for local assembly of reviewed, retained clips."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from uuid import UUID

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from viraldy.modules.jobs.models import ProcessingJobModel
from viraldy.platform.config.settings import Settings
from viraldy.shared.errors.base import AppError

from .kie_workflow import _service
from .timeline_service import TimelineWorkflow


def execute_compose_job(
    job: ProcessingJobModel, settings: Settings, ensure_active: Callable[[], None]
) -> dict[str, object]:
    if job.subject_type != "smart_remake_project" or str(job.subject_id) != str(
        job.input_json.get("project_id")
    ):
        raise AppError("SMART_REMAKE_JOB_BINDING_INVALID", "Invalid timeline job binding.")

    async def execute() -> dict[str, object]:
        engine = create_async_engine(settings.database_url, pool_pre_ping=True)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        try:
            async with factory() as session:
                operation_id = UUID(str(job.input_json["operation_id"]))
                return await TimelineWorkflow(
                    _service(session, settings, job.workspace_id), ensure_active=ensure_active
                ).execute(job.subject_id, operation_id)
        finally:
            await engine.dispose()

    return asyncio.run(execute())
