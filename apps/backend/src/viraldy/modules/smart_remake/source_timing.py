"""Map verified source evidence onto an independently allocated output clock."""

from __future__ import annotations

import copy
from typing import Any

from viraldy.shared.errors.base import AppError


def source_frame_clock_analysis(
    analysis: dict[str, Any], *, source_frame_count: int | None = None
) -> dict[str, Any]:
    """Use the validated 24 fps clock without changing retained raw model evidence."""
    result = copy.deepcopy(analysis)
    for field in ("sourceShots", "motionBeats"):
        items = result.get(field) or []
        for index, item in enumerate(items):
            terminal_error = (
                abs(float(item["endSecond"]) * 24 - source_frame_count)
                if source_frame_count is not None and index == len(items) - 1
                else None
            )
            if field == "sourceShots" and terminal_error is not None and terminal_error > 1:
                raise AppError(
                    "SMART_REMAKE_SOURCE_ANALYSIS_INCOMPLETE",
                    "Observed source intervals must cover the measured video clock.",
                    409,
                )
            start = round(float(item["startSecond"]) * 24) / 24
            end = round(float(item["endSecond"]) * 24) / 24
            if terminal_error is not None and terminal_error <= 1:
                assert source_frame_count is not None
                end = source_frame_count / 24
            if end <= start:
                raise AppError(
                    "SMART_REMAKE_SOURCE_ANALYSIS_INCOMPLETE",
                    "Observed source intervals must have a positive duration on the frame clock.",
                    409,
                )
            item.update(startSecond=start, endSecond=end, durationSeconds=end - start)
    detection = result.get("sourceCutDetection") or {}
    cuts = detection.get("cutFrames")
    if source_frame_count is not None and isinstance(cuts, list):
        # Visual detection uses the container clock, which can include longer
        # audio. Only its derived cuts use the measured video's outer boundary.
        detection["cutFrames"] = [
            0, *(frame for frame in cuts[1:-1] if 0 < frame < source_frame_count),
            source_frame_count,
        ]
    return result


def assert_observed_fragment_boundaries(
    analysis: dict[str, Any], units: list[dict[str, Any]]
) -> None:
    observed = {
        round(float(shot[field]) * 24)
        for shot in analysis.get("sourceShots", [])
        for field in ("startSecond", "endSecond")
    }
    if any(
        unit.get("sourceStartFrame") not in observed or unit.get("sourceEndFrame") not in observed
        for unit in units
    ):
        raise AppError(
            "SMART_REMAKE_SOURCE_ANALYSIS_INCOMPLETE",
            "New provider fragments need observed actions at their exact source boundaries.",
            409,
        )


def fit_observed_shots(
    shots: list[dict[str, Any]], *, source_start: float, source_end: float, target_frames: int
) -> list[dict[str, Any]]:
    source_frames = round((source_end - source_start) * 24)
    result = []
    for shot in shots:
        start = round(float(shot["startSecond"]) * 24)
        end = round(float(shot["endSecond"]) * 24)
        target_start = round(start * target_frames / source_frames)
        target_end = round(end * target_frames / source_frames)
        if target_end <= target_start:
            raise AppError(
                "SMART_REMAKE_OUTPUT_DENSITY_UNSUPPORTED",
                "The selected output duration cannot represent every observed action at 24 fps.",
                409,
            )
        result.append(
            {
                **copy.deepcopy(shot),
                "sourceTimeRange": {
                    "startSecond": source_start + start / 24,
                    "endSecond": source_start + end / 24,
                },
                "startSecond": target_start / 24,
                "endSecond": target_end / 24,
                "durationSeconds": (target_end - target_start) / 24,
            }
        )
    return result


def fit_source_motion_beats(
    analysis: dict[str, Any], *, source_start: float, source_end: float, target_frames: int
) -> list[dict[str, Any]]:
    """Keep supplied beat identity while using observed actions for partial windows."""
    localized = []
    fields = ("action", "physicalAction", "stateBefore", "stateAfter", "transitionOut")
    for index, beat in enumerate(analysis.get("motionBeats") or []):
        beat_start, beat_end = float(beat["startSecond"]), float(beat["endSecond"])
        left, right = max(source_start, beat_start), min(source_end, beat_end)
        if right <= left:
            continue
        partial = left > beat_start or right < beat_end
        evidence = analysis.get("sourceShots") or [] if partial else [beat]
        for observed in evidence:
            observed_start = float(observed["startSecond"])
            observed_end = float(observed["endSecond"])
            start, end = max(left, observed_start), min(right, observed_end)
            if end <= start:
                continue
            fragment = copy.deepcopy(beat)
            if partial:
                fragment = {key: value for key, value in fragment.items() if key not in fields}
                fragment.update(
                    {key: copy.deepcopy(observed[key]) for key in fields if key in observed}
                )
            if abs(start - observed_start) > 1 / 24:
                fragment.pop("stateBefore", None)
            if abs(end - observed_end) > 1 / 24:
                fragment.pop("stateAfter", None)
                fragment.pop("transitionOut", None)
            fragment.update(
                {
                    "sourceBeatIndex": index,
                    "startSecond": start - source_start,
                    "endSecond": end - source_start,
                }
            )
            if left > beat_start:
                fragment["continuesFromPreviousWindow"] = True
            localized.extend(
                fit_observed_shots(
                    [fragment],
                    source_start=source_start,
                    source_end=source_end,
                    target_frames=target_frames,
                )
            )
    return localized
