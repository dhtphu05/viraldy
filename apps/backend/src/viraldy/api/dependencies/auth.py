from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from viraldy.modules.identity.public import get_or_create_current_user
from viraldy.modules.workspaces.public import get_workspace_member_role
from viraldy.platform.auth.current_user import CurrentUser
from viraldy.platform.auth.local_test import LocalTestTokenVerifier
from viraldy.platform.auth.oidc import OidcTokenVerifier
from viraldy.platform.auth.policy import (
    Permission,
    WorkspaceMembershipPolicy,
    WorkspaceRole,
    normalize_workspace_role,
)
from viraldy.platform.auth.token_verifier import TokenVerifier
from viraldy.platform.config.settings import AuthMode, Settings, get_settings
from viraldy.platform.database.session import get_async_session
from viraldy.shared.errors.base import ForbiddenError, UnauthorizedError

DbSession = Annotated[AsyncSession, Depends(get_async_session)]


def get_token_verifier(settings: Annotated[Settings, Depends(get_settings)]) -> TokenVerifier:
    if settings.auth_mode is AuthMode.LOCAL_TEST:
        return LocalTestTokenVerifier()
    return OidcTokenVerifier(settings)


async def get_current_user(
    db: DbSession,
    verifier: Annotated[TokenVerifier, Depends(get_token_verifier)],
    settings: Annotated[Settings, Depends(get_settings)],
    authorization: Annotated[str | None, Header()] = None,
) -> CurrentUser:
    if settings.auth_disabled:
        raise UnauthorizedError()
    if not authorization or not authorization.lower().startswith("bearer "):
        raise UnauthorizedError()
    token = authorization.split(" ", 1)[1]
    verified = await verifier.verify(token)
    return await get_or_create_current_user(db, verified)


CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]


async def require_workspace_permission(
    workspace_id: UUID,
    permission: Permission,
    user: CurrentUser,
    db: AsyncSession,
) -> WorkspaceRole:
    role_value = await get_workspace_member_role(db, workspace_id, user.id)
    if role_value is None:
        raise ForbiddenError()
    try:
        role = normalize_workspace_role(role_value)
    except ValueError as exc:
        raise ForbiddenError() from exc
    if not WorkspaceMembershipPolicy().has_permission(role, permission):
        raise ForbiddenError()
    return role
