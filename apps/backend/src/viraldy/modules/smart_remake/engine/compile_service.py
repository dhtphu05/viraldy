from typing import Any

from .analyze_normalizer import has_analyze_source, normalize_analyze_input, normalize_analyze_output
from .asset_cleanup import cleanup_smart_remake_assets
from .audio_assets import extract_reference_music
from .compiler import compile_smart_remake_scene_map_with_diagnostics
from .errors import SmartRemakeValidationError
from .gemini_client import HttpGeminiClient, SmartRemakeGeminiClient
from .guards import assert_allowed_endpoint, assert_allowed_request_type, assert_no_reference_video_in_render_payload
from .media_validation import assert_product_image, assert_reference_video
from .product_lock_generator import generate_product_lock
from .reference_analyzer import analyze_reference_video
from .schemas import CompileSmartRemakeRequest
from .source_frames import attach_source_frame_assets
from .source_shot_detector import enrich_reference_analysis_with_detected_cuts


def _input_for_normalizer(input_data: CompileSmartRemakeRequest) -> dict[str, Any]:
    return {
        "prompt": input_data.prompt,
        "description": input_data.description,
        "productUrl": input_data.productUrl,
        "referenceImages": input_data.referenceImages,
        "referenceVideo": input_data.referenceVideoUrl,
        "productLock": input_data.productLock,
        "visualIdentity": input_data.visualIdentity,
        "productReference": input_data.productReference,
    }


def _without_extracted_reference_music(reference_analysis: dict[str, Any], reason: str) -> dict[str, Any]:
    audio_plan = reference_analysis.get("audioPlan") or {}
    warnings = [*(audio_plan.get("warnings") or []), reason]
    return {
        **reference_analysis,
        "audioPlan": {
            **audio_plan,
            "warnings": warnings,
            "referenceMusic": {"mode": "none", "reason": reason},
        },
    }


async def _extract_reference_music_if_needed(reference_analysis: dict[str, Any], input_data: CompileSmartRemakeRequest, warnings: list[str]) -> dict[str, Any]:
    audio_plan = reference_analysis.get("audioPlan") or {}
    reference_music = audio_plan.get("referenceMusic") if isinstance(audio_plan.get("referenceMusic"), dict) else {}
    if reference_music.get("mode") != "extract":
        return reference_analysis
    if not input_data.referenceVideo:
        reason = "No reference video bytes were available for music extraction."
        warnings.append("Reference music extraction skipped because no reference video bytes were available.")
        return _without_extracted_reference_music(reference_analysis, reason)
    try:
        extracted = extract_reference_music(input_data.referenceVideo)
    except Exception as exc:
        message = str(exc)
        warnings.append(f"Reference music extraction skipped: {message}")
        return _without_extracted_reference_music(reference_analysis, message)
    return {
        **reference_analysis,
        "audioPlan": {
            **audio_plan,
            "referenceMusic": {
                **reference_music,
                "mode": "extract",
                "assetId": extracted["assetId"],
            },
        },
    }


async def compile_smart_remake(
    input_data: CompileSmartRemakeRequest,
    *,
    gemini: SmartRemakeGeminiClient | None = None,
) -> dict[str, Any]:
    cleanup_smart_remake_assets()
    if input_data.referenceVideo:
        assert_reference_video(input_data.referenceVideo)
    if input_data.productImage:
        assert_product_image(input_data.productImage)

    normalized = normalize_analyze_input(_input_for_normalizer(input_data))
    if not has_analyze_source(
        normalized,
        {
            "hasReferenceVideo": bool(input_data.referenceVideo),
            "hasProductImage": bool(input_data.productImage),
        },
    ):
        raise SmartRemakeValidationError(
            "At least one prompt, description, product URL, image, or video reference is required.",
            "INVALID_ANALYZE_INPUT",
            [],
        )

    gemini = gemini or HttpGeminiClient()
    warnings = list(input_data.warnings)
    if not input_data.referenceVideo:
        warnings.append("No reference video supplied; motion analysis is inferred from prompt and product context only.")

    reference_analysis = await analyze_reference_video(
        target_duration=input_data.targetDuration,
        prompt=normalized.get("prompt"),
        description=normalized.get("description"),
        reference_video=input_data.referenceVideo,
        gemini=gemini,
    )
    reference_analysis = enrich_reference_analysis_with_detected_cuts(
        reference_analysis,
        input_data.referenceVideo,
    )
    reference_analysis = await _extract_reference_music_if_needed(reference_analysis, input_data, warnings)
    for warning in (reference_analysis.get("renderability") or {}).get("warnings", []):
        formatted = f"{warning.get('code')}: {warning.get('message')}"
        if warning.get("code") and warning.get("message") and formatted not in warnings:
            warnings.append(formatted)

    product_lock = await generate_product_lock(
        product_image=input_data.productImage,
        metadata=input_data.productMetadata,
        prompt=normalized.get("prompt"),
        description=normalized.get("description"),
        product_lock=normalized.get("productLock"),
        visual_identity=normalized.get("visualIdentity"),
        product_reference=normalized.get("productReference"),
        gemini=gemini,
    )
    compiled = compile_smart_remake_scene_map_with_diagnostics(
        {
            "mode": input_data.mode,
            "targetDuration": input_data.targetDuration,
            "aspectRatio": input_data.aspectRatio,
            "language": input_data.language,
            "referenceAnalysis": reference_analysis,
            "productLock": product_lock,
        }
    )
    scene_map = attach_source_frame_assets(
        scene_map=compiled["sceneMap"],
        reference_analysis=reference_analysis,
        reference_video=input_data.referenceVideo,
    )
    diagnostics = compiled["diagnostics"]
    for warning in diagnostics.get("normalizationWarnings", []):
        formatted = f"{warning.get('code')}: {warning.get('message')}"
        if warning.get("code") and warning.get("message") and formatted not in warnings:
            warnings.append(formatted)

    analyze_output = normalize_analyze_output(
        {
            "product": {
                "name": product_lock["productName"],
                "brandName": (normalized.get("productReference") or {}).get("brandName"),
                "description": input_data.productMetadata.description if input_data.productMetadata else normalized.get("description"),
                "category": product_lock["productType"],
            },
            "primarySubject": {
                "name": product_lock["productReference"]["characterName"],
                "description": (normalized.get("productReference") or {}).get("description"),
            },
            "productLock": {
                "mode": product_lock["mode"],
                "mustPreserve": product_lock["mustPreserve"],
                "canChange": product_lock["canChange"],
                "productUsage": product_lock.get("productUsage", {}),
            },
            "visualIdentity": {
                "colors": product_lock["visualIdentity"]["colors"],
                "style": (normalized.get("visualIdentity") or {}).get("style"),
                "typography": (normalized.get("visualIdentity") or {}).get("typography"),
                "mood": (normalized.get("visualIdentity") or {}).get("mood"),
            },
            "creativeDirection": {
                "concept": reference_analysis["creativeConcept"]["hook"],
                "tone": None,
                "visualStyle": reference_analysis["format"],
            },
            "audioPlan": reference_analysis["audioPlan"],
            "warnings": warnings,
        },
        normalized,
    )

    assert_no_reference_video_in_render_payload(scene_map)
    assert_allowed_request_type("GENERATE_IMAGE")
    assert_allowed_request_type("GENERATE_VIDEO")
    assert_allowed_endpoint("/api/requests/batch")

    return {
        "success": True,
        "mode": input_data.mode,
        "renderSubmitted": False,
        "inputSummary": {
            "targetDuration": input_data.targetDuration,
            "aspectRatio": input_data.aspectRatio,
            "language": input_data.language,
            "productSource": input_data.productSource,
            "referenceVideoMimeType": input_data.referenceVideo.mime_type if input_data.referenceVideo else None,
            "referenceVideoSizeBytes": len(input_data.referenceVideo.bytes) if input_data.referenceVideo else None,
            "productImageMimeType": input_data.productImage.mime_type if input_data.productImage else None,
            "productImageSizeBytes": len(input_data.productImage.bytes) if input_data.productImage else None,
        },
        "referenceAnalysis": reference_analysis,
        "analyzeOutput": analyze_output,
        "productLock": product_lock,
        "sceneMap": scene_map,
        "compiledPrompts": [
            {
                "displayOrder": scene["displayOrder"],
                "prompt": scene["prompt"],
                "imagePrompt": scene["imagePrompt"],
                "videoPrompt": scene["videoPrompt"],
            }
            for scene in scene_map["scenes"]
        ],
        "compilerVersion": "smart-remake-compiler-v2",
        "compilerDiagnostics": {
            "creativeArchetype": diagnostics["creativeArchetype"],
            "visualStructure": diagnostics["visualStructure"],
            "selectedStrategy": diagnostics["selectedStrategy"],
            "normalizedTimeline": diagnostics["scenes"],
            "warnings": diagnostics["normalizationWarnings"],
        },
        "diagnostics": diagnostics,
        "versions": {
            "referenceAnalyzer": "smart-remake-reference-analyzer-v1",
            "productLock": "smart-remake-product-lock-v1",
            "compiler": "smart-remake-compiler-v2",
            "sceneMap": "smart-remake-scene-map-v1",
        },
        "warnings": warnings,
    }
