from __future__ import annotations

from fastapi import APIRouter, Depends

from viraldy.api.dependencies.auth import CurrentUserDep
from viraldy.api.dependencies.request import get_request_id
from viraldy.api.responses.envelope import Envelope, success
from viraldy.modules.identity.schemas import MeResponse

router = APIRouter(tags=["identity"])


@router.get("/me", response_model=Envelope)
async def get_me(
    current_user: CurrentUserDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    return success(
        MeResponse(
            id=current_user.id,
            email=current_user.email,
            display_name=current_user.display_name,
            status="active",
        ).model_dump(mode="json"),
        request_id,
    )
