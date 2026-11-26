"""Retain owned image edits and fence unresolved paid submissions across retries."""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import tempfile
from collections.abc import Awaitable, Callable
from io import BytesIO
from pathlib import Path
from typing import Any, NoReturn
from uuid import UUID

from PIL import Image
from starlette.concurrency import run_in_threadpool

from viraldy.shared.errors.base import AppError

from .engine.media_binaries import ffmpeg_path
from .engine.openai_images import (
    IMAGE_MODEL,
    IMAGE_SIZE,
    SUPPORTED_IMAGE_MODELS,
    validate_generated_png,
)
from .engine.prompt_sanitizer import validate_generation_payload
from .engine.schemas import UploadedMedia
from .generation_budget import (
    character_reference,
    generation_execution_receipt,
    mark_generation_submitted,
    require_generation_policy,
    reserve_generation_attempt,
    saved_requirements_prompt,
    settle_generation_attempt,
)
from .generation_expectations import (
    expectations_scene,
    require_generation_expectations,
    validate_generation_expectations,
)

OPENING_FRAME_EXTRACTOR_VERSION = "source-opening-frame-v1"


def _asset_invalid() -> AppError:
    return AppError(
        "SMART_REMAKE_IMAGE_ASSET_INVALID",
        "The retained image references changed or are unreadable. Refresh the project first.",
        409,
    )


def extract_layout_frame(data: bytes, frame: int) -> bytes:
    """Decode a real frame from the private source; never follow client media URLs."""
    if type(frame) is not int or frame < 0:
        raise _asset_invalid()
    with tempfile.TemporaryDirectory(prefix="smart-remake-image-layout-") as temporary:
        source, target = Path(temporary) / "source", Path(temporary) / "layout.png"
        source.write_bytes(data)
        subprocess.run(  # noqa: S603 - fixed local argv, no shell or user paths
            [
                ffmpeg_path(),
                "-y",
                "-i",
                str(source),
                "-vf",
                f"fps=24,select=eq(n\\,{frame})",
                "-frames:v",
                "1",
                str(target),
            ],
            check=True,
            capture_output=True,
            timeout=120,
        )
        return target.read_bytes()


async def _references(repair: Any, row: Any, index: int) -> tuple[UploadedMedia, UploadedMedia]:
    context = row.context_json
    product_data = await repair.media.read(context["productKey"])
    product_hash = hashlib.sha256(product_data).hexdigest()
    if context.get("productMediaHash") not in {None, product_hash}:
        raise _asset_invalid()
    unit = context["renderPlan"]["units"][index]
    source_range, opening = _source_binding(context, unit)
    source_data = await repair.media.read(context["sourceKey"])
    source_hash = hashlib.sha256(source_data).hexdigest()
    if context.get("sourceMediaHash") not in {None, source_hash}:
        raise _asset_invalid()
    layout_data = await run_in_threadpool(
        extract_layout_frame, source_data, source_range["startFrame"]
    )
    if opening != {
        "sourceMediaHash": source_hash,
        "frame": source_range["startFrame"],
        "layoutHash": hashlib.sha256(layout_data).hexdigest(),
        "extractorVersion": OPENING_FRAME_EXTRACTOR_VERSION,
    }:
        raise _asset_invalid()
    try:
        with Image.open(BytesIO(layout_data)) as image:
            layout_mime = {"PNG": "image/png", "JPEG": "image/jpeg", "WEBP": "image/webp"}[
                image.format or ""
            ]
            image.verify()
    except (OSError, ValueError, KeyError):
        raise _asset_invalid() from None
    return (
        UploadedMedia(bytes=product_data, mime_type=context["productMimeType"]),
        UploadedMedia(bytes=layout_data, mime_type=layout_mime),
    )


def _source_binding(
    context: dict[str, Any], unit: dict[str, Any]
) -> tuple[dict[str, int], dict[str, Any]]:
    source_map = context["sourceSceneMap"]
    source = next(
        (scene for scene in source_map["scenes"] if scene["id"] == unit["sourceSceneId"]),
        None,
    )
    if source is None:
        raise _asset_invalid()
    fragment = source_map.get("timingMode") == "fit_target"
    start = unit.get("sourceStartFrame") if fragment else source["startFrame"]
    end = unit.get("sourceEndFrame") if fragment else source["endFrame"]
    if (
        type(start) is not int
        or type(end) is not int
        or not source["startFrame"] <= start < end <= source["endFrame"]
    ):
        raise _asset_invalid()
    binding_key = unit["id"] if fragment else unit["sourceSceneId"]
    opening = context.get("sourceOpeningFrames", {}).get(binding_key)
    if not isinstance(opening, dict):
        raise _asset_invalid()
    return {"startFrame": start, "endFrame": end}, opening


def _image_prompt(context: dict[str, Any], scene: dict[str, Any]) -> str:
    direction = scene.get("imagePrompt")
    if not isinstance(direction, str) or not direction.strip():
        raise AppError("OPENAI_IMAGE_VALIDATION_FAILED", "An opening-frame direction is required.")
    character = (
        "Image 3 is the authorized target character identity. Preserve that person's face and "
        "appearance. Do not use faces from composition image 2.\n"
        if context.get("characterKey") else ""
    )
    return (
        "Create one photorealistic 9:16 opening frame for a product video. "
        "Image 1 is the seller's real product and the sole product identity reference. "
        "Preserve its exact shape, proportions, colors, material, markings and physical details. "
        "Image 2 is the exact source scene opening frame: preserve its starting physical state, "
        "composition, camera, pose and background; replace its product "
        "with the exact product from image 1, including its existing branding. Do not copy "
        "source-video captions, unrelated branding or faces from composition image 2. "
        "Render a full scene, without a collage, frame labels or added captions.\n"
        f"{character}"
        f"PRODUCT IDENTITY: {json.dumps(context.get('productLock', {}), sort_keys=True)}\n"
        f"EXPECTATIONS HASH: {context.get('expectationsHash', '')}\n"
        f"SOURCE OPENING BINDING: {json.dumps({key: scene.get(key) for key in (
            'renderUnitId', 'sourceSceneId', 'sourceRange', 'openingFrame'
        )}, sort_keys=True)}\n"
        f"OPENING FRAME DIRECTIONS: {direction.strip()}"
        f"\nSCENE REQUIREMENTS: {json.dumps(scene.get('shotPlan', {}), sort_keys=True)}"
        "\nThe shot plan describes future action as context. Render its stateBefore at the "
        "source opening, before movement or stateAfter takes place."
        + ("\nSELLER SCENE EDITS: " + scene["userEdits"]
           + "\nApply these creative directions while product identity, saved requirements and "
           "the opening physical state remain fixed."
           if scene.get("userEdits") else "")
        + saved_requirements_prompt(context)
    )


async def _cached_image(repair: Any, row: Any, request_hash: str) -> dict[str, Any] | None:
    record = row.context_json.get("imageAssets", {}).get(request_hash)
    if record is None:
        return None
    prefix = f"workspaces/{repair.workspace_id}/smart-remake/"
    key = record.get("storageKey") if isinstance(record, dict) else None
    parts = key.split("/", 5) if isinstance(key, str) else []
    if (
        not isinstance(record, dict)
        or record.get("requestHash") != request_hash
        or not isinstance(key, str)
        or not key.startswith(prefix)
        or len(parts) != 6
        or parts[4] != "images"
        or not parts[5]
    ):
        raise _asset_invalid()
    try:
        UUID(parts[3])
    except ValueError:
        raise _asset_invalid() from None
    data = await repair.media.read(record["storageKey"])
    if hashlib.sha256(data).hexdigest() != record.get("mediaHash"):
        raise _asset_invalid()
    try:
        await run_in_threadpool(validate_generated_png, data)
    except ValueError:
        raise _asset_invalid() from None
    return copy.deepcopy(record)


async def prepare_scene_image(
    *,
    repair: Any,
    row: Any,
    operation: Any,
    index: int,
    compiled_scene: dict[str, Any],
    image_client: Any,
    save: Callable[..., Awaitable[None]],
    ensure_active: Callable[[], None],
) -> dict[str, Any]:
    ensure_active()
    # Re-read owned context so a cache committed by an earlier attempt is visible.
    row = await repair.repository.project(repair.workspace_id, row.id)
    await require_generation_policy(repair, row)
    plan = row.context_json["renderPlan"]
    model = plan.get("imageModel")
    quality = plan.get("imageQuality", "low")
    complexity = plan.get("imageComplexity")
    if (
        model not in SUPPORTED_IMAGE_MODELS
        or plan.get("imageSize", IMAGE_SIZE) != IMAGE_SIZE
        or quality not in {"low", "medium", "high", "xhigh", "max"}
        or (complexity is not None and complexity not in {"low", "medium", "high"})
        or (model == IMAGE_MODEL and complexity is None)
    ):
        raise AppError("OPENAI_IMAGE_VALIDATION_FAILED", "The saved image settings are invalid.")
    product, layout = await _references(repair, row, index)
    current_expectations = require_generation_expectations(row.context_json)
    frozen = operation.result_json.get("generationExpectations")
    if not operation.result_json.get("expectationsHash"):
        raise AppError(
            "SMART_REMAKE_EXPECTATIONS_REQUIRED",
            "The operation must retain its generation requirements before creating an image.", 409,
        )
    expectations = validate_generation_expectations(
        frozen, operation.result_json.get("expectationsHash")
    )
    if any(expectations.get(key) != current_expectations.get(key) for key in (
        "productLock", "requirements", "requirementsHash", "references", "sourceContext",
    )):
        raise AppError(
            "SMART_REMAKE_EXPECTATIONS_CHANGED", "The saved product or requirements changed.", 409,
        )
    unit = row.context_json["renderPlan"]["units"][index]
    source_range, opening = _source_binding(row.context_json, unit)
    expected_scene = expectations_scene(expectations, unit["id"])
    compiled_scene = expected_scene
    prompt_context = {
        **row.context_json,
        "productLock": expectations["productLock"],
        "expectationsHash": operation.result_json.get("expectationsHash"),
        "p0": {**row.context_json.get("p0", {}),
               "requirements": expectations.get("requirements", {})},
    }
    if (
        expected_scene["sourceSceneId"] != unit["sourceSceneId"]
        or expected_scene["sourceRange"] != source_range
        or expected_scene["openingFrame"] != opening
        or expected_scene["openingFrame"].get("layoutHash")
        != hashlib.sha256(layout.bytes).hexdigest()
        or expectations["references"]["product"]["mediaHash"]
        != hashlib.sha256(product.bytes).hexdigest()
    ):
        raise _asset_invalid()
    character = await character_reference(repair, row)
    prompt = _image_prompt(prompt_context, compiled_scene)
    validate_generation_payload(
        prompt, row.context_json.get("referenceAnalysis", {}), expectations["productLock"]
    )
    if len(prompt) > 32000:
        raise AppError(
            "OPENAI_IMAGE_VALIDATION_FAILED",
            "Saved constraints exceed the image prompt budget. Use concise requirements.",
        )
    # Expectations and extractor versions intentionally invalidate older layout caches.
    settings = {"model": model, "size": IMAGE_SIZE, "quality": quality}
    if complexity is not None:
        settings["complexity"] = complexity
    request_hash = hashlib.sha256(
        json.dumps(
            {
                **settings,
                "prompt": prompt,
                "productHash": hashlib.sha256(product.bytes).hexdigest(),
                "layoutHash": hashlib.sha256(layout.bytes).hexdigest(),
                "expectationsHash": operation.result_json.get("expectationsHash")
                or row.context_json["expectationsHash"],
                "openingFrame": expected_scene["openingFrame"],
                **(
                    {"characterHash": hashlib.sha256(character.bytes).hexdigest()}
                    if character else {}
                ),
            },
            sort_keys=True,
        ).encode()
    ).hexdigest()
    cached = await _cached_image(repair, row, request_hash)
    images = operation.result_json.get("images", {})
    previous = images.get(str(index), {})
    if cached is None and previous.get("status") in {"submitting", "completed"}:
        await _unresolved(operation, save)
    if cached is None:
        attempt, created = await reserve_generation_attempt(
            repair, row, operation, slot=f"image:{index}", request_hash=request_hash,
            stage="image", provider="openai", model=model, profile=settings,
        )
        if not created:
            await _unresolved(operation, save)
        attempt_id = str(attempt.id) if attempt else None
        intent = {
            **({"attemptId": attempt_id} if attempt_id else {}),
            "status": "submitting",
            "requestHash": request_hash,
            **settings,
        }
        await save(operation, {**operation.result_json, "images": {**images, str(index): intent}})
        ensure_active()
        try:
            await mark_generation_submitted(repair, row, attempt_id)
        except AppError as exc:
            await save(operation, {
                **operation.result_json,
                "images": {**images, str(index): {
                    **intent, "status": "preflight_rejected", "errorCode": exc.code,
                }},
            })
            raise
        try:
            output = await image_client.edit(
                prompt=prompt,
                product=product,
                layout=layout,
                **({"character": character} if character else {}),
                model=model,
                quality=quality,
                complexity=complexity or "high",
            )
        except Exception as exc:
            execution = generation_execution_receipt(
                image_client, attempt_id=attempt_id, request_hash=request_hash,
                provider="openai", model=model, operation="openai.images.edit",
            )
            if getattr(exc, "code", "") in {
                "OPENAI_IMAGE_NOT_LIVE",
                "OPENAI_IMAGE_NOT_CONFIGURED",
                "OPENAI_IMAGE_VALIDATION_FAILED",
                "OPENAI_IMAGE_AUTH_FAILED",
                "OPENAI_IMAGE_PERMISSION_DENIED",
                "OPENAI_IMAGE_RATE_LIMITED",
                "OPENAI_IMAGE_CREDITS_EXHAUSTED",
                "OPENAI_IMAGE_REQUEST_REJECTED",
            }:
                from .generation_recovery import image_rejection_details

                rejection = image_rejection_details(
                    getattr(image_client, "last_rejection_receipt", None)
                )
                await settle_generation_attempt(
                    repair, row, attempt_id, status="failed",
                    receipt={"errorCode": getattr(exc, "code", ""), **execution, **rejection},
                )
                await save(operation, {
                    **operation.result_json,
                    "images": {**operation.result_json.get("images", {}), str(index): {
                        **intent, "status": "rejected" if rejection else "failed",
                        "errorCode": getattr(exc, "code", ""), **rejection,
                    }},
                })
                raise
            await settle_generation_attempt(
                repair, row, attempt_id, status="unknown",
                receipt={"errorCode": "OPENAI_IMAGE_SUBMISSION_UNRESOLVED", **execution},
            )
            await _unresolved(operation, save)
        await settle_generation_attempt(
            repair, row, attempt_id, status="completed",
            receipt={
                "requestHash": request_hash, "mediaHash": output["mediaHash"],
                **({"providerRequestId": output["providerRequestId"]}
                   if output.get("providerRequestId") else {}),
                **generation_execution_receipt(
                    image_client, attempt_id=attempt_id, request_hash=request_hash,
                    provider="openai", model=model, operation="openai.images.edit",
                    request_id=output.get("providerRequestId"),
                ),
            },
            usage=output.get("usage"),
        )
        ensure_active()
        try:
            await run_in_threadpool(validate_generated_png, output["bytes"])
            if output["mediaHash"] != hashlib.sha256(output["bytes"]).hexdigest():
                raise _asset_invalid()
            key = await repair.media.put(
                f"workspaces/{repair.workspace_id}/smart-remake/{row.id}/images",
                output["bytes"],
                "image/png",
            )
            cached = {
                **{key: value for key, value in output.items() if key != "bytes"},
                "storageKey": key,
                "requestHash": request_hash,
                "expectationsHash": operation.result_json.get("expectationsHash")
                or row.context_json["expectationsHash"],
                "renderUnitId": expected_scene["renderUnitId"],
                "sourceSceneId": expected_scene["sourceSceneId"],
                "openingFrame": copy.deepcopy(expected_scene["openingFrame"]),
                **({"attemptId": attempt_id} if attempt_id else {}),
            }
            ensure_active()
            await repair.repository.merge_context(
                row,
                {"imageAssets": {**row.context_json.get("imageAssets", {}), request_hash: cached}},
            )
        except Exception as exc:
            if getattr(exc, "code", "") == "JOB_ATTEMPT_SUPERSEDED":
                raise
            await _unresolved(operation, save)
    await save(
        operation,
        {
            **operation.result_json,
            "images": {
                **operation.result_json.get("images", {}),
                str(index): {**cached, "status": "completed"},
            },
        },
    )
    return cached


async def _unresolved(operation: Any, save: Callable[..., Awaitable[None]]) -> NoReturn:
    await save(
        operation,
        {
            **operation.result_json,
            "needsReconciliation": True,
            "errorCode": "OPENAI_IMAGE_SUBMISSION_UNRESOLVED",
        },
    )
    raise AppError(
        "OPENAI_IMAGE_SUBMISSION_UNRESOLVED",
        "The existing image request requires reconciliation. No new image was generated.",
        409,
    )
