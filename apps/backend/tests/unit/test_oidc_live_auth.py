from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from pydantic import ValidationError

from viraldy.modules.identity.router import get_me
from viraldy.platform.auth.current_user import CurrentUser
from viraldy.platform.auth.oidc import OidcTokenVerifier
from viraldy.platform.config.settings import Settings
from viraldy.shared.errors.base import AppError, UnauthorizedError


def oidc_settings(**overrides: object) -> Settings:
    return Settings(
        _env_file=None,
        **{
            "auth_mode": "oidc",
            "oidc_issuer_url": "https://identity.example/realms/viraldy",
            "oidc_audience": "viraldy-api",
            "oidc_jwks_url": "https://identity.example/realms/viraldy/certs",
            **overrides,
        },
    )


@pytest.fixture
def private_key() -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def access_token(key: rsa.RSAPrivateKey, **changes: object) -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "iss": "https://identity.example/realms/viraldy",
            "aud": "viraldy-api",
            "sub": "seller-123",
            "iat": now,
            "exp": now + timedelta(minutes=5),
            "email": "seller@example.com",
            "email_verified": True,
            "name": "Seller One",
            **changes,
        },
        key,
        algorithm="RS256",
        headers={"kid": "test-key"},
    )


@pytest.mark.asyncio
async def test_email_verified_account_can_sign_in_without_phone(
    private_key: rsa.RSAPrivateKey,
) -> None:
    verifier = OidcTokenVerifier(oidc_settings())
    with patch.object(verifier._jwks, "get_signing_key_from_jwt") as signing_key:  # noqa: SLF001
        signing_key.return_value.key = private_key.public_key()
        identity = await verifier.verify(access_token(private_key))
    assert identity.email == "seller@example.com"
    assert identity.phone_number is None


@pytest.mark.asyncio
async def test_strict_phone_policy_still_requires_verified_phone(
    private_key: rsa.RSAPrivateKey,
) -> None:
    verifier = OidcTokenVerifier(oidc_settings(oidc_require_verified_phone=True))
    with patch.object(verifier._jwks, "get_signing_key_from_jwt") as signing_key:  # noqa: SLF001
        signing_key.return_value.key = private_key.public_key()
        with pytest.raises(UnauthorizedError):
            await verifier.verify(access_token(private_key))


@pytest.mark.asyncio
@pytest.mark.parametrize("claim", ["iss", "aud", "iat", "exp", "sub"])
async def test_required_jwt_claims_cannot_be_omitted(
    private_key: rsa.RSAPrivateKey,
    claim: str,
) -> None:
    claims = jwt.decode(
        access_token(private_key, phone_number="+84901234567", phone_number_verified=True),
        options={"verify_signature": False},
    )
    claims.pop(claim)
    token = jwt.encode(claims, private_key, algorithm="RS256")
    verifier = OidcTokenVerifier(oidc_settings())
    with patch.object(verifier._jwks, "get_signing_key_from_jwt") as signing_key:  # noqa: SLF001
        signing_key.return_value.key = private_key.public_key()
        with pytest.raises(UnauthorizedError):
            await verifier.verify(token)


@pytest.mark.asyncio
async def test_invalid_email_is_rejected_before_user_is_persisted(
    private_key: rsa.RSAPrivateKey,
) -> None:
    verifier = OidcTokenVerifier(oidc_settings())
    with patch.object(verifier._jwks, "get_signing_key_from_jwt") as signing_key:  # noqa: SLF001
        signing_key.return_value.key = private_key.public_key()
        with pytest.raises(UnauthorizedError):
            await verifier.verify(access_token(private_key, email="invalid-email"))


@pytest.mark.asyncio
async def test_unverified_optional_phone_is_not_exposed_as_verified_identity(
    private_key: rsa.RSAPrivateKey,
) -> None:
    verifier = OidcTokenVerifier(oidc_settings())
    with patch.object(verifier._jwks, "get_signing_key_from_jwt") as signing_key:  # noqa: SLF001
        signing_key.return_value.key = private_key.public_key()
        identity = await verifier.verify(
            access_token(
                private_key,
                phone_number="+84901234567",
                phone_number_verified=False,
            )
        )
    assert identity.phone_number is None


def test_jwks_cache_is_reused_across_requests() -> None:
    settings = oidc_settings()
    assert OidcTokenVerifier(settings)._jwks is OidcTokenVerifier(settings)._jwks  # noqa: SLF001


@pytest.mark.asyncio
async def test_jwks_outage_is_unavailable_rather_than_invalid_credentials(
    private_key: rsa.RSAPrivateKey,
) -> None:
    verifier = OidcTokenVerifier(oidc_settings())
    with patch.object(verifier._jwks, "get_signing_key_from_jwt") as signing_key:  # noqa: SLF001
        signing_key.side_effect = jwt.PyJWKClientConnectionError("Provider is down")
        with pytest.raises(AppError) as error:
            await verifier.verify(access_token(private_key))
    assert error.value.status_code == 503


@pytest.mark.parametrize("algorithms", [[], ["none"], ["HS256"], ["RS256", "HS256"]])
def test_oidc_rejects_unsafe_algorithm_configuration(algorithms: list[str]) -> None:
    with pytest.raises(ValidationError):
        oidc_settings(oidc_allowed_algorithms=algorithms)


@pytest.mark.parametrize("setting", ["oidc_issuer_url", "oidc_jwks_url"])
def test_production_requires_https_for_jwt_trust_endpoints(setting: str) -> None:
    with pytest.raises(ValidationError, match="HTTPS"):
        oidc_settings(
            app_env="production",
            oidc_authorization_url="https://identity.example/auth",
            oidc_token_url="https://identity.example/token",  # noqa: S106
            oidc_client_id="viraldy-web",
            **{setting: "http://identity.example/insecure"},
        )


@pytest.mark.asyncio
async def test_me_returns_profile_with_optional_phone() -> None:
    from uuid import uuid4

    user = CurrentUser(
        id=uuid4(),
        external_auth_id="seller-123",
        email="seller@example.com",
        display_name="Seller One",
        phone_number=None,
        status="active",
    )
    response = await get_me(current_user=user, request_id="test")
    assert response.data["phone_number"] is None
