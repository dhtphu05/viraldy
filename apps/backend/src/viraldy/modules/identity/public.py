from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from viraldy.modules.identity.models import UserModel
from viraldy.platform.auth.current_user import CurrentUser
from viraldy.platform.auth.token_verifier import VerifiedToken


async def get_or_create_current_user(
    session: AsyncSession,
    verified: VerifiedToken,
) -> CurrentUser:
    result = await session.execute(
        select(UserModel).where(UserModel.external_auth_id == verified.external_auth_id)
    )
    user = result.scalar_one_or_none()
    if user is None:
        user = UserModel(
            external_auth_id=verified.external_auth_id,
            email=verified.email,
            display_name=verified.display_name,
            status="active",
        )
        session.add(user)
        await session.flush()

    return CurrentUser(
        id=user.id,
        external_auth_id=user.external_auth_id,
        email=user.email,
        display_name=user.display_name,
    )
