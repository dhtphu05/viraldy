"""Sync Celery boundary for the asynchronous Smart Remake workflow."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from uuid import UUID

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from viraldy.modules.jobs.models import ProcessingJobModel
from viraldy.platform.config.settings import Settings
from viraldy.shared.errors.base import AppError

from .kie_workflow import KieWorkflow, _service
from .repair_repository import RepairRepository
from .runtime_limits import kie_job_poll_timeout_seconds


def execute_kie_job(
    job: ProcessingJobModel, settings: Settings, ensure_active: Callable[[], None]
) -> dict[str, object]:
    from .service import require_kie_renderer

    if str(job.subject_id) != str(job.input_json.get("project_id")):
        raise AppError("SMART_REMAKE_JOB_BINDING_INVALID", "Smart Remake job binding is invalid.")

    async def execute() -> dict[str, object]:
        # Each asyncio.run has its own loop; do not reuse the API's pooled engine.
        engine = create_async_engine(settings.database_url, pool_pre_ping=True)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        try:
            async with factory() as session:
                operation_id = UUID(str(job.input_json["operation_id"]))
                repository = RepairRepository(session)
                try:
                    require_kie_renderer(settings)
                except AppError as exc:
                    async with repository.execution_guard(operation_id) as acquired:
                        if acquired:
                            operation = await repository.operation(
                                job.workspace_id, job.subject_id, operation_id
                            )
                        if acquired and operation.status == "running":
                            unresolved = any(
                                task.get("taskId") or task.get("status") == "submitting"
                                for task in operation.result_json.get("tasks", {}).values()
                            ) or operation.result_json.get("repairNormalization", {}).get(
                                "phase"
                            ) == "invoking"
                            ensure_active()
                            await repository.finish(
                                operation,
                                "running" if unresolved else "failed",
                                {
                                    **operation.result_json,
                                    "needsReconciliation": unresolved,
                                    "errorCode": exc.code,
                                },
                            )
                    raise
                return await KieWorkflow(
                    _service(session, settings, job.workspace_id),
                    ensure_active=ensure_active,
                    poll_timeout_seconds=kie_job_poll_timeout_seconds(job.input_json),
                ).execute(job.subject_id, operation_id)
        finally:
            await engine.dispose()

    return asyncio.run(execute())
