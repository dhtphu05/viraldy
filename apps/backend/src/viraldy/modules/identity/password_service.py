from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta
from uuid import uuid4

from anyio import CapacityLimiter, to_thread
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from viraldy.modules.identity.models import UserModel
from viraldy.modules.identity.password_models import (
    PasswordCredentialModel,
    PasswordRefreshTokenModel,
    PasswordSessionModel,
)
from viraldy.modules.identity.password_schemas import PasswordRegisterRequest, PasswordTokenResponse
from viraldy.modules.product_events.public import ProductEventPublisher
from viraldy.modules.workspaces.repository import WorkspaceRepository
from viraldy.platform.auth.current_user import CurrentUser
from viraldy.platform.auth.password import (
    dummy_password_hash,
    issue_access_token,
    password_hasher,
    verify_password,
)
from viraldy.platform.auth.token_verifier import VerifiedToken
from viraldy.platform.clock.utc import utc_now
from viraldy.platform.config.settings import Settings
from viraldy.shared.errors.base import AppError, ConflictError, UnauthorizedError

_password_workers = CapacityLimiter(4)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def register_password_user(
    db: AsyncSession,
    settings: Settings,
    data: PasswordRegisterRequest,
) -> PasswordTokenResponse:
    email = str(data.email).lower()
    encoded = await to_thread.run_sync(
        password_hasher.hash, data.password.get_secret_value(), limiter=_password_workers
    )
    user_id = uuid4()
    user = UserModel(
        id=user_id,
        external_auth_id=f"password:{user_id}",
        email=email,
        display_name=data.display_name,
        status="active",
        last_login_at=utc_now(),
    )
    db.add(user)
    try:
        await db.flush()
        db.add(PasswordCredentialModel(user_id=user_id, email=email, password_hash=encoded))
        await db.flush()
        workspace = await WorkspaceRepository(db).create(
            f"{data.display_name}'s workspace"[:255],
            f"workspace-{uuid4().hex}",
            user_id,
        )
        events = ProductEventPublisher(db)
        await events.record(
            event_type="user_signed_up",
            workspace_id=None,
            actor_user_id=user_id,
            subject_type="user",
            subject_id=user_id,
            payload_json={},
        )
        await events.record(
            event_type="workspace_created",
            workspace_id=workspace.id,
            actor_user_id=user_id,
            subject_type="workspace",
            subject_id=workspace.id,
            payload_json={"name": workspace.name, "slug": workspace.slug},
        )
        tokens = await _new_session(db, settings, user)
        await db.commit()
        return tokens
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError(
            "ACCOUNT_EXISTS", "This email is already registered. Please sign in."
        ) from exc


async def login_password_user(
    db: AsyncSession,
    settings: Settings,
    email: str,
    password: str,
) -> PasswordTokenResponse:
    row = (
        await db.execute(
            select(PasswordCredentialModel, UserModel)
            .join(UserModel)
            .where(PasswordCredentialModel.email == email.lower())
        )
    ).first()
    encoded = (
        row[0].password_hash
        if row
        else await to_thread.run_sync(dummy_password_hash, limiter=_password_workers)
    )
    valid = await to_thread.run_sync(verify_password, password, encoded, limiter=_password_workers)
    if row is None or not valid or row[1].status != "active":
        raise UnauthorizedError("INVALID_CREDENTIALS", "Email or password is incorrect.")
    credential, user = row
    if password_hasher.check_needs_rehash(credential.password_hash):
        credential.password_hash = await to_thread.run_sync(
            password_hasher.hash, password, limiter=_password_workers
        )
    user.last_login_at = utc_now()
    tokens = await _new_session(db, settings, user)
    await db.commit()
    return tokens


async def _new_session(
    db: AsyncSession, settings: Settings, user: UserModel
) -> PasswordTokenResponse:
    session = PasswordSessionModel(
        id=uuid4(),
        user_id=user.id,
        expires_at=utc_now() + timedelta(days=settings.auth_refresh_token_days),
    )
    db.add(session)
    await db.flush()
    return _rotate_token(db, settings, session, user)


def _rotate_token(
    db: AsyncSession,
    settings: Settings,
    session: PasswordSessionModel,
    user: UserModel,
) -> PasswordTokenResponse:
    refresh_token = secrets.token_urlsafe(48)
    db.add(PasswordRefreshTokenModel(token_hash=token_hash(refresh_token), session_id=session.id))
    return PasswordTokenResponse(
        access_token=issue_access_token(
            settings,
            user_id=user.id,
            session_id=session.id,
            email=user.email,
            display_name=user.display_name or user.email,
        ),
        refresh_token=refresh_token,
        expires_in=settings.auth_access_token_seconds,
    )


async def refresh_password_session(
    db: AsyncSession,
    settings: Settings,
    refresh_token: str,
) -> PasswordTokenResponse:
    digest = token_hash(refresh_token)
    session_id = await db.scalar(
        select(PasswordRefreshTokenModel.session_id).where(
            PasswordRefreshTokenModel.token_hash == digest
        )
    )
    if session_id is None:
        raise UnauthorizedError()
    session = await db.scalar(
        select(PasswordSessionModel).where(PasswordSessionModel.id == session_id).with_for_update()
    )
    token = await db.get(PasswordRefreshTokenModel, digest, populate_existing=True)
    now = utc_now()
    if (
        session is None
        or session.revoked_at is not None
        or session.expires_at <= now
        or token is None
    ):
        raise UnauthorizedError()
    if token.consumed_at is not None:
        if now - token.consumed_at < timedelta(seconds=5):
            raise AppError(
                "REFRESH_ALREADY_USED", "Session refresh is already complete. Please retry.", 409
            )
        session.revoked_at = now
        await db.commit()
        raise UnauthorizedError("SESSION_REVOKED", "Please sign in again.")
    user = await db.get(UserModel, session.user_id)
    if user is None or user.status != "active":
        raise UnauthorizedError()
    token.consumed_at = now
    tokens = _rotate_token(db, settings, session, user)
    await db.commit()
    return tokens


async def logout_password_session(db: AsyncSession, refresh_token: str) -> None:
    session_id = await db.scalar(
        select(PasswordRefreshTokenModel.session_id).where(
            PasswordRefreshTokenModel.token_hash == token_hash(refresh_token)
        )
    )
    if session_id is not None:
        session = await db.get(PasswordSessionModel, session_id, with_for_update=True)
        if session is not None and session.revoked_at is None:
            session.revoked_at = utc_now()
            await db.commit()


async def get_password_current_user(db: AsyncSession, verified: VerifiedToken) -> CurrentUser:
    row = (
        await db.execute(
            select(UserModel)
            .join(PasswordSessionModel, PasswordSessionModel.user_id == UserModel.id)
            .where(
                UserModel.external_auth_id == verified.external_auth_id,
                UserModel.status == "active",
                PasswordSessionModel.id == verified.session_id,
                PasswordSessionModel.revoked_at.is_(None),
                PasswordSessionModel.expires_at > utc_now(),
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise UnauthorizedError()
    return CurrentUser(
        id=row.id,
        external_auth_id=row.external_auth_id,
        email=row.email,
        display_name=row.display_name,
        phone_number=row.phone_number,
        status=row.status,
    )
