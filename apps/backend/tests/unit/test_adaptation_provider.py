from __future__ import annotations

from uuid import uuid4

import pytest

from viraldy.modules.adaptations.contracts import AdaptationOutputV2
from viraldy.modules.adaptations.provider import _native_adaptation_validator
from viraldy.modules.adaptations.service import _fixture_adaptation
from viraldy.modules.products.contracts import (
    ClaimRuleV1,
    ProductContextV1,
    ProductGovernanceV1,
    ProductIdentityV1,
)
from viraldy.modules.products.public import ProductContextSnapshot


def test_native_adaptation_validator_rejects_unknown_evidence() -> None:
    product = _product()
    allowed_evidence_id = uuid4()
    dna = {"opening": {"hook_text": {"evidence_ids": [str(allowed_evidence_id)]}}}
    output = _fixture_output(product, dna)
    payload = output.model_dump(mode="json")
    payload["concepts"][0]["source_evidence_ids"] = [str(uuid4())]  # type: ignore[index]

    with pytest.raises(ValueError, match="outside Creative DNA"):
        _native_adaptation_validator(product, dna)(
            AdaptationOutputV2.model_validate(payload)
        )


def test_native_adaptation_validator_rejects_dropped_product_guardrail() -> None:
    product = _product()
    dna: dict[str, object] = {}
    output = _fixture_output(product, dna)
    payload = output.model_dump(mode="json")
    payload["concepts"][0]["claim_guardrails"] = []  # type: ignore[index]

    with pytest.raises(ValueError, match="claim guardrails"):
        _native_adaptation_validator(product, dna)(
            AdaptationOutputV2.model_validate(payload)
        )


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
