import time
from pathlib import Path
from typing import Any, Iterable

from viraldy.modules.smart_remake.runtime_paths import RENDERS_DIR

from . import audio_assets, source_frames
from .config import (
    get_smart_remake_asset_ttl_seconds,
    get_smart_remake_local_output_ttl_seconds,
)


def cleanup_smart_remake_assets(
    asset_ids: Iterable[str] | None = None,
    *,
    now: float | None = None,
    max_age_seconds: int | None = None,
) -> int:
    """Remove Smart Remake's temporary source frames and extracted audio."""
    directories = (source_frames.SOURCE_FRAME_DIR, audio_assets.AUDIO_ASSET_DIR)
    ids = [asset_id.strip() for asset_id in (asset_ids or []) if isinstance(asset_id, str) and asset_id.strip()]
    if ids:
        removed = 0
        for asset_id in ids:
            removed += _remove_asset_id(asset_id, directories)
        return removed

    cutoff = (time.time() if now is None else now) - float(
        max_age_seconds if max_age_seconds is not None else get_smart_remake_asset_ttl_seconds()
    )
    return _remove_older_than(directories, cutoff)


def cleanup_stale_smart_remake_outputs(
    *,
    now: float | None = None,
    max_age_seconds: int | None = None,
) -> int:
    """Remove old local fallback videos while leaving R2-backed output untouched."""
    cutoff = (time.time() if now is None else now) - float(
        max_age_seconds
        if max_age_seconds is not None
        else get_smart_remake_local_output_ttl_seconds()
    )
    return _remove_older_than((RENDERS_DIR,), cutoff, pattern="smart_remake_*.mp4")


def cleanup_render_assets(
    *,
    scene_map: dict[str, Any] | None,
    reference_analysis: dict[str, Any] | None,
) -> int:
    asset_ids: list[str] = []
    for scene in (scene_map or {}).get("scenes", []):
        if not isinstance(scene, dict):
            continue
        source_frames_list = scene.get("sourceFrames") if isinstance(scene.get("sourceFrames"), list) else []
        source_frame = scene.get("sourceFrame") if isinstance(scene.get("sourceFrame"), dict) else None
        candidates = [*source_frames_list, *([source_frame] if source_frame else [])]
        for item in candidates:
            if isinstance(item, dict) and isinstance(item.get("assetId"), str):
                asset_ids.append(item["assetId"])

    audio_plan = (reference_analysis or {}).get("audioPlan")
    reference_music = audio_plan.get("referenceMusic") if isinstance(audio_plan, dict) else None
    if isinstance(reference_music, dict) and isinstance(reference_music.get("assetId"), str):
        asset_ids.append(reference_music["assetId"])
    return cleanup_smart_remake_assets(asset_ids)


def _remove_asset_id(asset_id: str, directories: tuple[Path, ...]) -> int:
    if Path(asset_id).name != asset_id:
        return 0
    removed = 0
    for directory in directories:
        candidates = [directory / asset_id]
        if directory == audio_assets.AUDIO_ASSET_DIR and not asset_id.endswith(".m4a"):
            candidates.append(directory / f"{asset_id}.m4a")
        for path in candidates:
            if _remove_file(path):
                removed += 1
    return removed


def _remove_older_than(
    directories: tuple[Path, ...],
    cutoff: float,
    *,
    pattern: str = "*",
) -> int:
    removed = 0
    for directory in directories:
        if not directory.exists():
            continue
        for path in directory.glob(pattern):
            try:
                if path.is_file() and path.stat().st_mtime < cutoff and _remove_file(path):
                    removed += 1
            except OSError:
                continue
    return removed


def _remove_file(path: Path) -> bool:
    try:
        if not path.is_file():
            return False
        path.unlink()
        return True
    except OSError:
        return False
