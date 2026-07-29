from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from viraldy.modules.adaptations.models import AdaptationRunModel
from viraldy.modules.ai_gateway.public import ADAPTATION_PROMPT_VERSION


class AdaptationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        workspace_id: UUID,
        user_id: UUID,
        product_id: UUID,
        creative_dna_version_id: UUID,
        objective: str,
        target_market: str,
        target_buyer: dict[str, object],
        constraints: dict[str, object],
        result: dict[str, Any],
        analysis_mode: str,
        model_version: str | None,
        status: str = "completed",
        primary_model_run_id: UUID | None = None,
    ) -> AdaptationRunModel:
        run = AdaptationRunModel(
            workspace_id=workspace_id,
            product_id=product_id,
            creative_dna_version_id=creative_dna_version_id,
            objective=objective,
            target_market=target_market,
            target_buyer_json=target_buyer,
            constraints_json=constraints,
            result_json=result,
            status=status,
            analysis_mode=analysis_mode,
            primary_model_run_id=primary_model_run_id,
            model_version=model_version,
            prompt_version=ADAPTATION_PROMPT_VERSION,
            created_by_user_id=user_id,
        )
        self._session.add(run)
        await self._session.flush()
        return run

    async def get(self, workspace_id: UUID, adaptation_id: UUID) -> AdaptationRunModel | None:
        result = await self._session.execute(
            select(AdaptationRunModel).where(
                AdaptationRunModel.workspace_id == workspace_id,
                AdaptationRunModel.id == adaptation_id,
            )
        )
        return result.scalar_one_or_none()
