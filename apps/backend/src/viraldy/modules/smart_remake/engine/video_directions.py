"""Render a concise motion brief from canonical scenes without another model call."""

from __future__ import annotations

import ast
import json
import re
from collections import Counter
from typing import Any, cast

from .errors import SmartRemakeValidationError
from .performer_continuity import performer_continuity_directions
from .prompt_edits import scene_edit_directions

# Provenance stays in GenerationExpectations and operation records, never in Veo prose.
_PROVENANCE_FIELDS = frozenset({
    "renderUnitId", "sourceSceneId", "sourceRange", "openingFrame",
    "sourceMediaHash", "productMediaHash", "characterMediaHash", "layoutHash",
    "expectationsHash", "requirementsHash", "extractorVersion", "sourceTimeRange",
    "sourceSceneIndex", "sourceShotIndex", "sourceBeatIndex", "sourceDurationSeconds",
    "fragmentIndex", "fragmentCount", "segmentOrder", "segmentCount",
    "rawDurationFrames", "timingMode",
})


_SHOT_FIELDS = (
    "action", "physicalAction", "stateBefore", "stateAfter", "productState", "framing",
    "cameraAngle", "cameraMovement", "cameraBehavior", "subjectPresence", "transitionOut",
    "setting", "visualStructure", "shotType",
)
_BOILERPLATE = (
    "One photorealistic full-screen 9:16 opening frame.",
    "Recreate the observed actions, adapting their pace to that interval while preserving "
    "their order and physical cause and effect.",
    "Source evidence timestamps are provenance, not output timing.",
    "All timestamps below are local to this scene; the outer generation plan places this "
    "scene in its scheduled interval within the video.",
    "Preserve action order and physical cause and effect within the assigned interval.",
    "The seller will review a fixed-length selection before publishing; no selection is "
    "automatically approved.",
    "No frozen frames or invented/repeated actions.",
    "Do not copy reference product identity, faces, captions, or logos.",
)
_SENTENCES = re.compile(r"(?<=[.!?])\s+|\n+")
_PACING_FIELDS = ("pace", "motionIntensity", "cameraEnergy", "audioEnergy")


def _clean(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: cleaned for key, item in value.items()
            if key not in _PROVENANCE_FIELDS and (cleaned := _clean(item)) not in (None, "", [], {})
        }
    if isinstance(value, list):
        return [cleaned for item in value if (cleaned := _clean(item)) not in (None, "", [], {})]
    return value


def _seconds(value: float) -> int | float:
    rounded = round(float(value), 3)
    return int(rounded) if rounded.is_integer() else rounded


def _json(value: Any) -> str:
    return json.dumps(_clean(value), ensure_ascii=False, separators=(",", ":"))


def _normalized(text: str) -> str:
    return " ".join(text.split()).strip(" .;")


def common_language(scenes: list[dict[str, Any]]) -> str | None:
    values = {
        match.group(1).strip()
        for scene in scenes
        if re.match(r"Scene \d+ of \d+\. Execute the assigned ", scene.get("videoPrompt", ""))
        if (match := re.search(r"Language: ([^\n.]+)\.",
                               _protect_literals(scene.get("videoPrompt", ""))[0]))
    }
    return next(iter(values)) if len(values) == 1 else None


def shot_defaults(scenes: list[dict[str, Any]]) -> dict[str, str]:
    shots = [shot for scene in scenes for shot in (scene.get("shotPlan") or {}).get("shots", [])]
    defaults = {}
    for field in ("framing", "cameraAngle", "cameraMovement", "subjectPresence", "transitionOut"):
        if len(shots) < 3 or not all(isinstance(shot.get(field), str) for shot in shots):
            continue
        value, count = Counter(shot[field] for shot in shots).most_common(1)[0]
        if count >= 3:
            defaults[field] = value
    pacing = [(scene.get("shotPlan") or {}).get("pacingPlan") or {} for scene in scenes]
    for field in _PACING_FIELDS:
        values = [plan.get(field) for plan in pacing]
        if values and isinstance(values[0], str) and all(value == values[0] for value in values):
            defaults[field] = values[0]
    return defaults


def video_requirements(context: dict[str, Any]) -> str:
    requirements = (context.get("p0") or {}).get("requirements") or {}
    directions = {key: value for key, value in requirements.items()
                  if key not in {"requiresCharacter", "characterReferencePolicy"}}
    if not _clean(directions):
        return ""
    return (
        "\n\nSAVED REQUIREMENTS (all scenes; product identity and timing remain fixed): "
        + _json(directions)
    )


def window_brief(context: dict[str, Any]) -> str:
    """Describe this window's place in the film; all shot timestamps remain provider-local."""
    part = context.get("partIndex")
    if (
        type(part) is not int or part not in {1, 2} or context.get("partCount") != 2
        or context.get("totalDuration") != 12 or context.get("globalStart") != (part - 1) * 6
        or context.get("globalEnd") != part * 6
    ):
        raise SmartRemakeValidationError(
            "Window continuity must match the frozen two-part film.", "KIE_VALIDATION_FAILED",
        )
    parts = [
        f"PART {part} OF 2: {context['globalStart']}–{context['globalEnd']} seconds of one "
        "12-second film. The timestamps below are local to this part; perform only its assigned "
        "scenes in order.",
        "The supplied FIRST and LAST conditioning images are authoritative for boundary "
        "physical state, pose and layout. State analysis summaries below are context only, "
        "not verified instants; they cannot override the conditioning images when they conflict. "
        "Preserve every interior timed action and its order.",
        (
            "Begin the film, then handoff to the following part; this is not a complete ending. "
            "Do not add an outro, fade or concluding pose unless the analyzed scene explicitly "
            "requires it."
            if part == 1 else
            "Continue the same film, not a new introduction, recap or reprise. Do not restart or "
            "replay previous scenes; continue any unfinished action from the FIRST conditioning "
            "image."
        ),
    ]
    for key, label in (
        ("previousAction", "Previously shown (context only, do not replay)"),
        ("openingState", "Opening-state analysis summary (context only, not a verified instant)"),
        ("finalState", "Final-state analysis summary (context only, not a verified instant)"),
        ("nextOpeningState", "Next opening-state analysis summary "
         "(context only, not a verified instant)"),
        ("boundaryKind", "Source boundary evidence"),
    ):
        if isinstance(value := context.get(key), str) and value.strip():
            parts.append(f"{label}: {value.strip()}")
    parts.append(
        "Retain the analyzed cuts and changes of camera or state; story continuity does not "
        "mean an unbroken camera shot. Keep one consistent audio mood, rhythm and language; "
        "do not restart a music or voice introduction in each part. Do not recite a whole-video "
        "feature summary in this window."
    )
    dialogue = context.get("windowDialogue") or []
    if dialogue:
        parts.append("Dialogue evidence for this part only (no invented timestamps): "
                     + _json(dialogue))
    return "\n".join(parts)


def video_brief(
    product: dict[str, Any], context: dict[str, Any], *, ending: bool,
    language: str | None = None, defaults: dict[str, str] | None = None,
    duration_seconds: int = 8,
) -> str:
    identity = {key: product[key] for key in (
        "productName", "productType", "visualIdentity", "mustPreserve", "forbiddenErrors",
    ) if product.get(key)}
    usage = product.get("productUsage") or {}
    identity["physicalConstraints"] = {key: usage[key] for key in (
        "usageConstraints", "forbiddenUsageErrors", "contactPoints", "suitableSurfaces",
        "handlingInstructions",
    ) if usage.get(key)}
    audio = context.get("audioPlan") or {}
    source = {key: context[key] for key in (
        "setting", "subjectPresence", "actorBehavior",
    ) if context.get(key)}
    source["camera"] = {key: value for key, value in (context.get("cameraStyle") or {}).items()
                        if value not in (None, "", "mixed", "unknown")}
    source["audio"] = {key: audio[key] for key in (
        "mode", "music", "ambience", "dialogue", "language", "soundEffects",
    ) if audio.get(key)}
    return "\n\n".join(part for part in (
        f"Create exactly {duration_seconds} seconds, vertical 9:16. "
        "The FIRST image is the exact opening frame. "
        + ("The SECOND image is the exact final frame. " if ending else "")
        + "Follow every timed scene and action in order; retain analyzed cuts and continuous "
        "motion. Use split screen only where the scene explicitly calls for it. "
        "No unrelated footage, added captions or frozen padding. Preserve the conditioned "
        "person's facial features and appearance, and the target product's exact shape, "
        "proportions, "
        "components, colors, materials and visible branding throughout. Product constraints "
        "take precedence; never invent parts or mechanisms.",
        performer_continuity_directions(),
        "At rapid cuts, enter the next action already underway; cut cleanly instead of blending "
        "the previous actor or hand contacts into the next shot.",
        f"PRODUCT: {_json(identity)}" if _clean(identity) else "",
        f"CONTEXT: {_json(source)}" if _clean(source) else "",
        f"Scene/shot defaults (individual values override): {_json(defaults)}" if defaults else "",
        f"Language: {language}." if language else "",
    ) if part)


def _shot(
    shot: dict[str, Any], offset: float, defaults: dict[str, str] | None = None,
) -> dict[str, Any]:
    value = {key: shot[key] for key in _SHOT_FIELDS if shot.get(key) is not None}
    evidence = " ".join(str(shot.get(key) or "") for key in (
        "action", "stateBefore", "stateAfter", "productState",
    ))
    physical = shot.get("physicalAction")
    if isinstance(physical, dict):
        value["physicalAction"] = {
            key: item for key, item in physical.items()
            if not isinstance(item, str) or not _covered(item, evidence)
        }
    for key, default in (defaults or {}).items():
        if value.get(key) == default:
            value.pop(key)
    for key in ("startSecond", "endSecond"):
        observed = shot.get(key, shot.get("start" if key == "startSecond" else "end"))
        if isinstance(observed, int | float):
            value[key] = _seconds(offset + observed)
    if "startSecond" not in value or "endSecond" not in value:
        duration = shot.get("durationSeconds")
        value["durationSeconds"] = (
            _seconds(duration) if isinstance(duration, int | float) else duration
        )
    return cast(dict[str, Any], _clean(value))


def _covered(value: str, evidence: str) -> bool:
    # A literal whole phrase already in this shot remains visible in its original context.
    return bool(value.strip()) and re.search(
        r"(?<!\w)" + re.escape(value.strip()) + r"(?!\w)", evidence,
    ) is not None


def _timeline_text(shots: list[dict[str, Any]]) -> str:
    lines = []
    for shot in shots:
        timing = (
            f"{shot['startSecond']:g}–{shot['endSecond']:g}s: "
            if "startSecond" in shot and "endSecond" in shot else ""
        )
        facts = [str(shot["action"])] if shot.get("action") else []
        if shot.get("stateBefore") or shot.get("stateAfter"):
            facts.append(f"State: {shot.get('stateBefore', '?')} → {shot.get('stateAfter', '?')}")
        for key, value in shot.items():
            if key in {"action", "stateBefore", "stateAfter", "startSecond", "endSecond"}:
                continue
            if isinstance(value, dict):
                facts.append(f"{key}: " + "; ".join(f"{k}: {v}" for k, v in value.items()))
            else:
                facts.append(f"{key}: {value}")
        lines.append("- " + timing + "; ".join(facts))
    return "\n".join(lines)


def _beats(
    plan: dict[str, Any], shots: list[dict[str, Any]], offset: float,
    defaults: dict[str, str],
) -> list[dict[str, Any]]:
    """Retain distinct beat facts; repeated action at another time is never a duplicate."""
    result: list[dict[str, Any]] = []
    motion = plan.get("motionBeats") or []
    pacing = (plan.get("pacingPlan") or {}).get("actionBeats", [])
    candidates = motion + [beat for beat in pacing if not any(
        set(beat) <= {"sourceBeatIndex", "action", "durationSeconds"}
        and
        beat.get("sourceBeatIndex") is not None
        and beat.get("sourceBeatIndex") == other.get("sourceBeatIndex")
        and beat.get("action") == other.get("action")
        and beat.get("durationSeconds") == other.get("durationSeconds")
        for other in motion
    )]
    for beat in candidates:
        projected = _shot(beat, offset, defaults)
        if projected and not any(
            all(other.get(key) == value for key, value in projected.items())
            for other in shots + result
        ):
            result.append(projected)
    return result


def _protect_literals(text: str) -> tuple[str, dict[str, str]]:
    salt = 0
    while f"<<VIDEO_LITERAL_{salt}_" in text:
        salt += 1
    literals: dict[str, str] = {}

    def protect(match: re.Match[str]) -> str:
        key = f"<<VIDEO_LITERAL_{salt}_{len(literals)}>>"
        literals[key] = match.group(0)
        return key

    return re.sub(
        r"(?<!\w)(['\"])(?:\\.|(?!\1(?!\w)).)*?\1(?!\w)", protect, text, flags=re.S,
    ), literals


def _restore_literals(text: str, literals: dict[str, str]) -> str:
    for token, literal in literals.items():
        text = text.replace(token, literal)
    return text


def _strip_setting(
    match: re.Match[str], context: dict[str, Any], literals: dict[str, str],
) -> str:
    try:
        value = ast.literal_eval(_restore_literals(match.group(1), literals))
    except (SyntaxError, ValueError):
        return match.group(0)
    return "" if value == context.get("setting") else match.group(0)


def _residual(
    scene: dict[str, Any], product: dict[str, Any], context: dict[str, Any], language: str | None,
) -> list[str]:
    shots = (scene.get("shotPlan") or {}).get("shots") or []
    known = {key for shot in shots for _, key in _fragments(str(shot.get("action") or ""))}
    seen, result = set(known), []
    for field in ("prompt", "imagePrompt", "videoPrompt"):
        text = str(scene.get(field) or "").strip()
        if shots:
            text = _without_template(text, shots, product, context, language)
        for fragment, normalized in _fragments(text):
            if normalized and normalized not in seen:
                result.append(fragment.strip())
                seen.add(normalized)
    return result


def _fragments(text: str) -> list[tuple[str, str]]:
    protected, literals = _protect_literals(text)
    return [
        (_restore_literals(fragment.strip(), literals),
         _restore_literals(_normalized(fragment), literals))
        for fragment in _SENTENCES.split(protected)
    ]


def _without_template(
    text: str, shots: list[dict[str, Any]], product: dict[str, Any],
    context: dict[str, Any], language: str | None,
) -> str:
    identity, first = product.get("productName", ""), shots[0]
    prefix = re.sub(r"^Scene \d+ of \d+\.\s*", "", text)
    summary = f"{identity}. Source action: {first.get('action')}."
    image_prefix = (
        f"One photorealistic full-screen 9:16 opening frame. Use the uploaded {identity} "
    )
    if prefix.startswith(summary):
        return prefix[len(summary):]
    if prefix.startswith(image_prefix):
        ending = "Do not copy reference product identity, faces, captions, or logos."
    elif re.match(r"Scene \d+ of \d+\. Execute the assigned ", text):
        ending = "No frozen frames or invented/repeated actions."
    else:
        return text
    # Only remove known compiler prose; literal captions/dialogue appended by a seller stay intact.
    original = text
    text, literals = _protect_literals(text)
    at = text.find(ending)
    if at < 0:
        return original
    head, suffix = text[:at + len(ending)], text[at + len(ending):]
    text = head
    text = re.sub(r"^Scene \d+ of \d+\.\s*", "", text)
    text = re.sub(r"Setting: (\{[^\n]*?\}|None)\.(?= (?:Subject presence|Language):)",
                  lambda match: _strip_setting(match, context, literals), text)
    for literal in (
        *_BOILERPLATE,
        f"{identity}. Source action: ",
        f"Use the uploaded {identity} as the exact product identity; preserve its "
        "proportions, colors, material and branding.",
        f"Use only the uploaded {identity}, retaining exact product identity and physical use.",
        f"Subject presence: {context.get('subjectPresence')}.",
        f"Opening action/state: {first.get('action')}; {first.get('stateBefore') or ''}.",
        "SOURCE ACTION TIMELINE",
        f"Language: {language}." if language else "",
    ):
        if literal:
            text = text.replace(literal, "")
    text = re.sub(
        r"Execute the assigned [\d.]+-second source action "
        r"(?:within the assigned output interval|at its original speed)\.\s*", "", text,
    )
    camera = context.get("cameraStyle") or {}
    suffix = suffix.removeprefix("\nSOURCE ACTION TIMELINE\n")
    for shot in shots:
        if not all(isinstance(shot.get(key), int | float) for key in ("startSecond", "endSecond")):
            continue
        line = (
            f"{shot['startSecond']:g}–{shot['endSecond']:g}s: {shot.get('action', '')}. "
            f"Camera: {shot.get('cameraAngle') or camera.get('angle')}; "
            f"{shot.get('cameraMovement') or camera.get('movement')}. "
            f"State: {shot.get('stateBefore') or ''} → {shot.get('stateAfter') or ''}."
        )
        if not suffix.startswith(line):
            break
        suffix = suffix[len(line):].removeprefix("\n")
    return _restore_literals(text + suffix, literals)


def scene_brief(
    scene: dict[str, Any], *, start: int, end: int, index: int,
    product: dict[str, Any], context: dict[str, Any], language: str | None,
    defaults: dict[str, str] | None = None,
) -> str:
    plan = scene.get("shotPlan") or {}
    offset = start / 24
    shots = [_shot(shot, offset, defaults) for shot in plan.get("shots") or []]
    segment = scene.get("sourceSegment") or plan.get("sourceSegment") or {}
    details = {
        "cutTimes": [_seconds(offset + value) for value in plan.get("cutTimes") or []],
        "boundary": segment.get("boundary"), "continuity": segment.get("continuity"),
        "actionContext": {key: plan[key] for key in _SHOT_FIELDS if plan.get(key)
                          and not (key == "visualStructure"
                                   and plan[key] in {"continuous", "sequential_shots"})},
        "pacing": {key: value for key in _PACING_FIELDS
                   if (value := (plan.get("pacingPlan") or {}).get(key))
                   and value != (defaults or {}).get(key)},
    }
    parts = [f"[00:{start / 24:06.3f}–00:{end / 24:06.3f}] SCENE {index + 1}"]
    if shots:
        parts.append("Shots:\n" + _timeline_text(shots))
    if _clean(details):
        parts.append("Continuity: " + _json(details))
    if beats := _beats(plan, shots, offset, defaults or {}):
        parts.append("Supporting beats (refine, never contradict the shots):\n"
                     + _timeline_text(beats))
    if residual := _residual(scene, product, context, language):
        parts.append("Additional directions: " + " ".join(residual))
    edits = scene.get("userEdits") or scene_edit_directions(scene)
    if edits:
        parts.append("USER EDITS (creative override; product identity and timing stay fixed): "
                     + edits)
    return "\n".join(parts)
