"""Bound changed directions without truncating user edits or product identity rules."""

from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any

from .errors import SmartRemakeValidationError

FIELDS = {
    "prompt": "Scene direction",
    "imagePrompt": "Visual appearance and starting frame",
    "videoPrompt": "Motion and video direction",
}
MAX_EDIT_DIRECTION = 2200


def _too_long() -> SmartRemakeValidationError:
    return SmartRemakeValidationError(
        "These edits exceed the provider's direction budget. "
        "Make fewer focused changes or use a concise scene description.",
        "SMART_REMAKE_EDIT_PROMPT_TOO_LONG",
    )


def _changed_context(current: str, original: str, label: str) -> list[str]:
    if current == original:
        return []
    prefix = 0
    while prefix < min(len(current), len(original)) and current[prefix] == original[prefix]:
        prefix += 1
    suffix = 0
    while (
        suffix < min(len(current), len(original)) - prefix
        and current[-1 - suffix] == original[-1 - suffix]
    ):
        suffix += 1
    old_end = len(original) - suffix
    new_end = len(current) - suffix
    old, new = original[prefix:old_end], current[prefix:new_end]
    matcher = SequenceMatcher(None, old, new, autojunk=max(len(old), len(new)) > 3000)
    if matcher.ratio() < 0.2 and len(current) <= 1600:
        return [f"{label} (replacement):\n{current}"]
    ranges: list[tuple[int, int]] = []
    removals = []
    for tag, a, b, c, d in matcher.get_opcodes():
        if tag == "equal":
            continue
        if tag == "delete":
            if b - a > 400:
                raise _too_long()
            removals.append(f"{label}: omit this former scene direction:\n{old[a:b]}")
        start, end = max(0, prefix + c - 75), min(len(current), prefix + d + 75)
        if ranges and start <= ranges[-1][1]:
            ranges[-1] = (ranges[-1][0], max(end, ranges[-1][1]))
        else:
            ranges.append((start, end))
    return [f"{label} (updated context):\n{current[start:end]}" for start, end in ranges] + removals


def scene_edit_directions(scene: dict[str, Any]) -> str:
    if not scene.get("promptEdited"):
        return ""
    changes = []
    for field, label in FIELDS.items():
        current = scene.get(field)
        if not isinstance(current, str) or not current.strip():
            continue
        if len(current) > 12000:
            raise _too_long()
        original = scene.get(f"original{field[0].upper()}{field[1:]}")
        if isinstance(original, str):
            changes.extend(_changed_context(current, original, label))
        else:
            changes.append(f"{label}:\n{current}")
    direction = "\n\n".join(changes)
    if len(direction) > MAX_EDIT_DIRECTION:
        raise _too_long()
    return direction
