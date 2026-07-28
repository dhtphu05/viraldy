from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from viraldy.modules.tiktok_scorer.models import TikTokScoreRunModel

RUBRIC_VERSION = "tiktok_structure_rubric_v1"
RULE_VERSION = "tiktok_structure_rules_v1"


class TikTokScoreRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_pending(
        self,
        workspace_id: UUID,
        asset_version_id: UUID,
        analysis_mode: str,
    ) -> TikTokScoreRunModel:
        run = TikTokScoreRunModel(
            workspace_id=workspace_id,
            asset_version_id=asset_version_id,
            status="queued",
            analysis_mode=analysis_mode,
            rubric_version=RUBRIC_VERSION,
            rule_version=RULE_VERSION,
        )
        self._session.add(run)
        await self._session.flush()
        return run

    async def get(self, workspace_id: UUID, score_run_id: UUID) -> TikTokScoreRunModel | None:
        result = await self._session.execute(
            select(TikTokScoreRunModel).where(
                TikTokScoreRunModel.workspace_id == workspace_id,
                TikTokScoreRunModel.id == score_run_id,
            )
        )
        return result.scalar_one_or_none()


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

    def complete(
        self,
        run: TikTokScoreRunModel,
        creative_dna_version_id: UUID | None,
        result: dict[str, Any],
        model_version: str | None,
    ) -> TikTokScoreRunModel:
        run.status = "completed"
        run.creative_dna_version_id = creative_dna_version_id
        run.structural_score = Decimal(str(result["structural_score"]))
        run.confidence = str(result["confidence"])
        run.action_label = str(result["action"])
        run.dimension_scores_json = result["dimensions"]
        run.strengths_json = result["strengths"]
        run.blockers_json = result["blockers"]
        run.fixes_json = result["fixes"]
        run.evidence_ids_json = result["evidence_ids"]
        run.model_version = model_version
        self._session.flush()
        return run
