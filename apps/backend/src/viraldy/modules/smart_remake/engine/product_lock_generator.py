from typing import Any

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


async def generate_product_lock(
    *,
    product_image: UploadedMedia | None,
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
    system, user_prompt = build_product_lock_prompt(
        metadata=metadata,
        prompt=prompt,
        description=description,
        product_lock_mode=(product_lock or {}).get("mode"),
        must_preserve=(product_lock or {}).get("mustPreserve"),
        can_change=(product_lock or {}).get("canChange"),
        visual_colors=(visual_identity or {}).get("colors"),
    )
    raw = await gemini.generate_json(
        system_instruction=system,
        prompt=user_prompt,
        media=[{"mime_type": product_image.mime_type, "bytes": product_image.bytes}] if product_image else None,
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


__all__ = ["PRODUCT_IMAGE_MIME_TYPES", "generate_product_lock", "normalize_product_lock"]
