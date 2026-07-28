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
        self._jwks = PyJWKClient(str(settings.oidc_jwks_url))

    async def verify(self, token: str) -> VerifiedToken:
        try:
            signing_key = self._jwks.get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=self._settings.oidc_audience,
                issuer=self._settings.oidc_issuer_url,
            )
        except jwt.PyJWTError as exc:
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
