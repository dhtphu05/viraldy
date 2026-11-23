from pathlib import Path

from viraldy.platform.config.settings import AuthMode, Settings


def test_committed_env_template_loads_without_private_credentials() -> None:
    template = Path(__file__).resolve().parents[4] / ".env.example"
    settings = Settings(_env_file=template, auth_mode=AuthMode.LOCAL_TEST)
    assert "http://localhost:5173" in settings.backend_cors_origins
    assert "openid" in settings.oidc_scopes
    assert settings.oidc_allowed_algorithms == ["RS256"]
