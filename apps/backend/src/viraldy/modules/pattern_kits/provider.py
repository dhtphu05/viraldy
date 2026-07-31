from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Never, cast
from uuid import UUID

from pydantic import BaseModel

from viraldy.modules.ai_gateway.public import (
    PATTERN_KIT_PROMPT_VERSION,
    AiOperationName,
    EvidenceItemForModelV1,
    OpenAICompatibleClient,
    ProviderErrorCode,
    StructuredGenerationResult,
    StructuredOutputIssue,
    StructuredOutputValidationError,
    ViraldyOperationContextV1,
    execute_structured_operation,
    extract_message_json,
    get_prompt_package,
)
from viraldy.modules.creative_dna.contracts import CreativeDnaV1
from viraldy.modules.pattern_kits.contracts import (
    CreatorPatternV1,
    CtaPatternV1,
    DemoPatternV1,
    DropshippingApplicabilityV1,
    EditingPatternV1,
    NarrativePatternV1,
    OfferPatternV1,
    OpeningPatternV1,
    PatternAdaptationInstructionV1,
    PatternApplicabilityV1,
    PatternEvidenceRefV1,
    PatternKitProvenanceV1,
    PatternKitSourceV1,
    PatternKitV1,
    PatternPerformanceSummaryV1,
    PatternSequenceBeatV1,
    ProductRevealPatternV1,
    ProofPatternV1,
    SourceType,
)
from viraldy.modules.pattern_kits.schemas import CreatePatternKitRequest
from viraldy.platform.config.settings import Settings
from viraldy.shared.errors.base import AppError


@dataclass(frozen=True, slots=True)
class PatternEvidenceInput:
    id: UUID
    asset_version_id: UUID
    evidence_type: str
    source: str
    start_ms: int | None
    end_ms: int | None
    value_json: dict[str, object]
    confidence: float | None


@dataclass(frozen=True, slots=True)
class PatternSourceInput:
    creative_dna_version_id: UUID
    asset_version_id: UUID
    taxonomy_version: str
    dna: CreativeDnaV1
    evidence_by_id: dict[UUID, PatternEvidenceInput]


@dataclass(frozen=True, slots=True)
class PatternKitProviderExecution:
    output: PatternKitV1
    provider_result: StructuredGenerationResult | None


class LivePatternKitProvider:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = OpenAICompatibleClient(settings)

    def extract(
        self,
        *,
        pattern_kit_id: UUID,
        workspace_id: UUID,
        version: int,
        created_by: UUID,
        created_at: str,
        request: CreatePatternKitRequest,
        source_payloads: list[dict[str, object]],
        model_run_id: UUID,
    ) -> PatternKitV1:
        return self.extract_with_metadata(
            pattern_kit_id=pattern_kit_id,
            workspace_id=workspace_id,
            version=version,
            created_by=created_by,
            created_at=created_at,
            request=request,
            source_payloads=source_payloads,
            model_run_id=model_run_id,
        ).output

    def extract_with_metadata(
        self,
        *,
        pattern_kit_id: UUID,
        workspace_id: UUID,
        version: int,
        created_by: UUID,
        created_at: str,
        request: CreatePatternKitRequest,
        source_payloads: list[dict[str, object]],
        model_run_id: UUID,
        evidence_catalog: list[EvidenceItemForModelV1] | None = None,
        source_version_ids: list[UUID] | None = None,
    ) -> PatternKitProviderExecution:
        prompt = get_prompt_package(AiOperationName.PATTERN_KIT_EXTRACT)
        context = ViraldyOperationContextV1(
            operation=AiOperationName.PATTERN_KIT_EXTRACT,
            request_id=str(model_run_id),
            workspace_id=workspace_id,
            actor_user_id=created_by,
            objective=", ".join(request.objectives) or None,
            target_market=request.target_markets[0] if request.target_markets else None,
            source_version_ids=source_version_ids or [],
            evidence_catalog=evidence_catalog or [],
            seller_constraints={
                "primary_category": request.primary_category,
                "target_platforms": request.target_platforms,
                "target_markets": request.target_markets,
            },
            operation_payload={
                "pattern_kit_id": str(pattern_kit_id),
                "version": version,
                "created_at": created_at,
                "request": request.model_dump(mode="json"),
                "sources": source_payloads,
                "model_run_id": str(model_run_id),
            },
            schema_version=prompt.output_schema_version,
            prompt_version=prompt.prompt_version,
        )
        if self._settings.ai_provider == "openai":
            result = execute_structured_operation(
                self._settings,
                context,
                PatternKitV1,
                output_validator=_native_output_validator(
                    pattern_kit_id,
                    workspace_id,
                    version,
                    request,
                    source_payloads,
                ),
            )
            return PatternKitProviderExecution(
                output=PatternKitV1.model_validate(result.parsed_output),
                provider_result=result,
            )

        if not self._settings.ai_base_url or not self._settings.ai_text_model:
            raise AppError(
                "AI_PROVIDER_NOT_CONFIGURED",
                "PatternKit extraction requires AI_BASE_URL and AI_TEXT_MODEL.",
                status_code=503,
            )
        if self._settings.ai_mode == "live" and not self._settings.ai_api_key:
            raise AppError(
                "AI_PROVIDER_NOT_CONFIGURED",
                "Live PatternKit extraction requires AI_API_KEY.",
                status_code=503,
            )
        payload: dict[str, object] = {
            "model": self._settings.ai_text_model,
            "messages": [
                {
                    "role": "system",
                    "content": prompt.system_prompt,
                },
                {
                    "role": "user",
                    "content": f"{prompt.developer_prompt}\n\n{context.stable_json()}",
                },
            ],
            "response_format": _response_format(self._settings),
        }
        if self._settings.ai_max_output_tokens is not None:
            payload["max_tokens"] = self._settings.ai_max_output_tokens
        raw = extract_message_json(self._client.chat_json(payload))
        try:
            output = PatternKitV1.model_validate(raw)
            _native_output_validator(
                pattern_kit_id,
                workspace_id,
                version,
                request,
                source_payloads,
            )(output)
            return PatternKitProviderExecution(
                output=output,
                provider_result=None,
            )
        except ValueError as exc:
            raise AppError(
                "PATTERN_KIT_OUTPUT_INVALID",
                "Provider returned invalid PatternKit output.",
            ) from exc


def _native_output_validator(
    pattern_kit_id: UUID,
    workspace_id: UUID,
    version: int,
    request: CreatePatternKitRequest,
    source_payloads: list[dict[str, object]],
) -> Callable[[BaseModel], None]:
    expected_source_ids = [
        str(source["creative_dna_version_id"])
        for source in source_payloads
        if "creative_dna_version_id" in source
    ]

    def validate(output: BaseModel) -> None:
        pattern = PatternKitV1.model_validate(output)
        if (
            pattern.id != pattern_kit_id
            or pattern.workspace_id != workspace_id
            or pattern.version != version
        ):
            _reject_pattern_output("PatternKit identity changed.")
        if (
            pattern.name != request.name
            or pattern.kind != request.kind
            or pattern.scope != request.scope
        ):
            _reject_pattern_output("PatternKit request metadata changed.")
        observed_source_ids = [
            str(source_id) for source_id in pattern.source.creative_dna_version_ids
        ]
        if observed_source_ids != expected_source_ids:
            _reject_pattern_output("PatternKit source IDs changed.")
        if pattern.status != "candidate":
            _reject_pattern_output("New PatternKits must start as candidate.")
        if pattern.performance_summary.evidence_status != "none":
            _reject_pattern_output(
                "PatternKit cannot create unsupplied performance evidence."
            )
        _validate_native_pattern_evidence(pattern, source_payloads)
        _validate_native_anti_copy(pattern, source_payloads)

    return validate


def _validate_native_pattern_evidence(
    pattern: PatternKitV1,
    source_payloads: list[dict[str, object]],
) -> None:
    sources = {
        str(source["creative_dna_version_id"]): source
        for source in source_payloads
        if "creative_dna_version_id" in source
    }
    refs = [
        PatternEvidenceRefV1.model_validate(value)
        for value in _walk_payload(pattern.model_dump(mode="json"))
        if isinstance(value, dict)
        and {"creative_dna_version_id", "evidence_id", "feature_path"}.issubset(value)
    ]
    if not refs:
        _reject_pattern_output("PatternKit requires evidence references.")
    for ref in refs:
        source = sources.get(str(ref.creative_dna_version_id))
        if source is None:
            _reject_pattern_output(
                "PatternKit references an unknown Creative DNA source."
            )
        if str(source.get("asset_version_id")) != str(ref.asset_version_id):
            _reject_pattern_output("PatternKit evidence asset version changed.")
        evidence_ids = {
            str(item.get("evidence_id"))
            for item in _dict_list(source.get("evidence"))
            if item.get("evidence_id") is not None
        }
        if str(ref.evidence_id) not in evidence_ids:
            _reject_pattern_output("PatternKit references evidence outside the request.")
        dna = source.get("dna")
        if not isinstance(dna, dict) or not _payload_path_exists(dna, ref.feature_path):
            valid_paths = _feature_paths_for_evidence(source, ref.evidence_id)
            guidance = (
                f" Use one of these exact paths: {', '.join(valid_paths[:6])}."
                if valid_paths
                else ""
            )
            _reject_pattern_output(
                f"PatternKit feature_path '{ref.feature_path}' is not a Creative DNA field."
                f"{guidance}"
            )


def _validate_native_anti_copy(
    pattern: PatternKitV1,
    source_payloads: list[dict[str, object]],
) -> None:
    rendered = json.dumps(pattern.model_dump(mode="json"), sort_keys=True).casefold()
    for source in source_payloads:
        dna = source.get("dna")
        if not isinstance(dna, dict):
            continue
        for path in ("opening.hook_text", "cta.spoken_text", "cta.overlay_text"):
            payload = _payload_at_path(dna, path)
            text = str(payload.get("value") or "").strip()
            if len(text.split()) >= 8 and text.casefold() in rendered:
                _reject_pattern_output("PatternKit copied protected source expression.")


def _reject_pattern_output(message: str) -> Never:
    raise StructuredOutputValidationError(
        StructuredOutputIssue(
            code=ProviderErrorCode.DOMAIN_VALIDATION_FAILED,
            summary=message,
        )
    )


def _feature_paths_for_evidence(
    source_payload: dict[str, object],
    evidence_id: UUID,
) -> list[str]:
    catalog = source_payload.get("evidence_feature_paths")
    if not isinstance(catalog, dict):
        return []
    value = catalog.get(str(evidence_id))
    if not isinstance(value, list):
        return []
    return [str(path) for path in value if isinstance(path, str)]


def _evidence_feature_paths(dna_json: dict[str, object]) -> dict[str, list[str]]:
    paths_by_evidence: dict[str, list[str]] = {}

    def visit(value: object, path: str) -> None:
        if not isinstance(value, dict):
            return
        evidence_ids = value.get("evidence_ids")
        if path and isinstance(evidence_ids, list):
            for evidence_id in evidence_ids:
                key = str(evidence_id)
                paths_by_evidence.setdefault(key, []).append(path)
            return
        for key, item in value.items():
            visit(item, f"{path}.{key}" if path else key)

    visit(dna_json, "")
    return paths_by_evidence


def _walk_payload(value: object) -> list[object]:
    values = [value]
    if isinstance(value, dict):
        for item in value.values():
            values.extend(_walk_payload(item))
    elif isinstance(value, list):
        for item in value:
            values.extend(_walk_payload(item))
    return values


def _dict_list(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _payload_at_path(payload: dict[str, object], path: str) -> dict[str, object]:
    current: object = payload
    for part in path.split("."):
        if not isinstance(current, dict):
            return {}
        current = current.get(part)
    return current if isinstance(current, dict) else {}


def _payload_path_exists(payload: dict[str, object], path: str) -> bool:
    current: object = payload
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return False
        current = current[part]
    return True


def build_fixture_pattern_kit(
    *,
    pattern_kit_id: UUID,
    workspace_id: UUID,
    version: int,
    created_by: UUID,
    created_at: datetime,
    request: CreatePatternKitRequest,
    sources: list[PatternSourceInput],
    model_run_id: UUID | None,
) -> PatternKitV1:
    hook_refs = _refs_for_path(sources, "opening.primary_hook_type")
    hook_text_refs = _refs_for_path(sources, "opening.hook_text")
    opening_refs = _merge_refs(
        hook_refs,
        hook_text_refs,
        _refs_for_path(sources, "opening.opening_visual"),
    )
    product_refs = _merge_refs(
        _refs_for_path(sources, "product.first_appearance_ms"),
        _refs_for_path(sources, "product.appearance_sequence"),
    )
    demo_refs = _merge_refs(
        _refs_for_path(sources, "demo.demo_type"),
        _refs_for_path(sources, "demo.steps"),
    )
    proof_refs = _refs_for_path(sources, "proof.proof_types")
    creator_refs = _refs_for_path(sources, "creator.delivery_style")
    editing_refs = _refs_for_path(sources, "editing.pacing")
    offer_refs = _refs_for_path(sources, "offer.offer_types")
    cta_refs = _refs_for_path(sources, "cta.cta_types")
    all_refs = _merge_refs(
        opening_refs,
        product_refs,
        demo_refs,
        proof_refs,
        creator_refs,
        editing_refs,
        offer_refs,
        cta_refs,
    )
    if not all_refs:
        raise AppError(
            "PATTERN_KIT_EVIDENCE_INVALID",
            "PatternKit extraction requires at least one resolvable evidence reference.",
        )

    sequence = _sequence(opening_refs, product_refs, demo_refs, proof_refs, offer_refs, cta_refs)
    return PatternKitV1(
        id=pattern_kit_id,
        workspace_id=workspace_id,
        version=version,
        name=request.name,
        summary=_summary(request, sources, sequence),
        kind=request.kind,
        scope=request.scope,
        status="candidate",
        source=PatternKitSourceV1(
            creative_dna_version_ids=[source.creative_dna_version_id for source in sources],
            source_asset_count=len({source.asset_version_id for source in sources}),
            source_category_count=1,
            extraction_mode="deterministic_fixture",
        ),
        sequence=sequence,
        opening=_opening_pattern(sources, opening_refs),
        product_reveal=_product_reveal_pattern(sources, product_refs),
        narrative=_narrative_pattern(sources, opening_refs),
        demo=_demo_pattern(sources, demo_refs),
        proof=_proof_pattern(sources, proof_refs),
        creator=_creator_pattern(sources, creator_refs),
        editing=_editing_pattern(sources, editing_refs),
        offer=_offer_pattern(sources, offer_refs),
        cta=_cta_pattern(sources, cta_refs),
        applicability=_applicability(request),
        adaptation_instructions=_adaptation_instructions(demo_refs, proof_refs, cta_refs),
        performance_summary=PatternPerformanceSummaryV1(
            evidence_status="none",
            asset_count=0,
            campaign_count=0,
            date_range_start=None,
            date_range_end=None,
            metrics=[],
            caveats=["No performance data is linked yet."],
            confidence="low",
        ),
        overall_confidence=_overall_confidence(sources, all_refs),
        uncertainties=_uncertainties(sources),
        created_by=created_by,
        created_at=created_at,
        provenance=PatternKitProvenanceV1(
            taxonomy_version=_taxonomy_version(sources),
            model_run_id=model_run_id,
            prompt_version=PATTERN_KIT_PROMPT_VERSION,
        ),
    )


def _sequence(
    opening_refs: list[PatternEvidenceRefV1],
    product_refs: list[PatternEvidenceRefV1],
    demo_refs: list[PatternEvidenceRefV1],
    proof_refs: list[PatternEvidenceRefV1],
    offer_refs: list[PatternEvidenceRefV1],
    cta_refs: list[PatternEvidenceRefV1],
) -> list[PatternSequenceBeatV1]:
    candidates = [
        ("hook", "hook", "Establish the reusable opening mechanism.", opening_refs, "required"),
        (
            "product_reveal",
            "product_reveal",
            "Reveal the product early enough to ground the story.",
            product_refs,
            "required",
        ),
        ("demo", "demo", "Show an observable use or transformation.", demo_refs, "required"),
        ("proof", "proof", "Show proof only when evidence supports it.", proof_refs, "recommended"),
        ("offer", "offer", "Carry offer mechanics only when observed.", offer_refs, "optional"),
        ("cta", "cta", "Close with a platform-native action.", cta_refs, "recommended"),
    ]
    beats: list[PatternSequenceBeatV1] = []
    for beat_id, beat_type, purpose, refs, requiredness in candidates:
        if not refs and requiredness != "required":
            continue
        if not refs and requiredness == "required":
            continue
        beats.append(
            PatternSequenceBeatV1(
                beat_id=beat_id,
                order=len(beats) + 1,
                beat_type=beat_type,
                purpose=purpose,
                recommended_start_ms_min=_min_start(refs),
                recommended_start_ms_max=_max_start(refs),
                recommended_duration_ms_min=_min_duration(refs),
                recommended_duration_ms_max=_max_duration(refs),
                requiredness=requiredness,
                evidence_refs=refs,
                confidence=_confidence(refs),
            )
        )
    return beats


def _opening_pattern(
    sources: list[PatternSourceInput],
    refs: list[PatternEvidenceRefV1],
) -> OpeningPatternV1:
    hook_types = _values(sources, "opening.primary_hook_type")
    return OpeningPatternV1(
        primary_hook_types=hook_types,
        hook_mechanism=_or_unknown(_first(hook_types)),
        opening_visual_pattern="Open with a visible problem, result, or context cue.",
        first_three_second_structure=_or_unknown(
            _first(_values(sources, "opening.first_three_second_structure"))
        ),
        face_presence_preference=_preference(sources, "opening.face_present"),
        product_presence_preference=_preference(sources, "opening.product_present"),
        pattern_interrupt_strategy="Use only observed pattern interrupts; do not invent one.",
        evidence_refs=refs,
        confidence=_confidence(refs),
        uncertainties=_missing_note(refs, "opening"),
    )


def _product_reveal_pattern(
    sources: list[PatternSourceInput],
    refs: list[PatternEvidenceRefV1],
) -> ProductRevealPatternV1:
    appearances = _int_values(sources, "product.first_appearance_ms")
    return ProductRevealPatternV1(
        first_appearance_window_ms=(
            min(appearances) if appearances else None,
            max(appearances) if appearances else None,
        ),
        preferred_shot_types=_extract_sequence_values(
            sources,
            "product.appearance_sequence",
            "shot_type",
        ),
        close_up_expectation=_preference(sources, "product.close_up_present"),
        usage_visibility_expectation=_preference(sources, "product.usage_present"),
        screen_time_guidance=_or_unknown(_first(_values(sources, "product.screen_time_ratio"))),
        reveal_role="Ground the pattern in observable product presence.",
        product_match_requirement="The shown product must match the target product context.",
        evidence_refs=refs,
        confidence=_confidence(refs),
        uncertainties=_missing_note(refs, "product reveal"),
    )


def _narrative_pattern(
    sources: list[PatternSourceInput],
    refs: list[PatternEvidenceRefV1],
) -> NarrativePatternV1:
    return NarrativePatternV1(
        structures=_values(sources, "narrative.structure"),
        angle_family=_or_unknown(_first(_values(sources, "narrative.angle"))),
        buyer_pain_pattern=_or_unknown(_first(_values(sources, "narrative.buyer_pain"))),
        desired_outcome_pattern=_or_unknown(_first(_values(sources, "narrative.desired_outcome"))),
        emotional_drivers=_values(sources, "narrative.emotional_drivers"),
        awareness_stage=_or_unknown(_first(_values(sources, "narrative.awareness_stage"))),
        narrative_progression=["hook", "product_reveal", "demo", "proof", "cta"],
        evidence_refs=refs,
        confidence=_confidence(refs),
        uncertainties=_missing_note(refs, "narrative"),
    )


def _demo_pattern(
    sources: list[PatternSourceInput],
    refs: list[PatternEvidenceRefV1],
) -> DemoPatternV1:
    return DemoPatternV1(
        demo_types=_values(sources, "demo.demo_type"),
        mechanism_pattern=_or_unknown(_first(_values(sources, "demo.mechanism_clarity"))),
        required_steps=_extract_sequence_values(sources, "demo.steps", "action"),
        before_state_expectation=_or_unknown(_first(_values(sources, "demo.before_state_visible"))),
        after_state_expectation=_or_unknown(_first(_values(sources, "demo.after_state_visible"))),
        result_visibility_expectation=_or_unknown(_first(_values(sources, "demo.result_clarity"))),
        continuity_expectation="Maintain visible continuity for the demonstrated mechanism.",
        demo_failure_modes=["unclear mechanism", "result not visible", "product out of frame"],
        evidence_refs=refs,
        confidence=_confidence(refs),
        uncertainties=_missing_note(refs, "demo"),
    )


def _proof_pattern(
    sources: list[PatternSourceInput],
    refs: list[PatternEvidenceRefV1],
) -> ProofPatternV1:
    proof_types = _values(sources, "proof.proof_types")
    return ProofPatternV1(
        proof_types=proof_types,
        proof_mechanism=_or_unknown(_first(proof_types)),
        verifiability_requirement=_or_unknown(_first(_values(sources, "proof.verifiability"))),
        proof_timing_guidance=_timing_guidance(refs),
        proof_strength_conditions=["observable proof only", "avoid unsupported claims"],
        unsupported_proof_risks=["claim without evidence", "before/after without clear view"],
        evidence_refs=refs,
        confidence=_confidence(refs),
        uncertainties=_missing_note(refs, "proof"),
    )


def _creator_pattern(
    sources: list[PatternSourceInput],
    refs: list[PatternEvidenceRefV1],
) -> CreatorPatternV1:
    return CreatorPatternV1(
        creator_personas=_values(sources, "creator.creator_persona"),
        delivery_styles=_values(sources, "creator.delivery_style"),
        face_presence_preference=_preference(sources, "creator.face_present"),
        speaking_preference="Use speech only when it fits creator constraints.",
        emotion_range=_values(sources, "creator.emotion"),
        pacing_preference=_or_unknown(_first(_values(sources, "creator.pacing"))),
        authenticity_cues=_values(sources, "creator.authenticity_cues"),
        sales_language_intensity=_or_unknown(
            _first(_values(sources, "creator.sales_language_intensity"))
        ),
        creator_constraints=["Do not reuse a source creator's identity or exact delivery."],
        evidence_refs=refs,
        confidence=_confidence(refs),
        uncertainties=_missing_note(refs, "creator"),
    )


def _editing_pattern(
    sources: list[PatternSourceInput],
    refs: list[PatternEvidenceRefV1],
) -> EditingPatternV1:
    return EditingPatternV1(
        pacing=_or_unknown(_first(_values(sources, "editing.pacing"))),
        cut_density=_or_unknown(_first(_values(sources, "editing.cut_count"))),
        first_three_second_cut_guidance=_or_unknown(
            _first(_values(sources, "editing.first_three_second_cut_count"))
        ),
        caption_density=_or_unknown(_first(_values(sources, "editing.caption_density"))),
        transition_types=_values(sources, "editing.transition_types"),
        pattern_interrupt_guidance=_extract_sequence_values(
            sources,
            "editing.pattern_interrupts",
            "type",
        ),
        dead_air_tolerance=_preference(sources, "editing.dead_air_present"),
        visual_safe_zone_guidance=["Keep critical text and product cues inside safe zones."],
        evidence_refs=refs,
        confidence=_confidence(refs),
        uncertainties=_missing_note(refs, "editing"),
    )


def _offer_pattern(
    sources: list[PatternSourceInput],
    refs: list[PatternEvidenceRefV1],
) -> OfferPatternV1:
    offer_types = _values(sources, "offer.offer_types")
    return OfferPatternV1(
        offer_required=bool(offer_types),
        offer_types=offer_types,
        offer_positioning_pattern="Use offer mechanics only when supported by product context.",
        offer_timing_guidance=_timing_guidance(refs),
        urgency_policy=_preference(sources, "offer.urgency_present"),
        price_display_policy=_or_unknown(_first(_values(sources, "offer.price_text"))),
        commerce_constraints=["Carry only seller-provided commercial facts."],
        evidence_refs=refs,
        confidence=_confidence(refs),
        uncertainties=_missing_note(refs, "offer"),
    )


def _cta_pattern(
    sources: list[PatternSourceInput],
    refs: list[PatternEvidenceRefV1],
) -> CtaPatternV1:
    cta_types = _values(sources, "cta.cta_types")
    return CtaPatternV1(
        cta_required=bool(cta_types),
        cta_types=cta_types,
        modalities=["spoken", "overlay"] if refs else [],
        product_tag_expectation=_preference(sources, "cta.product_tag_visible"),
        cta_timing_guidance=_timing_guidance(refs),
        cta_language_pattern="Use a platform-native CTA without copying source wording.",
        cta_failure_modes=["CTA missing", "CTA too late", "product tag not visible when required"],
        evidence_refs=refs,
        confidence=_confidence(refs),
        uncertainties=_missing_note(refs, "cta"),
    )


def _applicability(request: CreatePatternKitRequest) -> PatternApplicabilityV1:
    return PatternApplicabilityV1(
        suitable_categories=[request.primary_category],
        unsuitable_categories=[],
        required_product_traits=[],
        preferred_product_traits=["observable product presence", "clear buyer context"],
        buyer_contexts=["unknown"],
        markets=list(request.target_markets),
        platforms=list(request.target_platforms),
        objectives=list(request.objectives),
        fulfillment_constraints=["Use only seller-confirmed shipping and fulfillment claims."],
        compliance_sensitivities=[
            "Preserve prohibited claims and disclosures from Product Context."
        ],
        pod_context=None,
        dropshipping_context=DropshippingApplicabilityV1(
            visual_demo_required=True,
            trust_mechanisms=["observable use", "clear product view"],
            shipping_promise_constraints=["Do not invent shipping promises."],
            quality_proof_requirements=["Use observable proof."],
            margin_or_offer_constraints=["Use only seller-provided offer data."],
            claim_risks=["unsupported performance or guarantee claims"],
        ),
    )


def _adaptation_instructions(
    demo_refs: list[PatternEvidenceRefV1],
    proof_refs: list[PatternEvidenceRefV1],
    cta_refs: list[PatternEvidenceRefV1],
) -> list[PatternAdaptationInstructionV1]:
    return [
        PatternAdaptationInstructionV1(
            element_path="demo.mechanism",
            instruction_type="keep",
            instruction="Retain the structural demo mechanism, not the exact scene or wording.",
            rationale="The pattern is reusable only when the observable mechanism transfers.",
            evidence_refs=demo_refs,
            severity="high",
        ),
        PatternAdaptationInstructionV1(
            element_path="proof",
            instruction_type="change",
            instruction="Replace proof with evidence available for the target product.",
            rationale="Proof must be product-specific and verifiable.",
            evidence_refs=proof_refs,
            severity="high",
        ),
        PatternAdaptationInstructionV1(
            element_path="cta",
            instruction_type="avoid",
            instruction="Do not copy exact source CTA wording or imply guaranteed sales.",
            rationale="CTA must match the target offer, rights, and platform constraints.",
            evidence_refs=cta_refs,
            severity="hard",
        ),
    ]


def _refs_for_path(
    sources: list[PatternSourceInput],
    feature_path: str,
) -> list[PatternEvidenceRefV1]:
    refs: list[PatternEvidenceRefV1] = []
    for source in sources:
        field_payload = _field_payload(source.dna.model_dump(), feature_path)
        if not _is_observed(field_payload):
            continue
        evidence_ids = field_payload.get("evidence_ids")
        if not isinstance(evidence_ids, list):
            continue
        for raw_evidence_id in evidence_ids:
            evidence_id = UUID(str(raw_evidence_id))
            evidence = source.evidence_by_id.get(evidence_id)
            if evidence is None:
                continue
            refs.append(
                PatternEvidenceRefV1(
                    creative_dna_version_id=source.creative_dna_version_id,
                    asset_version_id=source.asset_version_id,
                    evidence_id=evidence_id,
                    feature_path=feature_path,
                    source_type=_source_type(evidence.source),
                    start_ms=evidence.start_ms,
                    end_ms=evidence.end_ms,
                    observation_summary=f"{evidence.evidence_type} supports {feature_path}",
                    confidence=float(
                        cast(
                            str | float,
                            field_payload.get("confidence") or evidence.confidence or 0.5,
                        )
                    ),
                )
            )
    return refs


def _field_payload(dna_json: dict[str, object], path: str) -> dict[str, object]:
    current: object = dna_json
    for part in path.split("."):
        if not isinstance(current, dict):
            return {}
        current = current.get(part)
    return current if isinstance(current, dict) else {}


def _is_observed(field_payload: dict[str, object]) -> bool:
    return field_payload.get("status") in {"observed", "inferred"} and field_payload.get(
        "value"
    ) not in (None, [], {})


def _values(sources: list[PatternSourceInput], path: str) -> list[str]:
    values: list[str] = []
    for source in sources:
        payload = _field_payload(source.dna.model_dump(), path)
        if not _is_observed(payload):
            continue
        raw = payload.get("value")
        if isinstance(raw, list):
            values.extend(_stringify(item) for item in raw if item not in (None, "", []))
        elif raw not in (None, ""):
            values.append(_stringify(raw))
    return _unique(values)


def _int_values(sources: list[PatternSourceInput], path: str) -> list[int]:
    values: list[int] = []
    for source in sources:
        payload = _field_payload(source.dna.model_dump(), path)
        if _is_observed(payload):
            raw = payload.get("value")
            if isinstance(raw, int):
                values.append(raw)
    return values


def _extract_sequence_values(
    sources: list[PatternSourceInput],
    path: str,
    key: str,
) -> list[str]:
    values: list[str] = []
    for source in sources:
        payload = _field_payload(source.dna.model_dump(), path)
        if not _is_observed(payload):
            continue
        raw = payload.get("value")
        if not isinstance(raw, list):
            continue
        for item in raw:
            if isinstance(item, dict) and item.get(key) not in (None, ""):
                values.append(str(item[key]))
    return _unique(values)


def _preference(sources: list[PatternSourceInput], path: str) -> str:
    values = _values(sources, path)
    if not values:
        return "unknown"
    if set(values) == {"true"}:
        return "preferred"
    if set(values) == {"false"}:
        return "not_required"
    return "mixed"


def _summary(
    request: CreatePatternKitRequest,
    sources: list[PatternSourceInput],
    sequence: list[PatternSequenceBeatV1],
) -> str:
    hook = _or_unknown(_first(_values(sources, "opening.primary_hook_type")))
    beat_names = ", ".join(beat.beat_type for beat in sequence)
    return (
        f"{request.name} abstracts a {hook} structure for {request.primary_category} "
        f"using observed beats: {beat_names}."
    )


def _overall_confidence(
    sources: list[PatternSourceInput],
    refs: list[PatternEvidenceRefV1],
) -> str:
    if len(sources) >= 2 and len(refs) >= 6:
        return "high"
    if len(refs) >= 3:
        return "medium"
    return "low"


def _uncertainties(sources: list[PatternSourceInput]) -> list[str]:
    values: list[str] = []
    for source in sources:
        values.extend(source.dna.uncertainties)
    for path in (
        "opening.primary_hook_type",
        "product.first_appearance_ms",
        "demo.demo_type",
        "proof.proof_types",
        "creator.delivery_style",
        "editing.pacing",
        "offer.offer_types",
        "cta.cta_types",
    ):
        observed = {value for source in sources for value in _values([source], path)}
        if len(observed) > 1:
            values.append(f"Source Creative DNA versions disagree on {path}.")
    return _unique(values) or ["No performance data is linked yet."]


def _taxonomy_version(sources: list[PatternSourceInput]) -> str:
    versions = _unique([source.taxonomy_version for source in sources])
    return versions[0] if len(versions) == 1 else ",".join(versions)


def _confidence(refs: list[PatternEvidenceRefV1]) -> float:
    if not refs:
        return 0
    return round(sum(ref.confidence for ref in refs) / len(refs), 3)


def _merge_refs(*groups: list[PatternEvidenceRefV1]) -> list[PatternEvidenceRefV1]:
    refs: list[PatternEvidenceRefV1] = []
    seen: set[tuple[UUID, str]] = set()
    for group in groups:
        for ref in group:
            key = (ref.evidence_id, ref.feature_path)
            if key in seen:
                continue
            seen.add(key)
            refs.append(ref)
    return refs


def _min_start(refs: list[PatternEvidenceRefV1]) -> int | None:
    starts = [ref.start_ms for ref in refs if ref.start_ms is not None]
    return min(starts) if starts else None


def _max_start(refs: list[PatternEvidenceRefV1]) -> int | None:
    starts = [ref.start_ms for ref in refs if ref.start_ms is not None]
    return max(starts) if starts else None


def _min_duration(refs: list[PatternEvidenceRefV1]) -> int | None:
    durations = _durations(refs)
    return min(durations) if durations else None


def _max_duration(refs: list[PatternEvidenceRefV1]) -> int | None:
    durations = _durations(refs)
    return max(durations) if durations else None


def _durations(refs: list[PatternEvidenceRefV1]) -> list[int]:
    return [
        ref.end_ms - ref.start_ms
        for ref in refs
        if ref.start_ms is not None and ref.end_ms is not None
    ]


def _timing_guidance(refs: list[PatternEvidenceRefV1]) -> str:
    start = _min_start(refs)
    end = _max_start(refs)
    if start is None or end is None:
        return "unknown"
    return f"Observed between {start}ms and {end}ms."


def _missing_note(refs: list[PatternEvidenceRefV1], area: str) -> list[str]:
    return [] if refs else [f"No resolved evidence for {area}."]


def _source_type(source: str) -> SourceType:
    if source == "spoken":
        return "asr"
    if source in {"vision", "asr", "ocr", "derived", "human_correction", "performance"}:
        return cast(SourceType, source)
    return "derived"


def _first(values: list[str]) -> str | None:
    return values[0] if values else None


def _or_unknown(value: str | None) -> str:
    return value if value else "unknown"


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        unique.append(value)
    return unique


def _stringify(value: object) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, sort_keys=True)


def _response_format(settings: Settings) -> dict[str, object]:
    if not settings.ai_supports_json_schema:
        return {"type": "json_object"}
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "PatternKitV1",
            "schema": PatternKitV1.model_json_schema(),
            "strict": True,
        },
    }
