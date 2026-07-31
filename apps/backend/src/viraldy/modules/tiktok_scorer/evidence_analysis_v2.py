from __future__ import annotations

from collections.abc import Sequence
from uuid import NAMESPACE_URL, uuid5

from viraldy.modules.media_analysis.public import EvidenceItemModel
from viraldy.modules.products.public import ProductContextSnapshot
from viraldy.modules.tiktok_scorer.contracts_v2 import (
    AuxiliarySignalV1,
    ConfidenceV2,
    IntendedUseV1,
    ProfileCodeV1,
    SceneInventoryV1,
    TikTokAuxiliarySignalsV1,
    TikTokDimensionResultV2,
    TikTokFindingV2,
)

DIMENSION_LABELS = {
    "hook_clarity": "Hook Clarity",
    "product_visibility": "Product Visibility",
    "demo_clarity": "Demo Clarity",
    "proof_strength": "Proof Strength",
    "creator_authenticity": "Creator Authenticity",
    "offer_clarity": "Value & Offer Clarity",
    "cta_readiness": "CTA Readiness",
    "tiktok_native_fit": "TikTok-Native Fit",
    "claim_safety": "Claim Safety",
}


def build_dimension_results(
    evidence: Sequence[EvidenceItemModel],
    *,
    product_context_snapshot: ProductContextSnapshot | None,
) -> list[TikTokDimensionResultV2]:
    return [
        _hook_dimension(evidence),
        _product_dimension(evidence),
        _demo_dimension(evidence),
        _proof_dimension(evidence),
        _creator_dimension(evidence),
        _offer_dimension(evidence),
        _cta_dimension(evidence),
        _native_dimension(evidence),
        _claim_dimension(evidence, product_context_snapshot),
    ]


def build_evidence_findings(
    evidence: Sequence[EvidenceItemModel],
    *,
    inventory: SceneInventoryV1,
    profile_code: ProfileCodeV1,
    intended_use: IntendedUseV1,
    product_context_snapshot: ProductContextSnapshot | None,
) -> list[TikTokFindingV2]:
    findings: list[TikTokFindingV2] = []
    product_items = _items(evidence, "product_appearance", "product_first_appearance")
    if product_context_snapshot is not None:
        mismatch = next(
            (
                item
                for item in product_items
                if (
                    (confidence := _float(item.value_json.get("product_match_confidence")))
                    is not None
                    and confidence < 0.4
                )
            ),
            None,
        )
        if mismatch is not None:
            findings.append(
                _finding(
                    item=mismatch,
                    inventory=inventory,
                    code="PRODUCT_MISMATCH",
                    rule_code="DROPSHIP_PRODUCT_OR_SKU_MISMATCH",
                    rule_class="product_governance_rule",
                    source_dimension="product_visibility",
                    severity="hard",
                    priority="P0",
                    title="The visible product does not match the attached product",
                    reason="Persisted product-match evidence conflicts with Product Context.",
                    expected={
                        "product_name": product_context_snapshot.product_context.identity.name,
                        "variant": product_context_snapshot.product_context.identity.variant,
                    },
                    observed={
                        "product_match_confidence": _float(
                            mismatch.value_json.get("product_match_confidence")
                        )
                    },
                    requires_physical_reshoot=True,
                )
            )
        findings.extend(_governance_findings(evidence, inventory, product_context_snapshot))

    findings.extend(
        _structural_findings(
            evidence,
            inventory=inventory,
            profile_code=profile_code,
            intended_use=intended_use,
        )
    )
    if profile_code in {"product_led_demo_v1", "tutorial_howto_v1", "offer_led_shop_v1"}:
        if not product_items:
            coverage_item = _first(evidence, "platform_signal", "hook_signal")
            if coverage_item is not None:
                findings.append(
                    _finding(
                        item=coverage_item,
                        inventory=inventory,
                        code="REQUIRED_PRODUCT_SCENE_MISSING",
                        rule_code=f"{profile_code.upper()}_PRODUCT_SCENE",
                        rule_class="contextual_guideline",
                        source_dimension="product_visibility",
                        severity="high",
                        priority="P0",
                        title="This format needs a verifiable product scene",
                        reason="The selected profile requires observable product grounding.",
                        expected={"required_scene": "clear product appearance"},
                        observed={"required_scene_exists": False},
                        requires_physical_reshoot=True,
                    )
                )
    return findings


def _structural_findings(
    evidence: Sequence[EvidenceItemModel],
    *,
    inventory: SceneInventoryV1,
    profile_code: ProfileCodeV1,
    intended_use: IntendedUseV1,
) -> list[TikTokFindingV2]:
    if inventory.coverage_status != "sufficient":
        return []
    findings: list[TikTokFindingV2] = []
    hooks = _items(evidence, "hook_signal")
    if hooks and hooks[0].value_json.get("clarity") in {"unclear", "unknown"}:
        findings.append(
            _finding(
                item=hooks[0],
                inventory=inventory,
                code="OPENING_PROPOSITION_UNCLEAR",
                rule_code="PROFILE_OPENING_CLARITY",
                rule_class="contextual_guideline",
                source_dimension="hook_clarity",
                severity="high",
                priority="P1",
                title="The opening does not establish a clear premise",
                reason="The persisted hook observation is unclear for the selected profile.",
                expected={"opening_state": "clear premise grounded in observed video content"},
                observed={"opening_clarity": hooks[0].value_json.get("clarity")},
                requires_physical_reshoot=True,
            )
        )
    elif not hooks and profile_code in {"product_led_demo_v1", "offer_led_shop_v1"}:
        opening_item = _earliest_timed(evidence, "product_appearance", "on_screen_text")
        if opening_item is not None:
            findings.append(
                _finding(
                    item=opening_item,
                    inventory=inventory,
                    code="CLEAR_HOOK_NOT_OBSERVED",
                    rule_code="PROFILE_OPENING_CLARITY",
                    rule_class="contextual_guideline",
                    source_dimension="hook_clarity",
                    severity="high",
                    priority="P1",
                    title="A clear opening premise was not observed",
                    reason=(
                        "Opening coverage exists, but no persisted clear-hook observation "
                        "was found."
                    ),
                    expected={"opening_state": "clear premise"},
                    observed={"hook_observed": False},
                    requires_physical_reshoot=True,
                )
            )

    demo_items = _items(evidence, "demo_summary", "demo_step")
    demo_expected = profile_code in {"product_led_demo_v1", "tutorial_howto_v1"}
    mechanism_observed = any(bool(item.value_json.get("mechanism_visible")) for item in demo_items)
    if demo_expected and demo_items and not mechanism_observed:
        findings.append(
            _finding(
                item=demo_items[0],
                inventory=inventory,
                code="PRODUCT_MECHANISM_UNCLEAR",
                rule_code=f"{profile_code.upper()}_DEMO_MECHANISM",
                rule_class="contextual_guideline",
                source_dimension="demo_clarity",
                severity="high",
                priority="P1",
                title="The product mechanism is not visible",
                reason="Demo evidence exists, but the physical mechanism is not observable.",
                expected={"demo_state": "product mechanism visible in use"},
                observed={"mechanism_visible": False},
                requires_physical_reshoot=True,
            )
        )
    elif demo_expected and not demo_items:
        product_item = _first(evidence, "product_appearance", "product_first_appearance")
        if product_item is not None:
            findings.append(
                _finding(
                    item=product_item,
                    inventory=inventory,
                    code="REQUIRED_DEMO_SCENE_MISSING",
                    rule_code=f"{profile_code.upper()}_DEMO_REQUIRED",
                    rule_class="contextual_guideline",
                    source_dimension="demo_clarity",
                    severity="high",
                    priority="P1",
                    title="A product-in-use demo scene is missing",
                    reason="Product evidence exists, but no demo step was observed.",
                    expected={"required_scene": "product mechanism shown in use"},
                    observed={"required_scene_exists": False},
                    requires_physical_reshoot=True,
                )
            )

    proof_expected = profile_code in {"product_led_demo_v1", "creator_review_v1"}
    if proof_expected and not _items(evidence, "proof_signal"):
        demo_item = _first(evidence, "demo_step", "product_appearance")
        if demo_item is not None:
            findings.append(
                _finding(
                    item=demo_item,
                    inventory=inventory,
                    code="OBSERVABLE_PROOF_SCENE_MISSING",
                    rule_code=f"{profile_code.upper()}_PROOF_REQUIRED",
                    rule_class="contextual_guideline",
                    source_dimension="proof_strength",
                    severity="high",
                    priority="P1",
                    title="The result needs an observable proof scene",
                    reason=(
                        "The selected profile has product footage but no persisted proof moment."
                    ),
                    expected={"required_scene": "observable product result or proof"},
                    observed={"required_scene_exists": False},
                    requires_physical_reshoot=True,
                )
            )

    cta_expected = intended_use != "tiktok_organic" or profile_code == "offer_led_shop_v1"
    if cta_expected and not _items(evidence, "cta_signal"):
        last_item = _latest_timed(evidence)
        if last_item is not None:
            findings.append(
                _finding(
                    item=last_item,
                    inventory=inventory,
                    code="CTA_NOT_OBSERVED",
                    rule_code=f"{profile_code.upper()}_CTA_REQUIRED",
                    rule_class="contextual_guideline",
                    source_dimension="cta_readiness",
                    severity="high",
                    priority="P1",
                    title="A clear next action is missing",
                    reason="End-to-end coverage exists, but no CTA observation was persisted.",
                    expected={"required_scene": "clear, context-appropriate next action"},
                    observed={"required_scene_exists": False, "cta_observed": False},
                    requires_physical_reshoot=False,
                )
            )
    return findings


def build_auxiliary_signals(
    evidence: Sequence[EvidenceItemModel],
    *,
    target_query: str | None,
    target_buyer_question: str | None,
    selected_search_topic: str | None,
    content_gap_topic: str | None,
) -> TikTokAuxiliarySignalsV1:
    targets = [
        value.strip()
        for value in (
            target_query,
            target_buyer_question,
            selected_search_topic,
            content_gap_topic,
        )
        if isinstance(value, str) and value.strip()
    ]
    if not targets:
        return TikTokAuxiliarySignalsV1()
    text_items = _items(evidence, "transcript_segment", "on_screen_text", "hook_signal")
    normalized_text = " ".join(_evidence_text(item).casefold() for item in text_items)
    matched = [target for target in targets if target.casefold() in normalized_text]
    return TikTokAuxiliarySignalsV1(
        search_discovery_readiness=AuxiliarySignalV1(
            status="evaluated",
            reason=(
                "The supplied search topic appears in persisted spoken or overlay evidence."
                if matched
                else "The supplied search topic was not observed in spoken or overlay evidence."
            ),
            evidence_ids=[item.id for item in text_items],
        )
    )


def critical_evidence_unavailable(
    evidence: Sequence[EvidenceItemModel],
    inventory: SceneInventoryV1,
) -> bool:
    if inventory.duration_ms is None or not evidence:
        return True
    visual_scenes = [scene for scene in inventory.scenes if scene.visual_quality != "unknown"]
    if visual_scenes and all(
        scene.visual_quality in {"dark", "blurry", "obscured"} for scene in visual_scenes
    ):
        return True
    return inventory.coverage_status == "insufficient"


def _hook_dimension(evidence: Sequence[EvidenceItemModel]) -> TikTokDimensionResultV2:
    items = _items(evidence, "hook_signal")
    if not items:
        return _unknown_dimension("hook_clarity", "No reliable opening-hook evidence is available.")
    item = items[0]
    clarity = str(item.value_json.get("clarity") or "unknown")
    score = {"clear": 88, "partial": 62, "unclear": 30, "unknown": 45}.get(clarity, 45)
    if item.start_ms is not None and item.start_ms > 1500:
        score -= 10
    return _scored_dimension(
        "hook_clarity",
        score,
        items,
        reason="Opening clarity is derived from the persisted hook observation.",
        positive=["An opening hook was observed."],
        missing=[] if clarity == "clear" else ["A fully clear opening proposition"],
    )


def _product_dimension(evidence: Sequence[EvidenceItemModel]) -> TikTokDimensionResultV2:
    items = _items(evidence, "product_appearance", "product_first_appearance")
    summary = _items(evidence, "product_visibility_summary")
    if not items and not summary:
        return _unknown_dimension(
            "product_visibility", "Product visibility cannot be scored from available evidence."
        )
    refs = [*items, *summary]
    clear = any(item.value_json.get("visibility") == "clear" for item in items)
    usage = any(bool(item.value_json.get("usage_visible")) for item in items) or any(
        bool(item.value_json.get("usage_present")) for item in summary
    )
    close_up = any(item.value_json.get("shot_type") in {"hero", "close_up"} for item in items)
    score = 45 + (25 if clear else 10) + (15 if usage else 0) + (15 if close_up else 0)
    return _scored_dimension(
        "product_visibility",
        score,
        refs,
        reason="Visibility is based on observed clarity, in-use footage, and readable framing.",
        positive=[
            signal
            for signal, present in {
                "Clear product appearance": clear,
                "Product shown in use": usage,
                "Readable close-up": close_up,
            }.items()
            if present
        ],
        missing=[
            signal
            for signal, present in {
                "Clear product appearance": clear,
                "Product shown in use": usage,
            }.items()
            if not present
        ],
    )


def _demo_dimension(evidence: Sequence[EvidenceItemModel]) -> TikTokDimensionResultV2:
    items = _items(evidence, "demo_summary", "demo_step")
    if not items:
        return _unknown_dimension("demo_clarity", "No reliable demo evidence is available.")
    steps = _items(evidence, "demo_step")
    mechanism = any(bool(item.value_json.get("mechanism_visible")) for item in steps)
    result = any(bool(item.value_json.get("result_visible")) for item in steps) or any(
        bool(item.value_json.get("after_state_visible")) for item in items
    )
    score = 40 + min(20, len(steps) * 10) + (25 if mechanism else 0) + (15 if result else 0)
    return _scored_dimension(
        "demo_clarity",
        score,
        items,
        reason="Demo clarity is derived from observed steps, mechanism, and result.",
        positive=["A demo is observed."],
        missing=[
            signal
            for signal, present in {
                "Visible mechanism": mechanism,
                "Visible result": result,
            }.items()
            if not present
        ],
    )


def _proof_dimension(evidence: Sequence[EvidenceItemModel]) -> TikTokDimensionResultV2:
    items = _items(evidence, "proof_signal")
    if not items:
        return _unknown_dimension("proof_strength", "No reliable proof evidence is available.")
    observable = any(item.value_json.get("verifiability") == "observable" for item in items)
    specific = any(
        item.value_json.get("description") not in {None, "", "unknown"} for item in items
    )
    score = 45 + (35 if observable else 10) + (20 if specific else 0)
    return _scored_dimension(
        "proof_strength",
        score,
        items,
        reason=(
            "Proof strength is based on observable, specific evidence rather than outcome claims."
        ),
        positive=["Observable proof" if observable else "A proof candidate was observed."],
        missing=[] if observable else ["Observable proof"],
    )


def _creator_dimension(evidence: Sequence[EvidenceItemModel]) -> TikTokDimensionResultV2:
    items = _items(evidence, "creator_signal")
    if not items:
        return _unknown_dimension(
            "creator_authenticity",
            "Creator delivery is not responsibly scoreable from available evidence.",
        )
    item = items[0]
    style = str(item.value_json.get("delivery_style") or "unknown")
    natural = style in {
        "authentic_review",
        "testimonial",
        "tutorial",
        "demonstration",
        "storytelling",
        "voiceover",
        "faceless_demo",
    }
    cues = item.value_json.get("authenticity_cues")
    cue_count = len(cues) if isinstance(cues, list) else 0
    score = 45 + (30 if natural else 10) + min(25, cue_count * 10)
    return _scored_dimension(
        "creator_authenticity",
        score,
        items,
        reason="Delivery is evaluated from observed voice, context, and firsthand-use cues.",
        positive=["Natural creator delivery"] if natural else [],
        missing=[] if natural else ["Natural, context-grounded delivery"],
    )


def _offer_dimension(evidence: Sequence[EvidenceItemModel]) -> TikTokDimensionResultV2:
    items = _items(evidence, "offer_signal")
    if not items:
        return _unknown_dimension(
            "offer_clarity", "Value or offer clarity is not established by available evidence."
        )
    specific = any(
        bool(item.value_json.get("text") or item.value_json.get("price_text")) for item in items
    )
    grounded = any(item.value_json.get("offer_type") == "value_statement" for item in items)
    score = 45 + (35 if specific else 10) + (20 if grounded else 5)
    return _scored_dimension(
        "offer_clarity",
        score,
        items,
        reason="Value & Offer Clarity uses observed specificity and product-grounded value.",
        positive=["A concrete value or offer statement was observed."],
        missing=[] if specific else ["A concrete, verified value statement"],
    )


def _cta_dimension(evidence: Sequence[EvidenceItemModel]) -> TikTokDimensionResultV2:
    items = _items(evidence, "cta_signal")
    if not items:
        return _unknown_dimension("cta_readiness", "No reliable CTA evidence is available.")
    clear = any(
        item.value_json.get("cta_type") not in {None, "unknown"}
        or bool(item.value_json.get("text"))
        for item in items
    )
    product_tag = any(bool(item.value_json.get("product_tag_visible")) for item in items)
    score = 50 + (35 if clear else 10) + (15 if product_tag else 0)
    return _scored_dimension(
        "cta_readiness",
        score,
        items,
        reason="CTA readiness is based on observed action clarity and supported shop cues.",
        positive=["A clear call to action was observed."] if clear else [],
        missing=[] if clear else ["A clear action for the viewer"],
    )


def _native_dimension(evidence: Sequence[EvidenceItemModel]) -> TikTokDimensionResultV2:
    items = _items(evidence, "platform_signal", "editing_signal", "on_screen_text")
    if not items:
        return _unknown_dimension(
            "tiktok_native_fit", "Platform-format evidence is insufficient for scoring."
        )
    vertical = any(item.value_json.get("vertical") is True for item in items)
    captions = any(item.evidence_type == "on_screen_text" for item in items)
    native = any(
        isinstance(item.value_json.get("native_signals"), list)
        and bool(item.value_json.get("native_signals"))
        for item in items
    )
    score = 40 + (25 if vertical else 5) + (20 if captions else 0) + (15 if native else 0)
    return _scored_dimension(
        "tiktok_native_fit",
        score,
        items,
        reason=(
            "TikTok-native fit is based on observed format, captions, and native execution cues."
        ),
        positive=[
            signal
            for signal, present in {
                "Vertical framing": vertical,
                "Readable on-screen text": captions,
                "TikTok-native execution cues": native,
            }.items()
            if present
        ],
        missing=[],
    )


def _claim_dimension(
    evidence: Sequence[EvidenceItemModel],
    product_context_snapshot: ProductContextSnapshot | None,
) -> TikTokDimensionResultV2:
    claims = _items(evidence, "claim_signal")
    coverage = _items(evidence, "transcript_segment", "on_screen_text")
    if not claims and not coverage:
        return _unknown_dimension(
            "claim_safety", "Claim safety cannot be evaluated without text or claim coverage."
        )
    refs = [*claims, *coverage]
    risks = [str(item.value_json.get("risk") or "unknown") for item in claims]
    worst = max(risks, key=_risk_rank, default="none")
    score = {"critical": 0, "high": 20, "medium": 55, "low": 78, "unknown": 70, "none": 92}[worst]
    uncertainty = []
    if product_context_snapshot is None:
        uncertainty.append("Product-specific claim support was not evaluated.")
    return _scored_dimension(
        "claim_safety",
        score,
        refs,
        reason="Claim safety is derived from persisted spoken and overlay claim evidence.",
        positive=["No high-risk claim candidate was observed."] if _risk_rank(worst) < 3 else [],
        missing=[],
        uncertainty=uncertainty,
    )


def _governance_findings(
    evidence: Sequence[EvidenceItemModel],
    inventory: SceneInventoryV1,
    snapshot: ProductContextSnapshot,
) -> list[TikTokFindingV2]:
    result: list[TikTokFindingV2] = []
    governance = snapshot.product_context.governance
    prohibited = [rule for rule in governance.claims if rule.rule_type == "prohibited"]
    for item in _items(evidence, "claim_signal"):
        text = _evidence_text(item)
        matched = next(
            (rule for rule in prohibited if _text_matches(text, rule.text)),
            None,
        )
        if matched is not None:
            result.append(
                _finding(
                    item=item,
                    inventory=inventory,
                    code="UNSUPPORTED_PRODUCT_CLAIM",
                    rule_code="TT_US_UNSUPPORTED_PRODUCT_CLAIM",
                    rule_class="product_governance_rule",
                    source_dimension="claim_safety",
                    severity="hard",
                    priority="P0",
                    title="The video uses a prohibited product claim",
                    reason=(
                        "The observed claim conflicts with immutable Product Context governance."
                    ),
                    expected={"claim_status": "allowed or seller-approved replacement"},
                    observed={
                        "claim_text": text,
                        "modality": item.value_json.get("source"),
                        "matched_prohibited_claim_id": matched.id,
                    },
                    requires_seller_truth=True,
                    can_be_resolved_by_edit=True,
                )
            )
    required_disclosures = [
        *governance.required_disclosures,
        *[rule.text for rule in governance.claims if rule.rule_type == "required_disclosure"],
    ]
    disclosures = [
        item
        for item in _items(evidence, "on_screen_text")
        if item.value_json.get("text_role") == "disclosure"
    ]
    coverage = _first(evidence, "on_screen_text", "transcript_segment")
    if required_disclosures and not disclosures and coverage is not None:
        result.append(
            _finding(
                item=coverage,
                inventory=inventory,
                code="REQUIRED_DISCLOSURE_MISSING",
                rule_code="PRODUCT_CONTEXT_DISCLOSURE_RECOMMENDED",
                rule_class="product_governance_rule",
                source_dimension="claim_safety",
                severity="medium",
                priority="P2",
                title="A recommended disclosure is missing",
                reason=(
                    "Product Context recommends a disclosure for this use. Treat this as a "
                    "creator/editor recommendation unless a separate paid-use compliance review "
                    "requires it."
                ),
                expected={"approved_disclosure_text": required_disclosures[0]},
                observed={"disclosure_observed": False},
                can_be_resolved_by_edit=True,
            )
        )
    offers = _items(evidence, "offer_signal")
    commercial = snapshot.product_context.commercial
    if offers and not any(
        (
            commercial.price,
            commercial.discount_text,
            commercial.bundle_text,
            commercial.shipping_text,
            commercial.offer_notes,
        )
    ):
        result.append(
            _finding(
                item=offers[0],
                inventory=inventory,
                code="OFFER_TRUTH_MISSING",
                rule_code="PRODUCT_OFFER_REQUIRES_SELLER_TRUTH",
                rule_class="product_governance_rule",
                source_dimension="offer_clarity",
                severity="high",
                priority="P0",
                title="The visible offer needs seller confirmation",
                reason="The video contains an offer that is not verified in Product Context.",
                expected={"offer": "seller-confirmed offer"},
                observed={"offer_text": _evidence_text(offers[0])},
                requires_seller_truth=True,
            )
        )
    return result


def _finding(
    *,
    item: EvidenceItemModel,
    inventory: SceneInventoryV1,
    code: str,
    rule_code: str,
    rule_class: str,
    source_dimension: str,
    severity: str,
    priority: str,
    title: str,
    reason: str,
    expected: dict[str, object],
    observed: dict[str, object],
    requires_seller_truth: bool = False,
    can_be_resolved_by_edit: bool | None = None,
    requires_physical_reshoot: bool | None = None,
) -> TikTokFindingV2:
    time_range = _item_time_range(item, inventory.duration_ms)
    return TikTokFindingV2(
        id=uuid5(
            NAMESPACE_URL,
            f"viraldy:tiktok-finding:{inventory.asset_version_id}:{code}:{item.id}",
        ),
        code=code,
        rule_code=rule_code,
        rule_class=rule_class,
        source_dimension=source_dimension,
        severity=severity,
        priority=priority,
        applicability="applicable",
        evidence_status="sufficient",
        title=title,
        reason=reason,
        expected=expected,
        observed=observed,
        target_time_range_ms=time_range,
        evidence_ids=[item.id],
        uncertainty=[],
        requires_seller_truth=requires_seller_truth,
        can_be_resolved_by_edit=can_be_resolved_by_edit,
        requires_physical_reshoot=requires_physical_reshoot,
    )


def _scored_dimension(
    code: str,
    score: int,
    items: Sequence[EvidenceItemModel],
    *,
    reason: str,
    positive: list[str],
    missing: list[str],
    uncertainty: list[str] | None = None,
) -> TikTokDimensionResultV2:
    evidence_ids = list(dict.fromkeys(item.id for item in items))
    confidence = _confidence(items)
    return TikTokDimensionResultV2(
        code=code,
        label=DIMENSION_LABELS[code],
        score=max(0, min(100, round(score))),
        applicability="applicable",
        evidence_status="partial" if confidence == "low" else "sufficient",
        confidence=confidence,
        reason=reason,
        positive_signals=positive,
        missing_signals=missing,
        uncertainty=uncertainty or [],
        evidence_ids=evidence_ids,
        contributing_rule_codes=[f"V2_{code.upper()}"],
    )


def _unknown_dimension(code: str, reason: str) -> TikTokDimensionResultV2:
    return TikTokDimensionResultV2(
        code=code,
        label=DIMENSION_LABELS[code],
        score=None,
        applicability="unknown",
        evidence_status="insufficient",
        confidence="low",
        reason=reason,
        positive_signals=[],
        missing_signals=["Sufficient persisted evidence"],
        uncertainty=[reason],
        evidence_ids=[],
        contributing_rule_codes=[],
    )


def _items(
    evidence: Sequence[EvidenceItemModel],
    *evidence_types: str,
) -> list[EvidenceItemModel]:
    allowed = set(evidence_types)
    return [item for item in evidence if item.evidence_type in allowed]


def _first(
    evidence: Sequence[EvidenceItemModel],
    *evidence_types: str,
) -> EvidenceItemModel | None:
    return next(iter(_items(evidence, *evidence_types)), None)


def _earliest_timed(
    evidence: Sequence[EvidenceItemModel],
    *evidence_types: str,
) -> EvidenceItemModel | None:
    timed = [item for item in _items(evidence, *evidence_types) if item.start_ms is not None]
    return min(timed, key=lambda item: item.start_ms or 0) if timed else None


def _latest_timed(
    evidence: Sequence[EvidenceItemModel],
) -> EvidenceItemModel | None:
    timed = [item for item in evidence if item.end_ms is not None]
    return max(timed, key=lambda item: item.end_ms or 0) if timed else None


def _confidence(items: Sequence[EvidenceItemModel]) -> ConfidenceV2:
    values = [float(item.confidence) for item in items if item.confidence is not None]
    if not values:
        return "low"
    average = sum(values) / len(values)
    if average >= 0.8:
        return "high"
    if average >= 0.55:
        return "medium"
    return "low"


def _float(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return float(value)


def _risk_rank(risk: str) -> int:
    return {"none": 0, "unknown": 1, "low": 1, "medium": 2, "high": 3, "critical": 4}.get(
        risk,
        1,
    )


def _evidence_text(item: EvidenceItemModel) -> str:
    value = item.value_json
    for key in ("text", "spoken_text", "overlay_text", "price_text", "discount_text"):
        text = value.get(key)
        if isinstance(text, str) and text.strip():
            return text.strip()
    return ""


def _text_matches(observed: str, governed: str) -> bool:
    left = " ".join(observed.casefold().split())
    right = " ".join(governed.casefold().split())
    return bool(left and right and (left in right or right in left))


def _item_time_range(
    item: EvidenceItemModel,
    duration_ms: int | None,
) -> tuple[int, int] | None:
    if duration_ms is None or item.start_ms is None or item.end_ms is None:
        return None
    if 0 <= item.start_ms <= item.end_ms <= duration_ms:
        return item.start_ms, item.end_ms
    return None


__all__ = [
    "DIMENSION_LABELS",
    "build_auxiliary_signals",
    "build_dimension_results",
    "build_evidence_findings",
    "critical_evidence_unavailable",
]
