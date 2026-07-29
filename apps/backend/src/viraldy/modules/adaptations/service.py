from __future__ import annotations

import hashlib
import json
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from viraldy.modules.adaptations.contracts import (
    AdaptationConceptV2,
    AdaptationConstraintsV2,
    AdaptationGuidanceV2,
    AdaptationInputV2,
    AdaptationOutputV2,
)
from viraldy.modules.adaptations.provider import LiveAdaptationProvider
from viraldy.modules.adaptations.repository import AdaptationRepository
from viraldy.modules.adaptations.schemas import AdaptationRunResponse, CreateAdaptationRequest
from viraldy.modules.ai_gateway.public import (
    ADAPTATION_PROMPT_VERSION,
    ADAPTATION_SCHEMA_VERSION,
    AiModelRunRepository,
)
from viraldy.modules.creative_dna.contracts import CreativeDnaV1
from viraldy.modules.creative_dna.public import CreativeDnaRepository
from viraldy.modules.products.contracts import ProductContextV1
from viraldy.modules.products.public import ProductContextSnapshot, ProductQueries
from viraldy.platform.config.settings import Settings
from viraldy.shared.errors.base import AppError, NotFoundError


class AdaptationService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings
        self._repository = AdaptationRepository(session)
        self._dna = CreativeDnaRepository(session)
        self._products = ProductQueries(session)

    async def create(
        self,
        workspace_id: UUID,
        user_id: UUID,
        data: CreateAdaptationRequest,
    ) -> AdaptationRunResponse:
        product = await self._products.get_product_context_snapshot(workspace_id, data.product_id)
        if product is None:
            raise NotFoundError("PRODUCT_NOT_FOUND", "Product was not found.")
        dna = await self._dna.get(workspace_id, data.creative_dna_version_id)
        if dna is None:
            raise NotFoundError("CREATIVE_DNA_NOT_FOUND", "Creative DNA version was not found.")
        adaptation_input = _adaptation_input(product, dna.dna_json, data)
        if self._settings.ai_mode != "fixture":
            run = await self._repository.create(
                workspace_id,
                user_id,
                data.product_id,
                data.creative_dna_version_id,
                data.objective,
                data.target_market,
                data.target_buyer,
                data.constraints,
                {},
                self._settings.ai_mode,
                self._settings.ai_text_model,
                status="processing",
                product_snapshot_json=product.product_context.model_dump(mode="json"),
            )
            model_repo = AiModelRunRepository(self._session)
            input_summary = {
                "product_id": str(product.product_id),
                "creative_dna_version_id": str(dna.id),
                "objective": data.objective,
                "target_market": data.target_market,
            }
            model_run = await model_repo.create_running(
                workspace_id=workspace_id,
                processing_job_id=None,
                subject_type="adaptation_run",
                subject_id=run.id,
                capability="generate_adaptation",
                analysis_mode=self._settings.ai_mode,
                provider=self._settings.ai_provider,
                model=str(self._settings.ai_text_model),
                prompt_version=ADAPTATION_PROMPT_VERSION,
                response_schema_version=ADAPTATION_SCHEMA_VERSION,
                request_hash=_hash_json(input_summary),
                input_summary=input_summary,
            )
            try:
                output = LiveAdaptationProvider(self._settings).generate(
                    product={
                        "id": str(product.product_id),
                        "context": adaptation_input.product_snapshot.model_dump(mode="json"),
                    },
                    dna_json=adaptation_input.creative_dna.model_dump(mode="json"),
                    objective=adaptation_input.objective,
                    target_market=adaptation_input.target_market,
                    target_buyer=adaptation_input.target_buyer,
                    constraints=adaptation_input.constraints.model_dump(mode="json"),
                )
            except AppError as exc:
                run.status = "failed"
                run.primary_model_run_id = model_run.id
                await model_repo.fail(model_run, exc.code, exc.message)
                await self._session.commit()
                raise
            result = output.model_dump(mode="json")
            run.result_json = result
            run.status = "completed"
            run.primary_model_run_id = model_run.id
            await model_repo.complete(
                model_run,
                {"concept_count": len(output.concepts)},
                http_status=None,
                provider_request_id=None,
                latency_ms=None,
            )
            await self._session.commit()
            return AdaptationRunResponse.model_validate(run)
        else:
            result = _fixture_adaptation(
                product,
                adaptation_input.creative_dna.model_dump(mode="json"),
                adaptation_input.target_buyer,
            )
        run = await self._repository.create(
            workspace_id,
            user_id,
            data.product_id,
            data.creative_dna_version_id,
            data.objective,
            data.target_market,
            data.target_buyer,
            data.constraints,
            result,
            self._settings.ai_mode,
            "fixture_adaptation_v1"
            if self._settings.ai_mode == "fixture"
            else self._settings.ai_text_model,
            product_snapshot_json=product.product_context.model_dump(mode="json"),
        )
        await self._session.commit()
        return AdaptationRunResponse.model_validate(run)

    async def get(self, workspace_id: UUID, adaptation_id: UUID) -> AdaptationRunResponse:
        run = await self._repository.get(workspace_id, adaptation_id)
        if run is None:
            raise NotFoundError("ADAPTATION_NOT_FOUND", "Adaptation run was not found.")
        return AdaptationRunResponse.model_validate(run)


def _adaptation_input(
    product: ProductContextSnapshot,
    dna_json: dict[str, object],
    data: CreateAdaptationRequest,
) -> AdaptationInputV2:
    try:
        creative_dna = CreativeDnaV1.model_validate(dna_json)
    except Exception as exc:
        raise AppError(
            "CREATIVE_DNA_SCHEMA_INVALID",
            "Adaptation requires CreativeDnaV1 input.",
        ) from exc
    try:
        constraints = AdaptationConstraintsV2.model_validate(data.constraints or {})
    except Exception as exc:
        raise AppError(
            "ADAPTATION_INPUT_INVALID",
            "Adaptation constraints are not valid AdaptationConstraintsV2.",
        ) from exc
    return AdaptationInputV2(
        product_snapshot=product.product_context,
        creative_dna=creative_dna,
        objective=data.objective,
        target_market=data.target_market,
        selected_persona_id=_selected_persona_id(data.target_buyer),
        target_buyer=data.target_buyer,
        constraints=constraints,
    )


def _fixture_adaptation(
    product_snapshot: ProductContextSnapshot,
    dna_json: dict[str, object],
    target_buyer: dict[str, object],
) -> dict[str, object]:
    context = product_snapshot.product_context
    product_name = context.identity.name
    persona = _persona_label(context, target_buyer)
    pain = _buyer_pain(context, target_buyer)
    desired_outcome = _desired_outcome(context, target_buyer)
    angle = _primary_angle(context)
    demo_mechanism = _demo_mechanism(context)
    proof = _proof_mechanism(context)
    guardrails = _claim_guardrails(context)
    evidence_ids = _dna_evidence_ids(dna_json)
    concepts = [
        AdaptationConceptV2(
            id="concept_1",
            name=f"{product_name} result opener",
            strategic_axis="result_first",
            angle=angle,
            buyer_persona_id=None,
            buyer_pain=pain,
            desired_outcome=desired_outcome,
            creator_persona=persona,
            delivery_style="authentic_review",
            hook_options=[f"Here is what changed after I tried {product_name}"],
            opening_visual="show the observed result first",
            demo_mechanism=demo_mechanism,
            demo_sequence=["show result", "show product close-up", demo_mechanism, proof],
            proof_mechanism=proof,
            offer_framing=None,
            cta_strategy="Use the product tag or shop cue when the campaign requires it.",
            claim_guardrails=guardrails,
            must_show=["product close-up", "demo in use", "observable result", "CTA if required"],
            risks=[],
            test_hypothesis="Test whether result-first framing improves retention.",
            source_evidence_ids=evidence_ids,
        ),
        AdaptationConceptV2(
            id="concept_2",
            name=f"{product_name} pain-to-demo",
            strategic_axis="problem_first",
            angle=angle,
            buyer_persona_id=None,
            buyer_pain=pain,
            desired_outcome=desired_outcome,
            creator_persona=persona,
            delivery_style="demonstration",
            hook_options=[f"If {pain} is familiar, watch the {product_name} demo"],
            opening_visual="show the buyer problem without exaggeration",
            demo_mechanism=demo_mechanism,
            demo_sequence=["show problem", "show product", demo_mechanism, "show outcome"],
            proof_mechanism=proof,
            offer_framing=None,
            cta_strategy="Ask viewers to check the product tag after proof is shown.",
            claim_guardrails=guardrails,
            must_show=["buyer problem", "product visible", "demo in use", "observable result"],
            risks=[],
            test_hypothesis="Test whether explicit pain framing increases qualified clicks.",
            source_evidence_ids=evidence_ids,
        ),
        AdaptationConceptV2(
            id="concept_3",
            name=f"{product_name} proof-led review",
            strategic_axis="proof_first",
            angle=angle,
            buyer_persona_id=None,
            buyer_pain=pain,
            desired_outcome=desired_outcome,
            creator_persona=persona,
            delivery_style="testimonial",
            hook_options=[f"I would only mention {product_name} after showing the proof"],
            opening_visual="show proof context before the claim",
            demo_mechanism=demo_mechanism,
            demo_sequence=["show proof setup", demo_mechanism, "show result", "state takeaway"],
            proof_mechanism=proof,
            offer_framing=None,
            cta_strategy="Keep CTA factual and separate from unsupported claims.",
            claim_guardrails=guardrails,
            must_show=["proof setup", "product in use", "result", "claim-safe CTA"],
            risks=[],
            test_hypothesis="Test whether proof-led ordering improves trust.",
            source_evidence_ids=evidence_ids,
        ),
    ]
    output = AdaptationOutputV2(
        guidance=[
            AdaptationGuidanceV2(
                element_type="creative_mechanism",
                source_path="creative_dna.reusable_mechanisms",
                action="keep",
                reason="Reuse observed mechanisms, not exact source wording.",
                evidence_ids=evidence_ids,
                product_context_refs=["creative", "governance"],
                risk_codes=[],
            ),
            AdaptationGuidanceV2(
                element_type="claims",
                source_path="product_context.governance",
                action="avoid",
                reason="Do not introduce claims unsupported by product governance or evidence.",
                evidence_ids=[],
                product_context_refs=["governance.claims"],
                risk_codes=["UNSUPPORTED_CLAIM"],
            ),
        ],
        concepts=concepts,
        uncertainties=[]
        if context.identity.category != "unknown"
        else ["product_category_unknown"],
    )
    return output.model_dump(mode="json")


def _selected_persona_id(target_buyer: dict[str, object]) -> str | None:
    persona_id = target_buyer.get("persona_id")
    return str(persona_id) if persona_id else None


def _persona_label(context: ProductContextV1, target_buyer: dict[str, object]) -> str:
    if context.personas:
        return context.personas[0].label
    return str(target_buyer.get("persona") or "unspecified buyer")


def _buyer_pain(context: ProductContextV1, target_buyer: dict[str, object]) -> str:
    if context.personas and context.personas[0].pain_points:
        return context.personas[0].pain_points[0]
    return str(target_buyer.get("pain") or "documented buyer pain")


def _desired_outcome(context: ProductContextV1, target_buyer: dict[str, object]) -> str:
    if context.personas and context.personas[0].desired_outcomes:
        return context.personas[0].desired_outcomes[0]
    return str(target_buyer.get("desired_outcome") or "documented product outcome")


def _primary_angle(context: ProductContextV1) -> str:
    if context.creative.primary_angles:
        return context.creative.primary_angles[0]
    if context.benefits:
        return context.benefits[0].label
    return f"{context.identity.name} observed use case"


def _demo_mechanism(context: ProductContextV1) -> str:
    if context.creative.demonstration_mechanisms:
        return context.creative.demonstration_mechanisms[0]
    visual_features = [
        feature.label for feature in context.features if feature.visual_demo_possible
    ]
    if visual_features:
        return f"show {visual_features[0]} in use"
    return "show the product in use"


def _proof_mechanism(context: ProductContextV1) -> str:
    if context.creative.available_proof:
        return context.creative.available_proof[0]
    return "show an observable result"


def _claim_guardrails(context: ProductContextV1) -> list[str]:
    guardrails = [rule.text for rule in context.governance.claims if rule.rule_type == "prohibited"]
    guardrails.extend(context.governance.prohibited_content)
    guardrails.extend(context.governance.required_disclosures)
    return guardrails or ["avoid unsupported claims"]


def _dna_evidence_ids(dna_json: dict[str, object]) -> list[UUID]:
    found: list[UUID] = []

    def visit(value: object) -> None:
        if isinstance(value, dict):
            evidence_ids = value.get("evidence_ids")
            if isinstance(evidence_ids, list):
                for evidence_id in evidence_ids:
                    try:
                        found.append(UUID(str(evidence_id)))
                    except ValueError:
                        continue
            for nested in value.values():
                visit(nested)
        elif isinstance(value, list):
            for nested in value:
                visit(nested)

    visit(dna_json)
    return list(dict.fromkeys(found))


def _hash_json(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, default=str, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()
