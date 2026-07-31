from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from typing import Any, Literal
from urllib.parse import urlsplit

from pydantic import AnyUrl, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_openai_timestamp_granularities() -> list[Literal["segment", "word"]]:
    return ["segment"]


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
    job_stale_after_seconds: int = Field(default=900, ge=60)
    product_crawl_max_concurrency: int = Field(default=2, ge=1, le=8)
    product_crawl_public_base_url: str = "http://127.0.0.1:8000"
    product_crawl_output_dir: str | None = None
    product_crawl_review_clip_ttl_hours: int = Field(default=6, ge=1, le=168)

    auth_mode: AuthMode = AuthMode.LOCAL_TEST
    auth_disabled: bool = False
    oidc_issuer_url: str | None = None
    oidc_audience: str | None = None
    oidc_jwks_url: AnyUrl | None = None
    oidc_allowed_algorithms: list[str] = Field(default_factory=lambda: ["RS256"])
    oidc_jwks_cache_seconds: int = 300
    oidc_authorization_url: AnyUrl | None = None
    oidc_token_url: AnyUrl | None = None
    oidc_client_id: str | None = None
    oidc_scopes: list[str] = Field(
        default_factory=lambda: ["openid", "profile", "email", "phone", "offline_access"]
    )
    oidc_registration_url: AnyUrl | None = None
    oidc_end_session_url: AnyUrl | None = None

    s3_endpoint_url: str | None = None
    s3_region: str = "us-east-1"
    s3_bucket: str = "viraldy-local"
    s3_access_key_id: SecretStr | None = None
    s3_secret_access_key: SecretStr | None = None
    s3_force_path_style: bool = True
    s3_presigned_expiry_seconds: int = 900

    max_declared_upload_mb: int = 250
    max_upload_size_bytes: int | None = Field(default=None, ge=1)
    allowed_upload_mime_types: list[str] = Field(
        default_factory=lambda: ["video/mp4", "video/quicktime", "image/jpeg", "image/png"]
    )
    max_media_duration_seconds: int = 180
    asset_retention_days: int = Field(default=14, ge=1)
    model_output_retention_days: int = Field(default=90, ge=1)

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

    openai_api_key: SecretStr | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    openai_text_model: str = "gpt-5"
    openai_vision_model: str = "gpt-5"
    openai_transcription_model: str = "whisper-1"
    openai_reasoning_effort: Literal["none", "minimal", "low", "medium", "high", "xhigh", "max"] = (
        "medium"
    )
    openai_store_responses: bool = False
    openai_max_output_tokens: int = Field(default=16000, ge=1)
    openai_request_timeout_seconds: float = Field(default=180, gt=0)
    openai_max_retries: int = Field(default=2, ge=0, le=10)
    openai_image_detail: Literal["auto", "low", "high", "original"] = "auto"
    openai_image_transport: Literal["base64"] = "base64"
    openai_transcription_response_format: str = "verbose_json"
    openai_transcription_timestamp_granularities: list[Literal["segment", "word"]] = Field(
        default_factory=_default_openai_timestamp_granularities
    )
    openai_max_frames_per_video: int = Field(default=12, ge=1)
    openai_max_frame_long_edge: int = Field(default=1280, ge=1)
    openai_max_transcript_chars: int = Field(default=50000, ge=1)
    openai_max_parallel_requests_per_workspace: int = Field(default=2, ge=1)
    openai_model_media_observation: str | None = None
    openai_model_creative_dna: str | None = None
    openai_model_pattern_kit: str | None = None
    openai_model_viral_kit: str | None = None
    openai_model_adaptation: str | None = None
    openai_model_campaign_pack: str | None = None
    openai_model_decision_summary: str | None = None
    openai_model_revision_message: str | None = None

    image_generation_enabled: bool = False
    video_generation_enabled: bool = False
    image_generation_model: str | None = None
    video_generation_model: str | None = None

    # "Supported" remains an evidence label, not a causal or winner claim.
    pattern_performance_supported_min_asset_count: int = Field(default=10, ge=1)
    pattern_performance_supported_min_campaign_count: int = Field(default=3, ge=1)
    pattern_performance_supported_min_metric_sample_size: int = Field(default=10, ge=1)

    sentry_dsn: SecretStr | None = None
    otel_exporter_otlp_endpoint: str | None = None

    git_sha: str | None = None
    release_version: str | None = None

    @field_validator(
        "backend_cors_origins",
        "allowed_upload_mime_types",
        "oidc_allowed_algorithms",
        "oidc_scopes",
        "openai_transcription_timestamp_granularities",
        mode="before",
    )
    @classmethod
    def parse_csv(cls, value: Any) -> Any:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("openai_api_key", mode="before")
    @classmethod
    def normalize_empty_openai_key(cls, value: Any) -> Any:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("oidc_client_id", mode="before")
    @classmethod
    def normalize_oidc_client_id(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip() or None
        return value

    @field_validator(
        "oidc_authorization_url",
        "oidc_token_url",
        "oidc_registration_url",
        "oidc_end_session_url",
    )
    @classmethod
    def validate_public_oidc_url(cls, value: AnyUrl | None) -> AnyUrl | None:
        if value is None:
            return None
        parsed = urlsplit(str(value))
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("Public OIDC URLs must use HTTP(S).")
        if parsed.username or parsed.password:
            raise ValueError("Public OIDC URLs must not contain credentials.")
        return value

    @field_validator("openai_base_url")
    @classmethod
    def validate_openai_base_url(cls, value: str) -> str:
        normalized = value.rstrip("/")
        parsed = urlsplit(normalized)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("OPENAI_BASE_URL must be an absolute HTTP(S) URL.")
        if parsed.username or parsed.password:
            raise ValueError("OPENAI_BASE_URL must not contain credentials.")
        return normalized

    @field_validator("product_crawl_public_base_url")
    @classmethod
    def validate_product_crawl_public_base_url(cls, value: str) -> str:
        normalized = value.rstrip("/")
        parsed = urlsplit(normalized)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("PRODUCT_CRAWL_PUBLIC_BASE_URL must be an absolute HTTP(S) URL.")
        if parsed.username or parsed.password:
            raise ValueError("PRODUCT_CRAWL_PUBLIC_BASE_URL must not contain credentials.")
        return normalized

    @field_validator(
        "openai_text_model",
        "openai_vision_model",
        "openai_transcription_model",
    )
    @classmethod
    def validate_required_openai_model(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Required OpenAI model settings must not be empty.")
        return value.strip()

    @field_validator(
        "openai_model_media_observation",
        "openai_model_creative_dna",
        "openai_model_pattern_kit",
        "openai_model_viral_kit",
        "openai_model_adaptation",
        "openai_model_campaign_pack",
        "openai_model_decision_summary",
        "openai_model_revision_message",
        mode="before",
    )
    @classmethod
    def normalize_optional_openai_model(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip() or None
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
        if is_prod_like and self.auth_mode is AuthMode.OIDC:
            missing_browser_settings = [
                name
                for name, value in {
                    "OIDC_AUTHORIZATION_URL": self.oidc_authorization_url,
                    "OIDC_TOKEN_URL": self.oidc_token_url,
                    "OIDC_CLIENT_ID": self.oidc_client_id,
                }.items()
                if not value
            ]
            if missing_browser_settings:
                raise ValueError(
                    f"Missing OIDC browser-flow settings: {', '.join(missing_browser_settings)}"
                )
            insecure_browser_settings = [
                name
                for name, value in {
                    "OIDC_AUTHORIZATION_URL": self.oidc_authorization_url,
                    "OIDC_TOKEN_URL": self.oidc_token_url,
                    "OIDC_REGISTRATION_URL": self.oidc_registration_url,
                    "OIDC_END_SESSION_URL": self.oidc_end_session_url,
                }.items()
                if value is not None and urlsplit(str(value)).scheme != "https"
            ]
            if insecure_browser_settings:
                raise ValueError(
                    "OIDC browser-flow settings must use HTTPS outside local/test: "
                    f"{', '.join(insecure_browser_settings)}"
                )
            required_scopes = {"openid", "profile", "email", "phone", "offline_access"}
            missing_scopes = sorted(required_scopes.difference(self.oidc_scopes))
            if missing_scopes:
                raise ValueError(f"OIDC_SCOPES must include: {', '.join(missing_scopes)}")
        if self.ai_mode == "live" and self.ai_provider == "openai" and not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required when AI_MODE=live and AI_PROVIDER=openai.")
        if (
            is_prod_like
            and self.ai_mode == "live"
            and self.ai_provider == "openai"
            and urlsplit(self.openai_base_url).scheme != "https"
        ):
            raise ValueError("OPENAI_BASE_URL must use HTTPS outside local/test.")
        return self

    @property
    def max_declared_upload_bytes(self) -> int:
        return self.max_upload_size_bytes or self.max_declared_upload_mb * 1024 * 1024

    @property
    def public_version(self) -> str:
        return self.release_version or self.app_version

    def resolve_openai_model(self, operation: str, *, vision: bool = False) -> str:
        operation_models = {
            "media_observation": self.openai_model_media_observation,
            "creative_dna_build": self.openai_model_creative_dna,
            "pattern_kit_extract": self.openai_model_pattern_kit,
            "viral_kit_compose": self.openai_model_viral_kit,
            "adaptation_generate": self.openai_model_adaptation,
            "campaign_pack_generate": self.openai_model_campaign_pack,
            "seller_decision_summary": self.openai_model_decision_summary,
            "revision_message_generate": self.openai_model_revision_message,
        }
        uses_vision_model = vision or operation == "media_observation"
        return operation_models.get(operation) or (
            self.openai_vision_model if uses_vision_model else self.openai_text_model
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
