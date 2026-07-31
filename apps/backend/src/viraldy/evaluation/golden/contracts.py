from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

RequirementStatus = Literal[
    "satisfied",
    "partial",
    "missing",
    "violated",
    "unknown",
    "not_applicable",
]
GoldenAction = Literal["revise", "ready_for_organic", "small_paid_test"]
GoldenDomain = Literal["tiktok_shop_us", "pod", "dropshipping"]


class GoldenContractBase(BaseModel):
    model_config = ConfigDict(extra="forbid")


class GoldenConceptV1(GoldenContractBase):
    concept_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    strategic_axis: str = Field(min_length=1)
    buyer_persona: str = Field(min_length=1)
    creator_persona: str = Field(min_length=1)
    spoken_hook: str = Field(min_length=1)
    overlay_hook: str | None = None
    diversity_axes: list[str] = Field(min_length=2)

    @model_validator(mode="after")
    def validate_personas_and_axes(self) -> GoldenConceptV1:
        if self.buyer_persona.casefold() == self.creator_persona.casefold():
            raise ValueError("buyer_persona and creator_persona must remain separate")
        if len(set(self.diversity_axes)) != len(self.diversity_axes):
            raise ValueError("diversity_axes must be unique")
        return self


class GoldenAssetV1(GoldenContractBase):
    asset_id: str = Field(min_length=1)
    asset_role: Literal["reference", "ugc_draft", "ugc_revision", "edge_case"]
    has_audio: bool
    duration_ms: int = Field(gt=0)
    observations: dict[str, object] = Field(default_factory=dict)


class GoldenPreflightV1(GoldenContractBase):
    asset_id: str = Field(min_length=1)
    action: GoldenAction
    product_required_before_ms: int | None = Field(default=None, ge=0)
    product_first_appearance_ms: int | None = Field(default=None, ge=0)
    disclosure_status: RequirementStatus = "not_applicable"
    proof_status: RequirementStatus = "not_applicable"
    product_tag_status: RequirementStatus = "not_applicable"
    hard_blocker_codes: list[str] = Field(default_factory=list)
    high_priority_fix_codes: list[str] = Field(default_factory=list)
    personalization_expected: str | None = None
    personalization_observed: str | None = None
    prohibited_claims_observed: list[str] = Field(default_factory=list)
    strengths_to_preserve: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_action(self) -> GoldenPreflightV1:
        if self.action != "revise" and self.hard_blocker_codes:
            raise ValueError("an approvable action cannot contain hard blockers")
        return self


class GoldenFixtureV1(GoldenContractBase):
    schema_version: Literal["golden_fixture_v1"] = "golden_fixture_v1"
    scenario_id: str = Field(min_length=1)
    domain: GoldenDomain
    product_name: str = Field(min_length=1)
    objective: str = Field(min_length=1)
    pattern_name: str = Field(min_length=1)
    concepts: list[GoldenConceptV1] = Field(min_length=3, max_length=3)
    assets: list[GoldenAssetV1] = Field(min_length=1)
    preflight_expectations: list[GoldenPreflightV1] = Field(default_factory=list)
    required_disclosures: list[str] = Field(default_factory=list)
    prohibited_claims: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_fixture_identity(self) -> GoldenFixtureV1:
        concept_ids = [concept.concept_id for concept in self.concepts]
        if len(set(concept_ids)) != 3:
            raise ValueError("golden concepts must have three unique concept IDs")
        asset_ids = [asset.asset_id for asset in self.assets]
        if len(set(asset_ids)) != len(asset_ids):
            raise ValueError("golden assets must have unique IDs")
        if not {item.asset_id for item in self.preflight_expectations}.issubset(
            set(asset_ids)
        ):
            raise ValueError("preflight expectations must reference fixture assets")
        return self


class GoldenSemanticOutputV1(GoldenContractBase):
    scenario_id: str
    product_name: str
    objective: str
    pattern_name: str
    concepts: list[GoldenConceptV1]
    preflight_results: list[GoldenPreflightV1] = Field(default_factory=list)
    performance_evidence_attached: bool = False
    performance_label: str | None = None

    @model_validator(mode="after")
    def validate_performance_claim(self) -> GoldenSemanticOutputV1:
        if self.performance_label and not self.performance_evidence_attached:
            raise ValueError("performance labels require attached performance evidence")
        return self


class GoldenValidationCheckV1(GoldenContractBase):
    check: str
    passed: bool
    detail: str


class GoldenValidationReportV1(GoldenContractBase):
    scenario_id: str
    passed: bool
    checks: list[GoldenValidationCheckV1]
