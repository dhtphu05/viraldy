import json
import os
import uuid
import zlib
from typing import Any, Callable

from .asset_cleanup import cleanup_render_assets, cleanup_smart_remake_assets, cleanup_stale_smart_remake_outputs
from .audio_assets import mux_reference_music
from .concat import concat_flowkit_video, concat_video_urls
from .config import (
    get_unifically_poll_interval_seconds,
    get_unifically_poll_timeout_seconds,
    get_unifically_seed,
    get_unifically_video_model,
)
from .errors import SmartRemakeError, SmartRemakeValidationError
from .flowkit_adapter import (
    SmartRemakeFlowKit,
    build_image_requests,
    build_video_requests,
    prepare_flowkit_job,
)
from .flowkit_client import FlowKitClient
from .guards import assert_allowed_request_type, assert_no_reference_video_in_render_payload
from .media_probe import probe_media_bytes
from .media_validation import assert_product_image
from .polling import wait_for_batch
from .schemas import RenderSmartRemakeInput
from .storage import save_smart_remake_output
from .unifically_adapter import (
    build_unifically_video_input,
    extract_task_output_url,
)
from .unifically_client import UnificallyClient
from .unifically_polling import wait_for_unifically_task


def _expected_scene_count(target_duration: int) -> int:
    return target_duration // 8


def _assert_render_input(input_data: RenderSmartRemakeInput) -> None:
    if not input_data.projectName.strip():
        raise SmartRemakeValidationError(
            "Smart Remake render projectName is required.",
            "INVALID_FLOWKIT_SCENE_PAYLOAD",
        )
    assert_product_image(input_data.productImage)
    scene_map = input_data.sceneMap
    target_duration = scene_map.get("targetDuration")
    if target_duration not in (8, 16, 24, 32):
        raise SmartRemakeValidationError("sceneMap targetDuration must be 8, 16, 24, or 32.", "INVALID_FLOWKIT_SCENE_PAYLOAD")
    scenes = scene_map.get("scenes")
    expected = _expected_scene_count(target_duration)
    if not isinstance(scenes, list) or scene_map.get("sceneCount") != expected or len(scenes) != expected:
        raise SmartRemakeValidationError(
            "Smart Remake sceneMap scene count does not match target duration.",
            "INVALID_FLOWKIT_SCENE_PAYLOAD",
        )
    product_character = input_data.productLock.get("productReference", {}).get("characterName")
    if not product_character:
        raise SmartRemakeValidationError("Product character name is required.", "INVALID_PRODUCT_LOCK")
    for scene in scenes:
        if scene.get("chainType") != "ROOT" or scene.get("parentSceneId") is not None:
            raise SmartRemakeValidationError(
                "Smart Remake render supports ROOT scenes only.",
                "INVALID_FLOWKIT_SCENE_PAYLOAD",
            )
        for key in ("prompt", "imagePrompt", "videoPrompt"):
            if not isinstance(scene.get(key), str) or not scene[key].strip():
                raise SmartRemakeValidationError(
                    f"Smart Remake scene {key} is required.",
                    "INVALID_FLOWKIT_SCENE_PAYLOAD",
                )
        if product_character not in scene.get("characterNames", []):
            raise SmartRemakeValidationError(
                "Smart Remake scene must include product character.",
                "INVALID_FLOWKIT_SCENE_PAYLOAD",
            )
    assert_no_reference_video_in_render_payload(scene_map)


def _request_ids(batch: list[dict[str, Any]]) -> list[str]:
    return [item["id"] for item in batch]


def _text_overlays(scenes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    enabled = os.getenv("SMART_REMAKE_RENDER_TEXT_OVERLAYS", "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    if not enabled:
        return []

    overlays = []
    for scene in scenes:
        text = scene.get("textOverlay")
        if isinstance(text, str) and text.strip():
            overlays.append({"displayOrder": scene["displayOrder"], "text": text.strip()})
    return overlays


def _has_video_output(statuses: dict[str, dict[str, Any]]) -> bool:
    return all(
        bool(status.get("output_url"))
        for status in statuses.values()
    )


def _stable_unifically_seed(input_data: RenderSmartRemakeInput) -> int:
    configured = get_unifically_seed()
    if configured is not None:
        return configured
    product_lock = json.dumps(input_data.productLock, sort_keys=True, ensure_ascii=True).encode("utf-8")
    return zlib.crc32(input_data.productImage.bytes + product_lock) & 0x7FFFFFFF


def _should_retry_unifically_video(error: SmartRemakeError) -> bool:
    if error.code not in {"UNIFICALLY_TASK_FAILED", "UNIFICALLY_TASK_CREATE_FAILED", "UNIFICALLY_VALIDATION_FAILED"}:
        return False
    message = str(error).lower()
    return (
        "couldn't be submitted" in message
        or "could not be submitted" in message
        or "try again" in message
        or "flow minter http 502" in message
        or "http 502" in message
        or "bad gateway" in message
        or "upstream" in message
        or error.code in {"UNIFICALLY_TASK_CREATE_FAILED", "UNIFICALLY_VALIDATION_FAILED"}
    )


async def render_smart_remake(
    input_data: RenderSmartRemakeInput,
    *,
    flowkit: SmartRemakeFlowKit | None = None,
    unifically: Any | None = None,
    concat: Callable[..., Any] | None = None,
    concat_urls: Callable[..., Any] | None = None,
    probe: Callable[[bytes], dict[str, Any]] | None = None,
    polling_interval_seconds: float = 2.0,
    polling_timeout_seconds: float = 900.0,
) -> dict[str, Any]:
    _assert_render_input(input_data)
    cleanup_smart_remake_assets()
    cleanup_stale_smart_remake_outputs()
    try:
        if input_data.provider == "unifically":
            return await _render_with_unifically(
                input_data,
                unifically=unifically,
                concat_urls=concat_urls,
                probe=probe,
            )
        return await _render_with_flowkit(
            input_data,
            flowkit=flowkit,
            concat=concat,
            probe=probe,
            polling_interval_seconds=polling_interval_seconds,
            polling_timeout_seconds=polling_timeout_seconds,
        )
    finally:
        cleanup_render_assets(
            scene_map=input_data.sceneMap,
            reference_analysis=input_data.referenceAnalysis,
        )


async def _render_with_flowkit(
    input_data: RenderSmartRemakeInput,
    *,
    flowkit: SmartRemakeFlowKit | None = None,
    concat: Callable[..., Any] | None = None,
    probe: Callable[[bytes], dict[str, Any]] | None = None,
    polling_interval_seconds: float = 2.0,
    polling_timeout_seconds: float = 900.0,
) -> dict[str, Any]:
    flowkit = flowkit or FlowKitClient()
    concat = concat or concat_flowkit_video
    probe = probe or probe_media_bytes
    warnings = list(input_data.warnings)
    audio_plan = input_data.referenceAnalysis.get("audioPlan") if input_data.referenceAnalysis else None

    prepared = await prepare_flowkit_job(
        flowkit=flowkit,
        project_name=input_data.projectName,
        product_lock=input_data.productLock,
        scene_map=input_data.sceneMap,
        audio_plan=audio_plan,
        product_image=input_data.productImage,
    )

    image_requests = build_image_requests(prepared)
    for request in image_requests:
        assert_allowed_request_type(request["type"])
    assert_no_reference_video_in_render_payload(image_requests)
    image_batch = await flowkit.create_batch_requests(image_requests)
    image_request_ids = _request_ids(image_batch)
    await wait_for_batch(
        image_request_ids,
        flowkit.get_request_status,
        failure_code="FLOWKIT_IMAGE_GENERATION_FAILED",
        interval_seconds=polling_interval_seconds,
        timeout_seconds=polling_timeout_seconds,
    )

    video_requests = build_video_requests(prepared)
    for request in video_requests:
        if request["type"] != "GENERATE_VIDEO":
            raise SmartRemakeValidationError(
                "Smart Remake initial render must use GENERATE_VIDEO only.",
                "INVALID_FLOWKIT_SCENE_PAYLOAD",
            )
        assert_allowed_request_type(request["type"])
    assert_no_reference_video_in_render_payload(video_requests)
    video_batch = await flowkit.create_batch_requests(video_requests)
    video_request_ids = _request_ids(video_batch)
    video_statuses = await wait_for_batch(
        video_request_ids,
        flowkit.get_request_status,
        failure_code="FLOWKIT_VIDEO_GENERATION_FAILED",
        interval_seconds=polling_interval_seconds,
        timeout_seconds=polling_timeout_seconds,
    )

    if not _has_video_output(video_statuses):
        return {
            "success": True,
            "mode": "smart_remake",
            "provider": "flowkit",
            "projectId": prepared["projectId"],
            "videoId": prepared["videoId"],
            "sceneIds": [scene["flowKitSceneId"] for scene in prepared["scenes"]],
            "imageRequestIds": image_request_ids,
            "videoRequestIds": video_request_ids,
            "finalVideoUrl": "",
            "targetDuration": input_data.sceneMap["targetDuration"],
            "sceneCount": input_data.sceneMap["sceneCount"],
            "renderSubmitted": True,
            "status": "submitted",
            "warnings": warnings,
        }

    output_bytes = await concat(
        flowkit=flowkit,
        video_id=prepared["videoId"],
        orientation="VERTICAL",
        title=input_data.projectName,
        text_overlays=_text_overlays(input_data.sceneMap["scenes"]),
    )
    final_url = _finalize_and_save_output(
        output_bytes,
        project_id=prepared["projectId"],
        video_id=prepared["videoId"],
        audio_plan=audio_plan,
        audio_required=input_data.audioRequired,
        warnings=warnings,
        probe=probe,
    )
    return {
        "success": True,
        "mode": "smart_remake",
        "provider": "flowkit",
        "projectId": prepared["projectId"],
        "videoId": prepared["videoId"],
        "sceneIds": [scene["flowKitSceneId"] for scene in prepared["scenes"]],
        "imageRequestIds": image_request_ids,
        "videoRequestIds": video_request_ids,
        "finalVideoUrl": final_url,
        "targetDuration": input_data.sceneMap["targetDuration"],
        "sceneCount": input_data.sceneMap["sceneCount"],
        "renderSubmitted": True,
        "status": "completed",
        "warnings": warnings,
    }


async def _render_with_unifically(
    input_data: RenderSmartRemakeInput,
    *,
    unifically: Any | None = None,
    concat_urls: Callable[..., Any] | None = None,
    probe: Callable[[bytes], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    client = unifically or UnificallyClient()
    concat_urls = concat_urls or concat_video_urls
    probe = probe or probe_media_bytes
    warnings = list(input_data.warnings)
    audio_plan = input_data.referenceAnalysis.get("audioPlan") if input_data.referenceAnalysis else None
    scenes = sorted(input_data.sceneMap["scenes"], key=lambda scene: int(scene.get("displayOrder", 0)))
    project_id = f"unifically_{uuid.uuid4().hex[:12]}"
    scene_ids = [f"unifically-scene-{scene.get('displayOrder', index)}" for index, scene in enumerate(scenes)]

    product_image_url = await client.upload_file(input_data.productImage)
    image_request_ids: list[str] = []
    video_request_ids: list[str] = []
    video_urls: list[str] = []
    video_seed = _stable_unifically_seed(input_data)

    for scene in scenes:
        # Keep the Veo reference set unambiguous: only the raw product upload
        # is a visual ingredient. The source video contributes its DNA through
        # the compiled shot plan, not through a competing product image.
        video_input = build_unifically_video_input(
            scene=scene,
            product_image_url=product_image_url,
            product_lock=input_data.productLock,
            reference_analysis=input_data.referenceAnalysis,
            object_reference_mode=True,
            seed=video_seed,
        )
        try:
            video_task = await client.create_task(model=get_unifically_video_model(), input_data=video_input)
            video_task_id = video_task["task_id"]
            video_request_ids.append(video_task_id)
            video_status = await wait_for_unifically_task(
                video_task_id,
                client.get_task,
                interval_seconds=get_unifically_poll_interval_seconds(),
                timeout_seconds=get_unifically_poll_timeout_seconds(),
            )
        except SmartRemakeError as exc:
            if not _should_retry_unifically_video(exc):
                raise
            warnings.append(f"Unifically video retry submitted after provider rejected the first payload: {exc}")
            fallback_video_input = build_unifically_video_input(
                scene=scene,
                product_image_url=product_image_url,
                product_lock=input_data.productLock,
                reference_analysis=input_data.referenceAnalysis,
                object_reference_mode=True,
                seed=None,
            )
            video_task = await client.create_task(model=get_unifically_video_model(), input_data=fallback_video_input)
            video_task_id = video_task["task_id"]
            video_request_ids.append(video_task_id)
            video_status = await wait_for_unifically_task(
                video_task_id,
                client.get_task,
                interval_seconds=get_unifically_poll_interval_seconds(),
                timeout_seconds=get_unifically_poll_timeout_seconds(),
            )
        video_url = extract_task_output_url(video_status, "video_url")
        if not video_url:
            raise SmartRemakeError(
                "Unifically video task completed without video_url.",
                "UNIFICALLY_INVALID_RESPONSE",
                {"taskId": video_task_id, "status": video_status},
            )
        video_urls.append(video_url)

    if len(video_urls) == 1:
        output_bytes = await client.download_file(video_urls[0])
    else:
        output_bytes = await concat_urls(
            video_urls=video_urls,
            orientation="VERTICAL",
            title=input_data.projectName,
            text_overlays=_text_overlays(scenes),
        )

    video_id = video_request_ids[0] if len(video_request_ids) == 1 else f"concat_{uuid.uuid4().hex[:12]}"
    final_url = _finalize_and_save_output(
        output_bytes,
        project_id=project_id,
        video_id=video_id,
        audio_plan=audio_plan,
        audio_required=input_data.audioRequired,
        warnings=warnings,
        probe=probe,
    )

    return {
        "success": True,
        "mode": "smart_remake",
        "provider": "unifically",
        "projectId": project_id,
        "videoId": video_id,
        "sceneIds": scene_ids,
        "imageRequestIds": image_request_ids,
        "videoRequestIds": video_request_ids,
        "finalVideoUrl": final_url,
        "targetDuration": input_data.sceneMap["targetDuration"],
        "sceneCount": input_data.sceneMap["sceneCount"],
        "renderSubmitted": True,
        "status": "completed",
        "warnings": warnings,
    }


def _finalize_and_save_output(
    output_bytes: bytes,
    *,
    project_id: str,
    video_id: str,
    audio_plan: dict[str, Any] | None,
    audio_required: bool,
    warnings: list[str],
    probe: Callable[[bytes], dict[str, Any]],
) -> str:
    media_probe = probe(output_bytes)
    if not media_probe.get("hasVideo"):
        raise SmartRemakeError("Smart Remake output is missing a video stream.", "SMART_REMAKE_CONCAT_FAILED", {"probe": media_probe})
    has_usable_audio = bool(media_probe.get("hasAudio")) and (media_probe.get("audioDurationSeconds") or 0) > 0.1
    if not has_usable_audio:
        if audio_required:
            raise SmartRemakeError("Native audio was not generated.", "NATIVE_AUDIO_MISSING", {"probe": media_probe})
        if "Native audio was not generated." not in warnings:
            warnings.append("Native audio was not generated.")

    reference_music = audio_plan.get("referenceMusic") if isinstance(audio_plan, dict) and isinstance(audio_plan.get("referenceMusic"), dict) else None
    if reference_music and reference_music.get("mode") == "extract" and reference_music.get("assetId"):
        try:
            output_bytes = mux_reference_music(output_bytes, reference_music["assetId"], bool(media_probe.get("hasAudio")))
            media_probe = probe(output_bytes)
        except Exception as exc:
            warnings.append(f"Reference music mux skipped: {exc}")
            if audio_required:
                raise SmartRemakeError(
                    "Required reference music could not be muxed.",
                    "NATIVE_AUDIO_MISSING",
                    {"cause": str(exc)},
                ) from exc

    _, final_url = save_smart_remake_output(project_id, video_id, output_bytes)
    return final_url
