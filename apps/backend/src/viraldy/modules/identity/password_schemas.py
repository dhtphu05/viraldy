from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field, SecretStr, field_validator


class PasswordLoginRequest(BaseModel):
    email: EmailStr
    password: SecretStr = Field(min_length=1, max_length=1024)


class PasswordRegisterRequest(PasswordLoginRequest):
    display_name: str = Field(min_length=1, max_length=255)
    password: SecretStr = Field(min_length=12, max_length=1024)

    @field_validator("display_name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Please enter your name.")
        return value


class RefreshTokenRequest(BaseModel):
    refresh_token: SecretStr = Field(min_length=32, max_length=256)


class PasswordTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"  # noqa: S105 - OAuth token type, not a credential
    expires_in: int
