from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from viraldy.api.dependencies.auth import CurrentUserDep
from viraldy.api.dependencies.request import get_request_id
from viraldy.api.responses.envelope import Envelope, success
from viraldy.modules.identity.schemas import (
    AuthConfigEnvelope,
    AuthConfigResponse,
    MeEnvelope,
    MeResponse,
)
from viraldy.platform.config.settings import AuthMode, Settings, get_settings
from viraldy.shared.errors.base import UnauthorizedError

router = APIRouter(tags=["identity"])
SettingsDep = Annotated[Settings, Depends(get_settings)]


@router.get("/auth/config", response_model=AuthConfigEnvelope)
async def get_auth_config(
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    oidc_enabled = settings.auth_mode is AuthMode.OIDC
    return success(
        AuthConfigResponse(
            auth_mode=settings.auth_mode.value,
            enabled=not settings.auth_disabled,
            authorization_url=settings.oidc_authorization_url if oidc_enabled else None,
            token_url=settings.oidc_token_url if oidc_enabled else None,
            client_id=settings.oidc_client_id if oidc_enabled else None,
            scopes=settings.oidc_scopes if oidc_enabled else [],
            registration_url=settings.oidc_registration_url if oidc_enabled else None,
            end_session_url=settings.oidc_end_session_url if oidc_enabled else None,
        ).model_dump(mode="json"),
        request_id,
    )


@router.get("/me", response_model=MeEnvelope)
async def get_me(
    current_user: CurrentUserDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    if current_user.display_name is None or current_user.phone_number is None:
        raise UnauthorizedError()
    return success(
        MeResponse(
            id=current_user.id,
            email=current_user.email,
            display_name=current_user.display_name,
            phone_number=current_user.phone_number,
            status=current_user.status,
        ).model_dump(mode="json"),
        request_id,
    )
