import re
from typing import Any

from .schemas import normalize_text, string_list


CREATIVE_ARCHETYPES = {
    "product_demo", "problem_solution", "before_after", "transformation", "unboxing",
    "testimonial", "comparison", "lifestyle_showcase", "offer_led", "product_reveal",
    "tutorial", "visual_meme", "continuous_one_take", "fast_montage", "other",
}
VISUAL_STRUCTURES = {"continuous", "sequential_shots", "before_after", "split_screen", "slideshow", "screen_recording", "mixed_media"}
PRIMARY_HOOK_TYPES = {"visual_action", "visual_surprise", "problem", "transformation", "reaction", "text", "spoken_line", "offer", "product_result"}
PRODUCT_CARDINALITIES = {"single", "multiple"}
MOTION_BEAT_ROLES = {"hook", "setup", "problem", "action", "demonstration", "transition", "reveal", "proof", "reaction", "payoff", "hero", "cta"}
MOTION_BEAT_PRIORITIES = {"mandatory", "supporting", "optional"}


def _enum(value: Any, allowed: set[str], fallback: str) -> str:
    return value if isinstance(value, str) and value in allowed else fallback


def _search_text(fallback: dict[str, Any]) -> str:
    creative = fallback.get("creativeConcept") or {}
    opening = fallback.get("openingShot") or {}
    return " ".join(
        str(part)
        for part in [
            fallback.get("format"),
            creative.get("hook"),
            creative.get("adType"),
            creative.get("productMoment"),
            opening.get("firstAction"),
            *[beat.get("action") for beat in fallback.get("motionBeats", []) if isinstance(beat, dict)],
        ]
        if part
    ).lower()


def _derive_archetype(fallback: dict[str, Any]) -> str:
    text = _search_text(fallback)
    pacing = fallback.get("pacingPlan") or {}
    if re.search(r"\bbefore\b.*\bafter\b|\bafter\b.*\bbefore\b", text):
        return "before_after"
    if re.search(r"\btransform|transformation|changed into|turns into\b", text):
        return "transformation"
    if re.search(r"\bunbox|unboxing|unpack|package opening\b", text):
        return "unboxing"
    if re.search(r"\btestimonial|review|ugc review|creator review|customer says\b", text):
        return "testimonial"
    if re.search(r"\bcompare|comparison|versus| vs |side by side\b", text):
        return "comparison"
    if re.search(r"\bmeme|joke|funny|reaction gag\b", text):
        return "visual_meme"
    if pacing.get("pace") == "fast" or re.search(r"\bmontage|rapid cuts|fast cuts\b", text):
        return "fast_montage"
    if re.search(r"\bproblem|friction|pain point|solve|solution|fix\b", text):
        return "problem_solution"
    if re.search(r"\blifestyle|daily routine|in use|real life\b", text):
        return "lifestyle_showcase"
    if re.search(r"\boffer|sale|discount|deal|limited time|coupon\b", text):
        return "offer_led"
    if re.search(r"\breveal|product reveal|show the result\b", text):
        return "product_reveal"
    if re.search(r"\btutorial|how to|step by step|instruction\b", text):
        return "tutorial"
    if pacing.get("cutStyle") == "continuous" and (pacing.get("shotCount", 1) <= 1 or fallback.get("sceneCount") == 1):
        return "continuous_one_take"
    return "product_demo" if text.strip() else "other"


def _derive_visual(archetype: str, fallback: dict[str, Any]) -> str:
    text = _search_text(fallback)
    pacing = fallback.get("pacingPlan") or {}
    if archetype == "before_after" or re.search(r"\bbefore\b.*\bafter\b", text):
        return "before_after"
    if re.search(r"\bsplit screen|side by side\b", text):
        return "split_screen"
    if re.search(r"\bslideshow|slides|still sequence\b", text):
        return "slideshow"
    if re.search(r"\bscreen recording|screen capture|app demo\b", text):
        return "screen_recording"
    if re.search(r"\bmixed media|screenshots and video|photos and video\b", text):
        return "mixed_media"
    if pacing.get("cutStyle") == "continuous" and pacing.get("shotCount", 1) <= 1:
        return "continuous"
    return "sequential_shots"


def _derive_hook(fallback: dict[str, Any]) -> str:
    creative = fallback.get("creativeConcept") or {}
    opening = fallback.get("openingShot") or {}
    first = (fallback.get("motionBeats") or [{}])[0] if fallback.get("motionBeats") else {}
    text = " ".join(str(part) for part in [creative.get("hook"), opening.get("firstAction"), first.get("action")] if part).lower()
    for pattern, hook in [
        (r"\bproblem|friction|pain|mess|struggle|annoying\b", "problem"),
        (r"\btransform|before|after\b", "transformation"),
        (r"\breaction|surprised|shocked|delighted\b", "reaction"),
        (r"\btext|caption|headline|on-screen\b", "text"),
        (r"\bsays|spoken|voice|dialogue|line\b", "spoken_line"),
        (r"\boffer|sale|discount|deal|coupon\b", "offer"),
        (r"\bresult|outcome|proof|finished\b", "product_result"),
        (r"\bsurprise|unexpected|sudden\b", "visual_surprise"),
    ]:
        if re.search(pattern, text):
            return hook
    return "visual_action"


def _derive_role(action: str, index: int, total: int) -> str:
    text = action.lower()
    if index == 0:
        return "problem" if re.search(r"\bproblem|friction|pain|struggle\b", text) else "hook"
    if re.search(r"\bproblem|friction|pain|struggle\b", text):
        return "problem"
    if re.search(r"\bdemo|demonstrate|use|show how|apply\b", text):
        return "demonstration"
    if re.search(r"\breveal|introduce|appears|show product\b", text):
        return "reveal"
    if re.search(r"\bproof|result|works|evidence\b", text):
        return "proof"
    if re.search(r"\breaction|respond|surprised|satisfied\b", text):
        return "reaction"
    if re.search(r"\bhero|beauty shot|final\b", text):
        return "hero"
    if re.search(r"\bcta|buy|shop|offer\b", text):
        return "cta"
    if index == total - 1:
        return "payoff"
    return "setup" if index == 1 else "action"


def _derive_priority(role: str, index: int, total: int) -> str:
    if index == 0:
        return "mandatory"
    if role in {"proof", "payoff"} and total <= 3:
        return "mandatory"
    if role == "cta":
        return "supporting" if index == total - 1 else "optional"
    return "supporting"


def normalize_creative_structure(input_value: Any, fallback: dict[str, Any] | None = None) -> dict[str, Any]:
    fallback = fallback or {}
    raw = input_value if isinstance(input_value, dict) else {}
    archetype = _enum(raw.get("archetype") or raw.get("creativeArchetype"), CREATIVE_ARCHETYPES, _derive_archetype(fallback))
    visual = _enum(raw.get("visualStructure"), VISUAL_STRUCTURES, _derive_visual(archetype, fallback))
    hook = _enum(raw.get("primaryHookType"), PRIMARY_HOOK_TYPES, _derive_hook(fallback))
    beats_raw = raw.get("motionBeatSemantics") if isinstance(raw.get("motionBeatSemantics"), list) else []
    fallback_count = max(1, len(fallback.get("motionBeats") or []), len((fallback.get("pacingPlan") or {}).get("actionBeats") or []))
    source = beats_raw or [
        {"beatIndex": index, "action": ((fallback.get("motionBeats") or [{}])[index] if index < len(fallback.get("motionBeats") or []) else {}).get("action", "show the key product action")}
        for index in range(fallback_count)
    ]
    semantics = []
    for index, beat in enumerate(source):
        if not isinstance(beat, dict):
            continue
        action = normalize_text(beat.get("action"), "show the key product action")
        role = _enum(beat.get("role"), MOTION_BEAT_ROLES, _derive_role(action, index, len(source)))
        semantics.append(
            {
                "beatIndex": int(beat.get("beatIndex", index) or index),
                "role": role,
                "priority": _enum(beat.get("priority"), MOTION_BEAT_PRIORITIES, _derive_priority(role, index, len(source))),
                "action": action,
                "productStateBefore": normalize_text(beat.get("productStateBefore") or beat.get("stateBefore")) or None,
                "productStateAfter": normalize_text(beat.get("productStateAfter") or beat.get("stateAfter")) or None,
                "subjectStateBefore": normalize_text(beat.get("subjectStateBefore")) or None,
                "subjectStateAfter": normalize_text(beat.get("subjectStateAfter")) or None,
                "visualEvidence": normalize_text(beat.get("visualEvidence"), action),
                "renderabilityWarnings": string_list(beat.get("renderabilityWarnings")),
            }
        )
    transitions = raw.get("stateTransitions") if isinstance(raw.get("stateTransitions"), list) else []
    state_transitions = [
        {
            "fromState": normalize_text(item.get("fromState")),
            "toState": normalize_text(item.get("toState")),
            "triggerAction": normalize_text(item.get("triggerAction")),
            "visualEvidence": normalize_text(item.get("visualEvidence") or item.get("triggerAction")),
            "priority": _enum(item.get("priority"), MOTION_BEAT_PRIORITIES, "supporting"),
        }
        for item in transitions
        if isinstance(item, dict) and normalize_text(item.get("fromState")) and normalize_text(item.get("toState")) and normalize_text(item.get("triggerAction"))
    ]
    if not state_transitions:
        first = semantics[0] if semantics else {"action": "show the key product action", "visualEvidence": "show the key product action", "priority": "mandatory"}
        state_transitions = [
            {
                "fromState": first.get("productStateBefore") or "initial product state",
                "toState": first.get("productStateAfter") or "demonstrated product state",
                "triggerAction": first["action"],
                "visualEvidence": first["visualEvidence"],
                "priority": first["priority"],
            }
        ]
    return {
        "archetype": archetype,
        "visualStructure": visual,
        "primaryHookType": hook,
        "productCardinality": _enum(raw.get("productCardinality"), PRODUCT_CARDINALITIES, "multiple" if re.search(r"\bmultiple products|several products|many products|two products|collection|assortment|comparison of products\b", _search_text(fallback)) else "single"),
        "motionBeatSemantics": semantics,
        "stateTransitions": state_transitions,
        "renderabilityWarnings": list(dict.fromkeys(string_list(raw.get("renderabilityWarnings")))),
    }


def _strategy(archetype: str, visual: str) -> str:
    if visual == "continuous" or archetype == "continuous_one_take":
        return "continuous_action"
    if visual in {"split_screen", "screen_recording", "mixed_media"}:
        return "simplified_sequential"
    return {
        "problem_solution": "problem_to_solution",
        "before_after": "before_to_after",
        "transformation": "transformation_sequence",
        "unboxing": "unboxing_sequence",
        "testimonial": "testimonial_structure",
        "comparison": "comparison_sequence",
        "offer_led": "offer_structure",
        "product_reveal": "reveal_sequence",
        "product_demo": "sequential_demo",
        "lifestyle_showcase": "sequential_demo",
        "tutorial": "sequential_demo",
    }.get(archetype, "simplified_sequential")


def route_creative_structure(analysis: dict[str, Any]) -> dict[str, Any]:
    structure = normalize_creative_structure(analysis.get("creativeStructure") or analysis, analysis)
    archetype = _enum(analysis.get("creativeArchetype"), CREATIVE_ARCHETYPES, structure["archetype"])
    visual = _enum(analysis.get("visualStructure"), VISUAL_STRUCTURES, structure["visualStructure"])
    hook = _enum(analysis.get("primaryHookType"), PRIMARY_HOOK_TYPES, structure["primaryHookType"])
    cardinality = _enum(analysis.get("productCardinality"), PRODUCT_CARDINALITIES, structure["productCardinality"])
    strategy = _strategy(archetype, visual)
    warnings = []
    explicit = ((analysis.get("renderability") or {}).get("warnings") if isinstance(analysis.get("renderability"), dict) else []) or []
    warnings.extend(item for item in explicit if isinstance(item, dict))
    warnings.extend({"code": "REFERENCE_STRUCTURE_SIMPLIFIED", "message": msg} for msg in structure.get("renderabilityWarnings", []))
    if visual in {"split_screen", "mixed_media"}:
        warnings.append({"code": "REFERENCE_STRUCTURE_SIMPLIFIED", "message": f"{visual} structure was converted to sequential shots.", "originalStructure": visual, "selectedStrategy": strategy})
    if visual == "screen_recording":
        warnings.append({"code": "SCREEN_RECORDING_UNSUPPORTED", "message": "Screen recording structure was converted to a product-focused visual sequence.", "originalStructure": visual, "selectedStrategy": strategy})
    if hook == "text":
        warnings.append({"code": "TEXT_DEPENDENT_HOOK", "message": "The hook depends on on-screen text; generation should preserve hook logic without copying exact captions."})
    if hook == "spoken_line":
        warnings.append({"code": "VOICE_DEPENDENT_HOOK", "message": "The hook depends on speech; generation should preserve intent without copying exact wording."})
    if cardinality == "multiple":
        warnings.append({"code": "MULTI_PRODUCT_COMPLEXITY", "message": "Multiple products may need simplification to keep the render clear."})
    if archetype == "comparison":
        warnings.append({"code": "COMPARISON_CLAIMS_RESTRICTED", "message": "Comparison logic must avoid competitor brands and unsupported measurable superiority claims."})
    if (analysis.get("pacingPlan") or {}).get("shotCount", 0) > 6 or archetype == "fast_montage":
        warnings.append({"code": "SHOT_COUNT_REDUCED", "message": "High shot count may be reduced to the strongest mandatory beats for renderability."})
    deduped = []
    seen = set()
    for warning in warnings:
        code = normalize_text(warning.get("code"))
        message = normalize_text(warning.get("message"))
        if not code or not message:
            continue
        key = (code, message, warning.get("originalStructure"), warning.get("selectedStrategy"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append({k: v for k, v in {"code": code, "message": message, "originalStructure": warning.get("originalStructure"), "selectedStrategy": warning.get("selectedStrategy")}.items() if v})
    return {
        "creativeArchetype": archetype,
        "visualStructure": visual,
        "primaryHookType": hook,
        "productCardinality": cardinality,
        "recommendedStrategy": strategy,
        "warnings": deduped,
    }
