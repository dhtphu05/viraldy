from typing import Any
from urllib.parse import urlparse

from .errors import SmartRemakeValidationError
from .schemas import ProductLock, ProductMetadata, normalize_text, string_list


ProductLockMode = str


def _trim_optional(value: Any) -> str | None:
    normalized = normalize_text(value)
    return normalized or None


def _null_if_blank(value: Any) -> str | None:
    return _trim_optional(value)


def _assert_url(value: str, field: str) -> None:
    parsed = urlparse(value)
    if not parsed.scheme or not parsed.netloc:
        raise SmartRemakeValidationError(
            f"{field} must be a valid URL.",
            "INVALID_ANALYZE_INPUT",
            {"field": field, "value": value},
        )


def _normalize_url_array(value: Any, field: str) -> list[str]:
    urls = string_list(value)
    for url in urls:
        _assert_url(url, field)
    return urls


def resolve_product_lock_mode(input_value: dict[str, Any] | None) -> ProductLockMode:
    if input_value and input_value.get("mode") is not None:
        mode = input_value["mode"]
        if mode in {"off", "auto", "strict"}:
            return mode
        raise SmartRemakeValidationError(
            "productLock.mode must be off, auto, or strict.",
            "INVALID_PRODUCT_LOCK",
            {"mode": mode},
        )
    if input_value and input_value.get("enabled") is False:
        return "off"
    return "auto"


def normalize_analyze_input(input_value: dict[str, Any]) -> dict[str, Any]:
    product_reference = input_value.get("productReference")
    normalized_reference = None
    if isinstance(product_reference, dict):
        normalized_reference = {
            "characterName": _trim_optional(product_reference.get("characterName")),
            "productName": _trim_optional(product_reference.get("productName")),
            "brandName": _trim_optional(product_reference.get("brandName")),
            "description": _trim_optional(product_reference.get("description")),
            "imageUrls": _normalize_url_array(product_reference.get("imageUrls"), "productReference.imageUrls"),
            "videoUrls": _normalize_url_array(product_reference.get("videoUrls"), "productReference.videoUrls"),
        }

    product_url = _trim_optional(input_value.get("productUrl"))
    if product_url:
        _assert_url(product_url, "productUrl")
    reference_video = _trim_optional(input_value.get("referenceVideo"))
    if reference_video:
        _assert_url(reference_video, "referenceVideo")

    visual_identity = input_value.get("visualIdentity") if isinstance(input_value.get("visualIdentity"), dict) else {}
    logo_url = _trim_optional(visual_identity.get("logoUrl"))
    if logo_url:
        _assert_url(logo_url, "visualIdentity.logoUrl")

    product_lock = input_value.get("productLock") if isinstance(input_value.get("productLock"), dict) else {}
    return {
        "prompt": _trim_optional(input_value.get("prompt")),
        "description": _trim_optional(input_value.get("description")),
        "productUrl": product_url,
        "referenceImages": _normalize_url_array(input_value.get("referenceImages"), "referenceImages"),
        "referenceVideo": reference_video,
        "productLock": {
            "mode": resolve_product_lock_mode(product_lock),
            "mustPreserve": string_list(product_lock.get("mustPreserve")),
            "canChange": string_list(product_lock.get("canChange")),
        },
        "visualIdentity": {
            "colors": string_list(visual_identity.get("colors")),
            "style": _trim_optional(visual_identity.get("style")),
            "typography": _trim_optional(visual_identity.get("typography")),
            "logoUrl": logo_url,
            "mood": _trim_optional(visual_identity.get("mood")),
        },
        "productReference": normalized_reference,
    }


def has_analyze_source(input_value: dict[str, Any], media: dict[str, bool] | None = None) -> bool:
    media = media or {}
    product_reference = input_value.get("productReference") or {}
    return bool(
        input_value.get("prompt")
        or input_value.get("description")
        or input_value.get("productUrl")
        or input_value.get("referenceVideo")
        or input_value.get("referenceImages")
        or product_reference.get("imageUrls")
        or product_reference.get("videoUrls")
        or media.get("hasReferenceVideo")
        or media.get("hasProductImage")
    )


def get_product_subject_name(input_value: dict[str, Any]) -> str:
    product_reference = input_value.get("productReference") or {}
    analyze_output = input_value.get("analyzeOutput") or {}
    product = analyze_output.get("product") or {}
    subject = analyze_output.get("primarySubject") or {}
    return (
        _trim_optional(product_reference.get("characterName"))
        or _trim_optional(product_reference.get("productName"))
        or _trim_optional(product_reference.get("brandName"))
        or _trim_optional(subject.get("name"))
        or _trim_optional(product.get("name"))
        or _trim_optional(input_value.get("productName"))
        or _trim_optional(input_value.get("productType"))
        or "Main Product"
    )


def normalize_analyze_output(raw: dict[str, Any], normalized: dict[str, Any]) -> dict[str, Any]:
    product_reference = normalized.get("productReference") or {}
    product = raw.get("product") or {}
    primary_subject = raw.get("primarySubject") or {}
    inferred_name = (
        _trim_optional(primary_subject.get("name"))
        or _trim_optional(product.get("name"))
        or product_reference.get("characterName")
        or product_reference.get("productName")
        or product_reference.get("brandName")
        or "Main Product"
    )
    return {
        "product": {
            "name": _null_if_blank(product.get("name")),
            "brandName": _null_if_blank(product.get("brandName")),
            "description": _null_if_blank(product.get("description")),
            "category": _null_if_blank(product.get("category")),
        },
        "primarySubject": {
            "name": inferred_name,
            "description": _null_if_blank(primary_subject.get("description")),
        },
        "productLock": {
            "mode": normalized["productLock"]["mode"],
            "mustPreserve": (raw.get("productLock") or {}).get("mustPreserve", normalized["productLock"]["mustPreserve"]),
            "canChange": (raw.get("productLock") or {}).get("canChange", normalized["productLock"]["canChange"]),
        },
        "visualIdentity": {
            "colors": (raw.get("visualIdentity") or {}).get("colors", normalized["visualIdentity"]["colors"]),
            "style": (raw.get("visualIdentity") or {}).get("style", normalized["visualIdentity"].get("style")),
            "typography": (raw.get("visualIdentity") or {}).get("typography", normalized["visualIdentity"].get("typography")),
            "mood": (raw.get("visualIdentity") or {}).get("mood", normalized["visualIdentity"].get("mood")),
        },
        "creativeDirection": {
            "concept": (raw.get("creativeDirection") or {}).get("concept"),
            "tone": (raw.get("creativeDirection") or {}).get("tone"),
            "visualStyle": (raw.get("creativeDirection") or {}).get("visualStyle"),
        },
        "audioPlan": raw.get("audioPlan"),
        "references": {
            "images": product_reference.get("imageUrls") or normalized.get("referenceImages") or [],
            "videos": product_reference.get("videoUrls") or ([normalized["referenceVideo"]] if normalized.get("referenceVideo") else []),
        },
        "warnings": raw.get("warnings") or [],
    }


def metadata_to_dict(metadata: ProductMetadata | None) -> dict[str, Any] | None:
    return metadata.model_dump(exclude_none=True) if metadata else None


def product_lock_to_dict(product_lock: ProductLock) -> dict[str, Any]:
    return product_lock.model_dump(exclude_none=True)
