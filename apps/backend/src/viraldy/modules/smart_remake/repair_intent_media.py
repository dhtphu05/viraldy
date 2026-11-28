"""Owned and hash-checked media for a single repair normalization call."""

from __future__ import annotations

import hashlib
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from starlette.concurrency import run_in_threadpool

from viraldy.shared.errors.base import AppError

from .assembly_snapshots import retained_expectations
from .engine.media_binaries import ffmpeg_path
from .engine.product_lock_generator import prepare_product_analysis_images
from .generation_expectations import expectations_scene, require_generation_expectations
from .image_workflow import _references
from .product_references import read_product_references
from .timeline_media import _assemble, probe_timeline_media, validate_trim


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
    products = (
        await read_product_references(row.context_json, repair.media)
        if row.context_json.get("p0", {}).get("additionalProductReferences")
        else [product]
    )
    product_hashes = [hashlib.sha256(value.bytes).hexdigest() for value in products]
    if (
        hashlib.sha256(product.bytes).hexdigest() != snapshot["references"]["product"]["mediaHash"]
        or product_hashes
        != snapshot.get(
            "productReferenceHashes",
            [snapshot["references"]["product"]["mediaHash"]],
        )
        or hashlib.sha256(opening.bytes).hexdigest() != binding["openingFrame"]["layoutHash"]
    ):
        raise AppError("SMART_REMAKE_INPUT_CHANGED", "Tư liệu tham chiếu đã thay đổi.", 409)
    version = next(value for value in scene["versions"] if value["id"] == scene["activeVersionId"])
    active = retained_expectations(version)
    if active is not None and product_hashes != active.get(
        "productReferenceHashes",
        [active["references"]["product"]["mediaHash"]],
    ):
        raise AppError("SMART_REMAKE_INPUT_CHANGED", "Tư liệu của phiên bản cảnh đã thay đổi.", 409)
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
    analysis_products = await run_in_threadpool(prepare_product_analysis_images, products)
    media: list[dict[str, Any]] = [
        *[{"bytes": value.bytes, "mime_type": value.mime_type} for value in analysis_products],
        {"bytes": opening.bytes, "mime_type": opening.mime_type},
        {"bytes": excerpt, "mime_type": "video/mp4"},
    ]
    if len(products) > 1 and sum(len(value["bytes"]) for value in media) > 14_000_000:
        raise AppError(
            "SMART_REMAKE_REPAIR_EVIDENCE_TOO_LARGE",
            "Tư liệu sửa cảnh quá lớn để phân tích. Chọn đoạn clip ngắn hơn rồi thử lại.",
            422,
        )
    return media, {
        "versionId": version["id"],
        "mediaHash": version["mediaHash"],
        "inFrame": item["inFrame"],
        "outFrame": item["outFrame"],
        "fps": 24,
        "evidenceHashes": [hashlib.sha256(item["bytes"]).hexdigest() for item in media],
        **({"productReferenceHashes": product_hashes} if len(products) > 1 else {}),
    }


async def group_repair_evidence(
    repair: Any, row: Any, repair_group: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Supply one exact reviewed group clip and its two source-bound frame references."""
    from .repair_intent import group_repair_bases

    group_repair_bases(row, repair_group)
    group, bases = repair_group["group"], repair_group["baseVersions"]
    scenes = {scene["id"]: scene for scene in row.state_json["scenes"]}
    first, last = scenes[bases[0]["sceneId"]], scenes[bases[-1]["sceneId"]]
    product, opening = await _references(repair, row, first["index"])
    _, ending = await _references(repair, row, last["index"], frame_role="ending")
    snapshot = require_generation_expectations(row.context_json)
    products = (
        await read_product_references(row.context_json, repair.media)
        if (row.context_json.get("p0") or {}).get("additionalProductReferences") else [product]
    )
    hashes = [hashlib.sha256(value.bytes).hexdigest() for value in products]
    if hashes != snapshot.get(
        "productReferenceHashes", [snapshot["references"]["product"]["mediaHash"]],
    ):
        raise AppError("SMART_REMAKE_INPUT_CHANGED", "Tư liệu sản phẩm đã thay đổi.", 409)
    first_binding = expectations_scene(snapshot, first["id"])
    if hashlib.sha256(opening.bytes).hexdigest() != first_binding["openingFrame"]["layoutHash"]:
        raise AppError("SMART_REMAKE_INPUT_CHANGED", "Khung nguồn đã thay đổi.", 409)
    clips, items = [], []
    units = {unit["id"]: unit for unit in row.context_json["renderPlan"]["units"]}
    for base in bases:
        data = await repair.media.read(base["storageKey"])
        if hashlib.sha256(data).hexdigest() != base["mediaHash"]:
            raise AppError("SMART_REMAKE_MEDIA_CHANGED", "Video clip đã thay đổi.", 409)
        item = {"inFrame": base["inFrame"], "outFrame": base["outFrame"],
                "targetDurationFrames": units[base["sceneId"]]["targetDurationFrames"]}
        info = await run_in_threadpool(probe_timeline_media, data)
        validate_trim(item, info["frameCount"])
        clips.append(data)
        items.append(item)
    excerpt = await run_in_threadpool(
        _assemble, clips, items,
        resolution=row.context_json["renderPlan"].get("videoResolution") or "720P",
    )
    info = await run_in_threadpool(probe_timeline_media, excerpt)
    if info["frameCount"] != group["targetDurationFrames"]:
        raise AppError(
            "SMART_REMAKE_REPAIR_EVIDENCE_INVALID", "Đoạn clip phân tích không đủ thời lượng.", 409,
        )
    analysis_products = await run_in_threadpool(prepare_product_analysis_images, products)
    media: list[dict[str, Any]] = [
        *[{"bytes": value.bytes, "mime_type": value.mime_type} for value in analysis_products],
        {"bytes": opening.bytes, "mime_type": opening.mime_type},
        {"bytes": ending.bytes, "mime_type": ending.mime_type},
        {"bytes": excerpt, "mime_type": "video/mp4"},
    ]
    if sum(len(value["bytes"]) for value in media) > 14_000_000:
        raise AppError("SMART_REMAKE_REPAIR_EVIDENCE_TOO_LARGE", "Tư liệu sửa clip quá lớn.", 422)
    return media, {
        "repairScope": "provider_group", "fps": 24,
        "frameCount": group["targetDurationFrames"],
        "sourceFrames": [
            {"role": role, "sourceMediaHash": snapshot["references"]["source"]["mediaHash"],
             "frame": frame, "mediaHash": hashlib.sha256(value.bytes).hexdigest()}
            for role, frame, value in (
                ("opening", first_binding["sourceRange"]["startFrame"], opening),
                ("ending", expectations_scene(snapshot, last["id"])["sourceRange"]["endFrame"] - 1,
                 ending),
            )
        ],
        "baseVersions": [{key: base[key] for key in (
            "sceneId", "baseVersionId", "mediaHash", "inFrame", "outFrame", "expectationsHash",
        )} for base in bases],
        "evidenceHashes": [hashlib.sha256(item["bytes"]).hexdigest() for item in media],
        **({"productReferenceHashes": hashes} if len(hashes) > 1 else {}),
    }
