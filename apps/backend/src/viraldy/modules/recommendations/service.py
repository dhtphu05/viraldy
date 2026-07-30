from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from viraldy.modules.product_events.public import ProductEventPublisher, ProductEventType
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
        event_type = _event_type_for_recommendation_action(data.action_type)
        if event_type is not None:
            await ProductEventPublisher(self._session).record(
                event_type=event_type,
                workspace_id=workspace_id,
                actor_user_id=user_id,
                subject_type="recommendation",
                subject_id=recommendation_id,
                payload_json={"action_id": str(action_id)},
            )
        await self._session.commit()
        return RecommendationActionResponse(id=action_id)


def _event_type_for_recommendation_action(action_type: str) -> ProductEventType | None:
    if action_type == "accepted":
        return "recommendation_accepted"
    if action_type == "rejected":
        return "recommendation_rejected"
    if action_type == "applied":
        return "recommendation_applied"
    return None
