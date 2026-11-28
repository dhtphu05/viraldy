"""Freeze exactly one provider request per saved output window."""

from __future__ import annotations

import copy
from typing import Any

from viraldy.shared.errors.base import AppError

from .engine.window_continuity import build_window_context
from .generation_expectations import validate_generation_expectations
from .provider_group_request import conditioned_group_request
from .timeline_schemas import provider_window_frames


def _fixed_windows(plan: dict[str, Any], total_frames: int) -> bool:
    units = plan["units"]
    groups = plan.get("groups") or []
    try:
        raw_frames = provider_window_frames(plan)
    except ValueError:
        return False
    if (
        plan.get("groupingPolicy") != "fixed_provider_windows"
        or total_frames not in {192, 288, 384}
        or (raw_frames == 144 and plan.get("audioRequired") is not True)
        or len(groups) != total_frames // raw_frames
        or [identity for group in groups for identity in group["renderUnitIds"]]
        != [unit["id"] for unit in units]
    ):
        return False
    by_id = {unit["id"]: unit for unit in units}
    for group in groups:
        if (
            group.get("rawDurationFrames") != raw_frames
            or group.get("targetDurationFrames") != raw_frames
        ):
            return False
        segments = group.get("segments") or []
        if len(segments) != len(group["renderUnitIds"]):
            return False
        cursor = 0
        for identity, segment in zip(group["renderUnitIds"], segments, strict=True):
            end = cursor + by_id[identity]["targetDurationFrames"]
            if segment != {"renderUnitId": identity, "inFrame": cursor, "outFrame": end}:
                return False
            cursor = end
        if cursor != raw_frames:
            return False
    return True


def freeze_provider_groups(context: dict[str, Any]) -> dict[str, Any]:
    """Validate complete provider requests without truncating scenes or adding paid calls."""
    plan: dict[str, Any] = copy.deepcopy(context["renderPlan"])
    if context.get("sourceSceneMap", {}).get("timingMode") != "fit_target":
        return plan
    total = sum(unit["targetDurationFrames"] for unit in plan["units"])
    if not _fixed_windows(plan, total):
        raise AppError(
            "SMART_REMAKE_PROVIDER_PLAN_UPDATE_REQUIRED",
            "Update the script to use the saved provider windows: two six-second calls for Wan.",
            409,
        )
    snapshot = validate_generation_expectations(context["generationExpectations"])
    units = {unit["id"]: unit for unit in plan["units"]}
    scenes = {scene["renderUnitId"]: scene for scene in snapshot["scenes"]}
    character = bool(context.get("characterKey"))
    for group in plan["groups"]:
        identities = group["renderUnitIds"]
        window_context = build_window_context(plan, group, snapshot)
        conditioned_group_request(
            context=context, plan=plan, snapshot=snapshot,
            duration_seconds=group["rawDurationFrames"] // 24,
            window_context=window_context,
            scenes=[{**units[identity], **scenes[identity]} for identity in identities],
            segments=group["segments"],
            has_character_reference=character,
        )
    return plan
