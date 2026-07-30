from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from viraldy.modules.campaign_packs.public import CompiledRequirementV2
from viraldy.modules.media_analysis.public import EvidenceItemModel
from viraldy.modules.preflight.contracts import RequirementEvaluationV2

_PUNCTUATION = re.compile(r"[^\w\s]+", re.UNICODE)
_SPACE = re.compile(r"\s+")
_PROOF_TYPES = {
    "before_after": {"before", "after", "before_after"},
    "visual_result": {"visual", "result", "visible", "finish"},
    "demonstration": {"demonstration", "demo", "use", "usage"},
    "testimonial": {"testimonial", "review", "story"},
    "measurement": {"measurement", "measured", "number"},
    "comparison": {"comparison", "compare", "versus", "vs"},
}


@dataclass(frozen=True, slots=True)
class RequirementMatcherContext:
    requirement: CompiledRequirementV2
    evidence: list[EvidenceItemModel]
    structural_result: dict[str, Any]
    product_snapshot: dict[str, object] | None = None
    media_duration_ms: int | None = None


@dataclass(frozen=True, slots=True)
class EvidenceFacts:
    grouped: dict[str, list[EvidenceItemModel]]

    @classmethod
    def from_evidence(cls, evidence: list[EvidenceItemModel]) -> EvidenceFacts:
        grouped: dict[str, list[EvidenceItemModel]] = {}
        for item in evidence:
            grouped.setdefault(item.evidence_type, []).append(item)
        return cls(grouped)

    def items(self, *evidence_types: str) -> list[EvidenceItemModel]:
        found: list[EvidenceItemModel] = []
        for evidence_type in evidence_types:
            found.extend(self.grouped.get(evidence_type, []))
        return sorted(found, key=lambda item: (item.start_ms is None, item.start_ms or 0))

    def first(self, *evidence_types: str) -> EvidenceItemModel | None:
        items = self.items(*evidence_types)
        return items[0] if items else None


def evaluate_requirement(context: RequirementMatcherContext) -> RequirementEvaluationV2:
    facts = EvidenceFacts.from_evidence(context.evidence)
    matcher = context.requirement.matcher_type
    if matcher == "prohibited_claim_absence":
        return _prohibited_claim_absence(context, facts)
    if matcher == "required_disclosure_presence":
        return _required_text_presence(context, facts, _all_text_items(facts))
    if matcher == "allowed_claim_qualification":
        return _allowed_claim_qualification(context, facts)
    if matcher == "product_visibility":
        return _product_visibility(context, facts)
    if matcher == "product_visibility_timing":
        return _product_visibility_timing(context, facts)
    if matcher == "product_match":
        return _product_match(context, facts)
    if matcher == "product_in_use":
        return _product_in_use(context, facts)
    if matcher == "demo_presence":
        return _demo_presence(context, facts)
    if matcher == "demo_mechanism_match":
        return _demo_mechanism_match(context, facts)
    if matcher == "proof_presence":
        return _proof_presence(context, facts)
    if matcher == "proof_type_match":
        return _proof_type_match(context, facts)
    if matcher == "overlay_text_presence":
        return _required_text_presence(context, facts, _overlay_text_items(facts))
    if matcher == "spoken_text_presence":
        return _required_text_presence(context, facts, _spoken_text_items(facts))
    if matcher == "hook_semantic_match":
        return _hook_semantic_match(context, facts)
    if matcher == "cta_presence":
        return _cta_presence(context, facts)
    if matcher == "cta_type_match":
        return _cta_type_match(context, facts)
    if matcher == "cta_timing":
        return _cta_timing(context, facts)
    if matcher == "product_tag_presence":
        return _product_tag_presence(context, facts)
    if matcher == "offer_presence":
        return _offer_presence(context, facts)
    if matcher == "offer_text_match":
        return _required_text_presence(context, facts, _offer_text_items(facts))
    if matcher == "offer_before_cta":
        return _offer_before_cta(context, facts)
    if matcher == "creator_style_match":
        return _creator_style_match(context, facts)
    return _evaluation(
        context.requirement,
        "unknown",
        40,
        "low",
        "No deterministic matcher exists for this requirement type.",
        [],
        expected=context.requirement.matcher_config,
        observed={"matcher_type": matcher},
    )


def _prohibited_claim_absence(
    context: RequirementMatcherContext, facts: EvidenceFacts
) -> RequirementEvaluationV2:
    requirement = context.requirement
    expected_text = _expected_text(requirement)
    items = _all_text_items(facts)
    match = _best_text_match(expected_text, items)
    if match is not None:
        item, observed_text, overlap = match
        return _evaluation(
            requirement,
            "violated",
            0,
            "high",
            "Prohibited claim text was observed.",
            [item.id],
            expected={"text": expected_text, "semantics": "absence"},
            observed={"text": observed_text, "token_overlap": overlap},
        )
    return _absence_success_or_unknown(requirement, items, expected_text)


def _required_text_presence(
    context: RequirementMatcherContext,
    facts: EvidenceFacts,
    items: list[tuple[EvidenceItemModel, str]],
) -> RequirementEvaluationV2:
    requirement = context.requirement
    expected_text = _expected_text(requirement)
    if not expected_text:
        return _evaluation(
            requirement,
            "unknown",
            40,
            "low",
            "Text requirement has no expected text.",
            [],
            expected=requirement.matcher_config,
            observed={},
        )
    match = _best_text_match(expected_text, items)
    if match is not None:
        item, observed_text, overlap = match
        return _evaluation(
            requirement,
            "satisfied",
            100,
            "high",
            "Required text was observed in an exact evidence source.",
            [item.id],
            expected={"text": expected_text},
            observed={"text": observed_text, "token_overlap": overlap, "source": item.source},
        )
    if not items:
        return _evaluation(
            requirement,
            "unknown",
            40,
            "low",
            "No eligible text evidence exists for this requirement.",
            [],
            expected={"text": expected_text},
            observed={"available_text_sources": 0},
        )
    return _evaluation(
        requirement,
        "missing",
        0,
        "high",
        "Required text was not observed in the eligible evidence sources.",
        [],
        expected={"text": expected_text},
        observed={"available_text_sources": len(items), "sample": [text for _, text in items[:3]]},
    )


def _allowed_claim_qualification(
    context: RequirementMatcherContext, facts: EvidenceFacts
) -> RequirementEvaluationV2:
    requirement = context.requirement
    claim_text = _clean_text(requirement.matcher_config.get("claim_text"))
    qualification_text = _clean_text(requirement.matcher_config.get("qualification_text"))
    text_items = _all_text_items(facts)
    claim_match = _best_text_match(claim_text, text_items) if claim_text else None
    claim_items = facts.items("claim_signal")
    matching_claim_signal = next(
        (
            item
            for item in claim_items
            if claim_text and text_matches(claim_text, _clean_text(item.value_json.get("text")))
        ),
        None,
    )
    if claim_match is None and matching_claim_signal is None:
        return _evaluation(
            requirement,
            "not_applicable",
            100,
            "high" if text_items else "low",
            "Allowed claim was not present, so qualification was not required.",
            [],
            expected={"claim_text": claim_text, "qualification_text": qualification_text},
            observed={"claim_present": False},
        )
    if matching_claim_signal is not None and bool(
        matching_claim_signal.value_json.get("qualification_present")
    ):
        return _evaluation(
            requirement,
            "satisfied",
            100,
            "high",
            "Claim evidence explicitly indicates qualification is present.",
            [matching_claim_signal.id],
            expected={"claim_text": claim_text, "qualification_text": qualification_text},
            observed={"claim_present": True, "qualification_present": True},
        )
    qualification_match = (
        _best_text_match(qualification_text, text_items) if qualification_text else None
    )
    if qualification_match is not None:
        evidence_ids = []
        if claim_match is not None:
            evidence_ids.append(claim_match[0].id)
        evidence_ids.append(qualification_match[0].id)
        return _evaluation(
            requirement,
            "satisfied",
            100,
            "high",
            "Claim and required qualification text were both observed.",
            evidence_ids,
            expected={"claim_text": claim_text, "qualification_text": qualification_text},
            observed={
                "claim_present": True,
                "qualification_text": qualification_match[1],
            },
        )
    evidence_ids = []
    if claim_match is not None:
        evidence_ids.append(claim_match[0].id)
    if matching_claim_signal is not None:
        evidence_ids.append(matching_claim_signal.id)
    return _evaluation(
        requirement,
        "violated",
        0,
        "high",
        "Allowed-with-qualification claim was present without the required qualification.",
        evidence_ids,
        expected={"claim_text": claim_text, "qualification_text": qualification_text},
        observed={"claim_present": True, "qualification_present": False},
    )


def _absence_success_or_unknown(
    requirement: CompiledRequirementV2,
    items: list[tuple[EvidenceItemModel, str]],
    expected_text: str,
) -> RequirementEvaluationV2:
    if not items:
        return _evaluation(
            requirement,
            "unknown",
            40,
            "low",
            "No text evidence exists to prove prohibited claim absence.",
            [],
            expected={"text": expected_text, "semantics": "absence"},
            observed={"available_text_sources": 0},
        )
    return _evaluation(
        requirement,
        "satisfied",
        100,
        "high",
        "Prohibited claim was absent from eligible text evidence.",
        [],
        expected={"text": expected_text, "semantics": "absence"},
        observed={"available_text_sources": len(items)},
    )


def _product_visibility(
    context: RequirementMatcherContext, facts: EvidenceFacts
) -> RequirementEvaluationV2:
    requirement = context.requirement
    summary = facts.first("product_visibility_summary")
    appearances = facts.items("product_appearance", "product_first_appearance")
    first_ms = _first_product_ms(facts)
    if first_ms is None and not appearances:
        return _evaluation(
            requirement,
            "missing",
            0,
            "high",
            "No product visibility evidence was observed.",
            [],
            expected=requirement.matcher_config,
            observed={"first_appearance_ms": None},
        )
    evidence_id = summary.id if summary else appearances[0].id
    value = summary.value_json if summary else appearances[0].value_json
    visibility = _clean_text(value.get("visibility"))
    clear = bool(
        value.get("clear_close_up_present")
        or value.get("shot_type") in {"hero", "close_up", "in_use"}
        or visibility == "clear"
    )
    status = "satisfied" if clear else "partial"
    return _evaluation(
        requirement,
        status,
        100 if clear else 65,
        "medium",
        "Product visibility was evaluated from direct product appearance evidence.",
        [evidence_id],
        expected=requirement.matcher_config,
        observed={"first_appearance_ms": first_ms, "visibility": visibility or None},
    )


def _product_visibility_timing(
    context: RequirementMatcherContext, facts: EvidenceFacts
) -> RequirementEvaluationV2:
    requirement = context.requirement
    before_ms = _int_config(requirement, "before_ms") or _int_config(
        requirement, "expected_before_ms"
    )
    first_ms = _first_product_ms(facts)
    evidence = _product_evidence_ids(facts)
    if before_ms is None:
        return _product_visibility(context, facts)
    if first_ms is None:
        return _evaluation(
            requirement,
            "missing",
            0,
            "high",
            "Product timing could not be satisfied because no first appearance was observed.",
            [],
            expected={"before_ms": before_ms},
            observed={"first_appearance_ms": None},
        )
    satisfied = first_ms <= before_ms
    return _evaluation(
        requirement,
        "satisfied" if satisfied else "missing",
        100 if satisfied else 0,
        "high",
        "Product first appearance was compared directly against the brief deadline.",
        evidence,
        expected={"before_ms": before_ms},
        observed={"first_appearance_ms": first_ms},
    )


def _product_match(
    context: RequirementMatcherContext, facts: EvidenceFacts
) -> RequirementEvaluationV2:
    requirement = context.requirement
    if context.product_snapshot is None:
        return _evaluation(
            requirement,
            "not_applicable",
            100,
            "high",
            "Product match is only evaluated when a product snapshot is supplied.",
            [],
            expected=requirement.matcher_config,
            observed={"product_snapshot_present": False},
        )
    appearances = facts.items("product_appearance")
    confidences: list[float] = []
    for item in appearances:
        confidence = _float_or_none(item.value_json.get("product_match_confidence"))
        if confidence is not None:
            confidences.append(confidence)
    if not confidences:
        return _evaluation(
            requirement,
            "unknown",
            40,
            "low",
            "No product match confidence was available in product appearance evidence.",
            [item.id for item in appearances],
            expected=requirement.matcher_config,
            observed={"product_match_confidence": None},
        )
    best = max(confidences)
    if best >= 0.70:
        status, score = "satisfied", 100
    elif best >= 0.40:
        status, score = "partial", 60
    else:
        status, score = "violated", 0
    return _evaluation(
        requirement,
        status,
        score,
        "high",
        "Observed product match confidence was compared against deterministic thresholds.",
        [item.id for item in appearances],
        expected=requirement.matcher_config,
        observed={"product_match_confidence": best},
    )


def _product_in_use(
    context: RequirementMatcherContext, facts: EvidenceFacts
) -> RequirementEvaluationV2:
    requirement = context.requirement
    evidence_ids: list[UUID] = []
    usage = False
    for item in facts.items("product_appearance"):
        if bool(item.value_json.get("usage_visible")):
            usage = True
            evidence_ids.append(item.id)
    summary = facts.first("product_visibility_summary")
    if summary is not None and bool(summary.value_json.get("usage_present")):
        usage = True
        evidence_ids.append(summary.id)
    for item in facts.items("demo_step"):
        if bool(item.value_json.get("product_visible")):
            usage = True
            evidence_ids.append(item.id)
    return _evaluation(
        requirement,
        "satisfied" if usage else "missing",
        100 if usage else 0,
        "high" if evidence_ids else "medium",
        "Product-in-use was evaluated from appearance summary and demo step evidence.",
        evidence_ids,
        expected=requirement.matcher_config,
        observed={"usage_visible": usage},
    )


def _demo_presence(
    context: RequirementMatcherContext, facts: EvidenceFacts
) -> RequirementEvaluationV2:
    requirement = context.requirement
    summary = facts.first("demo_summary", "demo_signal")
    steps = facts.items("demo_step")
    detected = bool(steps) or (
        summary is not None and bool(summary.value_json.get("detected", True))
    )
    evidence = [item.id for item in ([summary] if summary else []) + steps]
    return _evaluation(
        requirement,
        "satisfied" if detected else "missing",
        100 if detected else 0,
        "high" if evidence else "medium",
        "Demo presence was evaluated from demo summary and step evidence.",
        evidence,
        expected=requirement.matcher_config,
        observed={"demo_detected": detected, "step_count": len(steps)},
    )


def _demo_mechanism_match(
    context: RequirementMatcherContext, facts: EvidenceFacts
) -> RequirementEvaluationV2:
    requirement = context.requirement
    expected_text = _expected_text(requirement)
    demo_items: list[tuple[EvidenceItemModel, str]] = []
    for item in facts.items("demo_step"):
        demo_items.append((item, _clean_text(item.value_json.get("action"))))
    for item in facts.items("demo_summary", "demo_signal"):
        demo_items.append((item, _clean_text(item.value_json.get("demo_type"))))
        demo_items.append((item, _clean_text(item.value_json.get("mechanism_clarity"))))
    demo_items.extend(_spoken_text_items(facts))
    demo_items.extend(_overlay_text_items(facts))
    if not expected_text:
        return _demo_presence(context, facts)
    match = _best_text_match(expected_text, demo_items)
    if match is not None:
        return _evaluation(
            requirement,
            "satisfied",
            100,
            "high",
            "Expected demo mechanism matched direct demo or text evidence.",
            [match[0].id],
            expected={"text": expected_text},
            observed={"text": match[1], "token_overlap": match[2]},
        )
    if facts.items("demo_summary", "demo_signal", "demo_step"):
        return _evaluation(
            requirement,
            "missing",
            0,
            "high",
            "A demo was present, but the expected mechanism was not observed.",
            [item.id for item, _ in demo_items[:5]],
            expected={"text": expected_text},
            observed={"demo_text": [text for _, text in demo_items[:5] if text]},
        )
    return _evaluation(
        requirement,
        "missing",
        0,
        "medium",
        "No demo evidence was observed for the required mechanism.",
        [],
        expected={"text": expected_text},
        observed={"demo_present": False},
    )


def _proof_presence(
    context: RequirementMatcherContext, facts: EvidenceFacts
) -> RequirementEvaluationV2:
    requirement = context.requirement
    items = facts.items("proof_signal")
    if not items:
        return _evaluation(
            requirement,
            "missing",
            0,
            "high",
            "No proof evidence was observed.",
            [],
            expected=requirement.matcher_config,
            observed={"proof_present": False},
        )
    expected_text = _expected_text(requirement)
    if expected_text:
        match = _best_text_match(
            expected_text,
            [(item, _clean_text(item.value_json.get("description"))) for item in items],
        )
        if match is not None:
            return _evaluation(
                requirement,
                "satisfied",
                100,
                "high",
                "Proof description matched the expected proof direction.",
                [match[0].id],
                expected={"text": expected_text},
                observed={"text": match[1], "token_overlap": match[2]},
            )
        return _evaluation(
            requirement,
            "partial",
            60,
            "medium",
            "Proof exists, but the expected proof semantics did not match directly.",
            [item.id for item in items],
            expected={"text": expected_text},
            observed={
                "proof_descriptions": [
                    _clean_text(item.value_json.get("description")) for item in items
                ]
            },
        )
    return _evaluation(
        requirement,
        "satisfied",
        100,
        "high",
        "Proof evidence was observed.",
        [item.id for item in items],
        expected=requirement.matcher_config,
        observed={"proof_count": len(items)},
    )


def _proof_type_match(
    context: RequirementMatcherContext, facts: EvidenceFacts
) -> RequirementEvaluationV2:
    requirement = context.requirement
    expected_text = _expected_text(requirement)
    expected_types = _expected_proof_types(expected_text)
    items = facts.items("proof_signal")
    observed_types = {_clean_text(item.value_json.get("proof_type")) for item in items}
    matched = bool(expected_types.intersection(observed_types))
    if matched:
        return _evaluation(
            requirement,
            "satisfied",
            100,
            "high",
            "Observed proof type matched the Campaign Pack requirement.",
            [
                item.id
                for item in items
                if _clean_text(item.value_json.get("proof_type")) in expected_types
            ],
            expected={"proof_types": sorted(expected_types)},
            observed={"proof_types": sorted(observed_types)},
        )
    if items:
        return _evaluation(
            requirement,
            "missing",
            0,
            "high",
            "Proof exists, but the required proof type was not observed.",
            [item.id for item in items],
            expected={"proof_types": sorted(expected_types)},
            observed={"proof_types": sorted(observed_types)},
        )
    return _proof_presence(context, facts)


def _hook_semantic_match(
    context: RequirementMatcherContext, facts: EvidenceFacts
) -> RequirementEvaluationV2:
    requirement = context.requirement
    expected_text = _expected_text(requirement)
    hook_items: list[tuple[EvidenceItemModel, str]] = []
    for item in facts.items("hook_signal"):
        for key in ("spoken_text", "overlay_text", "visual_description", "buyer_pain", "hook_type"):
            hook_items.append((item, _clean_text(item.value_json.get(key))))
    hook_items.extend(_spoken_text_items(facts))
    hook_items.extend(_overlay_text_items(facts))
    match = _best_text_match(expected_text, hook_items) if expected_text else None
    if match is not None:
        return _evaluation(
            requirement,
            "satisfied",
            100,
            "high",
            "Hook requirement matched opening evidence.",
            [match[0].id],
            expected={"text": expected_text},
            observed={"text": match[1], "token_overlap": match[2]},
        )
    if facts.items("hook_signal"):
        return _evaluation(
            requirement,
            "missing",
            0,
            "high",
            "Opening hook exists, but required semantics were not observed.",
            [item.id for item in facts.items("hook_signal")],
            expected={"text": expected_text},
            observed={"hook_text": [text for _, text in hook_items[:5] if text]},
        )
    return _evaluation(
        requirement,
        "missing",
        0,
        "medium",
        "No hook evidence was observed.",
        [],
        expected={"text": expected_text},
        observed={"hook_present": False},
    )


def _cta_presence(
    context: RequirementMatcherContext, facts: EvidenceFacts
) -> RequirementEvaluationV2:
    requirement = context.requirement
    items = facts.items("cta_signal")
    return _evaluation(
        requirement,
        "satisfied" if items else "missing",
        100 if items else 0,
        "high" if items else "medium",
        "CTA presence was evaluated from CTA signal evidence.",
        [item.id for item in items],
        expected=requirement.matcher_config,
        observed={"cta_present": bool(items), "cta_count": len(items)},
    )


def _cta_type_match(
    context: RequirementMatcherContext, facts: EvidenceFacts
) -> RequirementEvaluationV2:
    requirement = context.requirement
    expected_type = _clean_text(requirement.matcher_config.get("cta_type"))
    items = facts.items("cta_signal")
    observed_types = [_clean_text(item.value_json.get("cta_type")) for item in items]
    matched = expected_type in observed_types if expected_type else bool(items)
    return _evaluation(
        requirement,
        "satisfied" if matched else "missing",
        100 if matched else 0,
        "high" if items else "medium",
        "CTA type was compared directly against CTA signal evidence.",
        [
            item.id
            for item in items
            if _clean_text(item.value_json.get("cta_type")) == expected_type
        ],
        expected={"cta_type": expected_type},
        observed={"cta_types": observed_types},
    )


def _cta_timing(
    context: RequirementMatcherContext, facts: EvidenceFacts
) -> RequirementEvaluationV2:
    requirement = context.requirement
    required_before_ms = _int_config(requirement, "required_before_ms")
    items = facts.items("cta_signal")
    first_cta_ms = _first_start_ms(items)
    if required_before_ms is None:
        duration = context.media_duration_ms or _media_duration_from_structural(
            context.structural_result
        )
        required_before_ms = round(duration * 0.9) if duration else None
    if first_cta_ms is None:
        return _evaluation(
            requirement,
            "missing",
            0,
            "high",
            "CTA timing failed because no CTA was observed.",
            [],
            expected={"required_before_ms": required_before_ms},
            observed={"first_cta_ms": None},
        )
    if required_before_ms is None:
        return _evaluation(
            requirement,
            "unknown",
            40,
            "low",
            "CTA timing could not be evaluated without a deadline or media duration.",
            [item.id for item in items],
            expected={},
            observed={"first_cta_ms": first_cta_ms},
        )
    satisfied = first_cta_ms <= required_before_ms
    return _evaluation(
        requirement,
        "satisfied" if satisfied else "missing",
        100 if satisfied else 0,
        "high",
        "CTA first appearance was compared directly against the required deadline.",
        [item.id for item in items],
        expected={"required_before_ms": required_before_ms},
        observed={"first_cta_ms": first_cta_ms},
    )


def _product_tag_presence(
    context: RequirementMatcherContext, facts: EvidenceFacts
) -> RequirementEvaluationV2:
    requirement = context.requirement
    items = facts.items("cta_signal")
    tagged = [item for item in items if bool(item.value_json.get("product_tag_visible"))]
    return _evaluation(
        requirement,
        "satisfied" if tagged else "missing",
        100 if tagged else 0,
        "high" if items else "medium",
        "Product tag requirement was evaluated from CTA signal evidence.",
        [item.id for item in tagged],
        expected={"product_tag_visible": True},
        observed={"product_tag_visible": bool(tagged)},
    )


def _offer_presence(
    context: RequirementMatcherContext, facts: EvidenceFacts
) -> RequirementEvaluationV2:
    requirement = context.requirement
    items = facts.items("offer_signal")
    return _evaluation(
        requirement,
        "satisfied" if items else "missing",
        100 if items else 0,
        "high" if items else "medium",
        "Offer presence was evaluated from offer signal evidence.",
        [item.id for item in items],
        expected=requirement.matcher_config,
        observed={"offer_present": bool(items), "offer_count": len(items)},
    )


def _offer_before_cta(
    context: RequirementMatcherContext, facts: EvidenceFacts
) -> RequirementEvaluationV2:
    requirement = context.requirement
    offers = facts.items("offer_signal")
    ctas = facts.items("cta_signal")
    first_offer_ms = _first_start_ms(offers)
    first_cta_ms = _first_start_ms(ctas)
    if first_offer_ms is None:
        return _evaluation(
            requirement,
            "missing",
            0,
            "medium",
            "Offer timing failed because no offer was observed.",
            [],
            expected={"offer_before_cta": True},
            observed={"first_offer_ms": None, "first_cta_ms": first_cta_ms},
        )
    if first_cta_ms is None:
        return _evaluation(
            requirement,
            "unknown",
            40,
            "low",
            "Offer timing could not compare against CTA because no CTA was observed.",
            [item.id for item in offers],
            expected={"offer_before_cta": True},
            observed={"first_offer_ms": first_offer_ms, "first_cta_ms": None},
        )
    satisfied = first_offer_ms <= first_cta_ms
    return _evaluation(
        requirement,
        "satisfied" if satisfied else "missing",
        100 if satisfied else 0,
        "high",
        "Offer timing was compared directly against CTA timing.",
        [item.id for item in offers + ctas],
        expected={"offer_before_cta": True},
        observed={"first_offer_ms": first_offer_ms, "first_cta_ms": first_cta_ms},
    )


def _creator_style_match(
    context: RequirementMatcherContext, facts: EvidenceFacts
) -> RequirementEvaluationV2:
    requirement = context.requirement
    creator = facts.first("creator_signal")
    if creator is None:
        return _evaluation(
            requirement,
            "missing",
            0,
            "medium",
            "No creator evidence was observed.",
            [],
            expected=requirement.matcher_config,
            observed={"creator_present": False},
        )
    expected_persona = _clean_text(requirement.matcher_config.get("creator_persona"))
    expected_delivery = _clean_text(requirement.matcher_config.get("delivery_style"))
    observed_persona = _clean_text(creator.value_json.get("creator_persona"))
    observed_delivery = _clean_text(creator.value_json.get("delivery_style"))
    persona_ok = not expected_persona or text_matches(expected_persona, observed_persona)
    delivery_ok = not expected_delivery or expected_delivery == observed_delivery
    if persona_ok and delivery_ok:
        status, score = "satisfied", 100
    elif persona_ok or delivery_ok:
        status, score = "partial", 60
    else:
        status, score = "missing", 0
    return _evaluation(
        requirement,
        status,
        score,
        "high",
        "Creator direction was compared against creator persona and delivery style evidence.",
        [creator.id],
        expected={"creator_persona": expected_persona, "delivery_style": expected_delivery},
        observed={"creator_persona": observed_persona, "delivery_style": observed_delivery},
    )


def text_matches(expected: str, observed: str) -> bool:
    if not expected or not observed:
        return False
    normalized_expected = normalize_text(expected)
    normalized_observed = normalize_text(observed)
    if not normalized_expected or not normalized_observed:
        return False
    if normalized_expected in normalized_observed or normalized_observed in normalized_expected:
        return True
    return token_overlap(expected, observed) >= 0.75


def normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    normalized = normalized.encode("ascii", "ignore").decode("ascii")
    normalized = _PUNCTUATION.sub(" ", normalized.lower())
    return _SPACE.sub(" ", normalized).strip()


def token_overlap(expected: str, observed: str) -> float:
    expected_tokens = set(normalize_text(expected).split())
    observed_tokens = set(normalize_text(observed).split())
    if not expected_tokens or not observed_tokens:
        return 0
    return len(expected_tokens.intersection(observed_tokens)) / len(expected_tokens)


def _best_text_match(
    expected: str,
    items: list[tuple[EvidenceItemModel, str]],
) -> tuple[EvidenceItemModel, str, float] | None:
    best: tuple[EvidenceItemModel, str, float] | None = None
    for item, observed in items:
        text = _clean_text(observed)
        if not text:
            continue
        overlap = token_overlap(expected, text)
        if text_matches(expected, text):
            if best is None or overlap > best[2]:
                best = (item, text, overlap)
    return best


def _all_text_items(facts: EvidenceFacts) -> list[tuple[EvidenceItemModel, str]]:
    items: list[tuple[EvidenceItemModel, str]] = []
    items.extend(_spoken_text_items(facts))
    items.extend(_overlay_text_items(facts))
    items.extend(_cta_text_items(facts))
    items.extend(_offer_text_items(facts))
    for item in facts.items("claim_signal"):
        items.append((item, _clean_text(item.value_json.get("text"))))
    return items


def _spoken_text_items(facts: EvidenceFacts) -> list[tuple[EvidenceItemModel, str]]:
    items = [
        (item, _clean_text(item.value_json.get("text")))
        for item in facts.items("transcript_segment")
    ]
    for item in facts.items("cta_signal", "offer_signal", "hook_signal"):
        if text := _clean_text(item.value_json.get("spoken_text")):
            items.append((item, text))
        elif item.value_json.get("modality") in {"spoken", "mixed"}:
            items.append((item, _clean_text(item.value_json.get("text"))))
    return items


def _overlay_text_items(facts: EvidenceFacts) -> list[tuple[EvidenceItemModel, str]]:
    items = [
        (item, _clean_text(item.value_json.get("text"))) for item in facts.items("on_screen_text")
    ]
    for item in facts.items("cta_signal", "offer_signal", "hook_signal"):
        if text := _clean_text(item.value_json.get("overlay_text")):
            items.append((item, text))
        elif item.value_json.get("modality") in {"overlay", "mixed"}:
            items.append((item, _clean_text(item.value_json.get("text"))))
    return items


def _cta_text_items(facts: EvidenceFacts) -> list[tuple[EvidenceItemModel, str]]:
    items: list[tuple[EvidenceItemModel, str]] = []
    for item in facts.items("cta_signal"):
        for key in ("text", "spoken_text", "overlay_text"):
            items.append((item, _clean_text(item.value_json.get(key))))
    return items


def _offer_text_items(facts: EvidenceFacts) -> list[tuple[EvidenceItemModel, str]]:
    items: list[tuple[EvidenceItemModel, str]] = []
    for item in facts.items("offer_signal"):
        for key in ("text", "spoken_text", "overlay_text", "price_text", "discount_text"):
            items.append((item, _clean_text(item.value_json.get(key))))
    return items


def _expected_text(requirement: CompiledRequirementV2) -> str:
    return _clean_text(
        requirement.matcher_config.get("text")
        or requirement.matcher_config.get("claim_text")
        or requirement.description
    )


def _expected_proof_types(text: str) -> set[str]:
    normalized = normalize_text(text)
    expected: set[str] = set()
    for proof_type, tokens in _PROOF_TYPES.items():
        if tokens.intersection(normalized.split()):
            expected.add(proof_type)
    return expected or {"unknown"}


def _first_product_ms(facts: EvidenceFacts) -> int | None:
    summary = facts.first("product_visibility_summary")
    if summary is not None:
        value = summary.value_json.get("first_appearance_ms")
        if isinstance(value, int | float):
            return int(value)
    appearance = facts.first("product_appearance", "product_first_appearance")
    if appearance is not None:
        return appearance.start_ms
    return None


def _product_evidence_ids(facts: EvidenceFacts) -> list[UUID]:
    return [item.id for item in facts.items("product_visibility_summary", "product_appearance")]


def _first_start_ms(items: list[EvidenceItemModel]) -> int | None:
    starts = [item.start_ms for item in items if item.start_ms is not None]
    return min(starts) if starts else None


def _int_config(requirement: CompiledRequirementV2, key: str) -> int | None:
    value = requirement.matcher_config.get(key)
    return int(value) if isinstance(value, int | float) else None


def _media_duration_from_structural(structural_result: dict[str, Any]) -> int | None:
    value = structural_result.get("media_duration_ms")
    return int(value) if isinstance(value, int | float) else None


def _float_or_none(value: object) -> float | None:
    return float(value) if isinstance(value, int | float) else None


def _clean_text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _evaluation(
    requirement: CompiledRequirementV2,
    status: str,
    score: int,
    confidence: str,
    reason: str,
    evidence_ids: list[UUID],
    *,
    expected: dict[str, object],
    observed: dict[str, object],
) -> RequirementEvaluationV2:
    return RequirementEvaluationV2(
        requirement_id=requirement.id,
        status=status,
        score=max(0, min(100, score)),
        confidence=confidence,
        reason=reason,
        evidence_ids=list(dict.fromkeys(evidence_ids)),
        expected=expected,
        observed=observed,
    )
