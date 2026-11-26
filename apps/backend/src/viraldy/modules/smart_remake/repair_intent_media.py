"""Owned and hash-checked media for a single repair normalization call."""

from __future__ import annotations

import hashlib
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from starlette.concurrency import run_in_threadpool

from viraldy.shared.errors.base import AppError

from .engine.media_binaries import ffmpeg_path
from .generation_expectations import expectations_scene, require_generation_expectations
from .image_workflow import _references
from .timeline_media import probe_timeline_media, validate_trim


def trim_repair_evidence(data: bytes, start: int, end: int) -> bytes:
    with tempfile.TemporaryDirectory(prefix="smart-remake-repair-evidence-") as temporary:
        source, output = Path(temporary) / "clip", Path(temporary) / "range.mp4"
        source.write_bytes(data)
        subprocess.run(  # noqa: S603 - fixed executable, local generated paths, no shell
            [
                ffmpeg_path(),
                "-v",
                "error",
                "-y",
                "-i",
                str(source),
                "-vf",
                f"fps=24,trim=start_frame={start}:end_frame={end},setpts=PTS-STARTPTS",
                "-an",
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
                "-map_metadata",
                "-1",
                str(output),
            ],
            check=True,
            capture_output=True,
            timeout=120,
        )
        return output.read_bytes()


async def repair_evidence(
    repair: Any,
    row: Any,
    scene: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    product, opening = await _references(repair, row, scene["index"])
    snapshot = require_generation_expectations(row.context_json)
    binding = expectations_scene(snapshot, scene["id"])
    if (
        hashlib.sha256(product.bytes).hexdigest() != snapshot["references"]["product"]["mediaHash"]
        or hashlib.sha256(opening.bytes).hexdigest() != binding["openingFrame"]["layoutHash"]
    ):
        raise AppError("SMART_REMAKE_INPUT_CHANGED", "Tư liệu tham chiếu đã thay đổi.", 409)
    version = next(value for value in scene["versions"] if value["id"] == scene["activeVersionId"])
    clip = await repair.media.read(version["storageKey"])
    if hashlib.sha256(clip).hexdigest() != version.get("mediaHash"):
        raise AppError("SMART_REMAKE_MEDIA_CHANGED", "Video cảnh đã thay đổi.", 409)
    unit = row.context_json["renderPlan"]["units"][scene["index"]]
    selection = next(
        (
            item
            for item in row.state_json.get("draftTimeline", {}).get("items", [])
            if item["renderUnitId"] == scene["id"] and item["versionId"] == version["id"]
        ),
        None,
    )
    start = version.get("suggestedInFrame", 0)
    item = selection or {
        "inFrame": start,
        "outFrame": version.get("suggestedOutFrame", start + unit["targetDurationFrames"]),
        "targetDurationFrames": unit["targetDurationFrames"],
    }
    info = await run_in_threadpool(probe_timeline_media, clip)
    validate_trim(item, info["frameCount"])
    excerpt = await run_in_threadpool(trim_repair_evidence, clip, item["inFrame"], item["outFrame"])
    media: list[dict[str, Any]] = [
        {"bytes": product.bytes, "mime_type": product.mime_type},
        {"bytes": opening.bytes, "mime_type": opening.mime_type},
        {"bytes": excerpt, "mime_type": "video/mp4"},
    ]
    return media, {
        "versionId": version["id"],
        "mediaHash": version["mediaHash"],
        "inFrame": item["inFrame"],
        "outFrame": item["outFrame"],
        "fps": 24,
        "evidenceHashes": [hashlib.sha256(item["bytes"]).hexdigest() for item in media],
    }
