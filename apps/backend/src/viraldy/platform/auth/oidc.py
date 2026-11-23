from __future__ import annotations

import re
from functools import lru_cache

import jwt
from jwt import PyJWKClient
from pydantic import EmailStr, TypeAdapter, ValidationError
from starlette.concurrency import run_in_threadpool

from viraldy.platform.auth.token_verifier import VerifiedToken
from viraldy.platform.config.settings import Settings
from viraldy.shared.errors.base import AppError, UnauthorizedError

_E164_PHONE_NUMBER = re.compile(r"\+[1-9]\d{1,14}\Z")
_EMAIL = TypeAdapter(EmailStr)


@lru_cache(maxsize=8)
def _jwks_client(url: str, lifespan: int) -> PyJWKClient:
    return PyJWKClient(url, cache_jwk_set=True, lifespan=lifespan, timeout=5)


def _required_text_claim(payload: dict[str, object], name: str) -> str:
    value = payload.get(name)
    if not isinstance(value, str) or not value.strip():
        raise UnauthorizedError()
    return value.strip()


class OidcTokenVerifier:
    def __init__(self, settings: Settings) -> None:
        if not settings.oidc_jwks_url:
            raise ValueError("OIDC_JWKS_URL is required")
        self._settings = settings
        self._jwks = _jwks_client(
            str(settings.oidc_jwks_url),
            settings.oidc_jwks_cache_seconds,
        )

    async def verify(self, token: str) -> VerifiedToken:
        try:
            header = jwt.get_unverified_header(token)
            algorithm = header.get("alg")
            if algorithm not in self._settings.oidc_allowed_algorithms:
                raise UnauthorizedError()
            signing_key = await run_in_threadpool(self._jwks.get_signing_key_from_jwt, token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=self._settings.oidc_allowed_algorithms,
                audience=self._settings.oidc_audience,
                issuer=self._settings.oidc_issuer_url,
                options={
                    "require": [
                        "iss",
                        "aud",
                        "iat",
                        "exp",
                        "sub",
                        "email",
                        "email_verified",
                        "name",
                    ]
                },
            )
        except jwt.PyJWKClientConnectionError as exc:
            raise AppError(
                "AUTH_PROVIDER_UNAVAILABLE",
                "Sign-in is temporarily unavailable.",
                503,
            ) from exc
        except jwt.PyJWTError as exc:
            raise UnauthorizedError() from exc
        except UnauthorizedError:
            raise
        except Exception as exc:
            raise UnauthorizedError() from exc
        subject = _required_text_claim(payload, "sub")
        email = _required_text_claim(payload, "email")
        display_name = _required_text_claim(payload, "name")
        if (
            payload.get("email_verified") is not True
            or len(subject) > 255
            or len(display_name) > 255
        ):
            raise UnauthorizedError()
        try:
            _EMAIL.validate_python(email)
        except ValidationError as exc:
            raise UnauthorizedError() from exc
        phone_number = payload.get("phone_number")
        phone_verified = (
            isinstance(phone_number, str)
            and _E164_PHONE_NUMBER.fullmatch(phone_number) is not None
            and payload.get("phone_number_verified") is True
        )
        if self._settings.oidc_require_verified_phone and not phone_verified:
            raise UnauthorizedError()
        return VerifiedToken(
            external_auth_id=subject,
            email=email,
            display_name=display_name,
            phone_number=phone_number if phone_verified else None,
        )
