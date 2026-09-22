import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Any

from viraldy.modules.smart_remake.runtime_paths import OUTPUTS_DIR
from .errors import SmartRemakeError
from .media_binaries import ffmpeg_path
from .schemas import UploadedMedia


SOURCE_FRAME_DIR = OUTPUTS_DIR / "smart-remake-assets" / "source-frames"
MAX_SOURCE_FRAMES_PER_SCENE = 3


def attach_source_frame_assets(
    *,
    scene_map: dict[str, Any],
    reference_analysis: dict[str, Any],
    reference_video: UploadedMedia | None,
) -> dict[str, Any]:
    if not reference_video:
        return scene_map

    scenes = scene_map.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        return scene_map

    seconds = _source_frame_seconds(reference_analysis, len(scenes))
    assets = extract_source_frames(reference_video, seconds)
    updated_scenes = []
    cursor = 0
    for scene in scenes:
        scene_assets = assets[cursor : cursor + MAX_SOURCE_FRAMES_PER_SCENE]
        cursor += MAX_SOURCE_FRAMES_PER_SCENE
        if not scene_assets:
            updated_scenes.append(scene)
            continue
        updated_scenes.append(
            {
                **scene,
                "sourceFrame": scene_assets[0],
                "sourceFrames": scene_assets,
            }
        )
    return {**scene_map, "scenes": updated_scenes}


def extract_source_frames(reference_video: UploadedMedia, seconds: list[float]) -> list[dict[str, Any]]:
    if not seconds:
        return []

    SOURCE_FRAME_DIR.mkdir(parents=True, exist_ok=True)
    suffix = _video_suffix(reference_video.mime_type)
    ffmpeg = ffmpeg_path()
    run_id = uuid.uuid4().hex[:12]
    assets: list[dict[str, Any]] = []

    with tempfile.TemporaryDirectory(prefix="smart-remake-source-video-") as tmp:
        input_path = Path(tmp) / f"reference{suffix}"
        input_path.write_bytes(reference_video.bytes)
        for index, second in enumerate(seconds):
            filename = f"smart_remake_source_frame_{run_id}_{index}.jpg"
            output_path = SOURCE_FRAME_DIR / filename
            try:
                subprocess.run(
                    [
                        ffmpeg,
                        "-y",
                        "-ss",
                        f"{max(0.0, second):.3f}",
                        "-i",
                        str(input_path),
                        "-frames:v",
                        "1",
                        "-q:v",
                        "2",
                        str(output_path),
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                )
            except subprocess.CalledProcessError as exc:
                raise SmartRemakeError(
                    "Could not extract source frame from reference video.",
                    "SMART_REMAKE_SOURCE_FRAME_FAILED",
                    {"second": second, "stderr": exc.stderr[-1000:] if exc.stderr else None},
                ) from exc
            assets.append(
                {
                    "assetId": filename,
                    "sourceSecond": round(max(0.0, second), 3),
                    "mimeType": "image/jpeg",
                }
            )
    return assets


def load_source_frame_asset(asset_id: str) -> UploadedMedia | None:
    if not asset_id or Path(asset_id).name != asset_id:
        raise SmartRemakeError(
            "Invalid Smart Remake source frame asset id.",
            "SMART_REMAKE_SOURCE_FRAME_INVALID",
            {"assetId": asset_id},
        )

    base_dir = SOURCE_FRAME_DIR.resolve()
    path = (SOURCE_FRAME_DIR / asset_id).resolve()
    if path.parent != base_dir:
        raise SmartRemakeError(
            "Invalid Smart Remake source frame asset path.",
            "SMART_REMAKE_SOURCE_FRAME_INVALID",
            {"assetId": asset_id},
        )
    if not path.exists():
        return None
    return UploadedMedia(bytes=path.read_bytes(), mime_type="image/jpeg", file_name=asset_id)


def _source_frame_seconds(reference_analysis: dict[str, Any], scene_count: int) -> list[float]:
    duration = _source_duration_seconds(reference_analysis)
    shots = reference_analysis.get("sourceShots") if isinstance(reference_analysis.get("sourceShots"), list) else []
    if scene_count <= 1:
        return _single_scene_anchor_seconds(shots, duration)
    seconds: list[float] = []
    for index in range(scene_count):
        start = duration * index / scene_count
        end = duration * (index + 1) / scene_count
        anchor = _scene_anchor_second(index, scene_count, duration, shots)
        seconds.extend(_dedupe_seconds([start + 0.1, anchor, end - 0.1], duration))
    return seconds


def _single_scene_anchor_seconds(shots: list[Any], duration: float) -> list[float]:
    if duration <= 0:
        return [0.0]
    anchors = [
        _clamp_second(min(0.25, duration * 0.08), duration),
        _first_action_second(shots, duration),
        _clamp_second(duration * 0.85, duration),
    ]
    if len(shots) >= 3:
        anchors = [
            _shot_midpoint(shots[0], duration),
            _shot_midpoint(shots[len(shots) // 2], duration),
            _shot_midpoint(shots[-1], duration),
        ]
    return _dedupe_seconds(anchors, duration)


def _source_duration_seconds(reference_analysis: dict[str, Any]) -> float:
    value = reference_analysis.get("sourceDurationSeconds")
    if isinstance(value, (int, float)) and value > 0:
        return float(value)
    shots = reference_analysis.get("sourceShots") if isinstance(reference_analysis.get("sourceShots"), list) else []
    ends = [float(shot.get("endSecond")) for shot in shots if isinstance(shot, dict) and isinstance(shot.get("endSecond"), (int, float))]
    return max(ends or [8.0])


def _first_action_second(shots: list[Any], duration: float) -> float:
    for shot in shots:
        if not isinstance(shot, dict):
            continue
        role = str(shot.get("role") or "").lower()
        action = str(shot.get("action") or "").lower()
        if role in {"action", "demonstration", "hero"} or any(word in action for word in ("use", "clean", "wipe", "scrub", "spray", "brush")):
            start = float(shot.get("startSecond") or 0)
            end = float(shot.get("endSecond") or start + 1)
            return _clamp_second((start + end) / 2, duration)
    return _clamp_second(min(0.25, duration / 4), duration)


def _shot_midpoint(shot: Any, duration: float) -> float:
    if not isinstance(shot, dict):
        return _clamp_second(duration / 2, duration)
    start = float(shot.get("startSecond") or 0)
    end = float(shot.get("endSecond") or start + 1)
    return _clamp_second((start + end) / 2, duration)


def _scene_anchor_second(index: int, scene_count: int, duration: float, shots: list[Any]) -> float:
    start = duration * index / scene_count
    end = duration * (index + 1) / scene_count
    candidates = [
        shot
        for shot in shots
        if isinstance(shot, dict)
        and isinstance(shot.get("startSecond"), (int, float))
        and isinstance(shot.get("endSecond"), (int, float))
        and shot["endSecond"] >= start
        and shot["startSecond"] <= end
    ]
    if candidates:
        best = sorted(candidates, key=lambda shot: _shot_priority(str(shot.get("role") or "")))[0]
        return _clamp_second((float(best["startSecond"]) + float(best["endSecond"])) / 2, duration)
    return _clamp_second((start + end) / 2, duration)


def _shot_priority(role: str) -> int:
    role = role.lower()
    if role in {"action", "demonstration", "hero"}:
        return 0
    if role in {"problem", "proof", "reveal", "payoff"}:
        return 1
    return 2


def _clamp_second(second: float, duration: float) -> float:
    return min(max(0.0, second), max(0.0, duration - 0.05))


def _dedupe_seconds(seconds: list[float], duration: float) -> list[float]:
    result: list[float] = []
    for second in seconds:
        rounded = round(_clamp_second(second, duration), 3)
        if all(abs(rounded - existing) > 0.2 for existing in result):
            result.append(rounded)
    while len(result) < MAX_SOURCE_FRAMES_PER_SCENE:
        fallback = _clamp_second(duration * ((len(result) + 1) / (MAX_SOURCE_FRAMES_PER_SCENE + 1)), duration)
        rounded = round(fallback, 3)
        if all(abs(rounded - existing) > 0.2 for existing in result):
            result.append(rounded)
        else:
            break
    return result[:MAX_SOURCE_FRAMES_PER_SCENE]


def _video_suffix(mime_type: str) -> str:
    normalized = mime_type.lower()
    if "webm" in normalized:
        return ".webm"
    if "quicktime" in normalized or "mov" in normalized:
        return ".mov"
    return ".mp4"
