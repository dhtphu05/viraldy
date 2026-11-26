"""Keep source evidence separate from output timing and provider-sized fragments."""

from __future__ import annotations

from itertools import accumulate
from typing import Any
from uuid import uuid4

from viraldy.shared.errors.base import AppError

from .timeline_schemas import DraftTimeline, RenderPlan, SourceSceneMap


def source_boundaries(analysis: dict[str, Any], *, total_frames: int) -> list[int]:
    shots = analysis.get("sourceShots") or []
    cuts = {
        round(float(shot["startSecond"]) * 24)
        for shot in shots
        if isinstance(shot, dict) and isinstance(shot.get("startSecond"), int | float)
    }
    return [0, *sorted(value for value in cuts if 0 < value < total_frames), total_frames]


def validate_source_excerpt(
    *, target_duration: int, source_frame_count: int, reference_start_frame: int
) -> int:
    if type(target_duration) is not int or target_duration not in {8, 16}:
        raise AppError("INVALID_SMART_REMAKE_DURATION", "Duration must be 8 or 16 seconds.")
    total = target_duration * 24
    if (
        type(reference_start_frame) is not int
        or reference_start_frame < 0
        or reference_start_frame + total > source_frame_count
    ):
        raise AppError(
            "SMART_REMAKE_SOURCE_RANGE_INVALID",
            "The selected source excerpt does not fit the measured source video.",
        )
    return total


def build_timeline_plan(
    *,
    target_duration: int,
    source_frame_count: int,
    reference_start_frame: int,
    cut_frames: list[int],
    render_group_breaks: list[int] | None = None,
    image_quality: str = "max",
    timing_mode: str = "source_rhythm",
) -> dict[str, Any]:
    total, source_total = _timing_lengths(
        target_duration, source_frame_count, reference_start_frame, timing_mode
    )
    if (
        not isinstance(cut_frames, list)
        or len(cut_frames) < 2
        or any(type(value) is not int for value in cut_frames)
        or cut_frames[0] != 0
        or cut_frames[-1] != source_total
        or any(b <= a for a, b in zip(cut_frames, cut_frames[1:], strict=False))
    ):
        raise AppError(
            "SMART_REMAKE_TIMELINE_CUTS_INVALID",
            "Cut boundaries must cover the analyzed source in increasing integer frames.",
        )
    source_lengths = [b - a for a, b in zip(cut_frames, cut_frames[1:], strict=False)]
    if timing_mode == "source_rhythm" and any(length > 192 for length in source_lengths):
        raise AppError(
            "SMART_REMAKE_TIMELINE_SCENE_TOO_LONG",
            "A source scene exceeds eight seconds. Choose an explicit cut before rendering.",
            details={"sourceCutFrames": cut_frames, "maxSceneFrames": 192},
        )
    targets = (
        _allocate_target_frames(source_lengths, total)
        if timing_mode == "fit_target"
        else source_lengths
    )
    sources = [
        {
            "id": str(uuid4()),
            "startFrame": reference_start_frame + start,
            "endFrame": reference_start_frame + end,
            "targetDurationFrames": target,
            **({"sourceSceneIndex": index} if timing_mode == "fit_target" else {}),
        }
        for index, (start, end, target) in enumerate(
            zip(cut_frames, cut_frames[1:], targets, strict=False)
        )
    ]
    source_starts = accumulate([0, *targets])
    fragments = [
        unit
        for source, start in zip(sources, source_starts, strict=False)
        for unit in _source_fragments(source, timing_mode, target_start_frame=start)
    ]
    units = [{**unit, "sceneIndex": index} for index, unit in enumerate(fragments)]
    items = _timeline_items(units)
    group_breaks = [] if timing_mode == "fit_target" else render_group_breaks
    groups = build_render_groups(units, render_group_breaks=group_breaks)
    if image_quality not in {"low", "medium", "high", "xhigh", "max"}:
        raise AppError(
            "SMART_REMAKE_RENDER_GROUPS_INVALID",
            "Image quality must be low, medium, high, xhigh or max.",
        )
    return {
        "sourceSceneMap": SourceSceneMap.model_validate(
            {
                "sourceStartFrame": reference_start_frame,
                "sourceFrameCount": source_frame_count,
                "timingMode": timing_mode,
                "scenes": sources,
            }
        ).model_dump(
            exclude_none=True,
            exclude=(
                {
                    "timingMode": True,
                    "scenes": {
                        "__all__": {
                            "sourceSceneIndex",
                            "prompt",
                            "imagePrompt",
                            "videoPrompt",
                            "shotPlan",
                        }
                    },
                }
                if timing_mode == "source_rhythm"
                else None
            ),
        ),
        "renderPlan": RenderPlan.model_validate(
            {
                "units": units,
                "groups": groups,
                "renderGroupBreaks": group_breaks or [],
                **(
                    {"groupingPolicy": "fixed_provider_windows"}
                    if timing_mode == "fit_target"
                    else {}
                ),
                "videoModel": "veo3_lite",
                "imageModel": "gpt-image-2.6-sunburst",
                "imageQuality": image_quality,
                "imageComplexity": "high",
                "imageSize": "720x1280",
            }
        ).model_dump(
            exclude_none=True,
            exclude=(
                {
                    "units": {
                        "__all__": {
                            "sourceSceneIndex",
                            "sourceStartFrame",
                            "sourceEndFrame",
                            "fragmentIndex",
                            "fragmentCount",
                        }
                    }
                }
                if timing_mode == "source_rhythm"
                else None
            ),
        ),
        "draftTimeline": DraftTimeline.model_validate(
            {
                "totalFrames": total,
                "items": items,
            }
        ).model_dump(),
    }


def _timing_lengths(
    target_duration: int, source_frame_count: int, reference_start_frame: int, timing_mode: str
) -> tuple[int, int]:
    if timing_mode == "source_rhythm":
        total = validate_source_excerpt(
            target_duration=target_duration,
            source_frame_count=source_frame_count,
            reference_start_frame=reference_start_frame,
        )
        return total, total
    if timing_mode != "fit_target":
        raise AppError("SMART_REMAKE_TIMELINE_INVALID", "Unknown timeline timing mode.")
    if type(target_duration) is not int or target_duration not in {8, 16}:
        raise AppError("INVALID_SMART_REMAKE_DURATION", "Duration must be 8 or 16 seconds.")
    if (
        type(source_frame_count) is not int
        or source_frame_count < 1
        or (type(reference_start_frame) is not int or reference_start_frame != 0)
    ):
        raise AppError(
            "SMART_REMAKE_SOURCE_RANGE_INVALID", "Full-source analysis must cover the entire video."
        )
    return target_duration * 24, source_frame_count


def _allocate_target_frames(source_lengths: list[int], total: int) -> list[int]:
    if len(source_lengths) > total:
        raise AppError(
            "SMART_REMAKE_TIMELINE_DENSITY_UNSUPPORTED",
            "The selected output duration cannot show every source scene for at least one frame.",
            details={"sourceSceneCount": len(source_lengths), "availableFrames": total},
        )
    source_total = sum(source_lengths)
    targets = [max(1, length * total // source_total) for length in source_lengths]
    remaining = total - sum(targets)
    while remaining:
        direction = 1 if remaining > 0 else -1
        candidates = [index for index, value in enumerate(targets) if direction > 0 or value > 1]
        index = max(
            candidates,
            key=lambda index: (
                direction * (source_lengths[index] * total - targets[index] * source_total),
                -index,
            ),
        )
        targets = [
            value + direction if position == index else value
            for position, value in enumerate(targets)
        ]
        remaining -= direction
    return targets


def _source_fragments(
    source: dict[str, Any], timing_mode: str, *, target_start_frame: int
) -> list[dict[str, Any]]:
    duration = source["targetDurationFrames"]
    boundaries = [
        0,
        *(
            [
                frame * 192 - target_start_frame
                for frame in range(
                    target_start_frame // 192 + 1,
                    (target_start_frame + duration - 1) // 192 + 1,
                )
            ]
            if timing_mode == "fit_target"
            else []
        ),
        duration,
    ]
    count = len(boundaries) - 1
    source_length = source["endFrame"] - source["startFrame"]
    if source_length < count:
        raise AppError(
            "SMART_REMAKE_SOURCE_RANGE_INVALID",
            "The source scene has fewer source frames than required provider fragments.",
        )
    source_lengths = _allocate_target_frames(
        [end - start for start, end in zip(boundaries, boundaries[1:], strict=False)],
        source_length,
    )
    source_offsets = list(accumulate([0, *source_lengths]))
    return [
        {
            "id": str(uuid4()),
            "sourceSceneId": source["id"],
            "rawDurationFrames": 192,
            "targetDurationFrames": end - start,
            **(
                {
                    "sourceSceneIndex": source["sourceSceneIndex"],
                    "sourceStartFrame": source["startFrame"] + source_offsets[index],
                    "sourceEndFrame": source["startFrame"] + source_offsets[index + 1],
                    "fragmentIndex": index,
                    "fragmentCount": count,
                }
                if timing_mode == "fit_target"
                else {}
            ),
        }
        for index, (start, end) in enumerate(zip(boundaries, boundaries[1:], strict=False))
    ]


def _timeline_items(units: list[dict[str, Any]]) -> list[dict[str, Any]]:
    starts = accumulate([0, *[unit["targetDurationFrames"] for unit in units]])
    return [
        {
            "id": str(uuid4()),
            "sourceSceneId": unit["sourceSceneId"],
            "renderUnitId": unit["id"],
            "targetStartFrame": start,
            "targetDurationFrames": unit["targetDurationFrames"],
            "inFrame": 0,
            "outFrame": unit["targetDurationFrames"],
        }
        for unit, start in zip(units, starts, strict=False)
    ]


def build_render_groups(
    units: list[dict[str, Any]], *, render_group_breaks: list[int] | None = None
) -> list[dict[str, Any]]:
    """Pack adjacent logical scenes while keeping every source scene intact."""
    breaks = [] if render_group_breaks is None else render_group_breaks
    if (
        not isinstance(breaks, list)
        or any(type(value) is not int or not 1 <= value < len(units) for value in breaks)
        or breaks != sorted(set(breaks))
    ):
        raise AppError(
            "SMART_REMAKE_RENDER_GROUPS_INVALID",
            "Group boundaries must be unique ordered scene positions before the final scene.",
        )
    groups: list[dict[str, Any]] = []
    for index, unit in enumerate(units):
        length = unit["targetDurationFrames"]
        if not groups or index in breaks or groups[-1]["targetDurationFrames"] + length > 192:
            groups.append(
                {
                    "id": str(uuid4()),
                    "renderUnitIds": [],
                    "rawDurationFrames": 192,
                    "targetDurationFrames": 0,
                    "segments": [],
                }
            )
        group = groups[-1]
        start = group["targetDurationFrames"]
        group["renderUnitIds"].append(unit["id"])
        group["segments"].append(
            {"renderUnitId": unit["id"], "inFrame": start, "outFrame": start + length}
        )
        group["targetDurationFrames"] += length
    return groups
