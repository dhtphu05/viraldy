from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class VerifiedToken:
    external_auth_id: str
    email: str
    display_name: str | None = None


class TokenVerifier(Protocol):
    async def verify(self, token: str) -> VerifiedToken:
        raise NotImplementedError
