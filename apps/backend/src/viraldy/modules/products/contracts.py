from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from viraldy.modules.creative_domain.schema_versions import PRODUCT_CONTEXT_SCHEMA_VERSION

AwarenessStageV1 = Literal[
    "unaware",
    "problem_aware",
    "solution_aware",
    "product_aware",
    "most_aware",
    "unknown",
]
ClaimStrengthV1 = Literal["observed", "supported", "subjective", "unknown"]
MarginBandV1 = Literal["low", "medium", "high", "unknown"]
ClaimRuleTypeV1 = Literal[
    "allowed",
    "allowed_with_qualification",
    "prohibited",
    "required_disclosure",
]
SeverityV1 = Literal["low", "medium", "high", "critical"]


class ProductContractBase(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProductIdentityV1(ProductContractBase):
    name: str = Field(min_length=1, max_length=255)
    brand: str | None = None
    category: str = Field(default="unknown", min_length=1, max_length=120)
    subcategory: str | None = None
    variant: str | None = None
    market: str = Field(default="unknown", min_length=1, max_length=100)
    currency: str | None = None


class BuyerPersonaV1(ProductContractBase):
    id: str = Field(min_length=1, max_length=120)
    label: str = Field(min_length=1, max_length=160)
    description: str | None = None
    pain_points: list[str] = Field(default_factory=list)
    desired_outcomes: list[str] = Field(default_factory=list)
    objections: list[str] = Field(default_factory=list)
    awareness_stage: AwarenessStageV1 = "unknown"


class ProductBenefitV1(ProductContractBase):
    id: str = Field(min_length=1, max_length=120)
    label: str = Field(min_length=1, max_length=160)
    description: str
    proof_available: list[str] = Field(default_factory=list)
    claim_strength: ClaimStrengthV1 = "unknown"


class ProductFeatureV1(ProductContractBase):
    id: str = Field(min_length=1, max_length=120)
    label: str = Field(min_length=1, max_length=160)
    description: str | None = None
    visual_demo_possible: bool = False
    visual_cues: list[str] = Field(default_factory=list)


class CommercialContextV1(ProductContractBase):
    price: Decimal | None = None
    compare_at_price: Decimal | None = None
    discount_text: str | None = None
    bundle_text: str | None = None
    shipping_text: str | None = None
    commission_percent: Decimal | None = None
    margin_band: MarginBandV1 = "unknown"
    offer_notes: list[str] = Field(default_factory=list)

    @field_validator("price", "compare_at_price", "commission_percent")
    @classmethod
    def non_negative_decimal(cls, value: Decimal | None) -> Decimal | None:
        if value is not None and value < 0:
            raise ValueError("commercial decimal fields must be non-negative")
        return value


class CreativeContextV1(ProductContractBase):
    primary_angles: list[str] = Field(default_factory=list)
    demonstration_mechanisms: list[str] = Field(default_factory=list)
    visual_differentiators: list[str] = Field(default_factory=list)
    available_proof: list[str] = Field(default_factory=list)
    creator_personas: list[str] = Field(default_factory=list)
    preferred_delivery_styles: list[str] = Field(default_factory=list)
    brand_voice: list[str] = Field(default_factory=list)
    prohibited_visuals: list[str] = Field(default_factory=list)
    required_product_reveal_before_ms: int | None = Field(default=None, ge=0)
    required_proof_mechanisms: list[str] = Field(default_factory=list)


class PersonalizationFieldV1(ProductContractBase):
    key: str = Field(min_length=1, max_length=120)
    label: str = Field(min_length=1, max_length=160)
    expected_value: str = Field(min_length=1, max_length=500)
    case_sensitive: bool = False
    visual_verification_required: bool = True


class ProductPersonalizationV1(ProductContractBase):
    required: bool = False
    fields: list[PersonalizationFieldV1] = Field(default_factory=list)
    physical_sample_required: bool = False
    ordering_instructions: list[str] = Field(default_factory=list)
    production_constraints: list[str] = Field(default_factory=list)
    delivery_constraints: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_required_fields(self) -> ProductPersonalizationV1:
        keys = [field.key for field in self.fields]
        if len(set(keys)) != len(keys):
            raise ValueError("personalization field keys must be unique")
        if self.required and not self.fields:
            raise ValueError("required personalization needs at least one field")
        return self


class ClaimRuleV1(ProductContractBase):
    id: str = Field(min_length=1, max_length=120)
    text: str = Field(min_length=1)
    rule_type: ClaimRuleTypeV1
    qualification: str | None = None
    severity: SeverityV1 = "medium"


class ProductGovernanceV1(ProductContractBase):
    claims: list[ClaimRuleV1] = Field(default_factory=list)
    required_disclosures: list[str] = Field(default_factory=list)
    prohibited_content: list[str] = Field(default_factory=list)
    rights_notes: list[str] = Field(default_factory=list)


class ProductContextV1(ProductContractBase):
    schema_version: Literal["product_context_v1"] = PRODUCT_CONTEXT_SCHEMA_VERSION
    identity: ProductIdentityV1
    personas: list[BuyerPersonaV1] = Field(default_factory=list)
    benefits: list[ProductBenefitV1] = Field(default_factory=list)
    features: list[ProductFeatureV1] = Field(default_factory=list)
    commercial: CommercialContextV1 = Field(default_factory=CommercialContextV1)
    creative: CreativeContextV1 = Field(default_factory=CreativeContextV1)
    personalization: ProductPersonalizationV1 = Field(default_factory=ProductPersonalizationV1)
    governance: ProductGovernanceV1 = Field(default_factory=ProductGovernanceV1)


def build_minimal_product_context(
    *,
    name: str,
    description: str | None,
    market: str | None,
    metadata_json: dict[str, object] | None = None,
) -> ProductContextV1:
    metadata = metadata_json or {}
    identity = ProductIdentityV1(
        name=name,
        brand=_optional_text(metadata.get("brand")),
        category=_text_or_unknown(metadata.get("category")),
        subcategory=_optional_text(metadata.get("subcategory")),
        variant=_optional_text(metadata.get("variant")),
        market=_text_or_unknown(market or metadata.get("market")),
        currency=_optional_text(metadata.get("currency")),
    )
    creative_notes = [_clean_text(description)] if _clean_text(description) else []
    return ProductContextV1(
        identity=identity,
        creative=CreativeContextV1(primary_angles=creative_notes),
    )


def product_context_to_json(context: ProductContextV1) -> dict[str, object]:
    return context.model_dump(mode="json")


def validate_product_context(value: ProductContextV1 | dict[str, object]) -> ProductContextV1:
    if isinstance(value, ProductContextV1):
        return value
    return ProductContextV1.model_validate(value)


def _optional_text(value: object) -> str | None:
    text = _clean_text(value)
    return text or None


def _text_or_unknown(value: object) -> str:
    return _clean_text(value) or "unknown"


def _clean_text(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()
