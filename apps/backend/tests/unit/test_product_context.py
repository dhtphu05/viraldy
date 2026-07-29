from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from viraldy.modules.products.contracts import (
    CommercialContextV1,
    ProductContextV1,
    build_minimal_product_context,
)


def test_minimal_product_context_does_not_fabricate_domain_facts() -> None:
    context = build_minimal_product_context(
        name="Test Product",
        description="Existing seller note.",
        market="US",
        metadata_json={},
    )

    assert context.schema_version == "product_context_v1"
    assert context.identity.name == "Test Product"
    assert context.identity.category == "unknown"
    assert context.identity.market == "US"
    assert context.personas == []
    assert context.benefits == []
    assert context.features == []
    assert context.governance.claims == []


def test_product_context_rejects_extra_fields() -> None:
    payload = build_minimal_product_context(
        name="Test Product",
        description=None,
        market=None,
    ).model_dump(mode="json")
    payload["fabricated_benefit"] = "viral orders"

    with pytest.raises(ValidationError):
        ProductContextV1.model_validate(payload)


def test_commercial_context_rejects_negative_values() -> None:
    with pytest.raises(ValidationError):
        CommercialContextV1(price=Decimal("-1"))
