from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from viraldy.api.dependencies.auth import CurrentUserDep
from viraldy.api.dependencies.request import get_request_id
from viraldy.api.responses.envelope import Envelope, success
from viraldy.modules.identity.schemas import AuthConfigResponse, MeResponse
from viraldy.platform.config.settings import Settings, get_settings

router = APIRouter(tags=["identity"])
SettingsDep = Annotated[Settings, Depends(get_settings)]


@router.get("/auth/config", response_model=Envelope)
async def get_auth_config(
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    return success(
        AuthConfigResponse(
            auth_mode=settings.auth_mode.value,
            enabled=not settings.auth_disabled,
            issuer_url=settings.oidc_issuer_url,
            audience=settings.oidc_audience,
        ).model_dump(mode="json"),
        request_id,
    )


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
            status=current_user.status,
        ).model_dump(mode="json"),
        request_id,
    )
