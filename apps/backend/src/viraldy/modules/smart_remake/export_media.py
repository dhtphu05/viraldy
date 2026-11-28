"""Local, verified AI disclosure burn-in for a reviewed video export."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from viraldy.shared.errors.base import AppError

from .engine.concat import FONT_CANDIDATES
from .engine.media_binaries import ffmpeg_path
from .engine.media_probe import probe_media_bytes
from .repair_media import technical_check
from .timeline_media import FPS, probe_timeline_media

LABEL = "AI-generated"
POLICY_VERSION = "smart-remake-ai-label-v1"


def _validate_media(
    data: bytes, *, expected_frames: int, audio_required: bool
) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        check = technical_check(
            data, expected_duration=expected_frames // FPS, audio_required=audio_required
        )
        info = probe_timeline_media(data)
        dimensions = probe_media_bytes(data)
        if (
            check["status"] != "passed"
            or info["frameCount"] != expected_frames
            or info["decodedFrameCount"] != expected_frames
            or info["fps"] != FPS
            or dimensions["effectiveWidth"] * 16 != dimensions["effectiveHeight"] * 9
        ):
            raise ValueError("Media does not match the reviewed frame contract.")
    except (AppError, OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        raise AppError(
            "SMART_REMAKE_EXPORT_CHECK_FAILED",
            "The export must match the reviewed duration, 24 fps, 9:16 dimensions and audio.",
        ) from exc
    return {**check, **info}, dimensions


def _label_image(width: int, height: int) -> tuple[Image.Image, int, int]:
    """Generate only the fixed policy text; no client text reaches the filter."""
    font_path = next((font for font in FONT_CANDIDATES if Path(font).is_file()), None)
    if not font_path:
        raise AppError(
            "SMART_REMAKE_AI_LABEL_UNAVAILABLE", "The AI disclosure font is unavailable."
        )
    margin, padding = max(4, round(width * 0.02)), max(3, round(width * 0.01))
    try:
        size = max(10, round(width * 0.04))
        font = ImageFont.truetype(font_path, size)
        while font.getlength(LABEL) + padding * 2 > width - margin * 2 and size > 8:
            size -= 1
            font = ImageFont.truetype(font_path, size)
        bounds = font.getbbox(LABEL)
        label_width = int((bounds[2] - bounds[0] + padding * 2 + 1) // 2) * 2
        label_height = int((bounds[3] - bounds[1] + padding * 2 + 1) // 2) * 2
        if label_width > width - margin * 2 or label_height > height - margin * 2:
            raise ValueError("Video is too small for a readable AI disclosure.")
        label = Image.new("RGB", (label_width, label_height), "black")
        ImageDraw.Draw(label).text(
            (padding - bounds[0], padding - bounds[1]), LABEL, font=font, fill="white"
        )
    except (OSError, ValueError) as exc:
        raise AppError(
            "SMART_REMAKE_AI_LABEL_UNAVAILABLE", "The AI disclosure could not be rendered."
        ) from exc
    # Even coordinates preserve the raster position through YUV420 encoding.
    return (
        label,
        ((width - label_width - margin) // 2) * 2,
        ((height - label_height - margin) // 2) * 2,
    )


def _verify_label(
    target: Path, label: Image.Image, x: int, y: int, frames: list[int]
) -> dict[str, Any]:
    width, height = label.size
    selection = "+".join(f"eq(n\\,{frame})" for frame in frames)
    decoded = subprocess.run(  # noqa: S603 - fixed filters and generated local paths
        [
            ffmpeg_path(),
            "-v",
            "error",
            "-i",
            str(target),
            "-vf",
            f"select={selection},crop={width}:{height}:{x}:{y}",
            "-frames:v",
            str(len(frames)),
            "-fps_mode",
            "passthrough",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "gray",
            "pipe:1",
        ],
        check=True,
        capture_output=True,
        timeout=120,
    ).stdout
    template = label.convert("L").tobytes()
    frame_size = len(template)
    if len(decoded) != frame_size * len(frames) or any(
        sum(
            (actual - expected) ** 2
            for actual, expected in zip(
                decoded[offset : offset + frame_size], template, strict=True
            )
        )
        / frame_size
        > 400
        for offset in range(0, len(decoded), frame_size)
    ):
        raise AppError(
            "SMART_REMAKE_AI_LABEL_VERIFICATION_FAILED",
            "The encoded export did not retain the visible AI disclosure.",
        )
    return {"method": "decoded-overlay-template", "sampledFrames": frames, "verified": True}


def export_labeled_media(
    data: bytes, *, expected_frames: int, audio_required: bool
) -> tuple[bytes, dict[str, Any]]:
    """Burn in the disclosure and prove the output still matches its reviewed media."""
    if type(expected_frames) is not int or expected_frames not in (192, 288, 384):
        raise AppError(
            "SMART_REMAKE_EXPORT_CHECK_FAILED", "Export duration must be 8, 12 or 16 seconds."
        )
    _, dimensions = _validate_media(
        data, expected_frames=expected_frames, audio_required=audio_required
    )
    label, x, y = _label_image(dimensions["effectiveWidth"], dimensions["effectiveHeight"])
    with tempfile.TemporaryDirectory(prefix="smart-remake-ai-export-") as tmp:
        source, overlay, target = (
            Path(tmp) / name for name in ("source.mp4", "label.png", "ai.mp4")
        )
        source.write_bytes(data)
        label.save(overlay)
        try:
            subprocess.run(  # noqa: S603 - fixed policy overlay and generated local paths
                [
                    ffmpeg_path(),
                    "-v",
                    "error",
                    "-y",
                    "-i",
                    str(source),
                    "-i",
                    str(overlay),
                    "-filter_complex",
                    f"[0:v:0][1:v:0]overlay={x}:{y}:eof_action=repeat[v]",
                    "-map",
                    "[v]",
                    "-map",
                    "0:a:0?",
                    "-frames:v",
                    str(expected_frames),
                    "-c:v",
                    "libx264",
                    "-preset",
                    "fast",
                    "-crf",
                    "18",
                    "-pix_fmt",
                    "yuv420p",
                    "-c:a",
                    "copy",
                    "-movflags",
                    "+faststart",
                    str(target),
                ],
                check=True,
                capture_output=True,
                timeout=180,
            )
            output = target.read_bytes()
            check, _ = _validate_media(
                output, expected_frames=expected_frames, audio_required=audio_required
            )
            verification = _verify_label(
                target, label, x, y, [0, expected_frames // 2, expected_frames - 1]
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise AppError(
                "SMART_REMAKE_AI_LABEL_UNAVAILABLE", "The labeled export could not be encoded."
            ) from exc
    return output, {
        **check,
        "label": LABEL,
        "policyVersion": POLICY_VERSION,
        "labelVerification": verification,
    }
