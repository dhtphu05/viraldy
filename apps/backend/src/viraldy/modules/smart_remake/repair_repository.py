from __future__ import annotations

import hashlib
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any
from uuid import UUID

from sqlalchemy import func, select, text, update
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from viraldy.shared.errors.base import AppError, ConflictError, NotFoundError

from .models import SmartRemakeOperationModel, SmartRemakeProjectModel


class RepairRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def project(
        self, workspace_id: UUID, project_id: UUID, *, lock: bool = False
    ) -> SmartRemakeProjectModel:
        statement = (
            select(SmartRemakeProjectModel)
            .where(
                SmartRemakeProjectModel.id == project_id,
                SmartRemakeProjectModel.workspace_id == workspace_id,
            )
            .execution_options(populate_existing=True)
        )
        if lock:
            statement = statement.with_for_update()
        row = (await self.session.execute(statement)).scalar_one_or_none()
        if row is None:
            raise NotFoundError(
                "SMART_REMAKE_PROJECT_NOT_FOUND", "Smart Remake project was not found."
            )
        return row

    async def create(self, row: SmartRemakeProjectModel) -> None:
        self.session.add(row)
        await self.session.commit()

    async def save(self, row: SmartRemakeProjectModel, state: dict[str, Any]) -> None:
        row.state_json = state
        row.revision = state["revision"]
        await self.session.commit()

    async def merge_context(
        self, row: SmartRemakeProjectModel, updates: dict[str, Any]
    ) -> None:
        await self.session.execute(
            update(SmartRemakeProjectModel)
            .where(
                SmartRemakeProjectModel.id == row.id,
                SmartRemakeProjectModel.workspace_id == row.workspace_id,
            )
            .values(context_json=SmartRemakeProjectModel.context_json.concat(updates))
            .execution_options(synchronize_session=False)
        )
        await self.session.commit()
        await self.session.refresh(row)

    async def start(
        self, workspace_id: UUID, project_id: UUID, key: str, request_hash: str
    ) -> tuple[SmartRemakeProjectModel, SmartRemakeOperationModel, bool]:
        project = await self.project(workspace_id, project_id, lock=True)
        existing = (
            await self.session.execute(
                select(SmartRemakeOperationModel).where(
                    SmartRemakeOperationModel.project_id == project_id,
                    SmartRemakeOperationModel.idempotency_key == key,
                )
            )
        ).scalar_one_or_none()
        if existing:
            await self.session.commit()
            if existing.request_hash != request_hash:
                raise ConflictError(
                    "SMART_REMAKE_IDEMPOTENCY_CONFLICT", "This key belongs to a different request."
                )
            return project, existing, False
        running = (
            await self.session.execute(
                select(SmartRemakeOperationModel.id)
                .where(
                    SmartRemakeOperationModel.project_id == project_id,
                    SmartRemakeOperationModel.status == "running",
                )
                .limit(1)
            )
        ).scalar_one_or_none()
        if running:
            await self.session.commit()
            error = ConflictError(
                "SMART_REMAKE_OPERATION_BUSY",
                "An operation is still running. Refresh its status before trying again.",
            )
            error.details = {"operationStatus": "running", "operationId": str(running)}
            raise error
        count = (
            await self.session.execute(
                select(func.count())
                .select_from(SmartRemakeOperationModel)
                .where(SmartRemakeOperationModel.project_id == project_id)
            )
        ).scalar_one()
        if count >= 100:
            await self.session.commit()
            raise AppError(
                "SMART_REMAKE_OPERATION_LIMIT", "This project has reached its operation limit.", 429
            )
        operation = SmartRemakeOperationModel(
            project_id=project_id,
            idempotency_key=key,
            request_hash=request_hash,
            status="running",
            result_json={},
        )
        self.session.add(operation)
        await self.session.commit()
        return project, operation, True

    async def finish(
        self, operation: SmartRemakeOperationModel, status: str, result: dict[str, Any]
    ) -> None:
        operation.status = status
        operation.result_json = result
        await self.session.commit()

    async def running(self, project_id: UUID) -> SmartRemakeOperationModel | None:
        return (
            await self.session.execute(
                select(SmartRemakeOperationModel)
                .where(
                    SmartRemakeOperationModel.project_id == project_id,
                    SmartRemakeOperationModel.status == "running",
                )
                .limit(1)
            )
        ).scalar_one_or_none()

    async def latest_operation(self, project_id: UUID) -> SmartRemakeOperationModel | None:
        return (
            await self.session.execute(
                select(SmartRemakeOperationModel)
                .where(SmartRemakeOperationModel.project_id == project_id)
                .order_by(
                    SmartRemakeOperationModel.created_at.desc(), SmartRemakeOperationModel.id.desc()
                )
                .limit(1)
                .execution_options(populate_existing=True)
            )
        ).scalar_one_or_none()

    async def attach_processing_job(
        self, operation: SmartRemakeOperationModel, job_id: UUID
    ) -> None:
        # A replay may race an executing worker. Merge just this field in SQL;
        # never write a stale status or replace the paid-task manifest.
        await self.session.execute(
            update(SmartRemakeOperationModel)
            .where(SmartRemakeOperationModel.id == operation.id)
            .values(
                result_json=SmartRemakeOperationModel.result_json.concat(
                    {
                        "processingJobId": str(job_id),
                    }
                )
            )
            .execution_options(synchronize_session=False)
        )
        await self.session.commit()
        await self.session.refresh(operation)

    async def operation(
        self, workspace_id: UUID, project_id: UUID, operation_id: UUID
    ) -> SmartRemakeOperationModel:
        await self.project(workspace_id, project_id)
        row = (
            await self.session.execute(
                select(SmartRemakeOperationModel)
                .where(
                    SmartRemakeOperationModel.project_id == project_id,
                    SmartRemakeOperationModel.id == operation_id,
                )
                .execution_options(populate_existing=True)
            )
        ).scalar_one_or_none()
        if row is None:
            raise NotFoundError("SMART_REMAKE_OPERATION_NOT_FOUND", "Operation was not found.")
        return row

    @asynccontextmanager
    async def execution_guard(self, operation_id: UUID) -> AsyncIterator[bool]:
        """Serialize worker/reconciliation across commits without a long transaction."""
        bind = self.session.bind
        if not isinstance(bind, AsyncEngine):
            raise AppError("SMART_REMAKE_WORKER_DATABASE_INVALID", "Async engine is required.")
        lock_key = int.from_bytes(hashlib.sha256(operation_id.bytes).digest()[:8], signed=True)
        # Session-level advisory locks stay bound to this dedicated connection
        # across the ORM's commits. Disconnect after a hard worker kill releases it.
        lease_engine = create_async_engine(bind.url, poolclass=NullPool)
        try:
            async with lease_engine.connect() as connection:
                acquired = bool(
                    await connection.scalar(
                        text("SELECT pg_try_advisory_lock(:key)"), {"key": lock_key}
                    )
                )
                await connection.commit()
                try:
                    yield acquired
                finally:
                    if acquired:
                        await connection.execute(
                            text("SELECT pg_advisory_unlock(:key)"), {"key": lock_key}
                        )
                        await connection.commit()
        finally:
            await lease_engine.dispose()

    async def complete(
        self,
        row: SmartRemakeProjectModel,
        state: dict[str, Any],
        operation: SmartRemakeOperationModel,
        result: dict[str, Any],
    ) -> None:
        row.state_json = state
        row.revision = state["revision"]
        operation.status = "completed"
        operation.result_json = result
        await self.session.commit()

    async def refresh(self, operation: SmartRemakeOperationModel) -> None:
        await self.session.refresh(operation)
