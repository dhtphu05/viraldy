# Recommendation copy remains as complete sentences for audit and snapshot readability.
# ruff: noqa: E501

from __future__ import annotations

import re
from collections.abc import Sequence

from viraldy.modules.domain_intelligence.schemas import (
    DomainRule,
    EvaluationCandidate,
    NormalizedEvidence,
    NormalizedEvidenceBundle,
    UGCReviewContext,
)


def evaluate_deterministically(
    context: UGCReviewContext,
    evidence: NormalizedEvidenceBundle,
    rules: Sequence[DomainRule],
) -> list[EvaluationCandidate]:
    rule_codes = {rule.code for rule in rules}
    candidates: list[EvaluationCandidate] = []
    candidates.extend(_expected_vs_observed(evidence.items, rule_codes))
    candidates.extend(_product_identity(context, evidence.items, rule_codes))
    candidates.extend(_personalization(context, evidence.items, rule_codes))
    candidates.extend(_offer(context, evidence.items, rule_codes))
    candidates.extend(_urgency(evidence.items, rule_codes))
    candidates.extend(_claims(evidence.items, rule_codes))
    candidates.extend(_dropshipping_compatibility(context, evidence.items, rule_codes))
    candidates.extend(_shipping(context, evidence.items, rule_codes))
    candidates.extend(_timing(context, evidence.items, rule_codes))
    candidates.extend(_demo(evidence.items, rule_codes))
    candidates.extend(_proof(evidence.items, rule_codes))
    candidates.extend(_creator(evidence.items, rule_codes))
    candidates.extend(_pod_media(context, evidence.items, rule_codes))
    candidates.extend(_disclosure(context, evidence.items, rule_codes))
    candidates.extend(_operational_unknowns(context, evidence, rule_codes))
    return candidates


def _product_identity(
    context: UGCReviewContext,
    items: list[NormalizedEvidence],
    rule_codes: set[str],
) -> list[EvaluationCandidate]:
    expected = _clean(context.exact_variant_or_sku)
    if not expected or "TT-CONTENT-001" not in rule_codes:
        return []
    identities = _items(items, "product_identity")
    if not identities:
        return [
            _confirm(
                rule_code="TT-CONTENT-001",
                mistake_code="M-PROD-001",
                title="Confirm the exact product variant",
                reason=f"The review could not verify the visible product against {expected}.",
                instructions=["Confirm the seller-approved SKU and provide a clear product shot."],
                completion=[
                    "The visible product and seller-approved SKU can be matched confidently."
                ],
                evidence_ids=[],
            )
        ]
    observed = identities[0]
    observed_identity = _clean(observed.value.get("observed_identity") or observed.observed)
    if observed.confidence == "low":
        return [
            _confirm(
                rule_code="TT-CONTENT-001",
                mistake_code="M-PROD-001",
                title="Confirm which product is visible",
                reason="The product identity signal is too uncertain to call a mismatch.",
                instructions=["Provide a closer, well-lit shot of the exact SKU or variant."],
                completion=["The product identity is readable with medium or high confidence."],
                evidence_ids=[observed.id],
                unknown_state="insufficient_evidence",
            )
        ]
    if _matches(expected, observed_identity):
        return []
    return [
        EvaluationCandidate(
            rule_code="TT-CONTENT-001",
            mistake_code="M-PROD-001",
            group="fix_first",
            title="Reshoot with the exact seller-approved product",
            reason=f"The seller expects {expected}, while the draft clearly shows {observed_identity}.",
            why_it_matters="The draft, product tag and listing should describe the same item.",
            owner="creator",
            fix_type="reshoot_scene",
            instructions=[
                f"Replace the mismatched shot with the exact {expected} product.",
                "Keep any usable creator delivery, audio and surrounding footage unchanged.",
            ],
            strengths_to_preserve=["Keep the usable creator delivery and unaffected footage."],
            completion_criteria=[f"The exact {expected} variant is clearly visible."],
            evidence_ids=[observed.id],
            confidence="high",
        )
    ]


def _personalization(
    context: UGCReviewContext,
    items: list[NormalizedEvidence],
    rule_codes: set[str],
) -> list[EvaluationCandidate]:
    expected = _clean(context.approved_personalization)
    if not expected or "POD-PERS-001" not in rule_codes:
        return []
    signals = _items(items, "personalization")
    if not signals or signals[0].confidence == "low":
        evidence_ids = [signals[0].id] if signals else []
        return [
            _confirm(
                rule_code="POD-PERS-001",
                mistake_code="M-POD-001",
                title="Confirm the approved personalization",
                reason="The personalized text is not readable enough to verify against seller input.",
                instructions=["Provide a sharp close-up of the finished personalized product."],
                completion=[
                    "The approved personalization is readable in the physical product shot."
                ],
                evidence_ids=evidence_ids,
                unknown_state="insufficient_evidence",
            )
        ]
    signal = signals[0]
    observed = _clean(signal.value.get("observed_personalization") or signal.observed)
    if _matches(expected, observed):
        return []
    return [
        EvaluationCandidate(
            rule_code="POD-PERS-001",
            mistake_code="M-POD-001",
            group="fix_first",
            title="Reshoot the approved personalization",
            reason=f"The approved personalization is {expected}, while the draft shows {observed}.",
            why_it_matters="Personalized content must match the buyer-approved input.",
            owner="creator",
            fix_type="reshoot_scene",
            instructions=[
                "Film the correctly personalized physical sample in a readable close-up."
            ],
            strengths_to_preserve=[
                "Keep the existing unboxing, reaction and unaffected product footage."
            ],
            completion_criteria=[f"The physical sample clearly reads {expected}."],
            evidence_ids=[signal.id],
            confidence="high",
        )
    ]


def _offer(
    context: UGCReviewContext,
    items: list[NormalizedEvidence],
    rule_codes: set[str],
) -> list[EvaluationCandidate]:
    signals = _items(items, "offer")
    expected = _clean(context.current_offer)
    if not signals or "TT-OFFER-001" not in rule_codes:
        return []
    signal = signals[0]
    observed = _clean(
        signal.value.get("price_text")
        or signal.value.get("discount_text")
        or signal.value.get("offer_text")
        or signal.observed
    )
    if not expected:
        return [
            _confirm(
                rule_code="TT-OFFER-001",
                mistake_code="M-OFFER-001",
                title="Confirm the current offer",
                reason=f"The draft shows {observed}, but no current seller offer was provided.",
                instructions=["Confirm the live offer or remove the offer text before use."],
                completion=["The draft offer matches the seller's current offer snapshot."],
                evidence_ids=[signal.id],
            )
        ]
    if signal.confidence == "low":
        return []
    if _matches(expected, observed):
        return []
    return [
        EvaluationCandidate(
            rule_code="TT-OFFER-001",
            mistake_code="M-OFFER-001",
            group="fix_first",
            title="Replace the offer text",
            reason=f"The current seller offer is {expected}, while the draft shows {observed}.",
            why_it_matters="Offer copy should match the current listing when the draft is used.",
            owner="editor",
            fix_type="replace_copy",
            instructions=[
                "Replace the displayed offer with the current seller-approved offer or remove it."
            ],
            strengths_to_preserve=["Keep the product demo and creator delivery around the offer."],
            completion_criteria=[
                "All spoken and on-screen offer language matches the current offer."
            ],
            evidence_ids=[signal.id],
            confidence=signal.confidence,
        )
    ]


def _claims(
    items: list[NormalizedEvidence],
    rule_codes: set[str],
) -> list[EvaluationCandidate]:
    if "TT-CLAIM-001" not in rule_codes:
        return []
    candidates: list[EvaluationCandidate] = []
    for signal in _items(items, "claim"):
        risk = str(signal.value.get("risk") or "").lower()
        category = str(signal.value.get("category") or "").lower()
        text = _clean(signal.value.get("text") or signal.observed)
        absolute = bool(re.search(r"\b(100%|every|always|guaranteed|never)\b", text.lower()))
        if signal.confidence == "low" or (risk not in {"high", "critical"} and not absolute):
            continue
        candidates.append(
            EvaluationCandidate(
                rule_code="TT-CLAIM-001",
                mistake_code="M-CLAIM-001",
                group="fix_first",
                title="Replace the unsupported claim",
                reason=f"The draft includes the unverified {category or 'product'} claim: {text}.",
                why_it_matters="The draft should use only seller-approved, supportable product language.",
                owner="editor",
                fix_type="replace_copy",
                instructions=["Remove the claim or replace it with a seller-approved observation."],
                strengths_to_preserve=[
                    "Keep the underlying demonstration and unaffected creator wording."
                ],
                completion_criteria=["The unsupported wording is absent from speech and overlays."],
                evidence_ids=[signal.id],
                confidence=signal.confidence,
            )
        )
    return candidates


def _urgency(
    items: list[NormalizedEvidence],
    rule_codes: set[str],
) -> list[EvaluationCandidate]:
    if "TT-URGENCY-001" not in rule_codes:
        return []
    signals = [
        item
        for item in _items(items, "offer")
        if item.value.get("urgency_present") is True
        or item.value.get("offer_type") == "limited_time"
    ]
    if not signals:
        return []
    signal = signals[0]
    return [
        _confirm(
            rule_code="TT-URGENCY-001",
            mistake_code="M-OFFER-002",
            title="Confirm the urgency language is current",
            reason="The draft uses urgency or limited-time language that video evidence cannot verify.",
            instructions=["Confirm the urgency is current and supportable, or remove the wording."],
            completion=["All urgency language is current, seller-approved and supportable."],
            evidence_ids=[signal.id],
        )
    ]


def _dropshipping_compatibility(
    context: UGCReviewContext,
    items: list[NormalizedEvidence],
    rule_codes: set[str],
) -> list[EvaluationCandidate]:
    if context.commerce_domain != "dropshipping" or "DROP-COMP-001" not in rule_codes:
        return []
    signals = [
        item
        for item in _items(items, "claim")
        if str(item.value.get("category") or "").lower() in {"comparison", "compatibility"}
    ]
    if not signals:
        return []
    signal = signals[0]
    return [
        _confirm(
            rule_code="DROP-COMP-001",
            mistake_code="M-DROP-001",
            title="Confirm the exact compatible models",
            reason="The draft makes a compatibility claim without verifiable model and condition details.",
            instructions=[
                "Confirm the exact compatible models and conditions, then narrow or remove the claim."
            ],
            completion=["Compatibility wording names only seller-verified models and conditions."],
            evidence_ids=[signal.id],
        )
    ]


def _demo(
    items: list[NormalizedEvidence],
    rule_codes: set[str],
) -> list[EvaluationCandidate]:
    if "PERF-PREFLIGHT-001" not in rule_codes:
        return []
    signals = [
        item
        for item in _items(items, "demo_summary")
        if item.value.get("detected") is True
        and item.value.get("mechanism_clarity") in {"unclear", "partial"}
        and item.confidence != "low"
    ]
    if not signals:
        return []
    signal = signals[0]
    return [
        EvaluationCandidate(
            rule_code="PERF-PREFLIGHT-001",
            mistake_code="M-DEMO-001",
            group="improve",
            title="Make the product mechanism easier to follow",
            reason="The demo is present, but the observed mechanism is partial or unclear.",
            why_it_matters="A clear sequence helps the seller verify what the product actually does.",
            owner="editor",
            fix_type="edit_existing_footage",
            instructions=["Use the clearest existing steps in order and hold on the visible result."],
            strengths_to_preserve=["Keep the usable demo steps and natural creator delivery."],
            completion_criteria=["The mechanism and result can be followed from the footage."],
            evidence_ids=[signal.id],
            confidence=signal.confidence,
        )
    ]


def _proof(
    items: list[NormalizedEvidence],
    rule_codes: set[str],
) -> list[EvaluationCandidate]:
    if "PERF-PREFLIGHT-001" not in rule_codes:
        return []
    signals = [
        item
        for item in _items(items, "proof_signal")
        if item.value.get("verifiability") == "not_observable" and item.confidence != "low"
    ]
    if not signals:
        return []
    signal = signals[0]
    return [
        EvaluationCandidate(
            rule_code="PERF-PREFLIGHT-001",
            mistake_code="M-PROOF-001",
            group="fix_first",
            title="Replace the unsupported proof moment",
            reason="The draft presents a result as proof, but the result is not observable in the footage.",
            why_it_matters="Proof should show an observable result rather than imply an unsupported outcome.",
            owner="creator",
            fix_type="reshoot_scene",
            instructions=["Reshoot only the proof scene so the actual result is continuously visible."],
            strengths_to_preserve=["Keep the unaffected demo, audio and creator delivery."],
            completion_criteria=["The proof moment shows an observable result supported by the footage."],
            evidence_ids=[signal.id],
            confidence=signal.confidence,
        )
    ]


def _creator(
    items: list[NormalizedEvidence],
    rule_codes: set[str],
) -> list[EvaluationCandidate]:
    if "PERF-PREFLIGHT-001" not in rule_codes:
        return []
    signals = [
        item
        for item in _items(items, "creator_signal")
        if item.value.get("delivery_style") == "sales_pitch"
        and item.value.get("sales_language_intensity") == "high"
        and not item.value.get("authenticity_cues")
        and item.confidence != "low"
    ]
    if not signals:
        return []
    signal = signals[0]
    return [
        EvaluationCandidate(
            rule_code="PERF-PREFLIGHT-001",
            mistake_code="M-CREATOR-001",
            group="improve",
            title="Make the creator delivery more natural",
            reason="The observed delivery is a high-intensity sales pitch without clear authenticity cues.",
            why_it_matters="A more natural delivery can make the product explanation easier to trust.",
            owner="creator",
            fix_type="reshoot_scene",
            instructions=["Keep the product facts, but deliver them in the creator's normal voice."],
            strengths_to_preserve=["Keep the useful product facts and any clear demonstration footage."],
            completion_criteria=["The delivery sounds conversational without adding new claims."],
            evidence_ids=[signal.id],
            confidence=signal.confidence,
        )
    ]


def _shipping(
    context: UGCReviewContext,
    items: list[NormalizedEvidence],
    rule_codes: set[str],
) -> list[EvaluationCandidate]:
    signals = _items(items, "shipping_claim")
    applicable_code = next(
        (code for code in ("DROP-SHIP-001", "FTC-SHIP-001") if code in rule_codes),
        None,
    )
    if not signals or not applicable_code:
        return []
    signal = signals[0]
    verified = _clean(context.verified_shipping_language)
    observed = _clean(signal.value.get("shipping_text") or signal.observed)
    if verified and _matches(verified, observed):
        return []
    return [
        EvaluationCandidate(
            rule_code=applicable_code,
            mistake_code="M-SUP-001",
            group="fix_first",
            title="Remove or verify the shipping promise",
            reason="The draft makes a shipping promise without matching verified customer-route language.",
            why_it_matters="Creator sample delivery does not prove the delivery time buyers will receive.",
            owner="editor",
            fix_type="replace_copy",
            instructions=[
                "Confirm the current customer-route shipping language with the seller, or remove the promise."
            ],
            strengths_to_preserve=["Keep the product demonstration and unaffected CTA."],
            completion_criteria=["No unverified delivery time remains in speech or overlays."],
            evidence_ids=[signal.id],
            confidence=signal.confidence,
        )
    ]


def _timing(
    context: UGCReviewContext,
    items: list[NormalizedEvidence],
    rule_codes: set[str],
) -> list[EvaluationCandidate]:
    if "PERF-TIME-001" not in rule_codes:
        return []
    appearances = _items(items, "product_appearance")
    if not appearances:
        return []
    signal = appearances[0]
    first_ms = signal.value.get("first_appearance_ms")
    if not isinstance(first_ms, int):
        first_ms = signal.start_ms
    if first_ms is None:
        return []
    required_ms = _brief_timing_requirement(context.creator_brief)
    if required_ms is not None and first_ms > required_ms:
        return [
            EvaluationCandidate(
                rule_code="PERF-TIME-001",
                mistake_code="M-PROD-002",
                group="fix_first",
                title="Meet the brief's product timing",
                reason=(
                    f"The brief requires the product by {required_ms / 1000:g} seconds, "
                    f"but it appears at {first_ms / 1000:g} seconds."
                ),
                why_it_matters="This is an explicit campaign requirement, not a universal platform rule.",
                owner="editor",
                fix_type="edit_existing_footage",
                instructions=[
                    "Move an existing clear product shot into the required opening window."
                ],
                strengths_to_preserve=[
                    "Keep the creator's strongest delivery and later demo footage."
                ],
                completion_criteria=[
                    f"The product is clearly visible by {required_ms / 1000:g} seconds."
                ],
                evidence_ids=[signal.id],
                confidence=signal.confidence,
            )
        ]
    if required_ms is None and first_ms > 3000:
        return [
            EvaluationCandidate(
                rule_code="PERF-TIME-001",
                mistake_code="M-PROD-002",
                group="improve",
                title="Consider connecting the product earlier",
                reason="The product appears after the opening beat; an earlier connection may improve clarity.",
                why_it_matters="This is a contextual creative suggestion, not a platform requirement.",
                owner="editor",
                fix_type="edit_existing_footage",
                instructions=[
                    "Test an edit that introduces the product earlier if a clear shot already exists."
                ],
                strengths_to_preserve=["Keep the current opening idea and creator delivery."],
                completion_criteria=[
                    "The opening and product role connect without losing the useful hook."
                ],
                evidence_ids=[signal.id],
                confidence=signal.confidence,
            )
        ]
    return []


def _pod_media(
    context: UGCReviewContext,
    items: list[NormalizedEvidence],
    rule_codes: set[str],
) -> list[EvaluationCandidate]:
    if context.commerce_domain != "pod_personalization" or "POD-MOCK-001" not in rule_codes:
        return []
    mockups = [
        item for item in _items(items, "personalization") if item.value.get("mockup_only") is True
    ]
    if not mockups or context.physical_sample_available is not False:
        return []
    return [
        _confirm(
            rule_code="POD-MOCK-001",
            mistake_code="M-POD-002",
            title="Request a physical-sample close-up",
            reason="A digital mockup cannot verify the finished personalization, placement or print quality.",
            instructions=[
                "Request clear footage of the physical personalized sample before making claims."
            ],
            completion=["The physical sample and approved personalization are clearly visible."],
            evidence_ids=[mockups[0].id],
            unknown_state="insufficient_evidence",
            fix_type="request_better_media",
        )
    ]


def _disclosure(
    context: UGCReviewContext,
    items: list[NormalizedEvidence],
    rule_codes: set[str],
) -> list[EvaluationCandidate]:
    if "DISC-001" not in rule_codes or context.material_connection == "no":
        return []
    disclosures = [
        item
        for item in _items(items, "disclosure")
        if item.confidence != "low" and item.value.get("present", True) is not False
    ]
    visible_disclosure_present = any(
        item.source == "ocr"
        or str(item.value.get("modality") or "").lower() in {"visual", "caption", "platform"}
        for item in disclosures
    )
    if visible_disclosure_present:
        return []
    spoken_disclosures = [
        item
        for item in disclosures
        if item.source == "transcript" or str(item.value.get("modality") or "").lower() == "spoken"
    ]
    if spoken_disclosures:
        signal = spoken_disclosures[0]
        return [
            EvaluationCandidate(
                rule_code="DISC-001",
                mistake_code="M-DISC-001",
                group="fix_first",
                title="Add visible disclosure for the target market",
                reason=(
                    "The transcript includes a spoken sponsorship disclosure, but the review "
                    "does not show a visible caption or publish-time disclosure setting."
                ),
                why_it_matters="The commercial relationship should be clear before viewers evaluate the product.",
                owner="editor",
                fix_type="add_overlay",
                instructions=[
                    "Add a seller-approved visible disclosure caption in the opening before product claims."
                ],
                strengths_to_preserve=["Keep the creator's natural delivery and product footage."],
                completion_criteria=[
                    "The visible disclosure appears before any product benefit claim.",
                    "The disclosure remains readable on mobile.",
                    "The seller or operator confirms the publish-time disclosure setting.",
                ],
                evidence_ids=[signal.id],
                confidence=signal.confidence,
                affected_use=context.intended_use,
                task_kind="video_edit_required",
                priority="fix_before_publish",
                exact_action=(
                    "Add a seller-approved visible disclosure caption during the opening."
                ),
                exact_copy=["seller-approved disclosure copy required"],
                acceptance_criteria=[
                    "The visible disclosure appears before any product benefit claim.",
                    "The disclosure remains readable on mobile.",
                    "The seller or operator confirms the publish-time disclosure setting.",
                ],
            )
        ]
    disclosure_present = any(
        item.confidence != "low" and item.value.get("present", True) is not False
        for item in _items(items, "disclosure")
    )
    if disclosure_present:
        return []
    if context.material_connection == "yes":
        return [
            EvaluationCandidate(
                rule_code="DISC-001",
                mistake_code="M-DISC-001",
                group="fix_first",
                title="Add the approved material-connection disclosure",
                reason="Seller input confirms a material connection, but no clear disclosure is visible.",
                why_it_matters="The commercial relationship should be clear to the viewer.",
                owner="editor",
                fix_type="add_overlay",
                instructions=[
                    "Add the seller-approved disclosure caption and confirm the publish-time setting."
                ],
                strengths_to_preserve=["Keep the creator's natural delivery and product footage."],
                completion_criteria=[
                    "The visible disclosure appears before any product benefit claim.",
                    "The disclosure remains readable on mobile.",
                    "The seller or operator confirms the publish-time disclosure setting.",
                ],
                evidence_ids=[],
                confidence="high",
                affected_use=context.intended_use,
                task_kind="video_edit_required",
                priority="fix_before_publish",
                time_range={"start_ms": 0, "end_ms": 2500},
                exact_action="Add a seller-approved visible disclosure caption during the opening.",
                exact_copy=["seller-approved disclosure copy required"],
                acceptance_criteria=[
                    "The visible disclosure appears before any product benefit claim.",
                    "The disclosure remains readable on mobile.",
                    "The seller or operator confirms the publish-time disclosure setting.",
                ],
            )
        ]
    return []


def _operational_unknowns(
    context: UGCReviewContext,
    evidence: NormalizedEvidenceBundle,
    rule_codes: set[str],
) -> list[EvaluationCandidate]:
    candidates: list[EvaluationCandidate] = []
    if (
        context.intended_use in {"paid_candidate", "spark_candidate"}
        and "UGC-RIGHTS-001" in rule_codes
        and not _has_confirmed(items=evidence.items, kind="rights")
    ):
        candidates.append(
            _confirm(
                rule_code="UGC-RIGHTS-001",
                mistake_code="M-RIGHTS-001",
                title="Confirm paid-use and Spark rights",
                reason="The draft cannot verify paid-use duration, editing rights or Spark authorization.",
                instructions=[
                    "Confirm channels, duration, editing scope, audio clearance and Spark authorization."
                ],
                completion=["The seller has a current rights record for the intended use."],
                evidence_ids=[],
                unknown_state="rights_incomplete",
                affected_use=context.intended_use,
            )
        )
    if context.intended_use in {
        "affiliate",
        "paid_candidate",
        "spark_candidate",
    } and not _has_confirmed(items=evidence.items, kind="publish_metadata"):
        candidates.append(
            _confirm(
                rule_code="SYS-UNKNOWN-001" if "SYS-UNKNOWN-001" in rule_codes else None,
                mistake_code="M-CTA-001",
                title="Confirm publish-time product metadata",
                reason="A draft file cannot prove the final product tag and platform settings.",
                instructions=[
                    "Check the exact product tag, disclosure setting and cleared audio at publish time."
                ],
                completion=[
                    "The final post metadata matches the reviewed product and intended use."
                ],
                evidence_ids=[],
                unknown_state="publish_check_required",
                affected_use=context.intended_use,
                task_kind="publish_ops_required",
                exact_action=(
                    "At publish time, confirm the product tag, disclosure setting and cleared audio."
                ),
                completion_override=[
                    "The final product tag points to the reviewed product/SKU.",
                    "The publish-time disclosure setting matches the material connection.",
                    "Audio is cleared for the intended use.",
                ],
            )
        )
    if evidence.metadata.get("economics_missing") is True:
        candidates.append(
            _confirm(
                rule_code="SYS-UNKNOWN-001" if "SYS-UNKNOWN-001" in rule_codes else None,
                mistake_code=None,
                title="Confirm economics before a paid test",
                reason="The creative review does not include current margin, fees, returns or supplier costs.",
                instructions=["Confirm current unit economics separately before paid use."],
                completion=[
                    "Current contribution economics are available for the intended paid use."
                ],
                evidence_ids=[],
                unknown_state="economics_insufficient",
                affected_use="paid_candidate",
            )
        )
    if not evidence.items and "SYS-UNKNOWN-001" in rule_codes:
        candidates.append(
            _confirm(
                rule_code="SYS-UNKNOWN-001",
                mistake_code="M-EVID-001",
                title="Review the missing evidence",
                reason="The available analysis could not verify key visual, transcript or overlay signals.",
                instructions=[
                    "Continue with seller confirmation or request clearer media for material facts."
                ],
                completion=["Material facts have direct evidence or explicit seller confirmation."],
                evidence_ids=[],
                unknown_state="insufficient_evidence",
                fix_type="request_better_media",
            )
        )
    return candidates


def _expected_vs_observed(
    items: list[NormalizedEvidence],
    rule_codes: set[str],
) -> list[EvaluationCandidate]:
    candidates: list[EvaluationCandidate] = []
    for item in _items(items, "expected_vs_observed"):
        status = str(item.value.get("status") or "unknown").lower()
        if status == "pass":
            continue
        rule_code_value = item.value.get("rule_code")
        rule_code = str(rule_code_value) if rule_code_value else None
        if rule_code and rule_code not in rule_codes:
            continue
        expected = _clean(item.value.get("expected"))
        observed = _clean(item.value.get("observed") or item.observed)
        editability = _clean(item.value.get("editability")).lower()
        mistake_code = _mistake_for_requirement(expected, observed, rule_code)
        unknown = "unknown" in status or status == "fail_or_unknown"
        group = "confirm" if unknown else "fix_first"
        fix_type = _fix_type(editability, unknown)
        candidates.append(
            EvaluationCandidate(
                rule_code=rule_code,
                mistake_code=mistake_code,
                group=group,
                title=(
                    f"Confirm {expected}"
                    if unknown
                    else f"Correct the draft requirement: {expected}"
                ),
                reason=f"Expected: {expected}. Observed: {observed}.",
                why_it_matters=(
                    "This material fact needs seller or publish-time confirmation."
                    if unknown
                    else "The observed draft does not match an explicit product or campaign requirement."
                ),
                owner="seller"
                if unknown
                else ("creator" if fix_type == "reshoot_scene" else "editor"),
                fix_type=fix_type,
                instructions=[
                    (
                        f"Confirm {expected} using current seller or publish-time information."
                        if unknown
                        else _instruction_for_fix(expected, fix_type)
                    )
                ],
                strengths_to_preserve=["Keep the unaffected demo, proof and creator delivery."],
                completion_criteria=[
                    f"The revised draft or seller confirmation satisfies: {expected}."
                ],
                evidence_ids=[item.id],
                confidence=item.confidence,
                unknown_state=_unknown_for_requirement(expected) if unknown else None,
            )
        )
    return candidates


def _confirm(
    *,
    rule_code: str | None,
    mistake_code: str | None,
    title: str,
    reason: str,
    instructions: list[str],
    completion: list[str],
    evidence_ids: list[str],
    unknown_state: str = "seller_confirmation_required",
    fix_type: str = "confirm_seller_input",
    affected_use: str | None = None,
    task_kind: str | None = None,
    exact_action: str | None = None,
    exact_copy: list[str] | None = None,
    completion_override: list[str] | None = None,
) -> EvaluationCandidate:
    completion_criteria = completion_override or completion
    return EvaluationCandidate(
        rule_code=rule_code,
        mistake_code=mistake_code,
        group="confirm",
        title=title,
        reason=reason,
        why_it_matters="Unknown information should be confirmed rather than treated as a creative failure.",
        owner="seller",
        fix_type=fix_type,
        instructions=instructions,
        strengths_to_preserve=["Keep all unaffected footage and creator delivery."],
        completion_criteria=completion,
        evidence_ids=evidence_ids,
        confidence="low" if unknown_state == "insufficient_evidence" else "medium",
        affected_use=affected_use,
        unknown_state=unknown_state,
        task_kind=task_kind,
        priority="confirm_before_publish",
        exact_action=exact_action or (instructions[0] if instructions else title),
        exact_copy=exact_copy or [],
        acceptance_criteria=completion_criteria,
    )


def _items(items: list[NormalizedEvidence], kind: str) -> list[NormalizedEvidence]:
    return [item for item in items if item.kind == kind]


def _clean(value: object) -> str:
    return str(value or "").strip()


def _matches(expected: str, observed: str) -> bool:
    def normalize(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()

    return normalize(expected) == normalize(observed)


def _brief_timing_requirement(brief: str | None) -> int | None:
    if not brief:
        return None
    match = re.search(
        r"(?:by|within(?: the first)?)\s+(\d+(?:\.\d+)?)\s*(?:seconds?|secs?|s\b)",
        brief,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    return int(float(match.group(1)) * 1000)


def _has_confirmed(*, items: list[NormalizedEvidence], kind: str) -> bool:
    return any(
        item.kind == kind and item.confidence != "low" and item.value.get("confirmed") is True
        for item in items
    )


def _mistake_for_requirement(
    expected: str,
    observed: str,
    rule_code: str | None,
) -> str | None:
    text = f"{expected} {observed}".lower()
    mappings = (
        (("sku", "variant", "exact product", "model"), "M-PROD-001"),
        (("personal",), "M-POD-001"),
        (("continuous", "mechanism", "demo"), "M-DEMO-001"),
        (("proof", "observable result"), "M-PROOF-001"),
        (("claim", "100%", "every fabric", "universal"), "M-CLAIM-001"),
        (("urgency", "scarcity", "limited time"), "M-OFFER-002"),
        (("price", "offer", "discount"), "M-OFFER-001"),
        (("shipping", "delivery time", "customer route"), "M-SUP-001"),
        (("disclosure",), "M-DISC-001"),
        (("rights", "spark", "audio"), "M-RIGHTS-001"),
        (("tag",), "M-CTA-001"),
        (("compatibility", "compatible model"), "M-DROP-001"),
        (("creator tone", "authentic", "hard-sell", "sales pitch"), "M-CREATOR-001"),
        (("product by", "opening", "timing"), "M-PROD-002"),
    )
    mapped = next((code for words, code in mappings if any(word in text for word in words)), None)
    if mapped is not None:
        return mapped
    return "M-REV-001" if rule_code == "UGC-REV-002" else None


def _fix_type(editability: str, unknown: bool) -> str:
    if unknown:
        return "confirm_seller_input"
    if "reshoot" in editability:
        return "reshoot_scene"
    if "remove" in editability or "replace" in editability:
        return "replace_copy"
    return "edit_existing_footage"


def _instruction_for_fix(expected: str, fix_type: str) -> str:
    if fix_type == "reshoot_scene":
        return f"Reshoot only the scene needed to show: {expected}."
    if fix_type == "replace_copy":
        return f"Remove or replace the copy so it matches: {expected}."
    return f"Edit the existing footage to satisfy: {expected}."


def _unknown_for_requirement(expected: str) -> str:
    lowered = expected.lower()
    if "rights" in lowered or "spark" in lowered or "audio" in lowered:
        return "rights_incomplete"
    if "econom" in lowered or "cost" in lowered or "margin" in lowered:
        return "economics_insufficient"
    if "tag" in lowered or "metadata" in lowered or "disclosure" in lowered:
        return "publish_check_required"
    return "seller_confirmation_required"
