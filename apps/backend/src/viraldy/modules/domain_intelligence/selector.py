from __future__ import annotations

from collections.abc import Sequence

from viraldy.modules.domain_intelligence.schemas import (
    DomainRule,
    NormalizedEvidenceBundle,
    UGCReviewContext,
)


def select_applicable_rules(
    rules: Sequence[DomainRule],
    context: UGCReviewContext,
    evidence: NormalizedEvidenceBundle,
) -> list[DomainRule]:
    evidence_kinds = {item.kind for item in evidence.items}
    explicit_rule_codes = {
        str(item.value["rule_code"])
        for item in evidence.items
        if item.value.get("rule_code")
    }
    selected = [
        rule
        for rule in rules
        if rule.enabled_for_mvp
        and _is_applicable(rule, context, evidence_kinds, explicit_rule_codes)
    ]
    return sorted(selected, key=lambda rule: rule.code)


def _is_applicable(
    rule: DomainRule,
    context: UGCReviewContext,
    evidence_kinds: set[str],
    explicit_rule_codes: set[str],
) -> bool:
    code = rule.code
    if code in explicit_rule_codes:
        return True
    if code.startswith("SYS-"):
        return True
    if code == "UGC-REV-002":
        return bool(context.creator_brief)
    if code == "UGC-RIGHTS-001":
        return context.intended_use in {"paid_candidate", "spark_candidate"}
    if code == "DISC-001":
        return context.material_connection != "no" or "disclosure" in evidence_kinds
    if code in {"PERF-PREFLIGHT-001", "PERF-TIME-001"}:
        return True
    if code.startswith("POD-"):
        return context.commerce_domain == "pod_personalization"
    if code.startswith("DROP-"):
        if context.commerce_domain != "dropshipping":
            return False
        if code == "DROP-SHIP-001":
            return bool(
                {"shipping_claim", "claim"}.intersection(evidence_kinds)
                or context.verified_shipping_language
            )
        return True
    if code == "FTC-SHIP-001":
        return bool(
            {"shipping_claim", "claim"}.intersection(evidence_kinds)
            or context.verified_shipping_language
        )
    if code == "TT-CONTENT-001":
        return bool(
            context.exact_variant_or_sku
            or {"product_identity", "product_appearance"}.intersection(evidence_kinds)
        )
    if code == "TT-CLAIM-001":
        return bool({"claim", "shipping_claim"}.intersection(evidence_kinds))
    if code in {"TT-OFFER-001", "TT-URGENCY-001"}:
        return bool(context.current_offer or "offer" in evidence_kinds)
    if rule.domain == "tiktok_shop_us":
        return context.platform == "tiktok_shop"
    if rule.domain == "pod_personalization":
        return context.commerce_domain == "pod_personalization"
    if rule.domain == "dropshipping":
        return context.commerce_domain == "dropshipping"
    return True
