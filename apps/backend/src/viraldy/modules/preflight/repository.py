from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from viraldy.modules.creative_domain.schema_versions import (
    PREFLIGHT_RUBRIC_VERSION,
    PREFLIGHT_RULE_VERSION,
    PREFLIGHT_SCHEMA_VERSION,
)
from viraldy.modules.preflight.models import PreflightRunModel


class PreflightRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_pending(
        self,
        workspace_id: UUID,
        ugc_asset_version_id: UUID,
        campaign_pack_version_id: UUID,
        analysis_mode: str,
    ) -> PreflightRunModel:
        run = PreflightRunModel(
            workspace_id=workspace_id,
            ugc_asset_version_id=ugc_asset_version_id,
            campaign_pack_version_id=campaign_pack_version_id,
            status="queued",
            schema_version=PREFLIGHT_SCHEMA_VERSION,
            analysis_mode=analysis_mode,
            rubric_version=PREFLIGHT_RUBRIC_VERSION,
            rule_version=PREFLIGHT_RULE_VERSION,
        )
        self._session.add(run)
        await self._session.flush()
        return run

    async def get(self, workspace_id: UUID, preflight_run_id: UUID) -> PreflightRunModel | None:
        result = await self._session.execute(
            select(PreflightRunModel).where(
                PreflightRunModel.workspace_id == workspace_id,
                PreflightRunModel.id == preflight_run_id,
            )
        )
        return result.scalar_one_or_none()


class SyncPreflightRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, workspace_id: UUID, preflight_run_id: UUID) -> PreflightRunModel | None:
        return self._session.execute(
            select(PreflightRunModel).where(
                PreflightRunModel.workspace_id == workspace_id,
                PreflightRunModel.id == preflight_run_id,
            )
        ).scalar_one_or_none()

    def complete(
        self,
        run: PreflightRunModel,
        result: dict[str, Any],
        structural_score_run_id: UUID | None,
        model_version: str | None,
        product_snapshot_json: dict[str, object] | None,
        product_context_schema_version: str | None,
        requirements_snapshot_json: dict[str, object] | None,
    ) -> PreflightRunModel:
        run.status = "completed"
        run.schema_version = PREFLIGHT_SCHEMA_VERSION
        run.structural_score_run_id = structural_score_run_id
        run.structural_score = Decimal(str(result["structural_score"]))
        run.brief_alignment_score = Decimal(str(result["brief_alignment_score"]))
        run.preflight_score = Decimal(str(result["preflight_score"]))
        run.confidence = str(result["confidence"])
        run.action_label = str(result["action"])
        run.dimension_scores_json = result["dimensions"]
        run.brief_alignment_json = result["brief_alignment"]
        run.strengths_json = result["strengths"]
        run.blockers_json = result["blockers"]
        run.fixes_json = result["fixes"]
        run.revision_message = str(result["revision_message"])
        run.evidence_ids_json = result["evidence_ids"]
        run.product_snapshot_json = product_snapshot_json
        run.product_context_schema_version = product_context_schema_version
        run.requirements_snapshot_json = requirements_snapshot_json
        run.model_version = model_version
        self._session.flush()
        return run
