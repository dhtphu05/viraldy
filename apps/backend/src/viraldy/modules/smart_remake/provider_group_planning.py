"""Freeze exactly one provider request per eight-second output window."""

from __future__ import annotations

import copy
from typing import Any

from viraldy.shared.errors.base import AppError

from .engine.video_directions import video_requirements
from .engine.video_requests import build_group_request, validate_video_input
from .generation_expectations import validate_generation_expectations


def _fixed_windows(plan: dict[str, Any], total_frames: int) -> bool:
    units = plan["units"]
    groups = plan.get("groups") or []
    if (
        plan.get("groupingPolicy") != "fixed_provider_windows"
        or total_frames not in {192, 384}
        or len(groups) != total_frames // 192
        or [identity for group in groups for identity in group["renderUnitIds"]]
        != [unit["id"] for unit in units]
    ):
        return False
    by_id = {unit["id"]: unit for unit in units}
    for group in groups:
        if group.get("rawDurationFrames") != 192 or group.get("targetDurationFrames") != 192:
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
        if cursor != 192:
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
            "Update the script to use one KIE request for eight seconds or two for sixteen.",
            409,
        )
    snapshot = validate_generation_expectations(context["generationExpectations"])
    units = {unit["id"]: unit for unit in plan["units"]}
    scenes = {scene["renderUnitId"]: scene for scene in snapshot["scenes"]}
    character = bool(context.get("characterKey"))
    prompt_context = {
        **context,
        "p0": {**context.get("p0", {}), "requirements": snapshot["requirements"]},
    }
    suffix = video_requirements(prompt_context)
    for group in plan["groups"]:
        identities = group["renderUnitIds"]
        request = build_group_request(
            model=plan.get("videoModel", "veo3_lite"),
            resolution=plan.get("videoResolution") or "720P",
            audio=bool(context.get("audioRequired")),
            scenes=[{**units[identity], **scenes[identity]} for identity in identities],
            segments=group["segments"],
            reference_image_urls=["https://1.1.1.1/opening.png", "https://1.1.1.1/ending.png"],
            has_character_reference=character,
            product_lock=snapshot["productLock"],
            reference_analysis=snapshot["sourceContext"],
        )
        request["input"]["prompt"] += suffix
        validate_video_input(request["model"], request["input"])
    return plan
