from __future__ import annotations

import pytest
from pydantic import ValidationError

from viraldy.platform.config.settings import AuthMode, Settings


def test_production_rejects_local_auth() -> None:
    with pytest.raises(ValidationError):
        Settings(app_env="production", auth_mode=AuthMode.LOCAL_TEST)


def test_production_rejects_auth_disabled() -> None:
    with pytest.raises(ValidationError):
        Settings(app_env="production", auth_mode=AuthMode.OIDC, auth_disabled=True)


def test_staging_rejects_wildcard_cors() -> None:
    with pytest.raises(ValidationError):
        Settings(
            app_env="staging",
            auth_mode=AuthMode.OIDC,
            backend_cors_origins=["*"],
            oidc_issuer_url="https://issuer.example",
            oidc_audience="viraldy-api",
            oidc_jwks_url="https://issuer.example/.well-known/jwks.json",
        )


def test_oidc_mode_requires_issuer_audience_and_jwks() -> None:
    with pytest.raises(ValidationError):
        Settings(auth_mode=AuthMode.OIDC)


def test_csv_env_values_are_parsed() -> None:
    settings = Settings(
        backend_cors_origins="https://a.example,https://b.example",
        allowed_upload_mime_types="image/png,video/mp4",
        oidc_allowed_algorithms="RS256,ES256",
    )
    assert settings.backend_cors_origins == ["https://a.example", "https://b.example"]
    assert settings.allowed_upload_mime_types == ["image/png", "video/mp4"]
    assert settings.oidc_allowed_algorithms == ["RS256", "ES256"]
