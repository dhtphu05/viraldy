"""Wan's first/last-frame contract around the shared Smart Remake scene prose."""
from __future__ import annotations

from typing import Any

from .errors import SmartRemakeValidationError
from .kie_adapter import build_kie_group_request, public_media_url

WAN_VIDEO_MODEL = "wan/3-0-video"
WAN_MAX_PROMPT_CHARACTERS = 20000
_FIELDS = {
    "prompt", "first_frame_url", "last_frame_url", "resolution",
    "duration", "aspect_ratio", "audio",
}


def validate_wan_video_input(data: dict[str, Any]) -> None:
    prompt = data.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > WAN_MAX_PROMPT_CHARACTERS:
        raise SmartRemakeValidationError(
            "Wan video directions must contain 1–20,000 characters; "
            "saved scenes are never truncated.",
            "KIE_VALIDATION_FAILED",
        )
    if (
        set(data) != _FIELDS
        or type(data.get("duration")) is not int or not 2 <= data["duration"] <= 30
        or data.get("resolution") not in {"480P", "720P", "1080P"}
        or data.get("aspect_ratio") != "9:16"
        or type(data.get("audio")) is not bool
        or any(not isinstance(data.get(key), str) for key in ("first_frame_url", "last_frame_url"))
    ):
        raise SmartRemakeValidationError(
            "Use Wan first/last-frame fields with a supported duration, "
            "resolution and audio setting.",
            "KIE_VALIDATION_FAILED",
        )
    public_media_url(data["first_frame_url"])
    public_media_url(data["last_frame_url"])


def build_wan_group_request(
    *,
    scenes: list[dict[str, Any]],
    segments: list[dict[str, Any]],
    reference_image_urls: list[str],
    has_character_reference: bool = False,
    product_lock: dict[str, Any] | None = None,
    reference_analysis: dict[str, Any] | None = None,
    audio: bool = False,
    resolution: str = "720P",
) -> dict[str, Any]:
    # Scene prose/timing is provider-independent. Never forward the Veo wire fields.
    directions = build_kie_group_request(
        scenes=scenes, segments=segments, reference_image_urls=reference_image_urls,
        has_character_reference=has_character_reference,
        product_lock=product_lock, reference_analysis=reference_analysis,
    )["input"]["prompt"]
    data = {
        "prompt": directions,
        "first_frame_url": reference_image_urls[0],
        "last_frame_url": reference_image_urls[1],
        "resolution": resolution, "duration": 8, "aspect_ratio": "9:16", "audio": audio,
    }
    validate_wan_video_input(data)
    return {"model": WAN_VIDEO_MODEL, "input": data}
