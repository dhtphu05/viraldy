"""Validate logical source coverage independently from provider and edit clocks."""

from __future__ import annotations

from typing import Any


def _require(condition: bool) -> None:
    if not condition:
        raise ValueError("Invalid saved timeline manifest")


def _source_ranges(source: dict[str, Any], total: int, ids: set[str]) -> dict[str, dict[str, Any]]:
    adapted = source.get("timingMode", "source_rhythm") == "fit_target"
    _require(source.get("timingMode", "source_rhythm") in {"source_rhythm", "fit_target"})
    start, count = source["sourceStartFrame"], source["sourceFrameCount"]
    _require(type(start) is int and start >= 0 and type(count) is int and count > start)
    _require(bool(source["scenes"]) and (not adapted or start == 0))
    cursor, assigned = start, 0
    scenes = {}
    for shot in source["scenes"]:
        left, right, length = shot["startFrame"], shot["endFrame"], shot["targetDurationFrames"]
        _require(type(left) is int and type(right) is int and left == cursor < right <= count)
        _require(type(length) is int and length > 0)
        _require(adapted or (right - left == length and length <= 192))
        _require(isinstance(shot["id"], str) and bool(shot["id"]) and shot["id"] not in ids)
        ids.add(shot["id"])
        scenes[shot["id"]] = shot
        cursor, assigned = right, assigned + length
    _require(assigned == total and (not adapted or cursor == count))
    return scenes


def _fragment_ranges(
    unit: dict[str, Any], shot: dict[str, Any], index: int, count: int, adapted: bool
) -> tuple[int, int]:
    left = unit.get("sourceStartFrame", shot["startFrame"])
    right = unit.get("sourceEndFrame", shot["endFrame"])
    _require(type(left) is int and type(right) is int and left < right <= shot["endFrame"])
    _require(unit.get("fragmentIndex", 0) == index and unit.get("fragmentCount", 1) == count)
    _require(type(unit.get("fragmentIndex", 0)) is int)
    _require(type(unit.get("fragmentCount", 1)) is int)
    _require(adapted or (left == shot["startFrame"] and right == shot["endFrame"]))
    return left, right


def _provider_fragments(
    state: dict[str, Any], shots: dict[str, dict[str, Any]], ids: set[str]
) -> None:
    source, plan, timeline = (
        state[key] for key in ("sourceSceneMap", "renderPlan", "draftTimeline")
    )
    adapted = source.get("timingMode") == "fit_target"
    units, items, scenes = plan["units"], timeline["items"], state["scenes"]
    _require(1 <= len(units) == len(items) == len(scenes))
    counts = {shot_id: sum(unit["sourceSceneId"] == shot_id for unit in units) for shot_id in shots}
    _require(all(counts.values()) and (adapted or all(count == 1 for count in counts.values())))
    source_cursor = {shot_id: shot["startFrame"] for shot_id, shot in shots.items()}
    assigned = {shot_id: 0 for shot_id in shots}
    fragments = {shot_id: 0 for shot_id in shots}
    source_order = {shot_id: index for index, shot_id in enumerate(shots)}
    offset, previous_source = 0, 0
    for index, (unit, item, scene) in enumerate(zip(units, items, scenes, strict=True)):
        shot_id, length = unit["sourceSceneId"], unit["targetDurationFrames"]
        _require(shot_id in shots and type(length) is int and 1 <= length <= 192)
        source_index = source_order[shot_id]
        _require(source_index in {previous_source, previous_source + 1})
        left, right = _fragment_ranges(
            unit, shots[shot_id], fragments[shot_id], counts[shot_id], adapted
        )
        _require(left == source_cursor[shot_id])
        _require(unit["id"] == scene["id"] == item["renderUnitId"])
        _require(item["sourceSceneId"] == shot_id)
        _require(type(unit["sceneIndex"]) is int and unit["sceneIndex"] == scene["index"] == index)
        _require(unit["rawDurationFrames"] == 192)
        _require(item["targetDurationFrames"] == length and item["targetStartFrame"] == offset)
        for value in (unit["id"], item["id"]):
            _require(isinstance(value, str) and bool(value) and value not in ids)
            ids.add(value)
        source_cursor[shot_id] = right
        assigned[shot_id] += length
        fragments[shot_id] += 1
        offset, previous_source = offset + length, source_index
    _require(offset == timeline["totalFrames"])
    _require(all(source_cursor[key] == shot["endFrame"] for key, shot in shots.items()))
    _require(all(assigned[key] == shot["targetDurationFrames"] for key, shot in shots.items()))


def validate_timeline_structure(state: dict[str, Any], context: dict[str, Any]) -> set[str]:
    """Return domain IDs only after complete source, render and output coverage agree."""
    source, plan, timeline = (
        state[key] for key in ("sourceSceneMap", "renderPlan", "draftTimeline")
    )
    _require(state["schemaVersion"] == 2 and context["schemaVersion"] == 2)
    _require(source == context["sourceSceneMap"] and plan == context["renderPlan"])
    _require(source["fps"] == plan["fps"] == timeline["fps"] == 24)
    _require(plan["provider"] == state["provider"] == "kie")
    _require(timeline["totalFrames"] in (192, 384))
    _require(timeline["totalFrames"] == state["targetDuration"] * 24)
    ids: set[str] = set()
    shots = _source_ranges(source, timeline["totalFrames"], ids)
    _provider_fragments(state, shots, ids)
    return ids
