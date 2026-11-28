"""Compile observed source scenes into independent raw renders and timeline edits."""

from __future__ import annotations

import copy
import hashlib
import json
import math
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
from uuid import UUID, uuid4

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from viraldy.platform.config.settings import Settings
from viraldy.platform.storage.s3 import S3StorageAdapter
from viraldy.shared.errors.base import AppError

from .engine.config import get_gemini_model, get_openai_image_quality
from .engine.errors import SmartRemakeError
from .engine.gemini_client import HttpGeminiClient, SmartRemakeGeminiClient
from .engine.media_binaries import ffmpeg_path, ffprobe_path
from .engine.media_probe import probe_media_bytes
from .engine.media_validation import assert_product_image, assert_reference_video
from .engine.product_lock_generator import generate_product_lock, prepare_product_analysis_images
from .engine.prompt_sanitizer import (
    sanitize_generation_scene,
    sanitize_reference_product_text,
    validate_sanitized_compiler_prompts,
)
from .engine.reference_analyzer import (
    analyze_reference_video,
    resolve_source_cut_semantics,
    validate_source_analysis,
)
from .engine.schemas import ProductMetadata, UploadedMedia
from .engine.source_shot_detector import enrich_reference_analysis_with_detected_cuts
from .fixture import FixtureGeminiClient
from .generation_expectations import (
    build_generation_expectations,
    expectations_hash,
    validate_product_lock,
)
from .models import SmartRemakeProjectModel
from .product_references import MAX_PRODUCT_REFERENCE_IMAGES
from .repair_media import RepairMediaStore
from .repair_repository import RepairRepository
from .service import _duration, _error, _read_product_link_image, feature_enabled, read_media
from .timeline_planner import build_timeline_plan, source_boundaries, validate_source_excerpt


def measure_video_frames(data: bytes) -> int:
    """Measure the video packet clock, excluding any longer audio/container duration."""
    with tempfile.TemporaryDirectory(prefix="smart-remake-video-clock-") as tmp:
        path = Path(tmp) / "source"
        path.write_bytes(data)
        process = subprocess.run(  # noqa: S603 - fixed local argv; no shell
            [
                ffprobe_path(),
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_packets",
                "-show_entries",
                "packet=pts_time,duration_time",
                "-of",
                "json",
                str(path),
            ],
            check=True,
            capture_output=True,
            timeout=120,
        )
    packets = json.loads(process.stdout).get("packets") or []
    intervals = [
        (float(packet["pts_time"]), float(packet.get("duration_time", 0)))
        for packet in packets
        if packet.get("pts_time") is not None
    ]
    if not intervals:
        raise AppError("SMART_REMAKE_SOURCE_INVALID", "No readable source video frames exist.")
    duration = max(start + length for start, length in intervals) - min(
        start for start, _ in intervals
    )
    return math.floor(duration * 24 + 1e-6)


def extract_timeline_thumbnails(source: UploadedMedia, seconds: list[float]) -> list[bytes]:
    with tempfile.TemporaryDirectory(prefix="smart-remake-thumbnails-") as tmp:
        source_path = Path(tmp) / "excerpt.mp4"
        source_path.write_bytes(source.bytes)
        result = []
        for index, second in enumerate(seconds):
            target = Path(tmp) / f"scene-{index}.jpg"
            subprocess.run(  # noqa: S603 - fixed local argv; no shell
                [
                    ffmpeg_path(),
                    "-y",
                    "-ss",
                    str(second),
                    "-i",
                    str(source_path),
                    "-frames:v",
                    "1",
                    "-vf",
                    "scale=240:-2",
                    "-q:v",
                    "4",
                    str(target),
                ],
                check=True,
                capture_output=True,
                timeout=60,
            )
            result.append(target.read_bytes())
        return result


def extract_source_excerpt(
    source: UploadedMedia, *, start_frame: int, total_frames: int
) -> UploadedMedia:
    """Decode the selected interval at normal speed; never pad missing source frames."""
    with tempfile.TemporaryDirectory(prefix="smart-remake-excerpt-") as tmp:
        input_path, output_path = Path(tmp) / "source", Path(tmp) / "excerpt.mp4"
        input_path.write_bytes(source.bytes)
        start, end = start_frame / 24, (start_frame + total_frames) / 24
        subprocess.run(  # noqa: S603 - fixed argv with generated local paths; no shell
            [
                ffmpeg_path(),
                "-y",
                "-i",
                str(input_path),
                "-ss",
                str(start),
                "-t",
                str(end - start),
                "-map",
                "0:v:0",
                "-map",
                "0:a:0?",
                "-vf",
                "setpts=PTS-STARTPTS,fps=24",
                "-af",
                "asetpts=PTS-STARTPTS",
                "-c:v",
                "libx264",
                "-preset",
                "fast",
                "-crf",
                "20",
                "-c:a",
                "aac",
                "-movflags",
                "+faststart",
                str(output_path),
            ],
            check=True,
            capture_output=True,
            timeout=120,
        )
        return UploadedMedia(
            bytes=output_path.read_bytes(), mime_type="video/mp4", file_name="excerpt.mp4"
        )


def _local_shots(analysis: dict[str, Any], start: float, end: float) -> list[dict[str, Any]]:
    source = analysis.get("sourceShots") or analysis.get("motionBeats") or []
    shots: list[dict[str, Any]] = []
    for item in source:
        left, right = (
            max(start, float(item.get("startSecond", 0))),
            min(end, float(item.get("endSecond", end))),
        )
        if right <= left:
            continue
        shot = {
            **item,
            "shotIndex": len(shots),
            "sourceShotIndex": item.get("shotIndex"),
            "startSecond": left - start,
            "endSecond": right - start,
            "durationSeconds": right - left,
            "stateBefore": item.get("stateBefore")
            if abs(left - float(item.get("startSecond", 0))) < 1e-6 else None,
            "stateAfter": item.get("stateAfter")
            if abs(right - float(item.get("endSecond", end))) < 1e-6 else None,
        }
        shots.append(shot)
    if not shots:
        raise AppError(
            "SMART_REMAKE_SOURCE_ANALYSIS_INCOMPLETE",
            "No source action covers this scene. Update the source boundaries and analyze again.",
        )
    return shots


def _compile_scene(
    *,
    analysis: dict[str, Any],
    product_lock: dict[str, Any],
    source: dict[str, Any],
    unit: dict[str, Any],
    source_start: int,
    scene_count: int,
    language: str | None,
    fit_target: bool = False,
    visual_cut_frames: list[int] | None = None,
) -> dict[str, Any]:
    source_first = unit.get("sourceStartFrame", source["startFrame"])
    source_last = unit.get("sourceEndFrame", source["endFrame"])
    local_start = (source_first - source_start) / 24
    local_end = (source_last - source_start) / 24
    duration = unit["targetDurationFrames"] / 24
    shots = _local_shots(analysis, local_start, local_end)
    if fit_target:
        from .source_timing import fit_observed_shots

        shots = fit_observed_shots(
            shots, source_start=local_start, source_end=local_end,
            target_frames=unit["targetDurationFrames"],
        )
    scene_count_text = f"Scene {unit['sceneIndex']+1} of {scene_count}."
    identity = str(product_lock["productName"])
    actions = "\n".join(
        f"{shot['startSecond']:g}–{shot['endSecond']:g}s: {shot.get('action', '')}. "
        f"Camera: {shot.get('cameraAngle') or (analysis.get('cameraStyle') or {}).get('angle')}; "
        f"{shot.get('cameraMovement') or (analysis.get('cameraStyle') or {}).get('movement')}. "
        f"State: {shot.get('stateBefore') or ''} → {shot.get('stateAfter') or ''}."
        for shot in shots
    )
    summary = f"{scene_count_text} {identity}. Source action: {shots[0].get('action')}."
    image_prompt = (
        f"One photorealistic full-screen 9:16 opening frame. Use the uploaded {identity} "
        "as the exact product identity; preserve its proportions, colors, material and branding. "
        f"Setting: {analysis.get('setting')}. Subject presence: {analysis.get('subjectPresence')}. "
        f"Opening action/state: {shots[0].get('action')}; {shots[0].get('stateBefore') or ''}. "
        "Do not copy reference product identity, faces, captions, or logos."
    )
    timing_direction = (
        "within the assigned output interval. Recreate the observed actions, adapting their "
        "pace to that interval while preserving their order and physical cause and effect. "
        "Source evidence timestamps are provenance, not output timing. "
        if fit_target else
        "at its original speed. "
    )
    video_prompt = (
        f"{scene_count_text} Execute the assigned {duration:g}-second source action "
        f"{timing_direction}All timestamps below are local to this scene; the outer "
        "generation plan places this scene in its scheduled interval within the video. "
        "Preserve action order and physical cause and effect within the assigned interval. "
        "The seller will review "
        "a fixed-length selection before publishing; no selection is automatically approved. "
        f"Use only the uploaded {identity}, retaining exact product identity and physical use. "
        f"Subject presence: {analysis.get('subjectPresence')}. Setting: {analysis.get('setting')}. "
        f"Language: {language or 'source context'}. "
        "No frozen frames or invented/repeated actions.\n"
        f"SOURCE ACTION TIMELINE\n{actions}"
    )
    prompts = {
        key: sanitize_reference_product_text(
            text=text, analysis=analysis, product_lock=product_lock
        )
        for key, text in {
            "prompt": summary,
            "imagePrompt": image_prompt,
            "videoPrompt": video_prompt,
        }.items()
    }
    segment = {
        "segmentOrder": unit["sceneIndex"] + 1,
        "segmentCount": scene_count,
        "sourceTimeRange": {
            "startSecond": source_first / 24,
            "endSecond": source_last / 24,
        },
        "boundary": {"kind": (
            "source_continuation" if fit_target and unit.get("fragmentIndex", 0) > 0
            else "source_start" if not unit["sceneIndex"] else "source_cut"
        )},
    }
    if fit_target:
        segment.update({
            "timingMode": "fit_target", "sourceSceneId": source["id"],
            "sourceSceneIndex": source.get("sourceSceneIndex", unit["sceneIndex"]),
            "fragmentIndex": unit.get("fragmentIndex", 0),
            "fragmentCount": unit.get("fragmentCount", 1),
        })
    shot_plan = {
        "targetDuration": duration,
        "rawDurationFrames": unit.get("rawDurationFrames", 192),
        "targetDurationFrames": unit["targetDurationFrames"],
        "shotCount": len(shots),
        "shots": shots,
        "cutTimes": [shot["startSecond"] for shot in shots[1:]],
        "visualStructure": "continuous" if len(shots) == 1 else "sequential_shots",
        "sourceSegment": segment,
    }
    if fit_target:
        from .source_timing import fit_source_motion_beats

        shot_plan["timingMode"] = "fit_target"
        shot_plan["cutTimes"] = [
            round(
                (cut - source_first) * unit["targetDurationFrames"] / (source_last - source_first)
            )
            / 24
            for cut in visual_cut_frames or [] if source_first < cut < source_last
        ]
        shot_plan["shotCount"] = len(shot_plan["cutTimes"]) + 1
        shot_plan["visualStructure"] = (
            "sequential_shots" if shot_plan["cutTimes"] else "continuous"
        )
        beats = fit_source_motion_beats(
            analysis, source_start=local_start, source_end=local_end,
            target_frames=unit["targetDurationFrames"],
        )
        shot_plan["motionBeats"] = beats
        source_pacing = analysis.get("pacingPlan") or {}
        shot_plan["pacingPlan"] = {
            **{
                key: source_pacing[key]
                for key in ("pace", "motionIntensity", "cameraEnergy", "audioEnergy")
                if key in source_pacing
            },
            "shotCount": shot_plan["shotCount"],
            "averageShotDuration": duration / shot_plan["shotCount"],
            "cutStyle": "mixed" if shot_plan["cutTimes"] else "continuous",
            "sourceDurationSeconds": local_end - local_start,
            "targetDurationSeconds": duration,
            "actionBeats": [
                {key: beat[key] for key in ("sourceBeatIndex", "action", "durationSeconds")}
                for beat in beats
            ],
        }
    validate_sanitized_compiler_prompts(
        prompt=prompts["prompt"],
        image_prompt=prompts["imagePrompt"],
        video_prompt=prompts["videoPrompt"],
        analysis=analysis,
        product_lock=product_lock,
        timeline=shot_plan,
    )
    return sanitize_generation_scene({
        "displayOrder": unit["sceneIndex"],
        "chainType": "ROOT",
        "parentSceneId": None,
        **prompts,
        "characterNames": [product_lock["productReference"]["characterName"]],
        "source": "smart_remake",
        "sourceSegment": segment,
        "shotPlan": shot_plan,
        "targetDurationFrames": unit["targetDurationFrames"],
        "rawDurationFrames": unit.get("rawDurationFrames", 192),
    }, analysis, product_lock)


def build_timeline_compile(
    *,
    analysis: dict[str, Any],
    product_lock: dict[str, Any],
    plan: dict[str, Any],
    language: str | None,
    mode: str,
) -> dict[str, Any]:
    source_map = plan["sourceSceneMap"]
    fit_target = source_map.get("timingMode") == "fit_target"
    validate_source_analysis(
        analysis, target_duration=(
            source_map["sourceFrameCount"] if fit_target
            else plan["draftTimeline"]["totalFrames"]
        ) / 24
    )
    validate_product_lock(product_lock)
    if (analysis.get("renderability") or {}).get("supported") is False:
        raise AppError(
            "SMART_REMAKE_SOURCE_UNSUPPORTED",
            "The source structure cannot preserve the product with this render plan.", 409,
        )
    if (analysis.get("sourceCutDetection") or {}).get("requiresSemanticReanalysis"):
        raise AppError(
            "SMART_REMAKE_SOURCE_ANALYSIS_INCOMPLETE",
            "Complete the per-scene source analysis before generating.", 409,
        )
    result = copy.deepcopy(plan)
    source_map, render_plan = result["sourceSceneMap"], result["renderPlan"]
    scenes = []
    sources = {source["id"]: source for source in source_map["scenes"]}
    visual_cuts = [source["endFrame"] for source in source_map["scenes"][:-1]]
    generation_analysis = analysis
    if fit_target:
        from .source_timing import assert_observed_fragment_boundaries, source_frame_clock_analysis

        assert_observed_fragment_boundaries(analysis, render_plan["units"])
        generation_analysis = source_frame_clock_analysis(analysis)
    for unit in render_plan["units"]:
        source = sources[unit["sourceSceneId"]]
        scene = _compile_scene(
            analysis=generation_analysis,
            product_lock=product_lock,
            source=source,
            unit=unit,
            source_start=source_map["sourceStartFrame"],
            scene_count=len(render_plan["units"]),
            language=language,
            fit_target=fit_target,
            visual_cut_frames=visual_cuts,
        )
        scenes.append(scene)
        unit.update({key: scene[key] for key in ("prompt", "imagePrompt", "videoPrompt")})
    logical_prompts = []
    if fit_target:
        for index, source in enumerate(source_map["scenes"]):
            logical = _compile_scene(
                analysis=generation_analysis, product_lock=product_lock, source=source,
                unit={"sceneIndex": index, "targetDurationFrames": source["targetDurationFrames"]},
                source_start=source_map["sourceStartFrame"],
                scene_count=len(source_map["scenes"]), language=language, fit_target=True,
                visual_cut_frames=visual_cuts,
            )
            source.update({key: logical[key] for key in ("prompt", "imagePrompt", "videoPrompt")})
            source["shotPlan"] = {
                key: value for key, value in logical["shotPlan"].items()
                if key != "rawDurationFrames"
            }
            logical_prompts.append({
                "sourceSceneId": source["id"],
                **{
                    key: logical[key]
                    for key in ("displayOrder", "prompt", "imagePrompt", "videoPrompt")
                },
            })
    total_duration = result["draftTimeline"]["totalFrames"] // 24
    scene_map = {
        "schemaVersion": 2,
        "version": "smart-remake-scene-map-v2",
        "mode": mode,
        "targetDuration": total_duration,
        "aspectRatio": "9:16",
        "orientation": "VERTICAL",
        "sceneCount": len(scenes),
        "scenes": scenes,
    }
    return {
        **result,
        "schemaVersion": 2,
        "success": True,
        "mode": mode,
        "renderSubmitted": False,
        "sceneMap": scene_map,
        "referenceAnalysis": analysis,
        "productLock": product_lock,
        "inputSummary": {
            "targetDuration": total_duration,
            "aspectRatio": "9:16",
            "language": language,
        },
        "analyzeOutput": {"audioPlan": analysis.get("audioPlan"), "warnings": []},
        "compiledPrompts": [
            {key: scene[key] for key in ("displayOrder", "prompt", "imagePrompt", "videoPrompt")}
            for scene in scenes
        ] if not fit_target else logical_prompts,
        "compilerVersion": "smart-remake-timeline-v2.3",
        "compilerDiagnostics": {},
        "diagnostics": {},
        "versions": {"compiler": "smart-remake-timeline-v2.3"},
        "warnings": [],
    }


async def _retain_compile_orphans(
    repository: RepairRepository, workspace_id: UUID, project_id: UUID, keys: list[str]
) -> None:
    if not keys:
        return
    current = await repository.project(workspace_id, project_id, lock=True)
    context = copy.deepcopy(current.context_json)
    p0 = context["p0"]
    p0["retainedMediaKeys"] = sorted({*p0.get("retainedMediaKeys", []), *keys})
    current.context_json = context
    await repository.session.commit()


def source_opening_bindings(
    source: UploadedMedia, scenes: list[dict[str, Any]]
) -> dict[str, dict[str, Any]]:
    from .image_workflow import OPENING_FRAME_EXTRACTOR_VERSION, extract_layout_frame

    source_hash = hashlib.sha256(source.bytes).hexdigest()
    return {
        scene["id"]: {
            "sourceMediaHash": source_hash,
            "frame": scene["startFrame"],
            "layoutHash": hashlib.sha256(
                extract_layout_frame(source.bytes, scene["startFrame"])
            ).hexdigest(),
            "extractorVersion": OPENING_FRAME_EXTRACTOR_VERSION,
        }
        for scene in scenes
    }


async def initialize_timeline_project(
    *,
    repository: RepairRepository,
    media: RepairMediaStore,
    workspace_id: UUID,
    compile_result: dict[str, Any],
    source: UploadedMedia,
    product: UploadedMedia,
    source_probe: dict[str, Any],
    thumbnails: list[bytes] | None = None,
    image_assets: dict[str, Any] | None = None,
    existing_project: SmartRemakeProjectModel | None = None,
    expected_revision: int | None = None,
    compile_operation_id: UUID | None = None,
    additional_products: list[UploadedMedia] | None = None,
) -> SmartRemakeProjectModel:
    project_id = existing_project.id if existing_project is not None else uuid4()
    original_revision = (
        existing_project.state_json["revision"] if existing_project is not None else None
    )
    prefix = f"workspaces/{workspace_id}/smart-remake/{project_id}"
    thumbnail_keys = {}
    binding_scenes = compile_result["sourceSceneMap"]["scenes"]
    if compile_result["sourceSceneMap"].get("timingMode") == "fit_target":
        binding_scenes = [
            {"id": unit["id"], "startFrame": unit["sourceStartFrame"]}
            for unit in compile_result["renderPlan"]["units"]
        ]
    opening_frames = await run_in_threadpool(source_opening_bindings, source, binding_scenes)
    additional_assets = copy.deepcopy(
        (existing_project.context_json.get("p0") or {}).get("additionalProductReferences", [])
    ) if existing_project is not None else []
    try:
        source_key = (
            existing_project.context_json["sourceKey"] if existing_project is not None
            else await media.put(prefix, source.bytes, source.mime_type)
        )
        product_key = (
            existing_project.context_json["productKey"] if existing_project is not None
            else await media.put(prefix, product.bytes, product.mime_type)
        )
        if existing_project is None:
            for upload in additional_products or []:
                key = await media.put(prefix, upload.bytes, upload.mime_type)
                additional_assets.append({
                    "id": str(uuid4()), "role": "product", "storageKey": key,
                    "mimeType": upload.mime_type,
                    "mediaHash": hashlib.sha256(upload.bytes).hexdigest(),
                    "sizeBytes": len(upload.bytes),
                })
        for scene, data in zip(
            compile_result["sourceSceneMap"]["scenes"], thumbnails or [], strict=False
        ):
            thumbnail_keys[scene["id"]] = await media.put(prefix, data, "image/jpeg")
    except Exception as exc:
        if existing_project is not None:
            await _retain_compile_orphans(
                repository, workspace_id, project_id, list(thumbnail_keys.values())
            )
        raise AppError(
            "SMART_REMAKE_RETENTION_UNAVAILABLE",
            "Source and product storage is unavailable.",
            503,
        ) from exc
    if existing_project is not None:
        from .project_policy import assert_project_policy
        from .repair_service import _revision

        existing_project = await repository.project(workspace_id, project_id, lock=True)
        try:
            assert_project_policy(existing_project, purpose="analysis")
            _revision(
                existing_project.state_json,
                expected_revision if expected_revision is not None
                else cast(int, original_revision),
            )
        except AppError:
            # Owned writes that raced a stop/revision remain discoverable for cleanup.
            retained_context = copy.deepcopy(existing_project.context_json)
            p0 = retained_context["p0"]
            p0["retainedMediaKeys"] = sorted({
                *p0.get("retainedMediaKeys", []), *thumbnail_keys.values(),
            })
            existing_project.context_json = retained_context
            await repository.session.commit()
            raise
    result = copy.deepcopy(compile_result)
    previous = copy.deepcopy(existing_project.context_json) if existing_project is not None else {}
    context = {
        **previous,
        "schemaVersion": 2,
        "sourceKey": source_key,
        "sourceMimeType": source.mime_type,
        "sourceMediaHash": hashlib.sha256(source.bytes).hexdigest(),
        "sourceProbe": source_probe,
        "sourceFrameCount": result["sourceSceneMap"]["sourceFrameCount"],
        "sourceThumbnailKeys": thumbnail_keys,
        "sourceOpeningFrames": opening_frames,
        "productKey": product_key,
        "productMimeType": product.mime_type,
        "productMediaHash": hashlib.sha256(product.bytes).hexdigest(),
        "sceneMap": result["sceneMap"],
        "productLock": result["productLock"],
        "referenceAnalysis": result["referenceAnalysis"],
        "audioRequired": bool(result["renderPlan"].get("audioRequired", False)),
        "projectName": previous.get("projectName", "Smart Remake"),
        "textOverlays": [],
        "sourceSceneMap": result["sourceSceneMap"],
        "renderPlan": result["renderPlan"],
        "compileResult": result,
    }
    if image_assets:
        context["imageAssets"] = copy.deepcopy(image_assets)
    if additional_assets:
        context.setdefault("p0", {})["additionalProductReferences"] = additional_assets
    context["generationExpectations"] = build_generation_expectations(context)
    context["expectationsHash"] = expectations_hash(context["generationExpectations"])
    if result["sourceSceneMap"].get("timingMode") == "fit_target":
        from .provider_group_planning import freeze_provider_groups

        result["renderPlan"] = freeze_provider_groups(context)
        context["renderPlan"] = copy.deepcopy(result["renderPlan"])
    context["compileResult"] = {
        **result, "expectationsVersion": 1, "expectationsHash": context["expectationsHash"],
    }
    previous_state = existing_project.state_json if existing_project is not None else {}
    state = {
        "id": str(project_id),
        "schemaVersion": 2,
        "revision": previous_state.get("revision", 0) + 1,
        "phase": "compiled",
        "status": "draft",
        "finalVideoUrl": "",
        "targetDuration": result["sceneMap"]["targetDuration"],
        "provider": "kie",
        "sourceSceneMap": copy.deepcopy(result["sourceSceneMap"]),
        "renderPlan": copy.deepcopy(result["renderPlan"]),
        "draftTimeline": copy.deepcopy(result["draftTimeline"]),
        "publishedTimeline": None,
        "scenes": [
            {
                "id": unit["id"],
                "index": index,
                "startSecond": result["draftTimeline"]["items"][index]["targetStartFrame"] / 24,
                "durationSeconds": unit["targetDurationFrames"] / 24,
                "rawDurationFrames": unit["rawDurationFrames"],
                "activeVersionId": None,
                "versions": [],
                **{key: unit[key] for key in ("prompt", "imagePrompt", "videoPrompt")},
            }
            for index, unit in enumerate(result["renderPlan"]["units"])
        ],
    }
    if existing_project is not None:
        from .assembly_snapshots import invalidate_release

        retired = set(previous.get("p0", {}).get("retainedMediaKeys", []))
        retired.update(previous.get("sourceThumbnailKeys", {}).values())
        retired.update(
            version["storageKey"] for scene in previous_state.get("scenes", [])
            for version in scene.get("versions", []) if version.get("storageKey")
        )
        if previous_state.get("finalStorageKey"):
            retired.add(previous_state["finalStorageKey"])
        context["p0"] = invalidate_release(context["p0"], "plan_recompiled")
        context["p0"]["runtime"] = {
            "serverMode": result.get("serverMode"),
            "executionMode": result.get("executionMode", "unverified"),
            "compileOperationId": str(compile_operation_id) if compile_operation_id else None,
        }
        context["p0"]["retainedMediaKeys"] = sorted(retired)
        if previous_state.get("scenes"):
            context["p0"]["planHistory"] = [
                *context["p0"].get("planHistory", []),
                {"id": str(uuid4()), "revision": previous_state["revision"],
                 "retiredAt": datetime.now(UTC).isoformat(),
                 "stateSnapshot": copy.deepcopy(previous_state),
                 "contextSnapshot": {
                     key: copy.deepcopy(previous[key]) for key in (
                         "sceneMap", "productLock", "referenceAnalysis", "sourceSceneMap",
                         "renderPlan", "compileResult", "sourceThumbnailKeys",
                         "sourceOpeningFrames", "generationExpectations", "expectationsHash",
                     ) if key in previous
                 }},
            ]
        state.update({key: copy.deepcopy(previous_state[key]) for key in (
            "finalStorageKey", "assemblyCheck", "publishedTimeline"
        ) if key in previous_state})
        existing_project.context_json = context
        await repository.save(existing_project, state)
        return existing_project
    row = SmartRemakeProjectModel(
        id=project_id, workspace_id=workspace_id, revision=1, state_json=state, context_json=context
    )
    await repository.create(row)
    return row


async def compile_timeline_request(
    *,
    session: AsyncSession,
    settings: Settings,
    workspace_id: UUID,
    mode: str,
    target_duration: str,
    aspect_ratio: str,
    language: str | None,
    prompt: str | None,
    description: str | None,
    product_url: str | None,
    product_title: str | None,
    product_description: str | None,
    reference_video: UploadFile | None,
    product_image: UploadFile | None,
    reference_start_frame: int = 0,
    source_cut_frames: list[int] | None = None,
    render_group_breaks: list[int] | None = None,
    project_id: UUID | None = None,
    expected_revision: int | None = None,
    idempotency_key: str | None = None,
    actor_id: UUID | None = None,
    analysis_scope: str = "excerpt",
    additional_product_images: list[UploadFile] | None = None,
) -> dict[str, Any]:
    if not feature_enabled(settings):
        raise AppError("SMART_REMAKE_DISABLED", "Smart Remake is disabled.", 503)
    if aspect_ratio != "9:16":
        raise AppError("INVALID_SMART_REMAKE_ASPECT_RATIO", "Smart Remake supports 9:16 only.")
    if analysis_scope not in {"excerpt", "full_source"}:
        raise AppError("SMART_REMAKE_SOURCE_RANGE_INVALID", "Unsupported source analysis scope.")
    full_source = analysis_scope == "full_source"
    if len(additional_product_images or []) >= MAX_PRODUCT_REFERENCE_IMAGES:
        raise AppError(
            "SMART_REMAKE_PRODUCT_REFERENCES_INVALID", "Use at most fourteen product images.", 422
        )
    if full_source and reference_start_frame != 0:
        raise AppError(
            "SMART_REMAKE_SOURCE_RANGE_INVALID", "Full-source analysis must start at frame zero."
        )
    if settings.ai_mode.strip().lower() not in {"fixture", "mock"} and project_id is None:
        raise AppError(
            "SMART_REMAKE_INTAKE_REQUIRED", "Create an owned intake before analyzing media.", 409
        )
    duration = _duration(target_duration)
    reference = await read_media(reference_video, "video/mp4")
    product = await read_media(product_image, "image/png")
    additional = [
        value for upload in additional_product_images or []
        if (value := await read_media(upload, "image/png")) is not None
    ]
    owned = (
        await RepairRepository(session).project(workspace_id, project_id)
        if project_id is not None
        else None
    )
    compile_operation = None
    compile_intent = None
    fresh_compile = False
    compile_completed = False
    summary_task = None
    if owned is not None and (
        owned.context_json.get("p0") or settings.ai_mode.strip().lower() not in {"fixture", "mock"}
    ):
        from .project_intake import assert_input_binding
        from .project_policy import assert_project_policy, stable_hash
        from .repair_service import _revision

        assert_project_policy(owned, purpose="analysis")
        await assert_input_binding(owned, RepairMediaStore(S3StorageAdapter(settings)))
        if expected_revision is None or not idempotency_key:
            raise AppError(
                "SMART_REMAKE_INTAKE_REVISION_REQUIRED",
                "Compile requires the saved revision and an idempotency key.", 409,
            )
        if product_url:
            raise AppError("SMART_REMAKE_INPUT_CHANGED", "Compile must use the owned product.", 409)
        for uploaded, role in ((reference, "source"), (product, "product")):
            if uploaded is not None and hashlib.sha256(uploaded.bytes).hexdigest() != (
                owned.context_json.get(f"{role}MediaHash")
            ):
                raise AppError(
                    "SMART_REMAKE_INPUT_CHANGED", "Create an intake for new inputs.", 409
                )
        if duration != owned.context_json["p0"].get("targetDuration"):
            raise AppError("SMART_REMAKE_INPUT_CHANGED", "Use the intake target duration.", 409)
        intent_data = {
            "projectId": str(project_id), "actorId": str(actor_id),
            "revision": expected_revision, "duration": duration, "language": language,
            "prompt": prompt, "description": description, "title": product_title,
            "productDescription": product_description, "start": reference_start_frame,
            "cuts": source_cut_frames, "groups": render_group_breaks,
        }
        if full_source:
            intent_data["analysisScope"] = analysis_scope
            intent_data["compilerVersion"] = "smart-remake-timeline-v2.3"
        compile_intent = stable_hash(intent_data)
    if owned is not None and (reference is None or product is None):
        if not owned.context_json.get("sourceKey"):
            raise AppError(
                "SMART_REMAKE_SOURCE_REUPLOAD_REQUIRED",
                "This older project has no retained source. Upload the original video again.",
            )
        media = RepairMediaStore(S3StorageAdapter(settings))
        if reference is None:
            reference = UploadedMedia(
                bytes=await media.read(owned.context_json["sourceKey"]),
                mime_type=owned.context_json["sourceMimeType"],
            )
        if product is None and not (product_url and product_url.strip()):
            product = UploadedMedia(
                bytes=await media.read(owned.context_json["productKey"]),
                mime_type=owned.context_json["productMimeType"],
            )
    if product is None and product_url and product_url.strip():
        linked = await _read_product_link_image(product_url.strip())
        product = UploadedMedia(bytes=linked.bytes, mime_type=linked.mime_type)
        product_title = product_title or linked.title
        product_description = product_description or linked.description
    if owned is not None and (owned.context_json.get("p0") or {}).get(
        "additionalProductReferences"
    ):
        from .product_references import read_product_references

        retained = await read_product_references(
            owned.context_json, RepairMediaStore(S3StorageAdapter(settings))
        )
        if additional_product_images is not None and [
            hashlib.sha256(value.bytes).hexdigest() for value in additional
        ] != [hashlib.sha256(value.bytes).hexdigest() for value in retained[1:]]:
            raise AppError("SMART_REMAKE_INPUT_CHANGED", "Use the retained product views.", 409)
        additional = retained[1:]
    elif owned is not None and additional:
        raise AppError("SMART_REMAKE_INPUT_CHANGED", "Create an intake for new product views.", 409)
    if reference is None or product is None:
        raise AppError(
            "SMART_REMAKE_MEDIA_REQUIRED", "Reference video and product image are required."
        )
    try:
        from .analysis_progress import checkpoint_analysis

        if compile_intent is not None:
            assert owned is not None and idempotency_key and expected_revision is not None
            owned, compile_operation, fresh_compile = await RepairRepository(session).start(
                workspace_id, owned.id, idempotency_key, compile_intent
            )
            if not fresh_compile:
                if compile_operation.status == "completed":
                    response = copy.deepcopy(compile_operation.result_json["compileResult"])
                    replay_media = RepairMediaStore(S3StorageAdapter(settings))
                    for scene in response.get("sourceSceneMap", {}).get("scenes", []):
                        scene.pop("thumbnailUrl", None)
                        key = owned.context_json.get("sourceThumbnailKeys", {}).get(scene["id"])
                        if key:
                            scene["thumbnailUrl"] = await replay_media.url(key)
                    return cast(dict[str, Any], response)
                raise AppError(
                    "SMART_REMAKE_COMPILE_RECONCILIATION_REQUIRED",
                    "This compile attempt already exists; inspect its status before retrying.", 409,
                )
            await checkpoint_analysis(
                session, compile_operation, "validating_source", request_key=idempotency_key
            )
            _revision(owned.state_json, expected_revision)
            from sqlalchemy import select

            from .budget_models import SmartRemakeAttemptModel
            from .generation_recovery import attempt_needs_reconciliation

            attempts = list(await session.scalars(
                select(SmartRemakeAttemptModel).where(
                    SmartRemakeAttemptModel.project_id == owned.id,
                    SmartRemakeAttemptModel.workspace_id == workspace_id,
                )
            ))
            if any(attempt_needs_reconciliation(attempt) for attempt in attempts):
                raise AppError(
                    "SMART_REMAKE_ATTEMPT_RECONCILIATION_REQUIRED",
                    "A previous model request must be reconciled before starting new analysis.",
                    409,
                )
        assert_reference_video(reference)
        assert_product_image(product)
        analysis_images = [product, *additional]
        if additional:
            from .product_references import validate_product_reference_image

            for image in [product, *additional]:
                validate_product_reference_image(image)
            hashes = [hashlib.sha256(image.bytes).hexdigest() for image in [product, *additional]]
            if len(hashes) != len(set(hashes)):
                raise AppError(
                    "SMART_REMAKE_PRODUCT_REFERENCES_INVALID", "Choose distinct product views.", 422
                )
            analysis_images = prepare_product_analysis_images(analysis_images)
        info = await run_in_threadpool(probe_media_bytes, reference.bytes)
        if not info.get("hasVideo") or not info.get("durationSeconds"):
            raise AppError("SMART_REMAKE_SOURCE_INVALID", "The source video could not be measured.")
        frame_count = await run_in_threadpool(measure_video_frames, reference.bytes)
        info = {**info, "videoDurationSeconds": frame_count / 24}
        await checkpoint_analysis(
            session, compile_operation, "analyzing_source", request_key=idempotency_key,
            source_duration=frame_count / 24,
        )
        total = frame_count if full_source else validate_source_excerpt(
            target_duration=duration, source_frame_count=frame_count,
            reference_start_frame=reference_start_frame,
        )
        timing_options = {"timing_mode": "fit_target"} if full_source else {}
        if source_cut_frames is not None:
            build_timeline_plan(
                target_duration=duration,
                source_frame_count=frame_count,
                reference_start_frame=reference_start_frame,
                cut_frames=source_cut_frames,
                render_group_breaks=render_group_breaks,
                image_quality=get_openai_image_quality(),
                **timing_options,
            )
        excerpt = reference if full_source else await run_in_threadpool(
            extract_source_excerpt, reference, start_frame=reference_start_frame, total_frames=total
        )
        if await run_in_threadpool(measure_video_frames, excerpt.bytes) != total:
            raise AppError(
                "SMART_REMAKE_SOURCE_RANGE_INVALID",
                "The source excerpt does not contain the required video frames.",
            )
        gemini: SmartRemakeGeminiClient = (
            FixtureGeminiClient()
            if settings.ai_mode.strip().lower() in {"fixture", "mock"}
            else HttpGeminiClient()
        )
        if compile_operation is not None and settings.ai_mode.strip().lower() not in {
            "fixture", "mock"
        }:
            assert owned is not None
            from .budgeted_analysis import LedgerGeminiClient

            gemini = LedgerGeminiClient(
                session, workspace_id, owned.id, compile_operation.id, actor_id,
                client=HttpGeminiClient(
                    max_attempts=1, repair_json=False,
                    thinking_budget=1024 if get_gemini_model() == "gemini-2.5-flash" else None,
                ),
            )
        if compile_operation is not None:
            assert owned is not None
            requirements_text = json.dumps(
                owned.context_json["p0"]["requirements"], ensure_ascii=False, sort_keys=True
            )
            description = f"{description or ''}\nSAVED SELLER REQUIREMENTS: {requirements_text}"
        if full_source and compile_operation is not None:
            assert owned is not None
            from .loading_summary import start_loading_summary

            summary_task = start_loading_summary(
                session, workspace_id=workspace_id, project_id=owned.id,
                operation_id=compile_operation.id, actor_id=actor_id, source=excerpt,
                duration=frame_count / 24, mode=settings.ai_mode.strip().lower(),
            )
        analysis = await analyze_reference_video(
            target_duration=total / 24 if full_source else duration,
            prompt=prompt,
            description=description,
            reference_video=excerpt,
            gemini=gemini,
        )
        source_checkpoint = (
            {
                "phase": "source_analyzed",
                "sourceAnalysisCheckpoint": {
                    "analysisScope": analysis_scope,
                    "sourceMediaHash": hashlib.sha256(reference.bytes).hexdigest(),
                    "sourceFrameCount": frame_count,
                    "analysis": copy.deepcopy(analysis),
                },
            }
            if full_source and compile_operation is not None else None
        )
        await checkpoint_analysis(
            session, compile_operation, "resolving_scenes", request_key=idempotency_key,
            source_duration=frame_count / 24, analysis=analysis if full_source else None,
            result_updates=source_checkpoint,
        )
        if full_source:
            from .source_timing import source_frame_clock_analysis

            try:
                validate_source_analysis(analysis, target_duration=total / 24)
                analysis = source_frame_clock_analysis(analysis, source_frame_count=total)
            except AppError as exc:
                if exc.code != "SMART_REMAKE_SOURCE_ANALYSIS_INCOMPLETE":
                    raise
                # Keep raw evidence in the checkpoint. Invalid model timing
                # cannot seed cuts; the measured intervals need fresh semantics.
                analysis = {**analysis, "sourceShots": [], "motionBeats": []}
        analysis = await run_in_threadpool(
            enrich_reference_analysis_with_detected_cuts, analysis, excerpt
        )
        if full_source:
            analysis = source_frame_clock_analysis(analysis, source_frame_count=total)
        plan = None
        requested_semantic_cuts = source_cut_frames
        if full_source:
            detection = analysis.get("sourceCutDetection") or {}
            logical_cuts = source_cut_frames or (
                detection.get("cutFrames") if detection.get("requiresSemanticReanalysis")
                else source_boundaries(analysis, total_frames=total)
            )
            if not isinstance(logical_cuts, list):
                raise AppError(
                    "SMART_REMAKE_SOURCE_ANALYSIS_INCOMPLETE",
                    "Source cut analysis has no measured interval boundaries.", 409,
                )
            plan = build_timeline_plan(
                target_duration=duration, source_frame_count=frame_count,
                reference_start_frame=0, cut_frames=logical_cuts,
                render_group_breaks=render_group_breaks,
                image_quality=get_openai_image_quality(), timing_mode="fit_target",
            )
            requested_semantic_cuts = sorted({
                value for unit in plan["renderPlan"]["units"]
                for value in (unit["sourceStartFrame"], unit["sourceEndFrame"])
            })
        await checkpoint_analysis(
            session, compile_operation, "resolving_scenes", request_key=idempotency_key,
            source_duration=frame_count / 24, analysis=analysis if full_source else None,
            source_scenes=(plan or {}).get("sourceSceneMap", {}).get("scenes"),
        )
        analysis = await resolve_source_cut_semantics(
            analysis=analysis,
            target_duration=total / 24 if full_source else duration, prompt=prompt,
            description=description, reference_video=excerpt, gemini=gemini,
            requested_cut_frames=requested_semantic_cuts,
        )
        plan = plan or build_timeline_plan(
            target_duration=duration,
            source_frame_count=frame_count,
            reference_start_frame=reference_start_frame,
            cut_frames=source_cut_frames
            if source_cut_frames is not None
            else source_boundaries(analysis, total_frames=total),
            render_group_breaks=render_group_breaks,
            image_quality=get_openai_image_quality(),
        )
        if full_source:
            from .source_timing import assert_observed_fragment_boundaries

            validate_source_analysis(analysis, target_duration=frame_count / 24)
            assert_observed_fragment_boundaries(analysis, plan["renderPlan"]["units"])
        await checkpoint_analysis(
            session, compile_operation, "identifying_product", request_key=idempotency_key,
            source_duration=frame_count / 24, analysis=analysis if full_source else None,
            source_scenes=plan["sourceSceneMap"]["scenes"],
        )
        lock = await generate_product_lock(
            product_image=analysis_images[0],
            **({"additional_product_images": analysis_images[1:]} if additional else {}),
            metadata=ProductMetadata(title=product_title, description=product_description),
            prompt=prompt,
            description=description,
            product_lock=None,
            visual_identity=None,
            product_reference=None,
            gemini=gemini,
        )
        await checkpoint_analysis(
            session, compile_operation, "building_storyboard", request_key=idempotency_key,
            product=lock,
        )
        result = build_timeline_compile(
            analysis=analysis,
            product_lock=lock,
            plan=plan,
            language=language,
            mode=mode if mode in {"smart_remake", "montage"} else "smart_remake",
        )
        if full_source:
            result["inputSummary"].update({
                "analysisScope": "full_source", "sourceDuration": frame_count / 24,
            })
        result["serverMode"] = settings.ai_mode.strip().lower()
        result["executionMode"] = (
            "fixture" if settings.ai_mode.strip().lower() in {"fixture", "mock"}
            else "unverified"
        )
        if compile_operation is not None:
            assert owned is not None
            result["renderPlan"]["referencePolicy"] = (
                "product-character-first-layout" if owned.context_json.get("characterKey")
                else "product-first-last-layout"
            )
        thumbnails = await run_in_threadpool(
            extract_timeline_thumbnails,
            reference if full_source else excerpt,
            [
                (
                    scene["startFrame"] + scene["endFrame"]
                    - (0 if full_source else 2 * reference_start_frame)
                ) / 48
                for scene in result["sourceSceneMap"]["scenes"]
            ],
        )
        media = RepairMediaStore(S3StorageAdapter(settings))
        if compile_operation is not None:
            assert owned is not None and expected_revision is not None
            owned = await RepairRepository(session).project(workspace_id, owned.id)
            assert_project_policy(owned, purpose="analysis")
            _revision(owned.state_json, expected_revision)
            await session.commit()
        row = await initialize_timeline_project(
            repository=RepairRepository(session),
            media=media,
            workspace_id=workspace_id,
            compile_result=result,
            source=reference,
            product=product,
            **({"additional_products": additional} if additional else {}),
            source_probe=info,
            thumbnails=thumbnails,
            image_assets=(
                owned.context_json.get("imageAssets")
                if owned is not None
                and owned.context_json.get("sourceMediaHash")
                == hashlib.sha256(reference.bytes).hexdigest()
                and owned.context_json.get("productMediaHash")
                == hashlib.sha256(product.bytes).hexdigest()
                else None
            ),
            existing_project=owned if compile_operation is not None else None,
            expected_revision=expected_revision,
            compile_operation_id=compile_operation.id if compile_operation is not None else None,
        )
        if full_source:
            result = copy.deepcopy(row.context_json.get("compileResult", result))
        response = {
            **result,
            "expectationsVersion": 1,
            "expectationsHash": row.context_json["expectationsHash"],
            "projectId": str(row.id),
            "revision": row.revision,
            "sourceSceneMap": copy.deepcopy(result["sourceSceneMap"]),
        }
        if compile_operation is not None:
            await checkpoint_analysis(
                session, compile_operation, "completed", request_key=idempotency_key,
                result_updates={"compileResult": response, "actorId": str(actor_id)},
            )
            compile_completed = True
            await RepairRepository(session).finish(
                compile_operation, "completed", copy.deepcopy(compile_operation.result_json)
            )
        response = copy.deepcopy(response)
        for scene in response["sourceSceneMap"]["scenes"]:
            key = row.context_json["sourceThumbnailKeys"].get(scene["id"])
            if key:
                scene["thumbnailUrl"] = await media.url(key)
        return cast(dict[str, Any], response)
    except Exception as exc:
        if compile_operation is not None and fresh_compile and not compile_completed:
            await checkpoint_analysis(
                session, compile_operation, "failed", request_key=idempotency_key,
                error_code=getattr(exc, "code", "SMART_REMAKE_COMPILE_FAILED"),
                result_updates={"actorId": str(actor_id),
                                "errorCode": getattr(exc, "code", "SMART_REMAKE_COMPILE_FAILED")},
            )
            await RepairRepository(session).finish(
                compile_operation, "failed", {
                    **(compile_operation.result_json or {}),
                    "kind": "compile", "actorId": str(actor_id),
                    "errorCode": getattr(exc, "code", "SMART_REMAKE_COMPILE_FAILED"),
                }
            )
        if isinstance(exc, SmartRemakeError):
            raise _error(exc) from exc
        if isinstance(exc, OSError | ValueError | subprocess.SubprocessError):
            raise AppError(
                "SMART_REMAKE_SOURCE_INVALID",
                "The source video could not be decoded. Choose another video.",
            ) from exc
        raise
    finally:
        from .loading_summary import finish_loading_summary

        await finish_loading_summary(summary_task)
