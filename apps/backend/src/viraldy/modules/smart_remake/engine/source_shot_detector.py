import json
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from .media_binaries import ffmpeg_path, ffprobe_path
from .schemas import UploadedMedia


MAX_DETECTED_SOURCE_SHOTS = 12
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
        source_shots = analysis.get("sourceShots") if isinstance(analysis.get("sourceShots"), list) else []
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

    if duration <= 0 or len(cut_times) + 1 <= len(source_shots):
        return analysis

    expanded = expand_source_shots_to_cut_boundaries(
        analysis,
        duration_seconds=duration,
        cut_times=cut_times,
    )
    if len(expanded) <= len(source_shots):
        return analysis
    return {
        **analysis,
        **expanded,
        "sourceCutDetection": {
            "detectedCutCount": len(cut_times),
            "sourceShotCount": len(expanded["sourceShots"]),
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

    pacing = analysis.get("pacingPlan") if isinstance(analysis.get("pacingPlan"), dict) else {}
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

    existing = analysis.get("sourceShots") if isinstance(analysis.get("sourceShots"), list) else []
    motion_beats = analysis.get("motionBeats") if isinstance(analysis.get("motionBeats"), list) else []
    shots: list[dict[str, Any]] = []
    for index, (start, end) in enumerate(zip(boundaries, boundaries[1:])):
        parent = _containing_item(existing, (start + end) / 2)
        fallback = _containing_item(motion_beats, (start + end) / 2)
        template = parent or fallback or {}
        action = str(template.get("action") or "continue the source demo action").strip()
        if parent and not _same_time_range(parent, start, end):
            action = f"{action}; preserve this source cut and continue the same physical demo action"
        shots.append(
            {
                "shotIndex": index,
                "startSecond": round(start, 3),
                "endSecond": round(end, 3),
                "durationSeconds": round(end - start, 3),
                "role": template.get("role") or ("hook" if index == 0 else "payoff" if index == len(boundaries) - 2 else "action"),
                "priority": template.get("priority") or "supporting",
                "framing": template.get("framing") or (analysis.get("cameraStyle") or {}).get("framing") or "product shot",
                "cameraAngle": template.get("cameraAngle") or (analysis.get("cameraStyle") or {}).get("angle") or "front",
                "cameraMovement": template.get("cameraMovement") or (analysis.get("cameraStyle") or {}).get("movement") or "static",
                "subjectPresence": template.get("subjectPresence") or analysis.get("subjectPresence", "none"),
                "action": action,
                "productState": template.get("productState"),
                "stateBefore": template.get("stateBefore"),
                "stateAfter": template.get("stateAfter"),
                "transitionOut": template.get("transitionOut"),
            }
        )

    return {
        "shotPreservationMode": "exact",
        "sourceShotCount": len(shots),
        "sourceDurationSeconds": duration,
        "sourceShots": shots,
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
    return normalized[: MAX_DETECTED_SOURCE_SHOTS - 1]


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
    return abs(item_start - start) < 0.1 and abs(item_end - end) < 0.1


def _video_suffix(mime_type: str) -> str:
    normalized = mime_type.lower()
    if "webm" in normalized:
        return ".webm"
    if "quicktime" in normalized or "mov" in normalized:
        return ".mov"
    return ".mp4"
