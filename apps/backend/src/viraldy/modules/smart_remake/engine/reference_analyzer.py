from typing import Any

from .creative_router import normalize_creative_structure, route_creative_structure
from .errors import SmartRemakeSecurityError, SmartRemakeValidationError
from .gemini_client import SmartRemakeGeminiClient
from .media_validation import assert_reference_video
from .prompts import build_reference_analysis_prompt
from .schemas import UploadedMedia, normalize_text, string_list


def _normalize_physical_action(raw: Any) -> dict[str, str] | None:
    raw = raw if isinstance(raw, dict) else {}
    normalized = {
        key: normalize_text(raw.get(key))
        for key in ("operator", "targetSurface", "contactPoint", "movement", "visibleEffect")
        if normalize_text(raw.get(key))
    }
    return normalized or None


def _default_audio_plan(raw: dict[str, Any] | None = None) -> dict[str, Any]:
    raw = raw if isinstance(raw, dict) else {}
    reference_music = raw.get("referenceMusic")
    if not isinstance(reference_music, dict):
        reference_music = {"mode": "none"}
    return {
        "mode": raw.get("mode") if raw.get("mode") in {"native", "silent"} else "silent",
        "language": raw.get("language"),
        "dialogue": raw.get("dialogue"),
        "ambience": raw.get("ambience"),
        "soundEffects": string_list(raw.get("soundEffects")),
        "music": raw.get("music"),
        "referenceMusic": reference_music,
        "warnings": string_list(raw.get("warnings")),
    }


def _normalize_pacing_plan(raw: dict[str, Any] | None, motion_beats: list[dict[str, Any]], target_duration: int) -> dict[str, Any]:
    raw = raw if isinstance(raw, dict) else {}
    action_beats = raw.get("actionBeats") if isinstance(raw.get("actionBeats"), list) else []
    if not action_beats:
        action_beats = [
            {"action": beat["action"], "durationSeconds": max(0.5, beat["endSecond"] - beat["startSecond"]), "shotType": "product-focused shot"}
            for beat in motion_beats
        ]
    return {
        "pace": raw.get("pace") if raw.get("pace") in {"slow", "medium", "fast"} else "medium",
        "shotCount": int(raw.get("shotCount") or max(1, len(action_beats))),
        "averageShotDuration": float(raw.get("averageShotDuration") or max(1, target_duration / max(1, len(action_beats)))),
        "cutStyle": raw.get("cutStyle") if raw.get("cutStyle") in {"continuous", "soft_cut", "hard_cut", "jump_cut", "mixed"} else "soft_cut",
        "motionIntensity": raw.get("motionIntensity") if raw.get("motionIntensity") in {"low", "medium", "high"} else "medium",
        "cameraEnergy": raw.get("cameraEnergy") if raw.get("cameraEnergy") in {"static", "smooth", "dynamic"} else "smooth",
        "audioEnergy": raw.get("audioEnergy") if raw.get("audioEnergy") in {"low", "medium", "high"} else "medium",
        "actionBeats": [
            {
                "action": normalize_text(item.get("action"), "show the key product action"),
                "durationSeconds": float(item.get("durationSeconds") or 1),
                "shotType": normalize_text(item.get("shotType"), "product-focused shot"),
            }
            for item in action_beats
            if isinstance(item, dict)
        ],
    }


def _normalize_opening_shot(raw: dict[str, Any] | None, output: dict[str, Any], motion_beats: list[dict[str, Any]], target_duration: int) -> dict[str, Any]:
    raw = raw if isinstance(raw, dict) else {}
    camera = output.get("cameraStyle") if isinstance(output.get("cameraStyle"), dict) else {}
    setting = output.get("setting") if isinstance(output.get("setting"), dict) else {}
    first_action = motion_beats[0]["action"] if motion_beats else "show product"
    return {
        "durationSeconds": float(raw.get("durationSeconds") or min(2, target_duration)),
        "framing": normalize_text(raw.get("framing"), normalize_text(camera.get("framing"), "product close-up")),
        "cameraAngle": normalize_text(raw.get("cameraAngle"), normalize_text(camera.get("angle"), "front")),
        "cameraMovement": normalize_text(raw.get("cameraMovement"), normalize_text(camera.get("movement"), "static")),
        "subjectPresence": raw.get("subjectPresence") if raw.get("subjectPresence") in {"none", "hands_only", "person"} else output.get("subjectPresence", "none"),
        "subjectPosition": normalize_text(raw.get("subjectPosition"), "none"),
        "productPosition": normalize_text(raw.get("productPosition"), "center frame"),
        "productState": normalize_text(raw.get("productState"), "visible"),
        "initialPose": normalize_text(raw.get("initialPose"), "static"),
        "firstAction": normalize_text(raw.get("firstAction"), first_action),
        "gazeDirection": normalize_text(raw.get("gazeDirection")) or None,
        "backgroundLayout": string_list(raw.get("backgroundLayout") or setting.get("backgroundElements")),
        **({"cutAtSecond": float(raw["cutAtSecond"])} if raw.get("cutAtSecond") is not None else {}),
    }


def _normalize_source_shots(output: dict[str, Any]) -> list[dict[str, Any]] | None:
    source = output.get("sourceShots")
    if not isinstance(source, list) or not source:
        return None
    shots = []
    for index, shot in enumerate(source):
        if not isinstance(shot, dict):
            continue
        start = float(shot.get("startSecond", 0))
        duration = max(0.1, float(shot.get("durationSeconds") or 1.0))
        end = float(shot.get("endSecond") or (start + duration or start + 1))
        shots.append(
            {
                "shotIndex": index,
                "startSecond": start,
                "endSecond": max(start + 0.1, end),
                "durationSeconds": max(0.1, float(shot.get("durationSeconds") or (end - start))),
                "role": shot.get("role") or "action",
                "priority": shot.get("priority") or "supporting",
                "framing": normalize_text(shot.get("framing"), "product shot"),
                "cameraAngle": normalize_text(shot.get("cameraAngle"), "front"),
                "cameraMovement": normalize_text(shot.get("cameraMovement"), "static"),
                "subjectPresence": shot.get("subjectPresence") if shot.get("subjectPresence") in {"none", "hands_only", "person"} else output.get("subjectPresence", "none"),
                "action": normalize_text(shot.get("action"), "show product"),
                **({"physicalAction": physical_action} if (physical_action := _normalize_physical_action(shot.get("physicalAction"))) else {}),
                "productState": normalize_text(shot.get("productState")) or None,
                "stateBefore": normalize_text(shot.get("stateBefore")) or None,
                "stateAfter": normalize_text(shot.get("stateAfter")) or None,
                "transitionOut": normalize_text(shot.get("transitionOut")) or None,
            }
        )
    return shots or None


def _assert_no_identity_clone_instruction(value: Any) -> None:
    serialized = str(value).lower()
    forbidden = [
        "identityreference",
        "facereference",
        "referenceactorimage",
        "actoridentitymediaid",
        "same face as the reference",
        "clone the reference actor",
        "preserve the actor identity",
        "use the reference person's likeness",
        "generate_video_refs",
        "generate-video-refs",
    ]
    found = next((phrase for phrase in forbidden if phrase in serialized), None)
    if found:
        raise SmartRemakeSecurityError(
            f"Reference analysis contains forbidden reuse instruction: {found}.",
            "FORBIDDEN_REFERENCE_RENDER_INPUT",
            {"phrase": found},
        )


def normalize_reference_analysis(raw_output: Any, target_duration: int) -> dict[str, Any]:
    if isinstance(raw_output, dict) and isinstance(raw_output.get("referenceAnalysis"), dict):
        raw_output = raw_output["referenceAnalysis"]
    if not isinstance(raw_output, dict):
        raise SmartRemakeValidationError("Reference analysis must be a JSON object.", "INVALID_REFERENCE_ANALYSIS")
    _assert_no_identity_clone_instruction(raw_output)

    motion_beats_raw = raw_output.get("motionBeats") if isinstance(raw_output.get("motionBeats"), list) else []
    motion_beats = []
    for index, beat in enumerate(motion_beats_raw):
        if not isinstance(beat, dict):
            continue
        start = float(beat.get("startSecond", index * 4))
        end = float(beat.get("endSecond", min(target_duration, start + 4)))
        semantic = (raw_output.get("creativeStructure") or {}).get("motionBeatSemantics", [])
        semantic_beat = semantic[index] if isinstance(semantic, list) and index < len(semantic) and isinstance(semantic[index], dict) else {}
        action = normalize_text(beat.get("action") or semantic_beat.get("action"), "show the key product action")
        motion_beats.append(
            {
                "startSecond": max(0, start),
                "endSecond": max(start + 0.1, end),
                "action": action,
                **({"physicalAction": physical_action} if (physical_action := _normalize_physical_action(beat.get("physicalAction"))) else {}),
                "role": beat.get("role") or semantic_beat.get("role") or ("hook" if index == 0 else "action"),
                "priority": beat.get("priority") or semantic_beat.get("priority") or ("mandatory" if index == 0 else "supporting"),
                **({"stateBefore": normalize_text(beat.get("stateBefore") or semantic_beat.get("productStateBefore"))} if normalize_text(beat.get("stateBefore") or semantic_beat.get("productStateBefore")) else {}),
                **({"stateAfter": normalize_text(beat.get("stateAfter") or semantic_beat.get("productStateAfter"))} if normalize_text(beat.get("stateAfter") or semantic_beat.get("productStateAfter")) else {}),
            }
        )
    if not motion_beats:
        motion_beats = [{"startSecond": 0, "endSecond": target_duration, "action": "show the key product action", "role": "hook", "priority": "mandatory"}]

    camera = raw_output.get("cameraStyle") if isinstance(raw_output.get("cameraStyle"), dict) else {}
    setting = raw_output.get("setting") if isinstance(raw_output.get("setting"), dict) else {}
    creative = raw_output.get("creativeConcept") if isinstance(raw_output.get("creativeConcept"), dict) else {}
    audio_plan = _default_audio_plan(raw_output.get("audioPlan") if isinstance(raw_output.get("audioPlan"), dict) else None)
    pacing_plan = _normalize_pacing_plan(raw_output.get("pacingPlan") if isinstance(raw_output.get("pacingPlan"), dict) else None, motion_beats, target_duration)
    opening_shot = _normalize_opening_shot(raw_output.get("openingShot") if isinstance(raw_output.get("openingShot"), dict) else None, {**raw_output, "cameraStyle": camera, "setting": setting}, motion_beats, target_duration)
    source_shots = _normalize_source_shots(raw_output)
    base = {
        "analysisOnly": True,
        "subjectPresence": raw_output.get("subjectPresence") if raw_output.get("subjectPresence") in {"none", "hands_only", "person"} else "none",
        "shotPreservationMode": raw_output.get("shotPreservationMode") if raw_output.get("shotPreservationMode") in {"exact", "adaptive"} else ("exact" if source_shots else "adaptive"),
        "sourceShotCount": len(source_shots) if source_shots else None,
        "sourceDurationSeconds": raw_output.get("sourceDurationSeconds") or (sum(shot["durationSeconds"] for shot in source_shots) if source_shots else None),
        "sourceShots": source_shots,
        "format": normalize_text(raw_output.get("format"), "vertical product ad"),
        "sceneCount": int(raw_output.get("sceneCount") or (1 if target_duration == 8 else 2)),
        "cameraStyle": {
            "angle": normalize_text(camera.get("angle"), "front"),
            "framing": normalize_text(camera.get("framing"), "product close-up"),
            "movement": normalize_text(camera.get("movement"), "subtle push-in"),
        },
        "setting": {
            "locationType": normalize_text(setting.get("locationType"), "studio"),
            "backgroundElements": string_list(setting.get("backgroundElements")) or ["clean background"],
        },
        "actorBehavior": raw_output.get("actorBehavior") if isinstance(raw_output.get("actorBehavior"), dict) else {"expression": None, "gestures": []},
        "creativeConcept": {
            "hook": normalize_text(creative.get("hook"), "Show the product benefit immediately"),
            "adType": normalize_text(creative.get("adType"), "product_demo"),
            "productMoment": normalize_text(creative.get("productMoment"), "product hero moment"),
        },
        "motionBeats": motion_beats,
        "forbiddenReuse": string_list(raw_output.get("forbiddenReuse")),
        "audioPlan": audio_plan,
        "pacingPlan": pacing_plan,
        "openingShot": opening_shot,
        "openingForbiddenSubstitutions": string_list(raw_output.get("openingForbiddenSubstitutions")),
    }
    creative_structure = normalize_creative_structure(raw_output.get("creativeStructure") or raw_output, base)
    route = route_creative_structure({**base, **raw_output, "creativeStructure": creative_structure})
    base.update(
        {
            "creativeArchetype": route["creativeArchetype"],
            "visualStructure": route["visualStructure"],
            "primaryHookType": route["primaryHookType"],
            "productCardinality": route["productCardinality"],
            "renderability": {
                "supported": (raw_output.get("renderability") or {}).get("supported", True) if isinstance(raw_output.get("renderability"), dict) else True,
                "selectedStrategy": route["recommendedStrategy"],
                "warnings": route["warnings"],
            },
            "creativeStructure": creative_structure,
        }
    )
    return {key: value for key, value in base.items() if value is not None}


async def analyze_reference_video(
    *,
    target_duration: int,
    prompt: str | None,
    description: str | None,
    reference_video: UploadedMedia | None,
    gemini: SmartRemakeGeminiClient,
) -> dict[str, Any]:
    if reference_video:
        assert_reference_video(reference_video)
    system, user_prompt = build_reference_analysis_prompt(
        target_duration=target_duration,
        mime_type=reference_video.mime_type if reference_video else None,
        prompt=prompt,
        description=description,
        has_video=bool(reference_video),
    )
    raw = await gemini.generate_json(
        system_instruction=system,
        prompt=user_prompt,
        media=[{"mime_type": reference_video.mime_type, "bytes": reference_video.bytes}] if reference_video else None,
    )
    return normalize_reference_analysis(raw, target_duration)
