import os
import shutil
from pathlib import Path

from .errors import SmartRemakeError


FFMPEG_CANDIDATES = [
    "/opt/homebrew/bin/ffmpeg",
    "/usr/local/bin/ffmpeg",
    "/usr/bin/ffmpeg",
]

FFPROBE_CANDIDATES = [
    "/opt/homebrew/bin/ffprobe",
    "/usr/local/bin/ffprobe",
    "/usr/bin/ffprobe",
]


def ffmpeg_path() -> str:
    return _binary_path(
        "ffmpeg",
        env_names=("SMART_REMAKE_FFMPEG_PATH", "FFMPEG_PATH"),
        candidates=FFMPEG_CANDIDATES,
    )


def ffprobe_path() -> str:
    return _binary_path(
        "ffprobe",
        env_names=("SMART_REMAKE_FFPROBE_PATH", "FFPROBE_PATH"),
        candidates=FFPROBE_CANDIDATES,
    )


def _binary_path(name: str, *, env_names: tuple[str, ...], candidates: list[str]) -> str:
    for env_name in env_names:
        configured = os.getenv(env_name, "").strip()
        if configured and Path(configured).exists():
            return configured

    resolved = shutil.which(name)
    if resolved:
        return resolved

    for candidate in candidates:
        if Path(candidate).exists():
            return candidate

    raise SmartRemakeError(
        f"{name} is required for Smart Remake rendering but was not found.",
        "SMART_REMAKE_MEDIA_BINARY_MISSING",
        {"binary": name, "env": list(env_names), "candidates": candidates},
    )
