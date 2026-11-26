"""Boundary observations from final bytes or explicitly resolved adjacent raw versions."""

from __future__ import annotations

from starlette.concurrency import run_in_threadpool

from .contracts import (
    InspectionConstraints,
    InspectionSubject,
    ModelImage,
    Observation,
    ResolvedMedia,
)
from .media import video_observations


async def boundary_observations(
    subject: InspectionSubject,
    media: ResolvedMedia,
    references: list[ResolvedMedia],
    constraints: InspectionConstraints,
    windows: list[tuple[int, int, str | None]],
) -> list[tuple[list[Observation], list[ModelImage]]]:
    """An absent resolved neighbor yields no fabricated evidence or speculative mapping."""
    if subject.range is None or constraints.maxFramesPerVideo < 4:
        return []
    observations = []
    if subject.kind == "assembly":
        for left, right in zip(windows, windows[1:], strict=False):
            boundary = left[1]
            frames = sorted(
                {
                    max(left[0], boundary - 2),
                    boundary - 1,
                    boundary,
                    min(right[1] - 1, boundary + 1),
                }
            )
            observations.append(
                await run_in_threadpool(
                    video_observations,
                    media,
                    frames,
                    timebase="final",
                    max_long_edge=constraints.maxFrameLongEdge,
                )
            )
        return observations
    items = constraints.timeline.get("items", [])
    current_index = next(
        (index for index, item in enumerate(items) if item.get("renderUnitId") == subject.sceneId),
        None,
    )
    if current_index is None:
        return []
    for neighbor in references:
        if neighbor.role != "neighbor" or neighbor.versionId not in (
            subject.neighborVersionIds or []
        ):
            continue
        index = next(
            (
                index
                for index, item in enumerate(items)
                if item.get("versionId") == neighbor.versionId and abs(index - current_index) == 1
            ),
            None,
        )
        if index is None:
            continue
        item = items[index]
        start, end = item.get("inFrame"), item.get("outFrame")
        if (
            type(start) is not int
            or type(end) is not int
            or start < 0
            or end <= start
            or end > (neighbor.frameCount or 0)
        ):
            raise ValueError("The saved neighbor range exceeds its resolved media.")
        own_start, own_end = subject.range.inFrame, subject.range.outFrame
        own_frames = (
            [max(own_start, own_end - 2), own_end - 1]
            if index > current_index
            else [own_start, min(own_end - 1, own_start + 1)]
        )
        neighbor_frames = (
            [start, min(end - 1, start + 1)]
            if index > current_index
            else [max(start, end - 2), end - 1]
        )
        own, own_images = await run_in_threadpool(
            video_observations,
            media,
            sorted(set(own_frames)),
            timebase=subject.range.timebase,
            max_long_edge=constraints.maxFrameLongEdge,
        )
        adjacent, adjacent_images = await run_in_threadpool(
            video_observations,
            neighbor,
            sorted(set(neighbor_frames)),
            timebase="raw_group",
            max_long_edge=constraints.maxFrameLongEdge,
        )
        observations.append((own + adjacent, own_images + adjacent_images))
    return observations
