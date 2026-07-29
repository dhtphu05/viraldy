from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from viraldy.modules.creative_dna.contracts import CreativeDnaV1
from viraldy.modules.creative_domain.schema_versions import ADAPTATION_SCHEMA_VERSION
from viraldy.modules.products.contracts import ProductContextV1


class AdaptationContractBase(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AdaptationConstraintsV2(AdaptationContractBase):
    max_duration_seconds: int | None = Field(default=None, ge=1)
    must_include: list[str] = Field(default_factory=list)
    must_avoid: list[str] = Field(default_factory=list)
    channel_constraints: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class AdaptationInputV2(AdaptationContractBase):
    schema_version: Literal["adaptation_v2"] = ADAPTATION_SCHEMA_VERSION
    product_snapshot: ProductContextV1
    creative_dna: CreativeDnaV1
    objective: str
    target_market: str
    selected_persona_id: str | None = None
    target_buyer: dict[str, object] = Field(default_factory=dict)
    constraints: AdaptationConstraintsV2 = Field(default_factory=AdaptationConstraintsV2)


class AdaptationGuidanceV2(AdaptationContractBase):
    element_type: str
    source_path: str
    action: Literal["keep", "change", "avoid"]
    reason: str
    evidence_ids: list[UUID] = Field(default_factory=list)
    product_context_refs: list[str] = Field(default_factory=list)
    risk_codes: list[str] = Field(default_factory=list)


class AdaptationConceptV2(AdaptationContractBase):
    id: str
    name: str
    strategic_axis: str
    angle: str
    buyer_persona_id: str | None = None
    buyer_persona_label: str
    buyer_pain: str
    desired_outcome: str
    creator_persona: str
    delivery_style: str
    hook_options: list[str]
    opening_visual: str
    demo_mechanism: str
    demo_sequence: list[str]
    proof_mechanism: str
    offer_framing: str | None = None
    cta_strategy: str
    claim_guardrails: list[str]
    must_show: list[str]
    risks: list[dict[str, object]] = Field(default_factory=list)
    test_hypothesis: str
    source_evidence_ids: list[UUID] = Field(default_factory=list)


class AdaptationOutputV2(AdaptationContractBase):
    schema_version: Literal["adaptation_v2"] = ADAPTATION_SCHEMA_VERSION
    guidance: list[AdaptationGuidanceV2]
    concepts: list[AdaptationConceptV2]
    uncertainties: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_concepts(self) -> AdaptationOutputV2:
        if len(self.concepts) != 3:
            raise ValueError("Adaptation output must include exactly three concepts.")
        axes_with_diversity = 0
        axes = [
            [concept.buyer_persona_id or concept.buyer_pain for concept in self.concepts],
            [concept.angle for concept in self.concepts],
            [concept.creator_persona for concept in self.concepts],
            [concept.delivery_style for concept in self.concepts],
            [concept.demo_mechanism for concept in self.concepts],
            [concept.proof_mechanism for concept in self.concepts],
            [concept.offer_framing or "" for concept in self.concepts],
            [concept.strategic_axis for concept in self.concepts],
        ]
        for values in axes:
            if len({value.strip().lower() for value in values if value.strip()}) > 1:
                axes_with_diversity += 1
        if axes_with_diversity < 2:
            raise ValueError("Adaptation concepts must differ on at least two strategy axes.")
        return self
