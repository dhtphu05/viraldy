import os
from pathlib import Path

from viraldy.modules.smart_remake.runtime_paths import RENDERS_DIR

from .config import get_public_base_url, get_r2_config, is_r2_configured
from .errors import SmartRemakeError, SmartRemakeValidationError


def _safe_part(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in "_-" else "_" for ch in value).strip("_")
    return cleaned or "unknown"


def _local_save(key: str, data: bytes) -> tuple[Path, str]:
    filename = Path(key).name
    final_path = RENDERS_DIR / filename
    tmp_path = RENDERS_DIR / f".{filename}.{os.getpid()}.tmp"
    RENDERS_DIR.mkdir(parents=True, exist_ok=True)
    tmp_path.write_bytes(data)
    tmp_path.replace(final_path)
    return final_path, f"{get_public_base_url()}/outputs/renders/{filename}"


def save_smart_remake_output(project_id: str, video_id: str, data: bytes) -> tuple[Path | None, str]:
    if not data:
        raise SmartRemakeValidationError("Smart Remake output video is empty.", "SMART_REMAKE_CONCAT_FAILED")

    filename = f"smart_remake_{_safe_part(project_id)}_{_safe_part(video_id)}.mp4"
    key = f"smart-remake/{filename}"
    if is_r2_configured():
        try:
            return _r2_save(key, data)
        except Exception as exc:
            # Local fallback keeps dev/staging usable if R2 is misconfigured, while
            # still surfacing the warning through logs for operators.
            print(f"[SmartRemakeStorage] R2 upload failed, falling back to local output: {exc}")
    return _local_save(filename, data)


def _r2_save(key: str, data: bytes) -> tuple[None, str]:
    try:
        import boto3
    except ImportError as exc:
        raise SmartRemakeError("boto3 is required for R2 uploads.", "SMART_REMAKE_STORAGE_FAILED") from exc

    config = get_r2_config()
    endpoint = f"https://{config['account_id']}.r2.cloudflarestorage.com"
    client = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=config["access_key_id"],
        aws_secret_access_key=config["secret_access_key"],
        region_name="auto",
    )
    client.put_object(
        Bucket=config["bucket"],
        Key=key,
        Body=data,
        ContentType="video/mp4",
        CacheControl="public, max-age=31536000, immutable",
    )
    return None, f"{config['public_base_url']}/{key}"
