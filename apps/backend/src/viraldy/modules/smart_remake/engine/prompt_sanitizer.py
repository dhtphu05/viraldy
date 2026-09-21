import re
from typing import Any

from .errors import SmartRemakeError


COLOR_WORDS = ["black", "white", "grey", "gray", "green", "blue", "red", "pink", "purple", "yellow", "orange", "brown", "beige", "cream", "silver", "gold", "transparent"]
MATERIAL_WORDS = ["cotton", "linen", "leather", "wood", "metal", "plastic", "glass", "ceramic", "fabric", "velvet", "silicone", "rubber"]
PATTERN_WORDS = ["checkered", "checked", "plaid", "striped", "floral", "dotted", "speckled", "geometric", "quilted"]
GENERIC_FORBIDDEN_REUSE_TERMS = {
    "brand",
    "branding",
    "caption",
    "captions",
    "graphic",
    "graphics",
    "logo",
    "logos",
    "text",
    "wording",
    "words",
}


def _allowed_product_text(product_lock: dict[str, Any]) -> str:
    identity = product_lock.get("visualIdentity") or {}
    return " ".join(
        str(part)
        for part in [
            product_lock.get("productName"),
            product_lock.get("productType"),
            *(identity.get("colors") or []),
            identity.get("pattern"),
            identity.get("texture"),
            identity.get("shape"),
            identity.get("material"),
            identity.get("visibleBranding"),
            *(product_lock.get("mustPreserve") or []),
        ]
        if part
    ).lower()


def _forbidden_literal_terms(analysis: dict[str, Any], product_lock: dict[str, Any]) -> list[str]:
    allowed = _allowed_product_text(product_lock)
    terms = []
    for term in analysis.get("forbiddenReuse") or []:
        normalized = str(term).strip()
        lowered = normalized.lower()
        if (
            len(normalized) >= 3
            and not re.match(r"^(reference|original|same)\b", normalized, re.I)
            and lowered not in GENERIC_FORBIDDEN_REUSE_TERMS
            and lowered not in allowed
        ):
            terms.append(normalized)
    return terms


def sanitize_reference_product_text(*, text: str, analysis: dict[str, Any], product_lock: dict[str, Any]) -> str:
    result = text
    for term in _forbidden_literal_terms(analysis, product_lock):
        result = re.sub(rf"\b{re.escape(term)}\b", "the product", result, flags=re.I)
    allowed = _allowed_product_text(product_lock)
    for word in [*COLOR_WORDS, *MATERIAL_WORDS, *PATTERN_WORDS]:
        if word not in allowed:
            result = re.sub(rf"\b{word}\b", "target-product", result, flags=re.I)
    return (
        result.replace("the the product", "the product")
        .replace("target-product target-product", "target-product")
        .strip()
    )


def _affirmative_text(text: str) -> str:
    lines = []
    stripped = re.sub(r"\bdo not\b[^.\n]*", "", text, flags=re.I)
    stripped = re.sub(r"\bno\b[^.\n]*", "", stripped, flags=re.I)
    for line in stripped.splitlines():
        if not re.match(r"^\s*(do not|no)\b", line, re.I):
            lines.append(line)
    return "\n".join(lines)


def validate_sanitized_compiler_prompts(*, prompt: str, image_prompt: str, video_prompt: str, analysis: dict[str, Any], product_lock: dict[str, Any], timeline: dict[str, Any]) -> None:
    combined = f"{prompt}\n{image_prompt}\n{video_prompt}"
    affirmative = _affirmative_text(combined)
    for term in _forbidden_literal_terms(analysis, product_lock):
        if re.search(rf"\b{re.escape(term)}\b", affirmative, re.I):
            raise SmartRemakeError(f"Reference product descriptor remains in prompt: {term}.", "COMPILER_OUTPUT_INVALID")
    if analysis.get("subjectPresence") == "none" and re.search(r"\b(show|visible|include|use)\s+(an?\s+)?(actor|presenter|reviewer|person|woman|man|model|hands)\b", affirmative, re.I):
        raise SmartRemakeError("Product-only scene contains actor or presenter instructions.", "COMPILER_OUTPUT_INVALID")
    if analysis.get("subjectPresence") == "hands_only" and re.search(r"\b(show|visible|include|use)\s+(a\s+)?(face|facial identity|presenter|reviewer|visible person)\b", affirmative, re.I):
        raise SmartRemakeError("Hands-only scene contains face or presenter instructions.", "COMPILER_OUTPUT_INVALID")
    timeline_shots = timeline.get("shots") if isinstance(timeline.get("shots"), list) else []
    if timeline.get("visualStructure") == "continuous" and len(timeline_shots) <= 1 and re.search(r"\b(hard cut|jump cut|rapid cut|smash cut)\b", video_prompt, re.I):
        raise SmartRemakeError("Continuous structure contains hard-cut instructions.", "COMPILER_OUTPUT_INVALID")
