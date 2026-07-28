from __future__ import annotations

from viraldy.platform.auth.token_verifier import VerifiedToken
from viraldy.shared.errors.base import UnauthorizedError


class LocalTestTokenVerifier:
    async def verify(self, token: str) -> VerifiedToken:
        if token != "local-test":  # noqa: S105 # nosec B105
            raise UnauthorizedError()
        return VerifiedToken(
            external_auth_id="local-test-user",
            email="local@viraldy.test",
            display_name="Local Viraldy User",
        )
