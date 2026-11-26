import copy
import json
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from .media_binaries import ffmpeg_path, ffprobe_path
from .schemas import UploadedMedia

MIN_SOURCE_SHOT_DURATION_SECONDS = 0.35
DEFAULT_SCENE_THRESHOLD = 0.18
FALLBACK_SCENE_THRESHOLD = 0.10


def enrich_reference_analysis_with_detected_cuts(
    analysis: dict[str, Any],
    reference_video: UploadedMedia | None,
) -> dict[str, Any]:
    """Use measured visual cuts to recover source shots missed by the LLM.

    Gemini remains responsible for semantic meaning. FFmpeg only supplies
    actual visual boundaries, so a fast source montage is not silently reduced
    to the two semantic beats Gemini sometimes returns.
    """
    if not reference_video:
        return analysis

    try:
        duration, cut_times = detect_source_cuts(reference_video)
        raw_shots = analysis.get("sourceShots")
        source_shots = raw_shots if isinstance(raw_shots, list) else []
        if _should_recover_missed_cuts(analysis, source_shots, cut_times):
            try:
                fallback_duration, fallback_cut_times = detect_source_cuts(
                    reference_video,
                    threshold=FALLBACK_SCENE_THRESHOLD,
                )
            except (OSError, RuntimeError, ValueError, subprocess.SubprocessError, json.JSONDecodeError):
                fallback_duration, fallback_cut_times = duration, []
            if len(fallback_cut_times) > len(cut_times):
                duration, cut_times = fallback_duration, fallback_cut_times
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError, json.JSONDecodeError):
        return analysis

    if duration <= 0:
        return analysis
    known = [float(shot.get("startSecond", 0)) for shot in source_shots]
    if not any(all(abs(cut - boundary) > 1 / 24 for boundary in known) for cut in cut_times):
        return analysis
    # A missed measured boundary matters even if the model returned the same
    # number of shots at different times. Retain its existing intervals too;
    # the semantic pass will describe each interval without inventing cuts.
    semantic_cuts = sorted({*cut_times, *(value for value in known if 0 < value < duration)})

    expanded = expand_source_shots_to_cut_boundaries(
        analysis,
        duration_seconds=duration,
        cut_times=semantic_cuts,
    )
    return {
        **analysis,
        **expanded,
        "sourceCutDetection": {
            **expanded.get("sourceCutDetection", {}),
            "detectedCutCount": len(cut_times),
            "sourceShotCount": len(semantic_cuts) + 1,
        },
    }


def detect_source_cuts(
    reference_video: UploadedMedia,
    *,
    threshold: float = DEFAULT_SCENE_THRESHOLD,
) -> tuple[float, list[float]]:
    suffix = _video_suffix(reference_video.mime_type)
    with tempfile.TemporaryDirectory(prefix="smart-remake-source-cuts-") as tmp:
        input_path = Path(tmp) / f"reference{suffix}"
        input_path.write_bytes(reference_video.bytes)
        duration = _probe_duration(input_path)
        proc = subprocess.run(
            [
                ffmpeg_path(),
                "-hide_banner",
                "-i",
                str(input_path),
                "-an",
                "-vf",
                f"select='gt(scene,{threshold})',showinfo",
                "-f",
                "null",
                "-",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
    raw_times = [float(value) for value in re.findall(r"pts_time:([0-9.]+)", proc.stderr or "")]
    return duration, _normalize_cut_times(raw_times, duration)


def _should_recover_missed_cuts(
    analysis: dict[str, Any],
    source_shots: list[Any],
    cut_times: list[float],
) -> bool:
    if len(cut_times) >= 2 or len(source_shots) > 1:
        return False

    raw_pacing = analysis.get("pacingPlan")
    pacing = raw_pacing if isinstance(raw_pacing, dict) else {}
    shot_count = pacing.get("shotCount")
    try:
        expects_multiple_shots = int(shot_count or 0) > 1
    except (TypeError, ValueError):
        expects_multiple_shots = False

    cut_style = str(pacing.get("cutStyle") or "").lower()
    visual_structure = str(analysis.get("visualStructure") or "").lower()
    return expects_multiple_shots or cut_style in {"soft_cut", "hard_cut", "jump_cut", "mixed"} or visual_structure in {
        "montage",
        "sequential_shots",
        "split_screen",
    }


def expand_source_shots_to_cut_boundaries(
    analysis: dict[str, Any],
    *,
    duration_seconds: float,
    cut_times: list[float],
) -> dict[str, Any]:
    duration = max(0.1, float(duration_seconds))
    boundaries = _boundaries(cut_times, duration)
    if len(boundaries) < 3:
        return analysis

    raw_shots = analysis.get("sourceShots")
    existing = raw_shots if isinstance(raw_shots, list) else []
    shots: list[dict[str, Any]] = []
    for index, (start, end) in enumerate(zip(boundaries, boundaries[1:], strict=False)):
        parent = _containing_item(existing, (start + end) / 2)
        if parent is None or not _same_time_range(parent, start, end):
            # A visual boundary measures time, not what happened on either side.
            # Keep the original evidence rather than inventing per-cut semantics.
            return {
                "shotPreservationMode": "unverified",
                "sourceShots": copy.deepcopy(existing),
                "sourceCutDetection": {
                    "requiresSemanticReanalysis": True,
                    "cutFrames": [round(value * 24) for value in boundaries],
                },
            }
        shots.append(
            {
                **copy.deepcopy(parent),
                "shotIndex": index,
                "startSecond": round(start, 3),
                "endSecond": round(end, 3),
                "durationSeconds": round(end - start, 3),
            }
        )

    return {
        "shotPreservationMode": "exact",
        "sourceShotCount": len(shots),
        "sourceDurationSeconds": duration,
        "sourceShots": shots,
        "sourceCutDetection": {"requiresSemanticReanalysis": False},
    }


def _probe_duration(path: Path) -> float:
    proc = subprocess.run(
        [ffprobe_path(), "-v", "error", "-print_format", "json", "-show_format", str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(proc.stdout or "{}")
    duration = float((payload.get("format") or {}).get("duration") or 0)
    if duration <= 0:
        raise ValueError("Reference video duration is unavailable.")
    return duration


def _normalize_cut_times(values: list[float], duration: float) -> list[float]:
    usable = [value for value in values if MIN_SOURCE_SHOT_DURATION_SECONDS <= value <= duration - MIN_SOURCE_SHOT_DURATION_SECONDS]
    normalized: list[float] = []
    for value in usable:
        rounded = round(value, 3)
        if not normalized or rounded - normalized[-1] >= MIN_SOURCE_SHOT_DURATION_SECONDS:
            normalized.append(rounded)
    return normalized


def _boundaries(cut_times: list[float], duration: float) -> list[float]:
    normalized = _normalize_cut_times(cut_times, duration)
    boundaries = [0.0, *normalized, duration]
    return [value for index, value in enumerate(boundaries) if index == 0 or value - boundaries[index - 1] >= MIN_SOURCE_SHOT_DURATION_SECONDS]


def _containing_item(items: list[Any], second: float) -> dict[str, Any] | None:
    for item in items:
        if not isinstance(item, dict):
            continue
        start = float(item.get("startSecond") or 0)
        end = float(item.get("endSecond") or start)
        if start <= second <= end:
            return item
    return None


def _same_time_range(item: dict[str, Any], start: float, end: float) -> bool:
    item_start = float(item.get("startSecond") or 0)
    item_end = float(item.get("endSecond") or item_start)
    return abs(item_start - start) <= 1 / 24 and abs(item_end - end) <= 1 / 24


def _video_suffix(mime_type: str) -> str:
    normalized = mime_type.lower()
    if "webm" in normalized:
        return ".webm"
    if "quicktime" in normalized or "mov" in normalized:
        return ".mov"
    return ".mp4"
