from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from viraldy.api.dependencies.auth import CurrentUserDep, DbSession, require_workspace_permission
from viraldy.api.dependencies.request import get_request_id
from viraldy.api.responses.envelope import Envelope, success
from viraldy.modules.product_events.contracts import ProductEventType
from viraldy.modules.product_events.service import ProductEventService
from viraldy.platform.auth.policy import Permission

router = APIRouter(prefix="/workspaces/{workspace_id}/events", tags=["product-events"])


@router.get("", response_model=Envelope)
async def list_product_events(
    workspace_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    event_type: ProductEventType | None = None,
    subject_type: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.DATA_EXPORT, current_user, db)
    events = await ProductEventService(db).list_events(
        workspace_id=workspace_id,
        event_type=event_type,
        subject_type=subject_type,
        limit=limit,
    )
    return success([event.model_dump(mode="json") for event in events], request_id)
