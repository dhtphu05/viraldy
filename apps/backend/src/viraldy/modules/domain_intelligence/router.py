from __future__ import annotations

from fastapi import APIRouter, Depends

from viraldy.api.dependencies.auth import CurrentUserDep, DbSession
from viraldy.api.dependencies.request import get_request_id
from viraldy.api.responses.envelope import Envelope, success
from viraldy.modules.domain_intelligence.public import DomainIntelligenceQueries

router = APIRouter(prefix="/domain-intelligence", tags=["domain-intelligence"])


@router.get("/status", response_model=Envelope)
async def get_domain_intelligence_status(
    current_user: CurrentUserDep,
    db: DbSession,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    _ = current_user
    status = await DomainIntelligenceQueries(db).status()
    return success(status.model_dump(mode="json"), request_id)
