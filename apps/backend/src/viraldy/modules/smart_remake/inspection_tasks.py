"""Celery inspection bridge with scoped operation identity and budgeted VLM calls."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from viraldy.modules.jobs.models import ProcessingJobModel
from viraldy.platform.config.settings import Settings
from viraldy.shared.errors.base import AppError

from .budgeted_analysis import inspection_invoke
from .inspection_service import InspectionService
from .kie_workflow import _service
from .repair_repository import RepairRepository


def execute_inspection_job(
    job: ProcessingJobModel, settings: Settings, ensure_active: Callable[[], None]
) -> dict[str, Any]:
    if job.subject_type != "smart_remake_project" or str(job.subject_id) != str(
        job.input_json.get("project_id")
    ):
        raise AppError("SMART_REMAKE_JOB_BINDING_INVALID", "Invalid inspection job binding.")
    try:
        operation_id = UUID(str(job.input_json["operation_id"]))
    except (KeyError, ValueError, TypeError) as exc:
        raise AppError("SMART_REMAKE_JOB_BINDING_INVALID", "Invalid inspection operation.") from exc

    async def execute() -> dict[str, Any]:
        engine = create_async_engine(settings.database_url, pool_pre_ping=True)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        try:
            async with factory() as session:
                mode = getattr(settings, "ai_mode", None)
                if mode is not None and str(mode).strip().lower() != "live":
                    # Load and stop retained work without constructing the media
                    # adapter or a VLM client. A worker restarted in fixture/mock
                    # must not submit an old queued live operation.
                    ensure_active()
                    repository = RepairRepository(session)
                    operation = await repository.operation(
                        job.workspace_id, job.subject_id, operation_id
                    )
                    if operation.result_json.get("kind") != "inspection":
                        raise AppError(
                            "SMART_REMAKE_JOB_BINDING_INVALID", "Invalid inspection operation kind."
                        )
                    if operation.status == "completed":
                        return operation.result_json
                    if operation.status == "running":
                        intent = operation.result_json
                        await repository.finish(
                            operation,
                            "failed",
                            {
                                **intent,
                                "phase": "mode_blocked",
                                "errorCode": "SMART_REMAKE_INSPECTION_NOT_LIVE",
                                "needsReconciliation": bool(
                                    intent.get("needsReconciliation")
                                    or intent.get("phase") == "invoking"
                                ),
                            },
                        )
                    raise AppError(
                        "SMART_REMAKE_INSPECTION_NOT_LIVE",
                        "Inspection provider calls require live AI mode.",
                        409,
                    )
                repair = _service(session, settings, job.workspace_id)
                operation = await repair.repository.operation(
                    job.workspace_id, job.subject_id, operation_id
                )
                try:
                    actor_id = UUID(operation.result_json["actorId"])
                except (KeyError, ValueError, TypeError) as exc:
                    raise AppError(
                        "SMART_REMAKE_JOB_BINDING_INVALID", "Missing inspection actor."
                    ) from exc
                declared_actor = job.input_json.get("actor_id")
                if declared_actor and str(declared_actor) != str(actor_id):
                    raise AppError("SMART_REMAKE_JOB_BINDING_INVALID", "Inspection actor changed.")
                ensure_active()
                intent = operation.result_json
                snapshot = intent.get("snapshot", {})
                invoke = inspection_invoke(
                    session,
                    job.workspace_id,
                    job.subject_id,
                    operation_id,
                    actor_id,
                    metadata={
                        "contextHash": intent.get("contextHash"),
                        "constraintsHash": snapshot.get("constraintsHash"),
                        "manifestHash": snapshot.get("manifestHash"),
                        "mediaHash": snapshot.get("subject", {}).get("mediaHash"),
                    },
                )

                async def checked_invoke(payload: dict[str, Any]) -> Any:
                    ensure_active()
                    result = await invoke(payload)
                    ensure_active()
                    return result

                checked_invoke.model_profile = getattr(invoke, "model_profile", {})  # type: ignore[attr-defined]
                result = await InspectionService(
                    repair.repository, repair.media, job.workspace_id, settings=settings
                ).execute(job.subject_id, operation_id, invoke_model=checked_invoke)
                ensure_active()
                if result.get("errorCode"):
                    raise AppError(
                        str(result["errorCode"]),
                        "Inspection could not complete. Review the saved operation.",
                        409,
                    )
                return result
        finally:
            await engine.dispose()

    return asyncio.run(execute())
