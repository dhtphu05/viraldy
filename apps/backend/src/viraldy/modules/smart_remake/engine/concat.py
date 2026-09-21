import functools
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Protocol

import httpx

from .errors import SmartRemakeError
from .media_binaries import ffmpeg_path


class SceneProvider(Protocol):
    async def list_scenes(self, video_id: str) -> list[dict[str, Any]]:
        ...


async def _fetch_scene_video_bytes(url: str, index: int) -> bytes:
    """Read a scene video from FlowKit. FlowKit may return an HTTP(S) URL
    (remote media) or a local `file://` path / bare filesystem path when it
    downloads Flow output to disk on the same host."""
    if url.startswith(("http://", "https://")):
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(url)
        if response.status_code >= 400:
            raise SmartRemakeError(f"Could not download Smart Remake scene {index}.", "SMART_REMAKE_CONCAT_FAILED")
        return response.content

    local_path = url[len("file://"):] if url.startswith("file://") else url
    try:
        return Path(local_path).read_bytes()
    except OSError as exc:
        raise SmartRemakeError(
            f"Could not read Smart Remake scene {index} from local path.",
            "SMART_REMAKE_CONCAT_FAILED",
            {"path": local_path, "cause": str(exc)},
        ) from exc


FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/Library/Fonts/Arial.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
]


async def concat_flowkit_video(
    *,
    flowkit: SceneProvider,
    video_id: str,
    orientation: str = "VERTICAL",
    title: str = "smart_remake",
    text_overlays: list[dict[str, Any]] | None = None,
) -> bytes:
    scenes = await flowkit.list_scenes(video_id)
    sorted_scenes = sorted(scenes, key=lambda item: int(item.get("display_order", 0)))
    return await concat_scene_video_records(
        sorted_scenes,
        orientation=orientation,
        title=title,
        text_overlays=text_overlays,
    )


async def concat_video_urls(
    *,
    video_urls: list[str],
    orientation: str = "VERTICAL",
    title: str = "smart_remake",
    text_overlays: list[dict[str, Any]] | None = None,
) -> bytes:
    scenes = [
        {
            "display_order": index,
            "vertical_video_url": url,
        }
        for index, url in enumerate(video_urls)
    ]
    return await concat_scene_video_records(
        scenes,
        orientation=orientation,
        title=title,
        text_overlays=text_overlays,
    )


async def concat_scene_video_records(
    scenes: list[dict[str, Any]],
    *,
    orientation: str = "VERTICAL",
    title: str = "smart_remake",
    text_overlays: list[dict[str, Any]] | None = None,
) -> bytes:
    sorted_scenes = sorted(scenes, key=lambda item: int(item.get("display_order", 0)))
    prefix = "vertical" if orientation == "VERTICAL" else "horizontal"
    width, height = (720, 1280) if orientation == "VERTICAL" else (1280, 720)
    ffmpeg = ffmpeg_path()
    overlays = text_overlays or []

    with tempfile.TemporaryDirectory(prefix="smart-remake-concat-") as tmp:
        tmp_dir = Path(tmp)
        norm_files: list[Path] = []
        for index, scene in enumerate(sorted_scenes):
            url = scene.get(f"{prefix}_video_url")
            if not isinstance(url, str) or not url:
                continue
            raw_path = tmp_dir / f"raw_{index}.mp4"
            norm_path = tmp_dir / f"norm_{index}.mp4"
            raw_path.write_bytes(await _fetch_scene_video_bytes(url, index))

            trim_args: list[str] = []
            trim_start = scene.get("trim_start")
            trim_end = scene.get("trim_end")
            if isinstance(trim_start, (int, float)) and trim_start > 0:
                trim_args += ["-ss", str(trim_start)]
            duration = None
            if isinstance(trim_start, (int, float)) and isinstance(trim_end, (int, float)) and trim_end > trim_start:
                duration = trim_end - trim_start
            if duration:
                trim_args += ["-t", str(duration)]

            vf = _video_filter(width, height, _overlay_for_scene(overlays, scene), scene.get("display_order", index))
            subprocess.run(
                [
                    ffmpeg,
                    "-y",
                    *trim_args,
                    "-i",
                    str(raw_path),
                    "-c:v",
                    "libx264",
                    "-preset",
                    "fast",
                    "-crf",
                    "18",
                    "-vf",
                    vf,
                    "-r",
                    "24",
                    "-pix_fmt",
                    "yuv420p",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "192k",
                    "-movflags",
                    "+faststart",
                    str(norm_path),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            norm_files.append(norm_path)

        if not norm_files:
            raise SmartRemakeError("No scenes with video available for concatenation.", "SMART_REMAKE_CONCAT_FAILED")

        list_path = tmp_dir / "list.txt"
        list_path.write_text("".join(f"file '{_ffmpeg_concat_path(path)}'\n" for path in norm_files), encoding="utf-8")
        final_path = tmp_dir / f"{_slug(title)}_final.mp4"
        subprocess.run(
            [
                ffmpeg,
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(list_path),
                "-c",
                "copy",
                "-movflags",
                "+faststart",
                str(final_path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        return final_path.read_bytes()


def _overlay_for_scene(overlays: list[dict[str, Any]], scene: dict[str, Any]) -> dict[str, Any] | None:
    display_order = scene.get("display_order")
    for overlay in overlays:
        if overlay.get("displayOrder") == display_order or overlay.get("display_order") == display_order:
            return overlay
    return None


def _video_filter(width: int, height: int, overlay: dict[str, Any] | None, display_order: Any) -> str:
    base = f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2"
    text = overlay.get("text") if overlay else None
    if not isinstance(text, str) or not text.strip():
        return base
    position = overlay.get("position") if overlay else None
    if position not in {"top", "center", "bottom"}:
        position = "top" if display_order == 0 else "center"
    drawtext = _drawtext_filter(text, position, width, height)
    return f"{base},{drawtext}" if drawtext else base


@functools.lru_cache(maxsize=1)
def _drawtext_available() -> bool:
    """Whether the local ffmpeg build ships the drawtext filter (needs
    libfreetype). Homebrew-core ffmpeg omits it, so text overlays must
    degrade to a no-op rather than crashing an already-rendered video."""
    try:
        result = subprocess.run(
            [ffmpeg_path(), "-hide_banner", "-filters"],
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception:
        return False
    return "drawtext" in result.stdout


def _drawtext_filter(text: str, position: str, width: int, height: int) -> str:
    if not _drawtext_available():
        return ""
    lines = [line.strip() for line in text.replace("\r", "\n").split("\n") if line.strip()]
    if not lines:
        return ""
    font_size = round(width * 0.068)
    line_gap = round(font_size * 1.5)
    padding = round(height * 0.055)
    box_pad = round(font_size * 0.25)
    font = _font_file()
    font_part = f":fontfile='{font}'" if font else ""
    filters = []
    for index, line in enumerate(lines):
        if position == "bottom":
            y = f"h-text_h-{(len(lines) - 1 - index) * line_gap + padding}"
        elif position == "top":
            y = str(padding + index * line_gap)
        else:
            y = f"(h-{len(lines) * line_gap})/2+{index * line_gap}"
        color = "#FF3B30" if re.search(r"\bnow\b[\s\S]{0,6}[\d.]+", line, re.I) else "white"
        filters.append(
            "drawtext="
            f"text='{_escape_drawtext(line)}'"
            f"{font_part}:fontcolor={color}:fontsize={font_size}:x=(w-text_w)/2:y={y}"
            f":shadowcolor=black@0.85:shadowx=2:shadowy=2:box=1:boxcolor=black@0.5:boxborderw={box_pad}"
        )
    return ",".join(filters)


def _font_file() -> str:
    return next((font for font in FONT_CANDIDATES if os.path.exists(font)), "")


def _escape_drawtext(text: str) -> str:
    return (
        re.sub(r"[\U0001F000-\U0001FFFF\u2600-\u27BF]", "", text)
        .replace("\\", "\\\\")
        .replace("'", "\\'")
        .replace(":", "\\:")
        .replace("[", "\\[")
        .replace("]", "\\]")
        .replace("$", "\\$")
        .replace("!", "\\!")
        .strip()
    )


def _ffmpeg_concat_path(path: Path) -> str:
    return str(path).replace("'", "'\\''")


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_") or "smart_remake"
