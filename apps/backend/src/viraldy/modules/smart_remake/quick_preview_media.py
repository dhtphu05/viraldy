"""Small, bounded media for the optional loading observation, never for generation."""

from __future__ import annotations

import hashlib
import json
import math
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from viraldy.shared.errors.base import AppError

from .engine.media_binaries import ffmpeg_path, ffprobe_path
from .engine.schemas import UploadedMedia

MAX_PREVIEW_BYTES = 4 * 1024 * 1024
MAX_SOURCE_BYTES = 30 * 1024 * 1024
SAMPLE_COUNT = 6


@dataclass(frozen=True)
class QuickPreviewMedia:
    media: tuple[UploadedMedia, ...]
    kind: Literal["video_proxy", "sampled_frames"]
    has_audio: bool
    source_duration_seconds: float
    source_hash: str

    @property
    def metadata(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "sourceMediaHash": self.source_hash,
            "sourceDurationSeconds": self.source_duration_seconds,
            "hasAudio": self.has_audio,
            "byteLength": sum(len(item.bytes) for item in self.media),
            **({"sampleCount": len(self.media)} if self.kind == "sampled_frames" else {}),
        }


def _unavailable() -> AppError:
    return AppError(
        "SMART_REMAKE_QUICK_PREVIEW_UNAVAILABLE", "A small source preview could not be prepared."
    )


def _probe(path: Path) -> tuple[bool, bool]:
    result = subprocess.run(  # noqa: S603 - fixed binary/args, owned temporary media only
        [ffprobe_path(), "-v", "error", "-show_entries", "stream=codec_type", "-of", "json",
         str(path)],
        check=True, capture_output=True, timeout=2,
    )
    streams = json.loads(result.stdout)["streams"]
    return (
        any(item.get("codec_type") == "video" for item in streams),
        any(item.get("codec_type") == "audio" for item in streams),
    )


def _video_proxy(source: Path, target: Path, duration: float) -> bytes:
    subprocess.run(  # noqa: S603 - fixed binary/args, owned temporary media only
        [
            ffmpeg_path(), "-y", "-v", "error", "-i", str(source), "-t", str(duration),
            "-map", "0:v:0", "-map", "0:a:0?", "-map_metadata", "-1",
            "-vf", "setpts=PTS-STARTPTS,fps=2,scale=640:640:force_original_aspect_ratio=decrease:"
            "force_divisible_by=2,setsar=1",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "34", "-threads", "1",
            "-pix_fmt", "yuv420p", "-af", "asetpts=PTS-STARTPTS",
            "-c:a", "aac", "-b:a", "32k", "-ac", "1", "-ar", "16000",
            "-movflags", "+faststart", str(target),
        ],
        check=True, capture_output=True, timeout=8,
    )
    return target.read_bytes()


def _sample_frames(source: Path, directory: Path, duration: float) -> tuple[UploadedMedia, ...]:
    deadline = time.monotonic() + 6
    frames = []
    for index in range(SAMPLE_COUNT):
        second = duration * index / SAMPLE_COUNT
        target = directory / f"sample-{index}.jpg"
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise _unavailable()
        subprocess.run(  # noqa: S603 - fixed binary/args, owned temporary media only
            [
                ffmpeg_path(), "-y", "-v", "error", "-ss", str(second), "-i", str(source),
                "-frames:v", "1", "-vf",
                "scale=320:320:force_original_aspect_ratio=decrease:force_divisible_by=2",
                "-q:v", "5", "-map_metadata", "-1", "-threads", "1", str(target),
            ],
            check=True, capture_output=True, timeout=remaining,
        )
        data = target.read_bytes()
        if not data:
            raise _unavailable()
        frames.append(UploadedMedia(bytes=data, mime_type="image/jpeg"))
    if sum(len(frame.bytes) for frame in frames) > MAX_PREVIEW_BYTES:
        raise _unavailable()
    return tuple(frames)


def prepare_quick_preview(source: UploadedMedia, duration: float) -> QuickPreviewMedia:
    """Preserve the whole source clock/audio; image fallback never claims heard speech."""
    if (
        type(duration) not in {int, float} or not math.isfinite(duration) or duration <= 0
        or source.mime_type not in {"video/mp4", "video/quicktime", "video/webm"}
        or not 0 < len(source.bytes) <= MAX_SOURCE_BYTES
    ):
        raise _unavailable()
    source_hash = hashlib.sha256(source.bytes).hexdigest()
    try:
        with tempfile.TemporaryDirectory(prefix="smart-remake-quick-preview-") as temporary:
            directory = Path(temporary)
            original = directory / "source"
            original.write_bytes(source.bytes)
            has_video, has_audio = _probe(original)
            if not has_video:
                raise _unavailable()
            try:
                data = _video_proxy(original, directory / "preview.mp4", duration)
                if 0 < len(data) <= MAX_PREVIEW_BYTES:
                    return QuickPreviewMedia(
                        (UploadedMedia(bytes=data, mime_type="video/mp4"),),
                        "video_proxy", has_audio, duration, source_hash,
                    )
            except (OSError, subprocess.SubprocessError):
                pass  # Prepare image evidence before the sole optional model request.
            frames = _sample_frames(original, directory, duration)
            return QuickPreviewMedia(frames, "sampled_frames", False, duration, source_hash)
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, TypeError) as exc:
        raise _unavailable() from exc
