import copy
import json
import re
from typing import Any, cast

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
            and lowered not in {*COLOR_WORDS, *MATERIAL_WORDS, *PATTERN_WORDS}
            and not re.match(r"^(do not|never|avoid|no)\b", normalized, re.I)
            and lowered not in allowed
        ):
            terms.append(normalized)
    return terms



def _replace_product_attributes(text: str, allowed: str) -> str:
    """Normalize product adjectives/predicates without editing surrounding props or action state."""
    words = [*COLOR_WORDS, *MATERIAL_WORDS, *PATTERN_WORDS]
    attributes = "|".join(re.escape(word) for word in words)
    product = r"(?:product|bottle|cup|tumbler|thermos|mug|container|lid|cap|label|packaging)"
    blocked = {word for word in words if not re.search(rf"\b{word}\b", allowed, re.I)}

    def replace_attribute(match: re.Match[str]) -> str:
        return "target-product" if match.group().lower() in blocked else match.group()

    result = re.sub(
        rf"\b(?:{attributes})\b(?=\s+(?:(?:{attributes})\s+)*{product}\b)",
        replace_attribute, text, flags=re.I,
    )
    # Restrict predicate spans to attribute/state words and their connectors.
    # A new subject or location ('the background', 'on a wood table') ends the
    # span, so its color/material never inherits the product's identity role.
    states = r"open|closed|sealed|unsealed|full|empty|upright|tilted|wet|dry"
    modifiers = r"and|or|still|now|fully|partly|partially|mostly|very"
    descriptors = rf"(?:{attributes}|{states}|{modifiers})"
    predicate = re.compile(
        rf"(?P<prefix>\b{product}(?:['’]s)?"
        r"(?:\s+(?:body|color|colour|material|texture|pattern|finish))?\s+"
        r"(?:(?:is|are|was|were|remains?|looks?|appears?|stays?|becomes?)\s+"
        r"(?:(?:made|constructed|manufactured)\s+(?:of|from)\s+)?"
        r"|(?:made|constructed|manufactured)\s+(?:of|from)\s+)(?:an?\s+)?)"
        rf"(?P<description>{descriptors}\b(?:(?:\s+|,\s*){descriptors}\b)*)",
        flags=re.I,
    )

    def replace_predicate(match: re.Match[str]) -> str:
        description = re.sub(
            rf"\b(?:{attributes})\b", replace_attribute, match["description"], flags=re.I,
        )
        return match["prefix"] + description

    return predicate.sub(replace_predicate, result)

def sanitize_reference_product_text(*, text: str, analysis: dict[str, Any], product_lock: dict[str, Any]) -> str:
    result = text
    for term in _forbidden_literal_terms(analysis, product_lock):
        result = re.sub(rf"\b{re.escape(term)}\b", "the product", result, flags=re.I)
    result = _replace_product_attributes(result, _allowed_product_text(product_lock))
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
    shots = timeline.get("shots")
    timeline_shots = shots if isinstance(shots, list) else []
    if timeline.get("visualStructure") == "continuous" and len(timeline_shots) <= 1 and re.search(r"\b(hard cut|jump cut|rapid cut|smash cut)\b", video_prompt, re.I):
        raise SmartRemakeError("Continuous structure contains hard-cut instructions.", "COMPILER_OUTPUT_INVALID")


def sanitize_generation_scene(
    scene: dict[str, Any], analysis: dict[str, Any], product_lock: dict[str, Any]
) -> dict[str, Any]:
    """Copy and normalize every creative field, including nested action/state data."""
    def clean(value: Any) -> Any:
        if isinstance(value, str):
            return sanitize_reference_product_text(
                text=value, analysis=analysis, product_lock=product_lock
            )
        if isinstance(value, dict):
            return {key: clean(item) for key, item in value.items() if key != "forbiddenReuse"}
        if isinstance(value, list):
            return [clean(item) for item in value]
        return copy.deepcopy(value)

    return cast(dict[str, Any], clean(scene))


def validate_generation_payload(
    payload: Any, analysis: dict[str, Any], product_lock: dict[str, Any]
) -> None:
    """Fail closed on source identity remaining anywhere in the final creative payload."""
    text = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)
    for term in _forbidden_literal_terms(analysis, product_lock):
        if re.search(rf"\b{re.escape(term)}\b", text, re.I):
            raise SmartRemakeError(
                "Source product identity remains in generation directions. Update the analysis.",
                "COMPILER_OUTPUT_INVALID",
            )
    if _replace_product_attributes(text, _allowed_product_text(product_lock)) != text:
        raise SmartRemakeError(
            "Product attributes conflict with the target identity. Update the analysis.",
            "COMPILER_OUTPUT_INVALID",
        )


def sanitize_generation_requirements(
    requirements: dict[str, Any], analysis: dict[str, Any], product_lock: dict[str, Any]
) -> dict[str, Any]:
    """Preserve saved intent while giving negative/replacement identities an explicit role."""
    saved = copy.deepcopy(requirements)
    for field, replacement in (
        ("forbid", "source product identity"), ("replace", "source product")
    ):
        values = saved.get(field)
        if not isinstance(values, list):
            continue
        projected = []
        for value in values:
            text = value
            if isinstance(text, str):
                for term in _forbidden_literal_terms(analysis, product_lock):
                    text = re.sub(rf"\b{re.escape(term)}\b", replacement, text, flags=re.I)
            projected.append(text)
        saved[field] = projected
    # Keep/intent/claims conflicts must be resolved, never silently rewritten.
    validate_generation_payload(saved, analysis, product_lock)
    return saved
