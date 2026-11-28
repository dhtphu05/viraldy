"""Pure final KIE directions shared by planning, draft preview and paid submission."""

from __future__ import annotations

from typing import Any

from .engine.prompt_sanitizer import validate_generation_payload
from .engine.video_directions import video_requirements
from .engine.video_requests import build_group_request, validate_video_input


def conditioned_group_request(
    *,
    context: dict[str, Any],
    plan: dict[str, Any],
    snapshot: dict[str, Any],
    scenes: list[dict[str, Any]],
    segments: list[dict[str, Any]],
    has_character_reference: bool,
) -> dict[str, Any]:
    # These literal image placeholders are never fetched, uploaded or sent to KIE.
    request = build_group_request(
        model=plan.get("videoModel", "veo3_lite"),
        resolution=plan.get("videoResolution") or "720P",
        audio=bool(context.get("audioRequired")),
        scenes=scenes,
        segments=segments,
        reference_image_urls=["https://1.1.1.1/opening.png", "https://1.1.1.1/ending.png"],
        has_character_reference=has_character_reference,
        product_lock=snapshot["productLock"],
        reference_analysis=snapshot.get("sourceContext", {}),
    )
    prompt_context = {
        **context,
        "p0": {**context.get("p0", {}), "requirements": snapshot.get("requirements", {})},
    }
    request["input"]["prompt"] += video_requirements(prompt_context)
    validate_video_input(request["model"], request["input"])
    validate_generation_payload(
        request["input"]["prompt"],
        context.get("referenceAnalysis", {}),
        snapshot["productLock"],
    )
    return request
