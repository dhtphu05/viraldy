from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, cast
from uuid import UUID

from sqlalchemy import case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from viraldy.modules.assets.public import AssetVersionModel
from viraldy.modules.creative_domain.schema_versions import TIKTOK_SCORE_SCHEMA_VERSION
from viraldy.modules.product_events.public import SyncProductEventPublisher
from viraldy.modules.tiktok_scorer.models import (
    TikTokFixActionEventModel,
    TikTokFixActionModel,
    TikTokScoreComparisonModel,
    TikTokScoreDimensionModel,
    TikTokScoreFindingModel,
    TikTokScoreProfileModel,
    TikTokScoreRunModel,
)
from viraldy.modules.tiktok_scorer.rubric import TIKTOK_STRUCTURE_RUBRIC
from viraldy.platform.clock.utc import utc_now
from viraldy.shared.errors.base import AppError

RUBRIC_VERSION = TIKTOK_STRUCTURE_RUBRIC.version
RULE_VERSION = TIKTOK_STRUCTURE_RUBRIC.rule_version


@dataclass(frozen=True, slots=True)
class TikTokScoreListFilters:
    status: str | None = None
    score_mode: str | None = None
    score_profile: str | None = None
    product_id: UUID | None = None
    intended_use: str | None = None
    decision: str | None = None
    created_from: datetime | None = None
    created_to: datetime | None = None
    search: str | None = None
    sort: str = "created_at_desc"
    limit: int = 50
    offset: int = 0


@dataclass(frozen=True, slots=True)
class TikTokScoreListRow:
    run: TikTokScoreRunModel
    asset_filename: str
    revision_count: int


@dataclass(frozen=True, slots=True)
class TikTokScoreLineageMetadata:
    revision_count: int
    comparison_ids: list[UUID]


class TikTokScoreRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_pending(
        self,
        *,
        workspace_id: UUID,
        asset_id: UUID,
        asset_version_id: UUID,
        analysis_mode: str,
        product_id: UUID | None,
        score_mode: str,
        intended_use: str,
        score_profile: str,
        score_profile_version: int,
        score_profile_id: UUID | None,
        profile_selection_mode: str,
        profile_selection_confidence: float | None,
        alternative_profiles: list[str],
        profile_evidence_ids: list[UUID],
        product_context_snapshot: dict[str, object] | None,
        product_context_snapshot_hash: str | None,
        product_context_schema_version: str | None,
        product_context_version: int | None,
        media_checksum_sha256: str | None,
        creative_direction_context_id: UUID | None,
        creative_direction_context_snapshot: dict[str, object] | None,
        creative_direction_context_version: int | None,
        creative_direction_lookup_error: str | None,
        idempotency_key: str | None,
        parent_score_run_id: UUID | None = None,
        profile_override_reason: str | None = None,
        policy_pack_versions: dict[str, object] | None = None,
        rule_versions: dict[str, object] | None = None,
        prompt_versions: dict[str, object] | None = None,
        model_provider_versions: dict[str, object] | None = None,
    ) -> TikTokScoreRunModel:
        run = TikTokScoreRunModel(
            workspace_id=workspace_id,
            asset_id=asset_id,
            asset_version_id=asset_version_id,
            product_id=product_id,
            parent_score_run_id=parent_score_run_id,
            status="queued",
            current_stage="queued",
            schema_version=TIKTOK_SCORE_SCHEMA_VERSION,
            idempotency_key=idempotency_key,
            score_mode=score_mode,
            intended_use=intended_use,
            score_profile=score_profile,
            score_profile_version=score_profile_version,
            score_profile_id=score_profile_id,
            profile_selection_mode=profile_selection_mode,
            profile_selection_confidence=(
                Decimal(str(profile_selection_confidence))
                if profile_selection_confidence is not None
                else None
            ),
            alternative_profiles_json=alternative_profiles,
            profile_evidence_ids_json=[str(value) for value in profile_evidence_ids],
            profile_override_reason=profile_override_reason,
            product_context_snapshot_json=product_context_snapshot,
            product_context_snapshot_hash=product_context_snapshot_hash,
            product_context_schema_version=product_context_schema_version,
            product_context_version=product_context_version,
            policy_pack_versions_json=policy_pack_versions or {},
            rule_versions_json=rule_versions or {"legacy_rule_version": RULE_VERSION},
            prompt_versions_json=prompt_versions or {},
            model_provider_versions_json=model_provider_versions or {},
            media_checksum_sha256=media_checksum_sha256,
            creative_direction_context_id=creative_direction_context_id,
            creative_direction_context_snapshot_json=creative_direction_context_snapshot,
            creative_direction_context_version=creative_direction_context_version,
            creative_direction_lookup_error=creative_direction_lookup_error,
            analysis_mode=analysis_mode,
            rubric_version=RUBRIC_VERSION,
            rule_version=RULE_VERSION,
        )
        self._session.add(run)
        await self._session.flush()
        return run

    async def attach_job(
        self,
        run: TikTokScoreRunModel,
        processing_job_id: UUID,
        stage: str | None,
    ) -> None:
        run.processing_job_id = processing_job_id
        run.current_stage = stage or "queued"
        await self._session.flush()

    async def get(self, workspace_id: UUID, score_run_id: UUID) -> TikTokScoreRunModel | None:
        result = await self._session.execute(
            select(TikTokScoreRunModel).where(
                TikTokScoreRunModel.workspace_id == workspace_id,
                TikTokScoreRunModel.id == score_run_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_idempotency_key(
        self,
        workspace_id: UUID,
        idempotency_key: str | None,
    ) -> TikTokScoreRunModel | None:
        if not idempotency_key:
            return None
        return cast(
            TikTokScoreRunModel | None,
            await self._session.scalar(
                select(TikTokScoreRunModel).where(
                    TikTokScoreRunModel.workspace_id == workspace_id,
                    TikTokScoreRunModel.idempotency_key == idempotency_key,
                )
            ),
        )

    async def list_runs(
        self,
        workspace_id: UUID,
        filters: TikTokScoreListFilters,
    ) -> tuple[list[TikTokScoreListRow], int]:
        revision_counts = (
            select(
                TikTokScoreRunModel.parent_score_run_id.label("parent_id"),
                func.count(TikTokScoreRunModel.id).label("revision_count"),
            )
            .where(
                TikTokScoreRunModel.workspace_id == workspace_id,
                TikTokScoreRunModel.parent_score_run_id.is_not(None),
            )
            .group_by(TikTokScoreRunModel.parent_score_run_id)
            .subquery()
        )
        conditions = self._filter_conditions(workspace_id, filters)
        statement = (
            select(
                TikTokScoreRunModel,
                AssetVersionModel.original_filename,
                func.coalesce(revision_counts.c.revision_count, 0),
            )
            .join(AssetVersionModel, AssetVersionModel.id == TikTokScoreRunModel.asset_version_id)
            .outerjoin(revision_counts, revision_counts.c.parent_id == TikTokScoreRunModel.id)
            .where(*conditions)
            .order_by(self._sort_expression(filters.sort))
            .limit(filters.limit)
            .offset(filters.offset)
        )
        result = await self._session.execute(statement)
        rows = [
            TikTokScoreListRow(
                run=row[0],
                asset_filename=str(row[1]),
                revision_count=int(row[2]),
            )
            for row in result.all()
        ]
        total_result = await self._session.execute(
            select(func.count())
            .select_from(TikTokScoreRunModel)
            .join(
                AssetVersionModel,
                AssetVersionModel.id == TikTokScoreRunModel.asset_version_id,
            )
            .where(*conditions)
        )
        total = int(total_result.scalar_one())
        return rows, total

    def _filter_conditions(
        self,
        workspace_id: UUID,
        filters: TikTokScoreListFilters,
    ) -> list[ColumnElement[bool]]:
        conditions: list[ColumnElement[bool]] = [TikTokScoreRunModel.workspace_id == workspace_id]
        mappings = (
            (TikTokScoreRunModel.score_mode, filters.score_mode),
            (TikTokScoreRunModel.score_profile, filters.score_profile),
            (TikTokScoreRunModel.product_id, filters.product_id),
            (TikTokScoreRunModel.intended_use, filters.intended_use),
            (TikTokScoreRunModel.creative_structure_decision, filters.decision),
        )
        conditions.extend(column == value for column, value in mappings if value is not None)
        if filters.status == "partial_evidence":
            partial_coverage = ("partial", "insufficient")
            inventory_coverage = func.jsonb_extract_path_text(
                TikTokScoreRunModel.scene_inventory_json,
                "coverage_status",
            )
            result_coverage = func.jsonb_extract_path_text(
                TikTokScoreRunModel.result_json,
                "scene_inventory",
                "coverage_status",
            )
            conditions.extend(
                (
                    TikTokScoreRunModel.status == "completed",
                    or_(
                        inventory_coverage.in_(partial_coverage),
                        result_coverage.in_(partial_coverage),
                    ),
                )
            )
        elif filters.status is not None:
            conditions.append(TikTokScoreRunModel.status == filters.status)
        if filters.created_from is not None:
            conditions.append(TikTokScoreRunModel.created_at >= filters.created_from)
        if filters.created_to is not None:
            conditions.append(TikTokScoreRunModel.created_at <= filters.created_to)
        if filters.search:
            pattern = f"%{filters.search}%"
            product_name = func.jsonb_extract_path_text(
                TikTokScoreRunModel.product_context_snapshot_json,
                "product_context",
                "identity",
                "name",
            )
            conditions.append(
                or_(
                    AssetVersionModel.original_filename.ilike(pattern),
                    product_name.ilike(pattern),
                )
            )
        return conditions

    async def get_lineage_metadata(
        self,
        workspace_id: UUID,
        score_run_id: UUID,
    ) -> TikTokScoreLineageMetadata:
        revision_count = await self._session.scalar(
            select(func.count(TikTokScoreRunModel.id)).where(
                TikTokScoreRunModel.workspace_id == workspace_id,
                TikTokScoreRunModel.parent_score_run_id == score_run_id,
            )
        )
        comparison_ids = await self._session.scalars(
            select(TikTokScoreComparisonModel.id)
            .where(
                TikTokScoreComparisonModel.workspace_id == workspace_id,
                or_(
                    TikTokScoreComparisonModel.before_score_run_id == score_run_id,
                    TikTokScoreComparisonModel.after_score_run_id == score_run_id,
                ),
            )
            .order_by(
                TikTokScoreComparisonModel.created_at,
                TikTokScoreComparisonModel.id,
            )
        )
        return TikTokScoreLineageMetadata(
            revision_count=int(revision_count or 0),
            comparison_ids=list(comparison_ids),
        )

    def _sort_expression(self, sort: str) -> ColumnElement[Any]:
        sort_expressions: dict[str, ColumnElement[Any]] = {
            "created_at_asc": TikTokScoreRunModel.created_at.asc(),
            "created_at_desc": TikTokScoreRunModel.created_at.desc(),
            "updated_at_asc": TikTokScoreRunModel.updated_at.asc(),
            "updated_at_desc": TikTokScoreRunModel.updated_at.desc(),
            "score_asc": TikTokScoreRunModel.structural_score.asc().nulls_last(),
            "score_desc": TikTokScoreRunModel.structural_score.desc().nulls_last(),
        }
        return sort_expressions.get(sort, TikTokScoreRunModel.created_at.desc())

    async def list_dimensions(
        self,
        workspace_id: UUID,
        score_run_id: UUID,
    ) -> list[TikTokScoreDimensionModel]:
        result = await self._session.scalars(
            select(TikTokScoreDimensionModel)
            .where(
                TikTokScoreDimensionModel.workspace_id == workspace_id,
                TikTokScoreDimensionModel.score_run_id == score_run_id,
            )
            .order_by(TikTokScoreDimensionModel.created_at, TikTokScoreDimensionModel.code)
        )
        return list(result)

    async def list_findings(
        self,
        workspace_id: UUID,
        score_run_id: UUID,
    ) -> list[TikTokScoreFindingModel]:
        result = await self._session.scalars(
            select(TikTokScoreFindingModel)
            .where(
                TikTokScoreFindingModel.workspace_id == workspace_id,
                TikTokScoreFindingModel.score_run_id == score_run_id,
            )
            .order_by(
                case(
                    (TikTokScoreFindingModel.priority == "P0", 0),
                    (TikTokScoreFindingModel.priority == "P1", 1),
                    (TikTokScoreFindingModel.priority == "P2", 2),
                    else_=3,
                ),
                TikTokScoreFindingModel.created_at,
            )
        )
        return list(result)

    async def list_fix_actions(
        self,
        workspace_id: UUID,
        score_run_id: UUID,
    ) -> list[TikTokFixActionModel]:
        result = await self._session.scalars(
            select(TikTokFixActionModel)
            .where(
                TikTokFixActionModel.workspace_id == workspace_id,
                TikTokFixActionModel.score_run_id == score_run_id,
            )
            .order_by(
                case(
                    (TikTokFixActionModel.priority == "P0", 0),
                    (TikTokFixActionModel.priority == "P1", 1),
                    else_=2,
                ),
                TikTokFixActionModel.created_at,
            )
        )
        return list(result)

    async def get_fix_action(
        self,
        workspace_id: UUID,
        score_run_id: UUID,
        fix_action_id: UUID,
    ) -> TikTokFixActionModel | None:
        return cast(
            TikTokFixActionModel | None,
            await self._session.scalar(
                select(TikTokFixActionModel).where(
                    TikTokFixActionModel.workspace_id == workspace_id,
                    TikTokFixActionModel.score_run_id == score_run_id,
                    TikTokFixActionModel.id == fix_action_id,
                )
            ),
        )

    async def count_fix_actions(
        self,
        workspace_id: UUID,
        score_run_id: UUID,
        fix_action_ids: list[UUID],
    ) -> int:
        if not fix_action_ids:
            return 0
        return int(
            await self._session.scalar(
                select(func.count())
                .select_from(TikTokFixActionModel)
                .where(
                    TikTokFixActionModel.workspace_id == workspace_id,
                    TikTokFixActionModel.score_run_id == score_run_id,
                    TikTokFixActionModel.id.in_(fix_action_ids),
                )
            )
            or 0
        )

    async def record_fix_action_event(
        self,
        *,
        fix_action: TikTokFixActionModel,
        actor_user_id: UUID | None,
        event_type: str,
        details_json: dict[str, object],
        idempotency_key: str | None,
    ) -> TikTokFixActionEventModel:
        if idempotency_key:
            existing = await self._session.scalar(
                select(TikTokFixActionEventModel).where(
                    TikTokFixActionEventModel.workspace_id == fix_action.workspace_id,
                    TikTokFixActionEventModel.fix_action_id == fix_action.id,
                    TikTokFixActionEventModel.idempotency_key == idempotency_key,
                )
            )
            if existing is not None:
                return existing
        event = TikTokFixActionEventModel(
            workspace_id=fix_action.workspace_id,
            score_run_id=fix_action.score_run_id,
            fix_action_id=fix_action.id,
            actor_user_id=actor_user_id,
            event_type=event_type,
            idempotency_key=idempotency_key,
            details_json=details_json,
        )
        self._session.add(event)
        if event_type != "viewed":
            fix_action.current_action_state = event_type
        await self._session.flush()
        return event

    async def list_profiles(self, workspace_id: UUID) -> list[TikTokScoreProfileModel]:
        result = await self._session.scalars(
            select(TikTokScoreProfileModel)
            .where(
                or_(
                    TikTokScoreProfileModel.workspace_id == workspace_id,
                    TikTokScoreProfileModel.workspace_id.is_(None),
                ),
                TikTokScoreProfileModel.is_active.is_(True),
            )
            .order_by(
                case((TikTokScoreProfileModel.workspace_id == workspace_id, 0), else_=1),
                TikTokScoreProfileModel.code,
                TikTokScoreProfileModel.profile_version.desc(),
            )
        )
        return list(result)

    async def get_profile(
        self,
        workspace_id: UUID,
        code: str,
    ) -> TikTokScoreProfileModel | None:
        return cast(
            TikTokScoreProfileModel | None,
            await self._session.scalar(
                select(TikTokScoreProfileModel)
                .where(
                    or_(
                        TikTokScoreProfileModel.workspace_id == workspace_id,
                        TikTokScoreProfileModel.workspace_id.is_(None),
                    ),
                    TikTokScoreProfileModel.code == code,
                    TikTokScoreProfileModel.is_active.is_(True),
                )
                .order_by(
                    case((TikTokScoreProfileModel.workspace_id == workspace_id, 0), else_=1),
                    TikTokScoreProfileModel.profile_version.desc(),
                )
                .limit(1)
            ),
        )

    async def create_pending_comparison(
        self,
        *,
        workspace_id: UUID,
        before_score_run_id: UUID,
        after_score_run_id: UUID,
        accepted_fix_action_ids: list[UUID],
    ) -> TikTokScoreComparisonModel:
        comparison = TikTokScoreComparisonModel(
            workspace_id=workspace_id,
            before_score_run_id=before_score_run_id,
            after_score_run_id=after_score_run_id,
            status="pending",
            accepted_fix_action_ids_json=[str(value) for value in accepted_fix_action_ids],
        )
        self._session.add(comparison)
        await self._session.flush()
        return comparison

    async def get_comparison(
        self,
        workspace_id: UUID,
        score_run_id: UUID,
        comparison_id: UUID,
    ) -> TikTokScoreComparisonModel | None:
        return cast(
            TikTokScoreComparisonModel | None,
            await self._session.scalar(
                select(TikTokScoreComparisonModel).where(
                    TikTokScoreComparisonModel.workspace_id == workspace_id,
                    TikTokScoreComparisonModel.before_score_run_id == score_run_id,
                    TikTokScoreComparisonModel.id == comparison_id,
                )
            ),
        )

    async def get_comparison_for_pair(
        self,
        workspace_id: UUID,
        before_score_run_id: UUID,
        after_score_run_id: UUID,
    ) -> TikTokScoreComparisonModel | None:
        return cast(
            TikTokScoreComparisonModel | None,
            await self._session.scalar(
                select(TikTokScoreComparisonModel).where(
                    TikTokScoreComparisonModel.workspace_id == workspace_id,
                    TikTokScoreComparisonModel.before_score_run_id == before_score_run_id,
                    TikTokScoreComparisonModel.after_score_run_id == after_score_run_id,
                )
            ),
        )


class SyncTikTokScoreRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, workspace_id: UUID, score_run_id: UUID) -> TikTokScoreRunModel | None:
        return self._session.execute(
            select(TikTokScoreRunModel).where(
                TikTokScoreRunModel.workspace_id == workspace_id,
                TikTokScoreRunModel.id == score_run_id,
            )
        ).scalar_one_or_none()

    def load_run_with_snapshots(
        self,
        workspace_id: UUID,
        score_run_id: UUID,
    ) -> TikTokScoreRunModel | None:
        return self.get(workspace_id, score_run_id)

    def update_stage(
        self,
        run: TikTokScoreRunModel,
        stage: str,
        processing_job_id: UUID | None = None,
    ) -> TikTokScoreRunModel:
        self._assert_mutable(run)
        run.status = "processing"
        run.current_stage = stage
        if processing_job_id is not None:
            run.processing_job_id = processing_job_id
        self._session.flush()
        return run

    def mark_failed(
        self,
        run: TikTokScoreRunModel,
        failure_code: str,
        *,
        processing_job_id: UUID | None = None,
    ) -> TikTokScoreRunModel:
        self._assert_mutable(run)
        run.status = "failed"
        run.current_stage = "failed"
        run.failure_code = failure_code
        run.completed_at = utc_now()
        if processing_job_id is not None:
            run.processing_job_id = processing_job_id
        self._session.flush()
        return run

    def complete(
        self,
        run: TikTokScoreRunModel,
        creative_dna_version_id: UUID | None,
        result: dict[str, Any],
        model_version: str | None,
    ) -> TikTokScoreRunModel:
        self._assert_mutable(run)
        run.status = "completed"
        run.current_stage = "completed"
        run.completed_at = utc_now()
        run.schema_version = str(result.get("schema_version") or TIKTOK_SCORE_SCHEMA_VERSION)
        run.creative_dna_version_id = creative_dna_version_id
        raw_score = result.get("overall_score", result.get("structural_score"))
        run.structural_score = Decimal(str(raw_score)) if raw_score is not None else None
        run.confidence = str(result.get("overall_confidence", result.get("confidence", "low")))
        run.action_label = str(
            result.get("creative_structure_decision", result.get("action", "pending"))
        )
        run.creative_structure_decision = run.action_label
        dimensions = result.get("dimensions", {})
        run.dimension_scores_json = (
            dimensions
            if isinstance(dimensions, dict)
            else {str(item.get("code")): item for item in dimensions if isinstance(item, dict)}
        )
        run.strengths_json = list(result.get("strengths", []))
        run.blockers_json = list(result.get("blockers", result.get("findings", [])))
        run.fixes_json = list(result.get("fixes", result.get("required_fixes", [])))
        run.evidence_ids_json = list(result.get("evidence_ids", []))
        run.model_version = model_version
        self._session.flush()
        return run

    def persist_v2_result(
        self,
        run: TikTokScoreRunModel,
        result: dict[str, Any],
        *,
        processing_job_id: UUID | None = None,
        primary_model_run_id: UUID | None = None,
        model_version: str | None = None,
        prompt_versions: dict[str, object] | None = None,
        model_provider_versions: dict[str, object] | None = None,
        latency_ms: int | None = None,
        token_usage: dict[str, object] | None = None,
        cost_estimate: Decimal | None = None,
    ) -> TikTokScoreRunModel:
        self.complete(run, None, result, model_version)
        run.processing_job_id = processing_job_id
        run.primary_model_run_id = primary_model_run_id
        run.prompt_versions_json = prompt_versions or run.prompt_versions_json
        run.model_provider_versions_json = (
            model_provider_versions or run.model_provider_versions_json
        )
        run.latency_ms = latency_ms
        run.token_usage_json = token_usage or {}
        run.cost_estimate = cost_estimate
        run.paid_use_rights_status = str(result.get("paid_use_rights_status", "not_evaluated"))
        run.final_paid_readiness = str(result.get("final_paid_readiness", "not_evaluated"))
        run.scene_inventory_json = _dict_or_none(result.get("scene_inventory"))
        run.auxiliary_signals_json = _dict_or_none(result.get("auxiliary_signals"))
        run.creative_upgrades_json = list(result.get("optional_upgrades", []))
        run.result_json = result
        run.policy_pack_versions_json = dict(
            result.get("policy_pack_versions", run.policy_pack_versions_json)
        )
        dimensions = _dict_list(result.get("dimensions", []))
        findings = _dict_list(result.get("findings", []))
        fixes = _dict_list(result.get("required_fixes", result.get("fixes", [])))
        finding_ids: dict[str, UUID] = {}
        for dimension in dimensions:
            self._session.add(_dimension_model(run, dimension))
        for finding in findings:
            model = _finding_model(run, finding)
            finding_ids[str(finding.get("id"))] = model.id
            self._session.add(model)
        self._session.flush()
        for fix in fixes:
            source_id = finding_ids.get(str(fix.get("source_finding_id")))
            self._session.add(_fix_action_model(run, fix, source_id))
        self._session.flush()
        return run

    def persist_comparison_result(
        self,
        comparison: TikTokScoreComparisonModel,
        result: dict[str, Any],
    ) -> TikTokScoreComparisonModel:
        if comparison.status == "completed":
            raise AppError(
                "TIKTOK_COMPARISON_IMMUTABLE",
                "Completed comparisons cannot be overwritten.",
                status_code=409,
            )
        comparison.status = "completed"
        comparison.completed_at = utc_now()
        comparison.resolved_blockers_json = list(result.get("resolved_blockers", []))
        comparison.unresolved_blockers_json = list(result.get("unresolved_blockers", []))
        comparison.new_regressions_json = list(result.get("new_regressions", []))
        comparison.dimension_changes_json = list(result.get("dimension_changes", []))
        comparison.evidence_before_after_json = list(result.get("evidence_before_after", []))
        comparison.strengths_preserved_json = list(result.get("strengths_preserved", []))
        comparison.actions_verified_json = list(result.get("actions_verified", []))
        comparison.final_next_action = str(result.get("final_next_action") or "") or None
        comparison.comparison_json = result
        self._session.flush()
        return comparison

    def record_verified_action_event(
        self,
        comparison: TikTokScoreComparisonModel,
        fix_action_id: UUID,
        *,
        actor_user_id: UUID | None,
        details_json: dict[str, object] | None = None,
        idempotency_key: str | None = None,
    ) -> TikTokFixActionEventModel:
        action = self._session.execute(
            select(TikTokFixActionModel).where(
                TikTokFixActionModel.workspace_id == comparison.workspace_id,
                TikTokFixActionModel.score_run_id == comparison.before_score_run_id,
                TikTokFixActionModel.id == fix_action_id,
            )
        ).scalar_one_or_none()
        if action is None:
            raise AppError(
                "TIKTOK_FIX_ACTION_NOT_FOUND",
                "Verified action does not belong to the comparison's parent score run.",
                status_code=404,
            )
        effective_key = idempotency_key or f"{comparison.id}:verified:{fix_action_id}"
        existing = self._session.execute(
            select(TikTokFixActionEventModel).where(
                TikTokFixActionEventModel.workspace_id == comparison.workspace_id,
                TikTokFixActionEventModel.fix_action_id == fix_action_id,
                TikTokFixActionEventModel.idempotency_key == effective_key,
            )
        ).scalar_one_or_none()
        if existing is not None:
            return existing
        event = TikTokFixActionEventModel(
            workspace_id=comparison.workspace_id,
            score_run_id=comparison.before_score_run_id,
            fix_action_id=fix_action_id,
            actor_user_id=actor_user_id,
            event_type="verified_after_revision",
            idempotency_key=effective_key,
            details_json={
                "comparison_id": str(comparison.id),
                "after_score_run_id": str(comparison.after_score_run_id),
                **(details_json or {}),
            },
        )
        action.current_action_state = "verified_after_revision"
        self._session.add(event)
        SyncProductEventPublisher(self._session).record(
            event_type="tiktok_action_verified_after_revision",
            workspace_id=comparison.workspace_id,
            actor_user_id=actor_user_id,
            subject_type="tiktok_score_run",
            subject_id=comparison.after_score_run_id,
            payload_json={
                "score_run_id": str(comparison.after_score_run_id),
                "parent_score_run_id": str(comparison.before_score_run_id),
                "comparison_id": str(comparison.id),
                "fix_action_id": str(fix_action_id),
            },
        )
        self._session.flush()
        return event

    def load_comparison(
        self,
        workspace_id: UUID,
        comparison_id: UUID,
    ) -> TikTokScoreComparisonModel | None:
        return self._session.execute(
            select(TikTokScoreComparisonModel).where(
                TikTokScoreComparisonModel.workspace_id == workspace_id,
                TikTokScoreComparisonModel.id == comparison_id,
            )
        ).scalar_one_or_none()

    def load_result_payload(
        self,
        workspace_id: UUID,
        score_run_id: UUID,
    ) -> dict[str, object] | None:
        run = self.get(workspace_id, score_run_id)
        if run is None or run.result_json is None:
            return None
        return dict(run.result_json)

    def _assert_mutable(self, run: TikTokScoreRunModel) -> None:
        if run.status == "completed":
            raise AppError(
                "TIKTOK_SCORE_RUN_IMMUTABLE",
                "Completed TikTok score runs cannot be overwritten.",
                status_code=409,
            )


def _dict_list(value: object) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        return [item for item in value.values() if isinstance(item, dict)]
    return []


def _dict_or_none(value: object) -> dict[str, object] | None:
    return value if isinstance(value, dict) else None


def _dimension_model(
    run: TikTokScoreRunModel,
    value: dict[str, Any],
) -> TikTokScoreDimensionModel:
    return TikTokScoreDimensionModel(
        workspace_id=run.workspace_id,
        score_run_id=run.id,
        code=str(value["code"]),
        label=str(value.get("label") or value["code"]),
        score=value.get("score"),
        applicability=str(value.get("applicability", "unknown")),
        evidence_status=str(value.get("evidence_status", "insufficient")),
        confidence=str(value.get("confidence", "low")),
        reason=str(value.get("reason") or "No reason provided."),
        positive_signals_json=list(value.get("positive_signals", [])),
        missing_signals_json=list(value.get("missing_signals", [])),
        uncertainty_json=list(value.get("uncertainty", [])),
        evidence_ids_json=list(value.get("evidence_ids", [])),
        contributing_rule_codes_json=list(value.get("contributing_rule_codes", [])),
        result_json=value,
    )


def _finding_model(
    run: TikTokScoreRunModel,
    value: dict[str, Any],
) -> TikTokScoreFindingModel:
    finding_id = UUID(str(value["id"]))
    return TikTokScoreFindingModel(
        id=finding_id,
        workspace_id=run.workspace_id,
        score_run_id=run.id,
        code=str(value["code"]),
        rule_code=str(value["rule_code"]),
        rule_class=str(value["rule_class"]),
        source_dimension=str(value["source_dimension"]),
        severity=str(value["severity"]),
        priority=str(value["priority"]),
        applicability=str(value["applicability"]),
        evidence_status=str(value["evidence_status"]),
        title=str(value["title"]),
        reason=str(value["reason"]),
        expected_json=dict(value.get("expected", {})),
        observed_json=dict(value.get("observed", {})),
        target_time_range_ms_json=value.get("target_time_range_ms"),
        evidence_ids_json=list(value.get("evidence_ids", [])),
        uncertainty_json=list(value.get("uncertainty", [])),
        requires_seller_truth=bool(value.get("requires_seller_truth", False)),
        can_be_resolved_by_edit=value.get("can_be_resolved_by_edit"),
        requires_physical_reshoot=value.get("requires_physical_reshoot"),
        finding_json=value,
    )


def _fix_action_model(
    run: TikTokScoreRunModel,
    value: dict[str, Any],
    finding_id: UUID | None,
) -> TikTokFixActionModel:
    return TikTokFixActionModel(
        id=UUID(str(value["id"])),
        workspace_id=run.workspace_id,
        score_run_id=run.id,
        finding_id=finding_id,
        code=str(value["code"]),
        recommendation_class=str(value["recommendation_class"]),
        basis=str(value["basis"]),
        priority=str(value["priority"]),
        severity=str(value["severity"]),
        source_dimension=str(value["source_dimension"]),
        owner_role=str(value["owner_role"]),
        fix_type=str(value["fix_type"]),
        title=str(value["title"]),
        why_it_matters=str(value["why_it_matters"]),
        expected_json=dict(value.get("expected", {})),
        observed_json=dict(value.get("observed", {})),
        evidence_ids_json=list(value.get("evidence_ids", [])),
        target_time_range_ms_json=value.get("target_time_range_ms"),
        video_operations_json=list(value.get("video_operations", [])),
        instructions_json=list(value.get("instructions", [])),
        strengths_to_preserve_json=list(value.get("strengths_to_preserve", [])),
        required_inputs_json=list(value.get("required_inputs", [])),
        estimated_effort=str(value["estimated_effort"]),
        reshoot_required=bool(value.get("reshoot_required", False)),
        completion_criteria_json=list(value.get("completion_criteria", [])),
        verification_method=str(value["verification_method"]),
        action_json=value,
    )
