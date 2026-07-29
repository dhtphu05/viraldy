from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from viraldy.modules.products.contracts import (
    CommercialContextV1,
    ProductContextV1,
    ProductIdentityV1,
    build_minimal_product_context,
)
from viraldy.modules.products.schemas import CreateProductRequest
from viraldy.modules.products.service import _context_for_create, _validate_projection
from viraldy.shared.errors.base import AppError


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


def test_create_context_uses_context_identity_as_projection_source() -> None:
    context = build_minimal_product_context(
        name="Context Name",
        description=None,
        market="US",
    )
    request = CreateProductRequest(name="Context Name", market="US", product_context=context)

    created_context = _context_for_create(request)

    assert created_context.identity.name == "Context Name"
    assert created_context.identity.market == "US"


def test_projection_validation_rejects_conflicting_name_or_market() -> None:
    context = build_minimal_product_context(
        name="Context Name",
        description=None,
        market="US",
    )

    with pytest.raises(AppError):
        _validate_projection(context, "Different Name", "US")
    with pytest.raises(AppError):
        _validate_projection(context, "Context Name", "CA")


def test_top_level_projection_can_sync_context_identity() -> None:
    context = build_minimal_product_context(
        name="Old Name",
        description=None,
        market="US",
    )
    identity = context.identity.model_copy(update={"name": "New Name", "market": "CA"})
    updated_context = context.model_copy(
        update={"identity": ProductIdentityV1.model_validate(identity)}
    )

    assert updated_context.identity.name == "New Name"
    assert updated_context.identity.market == "CA"
