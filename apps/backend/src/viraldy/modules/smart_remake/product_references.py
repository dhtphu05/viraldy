"""Canonical primary-first product evidence shared across analysis, generation and QA."""

from __future__ import annotations

import copy
import hashlib
from io import BytesIO
from typing import TYPE_CHECKING, Any

from PIL import Image, UnidentifiedImageError

from viraldy.shared.errors.base import AppError

if TYPE_CHECKING:
    from .engine.schemas import UploadedMedia

MAX_PRODUCT_REFERENCE_IMAGES = 14


def _invalid() -> AppError:
    return AppError(
        "SMART_REMAKE_PRODUCT_REFERENCES_INVALID",
        "Use one main product image and at most thirteen additional product views.", 422,
    )


def product_reference_assets(context: dict[str, Any]) -> list[dict[str, Any]]:
    """Keep the persisted primary aliases intact and never manufacture extra rights roles."""
    p0 = context.get("p0") or {}
    primary = (p0.get("assets") or {}).get("product")
    if primary is None:
        primary = {
            "role": "product", "storageKey": context.get("productKey"),
            "mimeType": context.get("productMimeType"),
            "mediaHash": context.get("productMediaHash"),
        }
    extras = p0.get("additionalProductReferences", [])
    if (
        not isinstance(primary, dict) or not isinstance(extras, list)
        or len(extras) >= MAX_PRODUCT_REFERENCE_IMAGES
        or any(not isinstance(asset, dict) or asset.get("role") != "product" for asset in extras)
    ):
        raise _invalid()
    hashes = [asset.get("mediaHash") for asset in [primary, *extras]]
    if (
        extras and all(isinstance(value, str) for value in hashes)
        and len(set(hashes)) != len(hashes)
    ):
        raise _invalid()
    return copy.deepcopy([primary, *extras])


def validate_product_reference_image(media: UploadedMedia) -> None:
    """Check the declared MIME, size and decoded image format before remote processing."""
    from .engine.media_validation import assert_product_image

    assert_product_image(media)
    try:
        with Image.open(BytesIO(media.bytes)) as image:
            mime = {"PNG": "image/png", "JPEG": "image/jpeg", "WEBP": "image/webp"}.get(
                image.format or ""
            )
            image.verify()
        if mime != media.mime_type:
            raise ValueError("MIME does not match decoded bytes")
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise AppError(
            "SMART_REMAKE_INPUT_CHANGED", "A product reference is not a valid retained image.", 409
        ) from exc


async def read_product_references(context: dict[str, Any], media: Any) -> list[UploadedMedia]:
    """Read and hash-check every retained angle; never accept a browser URL as evidence."""
    from .engine.schemas import UploadedMedia

    values = []
    for index, asset in enumerate(product_reference_assets(context)):
        key, digest = asset.get("storageKey"), asset.get("mediaHash")
        if (
            not isinstance(key, str) or not key or not isinstance(digest, str)
            or asset.get("mimeType") not in {"image/png", "image/jpeg", "image/webp"}
        ):
            raise AppError(
                "SMART_REMAKE_INPUT_CHANGED", "Product reference binding is missing.", 409,
            )
        if index == 0 and any(
            context.get(alias) not in {None, asset.get(field)}
            for alias, field in (
                ("productKey", "storageKey"), ("productMediaHash", "mediaHash"),
                ("productMimeType", "mimeType"),
            )
        ):
            raise AppError("SMART_REMAKE_INPUT_CHANGED", "Main product binding changed.", 409)
        try:
            data = await media.read(key)
        except Exception as exc:
            raise AppError(
                "SMART_REMAKE_INPUT_UNAVAILABLE", "A product reference is unavailable.", 409,
            ) from exc
        if hashlib.sha256(data).hexdigest() != digest:
            raise AppError("SMART_REMAKE_INPUT_CHANGED", "Product reference bytes changed.", 409)
        value = UploadedMedia(bytes=data, mime_type=asset.get("mimeType"))
        validate_product_reference_image(value)
        values.append(value)
    return values
