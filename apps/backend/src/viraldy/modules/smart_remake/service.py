from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import UploadFile
from pydantic import ValidationError

from viraldy.modules.product_import.service import ProductLinkImage, fetch_product_link_image
from viraldy.platform.config.settings import Settings
from viraldy.shared.errors.base import AppError

from .engine import compile_smart_remake, render_smart_remake
from .engine.config import (
    get_flowkit_url,
    get_kie_api_key,
    get_kie_video_model,
    get_kie_video_resolution,
    get_max_product_image_bytes,
    get_max_reference_video_bytes,
    get_unifically_api_key,
    is_smart_remake_enabled,
)
from .engine.errors import SmartRemakeError
from .engine.guards import assert_no_reference_video_in_render_payload
from .engine.prompt_edits import scene_edit_directions
from .engine.prompt_sanitizer import validate_sanitized_compiler_prompts
from .engine.render_orchestrator import _assert_render_input
from .engine.schemas import (
    CompileSmartRemakeRequest,
    ProductMetadata,
    RenderSmartRemakeInput,
    UploadedMedia,
)
from .fixture import FixtureGeminiClient


def feature_enabled(settings: Settings) -> bool:
    return is_smart_remake_enabled() or settings.ai_mode.strip().lower() in {"fixture", "mock"}


def health_payload(settings: Settings) -> dict[str, Any]:
    fixture = settings.ai_mode.strip().lower() in {"fixture", "mock"}
    video_model = get_kie_video_model()
    return {
        "enabled": feature_enabled(settings),
        "mode": "fixture" if fixture else "live",
        "providers": ["fixture"] if fixture else ["kie", "unifically", "flowkit"],
        "kieConfigured": bool(get_kie_api_key()),
        "kieVideoModel": video_model,
        "kieVideoResolution": get_kie_video_resolution(video_model),
        "openaiImagesConfigured": bool(getattr(settings, "openai_api_key", None)),
        "openaiImageModel": "gpt-image-2.6-sunburst",
        "flowkitUrlSet": bool(get_flowkit_url()),
        "unificallyConfigured": bool(get_unifically_api_key()),
        "limits": {
            "referenceVideoBytes": get_max_reference_video_bytes(),
            "productImageBytes": get_max_product_image_bytes(),
        },
    }


def require_kie_renderer(settings: Settings) -> None:
    if settings.ai_mode.strip().lower() in {"fixture", "mock"}:
        raise AppError(
            "SMART_REMAKE_FIXTURE_MODE", "Live rendering is disabled in fixture mode.", 409
        )
    if not get_kie_api_key():
        raise AppError("KIE_NOT_CONFIGURED", "KIE video service is not configured.", 503)


def require_openai_images(settings: Settings) -> None:
    if settings.ai_mode.strip().lower() in {"fixture", "mock"}:
        raise AppError(
            "SMART_REMAKE_FIXTURE_MODE", "Live rendering is disabled in fixture mode.", 409
        )
    if not getattr(settings, "openai_api_key", None):
        raise AppError(
            "OPENAI_IMAGES_NOT_CONFIGURED", "OpenAI image service is not configured.", 503
        )


async def read_media(upload: UploadFile | None, default_mime: str) -> UploadedMedia | None:
    if upload is None:
        return None
    return UploadedMedia(
        bytes=await upload.read(),
        mime_type=upload.content_type or default_mime,
        file_name=upload.filename,
    )


def _error(exc: SmartRemakeError) -> AppError:
    details = (
        exc.details
        if isinstance(exc.details, dict)
        else {"details": exc.details}
        if exc.details
        else {}
    )
    return AppError(code=exc.code, message=str(exc), status_code=400, details=details)


def _duration(value: str) -> int:
    try:
        duration = int(value)
    except ValueError as exc:
        raise AppError(
            "INVALID_SMART_REMAKE_DURATION", "Duration must be 8, 12 or 16 seconds."
        ) from exc
    if duration not in {8, 12, 16}:
        raise AppError("INVALID_SMART_REMAKE_DURATION", "Duration must be 8, 12 or 16 seconds.")
    return duration


async def compile_request(
    *,
    settings: Settings,
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
) -> dict[str, Any]:
    if not feature_enabled(settings):
        raise AppError("SMART_REMAKE_DISABLED", "Smart Remake is disabled.", 503)
    if aspect_ratio != "9:16":
        raise AppError("INVALID_SMART_REMAKE_ASPECT_RATIO", "Smart Remake supports 9:16 only.")
    if _duration(target_duration) == 12:
        raise AppError(
            "SMART_REMAKE_VIDEO_DURATION_INVALID",
            "Twelve-second output requires an owned Wan timeline intake.", 422,
        )
    reference = await read_media(reference_video, "video/mp4")
    product = await read_media(product_image, "image/png")
    resolved_product_url = product_url.strip() if product_url else None
    resolved_product_title = product_title
    resolved_product_description = product_description
    if product is None and resolved_product_url:
        linked_product = await _read_product_link_image(resolved_product_url)
        product = UploadedMedia(
            bytes=linked_product.bytes,
            mime_type=linked_product.mime_type,
            file_name=linked_product.file_name,
        )
        resolved_product_url = linked_product.source_url
        resolved_product_title = resolved_product_title or linked_product.title
        resolved_product_description = resolved_product_description or linked_product.description
    if reference is None or product is None:
        raise AppError(
            "SMART_REMAKE_MEDIA_REQUIRED", "Reference video and product image are required."
        )
    request = CompileSmartRemakeRequest(
        mode="smart_remake" if mode not in {"smart_remake", "montage"} else mode,
        targetDuration=_duration(target_duration),
        aspectRatio="9:16",
        language=language,
        prompt=prompt,
        description=description,
        productUrl=resolved_product_url,
        referenceVideo=reference,
        productImage=product,
        productMetadata=ProductMetadata(
            title=resolved_product_title,
            description=resolved_product_description,
        ),
        productSource="url_and_upload" if resolved_product_url and product_image else "url"
        if resolved_product_url
        else "upload",
    )
    gemini = (
        FixtureGeminiClient() if settings.ai_mode.strip().lower() in {"fixture", "mock"} else None
    )
    try:
        return await compile_smart_remake(request, gemini=gemini)
    except SmartRemakeError as exc:
        raise _error(exc) from exc


async def _read_product_link_image(product_url: str) -> ProductLinkImage:
    from starlette.concurrency import run_in_threadpool

    return await run_in_threadpool(
        fetch_product_link_image,
        product_url,
        max_bytes=get_max_product_image_bytes(),
    )


async def render_request(
    *,
    settings: Settings,
    compile_result: dict[str, Any],
    product_image: UploadFile | None,
    provider: str,
    project_name: str,
    audio_required: bool,
    product_url: str | None = None,
    prepare_render: Callable[[RenderSmartRemakeInput], Awaitable[Any]] | None = None,
    submit_render: Callable[[RenderSmartRemakeInput], Awaitable[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    if not feature_enabled(settings):
        raise AppError("SMART_REMAKE_DISABLED", "Smart Remake is disabled.", 503)
    if provider not in {"fixture", "flowkit", "unifically", "kie"}:
        raise AppError(
            "INVALID_SMART_REMAKE_PROVIDER",
            "Provider must be fixture, kie, unifically, or flowkit.",
        )
    if provider == "kie":
        require_kie_renderer(settings)
        if submit_render is None:
            raise AppError(
                "KIE_DURABLE_JOB_REQUIRED", "KIE rendering requires a background job.", 503
            )
    product = await read_media(product_image, "image/png")
    if product is None and product_url and product_url.strip():
        linked = await _read_product_link_image(product_url.strip())
        product = UploadedMedia(bytes=linked.bytes, mime_type=linked.mime_type,
                                file_name=linked.file_name)
    if product is None:
        raise AppError("SMART_REMAKE_MEDIA_REQUIRED", "Product image is required for render.")
    try:
        assert_no_reference_video_in_render_payload(compile_result)
        input_data = RenderSmartRemakeInput(
            productLock=compile_result["productLock"],
            sceneMap=compile_result["sceneMap"],
            referenceAnalysis=compile_result.get("referenceAnalysis"),
            versions=compile_result.get("versions"),
            warnings=compile_result.get("warnings", []),
            audioRequired=audio_required,
            productImage=product,
            projectName=project_name.strip() or "Smart Remake",
            provider="unifically" if provider == "fixture" else provider,
        )
        _assert_render_input(input_data)
        if provider == "kie":
            _duration(str(input_data.sceneMap["targetDuration"]))
            if input_data.sceneMap.get("aspectRatio", "9:16") != "9:16":
                raise AppError(
                    "INVALID_SMART_REMAKE_ASPECT_RATIO", "Smart Remake supports 9:16 only."
                )
        for scene in input_data.sceneMap["scenes"]:
            if scene.get("promptEdited"):
                if provider in {"unifically", "kie"}:
                    scene_edit_directions(scene)
                validate_sanitized_compiler_prompts(
                    prompt=scene["prompt"], image_prompt=scene["imagePrompt"],
                    video_prompt=scene["videoPrompt"], analysis=input_data.referenceAnalysis or {},
                    product_lock=input_data.productLock, timeline=scene.get("shotPlan") or {},
                )
        if provider == "fixture":
            return {
                "success": True,
                "mode": "smart_remake",
                "provider": "fixture",
                "projectId": "fixture-project",
                "videoId": "fixture-video",
                "sceneIds": [
                    f"fixture-scene-{index + 1}"
                    for index in range(input_data.sceneMap["sceneCount"])
                ],
                "imageRequestIds": [],
                "videoRequestIds": [],
                "finalVideoUrl": "",
                "targetDuration": input_data.sceneMap["targetDuration"],
                "sceneCount": input_data.sceneMap["sceneCount"],
                "renderSubmitted": True,
                "status": "submitted",
                "warnings": [
                    "Fixture mode validated the render payload but did not call a video provider."
                ],
            }
        if provider == "kie" and submit_render:
            return await submit_render(input_data)
        if prepare_render:
            handler = await prepare_render(input_data)
            return await render_smart_remake(input_data, on_scene_output=handler)
        return await render_smart_remake(input_data)
    except (SmartRemakeError, KeyError, ValidationError) as exc:
        if isinstance(exc, SmartRemakeError):
            raise _error(exc) from exc
        raise AppError(
            "INVALID_SMART_REMAKE_COMPILE_RESULT", "Compile result is invalid for render."
        ) from exc
