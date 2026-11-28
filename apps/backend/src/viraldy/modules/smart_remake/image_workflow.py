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
    MAX_IMAGE_REFERENCES,
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
SOURCE_FRAME_POLICY_VERSION = "source-frame-authority-v1"
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
    product_reference_count: int = 1, continuity_frame: bool = False,
    terminal_repair: dict[str, Any] | None = None,
) -> str:
    direction = scene.get("videoPrompt") if frame_role == "ending" else scene.get("imagePrompt")
    if not isinstance(direction, str) or not direction.strip():
        raise AppError(
            "OPENAI_IMAGE_VALIDATION_FAILED", f"An {frame_role}-frame direction is required."
        )
    source_authority = context.get("conditioningPolicy") == SOURCE_FRAME_POLICY_VERSION
    repaired_ending = source_authority and frame_role == "ending" and terminal_repair is not None
    person_pose = (
        "Keep the source framing and camera while changing facial identity; use the validated "
        "terminal action below for the ending pose. "
        if repaired_ending else (
            "Preserve the observed action, pose, gaze, framing and camera while changing "
            "facial identity. "
        )
    )
    layout_index, character_index = product_reference_count + 1, product_reference_count + 2
    product_directions = (
        "Image 1 is the seller's real product and the sole product identity reference. "
        "Preserve its exact shape, proportions, colors, material, markings and physical details. "
        "If image 1 is a cutaway or section diagram, use it as a construction reference and render "
        "the intact finished outer body for normal product use, unless the saved scene explicitly "
        "requests a section illustration. Do not invent components or mechanisms. "
        if product_reference_count == 1 else (
            f"Images 1 through {product_reference_count} show the same seller product from "
            "different angles. Image 1 is the primary appearance reference; use all supporting "
            "views to preserve its complete shape, proportions, colors, materials, markings and "
            "physical details. A detail unobserved in one view is not evidence that it is absent; "
            "use another view where it is visible. Cutaways and section diagrams show "
            "construction, "
            "not missing parts: render the intact finished outer body for normal use unless the "
            "saved scene explicitly requests a section illustration. Do not invent components, "
            "mechanisms or details unobserved in all views. Do not copy people, backgrounds or "
            "composition from the product references. "
        )
    )
    character = (
        f"Image {character_index} is the authorized target character identity. Preserve that "
        f"person's face and appearance. Do not use faces from composition image {layout_index}.\n"
        if context.get("characterKey") else (
            f"When a person or face is visible in image {layout_index}, "
            "replace that identity with a "
            "distinct fictional adult Vietnamese presenter, distinct from every person in "
            f"image {layout_index}. "
            "Do not infer the source person's ethnicity. "
            f"{person_pose}Do not add a person or face "
            "to product-only or hands-only shots; preserve hands-only framing.\n"
            "This identity replacement takes precedence over source-person descriptions and "
            "creative edits that ask to retain the source face. Use a plain unbranded top as "
            "supporting wardrobe only; do not carry over the source person's clothing or graphic "
            "T-shirt unless it is the exact target garment required by the seller.\n"
            + (f"Image {character_index} is the previously generated target presenter. "
               "Reuse that same fictional "
               "adult's same face, hairstyle and wardrobe when a person is visible. Read only the "
               f"person region, even if image {character_index} is a montage; "
               "never copy the anchor's layout, "
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
    scene_direction = (
        f"CONDITIONING POLICY: {SOURCE_FRAME_POLICY_VERSION}\n"
        "The exact supplied source frame is authoritative for physical state, product position, "
        "hand contact, body pose, camera, background and panel layout. Recreate that instant, "
        "replacing only product and person identity as instructed above. Scene summaries can "
        "describe a different instant: never invent a terminal pose or switch viewpoints to "
        "illustrate an action, stateBefore or stateAfter."
        if source_authority else (
            f"{frame_role.upper()} FRAME DIRECTIONS: {direction.strip()}"
            f"\nSCENE REQUIREMENTS: {json.dumps(scene.get('shotPlan', {}), sort_keys=True)}"
            f"\nThe shot plan describes the full action as context. {state}"
        )
    )
    if repaired_ending:
        scene_direction = (
            f"CONDITIONING POLICY: {SOURCE_FRAME_POLICY_VERSION}\n"
            "Apply only this validated terminal action and state from the accepted structured "
            "repair, after the immutable opening. These normalized terminal instructions "
            "override the source ending's physical state and action pose; do not restore its "
            "old state. The source camera, background and panel layout remain fixed. Preserve "
            "the exact seller product and designated presenter identity. Never change product "
            "construction or add panels to illustrate the action. Only supplied changed fields "
            "may override the source ending; preserve its actual state/pose for unspecified "
            "fields.\nVALIDATED TERMINAL REPAIR: "
            + json.dumps(terminal_repair, sort_keys=True)
        )
    if continuity_frame:
        continuity_index = product_reference_count + 2 + int(
            bool(context.get("characterKey")) or presenter_anchor
        )
        scene_direction += (
            f"\nImage {continuity_index} is the previous clip's generated ending, not the current "
            "source frame. It is optional continuity context: preserve stable product details, "
            "the designated person's identity and pose only when compatible with the current "
            "source frame. The current source frame always wins for camera, state, contact and "
            "layout. A real source cut can change framing. Do not copy the previous composition "
            "or add its person to a hands-only/product-only frame. Do not infer a seamless cut."
        )
    product_replacement = (
        "with the exact product from image 1, including its existing branding. Do not copy "
        if product_reference_count == 1 else (
            f"with the exact product from all product reference images 1 through "
            f"{product_reference_count}, preserving primary appearance and supporting views' "
            "visible geometry, including its existing branding. Do not copy "
        )
    )
    frame_preservation = (
        "preserve its composition, camera, background and panel layout; adapt only the "
        "validated terminal action/state below; replace its product "
        if repaired_ending else (
            "preserve its physical state, composition, camera, pose and background; "
            "replace its product "
        )
    )
    return (
        f"Create one photorealistic 9:16 {frame_role} frame for a product video. "
        f"{product_directions}"
        f"Image {layout_index} is the exact source scene {frame_role} frame: "
        f"{frame_preservation}"
        f"{product_replacement}"
        "source-video captions, unrelated branding or faces from composition "
        f"image {layout_index}. "
        f"Preserve the exact panel count and layout from image {layout_index}: "
        "retain a source split-screen "
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
        f"{scene_direction}"
        + ("\nSELLER SCENE EDITS: " + scene["userEdits"]
           + "\nApply these creative directions while product identity, saved requirements and "
           + ("the validated terminal state remain fixed." if repaired_ending else
              f"the {frame_role} physical state remain fixed.")
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
    ) and value.get("productReferenceHashes") == identity.get("productReferenceHashes")


def _presenter_frame(record: dict[str, Any]) -> int:
    reference = record.get("referenceFrame") or record.get("openingFrame") or {}
    frame = reference.get("frame")
    return frame if type(frame) is int and frame >= 0 else 2**63


def _presenter_record(identity: dict[str, Any], anchor: dict[str, Any]) -> dict[str, Any]:
    return {
        **{key: identity[key] for key in ("policyVersion", "sourceMediaHash", "productMediaHash")},
        **({"productReferenceHashes": copy.deepcopy(identity["productReferenceHashes"])}
           if "productReferenceHashes" in identity else {}),
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


async def _previous_generated_ending(
    repair: Any, row: Any, operation: Any, index: int, expectations: dict[str, Any],
) -> tuple[UploadedMedia, dict[str, Any]] | None:
    plan = operation.result_json.get("renderPlan") or row.context_json["renderPlan"]
    groups = plan.get("groups") or []
    unit = plan["units"][index]
    position = next((i for i, group in enumerate(groups)
                     if group.get("renderUnitIds", [None])[0] == unit["id"]), None)
    if position is None or position == 0:
        return None
    prior_id = groups[position - 1]["renderUnitIds"][-1]
    prior = next(value for value in plan["units"] if value["id"] == prior_id)
    record = operation.result_json.get("images", {}).get(f"{prior['sceneIndex']}:ending", {})
    if record.get("status") != "completed":
        return None
    scene = expectations_scene(expectations, prior_id)
    reference = record.get("referenceFrame") or {}
    if (
        record.get("frameRole") != "ending" or record.get("renderUnitId") != prior_id
        or record.get("expectationsHash") != operation.result_json["expectationsHash"]
        or reference.get("sourceMediaHash") != expectations["references"]["source"]["mediaHash"]
        or reference.get("frame") != scene["sourceRange"]["endFrame"] - 1
    ):
        raise _asset_invalid()
    cached = await _cached_image(repair, row, record["requestHash"])
    keys = ("requestHash", "mediaHash", "storageKey", "renderUnitId", "referenceFrame",
            "expectationsHash")
    if cached is None or any(cached.get(key) != record.get(key) for key in keys):
        raise _asset_invalid()
    data = await repair.media.read(cached["storageKey"])
    if hashlib.sha256(data).hexdigest() != cached["mediaHash"]:
        raise _asset_invalid()
    return UploadedMedia(bytes=data, mime_type="image/png"), {
        key: copy.deepcopy(cached[key]) for key in keys
    }


def _validated_group_terminal(
    operation: Any, scene: dict[str, Any],
) -> dict[str, Any] | None:
    from .repair_intent import GROUP_NORMALIZER_VERSION

    result = operation.result_json
    request = result.get("request") or {}
    normalization = result.get("repairNormalization") or {}
    if not (
        result.get("kind") == "repair" and request.get("repairScope") == "provider_group"
        and request.get("repairIntent")
        and normalization.get("version") == GROUP_NORMALIZER_VERSION
        and normalization.get("phase") == "resolved"
        and normalization.get("validationError") is False
        and (normalization.get("result") or {}).get("status") == "accepted"
    ):
        return None
    compiled = result.get("compiledScenes") or []
    identities = result["repairGroup"]["group"]["renderUnitIds"]
    matching = next((value for value in compiled
                     if value.get("renderUnitId") == scene["renderUnitId"]), None)
    if (
        [value.get("renderUnitId") for value in compiled] != identities
        or matching is None
        or any(matching.get(key, {}) != scene.get(key, {}) for key in (
            "prompt", "imagePrompt", "videoPrompt", "shotPlan", "sourceSegment",
        ))
    ):
        raise AppError(
            "SMART_REMAKE_INPUT_CHANGED", "Yêu cầu sửa cuối clip không khớp kịch bản đã lưu.", 409,
        )
    shots = (scene.get("shotPlan") or {}).get("shots") or []
    patch = next((value for value in normalization["result"].get("scenePatches") or []
                  if value.get("unitIndex") == len(identities) - 1), None)
    bases = result.get("repairBaseScenes") or []
    if patch is None or [value.get("renderUnitId") for value in bases] != identities:
        return None
    prior_shots = (bases[-1].get("shotPlan") or {}).get("shots") or []
    changes = (patch.get("scenePatch") or {}).get("shots") or []
    fields = ("action", "stateAfter", "physicalAction")
    if (
        not shots or len(prior_shots) != len(shots) or len(changes) != len(shots)
        or changes[-1].get("shotIndex") != len(shots) - 1
        or not any(
            changes[-1].get(key) is not None and shots[-1].get(key) != prior_shots[-1].get(key)
            for key in fields
        )
    ):
        return None
    return {
        key: copy.deepcopy(shots[-1][key]) for key in fields
        if changes[-1].get(key) is not None and shots[-1].get(key) != prior_shots[-1].get(key)
    }


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
    if (operation.result_json.get("request") or {}).get("repairScope") == "provider_group":
        group = (operation.result_json.get("repairGroup") or {}).get("group") or {}
        identities = group.get("renderUnitIds") or []
        saved_group = next((value for value in operation.result_json.get("renderPlan", {}).get(
            "groups", []
        ) if value.get("id") == group.get("id")), None)
        if (
            operation.result_json.get("kind") != "repair"
            or not identities or saved_group is None
            or saved_group.get("renderUnitIds") != identities
            or frame_role not in {"opening", "ending"}
            or type(index) is not int or not 0 <= index < len(plan["units"])
            or plan["units"][index]["id"] != identities[0 if frame_role == "opening" else -1]
        ):
            raise AppError(
                "SMART_REMAKE_REPAIR_SCOPE_INVALID",
                "Ảnh sửa phải thuộc đúng khung đầu và cuối của clip đã chọn.", 409,
            )
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
    products = [product]
    if (row.context_json.get("p0") or {}).get("additionalProductReferences"):
        from .product_references import read_product_references

        products = await read_product_references(row.context_json, repair.media)
        product = products[0]
    product_hashes = [hashlib.sha256(value.bytes).hexdigest() for value in products]
    reference_hashes = {"productReferenceHashes": product_hashes} if len(products) > 1 else {}
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
        "productReferenceHashes",
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
    source_authority = (
        operation.result_json.get("conditioningPolicy") == SOURCE_FRAME_POLICY_VERSION
    )
    if source_authority:
        prompt_context["conditioningPolicy"] = SOURCE_FRAME_POLICY_VERSION
    terminal_repair = (
        _validated_group_terminal(operation, expected_scene)
        if source_authority and frame_role == "ending" else None
    )
    if (
        expected_scene["sourceSceneId"] != unit["sourceSceneId"]
        or expected_scene["sourceRange"] != source_range
        or expected_scene["openingFrame"] != opening
        or (frame_role == "opening" and expected_scene["openingFrame"].get("layoutHash")
            != hashlib.sha256(layout.bytes).hexdigest())
        or expectations["references"]["product"]["mediaHash"]
        != hashlib.sha256(product.bytes).hexdigest()
        or expectations.get("productReferenceHashes")
        != reference_hashes.get("productReferenceHashes")
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
        **reference_hashes,
        "eligibleAnchor": character is None and presence == "person",
    }
    retained = previous.get("status") in {"submitting", "submitted", "completed"}
    prior_identity = previous.get("presenterIdentity") or {}
    if retained and _same_presenter_scope(prior_identity, identity) and (
        (prior_identity.get("mode") == "custom") == (character is not None)
    ):
        identity = copy.deepcopy(prior_identity)
    prompt = _image_prompt(
        prompt_context, compiled_scene, frame_role=frame_role,
        product_reference_count=len(products),
        terminal_repair=terminal_repair,
    )
    # Expectations and extractor versions intentionally invalidate older layout caches.
    settings = {"model": model, "size": IMAGE_SIZE, "quality": quality}
    if complexity is not None:
        settings["complexity"] = complexity
    binding = {
        **settings, "productHash": identity["productMediaHash"],
        **reference_hashes,
        "layoutHash": reference_frame["layoutHash"],
        "expectationsHash": operation.result_json.get("expectationsHash")
        or row.context_json["expectationsHash"],
        "openingFrame": expected_scene["openingFrame"],
        "frameRole": frame_role, "referenceFrame": reference_frame,
        **({"conditioningPolicy": SOURCE_FRAME_POLICY_VERSION} if source_authority else {}),
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
                product_reference_count=len(products),
                terminal_repair=terminal_repair,
            )
            request_hash = _image_request_hash(binding, prompt, character, identity)
    continuity = None
    continuity_binding: dict[str, Any] = {}
    if (
        source_authority and frame_role == "opening"
        and len(products) + 1 + int(character is not None) < MAX_IMAGE_REFERENCES
    ):
        continuity = await _previous_generated_ending(repair, row, operation, index, expectations)
        if continuity is not None:
            continuity_binding = {"continuityReference": continuity[1]}
            binding = {**binding, **continuity_binding}
            prompt = _image_prompt(
                prompt_context, compiled_scene, frame_role=frame_role,
                presenter_anchor=identity["mode"] == "anchored",
                product_reference_count=len(products), continuity_frame=True,
                terminal_repair=terminal_repair,
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
            **({"conditioningPolicy": SOURCE_FRAME_POLICY_VERSION} if source_authority else {}),
            **continuity_binding,
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
                **({"additional_products": products[1:]} if len(products) > 1 else {}),
                **({"character": character} if character else {}),
                **({"continuity_frame": continuity[0]} if continuity else {}),
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
                **({"conditioningPolicy": SOURCE_FRAME_POLICY_VERSION} if source_authority else {}),
                **continuity_binding,
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
