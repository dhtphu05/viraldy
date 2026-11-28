"""Derive story handoffs from one frozen film without exposing private identifiers."""

from __future__ import annotations

from typing import Any

from .errors import SmartRemakeValidationError

WINDOW_CONTINUITY_VERSION = "two-part-film-v1"


def _invalid() -> SmartRemakeValidationError:
    return SmartRemakeValidationError(
        "Window continuity must match the frozen two-part film.",
        "KIE_VALIDATION_FAILED",
    )


def _shot(scene: dict[str, Any], *, ending: bool = False) -> dict[str, Any]:
    shots = (scene.get("shotPlan") or {}).get("shots") or []
    return shots[-1 if ending else 0] if shots else {}


def _state(scene: dict[str, Any], *, ending: bool = False) -> str | None:
    shot = _shot(scene, ending=ending)
    value = shot.get("stateAfter" if ending else "stateBefore") or shot.get("productState")
    return value.strip() if isinstance(value, str) and value.strip() else None


def _dialogue(scenes: list[dict[str, Any]]) -> list[str]:
    values = []
    for scene in scenes:
        plan = scene.get("shotPlan") or {}
        candidates = [(plan.get("audioPlan") or {}).get("dialogue")]
        source = scene.get("sourceRange") or {}
        for shot in plan.get("shots") or []:
            timing = shot.get("sourceTimeRange") or {}
            start, end = timing.get("startSecond"), timing.get("endSecond")
            if (
                isinstance(start, int | float)
                and not isinstance(start, bool)
                and isinstance(end, int | float)
                and not isinstance(end, bool)
                and type(source.get("startFrame")) is int
                and type(source.get("endFrame")) is int
                and source["startFrame"] / 24 <= start < end <= source["endFrame"] / 24
            ):
                candidates.append(shot.get("dialogue"))
        for value in candidates:
            if isinstance(value, str) and value.strip() and value.strip() not in values:
                values.append(value.strip())
    return values


def build_window_context(
    plan: dict[str, Any],
    group: dict[str, Any],
    snapshot: dict[str, Any],
) -> dict[str, Any] | None:
    """Only new 12-second plans gain handoffs; historical 8/16-second inputs stay exact."""
    groups = plan.get("groups") or []
    if (
        plan.get("videoModel") != "wan/3-0-video"
        or len(groups) != 2
        or any(
            item.get("rawDurationFrames") != 144 or item.get("targetDurationFrames") != 144
            for item in groups
        )
    ):
        return None
    try:
        index = next(index for index, value in enumerate(groups) if value["id"] == group["id"])
        if groups[index] != group:
            raise _invalid()
        by_id = {scene["renderUnitId"]: scene for scene in snapshot["scenes"]}
        parts = [[by_id[identity] for identity in item["renderUnitIds"]] for item in groups]
        current = parts[index]
        first, last = current[0], current[-1]
    except (KeyError, TypeError, IndexError, StopIteration):
        raise _invalid() from None
    first_plan = first.get("shotPlan") or {}
    segment = first.get("sourceSegment") or first_plan.get("sourceSegment") or {}
    value = {
        "partIndex": index + 1,
        "partCount": len(groups),
        "globalStart": index * 6,
        "globalEnd": (index + 1) * 6,
        "totalDuration": 12,
        "previousAction": _shot(parts[index - 1][-1], ending=True).get("action") if index else None,
        "openingState": _state(first),
        "finalState": _state(last, ending=True),
        "nextOpeningState": _state(parts[index + 1][0]) if index + 1 < len(parts) else None,
        # This is retained evidence, not an inference of identical pixels or a seamless cut.
        "boundaryKind": (segment.get("boundary") or {}).get("kind", "unknown"),
    }
    if dialogue := _dialogue(current):
        value["windowDialogue"] = dialogue
    return value
