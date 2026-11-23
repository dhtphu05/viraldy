from __future__ import annotations

# ruff: noqa: S106 - fixed, non-production inputs exercise credential validation
from datetime import timedelta
from uuid import uuid4

import jwt
import pytest
from pydantic import ValidationError

from viraldy.modules.identity.password_schemas import PasswordRegisterRequest
from viraldy.platform.auth.password import (
    PasswordTokenVerifier,
    issue_access_token,
    password_hasher,
    verify_password,
)
from viraldy.platform.clock.utc import utc_now
from viraldy.platform.config.settings import Settings
from viraldy.shared.errors.base import UnauthorizedError


def password_settings() -> Settings:
    return Settings(
        _env_file=None,
        auth_mode="password",
        auth_jwt_secret="test-only-secret-with-at-least-32-random-characters-123!ABC",
    )


def test_password_mode_requires_a_strong_explicit_signing_secret() -> None:
    with pytest.raises(ValidationError, match="AUTH_JWT_SECRET"):
        Settings(_env_file=None, auth_mode="password", auth_jwt_secret="")


def test_argon2_hashes_are_salted_and_wrong_passwords_are_rejected() -> None:
    first = password_hasher.hash("test-password-long-enough")
    second = password_hasher.hash("test-password-long-enough")
    assert first.startswith("$argon2id$")
    assert first != second
    assert verify_password("test-password-long-enough", first)
    assert not verify_password("wrong-password", first)


def test_registration_rejects_short_password_and_empty_name() -> None:
    with pytest.raises(ValidationError):
        PasswordRegisterRequest(email="seller@example.com", display_name="Seller", password="short")
    with pytest.raises(ValidationError):
        PasswordRegisterRequest(
            email="seller@example.com", display_name="  ", password=uuid4().hex
        )


@pytest.mark.asyncio
async def test_signed_access_token_has_issuer_audience_expiry_and_session() -> None:
    settings = password_settings()
    user_id, session_id = uuid4(), uuid4()
    token = issue_access_token(
        settings,
        user_id=user_id,
        session_id=session_id,
        email="seller@example.com",
        display_name="Seller",
    )
    identity = await PasswordTokenVerifier(settings).verify(token)
    assert identity.external_auth_id == f"password:{user_id}"
    assert identity.session_id == session_id


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "changes",
    [
        {"iss": "evil"},
        {"aud": "other-app"},
        {"type": "refresh"},
        {"exp": 0},
        {"sid": "invalid"},
        {"sub": "invalid"},
    ],
)
async def test_access_token_rejects_wrong_claims(changes: dict[str, object]) -> None:
    settings = password_settings()
    claims = {
        "iss": "viraldy",
        "aud": "viraldy-api",
        "sub": str(uuid4()),
        "sid": str(uuid4()),
        "jti": str(uuid4()),
        "type": "access",
        "iat": utc_now(),
        "exp": utc_now() + timedelta(minutes=5),
        **changes,
    }
    token = jwt.encode(claims, settings.auth_jwt_secret.get_secret_value(), algorithm="HS256")
    with pytest.raises(UnauthorizedError):
        await PasswordTokenVerifier(settings).verify(token)


@pytest.mark.asyncio
async def test_access_token_rejects_tampering() -> None:
    settings = password_settings()
    token = issue_access_token(
        settings,
        user_id=uuid4(),
        session_id=uuid4(),
        email="seller@example.com",
        display_name="Seller",
    )
    header, payload, signature = token.split(".")
    changed = ("a" if signature[0] != "a" else "b") + signature[1:]
    with pytest.raises(UnauthorizedError):
        await PasswordTokenVerifier(settings).verify(f"{header}.{payload}.{changed}")
