from __future__ import annotations

import secrets
from datetime import timedelta
from functools import lru_cache
from uuid import UUID, uuid4

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from viraldy.platform.auth.token_verifier import VerifiedToken
from viraldy.platform.clock.utc import utc_now
from viraldy.platform.config.settings import Settings
from viraldy.shared.errors.base import UnauthorizedError

password_hasher = PasswordHasher()


@lru_cache(maxsize=1)
def dummy_password_hash() -> str:
    return password_hasher.hash(secrets.token_urlsafe(32))


def verify_password(password: str, encoded: str) -> bool:
    try:
        return password_hasher.verify(encoded, password)
    except (VerificationError, InvalidHashError):
        return False


def issue_access_token(
    settings: Settings,
    *,
    user_id: UUID,
    session_id: UUID,
    email: str,
    display_name: str,
) -> str:
    if settings.auth_jwt_secret is None:
        raise ValueError("Password authentication is not configured")
    now = utc_now()
    return jwt.encode(
        {
            "iss": settings.auth_jwt_issuer,
            "aud": settings.auth_jwt_audience,
            "sub": str(user_id),
            "sid": str(session_id),
            "jti": str(uuid4()),
            "type": "access",
            "iat": now,
            "exp": now + timedelta(seconds=settings.auth_access_token_seconds),
            "email": email,
            "name": display_name,
        },
        settings.auth_jwt_secret.get_secret_value(),
        algorithm="HS256",
    )


class PasswordTokenVerifier:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def verify(self, token: str) -> VerifiedToken:
        secret = self._settings.auth_jwt_secret
        if secret is None:
            raise UnauthorizedError()
        try:
            payload = jwt.decode(
                token,
                secret.get_secret_value(),
                algorithms=["HS256"],
                issuer=self._settings.auth_jwt_issuer,
                audience=self._settings.auth_jwt_audience,
                options={"require": ["iss", "aud", "sub", "sid", "jti", "iat", "exp", "type"]},
            )
            user_id = UUID(payload["sub"])
            session_id = UUID(payload["sid"])
            if payload["type"] != "access":
                raise UnauthorizedError()
            return VerifiedToken(
                external_auth_id=f"password:{user_id}",
                email=str(payload.get("email", "")),
                display_name=str(payload.get("name", "")),
                phone_number=None,
                session_id=session_id,
            )
        except (jwt.PyJWTError, ValueError, TypeError, KeyError) as exc:
            raise UnauthorizedError() from exc
