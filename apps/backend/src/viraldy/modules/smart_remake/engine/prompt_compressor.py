from typing import Any

from .prompt_sanitizer import sanitize_reference_product_text


def _join_list(values: list[str]) -> str:
    return "; ".join(value.strip() for value in values if value and value.strip())


def _format_seconds(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else f"{value:.1f}".rstrip("0").rstrip(".")


def _unique_lines(lines: list[str]) -> list[str]:
    seen_headings = set()
    result = []
    for line in [line.strip() for line in lines if line and line.strip()]:
        is_heading = line.upper() == line and line[0].isalpha()
        if is_heading:
            if line in seen_headings:
                continue
            seen_headings.add(line)
        result.append(line)
    return result


def _product_identity_lines(product_lock: dict[str, Any]) -> list[str]:
    identity = product_lock.get("visualIdentity") or {}
    return [
        f"Target product: {product_lock.get('productName')}.",
        f"Product type: {product_lock.get('productType')}.",
        f"Visible colors: {_join_list(identity.get('colors') or [])}." if identity.get("colors") else "",
        f"Shape: {identity.get('shape')}." if identity.get("shape") else "",
        f"Material: {identity.get('material')}." if identity.get("material") else "",
        f"Texture: {identity.get('texture')}." if identity.get("texture") else "",
        f"Pattern: {identity.get('pattern')}." if identity.get("pattern") else "",
        "The uploaded product is the single hero product throughout the video.",
        "Do not substitute the source video's original object/tool, a generic product, or another similar product.",
        "Keep the same product silhouette, components, proportions, color placement, material, and texture across every cut.",
        "When the source structure has a product/tool action, the target product must be visibly present and performing that role.",
    ]


def _product_usage_lines(product_lock: dict[str, Any]) -> list[str]:
    usage = product_lock.get("productUsage") if isinstance(product_lock.get("productUsage"), dict) else {}
    return [
        "Use the target product in the same use-case and demo action sequence described by the reference video timeline.",
        "ProductUsage is only a physical guardrail for contact point, grip, scale, and impossible motion; it must not introduce a new use-case or new surface.",
        f"Realistic use cases: {_join_list(usage.get('realisticUseCases') or [])}." if usage.get("realisticUseCases") else "",
        f"Suitable surfaces/contexts: {_join_list(usage.get('suitableSurfaces') or [])}." if usage.get("suitableSurfaces") else "",
        f"Functional contact points: {_join_list(usage.get('contactPoints') or [])}." if usage.get("contactPoints") else "",
        f"Handling: {_join_list(usage.get('handlingInstructions') or [])}." if usage.get("handlingInstructions") else "",
        f"Usage constraints: {_join_list(usage.get('usageConstraints') or [])}." if usage.get("usageConstraints") else "",
        f"Never show: {_join_list(usage.get('forbiddenUsageErrors') or [])}." if usage.get("forbiddenUsageErrors") else "",
        "The active contact point of the product must touch the surface; do not use the wrong end, wrong scale, impossible bending, floating contact, or unrelated product motion.",
        "Do not invent a new product use-case, new surface, or alternate demo action that is not in the source timeline.",
    ]


def _causality_lines(timeline: dict[str, Any]) -> list[str]:
    shots = timeline.get("shots") if isinstance(timeline.get("shots"), list) else []
    transitions = [
        shot
        for shot in shots
        if isinstance(shot, dict) and shot.get("stateBefore") and shot.get("stateAfter")
    ]
    lines = [
        "DEMO CAUSALITY CONTRACT",
        "The reference timeline is the source of truth for the physical action and its visible effect, not loose inspiration.",
        "Preserve the same cause-and-effect direction: the target product must perform the source action and produce the source result/payoff.",
        "Do not reverse, weaken, replace, or reinterpret a demonstrated state transition, and do not add a negative side effect that is absent from the source.",
    ]
    if transitions:
        lines.append("Mandatory source state transitions; preserve each direction exactly:")
        lines.extend(
            f"SHOT {shot.get('shotIndex', 0) + 1}: {shot.get('stateBefore')} -> {shot.get('stateAfter')}."
            for shot in transitions
        )
    else:
        lines.append("No explicit state labels were available; follow every source action and result/payoff beat literally instead of inventing a different outcome.")
    lines.append("The final visible state must match the source result/payoff, with only the target product identity substituted.")
    return lines


def _source_fidelity_lines(analysis: dict[str, Any]) -> list[str]:
    setting = analysis.get("setting") if isinstance(analysis.get("setting"), dict) else {}
    actor = analysis.get("actorBehavior") if isinstance(analysis.get("actorBehavior"), dict) else {}
    creative = analysis.get("creativeConcept") if isinstance(analysis.get("creativeConcept"), dict) else {}
    return [
        "Preserve the reference video's scene realism: same type of environment, working surface, problem context, result reveal, and practical demo logic.",
        f"Reference setting type: {setting.get('locationType')}." if setting.get("locationType") else "",
        f"Reference background elements: {_join_list(setting.get('backgroundElements') or [])}." if setting.get("backgroundElements") else "",
        f"Reference human presence: {analysis.get('subjectPresence')}." if analysis.get("subjectPresence") else "",
        f"Reference gestures/interactions: {_join_list(actor.get('gestures') or [])}." if actor.get("gestures") else "",
        f"Reference product benefit moment: {creative.get('productMoment')}." if creative.get("productMoment") else "",
        "Keep the same demonstration sequence and use-case from the reference video; only swap the visible product identity/details.",
        "Avoid fake studio/showroom backgrounds, unrelated rooms, unrelated surfaces, or decorative lifestyle scenes unless the reference video actually uses them.",
        "Make the product effect visible: show the problem, the target product acting on it, and the result/payoff clearly.",
    ]


def _subject_line(subject_presence: str) -> str:
    if subject_presence == "none":
        return "Product-only scene. Do not invent an actor, presenter, face, or hands."
    if subject_presence == "hands_only":
        return "Generic hands only. Do not show a face, presenter, reviewer, or recognizable identity."
    return "Use an original generic presenter only. Do not copy identity, face, likeness, name, styling, or exact wording."


def _opening_image_lines(opening: dict[str, Any], first_shot: dict[str, Any] | None) -> list[str]:
    return [
        "EXACT FIRST FRAME",
        f"Composition: {(first_shot or {}).get('framing') or opening.get('framing')}.",
        f"Camera angle: {(first_shot or {}).get('cameraAngle') or opening.get('cameraAngle')}.",
        f"Camera movement at first frame: {(first_shot or {}).get('cameraMovement') or opening.get('cameraMovement')}.",
        _subject_line((first_shot or {}).get("subjectPresence") or opening.get("subjectPresence", "none")),
        f"Subject position: {opening.get('subjectPosition')}.",
        f"Product position: {opening.get('productPosition')}.",
        f"Product state: {(first_shot or {}).get('productState') or opening.get('productState')}.",
        f"Initial pose: {opening.get('initialPose')}.",
        f"Gaze direction: {opening.get('gazeDirection')}." if opening.get("gazeDirection") else "",
        f"Background: {_join_list(opening.get('backgroundLayout') or [])}.",
    ]


def _audio_lines(audio_plan: dict[str, Any]) -> list[str]:
    if audio_plan.get("mode") == "silent":
        return ["Audio mode: silent. No dialogue, no voiceover, no ambience, no sound effects, no music."]
    ref_music = audio_plan.get("referenceMusic") or {}
    extracted = ref_music.get("mode") == "extract"
    music_style_suffix = f" Reference style: {audio_plan.get('music')}." if audio_plan.get("music") else ""
    return [
        f"Dialogue: \"{audio_plan.get('dialogue')}\"" if audio_plan.get("dialogue") else "",
        f"Ambience: {audio_plan.get('ambience')}." if audio_plan.get("ambience") else "",
        f"Sound effects: {_join_list(audio_plan.get('soundEffects') or [])}." if audio_plan.get("soundEffects") else "",
        f"Music: use the separately muxed reference music bed; do not generate additional background music.{music_style_suffix}"
        if extracted
        else (f"Music: {audio_plan.get('music')}." if audio_plan.get("music") else ""),
        "No subtitles. No copied reference voice. Do not generate additional background music." if extracted else "No subtitles. No copied reference voice.",
    ]


def _timeline_lines(timeline: dict[str, Any], *, include_physical_execution: bool = True) -> list[str]:
    first = (timeline.get("shots") or [None])[0]
    lines = [
        "SHOT TIMELINE",
        "Follow this as the compressed full-reference edit script: same beat order, same relative rhythm, and same cut pacing from the whole source video.",
        f"This 8-second clip must contain {len(timeline.get('shots') or [])} distinct temporal shot(s)/cut segment(s) when listed below; do not collapse it into only 1-2 generic scenes.",
        "Each SHOT below is a full-screen time segment, not a grid, split-screen panel, storyboard cell, or collage tile.",
        "Do not merge, reorder, skip, replace, or reinterpret mandatory beats.",
        "Do not change the reference demo use-case, working surface, or way the product is used. The timeline action is the authority.",
        "Use fast, purposeful demo pacing: begin the useful product action immediately, avoid idle intros and beauty holds, and make every cut readable.",
        "For each demonstration beat, keep the target product visibly interacting with the source target/surface in the same way and show the practical effect or result before the next cut.",
        "The reference object's identity must not carry over; only the target uploaded product may occupy the product/tool role.",
        f"Pacing profile: {timeline.get('pacingProfile')}.",
        f"Visual structure: {timeline.get('visualStructure')}.",
        f"Opening duration: {_format_seconds(first.get('endSecond'))} seconds." if first else "",
        f"First cut timing: {_format_seconds(timeline['cutTimes'][0])} seconds." if timeline.get("cutTimes") else "",
        f"Cut times: {', '.join(_format_seconds(value) for value in timeline.get('cutTimes', []))} seconds." if timeline.get("cutTimes") else "Cut times: none; preserve continuous motion.",
    ]
    for shot in timeline.get("shots") or []:
        state = f"State transition: {shot.get('stateBefore')} -> {shot.get('stateAfter')}." if shot.get("stateBefore") and shot.get("stateAfter") else ""
        lines.extend(
            [
                f"SHOT {shot.get('shotIndex', 0) + 1} — {_format_seconds(shot.get('startSecond'))}–{_format_seconds(shot.get('endSecond'))}s",
                f"Role: {shot.get('priority')} {shot.get('role')}.",
                f"Framing: {shot.get('framing')}." if shot.get("framing") else "",
                f"Camera: {_join_list([value for value in [shot.get('cameraAngle'), shot.get('cameraMovement') or shot.get('cameraBehavior')] if value])}.",
                f"Action: {shot.get('action')}.",
                _physical_execution_line(shot.get("physicalAction")) if include_physical_execution else "",
                f"Product state: {shot.get('productState')}." if shot.get("productState") else "",
                state,
                f"Transition out: {shot.get('transitionOut')}." if shot.get("transitionOut") else "",
            ]
        )
    return lines


def _physical_execution_line(physical_action: Any) -> str:
    action = physical_action if isinstance(physical_action, dict) else {}
    labels = {
        "operator": "grip",
        "targetSurface": "target",
        "contactPoint": "contact",
        "movement": "movement",
        "visibleEffect": "effect",
    }
    details = [f"{label}: {action[key]}" for key, label in labels.items() if action.get(key)]
    return f"PHYSICAL EXECUTION: {'; '.join(details)}." if details else ""


def _source_segment_lines(source_segment: dict[str, Any] | None) -> list[str]:
    if not isinstance(source_segment, dict) or not source_segment:
        return []
    source_range = source_segment.get("sourceTimeRange") if isinstance(source_segment.get("sourceTimeRange"), dict) else {}
    boundary = source_segment.get("boundary") if isinstance(source_segment.get("boundary"), dict) else {}
    continuity = source_segment.get("continuity") if isinstance(source_segment.get("continuity"), dict) else {}
    order = source_segment.get("segmentOrder")
    count = source_segment.get("segmentCount")
    lines = [
        "SOURCE SEGMENT ASSIGNMENT",
        f"Execute only source segment {order} of {count}; do not replay, preview, or replace another source segment.",
        f"Reference source interval: {_format_seconds(source_range.get('startSecond'))}–{_format_seconds(source_range.get('endSecond'))} seconds."
        if source_range.get("startSecond") is not None and source_range.get("endSecond") is not None
        else "Execute only this scene's assigned source interval.",
    ]
    if boundary.get("kind") == "source_cut":
        lines.append(f"This segment begins at a real source cut; preserve its {boundary.get('cutStyle') or 'natural_cut'} boundary instead of adding an intro or transition.")
    elif boundary.get("kind") == "continuous_handoff":
        lines.append("This segment is a continuous handoff from the prior source action; continue the physical action, camera movement, and product state without a new intro or manufactured cut.")
    if continuity.get("previousState") or continuity.get("openingState"):
        lines.append(f"Continuity state: {continuity.get('previousState') or 'prior source state'} -> {continuity.get('openingState') or 'current source state'}.")
    return lines


def _motion_negative_lines(timeline: dict[str, Any]) -> list[str]:
    shot_count = len(timeline.get("shots") or [])
    if timeline.get("visualStructure") == "continuous" and shot_count <= 1:
        return ["Do not add hard cuts, jump cuts, split screen, collage, storyboard, or stacked panels."]
    if timeline.get("pacingProfile") == "fast_social":
        return ["No slow drift, lingering pause, idle opening, stretched simple action, beauty hold, collage, or grid layout."]
    if timeline.get("visualStructure") == "continuous":
        return ["Keep motion continuous, with no idle pauses, split screen, collage, storyboard, or stacked panels."]
    if timeline.get("pacingProfile") == "slow_cinematic":
        return ["No rushed montage, no abrupt jump cuts, no overly energetic camera motion."]
    return ["No unnecessary speed ramping, no overlong pauses, no collage, no split-screen unless explicitly in timeline."]


def build_compressed_smart_remake_prompts(
    *,
    analysis: dict[str, Any],
    product_lock: dict[str, Any],
    timeline: dict[str, Any],
    opening_shot: dict[str, Any],
    opening_forbidden_substitutions: list[str],
    display_order: int | None = None,
    scene_count: int | None = None,
    source_segment: dict[str, Any] | None = None,
    language: str | None = None,
) -> dict[str, str]:
    creative = analysis.get("creativeConcept") or {}
    summary = "\n".join(
        _unique_lines(
            [
                "SMART REMAKE SUMMARY",
                f"Scene {display_order + 1} of {scene_count}." if display_order is not None and scene_count is not None else "",
                f"Source segment {source_segment.get('segmentOrder')} of {source_segment.get('segmentCount')}." if isinstance(source_segment, dict) and source_segment else "",
                f"8-second vertical scene using {analysis.get('creativeArchetype') or creative.get('adType')} structure.",
                f"Hook: {creative.get('hook')}.",
                f"Product moment: {creative.get('productMoment')}.",
                f"Target product: {product_lock.get('productName')}.",
                f"Language context: {language}." if language else "",
            ]
        )
    )
    image_prompt = "\n".join(
        _unique_lines(
            [
                "IMAGE GENERATION",
                "Create one photorealistic 9:16 vertical still image for the first frame.",
                "Single coherent frame only. No collage, storyboard, grid, split screen, subtitles, UI, watermarks, or logos.",
                *_opening_image_lines(opening_shot, (timeline.get("shots") or [None])[0]),
                "SOURCE-FAITHFUL SCENE DNA",
                *_source_fidelity_lines(analysis),
                "TARGET PRODUCT IDENTITY",
                *_product_identity_lines(product_lock),
                "REALISTIC PRODUCT USAGE",
                *_product_usage_lines(product_lock),
                *[f"Preserve visibly: {item}." for item in (product_lock.get("mustPreserve") or [])[:4] if product_lock.get("mode") != "off"],
                *[f"Do not replace the opening with: {item}." for item in opening_forbidden_substitutions],
            ]
        )
    )
    video_prompt = "\n".join(
        _unique_lines(
            [
                "VIDEO GENERATION",
                "Create one 8-second 9:16 vertical clip that executes only the assigned source segment. Use the compiled source scene and timeline as the production brief, not a new creative concept."
                if source_segment
                else "Create one 8-second 9:16 vertical clip that condenses the full reference video, not only the first 8 seconds. Use the compiled source scene and timeline as the production brief, not a new creative concept.",
                "FAST PRODUCT-DEMO EDIT: start the useful action immediately, keep purposeful motion brisk, and show a clear practical result before the final frame.",
                "Keep the target product visually consistent with ProductLock throughout; it must not change into another object across scenes or cuts.",
                "Use the full reference video for pacing, camera rhythm, shot-role structure, background/demo sequence, and payoff; do not preserve the reference product/tool identity.",
                _subject_line(analysis.get("subjectPresence", "none")),
                "SOURCE-FAITHFUL SCENE DNA",
                *_source_fidelity_lines(analysis),
                *_source_segment_lines(source_segment),
                *_timeline_lines(timeline, include_physical_execution=bool(scene_count and scene_count > 1)),
                *_causality_lines(timeline),
                "CAMERA AND MOTION",
                f"Camera behavior: {(analysis.get('cameraStyle') or {}).get('movement')}.",
                *_motion_negative_lines(timeline),
                "PRODUCT CONSISTENCY",
                *_product_identity_lines(product_lock),
                "REALISTIC PRODUCT USAGE",
                *_product_usage_lines(product_lock),
                *[f"Preserve: {item}." for item in (product_lock.get("mustPreserve") or [])[:5] if product_lock.get("mode") != "off"],
                "AUDIO",
                *_audio_lines(analysis.get("audioPlan") or {}),
            ]
        )
    )
    return {
        "prompt": sanitize_reference_product_text(text=summary, analysis=analysis, product_lock=product_lock),
        "imagePrompt": sanitize_reference_product_text(text=image_prompt, analysis=analysis, product_lock=product_lock),
        "videoPrompt": sanitize_reference_product_text(text=video_prompt, analysis=analysis, product_lock=product_lock),
    }
