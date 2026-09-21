from typing import Any

from .creative_router import route_creative_structure
from .errors import SmartRemakeError
from .guards import assert_no_reference_video_in_render_payload
from .prompt_compressor import build_compressed_smart_remake_prompts
from .prompt_sanitizer import validate_sanitized_compiler_prompts
from .timeline_normalizer import normalize_scene_timeline


def _partition_beats(beats: list[dict[str, Any]], scene_count: int, duration_of) -> list[list[dict[str, Any]]]:
    """Split contiguous beats into scene_count balanced source-order groups.

    A duration-only split can place many short mandatory beats in the first
    8-second scene and leave one long beat in the second scene. That makes a
    valid 16-second Basic remake fail the per-scene shot budget. Keep the
    source order intact, but balance beat count so each generated 8-second
    scene gets a usable share of the narrative.
    """
    if scene_count <= 1:
        return [beats]
    if len(beats) <= 1:
        return [beats] + [[] for _ in range(scene_count - 1)]
    groups: list[list[dict[str, Any]]] = [[] for _ in range(scene_count)]
    start = 0
    for index in range(scene_count):
        remaining_beats = len(beats) - start
        remaining_groups = scene_count - index
        take = (remaining_beats + remaining_groups - 1) // remaining_groups
        end = min(len(beats), start + take)
        groups[index] = beats[start:end]
        start = end
    return groups


def _motion_duration(beat: dict[str, Any]) -> float:
    return max(0.0, beat.get("endSecond", 0) - beat.get("startSecond", 0))


def _pacing_duration(beat: dict[str, Any]) -> float:
    return beat.get("durationSeconds", 0)


def _source_shot_duration(shot: dict[str, Any]) -> float:
    if isinstance(shot.get("durationSeconds"), (int, float)):
        return max(0.1, float(shot["durationSeconds"]))
    return max(0.1, float(shot.get("endSecond", 0)) - float(shot.get("startSecond", 0)))


def _number(value: Any, fallback: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _timed_items(
    items: list[dict[str, Any]],
    duration_of,
    *,
    timeline_start: float = 0.0,
    timeline_end: float | None = None,
) -> list[dict[str, Any]]:
    """Return source-order items with usable contiguous timeline bounds.

    Gemini normally supplies timing for source shots and motion beats. Pacing
    beats do not have timestamps, so they are placed proportionally on the
    same source timeline. This gives all three representations one boundary.
    """
    if not items:
        return []
    explicit = all(_number(item.get("endSecond")) > _number(item.get("startSecond")) for item in items)
    if explicit:
        return [{**item, "_segmentStart": _number(item.get("startSecond")), "_segmentEnd": _number(item.get("endSecond"))} for item in items]

    durations = [max(0.1, _number(duration_of(item), 0.1)) for item in items]
    total_duration = sum(durations)
    available_duration = max(0.1, (timeline_end - timeline_start) if timeline_end is not None else total_duration)
    cursor = timeline_start
    timed = []
    for index, item in enumerate(items):
        end = timeline_start + available_duration if index == len(items) - 1 else cursor + (durations[index] / total_duration) * available_duration
        timed.append({**item, "_segmentStart": cursor, "_segmentEnd": end})
        cursor = end
    return timed


def _group_timed_items(items: list[dict[str, Any]], scene_count: int) -> list[list[dict[str, Any]]]:
    """Split contiguous source items near equal timeline durations.

    A group boundary can only fall between actual items. The selection uses
    time and item density, never semantic labels such as hook or payoff.
    """
    if scene_count <= 1:
        return [items]
    if not items:
        return [[] for _ in range(scene_count)]
    if len(items) < scene_count:
        return [*[[item] for item in items], *([[]] * (scene_count - len(items)))]

    timeline_start = _number(items[0].get("_segmentStart"))
    timeline_end = _number(items[-1].get("_segmentEnd"), timeline_start + len(items))
    total_duration = max(0.1, timeline_end - timeline_start)
    groups: list[list[dict[str, Any]]] = []
    start_index = 0
    for group_index in range(scene_count - 1):
        remaining_groups = scene_count - group_index - 1
        min_boundary = start_index + 1
        max_boundary = len(items) - remaining_groups
        target = timeline_start + total_duration * (group_index + 1) / scene_count
        boundary = min(
            range(min_boundary, max_boundary + 1),
            key=lambda candidate: (
                abs(_number(items[candidate - 1].get("_segmentEnd")) - target),
                abs((candidate / len(items)) - ((group_index + 1) / scene_count)),
                # Favor boundaries with explicit state evidence; this keeps
                # the next segment anchored to a real source handoff without
                # using creative-role labels to choose a narrative shape.
                0 if (items[candidate - 1].get("stateAfter") or items[candidate].get("stateBefore")) else 1,
            ),
        )
        groups.append(items[start_index:boundary])
        start_index = boundary
    groups.append(items[start_index:])
    return groups


def _item_groups_for_ranges(
    items: list[dict[str, Any]],
    duration_of,
    ranges: list[tuple[float, float]],
) -> list[list[dict[str, Any]]]:
    if not ranges:
        return []
    timed = _timed_items(items, duration_of, timeline_start=ranges[0][0], timeline_end=ranges[-1][1])
    groups = [[] for _ in ranges]
    for item in timed:
        midpoint = (_number(item.get("_segmentStart")) + _number(item.get("_segmentEnd"))) / 2
        index = next((index for index, (_, end) in enumerate(ranges) if midpoint <= end or index == len(ranges) - 1), len(ranges) - 1)
        groups[index].append({key: value for key, value in item.items() if not key.startswith("_segment")})
    return groups


def _segment_opening_shot(
    base_opening: dict[str, Any],
    source_shots: list[dict[str, Any]],
    beats: list[dict[str, Any]],
) -> dict[str, Any]:
    """Carry the local segment's actual action/state into its first frame."""
    first = (source_shots or beats or [{}])[0]
    state = first.get("stateBefore") or first.get("productState")
    return {
        **base_opening,
        "durationSeconds": _number(first.get("durationSeconds"), _number(base_opening.get("durationSeconds"), 1.0)),
        "framing": first.get("framing") or base_opening.get("framing"),
        "cameraAngle": first.get("cameraAngle") or base_opening.get("cameraAngle"),
        "cameraMovement": first.get("cameraMovement") or base_opening.get("cameraMovement"),
        "subjectPresence": first.get("subjectPresence") or base_opening.get("subjectPresence"),
        "productState": first.get("productState") or state or base_opening.get("productState"),
        "initialPose": state or base_opening.get("initialPose"),
        "firstAction": first.get("action") or base_opening.get("firstAction"),
    }


def _source_segment_metadata(
    *,
    index: int,
    scene_count: int,
    start_second: float,
    end_second: float,
    cut_style: str | None,
    source_cut: bool,
    previous_state: str | None,
    opening_state: str | None,
) -> dict[str, Any]:
    return {
        "segmentOrder": index + 1,
        "segmentCount": scene_count,
        "sourceTimeRange": {"startSecond": round(start_second, 3), "endSecond": round(end_second, 3)},
        "boundary": {
            "kind": "source_start" if index == 0 else ("source_cut" if source_cut else "continuous_handoff"),
            "cutStyle": cut_style or "natural_cut",
        },
        "continuity": {
            "previousState": previous_state,
            "openingState": opening_state,
            "required": bool(index and (previous_state or opening_state)),
        },
    }


def _source_aware_segments(analysis: dict[str, Any], scene_count: int) -> list[dict[str, Any]]:
    """Build one canonical source-order segmentation for compile inputs.

    Multi-shot references split only at real source-shot boundaries. One-take
    references split on their measured actions and retain a continuity
    handoff; neither path inspects role labels or imposes an ad template.
    """
    source_shots = analysis.get("sourceShots") if isinstance(analysis.get("sourceShots"), list) else []
    motion_beats = analysis.get("motionBeats") if isinstance(analysis.get("motionBeats"), list) else []
    pacing_beats = ((analysis.get("pacingPlan") or {}).get("actionBeats") or []) if isinstance(analysis.get("pacingPlan"), dict) else []
    cut_style = (analysis.get("pacingPlan") or {}).get("cutStyle") if isinstance(analysis.get("pacingPlan"), dict) else None

    timed_source = _timed_items(source_shots, _source_shot_duration)
    has_real_source_cuts = len(timed_source) >= scene_count
    if has_real_source_cuts:
        source_groups = _group_timed_items(timed_source, scene_count)
        ranges = [(_number(group[0]["_segmentStart"]), _number(group[-1]["_segmentEnd"])) for group in source_groups]
        assigned_source = [[{key: value for key, value in shot.items() if not key.startswith("_segment")} for shot in group] for group in source_groups]
        motion_groups = _item_groups_for_ranges(motion_beats, _motion_duration, ranges)
        pacing_groups = _item_groups_for_ranges(pacing_beats, _pacing_duration, ranges)
    else:
        fallback = motion_beats or source_shots
        timeline_end = max(
            _number(analysis.get("sourceDurationSeconds")),
            max((_number(item.get("endSecond")) for item in fallback), default=0.0),
            float(scene_count),
        )
        timed_motion = _timed_items(fallback, _motion_duration, timeline_start=0.0, timeline_end=timeline_end)
        motion_groups_timed = _group_timed_items(timed_motion, scene_count)
        ranges = []
        for index, group in enumerate(motion_groups_timed):
            if group:
                ranges.append((_number(group[0]["_segmentStart"]), _number(group[-1]["_segmentEnd"])))
            else:
                start = timeline_end * index / scene_count
                ranges.append((start, timeline_end * (index + 1) / scene_count))
        motion_groups = [[{key: value for key, value in beat.items() if not key.startswith("_segment")} for beat in group] for group in motion_groups_timed]
        # A one-take cannot be copied into both clips. Empty sourceShots force
        # the normalizer to build each clip from its local action interval.
        assigned_source = [[] for _ in range(scene_count)]
        pacing_groups = _item_groups_for_ranges(pacing_beats, _pacing_duration, ranges)

        # An analysis can describe a one-take with only one broad action.
        # Keep both source intervals explicit rather than letting scene two
        # fall back to the global opening/action.
        if fallback:
            for index, group in enumerate(motion_groups):
                if group:
                    continue
                source_action = fallback[min(index, len(fallback) - 1)]
                motion_groups[index] = [
                    {
                        **source_action,
                        "startSecond": ranges[index][0],
                        "endSecond": ranges[index][1],
                    }
                ]

    segments = []
    previous_state = None
    for index in range(scene_count):
        local_source = assigned_source[index]
        local_motion = motion_groups[index]
        local_pacing = pacing_groups[index]
        first = (local_source or local_motion or [{}])[0]
        last = (local_source or local_motion or [{}])[-1]
        opening_state = first.get("stateBefore") or first.get("productState")
        end_state = last.get("stateAfter") or last.get("productState")
        metadata = _source_segment_metadata(
            index=index,
            scene_count=scene_count,
            start_second=ranges[index][0],
            end_second=ranges[index][1],
            cut_style=cut_style,
            source_cut=has_real_source_cuts,
            previous_state=previous_state,
            opening_state=opening_state,
        )
        segments.append({"sourceShots": local_source, "motionBeats": local_motion, "pacingBeats": local_pacing, "metadata": metadata})
        previous_state = end_state or previous_state
    return segments


def _relative_beats(beats: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not beats:
        return beats
    first_start = beats[0].get("startSecond", 0)
    return [
        {
            **beat,
            "startSecond": max(0, beat.get("startSecond", 0) - first_start),
            "endSecond": max(0.5, beat.get("endSecond", 0) - first_start),
        }
        for beat in beats
    ]


def _relative_source_shots(shots: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not shots:
        return []
    first_start = float(shots[0].get("startSecond", 0))
    relative = []
    for index, shot in enumerate(shots):
        start = max(0.0, float(shot.get("startSecond", 0)) - first_start)
        end = max(start + 0.1, float(shot.get("endSecond", start + _source_shot_duration(shot))) - first_start)
        relative.append(
            {
                **shot,
                "shotIndex": index,
                "sourceShotIndex": shot.get("sourceShotIndex", shot.get("shotIndex", index)),
                "startSecond": start,
                "endSecond": end,
                "durationSeconds": max(0.1, end - start),
            }
        )
    return relative


def _scene_specific_analysis(
    *,
    analysis: dict[str, Any],
    beats: list[dict[str, Any]],
    pacing_beats: list[dict[str, Any]],
    source_shots: list[dict[str, Any]] | None = None,
    opening_shot: dict[str, Any] | None = None,
    opening_forbidden_substitutions: list[str] | None = None,
    shot_preservation_mode: str | None = None,
    source_segment: dict[str, Any] | None = None,
) -> dict[str, Any]:
    # ``source_shots=[]`` is intentional for a continuous source segment. It
    # must remain empty so scene two cannot silently reuse the full one-take.
    source_shots_assigned = source_shots is not None
    motion_beats = _relative_beats(beats if source_segment is not None else (beats or analysis.get("motionBeats", [])[:1]))
    relative_source_shots = _relative_source_shots(source_shots or [])
    pacing_plan = {
        **(analysis.get("pacingPlan") or {}),
        "actionBeats": pacing_beats if source_segment is not None else (pacing_beats or (analysis.get("pacingPlan") or {}).get("actionBeats", [])[:1]),
    }
    return {
        **analysis,
        "shotPreservationMode": "exact" if relative_source_shots else (shot_preservation_mode or analysis.get("shotPreservationMode")),
        "sceneCount": 1,
        "sourceShotCount": len(relative_source_shots) if source_shots_assigned else analysis.get("sourceShotCount"),
        "sourceDurationSeconds": sum(_source_shot_duration(shot) for shot in relative_source_shots) if source_shots_assigned else analysis.get("sourceDurationSeconds"),
        "sourceShots": relative_source_shots if source_shots_assigned else analysis.get("sourceShots"),
        "motionBeats": motion_beats,
        "pacingPlan": pacing_plan,
        "openingShot": opening_shot or analysis.get("openingShot") or {},
        "openingForbiddenSubstitutions": opening_forbidden_substitutions if opening_forbidden_substitutions is not None else analysis.get("openingForbiddenSubstitutions", []),
        "creativeStructure": None,
        "sourceSegment": source_segment or {},
    }


def _compile_scene(display_order: int, scene_count: int, analysis: dict[str, Any], product_lock: dict[str, Any], language: str | None) -> tuple[dict[str, Any], dict[str, Any]]:
    timeline = normalize_scene_timeline(analysis, target_duration=8)
    overload = next((warning for warning in timeline.get("warnings", []) if warning.get("code") == "MANDATORY_BEAT_OVERLOAD"), None)
    if overload and scene_count == 1:
        raise SmartRemakeError(overload["message"], "COMPILER_OUTPUT_INVALID")
    compressed = build_compressed_smart_remake_prompts(
        analysis=analysis,
        product_lock=product_lock,
        timeline=timeline,
        opening_shot=analysis.get("openingShot") or {},
        opening_forbidden_substitutions=analysis.get("openingForbiddenSubstitutions") or [],
        display_order=display_order,
        scene_count=scene_count,
        source_segment=analysis.get("sourceSegment") or None,
        language=language,
    )
    validate_sanitized_compiler_prompts(
        prompt=compressed["prompt"],
        image_prompt=compressed["imagePrompt"],
        video_prompt=compressed["videoPrompt"],
        analysis=analysis,
        product_lock=product_lock,
        timeline=timeline,
    )
    return (
        {
            "displayOrder": display_order,
            "chainType": "ROOT",
            "parentSceneId": None,
            "prompt": compressed["prompt"],
            "imagePrompt": compressed["imagePrompt"],
            "videoPrompt": compressed["videoPrompt"],
            "characterNames": [product_lock["productReference"]["characterName"]],
            "source": "smart_remake",
            "textOverlay": (analysis.get("creativeConcept") or {}).get("hook") if display_order == 0 else (analysis.get("creativeConcept") or {}).get("productMoment"),
            "sourceSegment": analysis.get("sourceSegment") or None,
            "shotPlan": _scene_shot_plan(timeline, analysis.get("sourceSegment") or None),
        },
        timeline,
    )


def _scene_shot_plan(timeline: dict[str, Any], source_segment: dict[str, Any] | None = None) -> dict[str, Any]:
    shots = timeline.get("shots") if isinstance(timeline.get("shots"), list) else []
    return {
        "targetDuration": timeline.get("targetDuration", 8),
        "shotCount": len(shots),
        "cutTimes": timeline.get("cutTimes", []),
        "pacingProfile": timeline.get("pacingProfile"),
        "visualStructure": timeline.get("visualStructure"),
        "sourceSegment": source_segment,
        "shots": [
            {
                "shotIndex": shot.get("shotIndex", index),
                "startSecond": shot.get("startSecond"),
                "endSecond": shot.get("endSecond"),
                "role": shot.get("role"),
                "priority": shot.get("priority"),
                "framing": shot.get("framing"),
                "cameraMovement": shot.get("cameraMovement") or shot.get("cameraBehavior"),
                "action": shot.get("action"),
                "physicalAction": shot.get("physicalAction"),
                "productState": shot.get("productState"),
                "stateBefore": shot.get("stateBefore"),
                "stateAfter": shot.get("stateAfter"),
                "sourceShotIndex": shot.get("sourceShotIndex"),
                "sourceStartSecond": shot.get("sourceStartSecond"),
                "sourceEndSecond": shot.get("sourceEndSecond"),
            }
            for index, shot in enumerate(shots)
        ],
    }


def _diagnostics(analysis: dict[str, Any], scenes: list[dict[str, Any]]) -> dict[str, Any]:
    route = route_creative_structure(analysis)
    scene_diagnostics = []
    for item in scenes:
        timeline = item["timeline"]
        scene_diagnostics.append(
            {
                "displayOrder": item["displayOrder"],
                "pacingProfile": timeline["pacingProfile"],
                "visualStructure": timeline["visualStructure"],
                "openingDurationSeconds": timeline["shots"][0]["endSecond"] if timeline.get("shots") else 0,
                "firstCutTimeSeconds": timeline["cutTimes"][0] if timeline.get("cutTimes") else None,
                "cutTimes": timeline.get("cutTimes", []),
                "shots": [
                    {
                        "shotIndex": shot["shotIndex"],
                        "startSecond": shot["startSecond"],
                        "endSecond": shot["endSecond"],
                        "role": shot["role"],
                        "priority": shot["priority"],
                        "sourceBeatIndexes": shot.get("sourceBeatIndexes", []),
                    }
                    for shot in timeline.get("shots", [])
                ],
                "warnings": timeline.get("warnings", []),
                "sourceSegment": item["scene"].get("sourceSegment"),
            }
        )
    return {
        "creativeArchetype": route["creativeArchetype"],
        "visualStructure": route["visualStructure"],
        "primaryHookType": route["primaryHookType"],
        "selectedStrategy": route["recommendedStrategy"],
        "scenes": scene_diagnostics,
        "normalizationWarnings": [warning for scene in scene_diagnostics for warning in scene.get("warnings", [])],
    }


def compile_smart_remake_scene_map_with_diagnostics(input_data: dict[str, Any]) -> dict[str, Any]:
    target_duration = input_data["targetDuration"]
    reference_analysis = input_data["referenceAnalysis"]
    product_lock = input_data["productLock"]
    language = input_data.get("language")
    mode = input_data.get("mode") or "smart_remake"
    scene_count = max(1, min(4, target_duration // 8))
    if scene_count == 1:
        scene_inputs = [
            {
                "displayOrder": 0,
                "analysis": _scene_specific_analysis(
                    analysis=reference_analysis,
                    beats=reference_analysis.get("motionBeats", []),
                    pacing_beats=(reference_analysis.get("pacingPlan") or {}).get("actionBeats", []),
                    source_shots=reference_analysis.get("sourceShots", []),
                    opening_shot=reference_analysis.get("openingShot"),
                    opening_forbidden_substitutions=reference_analysis.get("openingForbiddenSubstitutions", []),
                    shot_preservation_mode=reference_analysis.get("shotPreservationMode"),
                ),
            }
        ]
    else:
        segments = _source_aware_segments(reference_analysis, scene_count)
        scene_inputs = [
            {
                "displayOrder": index,
                "analysis": _scene_specific_analysis(
                    analysis=reference_analysis,
                    beats=segments[index]["motionBeats"],
                    pacing_beats=segments[index]["pacingBeats"],
                    source_shots=segments[index]["sourceShots"],
                    opening_shot=_segment_opening_shot(
                        reference_analysis.get("openingShot") or {},
                        segments[index]["sourceShots"],
                        segments[index]["motionBeats"],
                    ),
                    opening_forbidden_substitutions=reference_analysis.get("openingForbiddenSubstitutions", []) if index == 0 else [],
                    shot_preservation_mode=reference_analysis.get("shotPreservationMode"),
                    source_segment=segments[index]["metadata"],
                ),
            }
            for index in range(scene_count)
        ]
    compiled = []
    for scene_input in scene_inputs:
        scene, timeline = _compile_scene(scene_input["displayOrder"], scene_count, scene_input["analysis"], product_lock, language)
        compiled.append({"displayOrder": scene_input["displayOrder"], "scene": scene, "timeline": timeline})
    scene_map = {
        "version": "smart-remake-scene-map-v1",
        "mode": mode,
        "targetDuration": target_duration,
        "aspectRatio": "9:16",
        "orientation": "VERTICAL",
        "sceneCount": scene_count,
        "scenes": [item["scene"] for item in compiled],
    }
    if len(scene_map["scenes"]) != scene_count:
        raise SmartRemakeError("Smart Remake compiler produced an invalid scene map.", "COMPILER_OUTPUT_INVALID")
    assert_no_reference_video_in_render_payload(scene_map)
    return {"sceneMap": scene_map, "diagnostics": _diagnostics(reference_analysis, compiled)}


def compile_smart_remake_scene_map(input_data: dict[str, Any]) -> dict[str, Any]:
    return compile_smart_remake_scene_map_with_diagnostics(input_data)["sceneMap"]
