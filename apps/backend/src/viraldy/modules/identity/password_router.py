from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response

from viraldy.api.dependencies.auth import DbSession
from viraldy.api.dependencies.request import get_request_id
from viraldy.api.responses.envelope import Envelope, success
from viraldy.modules.identity.password_rate_limit import enforce_password_rate_limit
from viraldy.modules.identity.password_schemas import (
    PasswordLoginRequest,
    PasswordRegisterRequest,
    RefreshTokenRequest,
)
from viraldy.modules.identity.password_service import (
    login_password_user,
    logout_password_session,
    refresh_password_session,
    register_password_user,
)
from viraldy.platform.config.settings import AuthMode, Settings, get_settings
from viraldy.shared.errors.base import NotFoundError

router = APIRouter(prefix="/auth", tags=["identity"])


def require_password_auth(settings: Annotated[Settings, Depends(get_settings)]) -> Settings:
    if settings.auth_disabled or settings.auth_mode is not AuthMode.PASSWORD:
        raise NotFoundError("AUTH_NOT_AVAILABLE", "Email sign-in is not available.")
    return settings


PasswordSettings = Annotated[Settings, Depends(require_password_auth)]
RequestId = Annotated[str, Depends(get_request_id)]


@router.post("/register", status_code=201, response_model=Envelope)
async def register_password(
    payload: PasswordRegisterRequest,
    request: Request,
    response: Response,
    db: DbSession,
    settings: PasswordSettings,
    request_id: RequestId,
) -> Envelope:
    response.headers["Cache-Control"] = "no-store"
    await enforce_password_rate_limit(
        request, settings, action="register", email=str(payload.email)
    )
    tokens = await register_password_user(db, settings, payload)
    return success(tokens.model_dump(), request_id)


@router.post("/login", response_model=Envelope)
async def login_password(
    payload: PasswordLoginRequest,
    request: Request,
    response: Response,
    db: DbSession,
    settings: PasswordSettings,
    request_id: RequestId,
) -> Envelope:
    response.headers["Cache-Control"] = "no-store"
    await enforce_password_rate_limit(request, settings, action="login", email=str(payload.email))
    tokens = await login_password_user(
        db, settings, str(payload.email), payload.password.get_secret_value()
    )
    return success(tokens.model_dump(), request_id)


@router.post("/refresh", response_model=Envelope)
async def refresh_password(
    payload: RefreshTokenRequest,
    request: Request,
    response: Response,
    db: DbSession,
    settings: PasswordSettings,
    request_id: RequestId,
) -> Envelope:
    response.headers["Cache-Control"] = "no-store"
    await enforce_password_rate_limit(request, settings, action="refresh")
    tokens = await refresh_password_session(db, settings, payload.refresh_token.get_secret_value())
    return success(tokens.model_dump(), request_id)


@router.post("/logout", status_code=204)
async def logout_password(
    payload: RefreshTokenRequest,
    request: Request,
    db: DbSession,
    settings: PasswordSettings,
) -> Response:
    await enforce_password_rate_limit(request, settings, action="logout")
    await logout_password_session(db, payload.refresh_token.get_secret_value())
    return Response(status_code=204, headers={"Cache-Control": "no-store"})
