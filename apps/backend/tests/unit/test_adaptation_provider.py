from __future__ import annotations

from uuid import uuid4

import pytest

from viraldy.modules.adaptations.contracts import AdaptationOutputV2
from viraldy.modules.adaptations.provider import (
    _native_adaptation_validator,
    normalize_adaptation_output,
)
from viraldy.modules.adaptations.service import _fixture_adaptation
from viraldy.modules.products.contracts import (
    ClaimRuleV1,
    ProductContextV1,
    ProductGovernanceV1,
    ProductIdentityV1,
)
from viraldy.modules.products.public import ProductContextSnapshot


def test_native_adaptation_validator_prunes_unknown_evidence() -> None:
    product = _product()
    allowed_evidence_id = uuid4()
    dna = {"opening": {"hook_text": {"evidence_ids": [str(allowed_evidence_id)]}}}
    output = _fixture_output(product, dna)
    payload = output.model_dump(mode="json")
    payload["concepts"][0]["source_evidence_ids"] = [  # type: ignore[index]
        str(allowed_evidence_id),
        str(uuid4()),
    ]

    adaptation = AdaptationOutputV2.model_validate(payload)
    _native_adaptation_validator(product, dna)(adaptation)
    normalized = normalize_adaptation_output(adaptation, product, dna)

    assert normalized.concepts[0].source_evidence_ids == [allowed_evidence_id]


def test_native_adaptation_validator_preserves_product_guardrails() -> None:
    product = _product()
    dna: dict[str, object] = {}
    output = _fixture_output(product, dna)
    payload = output.model_dump(mode="json")
    payload["concepts"][0]["claim_guardrails"] = []  # type: ignore[index]

    adaptation = AdaptationOutputV2.model_validate(payload)
    _native_adaptation_validator(product, dna)(adaptation)
    normalized = normalize_adaptation_output(adaptation, product, dna)

    assert "Works perfectly on every fabric" in normalized.concepts[0].claim_guardrails


def test_native_adaptation_validator_preserves_product_name() -> None:
    product = _product()
    dna: dict[str, object] = {}
    output = _fixture_output(product, dna)
    payload = output.model_dump(mode="json")
    concept = payload["concepts"][0]  # type: ignore[index]
    concept["name"] = "Result opener"
    concept["angle"] = "Lead with the visible result"
    concept["opening_visual"] = "Show the result first"
    concept["demo_mechanism"] = "Demonstrate the core action"
    concept["proof_mechanism"] = "Show observed proof"
    concept["cta_strategy"] = "Ask viewers to check the product card"

    adaptation = AdaptationOutputV2.model_validate(payload)
    _native_adaptation_validator(product, dna)(adaptation)
    normalized = normalize_adaptation_output(adaptation, product, dna)

    assert normalized.concepts[0].name.startswith("SwiftPress Mini Garment Steamer - ")


def test_adaptation_risks_use_a_typed_strict_schema() -> None:
    schema = AdaptationOutputV2.model_json_schema()
    concept_schema = schema["$defs"]["AdaptationConceptV2"]
    risk_items = concept_schema["properties"]["risks"]["items"]

    assert risk_items == {"$ref": "#/$defs/AdaptationRiskV2"}
    assert schema["$defs"]["AdaptationRiskV2"]["additionalProperties"] is False


def _product() -> ProductContextV1:
    return ProductContextV1(
        identity=ProductIdentityV1(
            name="SwiftPress Mini Garment Steamer",
            category="garment_care",
            market="US",
        ),
        governance=ProductGovernanceV1(
            claims=[
                ClaimRuleV1(
                    id="universal_result",
                    text="Works perfectly on every fabric",
                    rule_type="prohibited",
                    severity="critical",
                )
            ]
        ),
    )


def _fixture_output(
    product: ProductContextV1,
    dna: dict[str, object],
) -> AdaptationOutputV2:
    snapshot = ProductContextSnapshot(
        product_id=uuid4(),
        workspace_id=uuid4(),
        context_schema_version=product.schema_version,
        product_context_version=1,
        product_context=product,
    )
    return AdaptationOutputV2.model_validate(
        _fixture_adaptation(snapshot, dna, {})
    )
