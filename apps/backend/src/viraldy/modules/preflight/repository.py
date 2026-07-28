from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from viraldy.modules.preflight.models import PreflightRunModel

PREFLIGHT_RUBRIC_VERSION = "ugc_preflight_rubric_v1"
PREFLIGHT_RULE_VERSION = "ugc_preflight_rules_v1"


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
    ) -> PreflightRunModel:
        run.status = "completed"
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
        run.model_version = model_version
        self._session.flush()
        return run
