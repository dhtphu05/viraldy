from __future__ import annotations

import hashlib
import json
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from viraldy.modules.adaptations.provider import LiveAdaptationProvider
from viraldy.modules.adaptations.repository import AdaptationRepository
from viraldy.modules.adaptations.schemas import AdaptationRunResponse, CreateAdaptationRequest
from viraldy.modules.ai_gateway.public import (
    ADAPTATION_PROMPT_VERSION,
    ADAPTATION_SCHEMA_VERSION,
    AiModelRunRepository,
)
from viraldy.modules.creative_dna.public import CreativeDnaRepository
from viraldy.modules.products.public import ProductQueries
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
        product = await self._products.get_product_summary(workspace_id, data.product_id)
        if product is None:
            raise NotFoundError("PRODUCT_NOT_FOUND", "Product was not found.")
        dna = await self._dna.get(workspace_id, data.creative_dna_version_id)
        if dna is None:
            raise NotFoundError("CREATIVE_DNA_NOT_FOUND", "Creative DNA version was not found.")
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
            )
            model_repo = AiModelRunRepository(self._session)
            input_summary = {
                "product_id": str(product.id),
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
                    product={"id": str(product.id), "name": product.name, "status": product.status},
                    dna_json=dna.dna_json,
                    objective=data.objective,
                    target_market=data.target_market,
                    target_buyer=data.target_buyer,
                    constraints=data.constraints,
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
            result = _fixture_adaptation(product.name, dna.dna_json, data.target_buyer)
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
        )
        await self._session.commit()
        return AdaptationRunResponse.model_validate(run)

    async def get(self, workspace_id: UUID, adaptation_id: UUID) -> AdaptationRunResponse:
        run = await self._repository.get(workspace_id, adaptation_id)
        if run is None:
            raise NotFoundError("ADAPTATION_NOT_FOUND", "Adaptation run was not found.")
        return AdaptationRunResponse.model_validate(run)


def _fixture_adaptation(
    product_name: str,
    dna_json: dict[str, object],
    target_buyer: dict[str, object],
) -> dict[str, object]:
    persona = str(target_buyer.get("persona") or "US apartment renter")
    pain = str(target_buyer.get("pain") or "limited counter space")
    evidence = dna_json.get("opening", {})
    evidence_ids = evidence.get("evidence_ids", []) if isinstance(evidence, dict) else []
    return {
        "keep": [
            {
                "element": "problem_first_structure",
                "reason": "The opening makes the buyer pain immediately visible.",
                "evidence_ids": evidence_ids,
            },
            {
                "element": "before_after_proof",
                "reason": "The transformation is easy to verify visually.",
            },
        ],
        "change": [
            {
                "element": "buyer_persona",
                "reason": (
                    f"Adapt the persona to {persona} and the product context for {product_name}."
                ),
            }
        ],
        "avoid": [
            {
                "element": "exact_script_copy",
                "reason": "Use the mechanism, not the original wording.",
            },
            {
                "element": "unsupported_superlatives",
                "reason": "Avoid claims that the product is best or guaranteed.",
            },
        ],
        "concepts": [
            {
                "id": "concept_1",
                "name": "Small apartment counter reset",
                "angle": "small_space_convenience",
                "buyer_persona": persona,
                "creator_persona": "budget home organizer",
                "hook": "This gave me half my counter back",
                "opening_visual": "crowded countertop",
                "demo_sequence": [
                    "show the clutter",
                    f"show the {product_name} close-up",
                    "demonstrate use",
                    "show the result",
                    "show TikTok Shop CTA",
                ],
                "proof": "before_after",
                "cta": "Linked in my TikTok Shop",
                "risks": [],
                "test_hypothesis": (
                    "Test whether space-saving value outperforms generic organization."
                ),
            },
            {
                "id": "concept_2",
                "name": "Morning rush fix",
                "angle": "faster_daily_routine",
                "buyer_persona": persona,
                "creator_persona": "busy home creator",
                "hook": "I stopped losing five minutes every morning",
                "opening_visual": "rushed kitchen routine",
                "demo_sequence": [
                    "show the bottleneck",
                    "install/use product",
                    "time the reset",
                    "show clean finish",
                    "CTA",
                ],
                "proof": "demonstration",
                "cta": "Check the product tag",
                "risks": [],
                "test_hypothesis": f"Test whether time-saving pain beats {pain}.",
            },
            {
                "id": "concept_3",
                "name": "Rental-friendly upgrade",
                "angle": "no_damage_home_upgrade",
                "buyer_persona": persona,
                "creator_persona": "renter lifestyle creator",
                "hook": "A no-drill fix for tiny kitchens",
                "opening_visual": "small rental kitchen",
                "demo_sequence": [
                    "show space constraint",
                    "show product details",
                    "demo setup",
                    "show before/after",
                    "CTA",
                ],
                "proof": "visual_result",
                "cta": "I put it in my TikTok Shop",
                "risks": [],
                "test_hypothesis": (
                    "Test whether renter-safe framing attracts higher intent buyers."
                ),
            },
        ],
    }


def _hash_json(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, default=str, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()
