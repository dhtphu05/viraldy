from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from viraldy.modules.adaptations.contracts import AdaptationConceptV2
from viraldy.modules.ai_gateway.context import ViraldyOperationContextV1
from viraldy.modules.ai_gateway.execution import execute_structured_operation
from viraldy.modules.ai_gateway.operations import AiOperationName
from viraldy.modules.ai_gateway.prompt_packages import get_prompt_package
from viraldy.modules.campaign_packs.contracts import CampaignPackBriefV1
from viraldy.modules.products.contracts import ProductContextV1
from viraldy.platform.config.settings import Settings
from viraldy.shared.errors.base import AppError


@dataclass(frozen=True, slots=True)
class CampaignPackProviderExecution:
    output: CampaignPackBriefV1
    provider: str
    model: str
    endpoint_family: Literal["responses", "chat_completions"]
    provider_request_id: str | None
    http_status: int | None
    latency_ms: int | None
    usage_json: dict[str, object]
    repair_attempt_count: int


class CampaignPackGenerationProvider:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def generate_with_metadata(
        self,
        *,
        workspace_id: UUID,
        actor_user_id: UUID,
        model_run_id: UUID,
        product_id: UUID,
        product_context: ProductContextV1,
        product_context_version: int,
        adaptation_run_id: UUID,
        selected_concept: AdaptationConceptV2,
        objective: str,
        target_market: str,
        target_buyer: dict[str, object],
        adaptation_constraints: dict[str, object],
        deterministic_baseline: CampaignPackBriefV1,
    ) -> CampaignPackProviderExecution:
        if self._settings.ai_mode == "fixture":
            raise AppError(
                "CAMPAIGN_PACK_AI_MODE_INVALID",
                "Campaign Pack AI generation cannot run in fixture mode.",
            )
        prompt = get_prompt_package(AiOperationName.CAMPAIGN_PACK_GENERATE)
        context = ViraldyOperationContextV1(
            operation=AiOperationName.CAMPAIGN_PACK_GENERATE,
            request_id=str(model_run_id),
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
            product_context=product_context,
            product_context_version=product_context_version,
            objective=objective,
            target_market=target_market,
            source_version_ids=[adaptation_run_id],
            seller_constraints={
                "target_buyer": target_buyer,
                "adaptation_constraints": adaptation_constraints,
            },
            operation_payload={
                "product_id": str(product_id),
                "source_adaptation_run_id": str(adaptation_run_id),
                "selected_concept": selected_concept.model_dump(mode="json"),
                "protected_campaign_baseline": deterministic_baseline.model_dump(mode="json"),
            },
            schema_version=prompt.output_schema_version,
            prompt_version=prompt.prompt_version,
        )
        validator = build_campaign_pack_output_validator(deterministic_baseline)
        result = execute_structured_operation(
            self._settings,
            context,
            CampaignPackBriefV1,
            output_validator=validator,
        )
        endpoint_family: Literal["responses", "chat_completions"] = (
            "responses" if result.endpoint_family.value == "responses" else "chat_completions"
        )
        return CampaignPackProviderExecution(
            output=CampaignPackBriefV1.model_validate(result.parsed_output),
            provider=result.provider,
            model=result.model,
            endpoint_family=endpoint_family,
            provider_request_id=result.provider_request_id,
            http_status=result.http_status,
            latency_ms=result.latency_ms,
            usage_json=result.usage.model_dump(mode="json"),
            repair_attempt_count=result.repair_attempt_count,
        )


def build_campaign_pack_output_validator(
    expected: CampaignPackBriefV1,
) -> Callable[[BaseModel], None]:
    expected_requirements = _requirement_signatures(expected)

    def validate(output: BaseModel) -> None:
        brief = CampaignPackBriefV1.model_validate(output)
        if brief.product_snapshot != expected.product_snapshot:
            raise ValueError("Campaign Pack product snapshot changed.")
        if brief.source_adaptation_run_id != expected.source_adaptation_run_id:
            raise ValueError("Campaign Pack source adaptation changed.")
        if brief.source_concept_id != expected.source_concept_id:
            raise ValueError("Campaign Pack source concept changed.")
        if (
            brief.source_viral_kit_id is not None
            or brief.source_viral_kit_version is not None
            or brief.source_pattern_kit_version_ids
        ):
            raise ValueError("Campaign Pack concept provenance changed.")
        if brief.objective != expected.objective:
            raise ValueError("Campaign Pack objective changed.")
        if (
            brief.audience.persona_id != expected.audience.persona_id
            or brief.audience.persona_label != expected.audience.persona_label
        ):
            raise ValueError("Campaign Pack buyer context changed.")
        if brief.audience.persona_label.casefold() == brief.creator_direction.persona.casefold():
            raise ValueError("Campaign Pack merged buyer and creator personas.")
        if brief.creator_direction.persona != expected.creator_direction.persona:
            raise ValueError("Campaign Pack creator persona changed.")
        if set(brief.claim_guardrails.prohibited) != set(expected.claim_guardrails.prohibited):
            raise ValueError("Campaign Pack prohibited claims changed.")
        if set(brief.claim_guardrails.allowed) != set(expected.claim_guardrails.allowed):
            raise ValueError("Campaign Pack allowed claims changed.")
        if set(brief.claim_guardrails.allowed_with_qualification) != set(
            expected.claim_guardrails.allowed_with_qualification
        ):
            raise ValueError("Campaign Pack qualified claims changed.")
        if set(brief.claim_guardrails.required_disclosures) != set(
            expected.claim_guardrails.required_disclosures
        ):
            raise ValueError("Campaign Pack required disclosures changed.")
        if brief.rights_note != expected.rights_note:
            raise ValueError("Campaign Pack rights requirements changed.")
        if _requirement_signatures(brief) != expected_requirements:
            raise ValueError("Campaign Pack hard requirement semantics changed.")
        if (
            brief.cta.product_tag_required != expected.cta.product_tag_required
            or brief.cta.required_before_ms != expected.cta.required_before_ms
            or brief.cta.cta_type != expected.cta.cta_type
        ):
            raise ValueError("Campaign Pack CTA requirements changed.")
        rendered = _creator_facing_text(brief)
        for prohibited_claim in brief.claim_guardrails.prohibited:
            normalized = prohibited_claim.strip().casefold()
            if normalized and normalized in rendered:
                raise ValueError("Campaign Pack used a prohibited claim in creator copy.")

    return validate


def _requirement_signatures(
    brief: CampaignPackBriefV1,
) -> dict[str, tuple[str, str, int | None, str]]:
    return {
        requirement.id: (
            requirement.requirement_type,
            requirement.severity,
            requirement.expected_before_ms,
            requirement.source_path,
        )
        for requirement in brief.must_show
    }


def _creator_facing_text(brief: CampaignPackBriefV1) -> str:
    values = [
        brief.angle.name,
        brief.angle.promise,
        brief.angle.mechanism,
        brief.angle.emotional_driver,
        *(hook.spoken_text or "" for hook in brief.hooks),
        *(hook.overlay_text or "" for hook in brief.hooks),
        *(hook.opening_visual for hook in brief.hooks),
        *(beat.instruction for beat in brief.script_beats),
        *(scene.instruction for scene in brief.storyboard),
        *(scene.overlay_text or "" for scene in brief.storyboard),
        *(scene.spoken_direction or "" for scene in brief.storyboard),
        *brief.talking_points,
        *brief.text_overlays,
        *brief.proof_direction,
        *brief.offer_direction,
        brief.cta.spoken or "",
        brief.cta.overlay or "",
    ]
    return "\n".join(values).casefold()


def stable_json_hash(payload: dict[str, object]) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode(
            "utf-8"
        )
    ).hexdigest()
