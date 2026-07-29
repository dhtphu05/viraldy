from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CompiledRequirementV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    requirement_type: str
    source_path: str
    description: str
    severity: Literal["hard", "high", "medium", "low"]
    matcher_type: str
    matcher_config: dict[str, object] = Field(default_factory=dict)


def compile_requirements(brief_json: dict[str, object]) -> list[CompiledRequirementV1]:
    requirements: list[CompiledRequirementV1] = []
    for index, item in enumerate(_must_show_items(brief_json.get("must_show")), start=1):
        matcher_type = _matcher_for_requirement(item["requirement_type"], item["description"])
        requirements.append(
            CompiledRequirementV1(
                id=item["id"] or f"must_show_{index}",
                requirement_type=item["requirement_type"],
                source_path=item["source_path"] or f"must_show[{index - 1}]",
                description=item["description"],
                severity=item["severity"],
                matcher_type=matcher_type,
                matcher_config={
                    "text": item["description"],
                    "expected_before_ms": item["expected_before_ms"],
                },
            )
        )
    cta = brief_json.get("cta")
    if isinstance(cta, dict):
        product_tag_required = bool(cta.get("product_tag_required"))
        required_before_ms = cta.get("required_before_ms")
        requirements.append(
            CompiledRequirementV1(
                id="cta_required",
                requirement_type="cta",
                source_path="cta",
                description="CTA must be present before the final moment.",
                severity="hard" if product_tag_required else "high",
                matcher_type="cta_presence",
                matcher_config={
                    "product_tag_required": product_tag_required,
                    "required_before_ms": required_before_ms
                    if isinstance(required_before_ms, int)
                    else None,
                },
            )
        )
    claim_guardrails = brief_json.get("claim_guardrails")
    prohibited_claims = []
    if isinstance(claim_guardrails, dict):
        prohibited_claims.extend(_list_of_text(claim_guardrails.get("prohibited")))
        prohibited_claims.extend(_list_of_text(claim_guardrails.get("required_disclosures")))
    prohibited_claims.extend(_list_of_text(brief_json.get("claims_to_avoid")))
    for index, claim in enumerate(prohibited_claims, start=1):
        requirements.append(
            CompiledRequirementV1(
                id=f"prohibited_claim_{index}",
                requirement_type="claim",
                source_path=f"claim_guardrails[{index - 1}]",
                description=f"Do not include prohibited claim: {claim}",
                severity="hard",
                matcher_type="claim_safety",
                matcher_config={"text": claim},
            )
        )
    if not requirements:
        requirements.append(
            CompiledRequirementV1(
                id="baseline_product_visibility",
                requirement_type="product",
                source_path="system.baseline_product_visibility",
                description="Product must be visible enough to evaluate the UGC.",
                severity="hard",
                matcher_type="product_visibility",
            )
        )
    return requirements


def _must_show_items(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    items: list[dict[str, object]] = []
    for index, item in enumerate(value, start=1):
        if isinstance(item, dict):
            description = _clean_text(item.get("description"))
            if not description:
                continue
            requirement_type = _requirement_type(item.get("requirement_type"), description)
            items.append(
                {
                    "id": _clean_text(item.get("id")) or f"must_show_{index}",
                    "requirement_type": requirement_type,
                    "source_path": _clean_text(item.get("source_path"))
                    or f"must_show[{index - 1}]",
                    "description": description,
                    "severity": _severity(item.get("severity")),
                    "expected_before_ms": item.get("expected_before_ms")
                    if isinstance(item.get("expected_before_ms"), int)
                    else None,
                }
            )
            continue
        description = _clean_text(item)
        if description:
            matcher_type = _matcher_for_text(description)
            items.append(
                {
                    "id": f"must_show_{index}",
                    "requirement_type": _requirement_type_for_matcher(matcher_type),
                    "source_path": f"must_show[{index - 1}]",
                    "description": description,
                    "severity": "high",
                    "expected_before_ms": None,
                }
            )
    return items


def _matcher_for_requirement(requirement_type: object, description: str) -> str:
    type_text = _clean_text(requirement_type)
    return {
        "cta": "cta_presence",
        "demo": "demo_presence",
        "proof": "proof_presence",
        "product": "product_visibility",
        "claim": "claim_safety",
    }.get(type_text, _matcher_for_text(description))


def _requirement_type(value: object, description: str) -> str:
    text = _clean_text(value)
    if text in {
        "product",
        "demo",
        "proof",
        "offer",
        "cta",
        "overlay",
        "creator",
        "scene",
        "claim",
    }:
        return text
    return _requirement_type_for_matcher(_matcher_for_text(description))


def _severity(value: object) -> Literal["hard", "high", "medium", "low"]:
    text = _clean_text(value)
    if text in {"hard", "high", "medium", "low"}:
        return text  # type: ignore[return-value]
    return "high"


def compiled_requirements_to_json(
    requirements: list[CompiledRequirementV1],
) -> dict[str, object]:
    return {
        "schema_version": "compiled_requirements_v1",
        "requirements": [item.model_dump(mode="json") for item in requirements],
    }


def _matcher_for_text(text: str) -> str:
    lowered = text.lower()
    if "cta" in lowered or "shop" in lowered or "tag" in lowered:
        return "cta_presence"
    if "demo" in lowered or "use" in lowered or "using" in lowered:
        return "demo_presence"
    if "before" in lowered or "after" in lowered or "result" in lowered or "proof" in lowered:
        return "proof_presence"
    if "product" in lowered or "close-up" in lowered or "close up" in lowered:
        return "product_visibility"
    return "semantic_presence_unknown"


def _requirement_type_for_matcher(matcher_type: str) -> str:
    return {
        "cta_presence": "cta",
        "demo_presence": "demo",
        "proof_presence": "proof",
        "product_visibility": "product",
        "claim_safety": "claim",
    }.get(matcher_type, "scene")


def _list_of_text(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [text for item in value if (text := _clean_text(item))]


def _clean_text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""
