from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status

from viraldy.api.dependencies.auth import CurrentUserDep, DbSession, require_workspace_permission
from viraldy.api.dependencies.request import get_request_id
from viraldy.api.responses.envelope import Envelope, success
from viraldy.modules.recommendations.schemas import RecordRecommendationActionRequest
from viraldy.modules.recommendations.service import RecommendationService
from viraldy.platform.auth.policy import Permission

router = APIRouter(prefix="/workspaces/{workspace_id}/recommendations", tags=["recommendations"])


@router.get("", response_model=Envelope)
async def list_recommendations(
    workspace_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.READ, current_user, db)
    recommendations = await RecommendationService(db).list_recommendations(workspace_id)
    return success(
        [recommendation.model_dump(mode="json") for recommendation in recommendations],
        request_id,
    )


@router.get("/{recommendation_id}", response_model=Envelope)
async def get_recommendation(
    workspace_id: UUID,
    recommendation_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.READ, current_user, db)
    recommendation = await RecommendationService(db).get_recommendation(
        workspace_id, recommendation_id
    )
    return success(recommendation.model_dump(mode="json"), request_id)


@router.post(
    "/{recommendation_id}/actions", status_code=status.HTTP_201_CREATED, response_model=Envelope
)
async def record_recommendation_action(
    workspace_id: UUID,
    recommendation_id: UUID,
    payload: RecordRecommendationActionRequest,
    current_user: CurrentUserDep,
    db: DbSession,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.READ, current_user, db)
    action = await RecommendationService(db).record_action(
        workspace_id,
        recommendation_id,
        current_user.id,
        payload,
    )
    return success(action.model_dump(mode="json"), request_id)
