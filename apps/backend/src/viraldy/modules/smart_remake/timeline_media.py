"""Frame-based local assembly. This module never submits AI generation."""

from __future__ import annotations

import hashlib
import json
import math
import subprocess
import tempfile
from pathlib import Path
from typing import Any, cast

from starlette.concurrency import run_in_threadpool

from viraldy.shared.errors.base import AppError

from .engine.media_binaries import ffmpeg_path, ffprobe_path
from .repair_media import technical_check

FPS = 24


def probe_timeline_media(data: bytes) -> dict[str, Any]:
    """Count decoded frames; duration tolerance alone cannot prove trim bounds."""
    with tempfile.TemporaryDirectory(prefix="smart-remake-frame-probe-") as tmp:
        path = Path(tmp) / "clip.mp4"
        path.write_bytes(data)
        result = subprocess.run(  # noqa: S603 - fixed executable, generated paths, no shell
            [
                ffprobe_path(),
                "-v",
                "error",
                "-count_frames",
                "-show_streams",
                "-show_format",
                "-of",
                "json",
                str(path),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=120,
        )
    info = json.loads(result.stdout)
    video: dict[str, Any] = next((s for s in info["streams"] if s.get("codec_type") == "video"), {})
    try:
        numerator, denominator = str(video["avg_frame_rate"]).split("/")
        fps = float(numerator) / float(denominator)
        decoded = int(video["nb_read_frames"])
        duration = float(video.get("duration") or info["format"]["duration"])
        frame_count = min(math.floor(duration * FPS + 1e-5), math.floor(decoded * FPS / fps + 1e-5))
        if frame_count < 1 or fps <= 0:
            raise ValueError("Missing video frames")
    except (KeyError, TypeError, ValueError, ZeroDivisionError) as exc:
        raise AppError("SMART_REMAKE_MEDIA_UNREADABLE", "Could not count the clip frames.") from exc
    return {
        "frameCount": frame_count,
        "decodedFrameCount": decoded,
        "fps": fps,
        "hasAudio": any(s.get("codec_type") == "audio" for s in info["streams"]),
    }


def validate_trim(item: dict[str, Any], frame_count: int) -> None:
    start, end, length = item["inFrame"], item["outFrame"], item["targetDurationFrames"]
    if (
        type(start) is not int
        or type(end) is not int
        or start < 0
        or end - start != length
        or end > frame_count
    ):
        raise AppError(
            "SMART_REMAKE_TRIM_INVALID",
            "The selected range must fit this clip and keep the planned duration.",
        )


async def selection_bytes(service: Any, state: dict[str, Any], item: dict[str, Any]) -> bytes:
    from .repair_service import _scene, _version

    version = _version(_scene(state, item["renderUnitId"]), item["versionId"])
    if version["technicalCheck"]["status"] != "passed":
        raise AppError("SMART_REMAKE_TECHNICAL_CHECK_FAILED", "The selected clip is not ready.")
    data = await service.media.read(version["storageKey"])
    if hashlib.sha256(data).hexdigest() != version["mediaHash"]:
        raise AppError(
            "SMART_REMAKE_MEDIA_CHANGED", "The retained clip no longer matches its version."
        )
    info = await run_in_threadpool(probe_timeline_media, data)
    validate_trim(item, info["frameCount"])
    return cast(bytes, data)


async def validate_selection_media(
    service: Any, state: dict[str, Any], item: dict[str, Any]
) -> None:
    await selection_bytes(service, state, item)


def _assemble(clips: list[bytes], items: list[dict[str, Any]]) -> bytes:
    with tempfile.TemporaryDirectory(prefix="smart-remake-timeline-") as tmp:
        folder = Path(tmp)
        normalized = []
        for index, (data, item) in enumerate(zip(clips, items, strict=True)):
            source, output = folder / f"raw-{index}.mp4", folder / f"part-{index}.mp4"
            source.write_bytes(data)
            info = probe_timeline_media(data)
            start, end = item["inFrame"], item["outFrame"]
            video_filter = (
                f"[0:v:0]fps=24,trim=start_frame={start}:end_frame={end},"
                "setpts=PTS-STARTPTS,scale=720:1280:force_original_aspect_ratio=decrease,"
                "pad=720:1280:(ow-iw)/2:(oh-ih)/2,setsar=1[v];"
            )
            audio_input = "[0:a:0]" if info["hasAudio"] else "[1:a:0]"
            audio_filter = (
                f"{audio_input}atrim=start={start/FPS:.9f}:end={end/FPS:.9f},"
                "asetpts=PTS-STARTPTS,aresample=48000[a]"
            )
            argv = [ffmpeg_path(), "-v", "error", "-y", "-i", str(source)]
            if not info["hasAudio"]:
                argv += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]
            argv += [
                "-filter_complex",
                video_filter + audio_filter,
                "-map",
                "[v]",
                "-map",
                "[a]",
                "-frames:v",
                str(end - start),
                "-c:v",
                "libx264",
                "-preset",
                "fast",
                "-crf",
                "18",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-ar",
                "48000",
                "-ac",
                "2",
                "-movflags",
                "+faststart",
                str(output),
            ]
            subprocess.run(argv, check=True, capture_output=True, timeout=180)  # noqa: S603
            normalized.append(output)
        listing = folder / "concat.txt"
        listing.write_text("".join(f"file '{p.name}'\n" for p in normalized))
        target = folder / "final.mp4"
        subprocess.run(  # noqa: S603 - controlled generated file names
            [
                ffmpeg_path(),
                "-v",
                "error",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(listing),
                "-c",
                "copy",
                "-movflags",
                "+faststart",
                str(target),
            ],
            check=True,
            capture_output=True,
            timeout=180,
        )
        return target.read_bytes()


async def compose_timeline(
    service: Any, row: Any, timeline: dict[str, Any]
) -> tuple[bytes, dict[str, Any]]:
    clips = [await selection_bytes(service, row.state_json, item) for item in timeline["items"]]
    output = await run_in_threadpool(_assemble, clips, timeline["items"])
    check = await run_in_threadpool(
        technical_check,
        output,
        expected_duration=timeline["totalFrames"] // FPS,
        audio_required=row.context_json["audioRequired"],
    )
    info = await run_in_threadpool(probe_timeline_media, output)
    check["frameCount"] = info["frameCount"]
    if (
        info["decodedFrameCount"] != timeline["totalFrames"]
        or info["fps"] != FPS
        or check["status"] != "passed"
    ):
        raise AppError(
            "SMART_REMAKE_ASSEMBLY_CHECK_FAILED",
            "The assembled video does not match the reviewed timeline.",
        )
    return output, check
