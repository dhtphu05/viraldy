from io import BytesIO
from typing import Any

from PIL import Image, ImageOps

from .analyze_normalizer import get_product_subject_name
from .gemini_client import SmartRemakeGeminiClient
from .media_validation import PRODUCT_IMAGE_MIME_TYPES, assert_product_image
from .prompts import build_product_lock_prompt
from .schemas import ProductMetadata, UploadedMedia, normalize_text, string_list


def _title_case(value: str) -> str:
    return " ".join(word[:1].upper() + word[1:] for word in normalize_text(value).split(" "))


def normalize_product_lock(raw: Any, *, metadata: ProductMetadata | None, prompt: str | None, description: str | None, product_lock: dict[str, Any] | None, visual_identity: dict[str, Any] | None, product_reference: dict[str, Any] | None) -> dict[str, Any]:
    raw = raw if isinstance(raw, dict) else {}
    product_lock = product_lock or {}
    visual_identity = visual_identity or {}
    product_reference = product_reference or {}
    raw_visual = raw.get("visualIdentity") if isinstance(raw.get("visualIdentity"), dict) else {}
    raw_ref = raw.get("productReference") if isinstance(raw.get("productReference"), dict) else {}
    raw_usage = raw.get("productUsage") if isinstance(raw.get("productUsage"), dict) else {}
    existing_usage = product_lock.get("productUsage") if isinstance(product_lock.get("productUsage"), dict) else {}
    product_name = normalize_text(raw.get("productName"), metadata.title if metadata and metadata.title else product_reference.get("productName") or "Main Product")
    product_type = normalize_text(raw.get("productType"), "product")
    mode = product_lock.get("mode") or raw.get("mode") or "auto"
    character_name = _title_case(
        get_product_subject_name(
            {
                "productReference": product_reference,
                "productName": metadata.title if metadata and metadata.title else product_name,
                "productType": product_type,
            }
        )
    )[:80]
    colors = string_list(raw_visual.get("colors")) or string_list(visual_identity.get("colors"))
    return {
        "mode": mode if mode in {"off", "auto", "strict"} else "auto",
        "productName": product_name,
        "productType": product_type,
        "visualIdentity": {
            "colors": colors,
            "pattern": normalize_text(raw_visual.get("pattern")) or None,
            "texture": normalize_text(raw_visual.get("texture")) or None,
            "shape": normalize_text(raw_visual.get("shape")) or None,
            "material": normalize_text(raw_visual.get("material")) or None,
            "visibleBranding": normalize_text(raw_visual.get("visibleBranding")) or None,
        },
        "productUsage": {
            "realisticUseCases": string_list(raw_usage.get("realisticUseCases")) or string_list(existing_usage.get("realisticUseCases")),
            "suitableSurfaces": string_list(raw_usage.get("suitableSurfaces")) or string_list(existing_usage.get("suitableSurfaces")),
            "contactPoints": string_list(raw_usage.get("contactPoints")) or string_list(existing_usage.get("contactPoints")),
            "handlingInstructions": string_list(raw_usage.get("handlingInstructions")) or string_list(existing_usage.get("handlingInstructions")),
            "usageConstraints": string_list(raw_usage.get("usageConstraints")) or string_list(existing_usage.get("usageConstraints")),
            "forbiddenUsageErrors": string_list(raw_usage.get("forbiddenUsageErrors")) or string_list(existing_usage.get("forbiddenUsageErrors")),
        },
        "mustPreserve": [] if mode == "off" else (string_list(raw.get("mustPreserve")) or string_list(product_lock.get("mustPreserve"))),
        "canChange": string_list(raw.get("canChange")) or string_list(product_lock.get("canChange")),
        "forbiddenErrors": [] if mode == "off" else string_list(raw.get("forbiddenErrors")),
        "productReference": {
            "imageUrl": raw_ref.get("imageUrl"),
            "storageKey": raw_ref.get("storageKey"),
            "characterName": character_name,
            "entityType": "visual_asset",
        },
    }


def prepare_product_analysis_images(images: list[UploadedMedia]) -> list[UploadedMedia]:
    """Bound multi-view inline analysis copies while retained generation originals stay intact."""
    if len(images) <= 1:
        return images
    from ..product_references import (
        MAX_PRODUCT_REFERENCE_IMAGES,
        validate_product_reference_image,
    )
    from .errors import SmartRemakeValidationError

    if len(images) > MAX_PRODUCT_REFERENCE_IMAGES:
        raise SmartRemakeValidationError(
            "Use at most fourteen product images.", "SMART_REMAKE_PRODUCT_REFERENCES_INVALID",
        )
    copies = []
    for reference in images:
        validate_product_reference_image(reference)
        if len(reference.bytes) <= 900_000:
            copies.append(reference)
            continue
        with Image.open(BytesIO(reference.bytes)) as decoded:
            rgba = ImageOps.exif_transpose(decoded).convert("RGBA")
            image = Image.alpha_composite(
                Image.new("RGBA", rgba.size, "white"), rgba,
            ).convert("RGB")
        encoded = b""
        for edge in (2048, 1536, 1024, 768, 512):
            image.thumbnail((edge, edge), Image.Resampling.LANCZOS)
            for quality in (90, 75, 55):
                output = BytesIO()
                image.save(output, format="JPEG", quality=quality)
                encoded = output.getvalue()
                if len(encoded) <= 900_000:
                    break
            if len(encoded) <= 900_000:
                break
        copies.append(UploadedMedia(bytes=encoded, mime_type="image/jpeg"))
    return copies


async def generate_product_lock(
    *,
    product_image: UploadedMedia | None,
    additional_product_images: list[UploadedMedia] | None = None,
    metadata: ProductMetadata | None,
    prompt: str | None,
    description: str | None,
    product_lock: dict[str, Any] | None,
    visual_identity: dict[str, Any] | None,
    product_reference: dict[str, Any] | None,
    gemini: SmartRemakeGeminiClient,
) -> dict[str, Any]:
    if product_image:
        assert_product_image(product_image)
    additional = additional_product_images or []
    if additional and product_image is None:
        from .errors import SmartRemakeValidationError

        raise SmartRemakeValidationError(
            "Additional product views require a main image.",
            "SMART_REMAKE_PRODUCT_REFERENCES_INVALID",
        )
    system, user_prompt = build_product_lock_prompt(
        metadata=metadata,
        prompt=prompt,
        description=description,
        product_lock_mode=(product_lock or {}).get("mode"),
        must_preserve=(product_lock or {}).get("mustPreserve"),
        can_change=(product_lock or {}).get("canChange"),
        visual_colors=(visual_identity or {}).get("colors"),
    )
    if additional:
        user_prompt += (
            "\nThe attached images show the same product from different views. Image 1 is the "
            "main reference; all later images are additional product evidence. Combine observed "
            "details across every image, including handles, lids and the complete exterior. "
            "Distinguish a cutaway or technical illustration from the product's actual exterior; "
            "never make the finished product appear cut open merely because an image is a diagram."
        )
    images = prepare_product_analysis_images(
        ([product_image] if product_image else []) + additional
    )
    raw = await gemini.generate_json(
        system_instruction=system,
        prompt=user_prompt,
        media=[{"mime_type": image.mime_type, "bytes": image.bytes} for image in images] or None,
    )
    return normalize_product_lock(
        raw,
        metadata=metadata,
        prompt=prompt,
        description=description,
        product_lock=product_lock,
        visual_identity=visual_identity,
        product_reference=product_reference,
    )


__all__ = [
    "PRODUCT_IMAGE_MIME_TYPES", "generate_product_lock", "normalize_product_lock",
    "prepare_product_analysis_images",
]
