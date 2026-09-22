from typing import Any

from .errors import SmartRemakeValidationError


MAX_UNIFICALLY_VIDEO_PROMPT_CHARS = 5000
MAX_UNIFICALLY_SCENE_PROMPT_CHARS = 2200
MAX_UNIFICALLY_SHOT_ACTION_CHARS = 260
MAX_UNIFICALLY_PHYSICAL_ACTION_CHARS = 520
UNIFICALLY_VEO_INPUT_KEYS = {
    "prompt",
    "aspect_ratio",
    "duration",
    "seed",
    "start_image_url",
    "end_image_url",
    "reference_image_urls",
    "reference_characters",
    "voice",
}


def _join_list(values: list[str]) -> str:
    return "; ".join(str(value).strip() for value in values if str(value).strip())


def _product_reference_text(product_lock: dict[str, Any] | None) -> str:
    if not product_lock:
        return "Use the uploaded product reference as the visual source of truth."
    identity = product_lock.get("visualIdentity") if isinstance(product_lock.get("visualIdentity"), dict) else {}
    usage = product_lock.get("productUsage") if isinstance(product_lock.get("productUsage"), dict) else {}
    preserve = product_lock.get("mustPreserve") if isinstance(product_lock.get("mustPreserve"), list) else []
    lines = [
        f"Exact target product name: {product_lock.get('productName')}." if product_lock.get("productName") else "",
        f"Exact target product type: {product_lock.get('productType')}." if product_lock.get("productType") else "",
        f"Exact target product colors: {_join_list(identity.get('colors') or [])}." if identity.get("colors") else "",
        f"Exact target product pattern: {identity.get('pattern')}." if identity.get("pattern") else "",
        f"Exact target product shape: {identity.get('shape')}." if identity.get("shape") else "",
        f"Exact target product material: {identity.get('material')}." if identity.get("material") else "",
        f"Exact target product texture: {identity.get('texture')}." if identity.get("texture") else "",
        f"Exact target product visible branding: {identity.get('visibleBranding')}." if identity.get("visibleBranding") else "",
        f"Must preserve from product reference: {_join_list(preserve)}." if preserve else "",
        f"Realistic use cases: {_join_list(usage.get('realisticUseCases') or [])}." if usage.get("realisticUseCases") else "",
        f"Suitable surfaces/contexts: {_join_list(usage.get('suitableSurfaces') or [])}." if usage.get("suitableSurfaces") else "",
        f"Functional contact points: {_join_list(usage.get('contactPoints') or [])}." if usage.get("contactPoints") else "",
        f"Handling instructions: {_join_list(usage.get('handlingInstructions') or [])}." if usage.get("handlingInstructions") else "",
        f"Usage constraints: {_join_list(usage.get('usageConstraints') or [])}." if usage.get("usageConstraints") else "",
        f"Forbidden usage errors: {_join_list(usage.get('forbiddenUsageErrors') or [])}." if usage.get("forbiddenUsageErrors") else "",
    ]
    return "\n".join(line for line in lines if line) or "Use the uploaded product reference as the visual source of truth."


def _video_product_identity_text(product_lock: dict[str, Any] | None) -> str:
    if not product_lock:
        return "Use the uploaded product reference as the visual source of truth."
    identity = product_lock.get("visualIdentity") if isinstance(product_lock.get("visualIdentity"), dict) else {}
    preserve = product_lock.get("mustPreserve") if isinstance(product_lock.get("mustPreserve"), list) else []
    lines = [
        f"Target colors: {_join_list(identity.get('colors') or [])}." if identity.get("colors") else "",
        f"Target shape: {identity.get('shape')}." if identity.get("shape") else "",
        f"Target material/texture: {_join_list([identity.get('material'), identity.get('texture')])}."
        if identity.get("material") or identity.get("texture")
        else "",
        f"Must preserve: {_join_list(preserve)}." if preserve else "",
    ]
    return "\n".join(line for line in lines if line) or "Use the uploaded product reference as the visual source of truth."


def _unifically_identity_prefix(product_lock: dict[str, Any] | None) -> str:
    return "\n".join(
        [
            "STRICT PRODUCT IDENTITY LOCK",
            "The uploaded product reference image is the exact target product.",
            "Copy the uploaded product reference's exact silhouette, proportions, geometry, component layout, colors, pattern, material, texture, and visible branding.",
            "Do not redesign, recolor, simplify, embellish, morph, or reconstruct the target product from the source video.",
            "Do not replace the target product with a different product, generic tool, catalog item, or invented variant.",
            "The target product must be visibly present as the hero product; do not generate only the problem surface or only the result.",
            _product_reference_text(product_lock),
        ]
    )


def _character_name(product_lock: dict[str, Any] | None) -> str:
    if not product_lock:
        return "Target Product"
    reference = product_lock.get("productReference") if isinstance(product_lock.get("productReference"), dict) else {}
    return (
        str(reference.get("characterName") or product_lock.get("productName") or product_lock.get("productType") or "Target Product")
        .strip()
        or "Target Product"
    )


def _video_identity_prefix(product_lock: dict[str, Any] | None, *, product_token: str = "@Image1") -> str:
    return "\n".join(
        [
            "STRICT PRODUCT IDENTITY LOCK",
            f"{product_token} is the exact user-uploaded target product.",
            f"Every visible product in the video must be {product_token}.",
            f"PRODUCT IDENTITY PRIORITY: {product_token} is the sole product identity authority; any source or scene frame is context only and must never supply product pixels or identity.",
            "Keep source frames only for background/demo/action context, never for product identity.",
            "DEMO CAUSALITY LOCK: the source shot map and compiled video prompt define the physical action and visible result.",
            f"Preserve the source cause-and-effect direction with {product_token}; do not reverse, weaken, replace, or reinterpret the demonstrated result.",
            "Do not add a negative side effect or make the demonstrated result worse when that side effect is absent from the source.",
            f"The source video's original object/tool is creative context only; replace its role with {product_token}.",
            f"{product_token} must stay visibly present and actively used in every shot where the source structure has a product/tool action.",
            f"Preserve {product_token}'s exact silhouette, proportions, geometry, component layout, colors, pattern, material, texture, and visible branding in every frame.",
            f"Keep {product_token} consistent across cuts: no redesign, color shift, component change, or morphing.",
            f"Do not replace {product_token} with a different product, generic tool, catalog item, or invented variant.",
            f"Do not show only the target surface, result, or hand motion without {product_token} during a product-action beat.",
            f"Use {product_token} in the same use-case and demo action sequence described by the source timeline.",
            "ProductUsage is only a physical guardrail for grip, scale, contact point, and impossible motion; it must not introduce a new use-case or alternate demonstration.",
            "Do not invent a different surface, target, product use, or alternate demonstration.",
            _video_product_identity_text(product_lock),
        ]
    )


def _single_frame_prefix() -> str:
    return "\n".join(
        [
            "SINGLE FULL-SCREEN 9:16 OUTPUT",
            "Render one single full-screen vertical video output.",
            "Never create a collage, split screen, grid, four panels, storyboard, before/after layout, contact sheet, or multiple simultaneous frames.",
            "Any cuts or shots described below are temporal edits over time, not panels shown at once.",
        ]
    )


def _format_seconds(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "?"
    return str(int(number)) if number.is_integer() else f"{number:.1f}".rstrip("0").rstrip(".")


def _shot_plan_prefix(
    scene: dict[str, Any],
    *,
    include_physical_execution: bool = True,
    include_source_scope: bool = True,
) -> str:
    plan = scene.get("shotPlan") if isinstance(scene.get("shotPlan"), dict) else {}
    shots = plan.get("shots") if isinstance(plan.get("shots"), list) else []
    shot_count = int(plan.get("shotCount") or len(shots) or 0)
    if shot_count <= 1 or not shots:
        return ""

    lines = [
        "MANDATORY MULTI-SHOT CUT MAP",
        f"Create {shot_count} distinct temporal shots/cut segments inside this single 8-second video.",
        "Return exactly one 8-second video output; these are cuts over time inside that one output, not multiple videos or panels.",
        "Do not collapse this into only 1-2 scenes, one continuous demonstration shot, one generic product shot, or a slow two-shot demo.",
        "Every listed shot is sequential over time and full-screen, never a split screen, grid, collage, or storyboard panel.",
        "The first useful product action begins immediately; do not spend the opening on idle posing, an establishing hold, or a beauty shot.",
        "For each demonstration shot, show the target product interacting with the source target/surface in the same way and make the visible practical effect readable before the next cut.",
    ]
    if include_source_scope:
        lines.insert(
            5,
            "Render only the listed source shots below. Do not add b-roll, establishing shots, repeated actions, filler transitions, or unrelated product shots.",
        )
    cut_times = plan.get("cutTimes") if isinstance(plan.get("cutTimes"), list) else []
    if cut_times:
        lines.append(f"Cut at approximately: {', '.join(_format_seconds(value) for value in cut_times)} seconds.")
    for index, shot in enumerate(shots[:12], start=1):
        action = _truncate_inline(
            str(shot.get("action") or "continue the source demo action").strip(),
            MAX_UNIFICALLY_SHOT_ACTION_CHARS,
        )
        role = str(shot.get("role") or "action").strip()
        start = _format_seconds(shot.get("startSecond"))
        end = _format_seconds(shot.get("endSecond"))
        lines.append(f"{start}-{end}s {role}: {action}")
        if include_physical_execution:
            physical_execution = _physical_execution_text(shot.get("physicalAction"))
            if physical_execution:
                lines.append(physical_execution)
        if shot.get("stateBefore") and shot.get("stateAfter"):
            lines.append(f"State transition: {shot.get('stateBefore')} -> {shot.get('stateAfter')} (preserve this direction).")
    return "\n".join(lines)


def _physical_execution_text(physical_action: Any) -> str:
    action = physical_action if isinstance(physical_action, dict) else {}
    labels = {
        "operator": "grip",
        "targetSurface": "target",
        "contactPoint": "contact",
        "movement": "movement",
        "visibleEffect": "effect",
    }
    details = [f"{label}: {str(action[key]).strip()}" for key, label in labels.items() if str(action.get(key) or "").strip()]
    if not details:
        return ""
    return _truncate_inline(f"PHYSICAL EXECUTION: {'; '.join(details)}.", MAX_UNIFICALLY_PHYSICAL_ACTION_CHARS)


def _cut_execution_suffix(scene: dict[str, Any]) -> str:
    plan = scene.get("shotPlan") if isinstance(scene.get("shotPlan"), dict) else {}
    shots = plan.get("shots") if isinstance(plan.get("shots"), list) else []
    shot_count = int(plan.get("shotCount") or len(shots) or 0)
    if shot_count <= 1:
        return ""
    cut_times = plan.get("cutTimes") if isinstance(plan.get("cutTimes"), list) else []
    return "\n".join(
        [
            "FINAL CUT EXECUTION",
            f"Render exactly {shot_count} distinct sequential full-screen shots inside this one 8-second video.",
            f"Cut near: {', '.join(_format_seconds(value) for value in cut_times)} seconds." if cut_times else "Use the listed shot boundaries for the cuts.",
            "Do not collapse the edit into a slow continuous take or only 1-2 shots. Every shot must advance the original demo action or payoff.",
        ]
    )


def _product_demo_execution_suffix(
    scene: dict[str, Any],
    product_lock: dict[str, Any] | None,
    *,
    product_token: str,
    include_physical_execution: bool = True,
) -> str:
    usage = product_lock.get("productUsage") if isinstance((product_lock or {}).get("productUsage"), dict) else {}
    plan = scene.get("shotPlan") if isinstance(scene.get("shotPlan"), dict) else {}
    shots = plan.get("shots") if isinstance(plan.get("shots"), list) else []
    if include_physical_execution:
        lines = [
            "FINAL PRODUCT DEMO EXECUTION",
            f"Every source action below is a mandatory physical demonstration: {product_token} must make the same source target/surface contact and movement; the visible result must be caused by {product_token}, never appear independently or before contact.",
            f"Keep {product_token} visible at the active contact point; no hand-only gesture, beauty hold, or unrelated result shot.",
            "Enter each cut already in the useful action. Make the source before -> in-use -> after evidence readable, then cut as soon as the beat is legible.",
            "Do not slow, embellish, or invent a different use-case. ProductUsage only makes the source demo mechanically plausible.",
        ]
    else:
        lines = [
            "FINAL PRODUCT DEMO EXECUTION",
            "Every source action below is a mandatory physical demonstration, not a generic product showcase.",
            f"Perform each action with {product_token} on the same source target/surface, contact, movement, and cause-and-effect.",
            f"Keep {product_token} visible at the active contact point; no hand-only gesture, beauty hold, or unrelated result shot.",
            "Enter each cut already in the useful action. Use each short shot for the action and visible effect, then cut as soon as the beat is legible.",
            "Do not slow, embellish, or invent a different use-case. ProductUsage only makes the source demo mechanically plausible.",
        ]
    if usage.get("contactPoints"):
        lines.append(f"Functional contact point: {_join_list(usage['contactPoints'])}.")
    if usage.get("realisticUseCases"):
        lines.append(f"Supported product use: {_join_list(usage['realisticUseCases'])}.")
    if usage.get("handlingInstructions"):
        lines.append(f"Required handling: {_join_list(usage['handlingInstructions'])}.")
    if usage.get("usageConstraints"):
        lines.append(f"Physical constraints: {_join_list(usage['usageConstraints'])}.")
    if shots:
        lines.append("Execute every action in the mandatory cut map in order; do not skip, merge, or replace a product-action beat.")
        if include_physical_execution:
            for shot in shots[:8]:
                physical_execution = _physical_execution_text(shot.get("physicalAction"))
                if physical_execution:
                    lines.append(f"Required {physical_execution}")
    return "\n".join(lines)


def _truncate_inline(value: str, max_chars: int) -> str:
    if len(value) <= max_chars:
        return value
    return f"{value[: max_chars - 3].rstrip()}..."


def _reference_rhythm_prefix(*, product_token: str = "@Image1") -> str:
    return "\n".join(
        [
            "REFERENCE RHYTHM LOCK",
            "Treat the written source timeline as the edit script: preserve shot order, cut timing, pacing, camera behavior, and action sequence.",
            "Cuts are temporal full-screen edits over time, never simultaneous panels.",
            f"Keep {product_token} as the consistent product while preserving every source action, use-case, and practical result.",
            "Do not replace the timeline with a generic product shot, new demonstration, slow opening, or beauty-only pause.",
        ]
    )


def _source_faithful_video_prefix(*, product_token: str = "@Image1") -> str:
    return "\n".join(
        [
            "SOURCE-FAITHFUL AD REMAKE",
            "The source is the script and set, not loose inspiration: preserve its environment, working surface/problem, human framing, camera crop, demo mechanics, result reveal, and pacing.",
            f"Only swap visible product identity/details to {product_token}; keep the proven reference demo structure and practical payoff.",
            "Do not invent a new room, studio, background, human action, surface, or use-case.",
        ]
    )


def _source_scene_execution_suffix(
    reference_analysis: dict[str, Any] | None,
    *,
    product_token: str,
) -> str:
    analysis = reference_analysis if isinstance(reference_analysis, dict) else {}
    setting = analysis.get("setting") if isinstance(analysis.get("setting"), dict) else {}
    actor = analysis.get("actorBehavior") if isinstance(analysis.get("actorBehavior"), dict) else {}
    backgrounds = setting.get("backgroundElements") if isinstance(setting.get("backgroundElements"), list) else []
    gestures = actor.get("gestures") if isinstance(actor.get("gestures"), list) else []
    lines = [
        "FINAL SOURCE SCENE LOCK",
        "The reference video is the literal set and shot script: keep its environment, practical working surface/problem, human framing, demo mechanics, camera/cut rhythm, and payoff.",
        f"Only replace the source product/tool with {product_token}; this is a remake, not a new ad concept.",
        "Do not invent a different room, studio, lifestyle scene, presenter behavior, working surface, or demonstration.",
    ]
    if setting.get("locationType"):
        lines.append(f"Reference environment: {_truncate_inline(str(setting['locationType']), 180)}.")
    if backgrounds:
        lines.append(f"Reference background to retain: {_truncate_inline(_join_list(backgrounds[:4]), 280)}.")
    if analysis.get("subjectPresence"):
        lines.append(f"Reference human presence/framing: {_truncate_inline(str(analysis['subjectPresence']), 100)}.")
    if gestures:
        lines.append(f"Reference interaction to retain: {_truncate_inline(_join_list(gestures[:3]), 240)}.")
    return "\n".join(lines)


def _source_segment_execution_suffix(scene: dict[str, Any], *, product_token: str) -> str:
    plan = scene.get("shotPlan") if isinstance(scene.get("shotPlan"), dict) else {}
    segment = scene.get("sourceSegment") if isinstance(scene.get("sourceSegment"), dict) else plan.get("sourceSegment")
    if not isinstance(segment, dict) or not segment:
        return ""
    source_range = segment.get("sourceTimeRange") if isinstance(segment.get("sourceTimeRange"), dict) else {}
    boundary = segment.get("boundary") if isinstance(segment.get("boundary"), dict) else {}
    continuity = segment.get("continuity") if isinstance(segment.get("continuity"), dict) else {}
    order = segment.get("segmentOrder")
    count = segment.get("segmentCount")
    lines = [
        "FINAL SOURCE SEGMENT EXECUTION",
        f"Execute only source segment {order} of {count} and only its listed cut map. Do not replay, summarize, preview, or replace another source segment.",
        "SEGMENT SCOPE IS ABSOLUTE: render only the listed cut-map shots for this segment. Do not add b-roll, new establishing shots, repeated actions from another segment, filler transitions, or unrelated product shots.",
        f"Source interval: {_format_seconds(source_range.get('startSecond'))}-{_format_seconds(source_range.get('endSecond'))} seconds."
        if source_range.get("startSecond") is not None and source_range.get("endSecond") is not None
        else "Execute only this assigned source interval.",
        f"Keep the reference environment, background, human framing, camera behavior, practical demo, and result for this segment; only swap the source product/tool for {product_token}.",
    ]
    if boundary.get("kind") == "source_cut":
        lines.append(f"Begin at the actual source cut using its {boundary.get('cutStyle') or 'natural_cut'} style. Do not add a new intro or invented transition.")
    elif boundary.get("kind") == "continuous_handoff":
        lines.append("Continue the exact source action, product state, and camera movement from segment one. Do not restart the demo or manufacture a cut.")
    if continuity.get("previousState") or continuity.get("openingState"):
        lines.append(f"Required state handoff: {continuity.get('previousState') or 'prior source state'} -> {continuity.get('openingState') or 'current source state'}.")
    return "\n".join(lines)


def _is_multi_segment_scene(scene: dict[str, Any]) -> bool:
    segment = scene.get("sourceSegment") if isinstance(scene.get("sourceSegment"), dict) else {}
    plan = scene.get("shotPlan") if isinstance(scene.get("shotPlan"), dict) else {}
    if not segment:
        segment = plan.get("sourceSegment") if isinstance(plan.get("sourceSegment"), dict) else {}
    try:
        return int(segment.get("segmentCount") or 1) > 1
    except (TypeError, ValueError):
        return False


def _reference_mode_instruction(*, context_urls: list[str], object_reference_mode: bool) -> str:
    if not context_urls:
        return ""
    if not object_reference_mode:
        return "REFERENCE MODE: use the persistent product reference and scene reference only; do not combine reference mode with start_image_url."
    return "REFERENCE IMAGE MODE: use reference_image_urls only; do not combine them with start_image_url."


def _context_identity_instruction(*, context_urls: list[str], product_token: str) -> str:
    if context_urls:
        return (
            f"If any context image contains a different tool/product or conflicts with {product_token}, "
            f"{product_token} wins for product identity, color, shape, components, and physical use. "
            "Keep context images only for background/demo/action context."
        )
    return f"Use {product_token} as the only product visual reference; infer setting, framing, and action from the written shot timeline."


def _scene_video_prompt(scene: dict[str, Any], shot_plan: str) -> str:
    prompt = str(scene.get("videoPrompt") or "").strip()
    if shot_plan and len(prompt) > MAX_UNIFICALLY_SCENE_PROMPT_CHARS:
        return _compact_prompt(prompt, MAX_UNIFICALLY_SCENE_PROMPT_CHARS)
    return prompt


def _compact_16s_shot_plan(scene: dict[str, Any], *, max_chars: int = 1450) -> str:
    """Keep every assigned source shot while fitting the 16s contract."""
    plan = scene.get("shotPlan") if isinstance(scene.get("shotPlan"), dict) else {}
    shots = plan.get("shots") if isinstance(plan.get("shots"), list) else []
    shot_count = int(plan.get("shotCount") or len(shots) or 0)
    if shot_count <= 1 or not shots:
        return ""

    lines = [
        "MANDATORY MULTI-SHOT CUT MAP",
        f"Execute exactly {shot_count} source shots in order inside this 8-second segment.",
        "These are temporal full-screen cuts in one vertical video; never create a collage, panels, b-roll, filler, a new scene, or an alternate use-case.",
        "Start each listed shot in its useful source action and preserve its target, movement, and visible result.",
    ]
    cut_times = plan.get("cutTimes") if isinstance(plan.get("cutTimes"), list) else []
    if cut_times:
        lines.append(f"Cut near: {', '.join(_format_seconds(value) for value in cut_times)} seconds.")

    assigned_shots = shots[:12]
    header_size = sum(len(line) + 1 for line in lines)
    line_budget = max(64, (max_chars - header_size - len(assigned_shots)) // max(1, len(assigned_shots)))
    for shot in assigned_shots:
        action = _truncate_inline(str(shot.get("action") or "continue the source action").strip(), 54)
        framing = _truncate_inline(str(shot.get("framing") or "").strip(), 18)
        camera = _truncate_inline(
            str(shot.get("cameraMovement") or shot.get("cameraBehavior") or "").strip(),
            18,
        )
        physical = shot.get("physicalAction") if isinstance(shot.get("physicalAction"), dict) else {}
        mechanics = _join_list(
            [
                f"target={_truncate_inline(str(physical.get('targetSurface')), 22)}" if physical.get("targetSurface") else "",
                f"effect={_truncate_inline(str(physical.get('visibleEffect')), 22)}" if physical.get("visibleEffect") else "",
            ]
        )
        visual = _join_list(
            [
                f"frame={framing}" if framing else "",
                f"camera={camera}" if camera else "",
            ]
        )
        line = f"{_format_seconds(shot.get('startSecond'))}-{_format_seconds(shot.get('endSecond'))}s {action}"
        if visual:
            line = f"{line} | {visual}"
        if mechanics:
            line = f"{line} | {_truncate_inline(mechanics, 48)}"
        lines.append(_truncate_inline(line, line_budget))
    return "\n".join(lines)


def _compact_16s_product_demo_lock(
    product_lock: dict[str, Any] | None,
    *,
    product_token: str,
) -> str:
    lines = [
        "FINAL PRODUCT DEMO EXECUTION",
        f"Use {product_token} for every listed source shot. Keep it visible at the real contact point and preserve the source target, movement, and cause-and-effect.",
        "ProductUsage is only a physical plausibility guardrail. Never invent a target, room, background, use-case, surface, result, presenter action, or product behavior absent from the source shot map; if absent, omit it.",
    ]
    return "\n".join(lines)


def _compact_16s_identity_lock(
    product_lock: dict[str, Any] | None,
    *,
    product_token: str,
    max_chars: int = 1750,
) -> str:
    """Keep the stable lock wording while bounding untrusted product detail text."""
    lines = _video_identity_prefix(product_lock, product_token=product_token).splitlines()
    if len("\n".join(lines)) <= max_chars:
        return "\n".join(lines)
    fixed_lines = lines[:17]
    detail_lines = lines[17:]
    fixed_size = len("\n".join(fixed_lines)) + (1 if detail_lines else 0)
    remaining = max(80, max_chars - fixed_size)
    details = _truncate_inline("TARGET PRODUCT DETAILS: " + "; ".join(detail_lines), remaining)
    return "\n".join([*fixed_lines, details])


def _bounded_16s_section(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return _compact_prompt(text, max_chars)


def _compact_16s_source_segment(scene: dict[str, Any], *, product_token: str) -> str:
    plan = scene.get("shotPlan") if isinstance(scene.get("shotPlan"), dict) else {}
    segment = scene.get("sourceSegment") if isinstance(scene.get("sourceSegment"), dict) else plan.get("sourceSegment")
    if not isinstance(segment, dict) or not segment:
        return ""
    source_range = segment.get("sourceTimeRange") if isinstance(segment.get("sourceTimeRange"), dict) else {}
    boundary = segment.get("boundary") if isinstance(segment.get("boundary"), dict) else {}
    continuity = segment.get("continuity") if isinstance(segment.get("continuity"), dict) else {}
    order = segment.get("segmentOrder")
    count = segment.get("segmentCount")
    lines = [
        "FINAL SOURCE SEGMENT EXECUTION",
        f"SEGMENT SCOPE IS ABSOLUTE: execute only source segment {order} of {count} and its listed source shots. Do not add b-roll, new establishing shots, repeated actions from another segment, filler transitions, or unrelated product shots.",
        f"Source interval: {_format_seconds(source_range.get('startSecond'))}-{_format_seconds(source_range.get('endSecond'))} seconds.",
        f"Keep this segment's reference environment, background, human framing, camera behavior, demo, and result; only replace the source product with {product_token}.",
    ]
    if boundary.get("kind") == "source_cut":
        lines.append(f"Begin at the actual source cut with {boundary.get('cutStyle') or 'natural_cut'}; do not add an intro or transition.")
    elif boundary.get("kind") == "continuous_handoff":
        lines.append("Continue the prior source action, product state, and camera movement; do not restart or invent a new shot.")
    if continuity.get("previousState") or continuity.get("openingState"):
        lines.append(f"State handoff: {continuity.get('previousState') or 'prior source state'} -> {continuity.get('openingState') or 'current source state'}.")
    return "\n".join(lines)


def _compact_16s_camera_context(reference_analysis: dict[str, Any] | None) -> str:
    analysis = reference_analysis if isinstance(reference_analysis, dict) else {}
    camera = analysis.get("cameraStyle") if isinstance(analysis.get("cameraStyle"), dict) else {}
    values = [
        f"angle={camera.get('angle')}" if camera.get("angle") else "",
        f"framing={camera.get('framing')}" if camera.get("framing") else "",
        f"movement={camera.get('movement')}" if camera.get("movement") else "",
    ]
    values = [value for value in values if value]
    return f"REFERENCE CAMERA: {_truncate_inline('; '.join(values), 180)}." if values else ""


def _build_unifically_16s_compact_prompt(
    *,
    scene: dict[str, Any],
    product_lock: dict[str, Any] | None,
    product_token: str,
    context_urls: list[str],
    context_reference_lines: list[str],
    reference_analysis: dict[str, Any] | None,
    object_reference_mode: bool,
) -> str:
    """Assemble 16s without dropping the middle source shots or product lock."""
    parts = [
        _compact_16s_shot_plan(scene),
        _reference_mode_instruction(context_urls=context_urls, object_reference_mode=object_reference_mode),
        *[_truncate_inline(line, 180) for line in context_reference_lines[:2]],
        _compact_16s_identity_lock(product_lock, product_token=product_token),
        _context_identity_instruction(context_urls=context_urls, product_token=product_token) if context_urls else "",
        _compact_16s_camera_context(reference_analysis),
        _bounded_16s_section(_compact_16s_product_demo_lock(product_lock, product_token=product_token), 500),
        _bounded_16s_section(_source_scene_execution_suffix(reference_analysis, product_token=product_token), 360),
        _bounded_16s_section(_compact_16s_source_segment(scene, product_token=product_token), 430),
    ]
    prompt = "\n\n".join(part for part in parts if isinstance(part, str) and part.strip())
    if len(prompt) > MAX_UNIFICALLY_VIDEO_PROMPT_CHARS:
        # This is a defensive fallback for unusually verbose Gemini output.
        # The normal section budgets above preserve the identity lock and all
        # assigned shots before this path is reached.
        prompt = _compact_prompt(prompt, MAX_UNIFICALLY_VIDEO_PROMPT_CHARS)
    return prompt


def _build_unifically_8s_prompt_parts(
    *,
    scene: dict[str, Any],
    product_lock: dict[str, Any] | None,
    product_token: str,
    context_urls: list[str],
    context_reference_lines: list[str],
    reference_analysis: dict[str, Any] | None,
    object_reference_mode: bool = True,
) -> list[str]:
    """Build the stable single-task 8s prompt used by commit 6a77893."""
    shot_plan = _shot_plan_prefix(scene, include_physical_execution=False, include_source_scope=False)
    scene_prompt = _scene_video_prompt(scene, shot_plan)
    return [
        shot_plan,
        _reference_mode_instruction(context_urls=context_urls, object_reference_mode=object_reference_mode),
        *context_reference_lines,
        _video_identity_prefix(product_lock, product_token=product_token),
        _context_identity_instruction(context_urls=context_urls, product_token=product_token),
        _reference_rhythm_prefix(product_token=product_token),
        _source_faithful_video_prefix(product_token=product_token),
        _single_frame_prefix(),
        scene_prompt,
        _cut_execution_suffix(scene),
        _product_demo_execution_suffix(
            scene,
            product_lock,
            product_token=product_token,
            include_physical_execution=False,
        ),
        _source_scene_execution_suffix(reference_analysis, product_token=product_token),
    ]


def _build_unifically_16s_prompt_parts(
    *,
    scene: dict[str, Any],
    product_lock: dict[str, Any] | None,
    product_token: str,
    context_urls: list[str],
    context_reference_lines: list[str],
    reference_analysis: dict[str, Any] | None,
    object_reference_mode: bool = True,
) -> list[str]:
    """Use the stable 8s product lock with an additional local source segment."""
    shot_plan = _shot_plan_prefix(scene, include_physical_execution=True)
    return [
        shot_plan,
        _reference_mode_instruction(context_urls=context_urls, object_reference_mode=object_reference_mode),
        *context_reference_lines,
        _video_identity_prefix(product_lock, product_token=product_token),
        _context_identity_instruction(context_urls=context_urls, product_token=product_token),
        _reference_rhythm_prefix(product_token=product_token),
        _source_faithful_video_prefix(product_token=product_token),
        _single_frame_prefix(),
        _scene_video_prompt(scene, shot_plan),
        _cut_execution_suffix(scene),
        _product_demo_execution_suffix(
            scene,
            product_lock,
            product_token=product_token,
            include_physical_execution=True,
        ),
        _source_scene_execution_suffix(reference_analysis, product_token=product_token),
        # Keep the segment contract in the prompt tail so compaction retains
        # it together with the stable product lock and source scene lock.
        _source_segment_execution_suffix(scene, product_token=product_token),
    ]


def _compact_prompt(prompt: str, max_chars: int = MAX_UNIFICALLY_VIDEO_PROMPT_CHARS) -> str:
    lines = [line.strip() for line in prompt.splitlines() if line.strip()]
    normalized = "\n".join(lines)
    if len(normalized) <= max_chars:
        return normalized

    # Keep complete instruction lines. Character slicing can cut an identity
    # rule in half and leave the provider with a contradictory prompt.
    head_budget = int(max_chars * 0.65)
    tail_budget = int(max_chars * 0.29)
    head: list[str] = []
    head_size = 0
    for line in lines:
        size = len(line) + (1 if head else 0)
        if head_size + size > head_budget:
            break
        head.append(line)
        head_size += size

    tail: list[str] = []
    tail_size = 0
    for line in reversed(lines):
        size = len(line) + (1 if tail else 0)
        if tail_size + size > tail_budget:
            break
        tail.append(line)
        tail_size += size
    tail.reverse()
    return "\n".join([*head, "...", *tail])


def validate_unifically_video_input(input_data: dict[str, Any]) -> None:
    """Validate the provider payload after all Gemini text is normalized."""
    unexpected_keys = sorted(set(input_data) - UNIFICALLY_VEO_INPUT_KEYS)
    if unexpected_keys:
        raise SmartRemakeValidationError(
            "Unifically video payload contains unsupported Veo input fields.",
            "UNIFICALLY_PAYLOAD_INVALID",
            {"fields": unexpected_keys},
        )
    prompt = input_data.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        raise SmartRemakeValidationError(
            "Unifically video prompt must be a non-empty string.",
            "UNIFICALLY_PAYLOAD_INVALID",
            {"field": "prompt"},
        )
    if len(prompt) > MAX_UNIFICALLY_VIDEO_PROMPT_CHARS:
        raise SmartRemakeValidationError(
            f"Unifically video prompt exceeds {MAX_UNIFICALLY_VIDEO_PROMPT_CHARS} characters.",
            "UNIFICALLY_PAYLOAD_INVALID",
            {"field": "prompt", "maxCharacters": MAX_UNIFICALLY_VIDEO_PROMPT_CHARS, "actualCharacters": len(prompt)},
        )
    if input_data.get("aspect_ratio") != "9:16":
        raise SmartRemakeValidationError(
            "Unifically Smart Remake video payload must use aspect_ratio 9:16.",
            "UNIFICALLY_PAYLOAD_INVALID",
            {"field": "aspect_ratio", "value": input_data.get("aspect_ratio")},
        )

    reference_image_urls = input_data.get("reference_image_urls") or []
    if not isinstance(reference_image_urls, list) or any(
        not isinstance(url, str) or not url.strip() for url in reference_image_urls
    ):
        raise SmartRemakeValidationError(
            "Unifically reference_image_urls must contain non-empty URLs.",
            "UNIFICALLY_PAYLOAD_INVALID",
            {"field": "reference_image_urls"},
        )

    character_image_count = 0
    reference_characters = input_data.get("reference_characters") or []
    if not isinstance(reference_characters, list):
        raise SmartRemakeValidationError(
            "Unifically reference_characters must be an array.",
            "UNIFICALLY_PAYLOAD_INVALID",
            {"field": "reference_characters"},
        )
    for character in reference_characters:
        if not isinstance(character, dict) or not isinstance(character.get("image_urls"), list):
            raise SmartRemakeValidationError(
                "Unifically reference_characters entries must include image_urls arrays.",
                "UNIFICALLY_PAYLOAD_INVALID",
                {"field": "reference_characters"},
            )
        image_urls = character["image_urls"]
        if any(not isinstance(url, str) or not url.strip() for url in image_urls):
            raise SmartRemakeValidationError(
                "Unifically character image_urls must contain non-empty URLs.",
                "UNIFICALLY_PAYLOAD_INVALID",
                {"field": "reference_characters"},
            )
        character_image_count += len(image_urls)

    reference_count = len(reference_image_urls) + character_image_count
    if reference_count > 3:
        raise SmartRemakeValidationError(
            "Unifically video payload contains more than 3 image ingredients.",
            "UNIFICALLY_PAYLOAD_INVALID",
            {"field": "reference_images", "max": 3, "actual": reference_count},
        )
    if reference_count and input_data.get("duration") != 8:
        raise SmartRemakeValidationError(
            "Unifically video reference mode requires duration 8.",
            "UNIFICALLY_PAYLOAD_INVALID",
            {"field": "duration", "value": input_data.get("duration")},
        )
    if input_data.get("start_image_url") and reference_count:
        raise SmartRemakeValidationError(
            "Unifically start_image_url cannot be combined with reference images.",
            "UNIFICALLY_PAYLOAD_INVALID",
            {"fields": ["start_image_url", "reference_images"]},
        )


def build_unifically_image_input(
    *,
    scene: dict[str, Any],
    product_image_url: str,
    product_lock: dict[str, Any] | None = None,
    source_frame_url: str | None = None,
) -> dict[str, Any]:
    prompt_parts = [_unifically_identity_prefix(product_lock), _single_frame_prefix()]
    image_urls = [product_image_url]
    if source_frame_url:
        image_urls.append(source_frame_url)
        prompt_parts.extend(
            [
                "PRODUCT-SWAPPED SOURCE START FRAME",
                "@Image1 is the exact target product. @Image2 is a frame from the uploaded reference video.",
                "Create a single photorealistic first frame that keeps @Image2's background, working surface, camera crop, hand/person framing, lighting, and demo pose.",
                "Replace only the source video's original visible product/tool role with @Image1. Do not keep the source tool if it conflicts with @Image1.",
                "@Image1 has absolute priority for product pixels and identity. @Image2 is context only: never blend, borrow, or reconstruct product shape, color, components, or branding from @Image2.",
                "Keep @Image1's exact geometry and appearance even when the source product is held at an angle, partially occluded, or moving.",
                "The target product must be visible in the resulting image where the demo action needs a product/tool.",
            ]
        )
    prompt_parts.append(scene["imagePrompt"])
    return {
        "prompt": "\n\n".join(prompt_parts),
        "aspect_ratio": "9:16",
        "image_urls": image_urls,
    }


def build_unifically_video_input(
    *,
    scene: dict[str, Any],
    product_image_url: str | None = None,
    scene_image_url: str | None = None,
    source_frame_urls: list[str] | None = None,
    start_image_url: str | None = None,
    product_lock: dict[str, Any] | None = None,
    reference_analysis: dict[str, Any] | None = None,
    include_scene_reference: bool = False,
    object_reference_mode: bool = True,
    duration: int = 8,
    seed: int | None = None,
) -> dict[str, Any]:
    product_token = "@Image1" if object_reference_mode else "@Character1"
    is_multi_segment = _is_multi_segment_scene(scene)
    prompt_builder = _build_unifically_16s_prompt_parts if is_multi_segment else _build_unifically_8s_prompt_parts
    prompt_parts = prompt_builder(
        scene=scene,
        product_lock=product_lock,
        product_token=product_token,
        context_urls=[],
        context_reference_lines=[],
        reference_analysis=reference_analysis,
        object_reference_mode=object_reference_mode,
    )
    input_data: dict[str, Any] = {
        "aspect_ratio": "9:16",
        "duration": duration,
    }
    if seed is not None:
        input_data["seed"] = seed

    context_urls: list[str] = []
    context_reference_lines: list[str] = []
    if product_image_url:
        source_urls = [url for url in (source_frame_urls or []) if isinstance(url, str) and url.strip()]
        use_scene_reference = bool(include_scene_reference and scene_image_url)
        # Unifically allows at most three expanded image ingredients. The
        # uploaded product is the authoritative identity reference, while any
        # generated scene frame is context-only.
        # A generated product-swapped frame is the only scene ingredient. Raw
        # source frames may contain the old product and must not be sent to the
        # video model, which can blend all reference images despite the prompt.
        if use_scene_reference:
            context_urls.append(scene_image_url)
        context_urls = context_urls[:2]
        if use_scene_reference:
            scene_reference_token = "@Image2"
            if not object_reference_mode:
                context_reference_lines.append(
                    "@Image1 is the same exact uploaded product image as @Character1; use both as identity anchors and never treat @Image1 as scene context."
                )
            context_reference_lines.append(
                f"{scene_reference_token} is a generated scene-context frame; preserve its background, camera crop, lighting, hands/person framing, target surface, and demo composition. Its product pixels are not authoritative."
            )
            context_reference_lines.append(
                f"Raw source frames were used only to construct {scene_reference_token} and are not video ingredients; never reconstruct the source product."
            )
        elif source_urls:
            context_reference_lines.append(
                "Raw source frames are analysis-only context and are not video ingredients; use them only for background, surface, human framing, camera, lighting, demo action, and pacing. Never use their product pixels."
            )
        prompt_parts = prompt_builder(
            scene=scene,
            product_lock=product_lock,
            product_token=product_token,
            context_urls=context_urls,
            context_reference_lines=context_reference_lines,
            reference_analysis=reference_analysis,
            object_reference_mode=object_reference_mode,
        )
        if object_reference_mode:
            input_data["reference_image_urls"] = [product_image_url, *context_urls]
        else:
            input_data["reference_characters"] = [
                {
                    "image_urls": [product_image_url],
                    "name": _character_name(product_lock),
                    "description": _product_reference_text(product_lock),
                }
            ]
            # Duplicate the uploaded product in the image-reference channel
            # as well as the character channel. This gives Veo two explicit
            # identity anchors while the generated scene remains context-only.
            input_data["reference_image_urls"] = [product_image_url, *context_urls]
    elif start_image_url:
        prompt_parts = [
            "START FRAME LOCK",
            "Animate from the provided start image while preserving its subject, composition, and first-frame continuity.",
            _reference_rhythm_prefix(product_token="the visible subject"),
            *prompt_parts,
        ]
        input_data["start_image_url"] = start_image_url
    else:
        prompt_parts = [
            "REFERENCE LOCK",
            "Follow the prompt without inventing unrelated products, panels, or disconnected action.",
            _single_frame_prefix(),
            str(scene.get("videoPrompt") or "").strip(),
        ]

    if is_multi_segment and product_image_url:
        input_data["prompt"] = _build_unifically_16s_compact_prompt(
            scene=scene,
            product_lock=product_lock,
            product_token=product_token,
            context_urls=context_urls,
            context_reference_lines=context_reference_lines,
            reference_analysis=reference_analysis,
            object_reference_mode=object_reference_mode,
        )
    else:
        # Keep the stable 8s path unchanged. It intentionally uses the
        # original prompt builder and compactor from commit 6a77893.
        input_data["prompt"] = _compact_prompt("\n\n".join(part for part in prompt_parts if isinstance(part, str) and part.strip()))
    validate_unifically_video_input(input_data)
    return input_data


def extract_task_output_url(task: dict[str, Any], key: str) -> str | None:
    for container in _output_containers(task):
        value = container.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        value = container.get("url")
        if key.endswith("_url") and isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _output_containers(task: dict[str, Any]) -> list[dict[str, Any]]:
    containers: list[dict[str, Any]] = []
    for key in ("output", "data", "result"):
        value = task.get(key)
        if isinstance(value, dict):
            containers.append(value)
    containers.append(task)
    return containers
