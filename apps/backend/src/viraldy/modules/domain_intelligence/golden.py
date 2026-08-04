from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from pydantic import BaseModel, ConfigDict

from viraldy.modules.domain_intelligence.schemas import (
    NormalizedEvidence,
    NormalizedEvidenceBundle,
    UGCReviewContext,
)


class FixtureArtifactMissingError(FileNotFoundError):
    pass


class GoldenCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    title: str
    raw_payload: dict[str, object]


def load_golden_cases(path: Path | str) -> list[GoldenCase]:
    fixture_path = _fixture_path(path)
    try:
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Golden Cases fixture is malformed: {fixture_path}: {exc}") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("golden_cases"), list):
        raise ValueError(f"Golden Cases fixture has an invalid contract: {fixture_path}")
    cases = cast(list[dict[str, object]], payload["golden_cases"])
    return [
        GoldenCase(
            case_id=str(case["case_id"]),
            title=str(case["title"]),
            raw_payload=case,
        )
        for case in cases
    ]


def load_semantic_regression_cases(path: Path | str) -> list[dict[str, object]]:
    fixture_path = _fixture_path(path)
    cases: list[dict[str, object]] = []
    for line_number, line in enumerate(fixture_path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"semantic regression fixture is malformed at line {line_number}: {exc}"
            ) from exc
        if not isinstance(payload, dict):
            raise ValueError(
                f"semantic regression fixture line {line_number} must contain an object"
            )
        cases.append(cast(dict[str, object], payload))
    if not cases:
        raise ValueError(f"semantic regression fixture contains no cases: {fixture_path}")
    return cases


def golden_case_to_review_input(
    case: GoldenCase,
) -> tuple[UGCReviewContext, NormalizedEvidenceBundle]:
    payload = case.raw_payload
    product = cast(dict[str, object], payload.get("verified_product_context") or {})
    campaign = cast(dict[str, object], payload.get("creative_campaign_pack") or {})
    requirements = cast(list[dict[str, object]], payload.get("compiled_requirements") or [])
    expected = cast(list[dict[str, object]], payload.get("preflight_expected_vs_observed") or [])
    rule_by_requirement = {
        str(requirement.get("id")): _first_rule_code(str(requirement.get("source") or ""))
        for requirement in requirements
    }
    evidence = [
        NormalizedEvidence(
            id=f"{case.case_id}:{record.get('requirement_id', index)}",
            kind="expected_vs_observed",
            source="policy",
            observed=(
                f"Expected: {record.get('expected', 'unknown')}. "
                f"Observed: {record.get('observed', 'unknown')}."
            ),
            confidence=("medium" if "unknown" in str(record.get("status")) else "high"),
            value={
                **record,
                "rule_code": rule_by_requirement.get(str(record.get("requirement_id"))),
            },
        )
        for index, record in enumerate(expected)
    ]
    context = UGCReviewContext(
        market=str(product.get("market") or "US"),
        commerce_domain=_commerce_domain(case.case_id),
        intended_use="spark_candidate",
        product_name=_optional_text(product.get("product_name")),
        exact_variant_or_sku=_optional_text(product.get("sku")),
        product_description=_optional_text(product.get("mechanism")),
        current_offer=_optional_text(product.get("fixture_price_usd")),
        approved_personalization=_optional_text(product.get("sample_personalization")),
        physical_sample_available=_physical_sample_available(product),
        creator_brief=_optional_text(campaign.get("creator_brief")),
        material_connection="yes",
    )
    pattern = cast(dict[str, object], payload.get("patternkit_candidate") or {})
    strengths = [str(value) for value in cast(list[object], pattern.get("keep") or [])]
    return context, NormalizedEvidenceBundle(
        items=evidence,
        coverage={"visual_observations": True, "brief": True},
        strengths=strengths,
        metadata={
            "economics_missing": bool(payload.get("missing_economic_or_rights_inputs")),
            "golden_case_id": case.case_id,
        },
        pipeline_version="golden_fixture_v1",
    )


def _fixture_path(path: Path | str) -> Path:
    fixture_path = Path(path)
    if not fixture_path.is_file():
        raise FixtureArtifactMissingError(f"required fixture artifact is missing: {fixture_path}")
    return fixture_path


def _commerce_domain(case_id: str) -> str:
    if case_id.startswith("GC-POD"):
        return "pod_personalization"
    if case_id.startswith("GC-DROP"):
        return "dropshipping"
    return "tiktok_shop_us"


def _first_rule_code(source: str) -> str | None:
    for token in source.replace("/", " ").split():
        if "-" in token and token.upper() == token:
            return token.strip(".,")
    if "Campaign Pack" in source:
        return "PERF-TIME-001"
    if "PatternKit" in source or "selected PatternKit" in source:
        return "PERF-PREFLIGHT-001"
    return None


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _physical_sample_available(product: dict[str, object]) -> bool | None:
    status = str(
        product.get("physical_sample_status") or product.get("exact_sample_status") or ""
    ).lower()
    if not status:
        return None
    return "verified" in status
