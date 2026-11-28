"""Private, idempotent intake persisted before any analysis or generation."""

from __future__ import annotations

import hashlib
import io
import logging
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from PIL import Image, UnidentifiedImageError
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from starlette.concurrency import run_in_threadpool

from viraldy.shared.errors.base import AppError, ConflictError, NotFoundError

from .engine.media_validation import assert_product_image, assert_reference_video
from .engine.schemas import UploadedMedia
from .models import SmartRemakeProjectModel
from .product_references import MAX_PRODUCT_REFERENCE_IMAGES, read_product_references
from .project_contracts import SmartRemakeIntakeRequest
from .project_policy import assert_character_consent, constraints_hash, rights_snapshot, stable_hash
from .repair_media import RepairMediaStore
from .repair_repository import RepairRepository

logger = logging.getLogger(__name__)


def _upload(
    value: UploadedMedia | bytes, *, role: Literal["source", "product", "character"]
) -> UploadedMedia:
    data = value.bytes if isinstance(value, UploadedMedia) else value
    if role == "source":
        mime = "video/webm" if data[:4] == b"\x1aE\xdf\xa3" else "video/mp4"
        result = (
            value if isinstance(value, UploadedMedia) else UploadedMedia(bytes=data, mime_type=mime)
        )
        assert_reference_video(result)
        if not (data[:4] == b"\x1aE\xdf\xa3" or data[4:8] == b"ftyp"):
            raise AppError(
                "UNSUPPORTED_SMART_REMAKE_MEDIA_TYPE", "Source must contain video media."
            )
        return result
    # Verify actual image bytes, not a browser MIME declaration, before retention.
    result = (
        value
        if isinstance(value, UploadedMedia)
        else UploadedMedia(bytes=data, mime_type="image/png")
    )
    assert_product_image(result)
    try:
        with Image.open(io.BytesIO(data)) as image:
            image_mime = {"PNG": "image/png", "JPEG": "image/jpeg", "WEBP": "image/webp"}.get(
                image.format or ""
            )
            image.verify()
        if image_mime is None:
            raise ValueError("Unsupported image format")
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise AppError(
            "UNSUPPORTED_SMART_REMAKE_MEDIA_TYPE", f"{role.title()} must be a valid image."
        ) from exc
    return UploadedMedia(bytes=data, mime_type=image_mime, file_name=result.file_name)


async def _discard_uncommitted(media: RepairMediaStore, keys: list[str]) -> None:
    for key in keys:
        try:
            await run_in_threadpool(media.storage.delete_object, key)
        except Exception:
            logger.exception("Failed to remove an uncommitted Smart Remake intake upload")


def _check_replay(row: SmartRemakeProjectModel, request_hash: str) -> SmartRemakeProjectModel:
    if row.context_json.get("p0", {}).get("intakeRequestHash") != request_hash:
        raise ConflictError(
            "SMART_REMAKE_IDEMPOTENCY_CONFLICT", "This key belongs to another intake."
        )
    return row


async def create_intake(
    repository: RepairRepository,
    media: RepairMediaStore,
    workspace_id: UUID,
    actor_id: UUID,
    payload: SmartRemakeIntakeRequest,
    source: UploadedMedia | bytes,
    product: UploadedMedia | bytes,
    character: UploadedMedia | bytes | None = None,
    *,
    additional_products: Sequence[UploadedMedia | bytes] | None = None,
    staged_uploads: Sequence[dict[str, Any]] | None = None,
) -> SmartRemakeProjectModel:
    if payload.targetDuration == 12:
        from .engine.config import get_kie_video_model

        if get_kie_video_model() != "wan/3-0-video":
            raise AppError(
                "SMART_REMAKE_VIDEO_DURATION_INVALID", "Twelve-second output requires Wan.", 422
            )
    if len(additional_products or []) >= MAX_PRODUCT_REFERENCE_IMAGES:
        raise AppError(
            "SMART_REMAKE_PRODUCT_REFERENCES_INVALID", "Use at most fourteen product images.", 422
        )
    additional = [_upload(value, role="product") for value in additional_products or []]
    uploads = {
        "source": _upload(source, role="source"),
        "product": _upload(product, role="product"),
    }
    if character is not None:
        uploads["character"] = _upload(character, role="character")
    if payload.requirements.requiresCharacter and "character" not in uploads:
        raise AppError(
            "SMART_REMAKE_CHARACTER_REFERENCE_REQUIRED", "Upload a real character reference.", 403
        )
    if "character" in uploads:
        assert_character_consent(payload.rights.model_dump(mode="json"))
    hashes: dict[str, Any] = {
        role: hashlib.sha256(upload.bytes).hexdigest() for role, upload in uploads.items()
    }
    if additional:
        hashes["additionalProducts"] = [
            hashlib.sha256(upload.bytes).hexdigest() for upload in additional
        ]
        product_hashes = [hashes["product"], *hashes["additionalProducts"]]
        if len(set(product_hashes)) != len(product_hashes):
            raise AppError(
                "SMART_REMAKE_PRODUCT_REFERENCES_INVALID",
                "Choose distinct product images; the same image was included more than once.", 422,
            )
    request_hash = stable_hash({"request": payload.model_dump(mode="json"), "inputs": hashes})
    project_id = uuid5(
        NAMESPACE_URL, f"viraldy-p0:{workspace_id}:{actor_id}:{payload.idempotencyKey}"
    )
    # Transaction-level lock also serializes duplicate intake uploads across API processes.
    session = getattr(repository, "session", None)
    if session is not None:
        await session.execute(
            text("SELECT pg_advisory_xact_lock(:key)"),
            {"key": int.from_bytes(hashlib.sha256(project_id.bytes).digest()[:8], signed=True)},
        )
    try:
        existing = await repository.project(workspace_id, project_id)
    except NotFoundError:
        existing = None
    if existing is not None:
        if session is not None:
            await session.commit()
        return _check_replay(existing, request_hash)
    prefix = f"workspaces/{workspace_id}/smart-remake/{project_id}/inputs"
    keys: list[str] = []
    try:
        assets = {}
        for role, upload in uploads.items():
            key = await media.put(prefix, upload.bytes, upload.mime_type)
            keys.append(key)
            assets[role] = {
                "id": str(uuid4()),
                "role": role,
                "storageKey": key,
                "mimeType": upload.mime_type,
                "mediaHash": hashes[role],
                "sizeBytes": len(upload.bytes),
            }
        now = datetime.now(UTC).isoformat()
        additional_assets = []
        for upload, digest in zip(additional, hashes.get("additionalProducts", []), strict=True):
            key = await media.put(prefix, upload.bytes, upload.mime_type)
            keys.append(key)
            additional_assets.append({
                "id": str(uuid4()), "role": "product", "storageKey": key,
                "mimeType": upload.mime_type, "mediaHash": digest, "sizeBytes": len(upload.bytes),
            })
        context: dict[str, Any] = {
            "schemaVersion": 2,
            "projectName": payload.projectName,
            "audioRequired": payload.targetDuration == 12,
            "p0": {
                "schemaVersion": 1,
                "phase": "intake",
                "actorId": str(actor_id),
                "createdAt": now,
                "intakeRequestHash": request_hash,
                "inputHash": stable_hash(hashes),
                "targetDuration": payload.targetDuration,
                "requirements": payload.requirements.model_dump(mode="json"),
                "rights": rights_snapshot(payload.rights, actor_id=actor_id),
                "budgetPolicy": payload.budget.model_dump(mode="json"),
                "assets": assets,
                "release": {"approval": None},
            },
        }
        if staged_uploads:
            context["p0"]["stagedUploads"] = [dict(item) for item in staged_uploads]
        if additional_assets:
            context["p0"]["additionalProductReferences"] = additional_assets
        for role, asset in assets.items():
            context.update(
                {
                    f"{role}Key": asset["storageKey"],
                    f"{role}MimeType": asset["mimeType"],
                    f"{role}MediaHash": asset["mediaHash"],
                }
            )
        context["p0"]["constraintsHash"] = constraints_hash(context)
        row = SmartRemakeProjectModel(
            id=project_id,
            workspace_id=workspace_id,
            revision=1,
            context_json=context,
            state_json={
                "id": str(project_id),
                "schemaVersion": 2,
                "revision": 1,
                "phase": "intake",
                "status": "draft",
                "scenes": [],
                "provider": "kie",
                "targetDuration": payload.targetDuration,
                "finalVideoUrl": "",
                "draftTimeline": None,
                "publishedTimeline": None,
            },
        )
        await repository.create(row)
    except IntegrityError:
        if session is None:
            raise
        await session.rollback()
        await _discard_uncommitted(media, keys)
        return _check_replay(await repository.project(workspace_id, project_id), request_hash)
    except Exception:
        if session is not None:
            await session.rollback()
        await _discard_uncommitted(media, keys)
        raise
    return row


async def assert_input_binding(row: SmartRemakeProjectModel, media: RepairMediaStore) -> None:
    """Validate the saved private inputs, including character references, before remote work."""
    p0 = row.context_json.get("p0", {})
    assets = p0.get("assets", {})
    if not assets or not p0.get("inputHash"):
        raise AppError(
            "SMART_REMAKE_INTAKE_REQUIRED", "Create an owned intake before continuing.", 403
        )
    hashes: dict[str, Any] = {}
    for role, asset in assets.items():
        if row.context_json.get(f"{role}Key") != asset.get("storageKey"):
            raise AppError("SMART_REMAKE_INPUT_CHANGED", "Saved input bindings have changed.", 409)
        try:
            data = await media.read(asset["storageKey"])
        except Exception as exc:
            raise AppError(
                "SMART_REMAKE_INPUT_UNAVAILABLE", "An owned input is unavailable.", 409
            ) from exc
        media_hash = hashlib.sha256(data).hexdigest()
        if media_hash != asset.get("mediaHash") or media_hash != row.context_json.get(
            f"{role}MediaHash"
        ):
            raise AppError("SMART_REMAKE_INPUT_CHANGED", "Owned input bytes have changed.", 409)
        hashes[role] = media_hash
    if "additionalProductReferences" in p0:
        references = await read_product_references(row.context_json, media)
        if len(references) > 1:
            hashes["additionalProducts"] = [
                hashlib.sha256(value.bytes).hexdigest() for value in references[1:]
            ]
    if stable_hash(hashes) != p0["inputHash"]:
        raise AppError("SMART_REMAKE_INPUT_CHANGED", "Owned input manifest has changed.", 409)
