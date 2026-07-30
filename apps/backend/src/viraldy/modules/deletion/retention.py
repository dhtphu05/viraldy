from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from viraldy.modules.ai_gateway.models import AiModelRunModel
from viraldy.modules.assets.models import AssetModel, AssetVersionModel
from viraldy.modules.deletion.models import StorageDeletionBatchModel
from viraldy.modules.deletion.storage_cleanup import (
    create_storage_deletion_batch,
    extract_storage_keys,
    process_storage_deletion_batch,
)
from viraldy.modules.generation.models import GenerationArtifactModel
from viraldy.modules.media_analysis.models import EvidenceItemModel, MediaArtifactModel
from viraldy.platform.clock.utc import utc_now
from viraldy.platform.config.settings import Settings
from viraldy.platform.storage.ports import StoragePort


@dataclass(frozen=True, slots=True)
class RetentionCutoffs:
    asset_before: datetime
    model_output_before: datetime


def retention_cutoffs(settings: Settings, now: datetime) -> RetentionCutoffs:
    return RetentionCutoffs(
        asset_before=now - timedelta(days=settings.asset_retention_days),
        model_output_before=now - timedelta(days=settings.model_output_retention_days),
    )


def execute_retention_cleanup(
    session: Session,
    workspace_id: UUID,
    settings: Settings,
    storage: StoragePort,
    *,
    now: datetime | None = None,
) -> dict[str, object]:
    cutoffs = retention_cutoffs(settings, now or utc_now())
    expired_asset_ids = list(
        session.scalars(
            select(AssetModel.id).where(
                AssetModel.workspace_id == workspace_id,
                AssetModel.status == "pending_upload",
                AssetModel.created_at < cutoffs.asset_before,
            )
        )
    )
    deleted_objects = 0
    deleted_assets = 0
    storage_keys: set[str] = set()
    batch_id: UUID | None = None
    if expired_asset_ids:
        storage_keys.update(
            session.scalars(
                select(AssetVersionModel.storage_key).where(
                    AssetVersionModel.asset_id.in_(expired_asset_ids)
                )
            )
        )
        session.execute(
            update(AssetModel)
            .where(AssetModel.id.in_(expired_asset_ids))
            .values(current_version_id=None)
        )
        session.execute(
            delete(AssetVersionModel).where(
                AssetVersionModel.asset_id.in_(expired_asset_ids)
            )
        )
        result = session.execute(
            delete(AssetModel).where(AssetModel.id.in_(expired_asset_ids))
        )
        deleted_assets = int(result.rowcount or 0)
    redacted = session.execute(
        update(AiModelRunModel)
        .where(
            AiModelRunModel.workspace_id == workspace_id,
            AiModelRunModel.created_at < cutoffs.model_output_before,
        )
        .values(
            input_summary_json={},
            output_summary_json={},
            error_message=None,
            safe_error_message=None,
        )
    )
    referenced_keys = _workspace_storage_keys(session, workspace_id)
    protected_keys = _pending_cleanup_keys(session, workspace_id)
    orphan_keys = {
        item.key
        for item in storage.list_objects(f"workspaces/{workspace_id}/")
        if item.last_modified < cutoffs.asset_before
        and item.key not in referenced_keys
        and item.key not in protected_keys
    }
    storage_keys.update(orphan_keys)
    if storage_keys:
        batch = create_storage_deletion_batch(
            session,
            workspace_id=workspace_id,
            source_type="retention",
            source_id=None,
            object_keys=sorted(storage_keys),
        )
        session.flush()
        batch_id = batch.id
    session.commit()
    storage_cleanup_status = "succeeded"
    if batch_id is not None:
        cleanup = process_storage_deletion_batch(session, batch_id, storage)
        storage_cleanup_status = cleanup.status
        deleted_objects = cleanup.deleted_object_count
    return {
        "workspace_id": str(workspace_id),
        "deleted_asset_count": deleted_assets,
        "deleted_orphan_count": len(orphan_keys),
        "deleted_object_count": deleted_objects,
        "redacted_model_run_count": int(redacted.rowcount or 0),
        "storage_cleanup_status": storage_cleanup_status,
        "asset_cutoff": cutoffs.asset_before.isoformat(),
        "model_output_cutoff": cutoffs.model_output_before.isoformat(),
    }


def _workspace_storage_keys(session: Session, workspace_id: UUID) -> set[str]:
    keys = set(
        session.scalars(
            select(AssetVersionModel.storage_key)
            .join(AssetModel, AssetVersionModel.asset_id == AssetModel.id)
            .where(AssetModel.workspace_id == workspace_id)
        )
    )
    for model, scalar_column, payload_column in (
        (MediaArtifactModel, MediaArtifactModel.storage_key, MediaArtifactModel.payload_json),
        (EvidenceItemModel, EvidenceItemModel.frame_storage_key, EvidenceItemModel.value_json),
    ):
        rows = session.execute(
            select(scalar_column, payload_column).where(model.workspace_id == workspace_id)
        )
        for scalar_key, payload in rows:
            if scalar_key:
                keys.add(scalar_key)
            keys.update(extract_storage_keys(payload))
    keys.update(
        key
        for key in session.scalars(
            select(GenerationArtifactModel.storage_key).where(
                GenerationArtifactModel.workspace_id == workspace_id
            )
        )
        if key
    )
    return keys


def _pending_cleanup_keys(session: Session, workspace_id: UUID) -> set[str]:
    keys: set[str] = set()
    payloads = session.scalars(
        select(StorageDeletionBatchModel.object_keys_json).where(
            StorageDeletionBatchModel.workspace_id == workspace_id,
            StorageDeletionBatchModel.status == "pending",
        )
    )
    for payload in payloads:
        keys.update(payload)
    return keys
