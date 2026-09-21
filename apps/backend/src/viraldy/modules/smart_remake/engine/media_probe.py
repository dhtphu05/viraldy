import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from .media_binaries import ffprobe_path


def probe_media_file(path: Path) -> dict[str, Any]:
    proc = subprocess.run(
        [
            ffprobe_path(),
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_streams",
            "-show_format",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(proc.stdout or "{}")
    streams = payload.get("streams") if isinstance(payload.get("streams"), list) else []
    audio_streams = [stream for stream in streams if stream.get("codec_type") == "audio"]
    video_streams = [stream for stream in streams if stream.get("codec_type") == "video"]
    video_stream = video_streams[0] if video_streams else {}
    format_payload = payload.get("format") if isinstance(payload.get("format"), dict) else {}
    width = _integer(video_stream.get("width"))
    height = _integer(video_stream.get("height"))
    rotation = _rotation(video_stream)
    effective_width, effective_height = _effective_dimensions(width, height, rotation)
    return {
        "hasVideo": bool(video_streams),
        "hasAudio": bool(audio_streams),
        "durationSeconds": _number(format_payload.get("duration")) or _number(video_stream.get("duration")),
        "audioDurationSeconds": _number(audio_streams[0].get("duration")) if audio_streams else None,
        "width": width,
        "height": height,
        "rotation": rotation,
        "effectiveWidth": effective_width,
        "effectiveHeight": effective_height,
        "videoCodec": video_stream.get("codec_name"),
        "codec": video_stream.get("codec_name"),
        "videoFormat": format_payload.get("format_name"),
        "format": format_payload.get("format_name"),
        "pixelFormat": video_stream.get("pix_fmt"),
        "fps": _frame_rate(video_stream.get("avg_frame_rate") or video_stream.get("r_frame_rate")),
        "videoFps": _frame_rate(video_stream.get("avg_frame_rate") or video_stream.get("r_frame_rate")),
        "bitrate": _integer(
            video_stream.get("bit_rate")
            or format_payload.get("bit_rate")
        ),
        "videoBitrate": _number(video_stream.get("bit_rate")),
        "formatName": format_payload.get("format_name"),
        "formatSize": _number(format_payload.get("size")),
    }


def probe_media_bytes(data: bytes) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="smart-remake-probe-") as tmp:
        path = Path(tmp) / "input.mp4"
        path.write_bytes(data)
        return probe_media_file(path)


def _number(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _integer(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _frame_rate(value: Any) -> float | None:
    if isinstance(value, str) and "/" in value:
        numerator, denominator = value.split("/", 1)
        try:
            parsed = float(numerator) / float(denominator)
        except (TypeError, ValueError, ZeroDivisionError):
            return None
        return parsed if parsed > 0 else None
    return _number(value)


def _rotation(stream: dict[str, Any]) -> int:
    tags = stream.get("tags") if isinstance(stream.get("tags"), dict) else {}
    raw_rotation = tags.get("rotate", 0)
    for side_data in stream.get("side_data_list") or []:
        if isinstance(side_data, dict) and "rotation" in side_data:
            raw_rotation = side_data["rotation"]
    try:
        return int(round(float(raw_rotation))) % 360
    except (TypeError, ValueError):
        return 0


def _effective_dimensions(width: int | None, height: int | None, rotation: int) -> tuple[int | None, int | None]:
    if width is None or height is None:
        return None, None
    if rotation in (90, 270):
        return height, width
    return width, height
