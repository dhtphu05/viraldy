from typing import Any

from .creative_router import route_creative_structure
from .errors import SmartRemakeError


def _round_tenth(value: float) -> float:
    return round(value * 10) / 10


def _has_state_transition(beat: dict[str, Any]) -> bool:
    before = beat.get("stateBefore")
    after = beat.get("stateAfter")
    return bool(before and after and str(before).lower() != str(after).lower())


def _derive_pacing_profile(analysis: dict[str, Any]) -> str:
    route = route_creative_structure(analysis)
    pacing = analysis.get("pacingPlan") or {}
    source_shots = analysis.get("sourceShots") if isinstance(analysis.get("sourceShots"), list) else []
    if (
        route["creativeArchetype"] == "fast_montage"
        or pacing.get("pace") == "fast"
        or pacing.get("shotCount", 0) > 4
        or pacing.get("cutStyle") in {"hard_cut", "jump_cut"}
        or len(source_shots) >= 4
    ):
        return "fast_social"
    if (
        route["visualStructure"] == "continuous"
        or route["creativeArchetype"] == "continuous_one_take"
        or (pacing.get("pace") == "slow" and pacing.get("cameraEnergy") in {"smooth", "static"})
    ):
        return "slow_cinematic"
    return "balanced"


def _role_fallback(action: str, index: int, total: int) -> str:
    text = action.lower()
    if index == 0 and any(word in text for word in ["problem", "friction", "issue", "mess", "before"]):
        return "problem"
    if index == 0:
        return "hook"
    if any(word in text for word in ["demo", "demonstrate", "use", "show how", "apply"]):
        return "demonstration"
    if any(word in text for word in ["reveal", "open", "unbox", "appears", "show product"]):
        return "reveal"
    if any(word in text for word in ["proof", "result", "after", "resolved", "works"]):
        return "proof"
    if index == total - 1:
        return "hero"
    return "action"


def _priority_fallback(role: str, index: int, total: int) -> str:
    if index == 0:
        return "mandatory"
    if role in {"proof", "payoff"} and total <= 3:
        return "mandatory"
    return "supporting"


def _beat_candidates(analysis: dict[str, Any]) -> list[dict[str, Any]]:
    beats = analysis.get("motionBeats") or []
    semantics = ((analysis.get("creativeStructure") or {}).get("motionBeatSemantics") or [])
    candidates = []
    for index, beat in enumerate(beats):
        semantic = semantics[index] if index < len(semantics) and isinstance(semantics[index], dict) else {}
        action = beat.get("action") or semantic.get("action") or "show the key product action"
        role = beat.get("role") or semantic.get("role") or _role_fallback(action, index, len(beats))
        state_before = beat.get("stateBefore") or semantic.get("productStateBefore")
        state_after = beat.get("stateAfter") or semantic.get("productStateAfter")
        priority = beat.get("priority") or semantic.get("priority") or _priority_fallback(role, index, len(beats))
        if state_before and state_after and priority != "optional":
            priority = "mandatory"
        candidates.append(
            {
                "sourceBeatIndexes": [index],
                "role": role,
                "priority": priority,
                "action": action,
                "physicalAction": beat.get("physicalAction"),
                "stateBefore": state_before,
                "stateAfter": state_after,
                "sourceDuration": max(0.5, float(beat.get("endSecond", 0)) - float(beat.get("startSecond", 0))),
            }
        )
    return candidates or [{"sourceBeatIndexes": [0], "role": "hook", "priority": "mandatory", "action": "show the key product action", "sourceDuration": 8}]


def _target_shot_count(analysis: dict[str, Any], pacing_profile: str) -> int:
    route = route_creative_structure(analysis)
    pacing = analysis.get("pacingPlan") or {}
    if route["visualStructure"] == "continuous" or route["creativeArchetype"] == "continuous_one_take":
        return 2 if any(_has_state_transition(beat) for beat in analysis.get("motionBeats", [])) else 1
    if route["creativeArchetype"] in {"before_after", "transformation"}:
        return 3
    if pacing_profile == "fast_social":
        return min(4, max(3, round(8 / max(1, pacing.get("averageShotDuration", 2)))))
    if pacing_profile == "slow_cinematic":
        return 2
    return 3


def _compatible_for_merge(left: dict[str, Any], right: dict[str, Any]) -> bool:
    if _has_state_transition(left) and _has_state_transition(right):
        return False
    phrase = f"{left.get('action', '')} {right.get('action', '')}".lower()
    return any(word in phrase for word in ["touch", "lift", "open", "reveal", "press", "demo", "demonstrate", "react", "payoff", "hold", "show", "arrange", "rotate", "place", "use"])


def _merge_beats(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    priority = "mandatory" if "mandatory" in {left["priority"], right["priority"]} else "supporting" if "supporting" in {left["priority"], right["priority"]} else "optional"
    return {
        "sourceBeatIndexes": [*left["sourceBeatIndexes"], *right["sourceBeatIndexes"]],
        "role": left["role"] if left["priority"] == "mandatory" else right["role"],
        "priority": priority,
        "action": f"{left['action']}; then {right['action']}",
        "stateBefore": left.get("stateBefore") or right.get("stateBefore"),
        "stateAfter": right.get("stateAfter") or left.get("stateAfter"),
        "sourceDuration": left["sourceDuration"] + right["sourceDuration"],
    }


def _reduce_beats(beats: list[dict[str, Any]], max_shots: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    warnings = []
    reduced = list(beats)
    optional_count = len([beat for beat in reduced if beat["priority"] == "optional"])
    if len(reduced) > max_shots:
        reduced = [beat for beat in reduced if beat["priority"] != "optional"]
        if optional_count:
            warnings.append({"code": "OPTIONAL_BEATS_REMOVED", "message": f"{optional_count} optional beat(s) were removed to fit the 8-second scene."})
    while len(reduced) > max_shots:
        merge_index = next((index for index in range(1, len(reduced)) if reduced[index]["priority"] != "mandatory" and _compatible_for_merge(reduced[index - 1], reduced[index])), -1)
        if merge_index == -1:
            break
        reduced = [*reduced[: merge_index - 1], _merge_beats(reduced[merge_index - 1], reduced[merge_index]), *reduced[merge_index + 1 :]]
        warnings.append({"code": "SUPPORTING_BEATS_MERGED", "message": "A supporting beat was merged into a neighboring shot to preserve mandatory actions."})
    if len(reduced) > max_shots and all(beat["priority"] == "mandatory" for beat in reduced):
        warnings.append({"code": "MANDATORY_BEAT_OVERLOAD", "message": "Mandatory beats exceed the safe shot count for one 8-second scene."})
    return reduced, warnings


def _allocate_shots(beats: list[dict[str, Any]], analysis: dict[str, Any]) -> list[dict[str, Any]]:
    total_weight = sum(max(0.5, beat["sourceDuration"]) for beat in beats) or 8
    cursor = 0.0
    shots = []
    opening = analysis.get("openingShot") or {}
    camera = analysis.get("cameraStyle") or {}
    for index, beat in enumerate(beats):
        is_last = index == len(beats) - 1
        duration = _round_tenth(8 - cursor) if is_last else max(0.5, _round_tenth((beat["sourceDuration"] / total_weight) * 8))
        start = _round_tenth(cursor)
        end = 8 if is_last else _round_tenth(start + duration)
        cursor = end
        shots.append(
            {
                "shotIndex": index,
                "startSecond": start,
                "endSecond": end,
                "durationSeconds": _round_tenth(end - start),
                "role": beat["role"],
                "priority": beat["priority"],
                "action": beat["action"],
                "physicalAction": beat.get("physicalAction"),
                "framing": opening.get("framing"),
                "cameraAngle": opening.get("cameraAngle"),
                "cameraMovement": opening.get("cameraMovement"),
                "cameraBehavior": camera.get("movement"),
                "subjectPresence": analysis.get("subjectPresence", "none"),
                "stateBefore": beat.get("stateBefore"),
                "stateAfter": beat.get("stateAfter"),
                "sourceBeatIndexes": beat["sourceBeatIndexes"],
            }
        )
    return shots


def _allocate_exact_shots(analysis: dict[str, Any], source_shots: list[dict[str, Any]], source_duration: float) -> list[dict[str, Any]]:
    if not source_shots or source_duration <= 0:
        raise SmartRemakeError("Exact source-shot preservation requires a positive source duration and at least one source shot.", "COMPILER_OUTPUT_INVALID")
    cursor = 0.0
    shots = []
    for index, source in enumerate(source_shots):
        if source.get("shotIndex") != index or source.get("durationSeconds", 0) <= 0 or source.get("endSecond", 0) <= source.get("startSecond", 0):
            raise SmartRemakeError("Exact source-shot timeline is malformed.", "COMPILER_OUTPUT_INVALID")
        duration = _round_tenth(8 - cursor) if index == len(source_shots) - 1 else max(0.1, _round_tenth((source["durationSeconds"] / source_duration) * 8))
        start = _round_tenth(cursor)
        end = 8 if index == len(source_shots) - 1 else _round_tenth(start + duration)
        cursor = end
        if end <= start:
            raise SmartRemakeError("Exact source-shot scaling produced a zero-duration shot.", "COMPILER_OUTPUT_INVALID")
        shots.append(
            {
                "shotIndex": index,
                "startSecond": start,
                "endSecond": end,
                "durationSeconds": _round_tenth(end - start),
                "role": source["role"],
                "priority": source["priority"],
                "action": source["action"],
                "physicalAction": source.get("physicalAction"),
                "framing": source.get("framing"),
                "cameraAngle": source.get("cameraAngle"),
                "cameraMovement": source.get("cameraMovement"),
                "cameraBehavior": source.get("cameraMovement"),
                "productState": source.get("productState"),
                "transitionOut": source.get("transitionOut"),
                "subjectPresence": source.get("subjectPresence", analysis.get("subjectPresence", "none")),
                "stateBefore": source.get("stateBefore"),
                "stateAfter": source.get("stateAfter"),
                "sourceShotIndex": source.get("sourceShotIndex", source.get("shotIndex")),
                "sourceStartSecond": source.get("startSecond"),
                "sourceEndSecond": source.get("endSecond"),
                "sourceBeatIndexes": [],
            }
        )
    return shots


def normalize_scene_timeline(analysis: dict[str, Any], target_duration: int = 8, pacing_profile: str | None = None) -> dict[str, Any]:
    pacing_profile = pacing_profile or _derive_pacing_profile(analysis)
    route = route_creative_structure(analysis)
    source_shots = analysis.get("sourceShots") or []
    visual_structure = route["visualStructure"]
    # Smart Remake has no user-facing adaptive toggle. When measured or
    # analyzed source shots exist, they are the authoritative edit structure.
    shot_mode = "exact" if source_shots else "adaptive"
    warnings = []
    if source_shots and analysis.get("shotPreservationMode") == "adaptive":
        warnings.append({"code": "SOURCE_SHOT_MODE_FORCED_EXACT", "message": "Source cuts were preserved exactly because Smart Remake is source-faithful by default."})
    if shot_mode == "exact" and source_shots:
        source_duration = analysis.get("sourceDurationSeconds") or sum(max(0, shot.get("durationSeconds", 0)) for shot in source_shots)
        shots = _allocate_exact_shots(analysis, source_shots, source_duration)
        if len(source_shots) > 6:
            warnings.append({"code": "HIGH_SHOT_DENSITY", "sourceShotCount": len(source_shots), "targetDuration": 8, "message": "All source shots were preserved in one 8-second scene. Exact model compliance may vary."})
    else:
        candidates = _beat_candidates(analysis)
        max_shots = _target_shot_count(analysis, pacing_profile)
        reduced, warnings = _reduce_beats(candidates, max_shots)
        shots = _allocate_shots(reduced or candidates[:1], analysis)
        if any(beat.get("endSecond", 0) > 8 or beat.get("startSecond", 0) < 0 for beat in analysis.get("motionBeats", [])):
            warnings.append({"code": "SOURCE_TIMELINE_NORMALIZED", "message": "Source motion-beat timestamps were normalized into one 8-second scene."})
    # A source cut list is authoritative. Do not let an analyzer label a
    # multi-cut reference as continuous and then emit a slow one-take prompt.
    if visual_structure == "continuous" and len(source_shots) > 1:
        visual_structure = "sequential_shots"
        warnings.append({"code": "SOURCE_CUT_STRUCTURE_PRESERVED", "message": "Multiple source cuts were preserved as sequential temporal shots."})
    if visual_structure == "continuous":
        warnings.append({"code": "CONTINUOUS_STRUCTURE_PRESERVED", "message": "Continuous visual structure was preserved with minimal cuts."})
    return {
        "targetDuration": 8,
        "pacingProfile": pacing_profile,
        "visualStructure": visual_structure,
        "shots": shots,
        "cutTimes": [shot["endSecond"] for shot in shots[:-1]],
        "warnings": warnings,
    }
