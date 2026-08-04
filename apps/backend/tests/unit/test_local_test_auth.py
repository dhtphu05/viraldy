from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import ValidationError

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
        phone_number=verified.phone_number,
        status="active",
    )

    assert str(identity.email) == "local@viraldy.example.com"
    assert identity.display_name == "Local Viraldy User"
    assert identity.phone_number == "+84901234567"


def test_me_response_requires_phone_number() -> None:
    with pytest.raises(ValidationError):
        MeResponse(
            id=uuid4(),
            email="seller@example.com",
            display_name="Seller",
            phone_number=None,
            status="active",
        )


def test_me_response_requires_display_name() -> None:
    with pytest.raises(ValidationError):
        MeResponse(
            id=uuid4(),
            email="seller@example.com",
            display_name=None,
            phone_number="+84901234567",
            status="active",
        )


@pytest.mark.asyncio
async def test_local_test_token_rejects_unknown_token() -> None:
    with pytest.raises(UnauthorizedError):
        await LocalTestTokenVerifier().verify("wrong-token")
