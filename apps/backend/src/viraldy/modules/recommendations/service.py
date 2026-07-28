from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from viraldy.modules.recommendations.repository import RecommendationRepository
from viraldy.modules.recommendations.schemas import (
    RecommendationActionResponse,
    RecommendationResponse,
    RecordRecommendationActionRequest,
)
from viraldy.modules.recommendations.validators import validate_action_type
from viraldy.shared.errors.base import NotFoundError


class RecommendationService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repository = RecommendationRepository(session)

    async def list_recommendations(self, workspace_id: UUID) -> list[RecommendationResponse]:
        recommendations = await self._repository.list_recommendations(workspace_id)
        return [
            RecommendationResponse.model_validate(recommendation)
            for recommendation in recommendations
        ]

    async def get_recommendation(
        self, workspace_id: UUID, recommendation_id: UUID
    ) -> RecommendationResponse:
        recommendation = await self._repository.get_recommendation(workspace_id, recommendation_id)
        if recommendation is None:
            raise NotFoundError("RECOMMENDATION_NOT_FOUND", "Recommendation was not found.")
        return RecommendationResponse.model_validate(recommendation)

    async def record_action(
        self,
        workspace_id: UUID,
        recommendation_id: UUID,
        user_id: UUID,
        data: RecordRecommendationActionRequest,
    ) -> RecommendationActionResponse:
        recommendation = await self._repository.get_recommendation(workspace_id, recommendation_id)
        if recommendation is None:
            raise NotFoundError("RECOMMENDATION_NOT_FOUND", "Recommendation was not found.")

        validate_action_type(data.action_type)
        action_id = await self._repository.record_action(
            workspace_id,
            recommendation_id,
            user_id,
            data.action_type,
            data.metadata_json,
        )
        await self._session.commit()
        return RecommendationActionResponse(id=action_id)
