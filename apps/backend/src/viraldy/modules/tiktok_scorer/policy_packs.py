from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from viraldy.modules.tiktok_scorer.contracts_v2 import RuleClassV1

SourceTierV1 = Literal[
    "A_OFFICIAL",
    "B_CORROBORATED",
    "C_COMMUNITY_SIGNAL",
    "D_INTERNAL_HYPOTHESIS",
]
UnknownBehaviorV1 = Literal[
    "unknown",
    "not_applicable",
    "request_better_media",
    "expert_review",
]

HARD_BLOCK_RULE_CLASSES = frozenset(
    {
        "official_hard_rule",
        "product_governance_rule",
        "operational_hard_constraint",
    }
)


class PolicyContractV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PolicyRuleV1(PolicyContractV1):
    code: str = Field(min_length=1, max_length=160)
    pack_code: str = Field(min_length=1, max_length=160)
    pack_version: str = Field(min_length=1, max_length=80)
    source_tier: SourceTierV1
    rule_class: RuleClassV1
    applicability: str = Field(min_length=1)
    required_inputs: list[str]
    unknown_behavior: UnknownBehaviorV1
    exceptions: list[str]
    can_hard_block: bool
    fix_template_code: str = Field(min_length=1, max_length=160)
    effective_at: datetime
    expires_at: datetime | None
    provenance_source_ids: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_rule_authority(self) -> Self:
        if self.effective_at.tzinfo is None:
            raise ValueError("policy rule effective_at must be timezone-aware")
        if self.expires_at is not None:
            if self.expires_at.tzinfo is None:
                raise ValueError("policy rule expires_at must be timezone-aware")
            if self.expires_at <= self.effective_at:
                raise ValueError("policy rule expiry must follow its effective time")
        if self.can_hard_block and self.rule_class not in HARD_BLOCK_RULE_CLASSES:
            raise ValueError(
                "only official, product-governance, or operational rules can hard-block"
            )
        if self.can_hard_block and self.source_tier in {
            "C_COMMUNITY_SIGNAL",
            "D_INTERNAL_HYPOTHESIS",
        }:
            raise ValueError("community signals and internal hypotheses cannot hard-block")
        if self.rule_class == "official_hard_rule" and self.source_tier != "A_OFFICIAL":
            raise ValueError("official hard rules require an official source")
        return self

    def is_active_at(self, moment: datetime) -> bool:
        if moment.tzinfo is None:
            raise ValueError("policy evaluation time must be timezone-aware")
        return self.effective_at <= moment and (self.expires_at is None or moment < self.expires_at)


class PolicyPackV1(PolicyContractV1):
    code: str = Field(min_length=1, max_length=160)
    version: str = Field(min_length=1, max_length=80)
    source_tier: SourceTierV1
    effective_at: datetime
    expires_at: datetime | None
    rules: list[PolicyRuleV1] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_pack(self) -> Self:
        rule_codes = [rule.code for rule in self.rules]
        if len(rule_codes) != len(set(rule_codes)):
            raise ValueError("policy rule codes must be unique within a pack")
        for rule in self.rules:
            if rule.pack_code != self.code or rule.pack_version != self.version:
                raise ValueError("policy rules must identify their containing pack and version")
            if rule.source_tier != self.source_tier:
                raise ValueError("policy rule source tier must match its pack")
        return self


def can_create_hard_block(rule: PolicyRuleV1) -> bool:
    return (
        rule.can_hard_block
        and rule.rule_class in HARD_BLOCK_RULE_CLASSES
        and rule.source_tier in {"A_OFFICIAL", "B_CORROBORATED"}
    )


def resolve_policy_rules(
    packs: list[PolicyPackV1],
    *,
    evaluation_at: datetime,
    completed_at: datetime | None = None,
) -> tuple[PolicyRuleV1, ...]:
    """Resolve rules at the run's immutable time, pinning completed-run overlays."""

    effective_time = completed_at or evaluation_at
    if effective_time.tzinfo is None:
        raise ValueError("policy evaluation time must be timezone-aware")
    return tuple(
        rule
        for pack in sorted(packs, key=lambda item: (item.code, item.version))
        for rule in pack.rules
        if rule.is_active_at(effective_time)
    )


_EFFECTIVE = datetime(2026, 1, 1, tzinfo=UTC)
_TREND_EXPIRY = datetime(2027, 1, 1, tzinfo=UTC)


def _rule(
    *,
    code: str,
    pack_code: str,
    pack_version: str,
    source_tier: SourceTierV1,
    rule_class: RuleClassV1,
    applicability: str,
    required_inputs: list[str],
    unknown_behavior: UnknownBehaviorV1,
    exceptions: list[str],
    can_hard_block: bool,
    fix_template_code: str,
    provenance_source_ids: list[str],
    expires_at: datetime | None = None,
) -> PolicyRuleV1:
    return PolicyRuleV1(
        code=code,
        pack_code=pack_code,
        pack_version=pack_version,
        source_tier=source_tier,
        rule_class=rule_class,
        applicability=applicability,
        required_inputs=required_inputs,
        unknown_behavior=unknown_behavior,
        exceptions=exceptions,
        can_hard_block=can_hard_block,
        fix_template_code=fix_template_code,
        effective_at=_EFFECTIVE,
        expires_at=expires_at,
        provenance_source_ids=provenance_source_ids,
    )


def _pack(
    *,
    code: str,
    version: str,
    source_tier: SourceTierV1,
    rules: list[PolicyRuleV1],
    expires_at: datetime | None = None,
) -> PolicyPackV1:
    return PolicyPackV1(
        code=code,
        version=version,
        source_tier=source_tier,
        effective_at=_EFFECTIVE,
        expires_at=expires_at,
        rules=rules,
    )


TIKTOK_US_OFFICIAL_POLICY_PACK = _pack(
    code="tiktok_us_official_policy_pack",
    version="2026.1",
    source_tier="A_OFFICIAL",
    rules=[
        _rule(
            code="TT_US_UNSUPPORTED_PRODUCT_CLAIM",
            pack_code="tiktok_us_official_policy_pack",
            pack_version="2026.1",
            source_tier="A_OFFICIAL",
            rule_class="official_hard_rule",
            applicability="A commerce claim is visible or spoken in a US-market video.",
            required_inputs=["claim evidence", "verified Product Context"],
            unknown_behavior="expert_review",
            exceptions=["The claim is explicitly supported by verified Product Context."],
            can_hard_block=True,
            fix_template_code="REPLACE_UNSUPPORTED_CLAIM",
            provenance_source_ids=["tiktok-us-commerce-policy"],
        )
    ],
)

TIKTOK_US_CREATIVE_GUIDELINE_PACK = _pack(
    code="tiktok_us_creative_guideline_pack",
    version="2026.1",
    source_tier="A_OFFICIAL",
    rules=[
        _rule(
            code="TT_US_CONTEXTUAL_SAFE_ZONE",
            pack_code="tiktok_us_creative_guideline_pack",
            pack_version="2026.1",
            source_tier="A_OFFICIAL",
            rule_class="contextual_guideline",
            applicability="Important text is observed near a platform UI region.",
            required_inputs=["safe-zone observation"],
            unknown_behavior="not_applicable",
            exceptions=["The selected placement declares a stricter official requirement."],
            can_hard_block=False,
            fix_template_code="MOVE_TEXT_TO_SAFE_ZONE",
            provenance_source_ids=["tiktok-creative-codes-us"],
        )
    ],
)

TIKTOK_2026_TREND_OVERLAY = _pack(
    code="tiktok_2026_trend_overlay",
    version="2026.1",
    source_tier="C_COMMUNITY_SIGNAL",
    expires_at=_TREND_EXPIRY,
    rules=[
        _rule(
            code="TT_2026_REALNESS_DIRECTION",
            pack_code="tiktok_2026_trend_overlay",
            pack_version="2026.1",
            source_tier="C_COMMUNITY_SIGNAL",
            rule_class="directional_pattern",
            applicability="A current US TikTok format is evaluated as optional direction.",
            required_inputs=["market", "observation time", "source", "expiry"],
            unknown_behavior="not_applicable",
            exceptions=["Never treat production roughness alone as authenticity."],
            can_hard_block=False,
            fix_template_code="OPTIONAL_REALNESS_DIRECTION",
            provenance_source_ids=["tiktok-2026-trend-research"],
            expires_at=_TREND_EXPIRY,
        )
    ],
)

FTC_ENDORSEMENT_PACK = _pack(
    code="ftc_endorsement_pack",
    version="2026.1",
    source_tier="A_OFFICIAL",
    rules=[
        _rule(
            code="FTC_REQUIRED_DISCLOSURE_MISSING",
            pack_code="ftc_endorsement_pack",
            pack_version="2026.1",
            source_tier="A_OFFICIAL",
            rule_class="official_hard_rule",
            applicability="A known material connection requires clear, conspicuous disclosure.",
            required_inputs=["intended use", "commercial relationship", "disclosure evidence"],
            unknown_behavior="unknown",
            exceptions=["No material connection exists and Product Context does not require one."],
            can_hard_block=True,
            fix_template_code="ADD_VERIFIED_DISCLOSURE",
            provenance_source_ids=["ftc-endorsement-guides"],
        )
    ],
)

POD_PERSONALIZATION_PACK = _pack(
    code="pod_personalization_pack",
    version="2026.1",
    source_tier="B_CORROBORATED",
    rules=[
        _rule(
            code="POD_PERSONALIZATION_MISMATCH",
            pack_code="pod_personalization_pack",
            pack_version="2026.1",
            source_tier="B_CORROBORATED",
            rule_class="product_governance_rule",
            applicability="Verified personalization is available for a POD product-aware run.",
            required_inputs=["Product Context personalization", "product appearance evidence"],
            unknown_behavior="unknown",
            exceptions=["The video intentionally demonstrates a clearly labeled generic sample."],
            can_hard_block=True,
            fix_template_code="RESHOOT_CORRECT_PERSONALIZATION",
            provenance_source_ids=["pod-product-truth-research"],
        )
    ],
)

DROPSHIPPING_PRODUCT_TRUTH_PACK = _pack(
    code="dropshipping_product_truth_pack",
    version="2026.1",
    source_tier="B_CORROBORATED",
    rules=[
        _rule(
            code="DROPSHIP_PRODUCT_OR_SKU_MISMATCH",
            pack_code="dropshipping_product_truth_pack",
            pack_version="2026.1",
            source_tier="B_CORROBORATED",
            rule_class="product_governance_rule",
            applicability="Product identity is evaluated against an immutable Product Context.",
            required_inputs=["Product Context identity", "product appearance evidence"],
            unknown_behavior="request_better_media",
            exceptions=["Packaging-only footage before a later verified product reveal."],
            can_hard_block=True,
            fix_template_code="RESHOOT_CORRECT_PRODUCT",
            provenance_source_ids=["dropshipping-product-truth-research"],
        )
    ],
)

UGC_CREATOR_WORKFLOW_PACK = _pack(
    code="ugc_creator_workflow_pack",
    version="2026.1",
    source_tier="B_CORROBORATED",
    rules=[
        _rule(
            code="UGC_CRITICAL_MEDIA_UNREADABLE",
            pack_code="ugc_creator_workflow_pack",
            pack_version="2026.1",
            source_tier="B_CORROBORATED",
            rule_class="operational_hard_constraint",
            applicability="The upload cannot provide evidence needed for responsible diagnostics.",
            required_inputs=["media duration", "decode status", "evidence coverage"],
            unknown_behavior="request_better_media",
            exceptions=["No audio is valid when visual or caption evidence remains sufficient."],
            can_hard_block=True,
            fix_template_code="REQUEST_BETTER_MEDIA",
            provenance_source_ids=["ugc-creator-production-workflow"],
        )
    ],
)

AGENCY_DIRECTIONAL_PATTERN_PACK = _pack(
    code="agency_directional_pattern_pack",
    version="2026.1",
    source_tier="C_COMMUNITY_SIGNAL",
    rules=[
        _rule(
            code="AGENCY_MODULAR_FOOTAGE_PREFERENCE",
            pack_code="agency_directional_pattern_pack",
            pack_version="2026.1",
            source_tier="C_COMMUNITY_SIGNAL",
            rule_class="directional_pattern",
            applicability="Reusable evidence-linked footage exists for a cheaper repair.",
            required_inputs=["scene inventory", "continuity and reuse observations"],
            unknown_behavior="not_applicable",
            exceptions=["Physical product truth or required proof is absent."],
            can_hard_block=False,
            fix_template_code="REUSE_EXISTING_FOOTAGE",
            provenance_source_ids=["agency-modular-ugc-research"],
        )
    ],
)

REQUIRED_POLICY_PACKS = {
    pack.code: pack
    for pack in (
        TIKTOK_US_OFFICIAL_POLICY_PACK,
        TIKTOK_US_CREATIVE_GUIDELINE_PACK,
        TIKTOK_2026_TREND_OVERLAY,
        FTC_ENDORSEMENT_PACK,
        POD_PERSONALIZATION_PACK,
        DROPSHIPPING_PRODUCT_TRUTH_PACK,
        UGC_CREATOR_WORKFLOW_PACK,
        AGENCY_DIRECTIONAL_PATTERN_PACK,
    )
}


__all__ = [
    "AGENCY_DIRECTIONAL_PATTERN_PACK",
    "DROPSHIPPING_PRODUCT_TRUTH_PACK",
    "FTC_ENDORSEMENT_PACK",
    "HARD_BLOCK_RULE_CLASSES",
    "POD_PERSONALIZATION_PACK",
    "PolicyPackV1",
    "PolicyRuleV1",
    "REQUIRED_POLICY_PACKS",
    "SourceTierV1",
    "TIKTOK_2026_TREND_OVERLAY",
    "TIKTOK_US_CREATIVE_GUIDELINE_PACK",
    "TIKTOK_US_OFFICIAL_POLICY_PACK",
    "UGC_CREATOR_WORKFLOW_PACK",
    "UnknownBehaviorV1",
    "can_create_hard_block",
    "resolve_policy_rules",
]
