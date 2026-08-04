from __future__ import annotations

from uuid import UUID

from pydantic import AnyUrl, BaseModel, EmailStr

from viraldy.api.responses.envelope import Envelope


class MeResponse(BaseModel):
    id: UUID
    email: EmailStr
    display_name: str
    phone_number: str
    status: str


class AuthConfigResponse(BaseModel):
    auth_mode: str
    enabled: bool
    authorization_url: AnyUrl | None
    token_url: AnyUrl | None
    client_id: str | None
    scopes: list[str]
    registration_url: AnyUrl | None
    end_session_url: AnyUrl | None


class MeEnvelope(Envelope):
    data: MeResponse


class AuthConfigEnvelope(Envelope):
    data: AuthConfigResponse
