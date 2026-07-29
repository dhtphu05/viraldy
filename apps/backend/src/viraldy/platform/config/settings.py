from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from typing import Any

from pydantic import AnyUrl, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppEnv(StrEnum):
    LOCAL = "local"
    TEST = "test"
    STAGING = "staging"
    PRODUCTION = "production"


class AuthMode(StrEnum):
    OIDC = "oidc"
    LOCAL_TEST = "local_test"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Viraldy"
    app_env: AppEnv = AppEnv.LOCAL
    app_version: str = "0.1.0"
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"  # noqa: S104 # nosec B104
    api_port: int = 8000
    backend_cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    database_url: str = "postgresql+asyncpg://viraldy:viraldy@localhost:5432/viraldy"
    database_sync_url: str = "postgresql+psycopg://viraldy:viraldy@localhost:5432/viraldy"

    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    auth_mode: AuthMode = AuthMode.LOCAL_TEST
    auth_disabled: bool = False
    oidc_issuer_url: str | None = None
    oidc_audience: str | None = None
    oidc_jwks_url: AnyUrl | None = None

    s3_endpoint_url: str | None = None
    s3_region: str = "us-east-1"
    s3_bucket: str = "viraldy-local"
    s3_access_key_id: SecretStr | None = None
    s3_secret_access_key: SecretStr | None = None
    s3_force_path_style: bool = True
    s3_presigned_expiry_seconds: int = 900

    max_declared_upload_mb: int = 250
    allowed_upload_mime_types: list[str] = Field(
        default_factory=lambda: ["video/mp4", "video/quicktime", "image/jpeg", "image/png"]
    )
    max_media_duration_seconds: int = 180

    ai_mode: str = "fixture"
    ai_provider: str = "openai_compatible"
    ai_base_url: str | None = None
    ai_api_key: SecretStr | None = None
    ai_text_model: str | None = None
    ai_vision_model: str | None = None
    asr_provider: str = "fixture"
    asr_base_url: str | None = None
    asr_api_key: SecretStr | None = None
    asr_model: str | None = None
    ocr_provider: str = "fixture"
    ocr_model: str | None = None
    ai_supports_json_schema: bool = True
    ai_supports_image_url: bool = True
    ai_request_timeout_seconds: int = 120
    ai_max_retries: int = 2
    ai_max_output_tokens: int | None = None

    sentry_dsn: SecretStr | None = None
    otel_exporter_otlp_endpoint: str | None = None

    git_sha: str | None = None
    release_version: str | None = None

    @field_validator("backend_cors_origins", "allowed_upload_mime_types", mode="before")
    @classmethod
    def parse_csv(cls, value: Any) -> Any:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @model_validator(mode="after")
    def validate_production_safety(self) -> Settings:
        is_prod_like = self.app_env in {AppEnv.STAGING, AppEnv.PRODUCTION}
        if is_prod_like and self.auth_disabled:
            raise ValueError("AUTH_DISABLED is not allowed outside local/test.")
        if is_prod_like and self.auth_mode is AuthMode.LOCAL_TEST:
            raise ValueError("AUTH_MODE=local_test is not allowed outside local/test.")
        if is_prod_like and "*" in self.backend_cors_origins:
            raise ValueError("Wildcard CORS origin is not allowed outside local/test.")
        if is_prod_like:
            required = {
                "DATABASE_URL": self.database_url,
                "DATABASE_SYNC_URL": self.database_sync_url,
                "REDIS_URL": self.redis_url,
                "CELERY_BROKER_URL": self.celery_broker_url,
                "CELERY_RESULT_BACKEND": self.celery_result_backend,
                "S3_BUCKET": self.s3_bucket,
            }
            missing = [name for name, value in required.items() if not value]
            if missing:
                raise ValueError(f"Missing production settings: {', '.join(missing)}")
        if self.auth_mode is AuthMode.OIDC:
            missing = [
                name
                for name, value in {
                    "OIDC_ISSUER_URL": self.oidc_issuer_url,
                    "OIDC_AUDIENCE": self.oidc_audience,
                    "OIDC_JWKS_URL": self.oidc_jwks_url,
                }.items()
                if not value
            ]
            if missing:
                raise ValueError(f"Missing OIDC settings: {', '.join(missing)}")
        return self

    @property
    def max_declared_upload_bytes(self) -> int:
        return self.max_declared_upload_mb * 1024 * 1024

    @property
    def public_version(self) -> str:
        return self.release_version or self.app_version


@lru_cache
def get_settings() -> Settings:
    return Settings()
