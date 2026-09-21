from __future__ import annotations

from typing import Any

from fastapi import UploadFile
from pydantic import ValidationError

from viraldy.platform.config.settings import Settings
from viraldy.shared.errors.base import AppError

from .engine import compile_smart_remake, render_smart_remake
from .engine.config import (
    get_flowkit_url,
    get_max_product_image_bytes,
    get_max_reference_video_bytes,
    get_unifically_api_key,
    is_smart_remake_enabled,
)
from .engine.errors import SmartRemakeError
from .engine.guards import assert_no_reference_video_in_render_payload
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
    return {
        "enabled": feature_enabled(settings),
        "mode": "fixture" if fixture else "live",
        "providers": ["fixture"] if fixture else ["unifically", "flowkit"],
        "flowkitUrlSet": bool(get_flowkit_url()),
        "unificallyConfigured": bool(get_unifically_api_key()),
        "limits": {
            "referenceVideoBytes": get_max_reference_video_bytes(),
            "productImageBytes": get_max_product_image_bytes(),
        },
    }


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
            "INVALID_SMART_REMAKE_DURATION", "Duration must be 8 or 16 seconds."
        ) from exc
    if duration not in {8, 16}:
        raise AppError("INVALID_SMART_REMAKE_DURATION", "Duration must be 8 or 16 seconds.")
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
    reference = await read_media(reference_video, "video/mp4")
    product = await read_media(product_image, "image/png")
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
        productUrl=product_url,
        referenceVideo=reference,
        productImage=product,
        productMetadata=ProductMetadata(title=product_title, description=product_description),
        productSource="url_and_upload" if product_url else "upload",
    )
    gemini = (
        FixtureGeminiClient() if settings.ai_mode.strip().lower() in {"fixture", "mock"} else None
    )
    try:
        return await compile_smart_remake(request, gemini=gemini)
    except SmartRemakeError as exc:
        raise _error(exc) from exc


async def render_request(
    *,
    settings: Settings,
    compile_result: dict[str, Any],
    product_image: UploadFile,
    provider: str,
    project_name: str,
    audio_required: bool,
) -> dict[str, Any]:
    if not feature_enabled(settings):
        raise AppError("SMART_REMAKE_DISABLED", "Smart Remake is disabled.", 503)
    if provider not in {"fixture", "flowkit", "unifically"}:
        raise AppError(
            "INVALID_SMART_REMAKE_PROVIDER", "Provider must be fixture, unifically, or flowkit."
        )
    product = await read_media(product_image, "image/png")
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
        return await render_smart_remake(input_data)
    except (SmartRemakeError, KeyError, ValidationError) as exc:
        if isinstance(exc, SmartRemakeError):
            raise _error(exc) from exc
        raise AppError(
            "INVALID_SMART_REMAKE_COMPILE_RESULT", "Compile result is invalid for render."
        ) from exc
