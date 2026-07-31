from __future__ import annotations

import pytest
from pydantic import ValidationError

from viraldy.modules.identity.router import get_auth_config
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


def test_production_oidc_requires_browser_flow_settings() -> None:
    with pytest.raises(
        ValidationError,
        match="OIDC_AUTHORIZATION_URL.*OIDC_TOKEN_URL.*OIDC_CLIENT_ID",
    ):
        Settings(
            _env_file=None,
            app_env="production",
            auth_mode=AuthMode.OIDC,
            oidc_issuer_url="https://issuer.example",
            oidc_audience="viraldy-api",
            oidc_jwks_url="https://issuer.example/.well-known/jwks.json",
        )


def test_production_oidc_requires_standard_identity_scopes() -> None:
    with pytest.raises(ValidationError, match="OIDC_SCOPES.*email.*phone"):
        Settings(
            _env_file=None,
            app_env="production",
            auth_mode=AuthMode.OIDC,
            oidc_issuer_url="https://issuer.example",
            oidc_audience="viraldy-api",
            oidc_jwks_url="https://issuer.example/.well-known/jwks.json",
            oidc_authorization_url="https://issuer.example/authorize",
            oidc_token_url="https://issuer.example/oauth/token",  # noqa: S106
            oidc_client_id="viraldy-web",
            oidc_scopes=["openid", "profile"],
        )


def test_production_oidc_requires_offline_access_for_session_refresh() -> None:
    with pytest.raises(ValidationError, match="OIDC_SCOPES.*offline_access"):
        Settings(
            _env_file=None,
            app_env="production",
            auth_mode=AuthMode.OIDC,
            oidc_issuer_url="https://issuer.example",
            oidc_audience="viraldy-api",
            oidc_jwks_url="https://issuer.example/.well-known/jwks.json",
            oidc_authorization_url="https://issuer.example/authorize",
            oidc_token_url="https://issuer.example/oauth/token",  # noqa: S106
            oidc_client_id="viraldy-web",
            oidc_scopes=["openid", "profile", "email", "phone"],
        )


def test_oidc_browser_flow_urls_reject_embedded_credentials() -> None:
    with pytest.raises(ValidationError, match="must not contain credentials"):
        Settings(
            _env_file=None,
            oidc_authorization_url="https://user:password@issuer.example/authorize",
        )


def test_production_oidc_requires_https_browser_flow_urls() -> None:
    with pytest.raises(ValidationError, match="must use HTTPS"):
        Settings(
            _env_file=None,
            app_env="production",
            auth_mode=AuthMode.OIDC,
            oidc_issuer_url="https://issuer.example",
            oidc_audience="viraldy-api",
            oidc_jwks_url="https://issuer.example/.well-known/jwks.json",
            oidc_authorization_url="http://issuer.example/authorize",
            oidc_token_url="https://issuer.example/oauth/token",  # noqa: S106
            oidc_client_id="viraldy-web",
        )


@pytest.mark.asyncio
async def test_auth_config_exposes_only_public_browser_flow_settings() -> None:
    settings = Settings(
        _env_file=None,
        auth_mode=AuthMode.OIDC,
        oidc_issuer_url="https://issuer.example",
        oidc_audience="viraldy-api",
        oidc_jwks_url="https://issuer.example/.well-known/jwks.json",
        oidc_authorization_url="https://issuer.example/authorize",
        oidc_token_url="https://issuer.example/oauth/token",  # noqa: S106
        oidc_client_id="viraldy-web",
        oidc_scopes="openid,profile,email,phone,offline_access",
        oidc_registration_url="https://issuer.example/register",
        oidc_end_session_url="https://issuer.example/logout",
    )

    response = await get_auth_config(settings=settings, request_id="test-request")

    assert response.data == {
        "auth_mode": "oidc",
        "enabled": True,
        "authorization_url": "https://issuer.example/authorize",
        "token_url": "https://issuer.example/oauth/token",
        "client_id": "viraldy-web",
        "scopes": ["openid", "profile", "email", "phone", "offline_access"],
        "registration_url": "https://issuer.example/register",
        "end_session_url": "https://issuer.example/logout",
    }


def test_csv_env_values_are_parsed() -> None:
    settings = Settings(
        _env_file=None,
        backend_cors_origins="https://a.example,https://b.example",
        allowed_upload_mime_types="image/png,video/mp4",
        oidc_allowed_algorithms="RS256,ES256",
        openai_transcription_timestamp_granularities="segment,word",
    )
    assert settings.backend_cors_origins == ["https://a.example", "https://b.example"]
    assert settings.allowed_upload_mime_types == ["image/png", "video/mp4"]
    assert settings.oidc_allowed_algorithms == ["RS256", "ES256"]
    assert settings.openai_transcription_timestamp_granularities == ["segment", "word"]


def test_openai_defaults_and_operation_model_routing() -> None:
    settings = Settings(
        _env_file=None,
        openai_model_pattern_kit="gpt-5-pattern",
        openai_model_decision_summary="gpt-5-summary",
    )

    assert settings.openai_base_url == "https://api.openai.com/v1"
    assert settings.openai_text_model == "gpt-5"
    assert settings.openai_vision_model == "gpt-5"
    assert settings.openai_transcription_model == "whisper-1"
    assert settings.openai_reasoning_effort == "medium"
    assert settings.openai_store_responses is False
    assert settings.openai_max_output_tokens == 16000
    assert settings.openai_request_timeout_seconds == 180
    assert settings.openai_max_retries == 2
    assert settings.openai_image_transport == "base64"
    assert settings.resolve_openai_model("pattern_kit_extract") == "gpt-5-pattern"
    assert settings.resolve_openai_model("seller_decision_summary") == "gpt-5-summary"
    assert settings.resolve_openai_model("media_observation", vision=True) == "gpt-5"
    assert settings.resolve_openai_model("media_observation") == "gpt-5"
    assert settings.resolve_openai_model("unknown_operation") == "gpt-5"


def test_live_native_openai_requires_openai_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("openai_api_key", raising=False)
    with pytest.raises(ValidationError, match="OPENAI_API_KEY"):
        Settings(
            _env_file=None,
            ai_mode="live",
            ai_provider="openai",
        )

    configured = Settings(
        _env_file=None,
        ai_mode="live",
        ai_provider="openai",
        openai_api_key="test-only-secret",
    )
    assert configured.openai_api_key is not None
    assert configured.openai_api_key.get_secret_value() == "test-only-secret"
    assert "test-only-secret" not in repr(configured)


def test_fixture_mode_does_not_require_openai_key() -> None:
    settings = Settings(
        _env_file=None,
        ai_mode="fixture",
        ai_provider="openai",
        openai_api_key="",
    )
    assert settings.openai_api_key is None


def test_openai_base_url_rejects_credentials() -> None:
    with pytest.raises(ValidationError, match="must not contain credentials"):
        Settings(
            _env_file=None,
            openai_base_url="https://user:password@api.openai.com/v1",
        )


def test_unimplemented_openai_signed_url_transport_is_rejected() -> None:
    with pytest.raises(ValidationError, match="openai_image_transport"):
        Settings(
            _env_file=None,
            openai_image_transport="signed_url",  # type: ignore[arg-type]
        )
