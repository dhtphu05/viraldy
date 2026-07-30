from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from sqlalchemy import Column, Table, delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from viraldy.modules.deletion.contracts import DeletionResourceType
from viraldy.modules.deletion.models import DeletionAuditRecordModel
from viraldy.modules.deletion.policy import (
    DELETION_ORDER,
    RESOURCE_TABLES,
    TABLE_SUBJECT_ALIASES,
)
from viraldy.modules.deletion.storage_cleanup import extract_storage_keys
from viraldy.platform.clock.utc import utc_now
from viraldy.platform.database import models as _models  # noqa: F401
from viraldy.platform.database.base import Base
from viraldy.shared.errors.base import AppError, NotFoundError


@dataclass(slots=True)
class DeletionPlan:
    workspace_id: UUID
    resource_type: DeletionResourceType
    resource_id: UUID
    selected: dict[str, set[UUID]] = field(default_factory=dict)

    def add(self, table_name: str, values: set[UUID]) -> bool:
        if not values:
            return False
        current = self.selected.setdefault(table_name, set())
        before = len(current)
        current.update(values)
        return len(current) != before


class DeletionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._tables = Base.metadata.tables

    async def create_audit(
        self,
        workspace_id: UUID,
        resource_type: DeletionResourceType,
        resource_id: UUID,
        user_id: UUID,
    ) -> DeletionAuditRecordModel:
        record = DeletionAuditRecordModel(
            workspace_id=workspace_id,
            resource_type=resource_type.value,
            resource_id=resource_id,
            initiated_by_user_id=user_id,
            status="processing",
        )
        self._session.add(record)
        await self._session.commit()
        await self._session.refresh(record)
        return record

    async def build_plan(
        self,
        workspace_id: UUID,
        resource_type: DeletionResourceType,
        resource_id: UUID,
    ) -> DeletionPlan:
        root_name = RESOURCE_TABLES[resource_type]
        root = self._tables[root_name]
        conditions = [root.c.id == resource_id]
        if root_name == "workspaces":
            conditions.append(root.c.id == workspace_id)
        else:
            conditions.append(root.c.workspace_id == workspace_id)
        exists = await self._session.scalar(select(root.c.id).where(*conditions))
        if exists is None:
            raise NotFoundError(
                "DELETION_RESOURCE_NOT_FOUND",
                "Deletion resource was not found.",
            )
        plan = DeletionPlan(workspace_id, resource_type, resource_id)
        plan.add(root_name, {resource_id})
        for _ in range(len(self._tables) * 3):
            changed = await self._expand_fk_children(plan)
            changed = await self._promote_semantic_parents(plan) or changed
            changed = await self._promote_exclusively_owned_assets(plan) or changed
            changed = await self._include_subject_traces(plan) or changed
            changed = await self._promote_trace_parents(plan) or changed
            if not changed:
                return plan
        raise RuntimeError("deletion graph did not converge")

    async def storage_keys(self, plan: DeletionPlan) -> list[str]:
        keys: set[str] = set()
        for table_name, column_name in (
            ("asset_versions", "storage_key"),
            ("media_artifacts", "storage_key"),
            ("evidence_items", "frame_storage_key"),
            ("generation_artifacts", "storage_key"),
        ):
            ids = plan.selected.get(table_name)
            if not ids:
                continue
            table = self._tables[table_name]
            conditions = [
                table.c.id.in_(ids),
                *self._workspace_conditions(table, plan),
            ]
            values = await self._session.scalars(
                select(table.c[column_name]).where(*conditions)
            )
            keys.update(
                value
                for value in values
                if value and not str(value).startswith("fixtures/")
            )
        for table_name, column_name in (
            ("media_artifacts", "payload_json"),
            ("evidence_items", "value_json"),
        ):
            ids = plan.selected.get(table_name)
            if not ids:
                continue
            table = self._tables[table_name]
            conditions = [
                table.c.id.in_(ids),
                *self._workspace_conditions(table, plan),
            ]
            payloads = await self._session.scalars(
                select(table.c[column_name]).where(*conditions)
            )
            for payload in payloads:
                keys.update(extract_storage_keys(payload))
        return sorted(keys)

    async def execute_plan(self, plan: DeletionPlan) -> dict[str, int]:
        await self._null_current_version_cycles(plan)
        counts: dict[str, int] = {}
        for table_name in DELETION_ORDER:
            table = self._tables[table_name]
            ids = plan.selected.get(table_name)
            if ids and len(table.primary_key.columns) == 1:
                primary_key = next(iter(table.primary_key.columns))
                conditions = [
                    primary_key.in_(ids),
                    *self._workspace_conditions(table, plan),
                ]
                result = await self._session.execute(
                    delete(table).where(*conditions)
                )
                counts[table_name] = int(result.rowcount or 0)
            elif (
                table_name == "workspace_members"
                and "workspaces" in plan.selected
            ):
                result = await self._session.execute(
                    delete(table).where(table.c.workspace_id == plan.workspace_id)
                )
                counts[table_name] = int(result.rowcount or 0)
        return {name: count for name, count in counts.items() if count}

    async def mark_succeeded(
        self,
        record: DeletionAuditRecordModel,
        deleted_object_count: int,
        row_counts: dict[str, int],
    ) -> None:
        record.status = "succeeded"
        record.deleted_object_count = deleted_object_count
        record.deleted_row_counts_json = row_counts
        record.completed_at = utc_now()
        await self._session.commit()

    async def mark_storage_cleanup_pending(
        self,
        record: DeletionAuditRecordModel,
        row_counts: dict[str, int],
    ) -> None:
        record.status = "storage_cleanup_pending"
        record.deleted_row_counts_json = row_counts
        record.safe_error_code = None
        record.safe_error_message = None

    async def mark_failed(
        self,
        audit_id: UUID,
        code: str,
        message: str,
    ) -> None:
        record = await self._session.get(DeletionAuditRecordModel, audit_id)
        if record is None:
            return
        record.status = "failed"
        record.safe_error_code = code
        record.safe_error_message = message
        record.completed_at = utc_now()
        await self._session.commit()

    async def _expand_fk_children(self, plan: DeletionPlan) -> bool:
        changed = False
        for child in self._tables.values():
            primary_keys = list(child.primary_key.columns)
            if len(primary_keys) != 1 or child.name == "deletion_audit_records":
                continue
            child_pk = primary_keys[0]
            for column in child.columns:
                for foreign_key in column.foreign_keys:
                    parent_ids = plan.selected.get(foreign_key.column.table.name)
                    if not parent_ids:
                        continue
                    await self._assert_no_cross_workspace_child(
                        plan,
                        child,
                        child_pk,
                        column,
                        parent_ids,
                    )
                    conditions = [
                        column.in_(parent_ids),
                        *self._workspace_conditions(child, plan),
                    ]
                    values = set(
                        await self._session.scalars(
                            select(child_pk).where(*conditions)
                        )
                    )
                    changed = await self._add_scoped(plan, child.name, values) or changed
        return changed

    async def _promote_semantic_parents(self, plan: DeletionPlan) -> bool:
        changed = False
        changed = await self._promote_pattern_kits(plan) or changed
        changed = await self._promote_viral_kits(plan) or changed
        changed = await self._promote_campaign_packs(plan) or changed
        return changed

    async def _promote_pattern_kits(self, plan: DeletionPlan) -> bool:
        version_ids: set[UUID] = set()
        for table_name in ("pattern_kit_sources", "pattern_kit_evidence_links"):
            row_ids = plan.selected.get(table_name)
            if not row_ids:
                continue
            table = self._tables[table_name]
            version_ids.update(
                await self._session.scalars(
                    select(table.c.pattern_kit_version_id).where(table.c.id.in_(row_ids))
                )
            )
        if not version_ids:
            return False
        versions = self._tables["pattern_kit_versions"]
        kit_ids = set(
            await self._session.scalars(
                select(versions.c.pattern_kit_id).where(versions.c.id.in_(version_ids))
            )
        )
        return await self._add_scoped(plan, "pattern_kits", kit_ids)

    async def _promote_viral_kits(self, plan: DeletionPlan) -> bool:
        link_ids = plan.selected.get("viral_kit_pattern_links")
        if not link_ids:
            return False
        links = self._tables["viral_kit_pattern_links"]
        version_ids = set(
            await self._session.scalars(
                select(links.c.viral_kit_version_id).where(links.c.id.in_(link_ids))
            )
        )
        versions = self._tables["viral_kit_versions"]
        kit_ids = set(
            await self._session.scalars(
                select(versions.c.viral_kit_id).where(versions.c.id.in_(version_ids))
            )
        )
        return await self._add_scoped(plan, "viral_kits", kit_ids)

    async def _promote_campaign_packs(self, plan: DeletionPlan) -> bool:
        link_ids = plan.selected.get("viral_kit_campaign_pack_links")
        if not link_ids:
            return False
        links = self._tables["viral_kit_campaign_pack_links"]
        pack_ids = set(
            await self._session.scalars(
                select(links.c.campaign_pack_id).where(links.c.id.in_(link_ids))
            )
        )
        return await self._add_scoped(plan, "campaign_packs", pack_ids)

    async def _promote_exclusively_owned_assets(self, plan: DeletionPlan) -> bool:
        reference_ids = plan.selected.get("references")
        if not reference_ids:
            return False
        references = self._tables["references"]
        asset_ids = set(
            await self._session.scalars(
                select(references.c.asset_id).where(references.c.id.in_(reference_ids))
            )
        )
        owned_asset_ids: set[UUID] = set()
        for asset_id in asset_ids:
            other_reference = await self._session.scalar(
                select(references.c.id)
                .where(
                    references.c.workspace_id == plan.workspace_id,
                    references.c.asset_id == asset_id,
                    references.c.id.not_in(reference_ids),
                )
                .limit(1)
            )
            if other_reference is None:
                owned_asset_ids.add(asset_id)
        return await self._add_scoped(plan, "assets", owned_asset_ids)

    async def _include_subject_traces(self, plan: DeletionPlan) -> bool:
        changed = False
        for source_table, aliases in TABLE_SUBJECT_ALIASES.items():
            subject_ids = plan.selected.get(source_table)
            if not subject_ids:
                continue
            for trace_name in (
                "processing_jobs",
                "ai_model_runs",
                "feedback_items",
                "product_events",
                "recommendations",
            ):
                trace = self._tables[trace_name]
                if "subject_type" not in trace.c or "subject_id" not in trace.c:
                    continue
                trace_ids = set(
                    await self._session.scalars(
                        select(trace.c.id).where(
                            trace.c.workspace_id == plan.workspace_id,
                            trace.c.subject_type.in_(aliases),
                            trace.c.subject_id.in_(subject_ids),
                        )
                    )
                )
                changed = await self._add_scoped(plan, trace_name, trace_ids) or changed
        return changed

    async def _promote_trace_parents(self, plan: DeletionPlan) -> bool:
        changed = False
        reference_columns = {
            "processing_job_id": "processing_jobs",
            "primary_model_run_id": "ai_model_runs",
            "model_run_id": "ai_model_runs",
            "source_model_run_id": "ai_model_runs",
        }
        for table_name, row_ids in tuple(plan.selected.items()):
            table = self._tables[table_name]
            if not row_ids or len(table.primary_key.columns) != 1:
                continue
            primary_key = next(iter(table.primary_key.columns))
            for column_name, parent_table in reference_columns.items():
                if column_name not in table.c:
                    continue
                parent_ids = set(
                    value
                    for value in await self._session.scalars(
                        select(table.c[column_name]).where(primary_key.in_(row_ids))
                    )
                    if value is not None
                )
                changed = await self._add_scoped(plan, parent_table, parent_ids) or changed
        return changed

    async def _null_current_version_cycles(self, plan: DeletionPlan) -> None:
        await self._null_selected(plan, "assets", "current_version_id")
        await self._null_selected(plan, "campaign_packs", "current_version_id")

    async def _null_selected(
        self,
        plan: DeletionPlan,
        table_name: str,
        column_name: str,
    ) -> None:
        ids = plan.selected.get(table_name)
        if not ids:
            return
        table = self._tables[table_name]
        conditions = [
            table.c.id.in_(ids),
            *self._workspace_conditions(table, plan),
        ]
        await self._session.execute(
            update(table).where(*conditions).values({column_name: None})
        )

    async def _add_scoped(
        self,
        plan: DeletionPlan,
        table_name: str,
        values: set[UUID],
    ) -> bool:
        if not values:
            return False
        table = self._tables[table_name]
        primary_keys = list(table.primary_key.columns)
        if len(primary_keys) != 1:
            return False
        scoped_values = set(
            await self._session.scalars(
                select(primary_keys[0]).where(
                    primary_keys[0].in_(values),
                    *self._workspace_conditions(table, plan),
                )
            )
        )
        return plan.add(table_name, scoped_values)

    async def _assert_no_cross_workspace_child(
        self,
        plan: DeletionPlan,
        child: Table,
        child_pk: Column[Any],
        foreign_key_column: Column[Any],
        parent_ids: set[UUID],
    ) -> None:
        if "workspace_id" not in child.c:
            return
        mismatched = await self._session.scalar(
            select(child_pk)
            .where(
                foreign_key_column.in_(parent_ids),
                child.c.workspace_id != plan.workspace_id,
            )
            .limit(1)
        )
        if mismatched is not None:
            raise AppError(
                "DELETION_TENANT_GRAPH_CONFLICT",
                "Data deletion was blocked by an invalid tenant relationship.",
                status_code=409,
            )

    @staticmethod
    def _workspace_conditions(
        table: Table,
        plan: DeletionPlan,
    ) -> list[ColumnElement[bool]]:
        if "workspace_id" in table.c:
            return [table.c.workspace_id == plan.workspace_id]
        if table.name == "workspaces":
            return [table.c.id == plan.workspace_id]
        return []
