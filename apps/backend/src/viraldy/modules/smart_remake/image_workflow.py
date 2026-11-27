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
from typing import Any, Literal, NoReturn
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
from .engine.performer_continuity import performer_continuity_directions
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
PRESENTER_IDENTITY_POLICY_VERSION = "fictional-vietnamese-presenter-v2"
ConditioningFrameRole = Literal["opening", "ending"]


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


async def _references(
    repair: Any, row: Any, index: int, *, frame_role: ConditioningFrameRole = "opening",
) -> tuple[UploadedMedia, UploadedMedia]:
    if frame_role not in {"opening", "ending"}:
        raise _asset_invalid()
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
    frame = source_range["startFrame"] if frame_role == "opening" else source_range["endFrame"] - 1
    layout_data = await run_in_threadpool(extract_layout_frame, source_data, frame)
    if opening.get("sourceMediaHash") != source_hash or (
        frame_role == "opening" and opening != {
            "sourceMediaHash": source_hash,
            "frame": source_range["startFrame"],
            "layoutHash": hashlib.sha256(layout_data).hexdigest(),
            "extractorVersion": OPENING_FRAME_EXTRACTOR_VERSION,
        }
    ):
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


def _image_prompt(
    context: dict[str, Any], scene: dict[str, Any], *,
    frame_role: ConditioningFrameRole = "opening", presenter_anchor: bool = False,
) -> str:
    direction = scene.get("videoPrompt") if frame_role == "ending" else scene.get("imagePrompt")
    if not isinstance(direction, str) or not direction.strip():
        raise AppError(
            "OPENAI_IMAGE_VALIDATION_FAILED", f"An {frame_role}-frame direction is required."
        )
    character = (
        "Image 3 is the authorized target character identity. Preserve that person's face and "
        "appearance. Do not use faces from composition image 2.\n"
        if context.get("characterKey") else (
            "When a person or face is visible in image 2, replace that identity with a "
            "distinct fictional adult Vietnamese presenter, distinct from every person in image 2. "
            "Do not infer the source person's ethnicity. Preserve the observed action, pose, "
            "gaze, framing and camera while changing facial identity. Do not add a person or face "
            "to product-only or hands-only shots; preserve hands-only framing.\n"
            "This identity replacement takes precedence over source-person descriptions and "
            "creative edits that ask to retain the source face. Use a plain unbranded top as "
            "supporting wardrobe only; do not carry over the source person's clothing or graphic "
            "T-shirt unless it is the exact target garment required by the seller.\n"
            + ("Image 3 is the previously generated target presenter. Reuse that same fictional "
               "adult's same face, hairstyle and wardrobe when a person is visible. Read only the "
               "person region, even if image 3 is a montage; never copy the anchor's layout, "
               "product, pose, camera, background or composition. It is identity-only evidence; "
               "its presence does not require a person in this frame.\n"
               if presenter_anchor else "")
        )
    )
    state = (
        "Render its stateAfter and terminal pose at the source ending, after the action. "
        "The earlier stateBefore is context, not the state to render."
        if frame_role == "ending" else
        "Render its stateBefore at the source opening, before movement or stateAfter takes place."
    )
    return (
        f"Create one photorealistic 9:16 {frame_role} frame for a product video. "
        "Image 1 is the seller's real product and the sole product identity reference. "
        "Preserve its exact shape, proportions, colors, material, markings and physical details. "
        "If image 1 is a cutaway or section diagram, use it as a construction reference and render "
        "the intact finished outer body for normal product use, unless the saved scene explicitly "
        "requests a section illustration. Do not invent components or mechanisms. "
        f"Image 2 is the exact source scene {frame_role} frame: preserve its physical state, "
        "composition, camera, pose and background; replace its product "
        "with the exact product from image 1, including its existing branding. Do not copy "
        "source-video captions, unrelated branding or faces from composition image 2. "
        "Preserve the exact panel count and layout from image 2: retain a source split-screen "
        "when present, and use a single full frame otherwise. Do not add panels, frame labels "
        "or captions.\n"
        f"{character}"
        "When the product is clothing or a saved requirement specifies an outfit, the target "
        "garment's design, graphics, colors and branding take precedence over supporting wardrobe "
        "and the identity anchor's outfit. Preserve that exact target garment, including its "
        "required logos; keep the designated person's facial identity.\n"
        f"{performer_continuity_directions()}\n"
        f"PRESENTER IDENTITY POLICY: {PRESENTER_IDENTITY_POLICY_VERSION}\n"
        f"PRODUCT IDENTITY: {json.dumps(context.get('productLock', {}), sort_keys=True)}\n"
        f"EXPECTATIONS HASH: {context.get('expectationsHash', '')}\n"
        f"SOURCE OPENING BINDING: {json.dumps({key: scene.get(key) for key in (
            'renderUnitId', 'sourceSceneId', 'sourceRange', 'openingFrame'
        )}, sort_keys=True)}\n"
        f"CONDITIONING FRAME: {json.dumps(context.get('conditioningFrame', {}), sort_keys=True)}\n"
        f"{frame_role.upper()} FRAME DIRECTIONS: {direction.strip()}"
        f"\nSCENE REQUIREMENTS: {json.dumps(scene.get('shotPlan', {}), sort_keys=True)}"
        f"\nThe shot plan describes the full action as context. {state}"
        + ("\nSELLER SCENE EDITS: " + scene["userEdits"]
           + "\nApply these creative directions while product identity, saved requirements and "
           f"the {frame_role} physical state remain fixed."
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
    try:
        data = await repair.media.read(record["storageKey"])
    except (OSError, KeyError):
        raise _asset_invalid() from None
    if hashlib.sha256(data).hexdigest() != record.get("mediaHash"):
        raise _asset_invalid()
    try:
        await run_in_threadpool(validate_generated_png, data)
    except ValueError:
        raise _asset_invalid() from None
    return copy.deepcopy(record)


def _frame_subject_presence(
    context: dict[str, Any], scene: dict[str, Any], frame: int,
) -> str | None:
    """Use observed shot metadata, never guess a face or ethnicity from free text."""
    analysis = context.get("referenceAnalysis") or {}
    source_start = (context.get("sourceSceneMap") or {}).get("sourceStartFrame", 0)
    analysis_second = (frame - source_start) / 24
    for shot in analysis.get("sourceShots") or []:
        start, end = shot.get("startSecond"), shot.get("endSecond")
        presence = shot.get("subjectPresence")
        if (
            isinstance(start, int | float) and isinstance(end, int | float)
            and start <= analysis_second < end
            and isinstance(presence, str) and presence in {"person", "none", "hands_only"}
        ):
            return presence
    shots = (scene.get("shotPlan") or {}).get("shots") or []
    if shots:
        shot = shots[0] if frame == scene["sourceRange"]["startFrame"] else shots[-1]
        presence = shot.get("subjectPresence")
        if isinstance(presence, str) and presence in {"person", "none", "hands_only"}:
            return presence
    # A video-wide person flag cannot establish that this particular frame shows a face.
    presence = analysis.get("subjectPresence")
    return presence if isinstance(presence, str) and presence in {"none", "hands_only"} else None


async def _presenter_anchor(
    repair: Any, row: Any, identity: dict[str, Any], previous: dict[str, Any],
) -> tuple[UploadedMedia, dict[str, Any]] | None:
    prior = previous.get("presenterIdentity") or {}
    retained = previous.get("status") in {"submitting", "submitted", "completed"}
    canonical = row.context_json.get("presenterIdentityAnchor") or {}
    if retained and _same_presenter_scope(prior, identity):
        selected = prior.get("anchor")
        if not selected:
            return None  # A retained submission keeps its original identity inputs.
        candidates = [selected["requestHash"]]
    elif _same_presenter_scope(canonical, identity):
        selected = canonical.get("anchor")
        if not isinstance(selected, dict) or not isinstance(selected.get("requestHash"), str):
            raise _asset_invalid()
        candidates = [selected["requestHash"]]
    else:
        assets = row.context_json.get("imageAssets", {})
        candidates = sorted((
            request_hash for request_hash, record in row.context_json.get("imageAssets", {}).items()
            if isinstance(record, dict)
            and (actor := record.get("presenterIdentity") or {}).get("eligibleAnchor") is True
            and _same_presenter_scope(actor, identity)
        ), key=lambda key: (_presenter_frame(assets[key]), key))
        selected = None
    if not candidates:
        return None
    cached = await _cached_image(repair, row, candidates[0])
    if cached is None:
        raise _asset_invalid()
    actor = cached.get("presenterIdentity") or {}
    if actor.get("eligibleAnchor") is not True or not _same_presenter_scope(actor, identity):
        raise _asset_invalid()
    anchor = {key: cached[key] for key in ("requestHash", "mediaHash", "storageKey")}
    if selected is not None and selected != anchor:
        raise _asset_invalid()
    try:
        data = await repair.media.read(anchor["storageKey"])
    except (OSError, KeyError):
        raise _asset_invalid() from None
    # Recheck the bytes we actually send, rather than trusting an earlier storage read.
    if hashlib.sha256(data).hexdigest() != anchor["mediaHash"]:
        raise _asset_invalid()
    if selected is None:
        await repair.repository.merge_context(row, {
            "presenterIdentityAnchor": _presenter_record(identity, anchor),
        })
    return UploadedMedia(bytes=data, mime_type="image/png", file_name="presenter-identity"), anchor


def _same_presenter_scope(value: Any, identity: dict[str, Any]) -> bool:
    return isinstance(value, dict) and all(
        value.get(key) == identity[key]
        for key in ("policyVersion", "sourceMediaHash", "productMediaHash")
    )


def _presenter_frame(record: dict[str, Any]) -> int:
    reference = record.get("referenceFrame") or record.get("openingFrame") or {}
    frame = reference.get("frame")
    return frame if type(frame) is int and frame >= 0 else 2**63


def _presenter_record(identity: dict[str, Any], anchor: dict[str, Any]) -> dict[str, Any]:
    return {
        **{key: identity[key] for key in ("policyVersion", "sourceMediaHash", "productMediaHash")},
        "anchor": copy.deepcopy(anchor),
    }


def _image_request_hash(
    binding: dict[str, Any], prompt: str, character: UploadedMedia | None,
    identity: dict[str, Any],
) -> str:
    return hashlib.sha256(json.dumps({
        **binding, "prompt": prompt, "presenterIdentity": identity,
        **({"characterHash": hashlib.sha256(character.bytes).hexdigest()} if character else {}),
    }, sort_keys=True).encode()).hexdigest()


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
    frame_role: ConditioningFrameRole = "opening",
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
    product, layout = await _references(repair, row, index, frame_role=frame_role)
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
        or (frame_role == "opening" and expected_scene["openingFrame"].get("layoutHash")
            != hashlib.sha256(layout.bytes).hexdigest())
        or expectations["references"]["product"]["mediaHash"]
        != hashlib.sha256(product.bytes).hexdigest()
    ):
        raise _asset_invalid()
    frame = source_range["startFrame"] if frame_role == "opening" else source_range["endFrame"] - 1
    reference_frame = {
        "sourceMediaHash": expectations["references"]["source"]["mediaHash"],
        "frame": frame, "layoutHash": hashlib.sha256(layout.bytes).hexdigest(),
        "extractorVersion": OPENING_FRAME_EXTRACTOR_VERSION,
    }
    prompt_context["conditioningFrame"] = {"frameRole": frame_role, **reference_frame}
    images = operation.result_json.get("images", {})
    image_key = str(index) if frame_role == "opening" else f"{index}:ending"
    previous = images.get(image_key, {})
    character = await character_reference(repair, row)
    presence = _frame_subject_presence(row.context_json, compiled_scene, frame)
    identity = {
        "policyVersion": PRESENTER_IDENTITY_POLICY_VERSION,
        "mode": "custom" if character else "synthetic",
        "sourceMediaHash": reference_frame["sourceMediaHash"],
        "productMediaHash": hashlib.sha256(product.bytes).hexdigest(),
        "eligibleAnchor": character is None and presence == "person",
    }
    retained = previous.get("status") in {"submitting", "submitted", "completed"}
    prior_identity = previous.get("presenterIdentity") or {}
    if retained and _same_presenter_scope(prior_identity, identity) and (
        (prior_identity.get("mode") == "custom") == (character is not None)
    ):
        identity = copy.deepcopy(prior_identity)
    prompt = _image_prompt(prompt_context, compiled_scene, frame_role=frame_role)
    # Expectations and extractor versions intentionally invalidate older layout caches.
    settings = {"model": model, "size": IMAGE_SIZE, "quality": quality}
    if complexity is not None:
        settings["complexity"] = complexity
    binding = {
        **settings, "productHash": identity["productMediaHash"],
        "layoutHash": reference_frame["layoutHash"],
        "expectationsHash": operation.result_json.get("expectationsHash")
        or row.context_json["expectationsHash"],
        "openingFrame": expected_scene["openingFrame"],
        "frameRole": frame_role, "referenceFrame": reference_frame,
    }
    request_hash = _image_request_hash(binding, prompt, character, identity)
    if character is None:
        anchored = await _presenter_anchor(repair, row, identity, previous)
        # The canonical image itself must restore without becoming its own reference.
        if anchored is not None and anchored[1]["requestHash"] != request_hash:
            character, anchor = anchored
            identity = {**identity, "mode": "anchored", "eligibleAnchor": False, "anchor": anchor}
            prompt = _image_prompt(
                prompt_context, compiled_scene, frame_role=frame_role, presenter_anchor=True,
            )
            request_hash = _image_request_hash(binding, prompt, character, identity)
    if retained and previous.get("requestHash") != request_hash:
        await _unresolved(operation, save)
    cached = await _cached_image(repair, row, request_hash)
    validate_generation_payload(
        prompt, row.context_json.get("referenceAnalysis", {}), expectations["productLock"]
    )
    if len(prompt) > 32000:
        raise AppError(
            "OPENAI_IMAGE_VALIDATION_FAILED",
            "Saved constraints exceed the image prompt budget. Use concise requirements.",
        )
    if cached is None and retained:
        await _unresolved(operation, save)
    if cached is None:
        attempt, created = await reserve_generation_attempt(
            repair, row, operation, slot=f"image:{image_key}", request_hash=request_hash,
            stage="image", provider="openai", model=model, profile=settings,
        )
        if not created:
            await _unresolved(operation, save)
        attempt_id = str(attempt.id) if attempt else None
        intent = {
            **({"attemptId": attempt_id} if attempt_id else {}),
            "status": "submitting",
            "requestHash": request_hash,
            "frameRole": frame_role, "referenceFrame": reference_frame,
            "presenterIdentity": identity,
            **settings,
        }
        await save(operation, {**operation.result_json, "images": {**images, image_key: intent}})
        ensure_active()
        try:
            await mark_generation_submitted(repair, row, attempt_id)
        except AppError as exc:
            await save(operation, {
                **operation.result_json,
                "images": {**images, image_key: {
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
                    "images": {**operation.result_json.get("images", {}), image_key: {
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
                "frameRole": frame_role, "referenceFrame": reference_frame,
                "presenterIdentity": identity,
                **({"attemptId": attempt_id} if attempt_id else {}),
            }
            ensure_active()
            updates = {"imageAssets": {
                **row.context_json.get("imageAssets", {}), request_hash: cached,
            }}
            if identity["eligibleAnchor"] and not _same_presenter_scope(
                row.context_json.get("presenterIdentityAnchor"), identity,
            ):
                updates["presenterIdentityAnchor"] = _presenter_record(identity, {
                    key: cached[key] for key in ("requestHash", "mediaHash", "storageKey")
                })
            await repair.repository.merge_context(row, updates)
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
                image_key: {**cached, "status": "completed"},
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
