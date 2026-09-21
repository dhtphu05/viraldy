import os


DEFAULT_MAX_REFERENCE_VIDEO_BYTES = 30 * 1024 * 1024
DEFAULT_MAX_PRODUCT_IMAGE_BYTES = 10 * 1024 * 1024
DEFAULT_SMART_REMAKE_GEMINI_MODEL = "gemini-2.5-flash"
DEFAULT_FLOWKIT_URL = "http://127.0.0.1:8100"
DEFAULT_UNIFICALLY_API_BASE_URL = "https://api.unifically.com"
DEFAULT_UNIFICALLY_FILES_BASE_URL = "https://files.storagecdn.online"
DEFAULT_UNIFICALLY_IMAGE_MODEL = "google/nano-banana-2-lite"
DEFAULT_UNIFICALLY_VIDEO_MODEL = "google/veo-3.1-lite-relaxed"
DEFAULT_UNIFICALLY_POLL_INTERVAL_SECONDS = 5.0
DEFAULT_UNIFICALLY_POLL_TIMEOUT_SECONDS = 900.0
DEFAULT_SMART_REMAKE_ASSET_TTL_SECONDS = 24 * 60 * 60
DEFAULT_SMART_REMAKE_LOCAL_OUTPUT_TTL_SECONDS = 7 * 24 * 60 * 60


def _positive_int_env(name: str, fallback: int) -> int:
    raw = os.getenv(name)
    if not raw:
        return fallback
    try:
        value = int(raw)
    except ValueError:
        return fallback
    return value if value > 0 else fallback


def _positive_float_env(name: str, fallback: float) -> float:
    raw = os.getenv(name)
    if not raw:
        return fallback
    try:
        value = float(raw)
    except ValueError:
        return fallback
    return value if value > 0 else fallback


def _bool_env(name: str, fallback: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return fallback
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def is_smart_remake_enabled() -> bool:
    return os.getenv("SMART_REMAKE_ENABLED") == "true"


def get_max_reference_video_bytes() -> int:
    return _positive_int_env(
        "SMART_REMAKE_MAX_REFERENCE_VIDEO_BYTES",
        DEFAULT_MAX_REFERENCE_VIDEO_BYTES,
    )


def get_max_product_image_bytes() -> int:
    return _positive_int_env(
        "SMART_REMAKE_MAX_PRODUCT_IMAGE_BYTES",
        DEFAULT_MAX_PRODUCT_IMAGE_BYTES,
    )


def get_smart_remake_asset_ttl_seconds() -> int:
    return _positive_int_env(
        "SMART_REMAKE_ASSET_TTL_SECONDS",
        DEFAULT_SMART_REMAKE_ASSET_TTL_SECONDS,
    )


def get_smart_remake_local_output_ttl_seconds() -> int:
    return _positive_int_env(
        "SMART_REMAKE_LOCAL_OUTPUT_TTL_SECONDS",
        DEFAULT_SMART_REMAKE_LOCAL_OUTPUT_TTL_SECONDS,
    )


def get_gemini_model() -> str:
    return os.getenv("SMART_REMAKE_GEMINI_MODEL", "").strip() or DEFAULT_SMART_REMAKE_GEMINI_MODEL


def get_flowkit_url() -> str:
    return os.getenv("FLOWKIT_URL", DEFAULT_FLOWKIT_URL).rstrip("/")


def get_unifically_api_key() -> str:
    return os.getenv("UNIFICALLY_API_KEY", "").strip()


def get_unifically_api_base_url() -> str:
    return os.getenv("UNIFICALLY_API_BASE_URL", DEFAULT_UNIFICALLY_API_BASE_URL).rstrip("/")


def get_unifically_files_base_url() -> str:
    return os.getenv("UNIFICALLY_FILES_BASE_URL", DEFAULT_UNIFICALLY_FILES_BASE_URL).rstrip("/")


def get_unifically_image_model() -> str:
    return os.getenv("UNIFICALLY_IMAGE_MODEL", DEFAULT_UNIFICALLY_IMAGE_MODEL).strip() or DEFAULT_UNIFICALLY_IMAGE_MODEL


def get_unifically_video_model() -> str:
    return os.getenv("UNIFICALLY_VIDEO_MODEL", DEFAULT_UNIFICALLY_VIDEO_MODEL).strip() or DEFAULT_UNIFICALLY_VIDEO_MODEL


def get_unifically_poll_interval_seconds() -> float:
    return _positive_float_env("UNIFICALLY_POLL_INTERVAL_SECONDS", DEFAULT_UNIFICALLY_POLL_INTERVAL_SECONDS)


def get_unifically_poll_timeout_seconds() -> float:
    return _positive_float_env("UNIFICALLY_POLL_TIMEOUT_SECONDS", DEFAULT_UNIFICALLY_POLL_TIMEOUT_SECONDS)


def get_unifically_seed() -> int | None:
    raw = os.getenv("SMART_REMAKE_UNIFICALLY_SEED", "").strip()
    if not raw:
        return None
    try:
        value = int(raw)
    except ValueError:
        return None
    return value if value >= 0 else None


def use_unifically_scene_reference() -> bool:
    return _bool_env("SMART_REMAKE_UNIFICALLY_SCENE_REFERENCE", False)


def is_unifically_configured() -> bool:
    return bool(get_unifically_api_key())


def get_public_base_url() -> str:
    return os.getenv("PUBLIC_BASE_URL", "http://127.0.0.1:8000").rstrip("/")


def get_r2_config() -> dict[str, str]:
    return {
        "account_id": os.getenv("ACCOUNT_ID", "").strip(),
        "access_key_id": os.getenv("R2_ACCESS_KEY_ID", "").strip(),
        "secret_access_key": os.getenv("R2_SECRET_ACCESS_KEY", "").strip(),
        "bucket": os.getenv("R2_BUCKET", "").strip(),
        "public_base_url": os.getenv("R2_PUBLIC_BASE_URL", "").strip().rstrip("/"),
    }


def is_r2_configured() -> bool:
    config = get_r2_config()
    return all(config.values())
