from __future__ import annotations

import re

import jwt
from jwt import PyJWKClient

from viraldy.platform.auth.token_verifier import VerifiedToken
from viraldy.platform.config.settings import Settings
from viraldy.shared.errors.base import UnauthorizedError

_E164_PHONE_NUMBER = re.compile(r"\+[1-9]\d{1,14}\Z")


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
        self._jwks = PyJWKClient(
            str(settings.oidc_jwks_url),
            cache_jwk_set=True,
            lifespan=settings.oidc_jwks_cache_seconds,
        )

    async def verify(self, token: str) -> VerifiedToken:
        try:
            header = jwt.get_unverified_header(token)
            algorithm = header.get("alg")
            if algorithm not in self._settings.oidc_allowed_algorithms:
                raise UnauthorizedError()
            signing_key = self._jwks.get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=self._settings.oidc_allowed_algorithms,
                audience=self._settings.oidc_audience,
                issuer=self._settings.oidc_issuer_url,
                options={
                    "require": [
                        "exp",
                        "sub",
                        "email",
                        "email_verified",
                        "name",
                        "phone_number",
                        "phone_number_verified",
                    ]
                },
            )
        except jwt.PyJWTError as exc:
            raise UnauthorizedError() from exc
        except UnauthorizedError:
            raise
        except Exception as exc:
            raise UnauthorizedError() from exc
        subject = _required_text_claim(payload, "sub")
        email = _required_text_claim(payload, "email")
        display_name = _required_text_claim(payload, "name")
        phone_number = _required_text_claim(payload, "phone_number")
        if (
            payload.get("email_verified") is not True
            or payload.get("phone_number_verified") is not True
            or phone_number != payload.get("phone_number")
            or _E164_PHONE_NUMBER.fullmatch(phone_number) is None
        ):
            raise UnauthorizedError()
        return VerifiedToken(
            external_auth_id=subject,
            email=email,
            display_name=display_name,
            phone_number=phone_number,
        )
