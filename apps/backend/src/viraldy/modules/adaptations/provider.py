from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ValidationError

from viraldy.modules.adaptations.contracts import AdaptationOutputV2
from viraldy.modules.ai_gateway.public import (
    AiOperationName,
    OpenAICompatibleClient,
    StructuredGenerationResult,
    ViraldyOperationContextV1,
    execute_structured_operation,
    extract_message_json,
    get_prompt_package,
)
from viraldy.modules.products.contracts import ProductContextV1
from viraldy.platform.config.settings import Settings
from viraldy.shared.errors.base import AppError


@dataclass(frozen=True, slots=True)
class AdaptationProviderExecution:
    output: AdaptationOutputV2
    provider_result: StructuredGenerationResult | None


class LiveAdaptationProvider:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = OpenAICompatibleClient(settings)

    def generate(
        self,
        product: dict[str, object],
        dna_json: dict[str, object],
        objective: str,
        target_market: str,
        target_buyer: dict[str, object],
        constraints: dict[str, object],
    ) -> AdaptationOutputV2:
        return self.generate_with_metadata(
            product=product,
            dna_json=dna_json,
            objective=objective,
            target_market=target_market,
            target_buyer=target_buyer,
            constraints=constraints,
        ).output

    def generate_with_metadata(
        self,
        *,
        product: dict[str, object],
        dna_json: dict[str, object],
        objective: str,
        target_market: str,
        target_buyer: dict[str, object],
        constraints: dict[str, object],
        workspace_id: UUID | None = None,
        actor_user_id: UUID | None = None,
        model_run_id: UUID | None = None,
        product_context_version: int | None = None,
        creative_dna_version_id: UUID | None = None,
    ) -> AdaptationProviderExecution:
        prompt = get_prompt_package(AiOperationName.ADAPTATION_GENERATE)
        typed_context: ViraldyOperationContextV1 | None = None
        if workspace_id is not None and model_run_id is not None:
            typed_context = ViraldyOperationContextV1(
                operation=AiOperationName.ADAPTATION_GENERATE,
                request_id=str(model_run_id),
                workspace_id=workspace_id,
                actor_user_id=actor_user_id,
                product_context=ProductContextV1.model_validate(product["context"]),
                product_context_version=product_context_version,
                objective=objective,
                target_market=target_market,
                source_version_ids=(
                    [creative_dna_version_id] if creative_dna_version_id else []
                ),
                seller_constraints={
                    "target_buyer": target_buyer,
                    "adaptation_constraints": constraints,
                },
                operation_payload={
                    "product_id": product["id"],
                    "creative_dna": dna_json,
                    "model_run_id": str(model_run_id),
                },
                schema_version=prompt.output_schema_version,
                prompt_version=prompt.prompt_version,
            )
        if self._settings.ai_provider == "openai":
            if typed_context is None:
                raise AppError(
                    "OPENAI_DOMAIN_VALIDATION_FAILED",
                    "Native adaptation requires workspace and model-run context.",
                )
            result = execute_structured_operation(
                self._settings,
                typed_context,
                AdaptationOutputV2,
                output_validator=_native_adaptation_validator(
                    ProductContextV1.model_validate(product["context"]),
                    dna_json,
                ),
            )
            output = normalize_adaptation_output(
                AdaptationOutputV2.model_validate(result.parsed_output),
                ProductContextV1.model_validate(product["context"]),
                dna_json,
            )
            return AdaptationProviderExecution(
                output=output,
                provider_result=result,
            )

        if not self._settings.ai_base_url or not self._settings.ai_text_model:
            raise AppError(
                "AI_PROVIDER_NOT_CONFIGURED",
                "Provider adaptation requires AI_BASE_URL and AI_TEXT_MODEL.",
                status_code=503,
            )
        if self._settings.ai_mode == "live" and not self._settings.ai_api_key:
            raise AppError(
                "AI_PROVIDER_NOT_CONFIGURED",
                "Live adaptation requires AI_API_KEY.",
                status_code=503,
            )
        context_json = (
            typed_context.stable_json()
            if typed_context is not None
            else json.dumps(
                {
                    "operation": AiOperationName.ADAPTATION_GENERATE.value,
                    "product": product,
                    "creative_dna": dna_json,
                    "objective": objective,
                    "target_market": target_market,
                    "target_buyer": target_buyer,
                    "constraints": constraints,
                    "schema_version": prompt.output_schema_version,
                    "prompt_version": prompt.prompt_version,
                },
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        payload: dict[str, Any] = {
            "model": self._settings.ai_text_model,
            "messages": [
                {
                    "role": "system",
                    "content": prompt.system_prompt,
                },
                {
                    "role": "user",
                    "content": f"{prompt.developer_prompt}\n\n{context_json}",
                },
            ],
            "response_format": _response_format(self._settings),
        }
        if self._settings.ai_max_output_tokens is not None:
            payload["max_tokens"] = self._settings.ai_max_output_tokens
        raw = extract_message_json(self._client.chat_json(payload))
        output = _validate(raw)
        try:
            _native_adaptation_validator(
                ProductContextV1.model_validate(product["context"]),
                dna_json,
            )(output)
        except ValueError as exc:
            raise AppError(
                "ADAPTATION_OUTPUT_INVALID",
                "Live provider returned invalid adaptation provenance.",
            ) from exc
        return AdaptationProviderExecution(
            output=output,
            provider_result=None,
        )


def _native_adaptation_validator(
    product_context: ProductContextV1,
    dna_json: dict[str, object],
) -> Callable[[BaseModel], None]:
    allowed_evidence_ids = _evidence_ids(dna_json)
    required_guardrails = {
        claim.text
        for claim in product_context.governance.claims
        if claim.rule_type == "prohibited"
    }.union(product_context.governance.prohibited_content)
    product_name = product_context.identity.name.casefold()

    def validate(output: BaseModel) -> None:
        adaptation = normalize_adaptation_output(
            AdaptationOutputV2.model_validate(output),
            product_context,
            dna_json,
        )
        referenced_evidence_ids = {
            evidence_id
            for guidance in adaptation.guidance
            for evidence_id in guidance.evidence_ids
        }.union(
            evidence_id
            for concept in adaptation.concepts
            for evidence_id in concept.source_evidence_ids
        )
        if not referenced_evidence_ids.issubset(allowed_evidence_ids):
            raise ValueError("Adaptation references evidence outside Creative DNA.")
        for concept in adaptation.concepts:
            if concept.buyer_persona_label.casefold() == concept.creator_persona.casefold():
                raise ValueError("Adaptation merged buyer and creator personas.")
            if required_guardrails and not required_guardrails.issubset(
                concept.claim_guardrails
            ):
                raise ValueError("Adaptation dropped product claim guardrails.")
            rendered = " ".join(
                (
                    concept.name,
                    concept.angle,
                    concept.opening_visual,
                    concept.demo_mechanism,
                    concept.proof_mechanism,
                    concept.cta_strategy,
                )
            ).casefold()
            if product_name not in rendered:
                raise ValueError("Adaptation concept omitted the supplied product name.")

    return validate


def normalize_adaptation_output(
    output: AdaptationOutputV2,
    product_context: ProductContextV1,
    dna_json: dict[str, object],
) -> AdaptationOutputV2:
    allowed_evidence_ids = _evidence_ids(dna_json)
    required_guardrails = {
        claim.text
        for claim in product_context.governance.claims
        if claim.rule_type == "prohibited"
    }.union(product_context.governance.prohibited_content)
    payload = output.model_dump(mode="python")
    _prune_foreign_evidence_ids(payload, allowed_evidence_ids)
    _preserve_required_guardrails(payload, required_guardrails)
    _preserve_product_name(payload, product_context.identity.name)
    return AdaptationOutputV2.model_validate(payload)


def _prune_foreign_evidence_ids(value: object, allowed_evidence_ids: set[UUID]) -> None:
    if isinstance(value, dict):
        for key in ("evidence_ids", "source_evidence_ids"):
            raw_ids = value.get(key)
            if isinstance(raw_ids, list):
                value[key] = [
                    evidence_id
                    for evidence_id in raw_ids
                    if isinstance(evidence_id, UUID) and evidence_id in allowed_evidence_ids
                ]
        for nested in value.values():
            _prune_foreign_evidence_ids(nested, allowed_evidence_ids)
        return
    if isinstance(value, list):
        for nested in value:
            _prune_foreign_evidence_ids(nested, allowed_evidence_ids)


def _preserve_required_guardrails(
    payload: dict[str, object],
    required_guardrails: set[str],
) -> None:
    if not required_guardrails:
        return
    concepts = payload.get("concepts")
    if not isinstance(concepts, list):
        return
    for concept in concepts:
        if not isinstance(concept, dict):
            continue
        guardrails = concept.get("claim_guardrails")
        if not isinstance(guardrails, list):
            concept["claim_guardrails"] = sorted(required_guardrails)
            continue
        existing = {item for item in guardrails if isinstance(item, str)}
        concept["claim_guardrails"] = [
            item for item in guardrails if isinstance(item, str)
        ] + sorted(required_guardrails - existing)


def _preserve_product_name(payload: dict[str, object], product_name: str) -> None:
    product_name = product_name.strip()
    if not product_name:
        return
    concepts = payload.get("concepts")
    if not isinstance(concepts, list):
        return
    for concept in concepts:
        if not isinstance(concept, dict):
            continue
        rendered = " ".join(
            str(concept.get(key) or "")
            for key in (
                "name",
                "angle",
                "opening_visual",
                "demo_mechanism",
                "proof_mechanism",
                "cta_strategy",
            )
        ).casefold()
        if product_name.casefold() in rendered:
            continue
        current_name = str(concept.get("name") or "").strip()
        concept["name"] = f"{product_name} - {current_name}" if current_name else product_name


def _evidence_ids(payload: dict[str, object]) -> set[UUID]:
    found: set[UUID] = set()

    def visit(value: object) -> None:
        if isinstance(value, dict):
            evidence_ids = value.get("evidence_ids")
            if isinstance(evidence_ids, list):
                for evidence_id in evidence_ids:
                    try:
                        found.add(UUID(str(evidence_id)))
                    except ValueError:
                        continue
            for nested in value.values():
                visit(nested)
        elif isinstance(value, list):
            for nested in value:
                visit(nested)

    visit(payload)
    return found


def _validate(payload: dict[str, Any]) -> AdaptationOutputV2:
    try:
        return AdaptationOutputV2.model_validate(payload)
    except ValidationError as exc:
        raise AppError(
            "ADAPTATION_OUTPUT_INVALID",
            "Live provider returned invalid adaptation output.",
            details={"errors": exc.errors()},
        ) from exc


def _response_format(settings: Settings) -> dict[str, object]:
    if not settings.ai_supports_json_schema:
        return {"type": "json_object"}
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "AdaptationOutputV2",
            "schema": AdaptationOutputV2.model_json_schema(),
            "strict": True,
        },
    }
