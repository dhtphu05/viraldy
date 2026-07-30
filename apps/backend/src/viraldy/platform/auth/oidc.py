from __future__ import annotations

import jwt
from jwt import PyJWKClient

from viraldy.platform.auth.token_verifier import VerifiedToken
from viraldy.platform.config.settings import Settings
from viraldy.shared.errors.base import UnauthorizedError


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
                options={"require": ["exp", "sub", "email"]},
            )
        except jwt.PyJWTError as exc:
            raise UnauthorizedError() from exc
        except UnauthorizedError:
            raise
        except Exception as exc:
            raise UnauthorizedError() from exc
        subject = payload.get("sub")
        email = payload.get("email")
        if not subject or not email:
            raise UnauthorizedError()
        return VerifiedToken(
            external_auth_id=str(subject),
            email=str(email),
            display_name=payload.get("name"),
        )
