from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import ValidationError

from viraldy.modules.ai_gateway.public import (
    VIRAL_KIT_PROMPT_VERSION,
    OpenAICompatibleClient,
    extract_message_json,
)
from viraldy.modules.creative_domain.schema_versions import ADAPTATION_SCHEMA_VERSION
from viraldy.modules.pattern_kits.contracts import PatternEvidenceRefV1
from viraldy.modules.pattern_kits.public import PatternKitVersionSnapshot
from viraldy.modules.products.contracts import (
    BuyerPersonaV1,
    ProductContextV1,
    ProductGovernanceV1,
)
from viraldy.modules.products.public import ProductContextSnapshot
from viraldy.modules.viral_kits.contracts import (
    AdaptationDecisionV1,
    BuyerContextV1,
    CommercialConstraintsV1,
    DiversityAxisV1,
    GenerationBriefV1,
    GenerationSceneV1,
    GovernanceConstraintsV1,
    ViralKitAdaptationPlanV1,
    ViralKitConceptV1,
    ViralKitConfidenceV1,
    ViralKitConstraintsV1,
    ViralKitDecisionCriterionV1,
    ViralKitHookV1,
    ViralKitPatternMatchV1,
    ViralKitPreflightRequirementLinkV1,
    ViralKitProductSnapshotV1,
    ViralKitProvenanceV1,
    ViralKitRequirementDraftV1,
    ViralKitRiskV1,
    ViralKitTestCellV1,
    ViralKitTestMatrixV1,
    ViralKitV1,
)
from viraldy.modules.viral_kits.schemas import CreateViralKitRequest
from viraldy.platform.config.settings import Settings
from viraldy.shared.errors.base import AppError


class LiveViralKitProvider:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = OpenAICompatibleClient(settings)

    def compose(
        self,
        *,
        viral_kit_id: UUID,
        workspace_id: UUID,
        version: int,
        created_by: UUID,
        created_at: str,
        request: CreateViralKitRequest,
        product_snapshot: dict[str, object],
        pattern_payloads: list[dict[str, object]],
        pattern_matches: list[dict[str, object]],
        model_run_id: UUID,
    ) -> ViralKitV1:
        if not self._settings.ai_base_url or not self._settings.ai_text_model:
            raise AppError(
                "AI_PROVIDER_NOT_CONFIGURED",
                "ViralKit composition requires AI_BASE_URL and AI_TEXT_MODEL.",
                status_code=503,
            )
        if self._settings.ai_mode == "live" and not self._settings.ai_api_key:
            raise AppError(
                "AI_PROVIDER_NOT_CONFIGURED",
                "Live ViralKit composition requires AI_API_KEY.",
                status_code=503,
            )
        payload: dict[str, object] = {
            "model": self._settings.ai_text_model,
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "Compose a ViralKitV1 from the supplied product snapshot and "
                        "PatternKit versions only. Return only JSON matching ViralKitV1. "
                        "Create exactly three diverse concepts. Do not promise virality, "
                        "GMV, ROAS, or sales. Preserve prohibited claims, required "
                        "disclosures, product facts, fulfillment constraints, and evidence "
                        "provenance.\n"
                        f"Viral kit ID: {viral_kit_id}\n"
                        f"Workspace ID: {workspace_id}\n"
                        f"Version: {version}\n"
                        f"Created by: {created_by}\n"
                        f"Created at: {created_at}\n"
                        f"Model run ID: {model_run_id}\n"
                        f"Request: {request.model_dump(mode='json')}\n"
                        f"Product snapshot: {product_snapshot}\n"
                        f"Pattern matches: {pattern_matches}\n"
                        f"Pattern payloads: {pattern_payloads}"
                    ),
                }
            ],
            "response_format": _response_format(self._settings),
        }
        if self._settings.ai_max_output_tokens is not None:
            payload["max_tokens"] = self._settings.ai_max_output_tokens
        raw = extract_message_json(self._client.chat_json(payload))
        try:
            return ViralKitV1.model_validate(raw)
        except ValidationError as exc:
            raise AppError(
                "VIRAL_KIT_OUTPUT_INVALID",
                "Provider returned invalid ViralKit output.",
                details={"errors": exc.errors()},
            ) from exc


def build_fixture_viral_kit(
    *,
    viral_kit_id: UUID,
    workspace_id: UUID,
    version: int,
    created_by: UUID,
    created_at: datetime,
    request: CreateViralKitRequest,
    product: ProductContextSnapshot,
    patterns: list[PatternKitVersionSnapshot],
    pattern_matches: list[ViralKitPatternMatchV1],
    model_run_id: UUID | None,
) -> ViralKitV1:
    context = product.product_context
    constraints = _constraints(context, request)
    buyer = _buyer_context(context, request.buyer_persona_id)
    pattern_ids = [snapshot.pattern_kit_version_id for snapshot in patterns]
    evidence_refs = _evidence_refs(patterns)
    concepts = [
        _concept(
            index=1,
            axis="result_first",
            diversity_axes=["hook_mechanism", "narrative_structure"],
            hook_type="result_first",
            delivery_style=_delivery_style(request, "authentic_review"),
            narrative_structure="result -> product reveal -> demo -> proof -> CTA",
            demo_mechanism=_demo_mechanism(context),
            proof_mechanism=_proof_mechanism(context),
            context=context,
            buyer=buyer,
            constraints=constraints,
            pattern_ids=pattern_ids,
            evidence_refs=evidence_refs,
        ),
        _concept(
            index=2,
            axis="problem_first",
            diversity_axes=["buyer_pain", "demo_mechanism", "hook_mechanism"],
            hook_type="problem_first",
            delivery_style=_delivery_style(request, "demonstration"),
            narrative_structure="problem -> fast reveal -> step demo -> result -> CTA",
            demo_mechanism=f"step-by-step {_demo_mechanism(context)}",
            proof_mechanism=_proof_mechanism(context),
            context=context,
            buyer=buyer,
            constraints=constraints,
            pattern_ids=pattern_ids,
            evidence_refs=evidence_refs,
        ),
        _concept(
            index=3,
            axis="proof_first",
            diversity_axes=["proof_mechanism", "delivery_style", "narrative_structure"],
            hook_type="proof_first",
            delivery_style=_delivery_style(request, "evidence_led_review"),
            narrative_structure="proof setup -> product use -> result explanation -> CTA",
            demo_mechanism=_demo_mechanism(context),
            proof_mechanism=f"observable proof from {_proof_mechanism(context)}",
            context=context,
            buyer=buyer,
            constraints=constraints,
            pattern_ids=pattern_ids,
            evidence_refs=evidence_refs,
        ),
    ]
    return ViralKitV1(
        id=viral_kit_id,
        workspace_id=workspace_id,
        version=version,
        status="ready_for_review",
        name=f"{context.identity.name} {request.objective} ViralKit",
        product=ViralKitProductSnapshotV1(
            product_id=product.product_id,
            product_context_schema_version=product.context_schema_version,
            product_context_version=product.product_context_version,
            snapshot_json=context,
            captured_at=created_at,
        ),
        objective=request.objective,
        platform=request.platform,
        target_market=request.target_market,
        buyer_context=buyer,
        constraints=constraints,
        pattern_matches=pattern_matches,
        adaptation_plan=_adaptation_plan(patterns, context),
        concepts=concepts,
        test_matrix=_test_matrix(concepts),
        selected_concept_id=None,
        campaign_pack_links=[],
        preflight_requirement_links=[
            ViralKitPreflightRequirementLinkV1(
                concept_id=concept.id,
                expected_requirement_classes=_expected_requirement_classes(
                    constraints.commercial
                ),
            )
            for concept in concepts
        ],
        generation_briefs=_generation_briefs(concepts, constraints)
        if request.production_constraints.concept_preview_requested
        else [],
        risks=_risks(context, pattern_matches, constraints),
        overall_confidence=_overall_confidence(context, pattern_matches),
        uncertainties=_uncertainties(context, pattern_matches),
        provenance=ViralKitProvenanceV1(
            pattern_kit_version_ids=pattern_ids,
            adaptation_schema_version=ADAPTATION_SCHEMA_VERSION,
            model_run_id=model_run_id,
            prompt_version=VIRAL_KIT_PROMPT_VERSION,
        ),
        created_by=created_by,
        created_at=created_at,
    )


def _constraints(
    context: ProductContextV1,
    request: CreateViralKitRequest,
) -> ViralKitConstraintsV1:
    return ViralKitConstraintsV1(
        creator=request.creator_constraints,
        production=request.production_constraints,
        commercial=request.commercial_constraints.model_copy(
            update={
                "product_tag_required": _product_tag_required(request),
            }
        ),
        governance=GovernanceConstraintsV1(
            prohibited_claims=_prohibited_claims(context.governance),
            required_disclosures=list(context.governance.required_disclosures),
            prohibited_content=list(context.governance.prohibited_content),
            rights_notes=list(context.governance.rights_notes),
        ),
    )


def _product_tag_required(request: CreateViralKitRequest) -> bool:
    if request.commercial_constraints.product_tag_required:
        return True
    return request.platform == "tiktok_shop" and request.objective.startswith("tiktok_shop")


def _buyer_context(context: ProductContextV1, buyer_persona_id: str | None) -> BuyerContextV1:
    persona = _selected_persona(context, buyer_persona_id)
    if persona is None:
        return BuyerContextV1(
            persona_id="unknown",
            persona_label="unknown buyer",
            pain_points=["unknown buyer pain"],
            desired_outcomes=["unknown desired outcome"],
            awareness_stage="unknown",
        )
    return BuyerContextV1(
        persona_id=persona.id,
        persona_label=persona.label,
        pain_points=persona.pain_points or ["unknown buyer pain"],
        desired_outcomes=persona.desired_outcomes or ["unknown desired outcome"],
        awareness_stage=persona.awareness_stage,
    )


def _selected_persona(
    context: ProductContextV1,
    buyer_persona_id: str | None,
) -> BuyerPersonaV1 | None:
    if buyer_persona_id is not None:
        for persona in context.personas:
            if persona.id == buyer_persona_id:
                return persona
    return context.personas[0] if context.personas else None


def _concept(
    *,
    index: int,
    axis: str,
    diversity_axes: list[DiversityAxisV1],
    hook_type: str,
    delivery_style: str,
    narrative_structure: str,
    demo_mechanism: str,
    proof_mechanism: str,
    context: ProductContextV1,
    buyer: BuyerContextV1,
    constraints: ViralKitConstraintsV1,
    pattern_ids: list[UUID],
    evidence_refs: list[PatternEvidenceRefV1],
) -> ViralKitConceptV1:
    product_name = context.identity.name
    pain = buyer.pain_points[0] if buyer.pain_points else "unknown buyer pain"
    outcome = buyer.desired_outcomes[0] if buyer.desired_outcomes else "unknown desired outcome"
    creator_persona = _creator_persona(context, constraints, buyer.persona_label)
    product_tag_required = constraints.commercial.product_tag_required
    must_show = [
        ViralKitRequirementDraftV1(
            id=f"concept_{index}_product_visible",
            requirement_type="product_visibility",
            instruction=f"Show {product_name} clearly in the first product moment.",
            required=True,
            severity="hard",
            expected_before_ms=3000,
            matcher_hint="product_visibility_timing",
        ),
        ViralKitRequirementDraftV1(
            id=f"concept_{index}_demo",
            requirement_type="demo_presence",
            instruction=demo_mechanism,
            required=True,
            severity="high",
            expected_before_ms=None,
            matcher_hint="demo_mechanism_match",
        ),
        ViralKitRequirementDraftV1(
            id=f"concept_{index}_proof",
            requirement_type="proof_presence",
            instruction=proof_mechanism,
            required=True,
            severity="high",
            expected_before_ms=None,
            matcher_hint="proof_type_match",
        ),
    ]
    if product_tag_required:
        must_show.append(
            ViralKitRequirementDraftV1(
                id=f"concept_{index}_product_tag",
                requirement_type="product_tag_presence",
                instruction=(
                    "Include the TikTok Shop product tag only after product context is clear."
                ),
                required=True,
                severity="hard",
                expected_before_ms=None,
                matcher_hint="product_tag_presence",
            )
        )
    for disclosure in constraints.governance.required_disclosures:
        must_show.append(
            ViralKitRequirementDraftV1(
                id=f"concept_{index}_disclosure_{len(must_show) + 1}",
                requirement_type="required_disclosure_presence",
                instruction=disclosure,
                required=True,
                severity="hard",
                expected_before_ms=None,
                matcher_hint="required_disclosure_presence",
            )
        )
    return ViralKitConceptV1(
        id=f"concept_{index}",
        name=f"{product_name} {axis.replace('_', ' ')} test",
        strategic_axis=axis,
        diversity_axes=diversity_axes,
        buyer_persona_id=buyer.persona_id or "unknown",
        buyer_persona_label=buyer.persona_label,
        buyer_pain=pain,
        desired_outcome=outcome,
        awareness_stage=buyer.awareness_stage,
        creative_angle=_creative_angle(context),
        hook=ViralKitHookV1(
            hook_type=hook_type,
            spoken_text=_hook_line(hook_type, product_name, pain, outcome),
            overlay_text=_overlay_text(hook_type, product_name),
            opening_visual=_opening_visual(hook_type, product_name, pain),
            target_time_ms=0,
            product_present=hook_type != "problem_first",
            buyer_pain=pain,
        ),
        opening_visual=_opening_visual(hook_type, product_name, pain),
        narrative_structure=narrative_structure,
        creator_persona=creator_persona,
        delivery_style=delivery_style,
        demo_mechanism=demo_mechanism,
        proof_mechanism=proof_mechanism,
        offer_framing=_offer_framing(context, constraints.commercial),
        cta_strategy=_cta_strategy(product_tag_required),
        must_show=must_show,
        overlays=[_overlay_text(hook_type, product_name), "Show the result"],
        spoken_lines=[
            _hook_line(hook_type, product_name, pain, outcome),
            f"Here is the actual {product_name} in use.",
        ],
        claims_to_avoid=_claim_guardrails(constraints.governance),
        required_disclosures=list(constraints.governance.required_disclosures),
        test_hypothesis=f"Test whether {axis} improves qualified creative signal.",
        expected_learning=f"Learn whether {axis} is a stronger structure for this product.",
        feasibility=_feasibility(context, constraints),
        risks=_concept_risks(context, constraints),
        source_pattern_kit_version_ids=pattern_ids,
        evidence_refs=evidence_refs[:8],
        confidence="medium" if evidence_refs else "low",
    )


def _adaptation_plan(
    patterns: list[PatternKitVersionSnapshot],
    context: ProductContextV1,
) -> ViralKitAdaptationPlanV1:
    keep: list[AdaptationDecisionV1] = []
    change: list[AdaptationDecisionV1] = []
    avoid: list[AdaptationDecisionV1] = []
    for snapshot in patterns:
        for instruction in snapshot.pattern.adaptation_instructions:
            decision = AdaptationDecisionV1(
                element_path=instruction.element_path,
                decision=instruction.instruction_type,
                source_pattern_kit_version_ids=[snapshot.pattern_kit_version_id],
                product_context_paths=["identity", "creative", "governance"],
                rationale=instruction.rationale,
                severity=instruction.severity,
                evidence_refs=instruction.evidence_refs,
            )
            if instruction.instruction_type == "keep":
                keep.append(decision)
            elif instruction.instruction_type == "change":
                change.append(decision)
            else:
                avoid.append(decision)
    for claim in _prohibited_claims(context.governance):
        avoid.append(
            AdaptationDecisionV1(
                element_path="claims",
                decision="avoid",
                source_pattern_kit_version_ids=[
                    snapshot.pattern_kit_version_id for snapshot in patterns
                ],
                product_context_paths=["governance.claims"],
                rationale=f"Product governance prohibits: {claim}",
                severity="hard",
                evidence_refs=[],
            )
        )
    return ViralKitAdaptationPlanV1(keep=keep, change=change, avoid=avoid)


def _test_matrix(concepts: list[ViralKitConceptV1]) -> ViralKitTestMatrixV1:
    return ViralKitTestMatrixV1(
        primary_hypothesis="Different structural concepts produce different creative signals.",
        concepts=[
            ViralKitTestCellV1(
                concept_id=concept.id,
                hypothesis=concept.test_hypothesis,
                changed_axes=concept.diversity_axes,
                held_constant=["product", "target_market", "platform", "offer_policy"],
                minimum_execution_requirements=[
                    requirement.instruction for requirement in concept.must_show
                ],
                metrics_to_observe=[
                    "hook retention",
                    "product clicks",
                    "orders",
                    "GMV",
                    "gross profit",
                ],
            )
            for concept in concepts
        ],
        controlled_variables=["product", "market", "platform", "governance"],
        intentionally_changed_variables=[
            "hook_mechanism",
            "narrative_structure",
            "demo_or_proof_mechanism",
        ],
        recommended_test_order=[concept.id for concept in concepts],
        decision_criteria=[
            ViralKitDecisionCriterionV1(
                criterion="No hard preflight blockers",
                signal_type="structural",
                comparison="must pass before publishing",
                caveat="Structural readiness does not predict sales.",
            ),
            ViralKitDecisionCriterionV1(
                criterion="Compare qualified click and order signals",
                signal_type="commercial",
                comparison="compare against same product and market context",
                caveat="Private beta does not infer statistical significance automatically.",
            ),
        ],
    )


def _generation_briefs(
    concepts: list[ViralKitConceptV1],
    constraints: ViralKitConstraintsV1,
) -> list[GenerationBriefV1]:
    return [
        GenerationBriefV1(
            concept_id=concept.id,
            purpose="storyboard_preview",
            aspect_ratio=constraints.production.required_aspect_ratio,
            duration_ms=constraints.production.max_duration_ms,
            product_asset_ids=[],
            reference_asset_ids=[],
            scenes=[
                GenerationSceneV1(
                    scene_id=f"{concept.id}_scene_1",
                    order=1,
                    purpose="opening",
                    visual_prompt=concept.opening_visual,
                    camera_direction="vertical mobile framing",
                    product_visibility="visible when required by concept",
                    creator_direction=concept.creator_persona,
                    overlay_text=concept.hook.overlay_text,
                    spoken_direction=concept.hook.spoken_text,
                    reference_asset_ids=[],
                )
            ],
            consistency_constraints=["Use authorized product assets only."],
            negative_constraints=["No face or voice cloning without consent."],
            overlay_instructions=concept.overlays,
            audio_direction=None,
            claim_guardrails=concept.claims_to_avoid,
            rights_confirmation_required=True,
        )
        for concept in concepts
    ]


def _expected_requirement_classes(commercial: CommercialConstraintsV1) -> list[str]:
    values = [
        "product_visibility",
        "product_visibility_timing",
        "product_match",
        "product_in_use",
        "demo_presence",
        "demo_mechanism_match",
        "proof_presence",
        "proof_type_match",
        "overlay_text_presence",
        "spoken_text_presence",
        "hook_semantic_match",
        "cta_presence",
        "cta_type_match",
        "cta_timing",
        "prohibited_claim_absence",
        "required_disclosure_presence",
        "allowed_claim_qualification",
    ]
    if commercial.product_tag_required:
        values.append("product_tag_presence")
    if commercial.offer_required:
        values.extend(["offer_presence", "offer_text_match", "offer_before_cta"])
    values.append("creator_style_match")
    return values


def _risks(
    context: ProductContextV1,
    matches: list[ViralKitPatternMatchV1],
    constraints: ViralKitConstraintsV1,
) -> list[ViralKitRiskV1]:
    risks: list[ViralKitRiskV1] = []
    if context.identity.category == "unknown":
        risks.append(
            ViralKitRiskV1(
                code="PRODUCT_CATEGORY_UNKNOWN",
                severity="medium",
                message="Product category is unknown, so applicability confidence is reduced.",
                source="product_context",
                mitigation="Fill product identity.category before private beta review.",
            )
        )
    if any(match.applicability_status in {"partial", "override"} for match in matches):
        risks.append(
            ViralKitRiskV1(
                code="PATTERN_MATCH_PARTIAL",
                severity="medium",
                message="At least one PatternKit has partial or overridden applicability.",
                source="pattern_matcher",
                mitigation="Reviewer should confirm pattern transfer before production.",
            )
        )
    if constraints.commercial.shipping_claim_policy != "no_shipping_claims":
        risks.append(
            ViralKitRiskV1(
                code="SHIPPING_CLAIM_GOVERNANCE",
                severity="high",
                message="Shipping language must come only from seller-confirmed product context.",
                source="commercial_constraints",
                mitigation="Avoid shipping promises unless present in Product Context.",
            )
        )
    return risks


def _concept_risks(
    context: ProductContextV1,
    constraints: ViralKitConstraintsV1,
) -> list[ViralKitRiskV1]:
    risks = []
    if _prohibited_claims(context.governance):
        risks.append(
            ViralKitRiskV1(
                code="PROHIBITED_CLAIM_RISK",
                severity="hard",
                message="Concept must avoid all prohibited product claims.",
                source="product_governance",
                mitigation="Run exact preflight before publishing.",
            )
        )
    if constraints.commercial.product_tag_required:
        risks.append(
            ViralKitRiskV1(
                code="PRODUCT_TAG_REQUIRED",
                severity="hard",
                message="TikTok Shop product tag must be present when executing this concept.",
                source="commercial_constraints",
                mitigation="Verify product-tag presence in preflight.",
            )
        )
    return risks


def _uncertainties(
    context: ProductContextV1,
    matches: list[ViralKitPatternMatchV1],
) -> list[str]:
    values: list[str] = []
    if not context.personas:
        values.append("buyer_persona_unknown")
    if not context.benefits:
        values.append("product_benefits_unknown")
    if context.identity.category == "unknown":
        values.append("product_category_unknown")
    for match in matches:
        values.extend(match.conflicts)
    return _unique(values)


def _overall_confidence(
    context: ProductContextV1,
    matches: list[ViralKitPatternMatchV1],
) -> ViralKitConfidenceV1:
    if any(match.applicability_status == "override" for match in matches):
        return "low"
    if context.identity.category == "unknown" or not context.personas:
        return "low"
    if all(match.applicability_status == "matched" for match in matches):
        return "high"
    return "medium"


def _evidence_refs(patterns: list[PatternKitVersionSnapshot]) -> list[PatternEvidenceRefV1]:
    refs: list[PatternEvidenceRefV1] = []
    seen: set[tuple[UUID, str]] = set()
    for snapshot in patterns:
        for beat in snapshot.pattern.sequence:
            for ref in beat.evidence_refs:
                key = (ref.evidence_id, ref.feature_path)
                if key in seen:
                    continue
                seen.add(key)
                refs.append(ref)
    return refs


def _creator_persona(
    context: ProductContextV1,
    constraints: ViralKitConstraintsV1,
    buyer_label: str,
) -> str:
    options = constraints.creator.allowed_personas or context.creative.creator_personas
    for option in options:
        if option not in constraints.creator.disallowed_personas and option != buyer_label:
            return option
    if "creator_operator" != buyer_label:
        return "creator_operator"
    return "product_demonstrator"


def _delivery_style(request: CreateViralKitRequest, fallback: str) -> str:
    return request.creator_constraints.delivery_style_preferences[0] if (
        request.creator_constraints.delivery_style_preferences
    ) else fallback


def _demo_mechanism(context: ProductContextV1) -> str:
    if context.creative.demonstration_mechanisms:
        return context.creative.demonstration_mechanisms[0]
    for feature in context.features:
        if feature.visual_demo_possible:
            return f"show {feature.label} in use"
    return "show the product in use"


def _proof_mechanism(context: ProductContextV1) -> str:
    if context.creative.available_proof:
        return context.creative.available_proof[0]
    for benefit in context.benefits:
        if benefit.proof_available:
            return benefit.proof_available[0]
    return "show an observable result"


def _creative_angle(context: ProductContextV1) -> str:
    if context.creative.primary_angles:
        return context.creative.primary_angles[0]
    if context.benefits:
        return context.benefits[0].label
    return f"{context.identity.name} product use case"


def _offer_framing(
    context: ProductContextV1,
    commercial: CommercialConstraintsV1,
) -> str | None:
    if commercial.offer_required:
        return context.commercial.discount_text or context.commercial.bundle_text or "seller offer"
    return context.commercial.discount_text or None


def _cta_strategy(product_tag_required: bool) -> str:
    if product_tag_required:
        return "Use a factual TikTok Shop product-tag CTA after the product is shown."
    return "Use a factual next step without promising sales or virality outcomes."


def _hook_line(hook_type: str, product_name: str, pain: str, outcome: str) -> str:
    if hook_type == "result_first":
        return f"Here is the visible change after using {product_name}."
    if hook_type == "problem_first":
        return f"If {pain} keeps happening, watch this product demo."
    return f"Before making any claim, here is the proof for {product_name}."


def _overlay_text(hook_type: str, product_name: str) -> str:
    if hook_type == "result_first":
        return "Visible result"
    if hook_type == "problem_first":
        return "Watch the demo"
    return f"{product_name} proof"


def _opening_visual(hook_type: str, product_name: str, pain: str) -> str:
    if hook_type == "problem_first":
        return f"Show the buyer problem clearly: {pain}."
    if hook_type == "proof_first":
        return f"Show observable proof before naming {product_name}."
    return f"Open on the result, then reveal {product_name}."


def _feasibility(context: ProductContextV1, constraints: ViralKitConstraintsV1) -> str:
    if (
        constraints.production.max_duration_ms is not None
        and constraints.production.max_duration_ms < 8000
    ):
        return "low"
    if context.identity.category == "unknown":
        return "medium"
    return "high"


def _prohibited_claims(governance: ProductGovernanceV1) -> list[str]:
    values = [rule.text for rule in governance.claims if rule.rule_type == "prohibited"]
    values.extend(governance.prohibited_content)
    return _unique(values)


def _claim_guardrails(governance: GovernanceConstraintsV1) -> list[str]:
    values = list(governance.prohibited_claims)
    values.extend(governance.prohibited_content)
    return _unique(values) or ["avoid unsupported claims"]


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        clean = value.strip()
        if not clean or clean in seen:
            continue
        seen.add(clean)
        unique.append(clean)
    return unique


def _response_format(settings: Settings) -> dict[str, object]:
    if not settings.ai_supports_json_schema:
        return {"type": "json_object"}
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "ViralKitV1",
            "schema": ViralKitV1.model_json_schema(),
            "strict": True,
        },
    }
