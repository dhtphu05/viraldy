"""Temporary, exact-frame observation extraction. No persistence or remote calls."""

from __future__ import annotations

import hashlib
import subprocess
import tempfile
from io import BytesIO
from pathlib import Path
from typing import Literal, cast

from PIL import Image

from ..engine.media_binaries import ffmpeg_path
from ..engine.media_probe import probe_media_bytes
from ..timeline_media import probe_timeline_media
from .contracts import ModelImage, Observation, ResolvedMedia, Timebase


def select_frames(
    start: int, end: int, limit: int, *, mandatory: list[int] | None = None
) -> list[int]:
    """Retain real endpoints and required anchors without exceeding the declared ceiling."""
    if (
        type(start) is not int
        or type(end) is not int
        or type(limit) is not int
        or start < 0
        or end <= start
        or limit < 1
    ):
        raise ValueError("Sampling requires an integer nonempty range and positive capacity.")
    size = end - start
    anchors = {start, end - 1, *(mandatory or [])}
    if any(type(frame) is not int or not start <= frame < end for frame in anchors):
        raise ValueError("Mandatory evidence must be inside the selected range.")
    if len(anchors) > limit:
        raise ValueError("Required evidence anchors exceed the observation capacity.")
    if size <= limit:
        return list(range(start, end))
    candidates = [start + (size - 1) * index // (limit - 1) for index in range(limit)]
    selected = set(anchors)
    for frame in candidates:
        if len(selected) == limit:
            break
        selected.add(frame)
    return sorted(selected)


def _image_bytes(
    data: bytes, max_long_edge: int
) -> tuple[bytes, Literal["image/jpeg", "image/png", "image/webp"]]:
    with Image.open(BytesIO(data)) as image:
        image.load()
        if max(image.size) <= max_long_edge and image.format in {"PNG", "JPEG", "WEBP"}:
            mime = {"PNG": "image/png", "JPEG": "image/jpeg", "WEBP": "image/webp"}[image.format]
            return data, cast(Literal["image/jpeg", "image/png", "image/webp"], mime)
        output = image.convert("RGB")
        output.thumbnail((max_long_edge, max_long_edge), Image.Resampling.LANCZOS)
        stream = BytesIO()
        output.save(stream, format="JPEG", quality=88, optimize=True)
        return stream.getvalue(), "image/jpeg"


def image_observation(
    media: ResolvedMedia, *, max_long_edge: int
) -> tuple[Observation, ModelImage]:
    data, mime = _image_bytes(media.bytes, max_long_edge)
    observation_id = f"ref-{media.id}"
    observation = Observation(
        id=observation_id,
        mediaId=media.id,
        mediaHash=media.mediaHash,
        imageHash=hashlib.sha256(data).hexdigest(),
        mimeType=mime,
    )
    return observation, ModelImage(observationId=observation_id, mimeType=mime, data=data)


def video_observations(
    media: ResolvedMedia, frames: list[int], *, timebase: Timebase, max_long_edge: int
) -> tuple[list[Observation], list[ModelImage]]:
    """Normalize to the canonical clock, then select exact frame indices in one decode."""
    if (
        not frames
        or frames != sorted(set(frames))
        or any(
            type(frame) is not int or frame < 0 or frame >= (media.frameCount or 0)
            for frame in frames
        )
    ):
        raise ValueError("Video observations must be unique valid canonical frame indices.")
    with tempfile.TemporaryDirectory(prefix="smart-remake-inspection-") as tmp:
        directory = Path(tmp)
        source = directory / "owned-input"
        source.write_bytes(media.bytes)
        expression = "+".join(f"eq(n\\,{frame})" for frame in frames)
        filters = (
            f"fps=24,select={expression},"
            f"scale=w='min({max_long_edge},iw)':h='min({max_long_edge},ih)'"
            ":force_original_aspect_ratio=decrease"
        )
        subprocess.run(  # noqa: S603 - fixed executable and local generated paths, no shell
            [
                ffmpeg_path(),
                "-v",
                "error",
                "-y",
                "-i",
                str(source),
                "-vf",
                filters,
                "-vsync",
                "vfr",
                "-frames:v",
                str(len(frames)),
                "-q:v",
                "3",
                str(directory / "frame-%03d.jpg"),
            ],
            check=True,
            capture_output=True,
            timeout=120,
        )
        outputs = sorted(directory.glob("frame-*.jpg"))
        if len(outputs) != len(frames):
            raise ValueError("Decoding did not produce every required observation frame.")
        observations, images = [], []
        for frame, output in zip(frames, outputs, strict=True):
            data = output.read_bytes()
            identity = f"{media.id}-frame-{frame}"
            observations.append(
                Observation(
                    id=identity,
                    mediaId=media.id,
                    mediaHash=media.mediaHash,
                    inFrame=frame,
                    outFrame=frame + 1,
                    timebase=timebase,
                    imageHash=hashlib.sha256(data).hexdigest(),
                    mimeType="image/jpeg",
                )
            )
            images.append(ModelImage(observationId=identity, mimeType="image/jpeg", data=data))
        return observations, images


def technical_problem(
    media: ResolvedMedia, *, kind: str, retained_status: str | None
) -> str | None:
    if retained_status is not None and retained_status != "passed":
        return "The retained technical check has not passed."
    if media.mimeType.startswith("image/"):
        with Image.open(BytesIO(media.bytes)) as image:
            image.load()
        return None
    info = probe_timeline_media(media.bytes)
    dimensions = probe_media_bytes(media.bytes)
    width = dimensions.get("effectiveWidth") or 0
    height = dimensions.get("effectiveHeight") or 0
    if not height or abs(width / height - 9 / 16) > 0.02:
        return "Output must have a 9:16 aspect ratio."
    if info["fps"] != 24 or info["frameCount"] != media.frameCount:
        return "Output must retain its exact decoded 24-fps frame clock."
    if kind == "assembly" and info["decodedFrameCount"] not in {192, 384}:
        return "Final MP4 must contain exactly 192 or 384 frames."
    return None
