from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from pydantic import BaseModel

from viraldy.modules.ai_gateway.context import ViraldyOperationContextV1
from viraldy.modules.ai_gateway.execution import execute_structured_operation
from viraldy.modules.ai_gateway.operations import AiOperationName
from viraldy.modules.ai_gateway.prompt_packages import get_prompt_package
from viraldy.modules.domain_intelligence.execution_brief_contracts import (
    UGCExecutionBriefRecommendationPatchV1,
    UGCExecutionBriefSynthesisV1,
)
from viraldy.modules.domain_intelligence.schemas import (
    NormalizedEvidenceBundle,
    UGCRecommendation,
    UGCReviewContext,
    UGCReviewResult,
)
from viraldy.platform.config.settings import Settings
from viraldy.shared.errors.base import AppError

PROHIBITED_EXECUTION_BRIEF_LANGUAGE = (
    "viral probability",
    "guaranteed performance",
    "predicted gmv",
    "predicted roas",
    "guaranteed to win",
    "winning creative",
    "guaranteed sales",
)


def synthesize_execution_brief(
    *,
    result: UGCReviewResult,
    context: UGCReviewContext,
    evidence: NormalizedEvidenceBundle,
    settings: Settings | None,
    workspace_id: UUID | None,
) -> tuple[UGCReviewResult, str]:
    if settings is None or workspace_id is None:
        return result, "deterministic_fallback"
    recommendations = _all_recommendations(result)
    if not recommendations:
        return result, "deterministic_fallback"
    operation = AiOperationName.UGC_EXECUTION_BRIEF_SYNTHESIS
    prompt = get_prompt_package(operation)
    operation_context = ViraldyOperationContextV1(
        operation=operation,
        request_id=result.review_id,
        workspace_id=workspace_id,
        target_market=context.market,
        objective="Convert UGC Review findings into seller-executable tasks.",
        operation_payload={
            "review": _review_payload(result),
            "context": context.model_dump(mode="json"),
            "evidence": [
                item.model_dump(mode="json")
                for item in evidence.items
                if item.id in _referenced_evidence_ids(recommendations)
            ],
        },
        schema_version=prompt.output_schema_version,
        prompt_version=prompt.prompt_version,
    )
    try:
        generated = execute_structured_operation(
            settings,
            operation_context,
            UGCExecutionBriefSynthesisV1,
            output_validator=_output_validator(result),
        )
    except (AppError, ValueError):
        return result, "deterministic_fallback"
    synthesis = UGCExecutionBriefSynthesisV1.model_validate(generated.parsed_output)
    return apply_execution_brief_synthesis(result, synthesis), generated.provider


def apply_execution_brief_synthesis(
    result: UGCReviewResult,
    synthesis: UGCExecutionBriefSynthesisV1,
) -> UGCReviewResult:
    """Apply model wording changes while preserving deterministic review facts."""
    _validate_synthesis(result, synthesis)
    recommendations = [
        *result.fix_first,
        *result.improvements,
        *result.confirmations,
    ]
    expected_ids = {recommendation.id for recommendation in recommendations}
    patches_by_id = {patch.recommendation_id: patch for patch in synthesis.recommendation_patches}
    if (
        len(patches_by_id) != len(synthesis.recommendation_patches)
        or set(patches_by_id) != expected_ids
    ):
        raise ValueError("Execution-brief recommendation IDs must exactly match the review")

    def patch_group(items: Sequence[UGCRecommendation]) -> list[UGCRecommendation]:
        return [_apply_patch(item, patches_by_id[item.id]) for item in items]

    return result.model_copy(
        update={
            "fix_first": patch_group(result.fix_first),
            "improvements": patch_group(result.improvements),
            "confirmations": patch_group(result.confirmations),
            "creator_revision_message": (
                synthesis.creator_revision_message or result.creator_revision_message
            ),
        }
    )


def _apply_patch(
    recommendation: UGCRecommendation,
    patch: UGCExecutionBriefRecommendationPatchV1,
) -> UGCRecommendation:
    patch_data = patch.model_dump(exclude_none=True, exclude={"recommendation_id"})
    return recommendation.model_copy(update=patch_data)


def _output_validator(result: UGCReviewResult):
    def validate(output: BaseModel) -> None:
        synthesis = UGCExecutionBriefSynthesisV1.model_validate(output)
        _validate_synthesis(result, synthesis)

    return validate


def _validate_synthesis(
    result: UGCReviewResult,
    synthesis: UGCExecutionBriefSynthesisV1,
) -> None:
    recommendations = _all_recommendations(result)
    expected_ids = {recommendation.id for recommendation in recommendations}
    patches_by_id = {patch.recommendation_id: patch for patch in synthesis.recommendation_patches}
    if (
        len(patches_by_id) != len(synthesis.recommendation_patches)
        or set(patches_by_id) != expected_ids
    ):
        raise ValueError("Execution-brief recommendation IDs must exactly match the review")
    recommendation_by_id = {recommendation.id: recommendation for recommendation in recommendations}
    for patch in synthesis.recommendation_patches:
        _validate_patch(recommendation_by_id[patch.recommendation_id], patch)
    if synthesis.creator_revision_message:
        _reject_prohibited_language(synthesis.creator_revision_message)


def _validate_patch(
    recommendation: UGCRecommendation,
    patch: UGCExecutionBriefRecommendationPatchV1,
) -> None:
    _reject_prohibited_language(
        " ".join(
            [
                patch.title or "",
                patch.reason or "",
                patch.exact_action or "",
                *patch.exact_copy,
                *patch.acceptance_criteria,
            ]
        )
    )
    if patch.exact_copy and recommendation.task_kind == "seller_input_required":
        raise ValueError("Seller-input tasks may not invent exact copy")


def _reject_prohibited_language(value: str) -> None:
    lowered = value.lower()
    if any(phrase in lowered for phrase in PROHIBITED_EXECUTION_BRIEF_LANGUAGE):
        raise ValueError("Execution brief contains prohibited performance language")


def _all_recommendations(result: UGCReviewResult) -> list[UGCRecommendation]:
    return [*result.fix_first, *result.improvements, *result.confirmations]


def _referenced_evidence_ids(recommendations: Sequence[UGCRecommendation]) -> set[str]:
    return {
        evidence.id
        for recommendation in recommendations
        for evidence in recommendation.evidence
    }


def _review_payload(result: UGCReviewResult) -> dict[str, object]:
    return {
        "review_id": result.review_id,
        "strengths_to_keep": result.strengths_to_keep,
        "fix_first": [item.model_dump(mode="json") for item in result.fix_first],
        "improvements": [item.model_dump(mode="json") for item in result.improvements],
        "confirmations": [item.model_dump(mode="json") for item in result.confirmations],
        "creator_revision_message": result.creator_revision_message,
    }
