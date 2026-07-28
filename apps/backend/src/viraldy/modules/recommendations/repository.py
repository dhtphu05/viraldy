from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from viraldy.modules.recommendations.models import (
    RecommendationActionModel,
    RecommendationModel,
)


class RecommendationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_recommendations(self, workspace_id: UUID) -> list[RecommendationModel]:
        result = await self._session.execute(
            select(RecommendationModel)
            .where(RecommendationModel.workspace_id == workspace_id)
            .order_by(RecommendationModel.created_at.desc())
        )
        return list(result.scalars())

    async def get_recommendation(
        self, workspace_id: UUID, recommendation_id: UUID
    ) -> RecommendationModel | None:
        result = await self._session.execute(
            select(RecommendationModel).where(
                RecommendationModel.workspace_id == workspace_id,
                RecommendationModel.id == recommendation_id,
            )
        )
        return result.scalar_one_or_none()

    async def record_action(
        self,
        workspace_id: UUID,
        recommendation_id: UUID,
        user_id: UUID,
        action_type: str,
        metadata_json: dict[str, object],
    ) -> UUID:
        action = RecommendationActionModel(
            workspace_id=workspace_id,
            recommendation_id=recommendation_id,
            user_id=user_id,
            action_type=action_type,
            metadata_json=metadata_json,
        )
        self._session.add(action)
        await self._session.flush()
        return action.id
