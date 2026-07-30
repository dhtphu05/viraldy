from __future__ import annotations

from uuid import uuid4

import pytest

from viraldy.modules.identity.schemas import MeResponse
from viraldy.platform.auth.local_test import LocalTestTokenVerifier
from viraldy.shared.errors.base import UnauthorizedError


@pytest.mark.asyncio
async def test_local_test_token_produces_valid_identity_email() -> None:
    verified = await LocalTestTokenVerifier().verify("local-test")

    identity = MeResponse(
        id=uuid4(),
        email=verified.email,
        display_name=verified.display_name,
        status="active",
    )

    assert str(identity.email) == "local@viraldy.example.com"


@pytest.mark.asyncio
async def test_local_test_token_rejects_unknown_token() -> None:
    with pytest.raises(UnauthorizedError):
        await LocalTestTokenVerifier().verify("wrong-token")
