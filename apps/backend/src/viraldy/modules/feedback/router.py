from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from viraldy.api.dependencies.auth import CurrentUserDep, DbSession, require_workspace_permission
from viraldy.api.dependencies.request import get_request_id
from viraldy.api.responses.envelope import Envelope, success
from viraldy.modules.feedback.contracts import FeedbackSubjectType
from viraldy.modules.feedback.schemas import CreateFeedbackRequest
from viraldy.modules.feedback.service import FeedbackService
from viraldy.platform.auth.policy import Permission

router = APIRouter(prefix="/workspaces/{workspace_id}/feedback", tags=["feedback"])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=Envelope)
async def create_feedback(
    workspace_id: UUID,
    payload: CreateFeedbackRequest,
    current_user: CurrentUserDep,
    db: DbSession,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.FEEDBACK_WRITE, current_user, db)
    feedback = await FeedbackService(db).create_feedback(
        workspace_id=workspace_id,
        user_id=current_user.id,
        data=payload,
    )
    return success(feedback.model_dump(mode="json"), request_id)


@router.get("", response_model=Envelope)
async def list_feedback(
    workspace_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    subject_type: FeedbackSubjectType | None = None,
    subject_id: UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.DATA_EXPORT, current_user, db)
    feedback = await FeedbackService(db).list_feedback(
        workspace_id=workspace_id,
        subject_type=subject_type,
        subject_id=subject_id,
        limit=limit,
    )
    return success([item.model_dump(mode="json") for item in feedback], request_id)
