from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, EmailStr


class MeResponse(BaseModel):
    id: UUID
    email: EmailStr
    display_name: str | None
    status: str


class AuthConfigResponse(BaseModel):
    auth_mode: str
    enabled: bool
    issuer_url: str | None
    audience: str | None
