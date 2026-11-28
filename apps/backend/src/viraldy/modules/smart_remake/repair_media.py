from __future__ import annotations

import hashlib
import subprocess
import tempfile
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from starlette.concurrency import run_in_threadpool

from viraldy.platform.storage.ports import StoragePort
from viraldy.platform.storage.s3 import R2_OBJECT_MARKER

from .engine.media_binaries import ffmpeg_path
from .engine.media_probe import probe_media_bytes


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def technical_check(
    data: bytes,
    *,
    expected_duration: int,
    audio_required: bool,
    probe: Callable[[bytes], dict[str, Any]] = probe_media_bytes,
) -> dict[str, Any]:
    findings = []
    coverage = ["video_stream", "dimensions", "duration"]
    try:
        info = probe(data)
        if not info.get("hasVideo"):
            findings.append("Video stream is missing.")
        width = info.get("effectiveWidth") or info.get("width") or 0
        height = info.get("effectiveHeight") or info.get("height") or 0
        if not height or abs(width / height - 9 / 16) > 0.02:
            findings.append("Video dimensions must have a 9:16 aspect ratio.")
        duration = info.get("durationSeconds") or 0
        if abs(duration - expected_duration) > 0.5:
            findings.append(f"Video duration must be {expected_duration} seconds.")
        if audio_required:
            coverage.append("audio_stream")
            if not info.get("hasAudio"):
                findings.append("Required audio stream is missing.")
    except Exception:
        findings.append("Video could not be decoded for technical inspection.")
    return {
        "status": "failed" if findings else "passed",
        "findings": findings,
        "checkedAt": now_iso(),
        "mediaHash": hashlib.sha256(data).hexdigest(),
        "checkerVersion": "smart-remake-technical-v1",
        "coverage": coverage,
    }


def with_silent_audio(data: bytes) -> bytes:
    """Give silent scenes an audio track so concat preserves later scene audio."""
    with tempfile.TemporaryDirectory(prefix="smart-remake-silence-") as tmp:
        source, target = Path(tmp) / "input.mp4", Path(tmp) / "output.mp4"
        source.write_bytes(data)
        subprocess.run(  # noqa: S603 - fixed argv and generated local media paths; no shell
            [
                ffmpeg_path(),
                "-y",
                "-i",
                str(source),
                "-f",
                "lavfi",
                "-i",
                "anullsrc=channel_layout=stereo:sample_rate=48000",
                "-map",
                "0:v:0",
                "-map",
                "1:a:0",
                "-c:v",
                "copy",
                "-c:a",
                "aac",
                "-shortest",
                str(target),
            ],
            check=True,
            capture_output=True,
            timeout=120,
        )
        return target.read_bytes()


class RepairMediaStore:
    """All reads use server-owned object keys; client URLs are never accepted."""

    def __init__(self, storage: StoragePort) -> None:
        self.storage = storage

    async def put(self, prefix: str, data: bytes, mime_type: str) -> str:
        separator = (
            R2_OBJECT_MARKER
            if getattr(self.storage, "smart_remake_r2_enabled", False) is True
            else "/"
        )
        key = f"{prefix}{separator}{uuid4().hex}"
        with tempfile.TemporaryDirectory(prefix="smart-remake-store-") as tmp:
            path = Path(tmp) / "media"
            path.write_bytes(data)
            await run_in_threadpool(self.storage.upload_file, str(path), key, mime_type)
        return key

    async def read(self, key: str) -> bytes:
        with tempfile.TemporaryDirectory(prefix="smart-remake-read-") as tmp:
            path = Path(tmp) / "media"
            await run_in_threadpool(self.storage.download_object, key, str(path))
            return path.read_bytes()

    async def url(self, key: str) -> str:
        return await run_in_threadpool(self.storage.create_presigned_download, key)

    async def download_url(self, key: str, filename: str) -> str:
        return await run_in_threadpool(
            self.storage.create_presigned_download, key, filename=filename
        )
