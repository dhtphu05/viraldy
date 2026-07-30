from __future__ import annotations

import asyncio
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from viraldy.modules.deletion.models import (
    DeletionAuditRecordModel,
    StorageDeletionBatchModel,
)
from viraldy.platform.clock.utc import utc_now
from viraldy.platform.storage.ports import StoragePort

StorageCleanupStatus = Literal["pending", "succeeded"]
_SINGLE_KEY_FIELDS = {
    "storage_key",
    "frame_storage_key",
    "thumbnail_storage_key",
    "audio_storage_key",
}
_MULTI_KEY_FIELDS = {"storage_keys", "frame_storage_keys"}


@dataclass(frozen=True, slots=True)
class StorageCleanupResult:
    status: StorageCleanupStatus
    deleted_object_count: int


def extract_storage_keys(payload: object) -> set[str]:
    keys: set[str] = set()

    def visit(value: object) -> None:
        if isinstance(value, Mapping):
            for field, nested in value.items():
                if field in _SINGLE_KEY_FIELDS:
                    _add_key(keys, nested)
                elif field in _MULTI_KEY_FIELDS and isinstance(nested, Sequence):
                    for candidate in nested:
                        _add_key(keys, candidate)
                visit(nested)
        elif isinstance(value, Sequence) and not isinstance(value, str | bytes):
            for nested in value:
                visit(nested)

    visit(payload)
    return keys


def create_storage_deletion_batch(
    session: Session | AsyncSession,
    *,
    workspace_id: UUID,
    source_type: str,
    source_id: UUID | None,
    object_keys: Sequence[str],
) -> StorageDeletionBatchModel:
    normalized_keys: set[str] = set()
    for object_key in object_keys:
        _add_key(normalized_keys, object_key)
    batch = StorageDeletionBatchModel(
        workspace_id=workspace_id,
        source_type=source_type,
        source_id=source_id,
        object_keys_json=sorted(normalized_keys),
        status="pending",
    )
    session.add(batch)
    return batch


async def process_storage_deletion_batch_async(
    session: AsyncSession,
    batch_id: UUID,
    storage: StoragePort,
) -> StorageCleanupResult:
    batch = await session.scalar(
        select(StorageDeletionBatchModel)
        .where(StorageDeletionBatchModel.id == batch_id)
        .with_for_update()
    )
    if batch is None:
        raise RuntimeError("storage deletion batch was not found")
    if batch.status == "succeeded":
        return StorageCleanupResult("succeeded", batch.deleted_object_count)

    try:
        for object_key in batch.object_keys_json:
            await asyncio.to_thread(storage.delete_object, object_key)
    except Exception:
        await session.rollback()
        batch = await session.get(StorageDeletionBatchModel, batch_id)
        if batch is None:
            raise RuntimeError("storage deletion batch was not found") from None
        _mark_pending_failure(batch)
        await _update_async_audit(session, batch, succeeded=False)
        await session.commit()
        return StorageCleanupResult("pending", 0)

    _mark_succeeded(batch)
    await _update_async_audit(session, batch, succeeded=True)
    await session.commit()
    return StorageCleanupResult("succeeded", batch.deleted_object_count)


def process_storage_deletion_batch(
    session: Session,
    batch_id: UUID,
    storage: StoragePort,
) -> StorageCleanupResult:
    batch = session.scalar(
        select(StorageDeletionBatchModel)
        .where(StorageDeletionBatchModel.id == batch_id)
        .with_for_update()
    )
    if batch is None:
        raise RuntimeError("storage deletion batch was not found")
    if batch.status == "succeeded":
        return StorageCleanupResult("succeeded", batch.deleted_object_count)

    try:
        for object_key in batch.object_keys_json:
            storage.delete_object(object_key)
    except Exception:
        session.rollback()
        batch = session.get(StorageDeletionBatchModel, batch_id)
        if batch is None:
            raise RuntimeError("storage deletion batch was not found") from None
        _mark_pending_failure(batch)
        _update_sync_audit(session, batch, succeeded=False)
        session.commit()
        return StorageCleanupResult("pending", 0)

    _mark_succeeded(batch)
    _update_sync_audit(session, batch, succeeded=True)
    session.commit()
    return StorageCleanupResult("succeeded", batch.deleted_object_count)


def process_pending_storage_deletions(
    session: Session,
    storage: StoragePort,
    *,
    limit: int = 50,
) -> dict[str, int]:
    batch_ids = list(
        session.scalars(
            select(StorageDeletionBatchModel.id)
            .where(StorageDeletionBatchModel.status == "pending")
            .order_by(StorageDeletionBatchModel.created_at)
            .limit(limit)
        )
    )
    succeeded = 0
    pending = 0
    deleted_objects = 0
    for batch_id in batch_ids:
        result = process_storage_deletion_batch(session, batch_id, storage)
        if result.status == "succeeded":
            succeeded += 1
            deleted_objects += result.deleted_object_count
        else:
            pending += 1
    return {
        "processed_batch_count": len(batch_ids),
        "succeeded_batch_count": succeeded,
        "pending_batch_count": pending,
        "deleted_object_count": deleted_objects,
    }


def _add_key(keys: set[str], candidate: object) -> None:
    if (
        isinstance(candidate, str)
        and candidate
        and not candidate.startswith("fixtures/")
        and not candidate.startswith(("http://", "https://"))
    ):
        keys.add(candidate)


def _mark_pending_failure(batch: StorageDeletionBatchModel) -> None:
    batch.attempt_count += 1
    batch.safe_error_code = "STORAGE_CLEANUP_RETRY"
    batch.safe_error_message = "Object storage cleanup will be retried."


def _mark_succeeded(batch: StorageDeletionBatchModel) -> None:
    batch.status = "succeeded"
    batch.attempt_count += 1
    batch.deleted_object_count = len(batch.object_keys_json)
    batch.safe_error_code = None
    batch.safe_error_message = None
    batch.completed_at = utc_now()


async def _update_async_audit(
    session: AsyncSession,
    batch: StorageDeletionBatchModel,
    *,
    succeeded: bool,
) -> None:
    if batch.source_type != "hard_delete" or batch.source_id is None:
        return
    audit = await session.get(DeletionAuditRecordModel, batch.source_id)
    if audit is not None:
        _apply_audit_cleanup_result(audit, batch, succeeded=succeeded)


def _update_sync_audit(
    session: Session,
    batch: StorageDeletionBatchModel,
    *,
    succeeded: bool,
) -> None:
    if batch.source_type != "hard_delete" or batch.source_id is None:
        return
    audit = session.get(DeletionAuditRecordModel, batch.source_id)
    if audit is not None:
        _apply_audit_cleanup_result(audit, batch, succeeded=succeeded)


def _apply_audit_cleanup_result(
    audit: DeletionAuditRecordModel,
    batch: StorageDeletionBatchModel,
    *,
    succeeded: bool,
) -> None:
    if succeeded:
        audit.status = "succeeded"
        audit.deleted_object_count = batch.deleted_object_count
        audit.safe_error_code = None
        audit.safe_error_message = None
        audit.completed_at = batch.completed_at
    else:
        audit.status = "storage_cleanup_pending"
        audit.safe_error_code = batch.safe_error_code
        audit.safe_error_message = batch.safe_error_message
