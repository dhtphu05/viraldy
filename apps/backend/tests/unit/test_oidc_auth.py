from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from viraldy.platform.auth.oidc import OidcTokenVerifier
from viraldy.platform.config.settings import AuthMode, Settings
from viraldy.shared.errors.base import UnauthorizedError


class FakeSigningKey:
    def __init__(self, key: object) -> None:
        self.key = key


class FakeJwks:
    def __init__(self, key: object) -> None:
        self.key = key

    def get_signing_key_from_jwt(self, token: str) -> FakeSigningKey:
        return FakeSigningKey(self.key)


@pytest.fixture
def key_pair() -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def verifier(public_key: object) -> OidcTokenVerifier:
    settings = Settings(
        auth_mode=AuthMode.OIDC,
        oidc_issuer_url="https://issuer.example",
        oidc_audience="viraldy-api",
        oidc_jwks_url="https://issuer.example/.well-known/jwks.json",
    )
    token_verifier = OidcTokenVerifier(settings)
    token_verifier._jwks = FakeJwks(public_key)  # type: ignore[attr-defined]  # noqa: SLF001
    return token_verifier


def signed_token(
    private_key: rsa.RSAPrivateKey,
    payload_updates: dict[str, Any] | None = None,
) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "iss": "https://issuer.example",
        "aud": "viraldy-api",
        "sub": "provider-user-123",
        "email": "Seller@Example.com",
        "email_verified": True,
        "name": "Seller",
        "phone_number": "+84901234567",
        "phone_number_verified": True,
        "iat": now,
        "nbf": now - timedelta(seconds=1),
        "exp": now + timedelta(minutes=5),
    }
    if payload_updates:
        payload.update(payload_updates)
    return jwt.encode(payload, private_key, algorithm="RS256", headers={"kid": "test-key"})


@pytest.mark.asyncio
async def test_oidc_verifier_accepts_valid_token(key_pair: rsa.RSAPrivateKey) -> None:
    verified = await verifier(key_pair.public_key()).verify(signed_token(key_pair))

    assert verified.external_auth_id == "provider-user-123"
    assert verified.email == "Seller@Example.com"
    assert verified.display_name == "Seller"
    assert verified.phone_number == "+84901234567"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload_updates",
    [
        {"iss": "https://wrong-issuer.example"},
        {"aud": "wrong-audience"},
        {"exp": datetime.now(UTC) - timedelta(minutes=1)},
        {"nbf": datetime.now(UTC) + timedelta(minutes=5)},
        {"sub": None},
        {"email": None},
        {"email": "   "},
        {"email_verified": None},
        {"email_verified": False},
        {"email_verified": "true"},
        {"name": None},
        {"name": "   "},
        {"phone_number": None},
        {"phone_number": ""},
        {"phone_number": "0901234567"},
        {"phone_number": " +84901234567"},
        {"phone_number": "+0123456789"},
        {"phone_number": "+8490123456789012"},
        {"phone_number_verified": None},
        {"phone_number_verified": False},
        {"phone_number_verified": "true"},
    ],
)
async def test_oidc_verifier_rejects_invalid_claims(
    key_pair: rsa.RSAPrivateKey,
    payload_updates: dict[str, Any],
) -> None:
    with pytest.raises(UnauthorizedError):
        await verifier(key_pair.public_key()).verify(signed_token(key_pair, payload_updates))


@pytest.mark.asyncio
async def test_oidc_verifier_rejects_wrong_signature(key_pair: rsa.RSAPrivateKey) -> None:
    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    with pytest.raises(UnauthorizedError):
        await verifier(other_key.public_key()).verify(signed_token(key_pair))


@pytest.mark.asyncio
async def test_oidc_verifier_rejects_disallowed_algorithm(
    key_pair: rsa.RSAPrivateKey,
) -> None:
    token = jwt.encode(
        {
            "iss": "https://issuer.example",
            "aud": "viraldy-api",
            "sub": "provider-user-123",
            "email": "seller@example.com",
            "exp": datetime.now(UTC) + timedelta(minutes=5),
        },
        "dev-only-hmac-key-with-32-byte-minimum",  # noqa: S106
        algorithm="HS256",
    )

    with pytest.raises(UnauthorizedError):
        await verifier(key_pair.public_key()).verify(token)
