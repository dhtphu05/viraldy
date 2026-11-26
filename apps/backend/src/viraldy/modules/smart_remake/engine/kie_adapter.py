"""KIE's native Veo 3.1 reference contract; no provider-specific image tokens."""

from __future__ import annotations

import json
import re
from collections import Counter
from typing import Any

from viraldy.modules.product_import.security import validate_public_http_url
from viraldy.shared.errors.base import AppError

from .errors import SmartRemakeError, SmartRemakeValidationError
from .prompt_edits import scene_edit_directions
from .prompt_sanitizer import sanitize_generation_scene, validate_generation_payload

KIE_MODEL = "veo-3-1"
# KIE returned this limit in its verified 422 response; the published schema omits it.
KIE_MAX_PROMPT_CHARACTERS = 60000
_PROMPT_SECTION_SEPARATOR = "\n\n"
_SHARED_SCENE_TEXT_PREFIX = (
    "Only in the JSON fields prompt, imagePrompt and videoPrompt, expand each "
    "shared-text reference to its exact literal below before following the directions. "
    "Apply all referenced instructions in full. Treat USER EDITS and all other fields "
    "literally. Never render tokens introduced as generated references in the video.\n"
    "SHARED SCENE DIRECTION TEXT: "
)


def public_media_url(value: str) -> str:
    try:
        return validate_public_http_url(value)
    except (AppError, ValueError) as exc:
        raise SmartRemakeError(
            "KIE media must use a publicly accessible HTTP or HTTPS URL.",
            "KIE_UNSAFE_MEDIA_URL",
        ) from exc


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _shared_scene_direction_text(
    directions: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    """Share exact repeated prose without removing any scene data or creative edits."""
    keys = ("prompt", "imagePrompt", "videoPrompt")
    sentences = re.compile(r"(?<=[.!?])(?=\s)")
    counts = Counter(
        fragment
        for direction in directions
        for key in keys
        if isinstance(value := direction.get(key), str)
        for fragment in sentences.split(value)
        if len(fragment) >= 64
    )
    original = _json(directions)
    salt = 0
    while (prefix := f"[[KIE_SHARED_TEXT_{salt}_") in original:
        salt += 1
    shared: dict[str, str] = {}
    references = {}
    for literal, count in counts.items():
        token = f"{prefix}{len(shared) + 1}]]"
        if count < 2 or count * len(_json(literal)) <= (
            count * len(_json(token)) + len(_json({token: literal}))
        ):
            continue
        shared[token] = literal
        references[literal] = token
    compact = [
        {
            **direction,
            **{
                key: "".join(references.get(fragment, fragment)
                             for fragment in sentences.split(value))
                for key in keys
                if isinstance(value := direction.get(key), str)
            },
        }
        for direction in directions
    ]
    overhead = len(_SHARED_SCENE_TEXT_PREFIX) + len(_PROMPT_SECTION_SEPARATOR)
    if not shared or len(_json(compact)) + len(_json(shared)) + overhead >= len(original):
        return directions, {}
    return compact, shared


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
    scene = sanitize_generation_scene(scene, reference_analysis or {}, product_lock or {})
    image_url = public_media_url(product_image_url)
    identity = {
        key: value
        for key, value in (product_lock or {}).items()
        if key
        in {
            "productName",
            "productType",
            "visualIdentity",
            "productUsage",
            "mustPreserve",
            "forbiddenErrors",
        }
    }
    plan = scene.get("shotPlan")
    has_plan = isinstance(plan, dict) and bool(plan.get("shots"))
    analysis = reference_analysis or {}
    context = {
        key: analysis[key]
        for key in (
            "subjectPresence",
            "cameraStyle",
            "setting",
            "actorBehavior",
            "audioPlan",
        )
        if analysis.get(key) is not None
    }
    context = sanitize_generation_scene(context, analysis, product_lock or {})
    video_direction = str(scene.get("videoPrompt") or scene.get("prompt") or "").strip()
    parts = [
        "Render exactly one full-screen 9:16, 8-second video. "
        "Cuts are sequential in time, never a collage, grid, storyboard or split screen.",
        "PRODUCT IDENTITY LOCK: The sole uploaded reference image is the exact target product. "
        "Preserve its shape, proportions, component layout, colors, material, texture and visible "
        "branding throughout every shot. Never replace it with the source's original product. "
        "Keep the target product visible during each product-action beat.",
        f"Product identity and physical constraints: {_json(identity)}" if identity else "",
        "Preserve the following source action order, cut timing and cause-and-effect direction. "
        "Do not reverse outcomes or add unrelated actions, b-roll or negative side effects.",
        f"Shot plan for this scene only: {_json(plan)}"
        if has_plan
        else f"Scene video direction: {video_direction}",
        f"Source segment boundaries and continuity: {_json(scene['sourceSegment'])}"
        if scene.get("sourceSegment")
        else "",
        f"Camera, setting, subjects and audio: {_json(context)}" if context else "",
        f"Canonical scene and opening: {_json({key: scene[key] for key in (
            'renderUnitId', 'sourceSceneId', 'sourceRange', 'openingFrame'
        ) if key in scene})}",
    ]
    target_frames = scene.get("targetDurationFrames")
    if target_frames is not None:
        if (
            type(target_frames) is not int
            or not 1 <= target_frames <= 192
            or scene.get("rawDurationFrames") != 192
        ):
            raise SmartRemakeValidationError(
                "Timeline scenes require a valid fixed target inside the raw eight-second clip.",
                "KIE_VALIDATION_FAILED",
            )
        timing = (
            "Follow the assigned output timing, adapted from the source, "
            if _adapted_timing(scene)
            else "Keep the assigned source action at its original speed "
        )
        padding = (
            "Never freeze or repeat the source action to fill eight seconds."
            if _adapted_timing(scene)
            else "Never slow down, stretch, freeze, or repeat the source action "
            "to fill eight seconds."
        )
        parts.extend(
            [
                f"TIMELINE SELECTION: {timing}"
                f"within the first {target_frames / 24:g} seconds of this raw 8-second clip. "
                "Continue naturally afterward without introducing a different action. "
                + padding,
                f"Opening visual direction: {scene.get('imagePrompt', '')}",
                f"Scene video direction: {video_direction}" if has_plan else "",
            ]
        )
    edits = scene.get("userEdits") or scene_edit_directions(scene)
    if edits:
        parts.append(
            "USER EDITS: Apply all directions below to this scene. They supersede the original "
            "scene directions while product identity, saved requirements, 8-second duration "
            "and segment boundaries "
            "remain fixed.\n" + edits
        )
    prompt = "\n\n".join(part for part in parts if part)
    validate_generation_payload(prompt, analysis, product_lock or {})
    data = {
        "model": "veo3_lite",
        "generation_type": "REFERENCE_2_VIDEO",
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
        "generation_type": "REFERENCE_2_VIDEO",
        "aspect_ratio": "9:16",
        "duration": 8,
        "resolution": "720p",
        "enable_translation": False,
    }
    allowed = {*expected, "prompt", "image_urls"}
    if set(data) != allowed or any(data.get(key) != value for key, value in expected.items()):
        raise SmartRemakeValidationError(
            "Smart Remake KIE requests require Veo 3.1 Lite, 9:16 and 8 seconds.",
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
        or not 1 <= len(images) <= 3
        or any(not isinstance(image, str) for image in images)
    ):
        raise SmartRemakeValidationError(
            "Smart Remake requires one to three image references, including the exact product.",
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
    parts = [
        "Create one full-screen vertical 9:16 video, exactly 8 seconds. "
        "Follow the timestamped scenes below in sequence using each scene's analyzed transition "
        "and continuity. Do not insert a hard cut into continuous action. Never create a collage, "
        "split screen, storyboard sheet or simultaneous panels. "
        + (
            "Follow each assigned output interval adapted from source timing, preserving "
            "action order and physical cause and effect."
            if any(_adapted_timing(scene) for scene in scenes)
            else "Preserve original action speed."
        ),
        "The FIRST reference image is the exact target product. Later references describe "
        "scene composition, not alternate products. Preserve the target product's shape, "
        "proportions, component layout, color, material and visible branding in EVERY scene. "
        "Never reproduce the source product when it differs from the target.",
        f"Target product identity and physical constraints: {_json(product_lock or {})}",
        f"Source camera, subjects, setting and audio continuity: {_json(context)}",
    ]
    if has_character_reference:
        parts.insert(2,
            "The SECOND reference image is the authorized target character identity. "
            "Preserve that person's facial features and appearance throughout; later images "
            "provide layout only and must not replace product or character identity."
        )
    directions, shared = _shared_scene_direction_text([
        {name: scene[name] for name in (
            "renderUnitId", "sourceSceneId", "sourceRange", "openingFrame", "prompt",
            "imagePrompt", "videoPrompt", "shotPlan", "sourceSegment",
        ) if scene.get(name)}
        for scene in scenes
    ])
    if shared:
        parts.append(_SHARED_SCENE_TEXT_PREFIX + _json(shared))
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
        edits = scene.get("userEdits") or scene_edit_directions(scene)
        parts.append(
            f"[00:{start / 24:06.3f}–00:{next_end / 24:06.3f}] SCENE {index + 1}\n"
            f"Scene direction (shotPlan times are local to THIS scene): {_json(directions[index])}"
            + (f"\nUSER EDITS supersede creative scene directions while exact product identity, "
               f"saved requirements, timing and segment boundaries remain fixed: {edits}"
               if edits else "")
        )
        end = next_end
    if end < 192:
        parts.append(
            f"After {end / 24:g} seconds, continue the last action naturally without "
            "new cuts, repeated actions, stretching or frozen frames. "
            "Only the timestamped scene ranges will be selected for the final edit."
        )
    data = {
        "model": "veo3_lite",
        "generation_type": "REFERENCE_2_VIDEO",
        "image_urls": reference_image_urls,
        "prompt": _PROMPT_SECTION_SEPARATOR.join(parts),
        "aspect_ratio": "9:16",
        "duration": 8,
        "resolution": "720p",
        "enable_translation": False,
    }
    validate_generation_payload(data["prompt"], reference_analysis or {}, product_lock or {})
    validate_kie_video_input(data)
    return {"model": KIE_MODEL, "input": data}
