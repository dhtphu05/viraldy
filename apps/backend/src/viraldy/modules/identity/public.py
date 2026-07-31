from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from viraldy.modules.identity.models import UserModel
from viraldy.modules.product_events.public import ProductEventPublisher
from viraldy.platform.auth.current_user import CurrentUser
from viraldy.platform.auth.token_verifier import VerifiedToken
from viraldy.platform.clock.utc import utc_now
from viraldy.shared.errors.base import ForbiddenError


class UserSummary(BaseModel):
    id: UUID
    email: EmailStr
    display_name: str | None
    status: str

    model_config = {"from_attributes": True}


class IdentityQueries:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_email(self, email: str) -> UserSummary | None:
        result = await self._session.execute(
            select(UserModel)
            .where(UserModel.email == email.strip().lower())
            .order_by(UserModel.created_at.desc())
            .limit(1)
        )
        user = result.scalar_one_or_none()
        return UserSummary.model_validate(user) if user is not None else None

    async def list_by_ids(self, user_ids: list[UUID]) -> list[UserSummary]:
        if not user_ids:
            return []
        result = await self._session.execute(select(UserModel).where(UserModel.id.in_(user_ids)))
        return [UserSummary.model_validate(user) for user in result.scalars()]


async def get_or_create_current_user(
    session: AsyncSession,
    verified: VerifiedToken,
) -> CurrentUser:
    normalized_email = verified.email.strip().lower()
    created = False
    result = await session.execute(
        select(UserModel).where(UserModel.external_auth_id == verified.external_auth_id)
    )
    user = result.scalar_one_or_none()
    if user is None:
        user = UserModel(
            external_auth_id=verified.external_auth_id,
            email=normalized_email,
            display_name=verified.display_name,
            phone_number=verified.phone_number,
            status="active",
        )
        session.add(user)
        try:
            await session.flush()
            created = True
        except IntegrityError:
            await session.rollback()
            result = await session.execute(
                select(UserModel).where(UserModel.external_auth_id == verified.external_auth_id)
            )
            user = result.scalar_one()

    if user.status != "active":
        raise ForbiddenError("USER_SUSPENDED", "User is not active.")

    user.email = normalized_email
    user.display_name = verified.display_name
    user.phone_number = verified.phone_number
    user.last_login_at = utc_now()
    if created:
        await ProductEventPublisher(session).record(
            event_type="user_signed_up",
            workspace_id=None,
            actor_user_id=user.id,
            subject_type="user",
            subject_id=user.id,
            payload_json={},
        )
    await session.commit()
    await session.refresh(user)

    return CurrentUser(
        id=user.id,
        external_auth_id=user.external_auth_id,
        email=user.email,
        display_name=user.display_name,
        status=user.status,
        phone_number=user.phone_number,
    )


__all__ = ["IdentityQueries", "UserSummary", "get_or_create_current_user"]
