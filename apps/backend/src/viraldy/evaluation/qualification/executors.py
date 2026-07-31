from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from typing import Protocol, cast, runtime_checkable
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from pydantic import BaseModel

from viraldy.evaluation.golden import (
    GoldenSemanticOutputV1,
    load_golden_fixture,
)
from viraldy.evaluation.qualification.contracts import (
    OperationExecutionV1,
    QualificationCaseExecutionV1,
    QualificationMode,
)
from viraldy.modules.ai_gateway.context import ViraldyOperationContextV1
from viraldy.modules.ai_gateway.execution import execute_structured_operation
from viraldy.modules.ai_gateway.operations import (
    AiOperationName,
    build_ai_operation_fixture,
    get_ai_operation_definition,
)
from viraldy.modules.ai_gateway.prompt_packages import get_prompt_package
from viraldy.modules.ai_gateway.providers.base import (
    AiProvider,
    InputTextPart,
    ProviderEndpointFamily,
    StructuredGenerationRequest,
)
from viraldy.modules.ai_gateway.providers.router import build_ai_provider
from viraldy.platform.config.settings import Settings

_QUALIFICATION_PROMPT_VERSION = "openai_semantic_qualification_v2"
_QUALIFICATION_SCHEMA_VERSION = "golden_semantic_output_v1"


@runtime_checkable
class QualificationExecutor(Protocol):
    def execute_operation(
        self,
        operation: AiOperationName,
        scenario_id: str,
    ) -> OperationExecutionV1: ...

    def execute_case(
        self,
        scenario_id: str,
        operations: Sequence[AiOperationName],
    ) -> QualificationCaseExecutionV1: ...


class DeterministicQualificationExecutor:
    def __init__(self, *, mode: QualificationMode) -> None:
        if mode == "live":
            raise ValueError("the deterministic executor cannot qualify live mode")
        self._mode = mode

    def execute_operation(
        self,
        operation: AiOperationName,
        scenario_id: str,
    ) -> OperationExecutionV1:
        definition = get_ai_operation_definition(operation)
        input_payload = _operation_input(operation, scenario_id)
        output = build_ai_operation_fixture(operation, input_payload)
        validated_output = definition.output_contract.model_validate(output)
        request_id = (
            f"mock-{_stable_id(scenario_id, operation.value, 'provider-request')}"
            if self._mode == "mock"
            else None
        )
        return OperationExecutionV1(
            operation=operation.value,
            provider=self._mode,
            endpoint_family=ProviderEndpointFamily.RESPONSES.value,
            model=f"{self._mode}-deterministic",
            prompt_name=definition.prompt_name,
            prompt_version=definition.prompt_version,
            schema_version=definition.schema_version,
            provider_request_id=request_id,
            output=cast(
                dict[str, object],
                validated_output.model_dump(mode="json"),
            ),
            output_valid=True,
            source_version_references_valid=True,
            evidence_ids_valid=_operation_evidence_ids_valid(
                operation,
                validated_output,
            ),
            timestamps_valid=True,
            silent_fixture_fallback=False,
        )

    def execute_case(
        self,
        scenario_id: str,
        operations: Sequence[AiOperationName],
    ) -> QualificationCaseExecutionV1:
        fixture = load_golden_fixture(scenario_id)
        semantic_output = GoldenSemanticOutputV1(
            scenario_id=fixture.scenario_id,
            product_name=fixture.product_name,
            objective=fixture.objective,
            pattern_name=fixture.pattern_name,
            concepts=fixture.concepts,
            preflight_results=fixture.preflight_expectations,
        )
        return QualificationCaseExecutionV1(
            scenario_id=scenario_id,
            semantic_output=semantic_output,
            operation_results=[
                self.execute_operation(operation, scenario_id)
                for operation in operations
            ],
            semantic_provider_request_id=(
                f"mock-{_stable_id(scenario_id, 'semantic', 'provider-request')}"
                if self._mode == "mock"
                else None
            ),
            semantic_model=f"{self._mode}-deterministic",
        )


class OpenAIQualificationExecutor:
    def __init__(
        self,
        *,
        settings: Settings,
        provider: AiProvider | None = None,
    ) -> None:
        if settings.ai_mode != "live" or settings.ai_provider != "openai":
            raise ValueError(
                "OpenAI qualification requires AI_MODE=live and AI_PROVIDER=openai"
            )
        self._settings = settings
        self._provider = provider or build_ai_provider(settings)

    def execute_operation(
        self,
        operation: AiOperationName,
        scenario_id: str,
    ) -> OperationExecutionV1:
        fixture = load_golden_fixture(scenario_id)
        scenario = _scenario_input(scenario_id)
        definition = get_ai_operation_definition(operation)
        prompt = get_prompt_package(operation)
        input_payload = _operation_input(operation, scenario_id)
        request_id = str(uuid4())
        context = ViraldyOperationContextV1(
            operation=operation,
            request_id=request_id,
            workspace_id=UUID(str(input_payload["workspace_id"])),
            objective=fixture.objective,
            target_market=_target_market(fixture.domain),
            source_version_ids=_source_version_ids(input_payload),
            seller_constraints={
                "qualification_scenario": scenario,
                "required_disclosures": fixture.required_disclosures,
                "prohibited_claims": fixture.prohibited_claims,
            },
            operation_payload={
                "qualification_input": input_payload,
                "qualification_scenario": scenario,
            },
            schema_version=prompt.output_schema_version,
            prompt_version=prompt.prompt_version,
        )
        result = execute_structured_operation(
            self._settings,
            context,
            definition.output_contract,
            provider=self._provider,
        )
        validated_output = definition.output_contract.model_validate(
            result.parsed_output
        )
        return OperationExecutionV1(
            operation=operation.value,
            provider=result.provider,
            endpoint_family=str(result.endpoint_family),
            model=result.model,
            prompt_name=definition.prompt_name,
            prompt_version=definition.prompt_version,
            schema_version=definition.schema_version,
            provider_request_id=result.provider_request_id,
            output=cast(
                dict[str, object],
                validated_output.model_dump(mode="json"),
            ),
            output_valid=True,
            source_version_references_valid=True,
            evidence_ids_valid=_operation_evidence_ids_valid(
                operation,
                validated_output,
            ),
            timestamps_valid=True,
            silent_fixture_fallback=result.provider != "openai",
        )

    def execute_case(
        self,
        scenario_id: str,
        operations: Sequence[AiOperationName],
    ) -> QualificationCaseExecutionV1:
        operation_results = [
            self.execute_operation(operation, scenario_id)
            for operation in operations
        ]
        semantic_output, request_id, model = self._execute_semantic_projection(
            scenario_id,
            operation_results,
        )
        return QualificationCaseExecutionV1(
            scenario_id=scenario_id,
            semantic_output=semantic_output,
            operation_results=operation_results,
            semantic_provider_request_id=request_id,
            semantic_model=model,
        )

    def _execute_semantic_projection(
        self,
        scenario_id: str,
        operation_results: Sequence[OperationExecutionV1],
    ) -> tuple[GoldenSemanticOutputV1, str | None, str]:
        prompt = get_prompt_package(AiOperationName.VIRAL_KIT_COMPOSE)
        input_text = json.dumps(
            {
                "task": (
                    "Derive the qualification semantic output only from the supplied "
                    "scenario observations and actual operation outputs. Preserve "
                    "product facts, distinguish three concepts, apply hard blockers, "
                    "and keep disclosures, personalization, and prohibited claims "
                    "grounded. Do not assume any hidden expected answer and do not add "
                    "performance labels."
                ),
                "scenario": _scenario_input(scenario_id),
                "operation_outputs": [
                    {
                        "operation": result.operation,
                        "output": result.output,
                    }
                    for result in operation_results
                ],
            },
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        request_id = str(uuid4())
        model = self._settings.resolve_openai_model(
            AiOperationName.VIRAL_KIT_COMPOSE.value
        )
        result = self._provider.generate_structured(
            StructuredGenerationRequest(
                operation="golden_semantic_projection",
                model=model,
                system_prompt=prompt.system_prompt,
                developer_prompt=(
                    "This is a bounded semantic qualification. Return only "
                    "GoldenSemanticOutputV1 derived from the supplied scenario and "
                    "operation outputs. The Golden expected output is intentionally "
                    "not provided. Unknown facts must remain unknown."
                ),
                user_content=[InputTextPart(text=input_text)],
                output_model=GoldenSemanticOutputV1,
                prompt_version=_QUALIFICATION_PROMPT_VERSION,
                schema_version=_QUALIFICATION_SCHEMA_VERSION,
                reasoning_effort=prompt.default_reasoning_effort,
                max_output_tokens=prompt.default_max_output_tokens,
                request_id=request_id,
                input_hash=hashlib.sha256(input_text.encode("utf-8")).hexdigest(),
                idempotency_key=request_id,
                max_repair_attempts=1,
            )
        )
        return (
            GoldenSemanticOutputV1.model_validate(result.parsed_output),
            result.provider_request_id,
            result.model,
        )


def _operation_input(
    operation: AiOperationName,
    scenario_id: str,
) -> dict[str, object]:
    fixture = load_golden_fixture(scenario_id)
    workspace_id = _stable_id(scenario_id, "workspace")
    actor_id = _stable_id(scenario_id, "actor")
    asset_id = _stable_id(scenario_id, "asset")
    asset_version_id = _stable_id(scenario_id, "asset-version")
    evidence_id = _stable_id(scenario_id, "evidence")
    dna_version_id = _stable_id(scenario_id, "creative-dna-version")
    pattern_version_id = _stable_id(scenario_id, "pattern-kit-version")
    viral_version_id = _stable_id(scenario_id, "viral-kit-version")
    product_id = _stable_id(scenario_id, "product")
    preflight_id = _stable_id(scenario_id, "preflight")

    common_asset: dict[str, object] = {
        "workspace_id": workspace_id,
        "asset_id": asset_id,
        "asset_version_id": asset_version_id,
    }
    if operation is AiOperationName.MEDIA_OBSERVATION:
        return common_asset
    if operation is AiOperationName.CREATIVE_DNA_BUILD:
        return {**common_asset, "evidence_item_ids": [evidence_id]}
    if operation is AiOperationName.PATTERN_KIT_EXTRACT:
        return {
            "workspace_id": workspace_id,
            "creative_dna_version_ids": [dna_version_id],
        }
    if operation is AiOperationName.VIRAL_KIT_COMPOSE:
        return {
            "workspace_id": workspace_id,
            "product_id": product_id,
            "product_context_version": 1,
            "pattern_kit_version_ids": [pattern_version_id],
        }
    if operation is AiOperationName.ADAPTATION_GENERATE:
        return {
            "workspace_id": workspace_id,
            "product_id": product_id,
            "product_context_version": 1,
            "creative_dna_version_id": dna_version_id,
        }
    if operation is AiOperationName.CAMPAIGN_PACK_GENERATE:
        return {
            "workspace_id": workspace_id,
            "viral_kit_version_id": viral_version_id,
            "concept_id": "qualification-concept-1",
        }
    if operation is AiOperationName.SELLER_DECISION_SUMMARY:
        return {
            "workspace_id": workspace_id,
            "preflight_run_id": preflight_id,
            "product_name": fixture.product_name,
            "objective": fixture.objective,
            "locale": "en-US",
        }
    if operation is AiOperationName.REVISION_MESSAGE_GENERATE:
        return {
            "workspace_id": workspace_id,
            "preflight_run_id": preflight_id,
            "blocker_codes": ["QUALIFICATION_REVIEW_REQUIRED"],
            "product_name": fixture.product_name,
            "strengths_to_preserve": [
                "Preserve the current evidence-supported strengths."
            ],
            "resubmission_request": "Please upload the revised version for review.",
        }
    return {
        "workspace_id": workspace_id,
        "viral_kit_version_id": viral_version_id,
        "concept_id": "qualification-concept-1",
        "source_asset_ids": [asset_id],
        "actor_user_id": actor_id,
    }


def _stable_id(scenario_id: str, *parts: str) -> UUID:
    return uuid5(NAMESPACE_URL, ":".join(("viraldy-qualification", scenario_id, *parts)))


def _source_version_ids(payload: dict[str, object]) -> list[UUID]:
    keys = (
        "asset_version_id",
        "creative_dna_version_id",
        "viral_kit_version_id",
    )
    values: list[UUID] = []
    for key in keys:
        raw = payload.get(key)
        if raw is not None:
            values.append(UUID(str(raw)))
    for key in ("creative_dna_version_ids", "pattern_kit_version_ids"):
        raw_values = payload.get(key)
        if isinstance(raw_values, list):
            values.extend(UUID(str(raw)) for raw in raw_values)
    return list(dict.fromkeys(values))


def _operation_evidence_ids_valid(
    operation: AiOperationName,
    output: BaseModel,
) -> bool:
    if operation is not AiOperationName.MEDIA_OBSERVATION:
        return True
    raw_ids = output.model_dump(mode="json").get("evidence_item_ids")
    return isinstance(raw_ids, list) and all(_is_uuid(value) for value in raw_ids)


def _is_uuid(value: object) -> bool:
    try:
        UUID(str(value))
    except ValueError:
        return False
    return True


def _target_market(domain: str) -> str:
    return "US" if domain in {"tiktok_shop_us", "pod", "dropshipping"} else domain


def _scenario_input(scenario_id: str) -> dict[str, object]:
    fixture = load_golden_fixture(scenario_id)
    return {
        "scenario_id": fixture.scenario_id,
        "domain": fixture.domain,
        "product_name": fixture.product_name,
        "objective": fixture.objective,
        "required_disclosures": fixture.required_disclosures,
        "prohibited_claims": fixture.prohibited_claims,
        "assets": [
            {
                "asset_id": asset.asset_id,
                "asset_role": asset.asset_role,
                "has_audio": asset.has_audio,
                "duration_ms": asset.duration_ms,
                "observations": asset.observations,
            }
            for asset in fixture.assets
        ],
    }
