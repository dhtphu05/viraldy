"""KIE's native Veo 3.1 image-to-video contract with conditioned frame bookends."""

from __future__ import annotations

from typing import Any

from viraldy.modules.product_import.security import validate_public_http_url
from viraldy.shared.errors.base import AppError

from .errors import SmartRemakeError, SmartRemakeValidationError
from .prompt_sanitizer import sanitize_generation_scene, validate_generation_payload
from .video_directions import common_language, scene_brief, shot_defaults, video_brief

KIE_MODEL = "veo-3-1"
KIE_IMAGE_TO_VIDEO_MODE = "FIRST_AND_LAST_FRAMES_2_VIDEO"
# KIE returned this limit in its verified 422 response; the published schema omits it.
KIE_MAX_PROMPT_CHARACTERS = 60000
_PROMPT_SECTION_SEPARATOR = "\n\n"
def public_media_url(value: str) -> str:
    try:
        return validate_public_http_url(value)
    except (AppError, ValueError) as exc:
        raise SmartRemakeError(
            "KIE media must use a publicly accessible HTTP or HTTPS URL.",
            "KIE_UNSAFE_MEDIA_URL",
        ) from exc


def _adapted_timing(scene: dict[str, Any]) -> bool:
    plan, source = scene.get("shotPlan") or {}, scene.get("sourceRange") or {}
    if plan.get("timingMode") == "fit_target":
        return True
    start, end, target = (
        source.get("startFrame"), source.get("endFrame"), scene.get("targetDurationFrames")
    )
    return (
        type(start) is int and type(end) is int and type(target) is int
        and end - start != target
    )


def build_kie_video_request(
    *,
    scene: dict[str, Any],
    product_image_url: str,
    product_lock: dict[str, Any] | None = None,
    reference_analysis: dict[str, Any] | None = None,
) -> dict[str, Any]:
    # Keep the existing argument name for callers; the image is a conditioned scene frame.
    scene = sanitize_generation_scene(scene, reference_analysis or {}, product_lock or {})
    image_url = public_media_url(product_image_url)
    target_frames = scene.get("targetDurationFrames", 192)
    if (
        type(target_frames) is not int or not 1 <= target_frames <= 192
        or ("targetDurationFrames" in scene and scene.get("rawDurationFrames") != 192)
    ):
        raise SmartRemakeValidationError(
            "Timeline scenes require a valid fixed target inside the raw eight-second clip.",
            "KIE_VALIDATION_FAILED",
        )
    analysis = reference_analysis or {}
    context = sanitize_generation_scene(analysis, analysis, product_lock or {})
    language = common_language([scene])
    defaults = shot_defaults([scene])
    parts = [
        video_brief(
            product_lock or {}, context, ending=False, language=language, defaults=defaults,
        ),
        scene_brief(
            scene, start=0, end=target_frames, index=0,
            product=product_lock or {}, context=context, language=language, defaults=defaults,
        ),
    ]
    if "targetDurationFrames" in scene:
        parts.append(
            f"Perform the assigned action within the first {target_frames / 24:g} seconds; "
            + ("fit its pace to the interval." if _adapted_timing(scene)
               else "preserve original speed.")
        )
    if target_frames < 192:
        parts.append(
            f"After {target_frames / 24:g}s continue the last action naturally; do not add "
            "cuts, repeat actions, stretch motion or freeze frames to fill eight seconds."
        )
    prompt = _PROMPT_SECTION_SEPARATOR.join(parts)
    validate_generation_payload(prompt, analysis, product_lock or {})
    data = {
        "model": "veo3_lite",
        "generation_type": KIE_IMAGE_TO_VIDEO_MODE,
        "image_urls": [image_url],
        "prompt": prompt,
        "aspect_ratio": "9:16",
        "duration": 8,
        "resolution": "720p",
        "enable_translation": False,
    }
    validate_kie_video_input(data)
    return {"model": KIE_MODEL, "input": data}


def validate_kie_video_input(data: dict[str, Any]) -> None:
    expected = {
        "model": "veo3_lite",
        "generation_type": KIE_IMAGE_TO_VIDEO_MODE,
        "aspect_ratio": "9:16",
        "duration": 8,
        "resolution": "720p",
        "enable_translation": False,
    }
    allowed = {*expected, "prompt", "image_urls"}
    if set(data) != allowed or any(data.get(key) != value for key, value in expected.items()):
        raise SmartRemakeValidationError(
            "Smart Remake KIE requests require Veo 3.1 Lite image-to-video, 9:16 and 8 seconds.",
            "KIE_VALIDATION_FAILED",
        )
    prompt = data.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        raise SmartRemakeValidationError(
            "The scene direction must be a nonempty string.",
            "KIE_VALIDATION_FAILED",
        )
    if len(prompt) > KIE_MAX_PROMPT_CHARACTERS:
        raise SmartRemakeValidationError(
            f"KIE Veo prompts cannot exceed {KIE_MAX_PROMPT_CHARACTERS} characters.",
            "KIE_VALIDATION_FAILED",
        )
    images = data.get("image_urls")
    if (
        not isinstance(images, list)
        or not 1 <= len(images) <= 2
        or any(not isinstance(image, str) for image in images)
    ):
        raise SmartRemakeValidationError(
            "Image-to-video requires an opening frame and optionally a final frame, in that order.",
            "KIE_VALIDATION_FAILED",
        )
    for image in images:
        public_media_url(image)


def build_kie_group_request(
    *,
    scenes: list[dict[str, Any]],
    segments: list[dict[str, Any]],
    reference_image_urls: list[str],
    has_character_reference: bool = False,
    product_lock: dict[str, Any] | None = None,
    reference_analysis: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not isinstance(reference_image_urls, list) or len(reference_image_urls) != 2:
        raise SmartRemakeValidationError(
            "A group requires exactly two conditioned images: opening and final frames, in order.",
            "KIE_VALIDATION_FAILED",
        )
    scenes = [
        sanitize_generation_scene(scene, reference_analysis or {}, product_lock or {})
        for scene in scenes
    ]
    if not scenes or len(scenes) != len(segments):
        raise SmartRemakeValidationError(
            "A group needs one direction per planned segment.", "KIE_VALIDATION_FAILED"
        )
    context = {
        name: value
        for name, value in (reference_analysis or {}).items()
        if name in {"subjectPresence", "cameraStyle", "setting", "actorBehavior", "audioPlan"}
    }
    context = sanitize_generation_scene(context, reference_analysis or {}, product_lock or {})
    language = common_language(scenes)
    defaults = shot_defaults(scenes)
    parts = [video_brief(
        product_lock or {}, context, ending=True, language=language, defaults=defaults,
    )]
    parts.append(
        "Fit actions to their assigned output intervals, preserving physical cause and effect."
        if any(_adapted_timing(scene) for scene in scenes) else "Preserve original action speed."
    )
    end = 0
    for index, (scene, segment) in enumerate(zip(scenes, segments, strict=True)):
        start, next_end = segment.get("inFrame"), segment.get("outFrame")
        if (
            type(start) is not int
            or type(next_end) is not int
            or start != end
            or not start < next_end <= 192
            or scene.get("targetDurationFrames", next_end - start) != next_end - start
        ):
            raise SmartRemakeValidationError(
                "Group scenes must cover contiguous frame ranges within eight seconds.",
                "KIE_VALIDATION_FAILED",
            )
        parts.append(scene_brief(
            scene, start=start, end=next_end, index=index,
            product=product_lock or {}, context=context, language=language, defaults=defaults,
        ))
        end = next_end
    if end < 192:
        parts.append(
            f"After {end / 24:g} seconds, continue the last action naturally without "
            "new cuts, repeated actions, stretching or frozen frames. "
            "Only the timestamped scene ranges will be selected for the final edit."
        )
    data = {
        "model": "veo3_lite",
        "generation_type": KIE_IMAGE_TO_VIDEO_MODE,
        "image_urls": list(reference_image_urls),
        "prompt": _PROMPT_SECTION_SEPARATOR.join(parts),
        "aspect_ratio": "9:16",
        "duration": 8,
        "resolution": "720p",
        "enable_translation": False,
    }
    validate_generation_payload(data["prompt"], reference_analysis or {}, product_lock or {})
    validate_kie_video_input(data)
    return {"model": KIE_MODEL, "input": data}
