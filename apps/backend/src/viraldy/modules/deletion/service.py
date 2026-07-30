from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from viraldy.modules.deletion.contracts import (
    DeletionResourceType,
    DeletionResult,
)
from viraldy.modules.deletion.repository import DeletionRepository
from viraldy.modules.deletion.storage_cleanup import (
    create_storage_deletion_batch,
    process_storage_deletion_batch_async,
)
from viraldy.platform.storage.ports import StoragePort
from viraldy.shared.errors.base import AppError


class DeletionService:
    def __init__(self, session: AsyncSession, storage: StoragePort) -> None:
        self._session = session
        self._storage = storage
        self._repository = DeletionRepository(session)

    async def delete(
        self,
        *,
        workspace_id: UUID,
        resource_type: DeletionResourceType,
        resource_id: UUID,
        user_id: UUID,
    ) -> DeletionResult:
        if resource_type is DeletionResourceType.WORKSPACE and resource_id != workspace_id:
            raise AppError(
                "DELETION_WORKSPACE_MISMATCH",
                "Workspace deletion must target the current workspace.",
            )
        plan = await self._repository.build_plan(
            workspace_id,
            resource_type,
            resource_id,
        )
        audit = await self._repository.create_audit(
            workspace_id,
            resource_type,
            resource_id,
            user_id,
        )
        try:
            storage_keys = await self._repository.storage_keys(plan)
            row_counts = await self._repository.execute_plan(plan)
            batch = create_storage_deletion_batch(
                self._session,
                workspace_id=workspace_id,
                source_type="hard_delete",
                source_id=audit.id,
                object_keys=storage_keys,
            )
            await self._repository.mark_storage_cleanup_pending(audit, row_counts)
            await self._session.flush()
            batch_id = batch.id
            await self._session.commit()
        except Exception as exc:
            await self._session.rollback()
            await self._repository.mark_failed(
                audit.id,
                "DELETION_FAILED",
                "Data deletion did not complete.",
            )
            if isinstance(exc, AppError):
                raise
            raise AppError(
                "DELETION_FAILED",
                "Data deletion did not complete.",
                status_code=500,
            ) from exc
        cleanup = await process_storage_deletion_batch_async(
            self._session,
            batch_id,
            self._storage,
        )
        refreshed_audit = await self._session.get(type(audit), audit.id)
        if refreshed_audit is None:
            raise AppError(
                "DELETION_AUDIT_MISSING",
                "Data deletion audit record was not found.",
                status_code=500,
            )
        return DeletionResult(
            audit_id=audit.id,
            workspace_id=workspace_id,
            resource_type=resource_type,
            resource_id=resource_id,
            status=(
                "succeeded"
                if cleanup.status == "succeeded"
                else "storage_cleanup_pending"
            ),
            deleted_object_count=cleanup.deleted_object_count,
            deleted_row_counts=row_counts,
            completed_at=refreshed_audit.completed_at,
        )
