"""Original test assets; no seller uploads, demo-media or remote downloads."""

from __future__ import annotations

import hashlib
import json
import math
import struct
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw

from viraldy.modules.smart_remake.engine.media_binaries import ffmpeg_path


def generate_media(root: Path) -> dict[str, Path]:
    root.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    # A marker appears and audio volume changes at four seconds, so
    # trims can be checked using actual decoded pixels/audio rather than metadata.
    for name, duration, color, frequency in (
        ("source", 20, "orange", 330),
        ("clip-0", 8, "orange", 440),
        ("clip-1", 8, "orange", 660),
        ("bad-group", 8, "orange", 440),
        ("repair", 8, "orange", 880),
    ):
        target = root / f"{name}.mp4"
        video_filter = (
            f"drawbox=x=60:y=100:w=60:h=100:color={color}:t=fill,"
            "drawbox=x=10:y=10:w=24:h=24:color=white:t=fill:enable='gte(t,4)'"
        )
        if name == "bad-group":
            video_filter += ",drawbox=x=60:y=100:w=60:h=100:color=blue:t=fill:enable='lt(t,2)'"
        subprocess.run(  # noqa: S603 - fixed argv, generated primitives and pytest-owned path
            [
                ffmpeg_path(),
                "-y",
                "-f",
                "lavfi",
                "-i",
                f"color=c=0x26334d:s=180x320:r=24:d={duration}",
                "-f",
                "lavfi",
                "-i",
                f"sine=frequency={frequency}:r=48000:d={duration}",
                "-vf",
                video_filter,
                "-af",
                "volume=0.1:enable='lt(t,4)'",
                "-c:v",
                "libx264",
                "-preset",
                "ultrafast",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-shortest",
                str(target),
            ],
            check=True,
            capture_output=True,
            timeout=30,
        )
        paths[name] = target
    product = Image.new("RGB", (180, 320), "#26334d")
    ImageDraw.Draw(product).rectangle((60, 100, 120, 200), fill="orange")
    product_path = root / "product.png"
    product.save(product_path)
    paths["product"] = product_path
    conditioning = root / "conditioning.png"
    product.resize((720, 1280)).save(conditioning)
    paths["conditioning"] = conditioning
    manifest = {
        "schemaVersion": 1,
        "mode": "fixture",
        "character": None,
        "rights": {
            "basis": "owned",
            "scope": "Internal offline QA only",
            "evidenceNote": "Generated locally from FFmpeg lavfi and Pillow primitives.",
        },
        "assets": {
            name: {"path": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
            for name, path in paths.items()
        },
    }
    paths["manifest"] = root / "rights-manifest.json"
    paths["manifest"].write_text(json.dumps(manifest, indent=2) + "\n")
    return paths


def assert_export_pixels_and_audio(path: Path, duration: int) -> None:
    """Independent decode checks: policy overlay pixels and the selected audio clock."""
    from io import BytesIO

    for second in (0, duration / 2, duration - 1 / 24):
        result = subprocess.run(  # noqa: S603 - fixed argv and pytest-owned export
            [
                ffmpeg_path(),
                "-v",
                "error",
                "-ss",
                str(second),
                "-i",
                str(path),
                "-frames:v",
                "1",
                "-vf",
                "crop=iw/2:ih/8:iw/2:7*ih/8",
                "-f",
                "image2pipe",
                "-c:v",
                "png",
                "pipe:1",
            ],
            check=True,
            capture_output=True,
            timeout=30,
        )
        with Image.open(BytesIO(result.stdout)) as frame:
            pixels = list(frame.convert("RGB").get_flattened_data())
        # This fixture has no white or black content in the bottom-right region.
        # White glyphs on the black disclosure panel must exist in encoded bytes.
        assert sum(min(pixel) > 215 for pixel in pixels) > 10, "AI label glyph pixels missing"
        assert sum(max(pixel) < 25 for pixel in pixels) > 30, "AI label backing pixels missing"
    if duration == 8:
        rms = []
        for second in (0.5, 3):
            result = subprocess.run(  # noqa: S603 - fixed argv and pytest-owned export
                [
                    ffmpeg_path(),
                    "-v",
                    "error",
                    "-ss",
                    str(second),
                    "-i",
                    str(path),
                    "-t",
                    "0.2",
                    "-vn",
                    "-ac",
                    "1",
                    "-ar",
                    "48000",
                    "-f",
                    "f32le",
                    "pipe:1",
                ],
                check=True,
                capture_output=True,
                timeout=30,
            )
            samples = struct.unpack(f"<{len(result.stdout) // 4}f", result.stdout)
            assert samples, "Audio disappeared from the selected export"
            rms.append(math.sqrt(sum(sample * sample for sample in samples) / len(samples)))
        assert rms[0] > rms[1] * 5, "Audio did not follow the reviewed 5s/1s raw clip trims"
