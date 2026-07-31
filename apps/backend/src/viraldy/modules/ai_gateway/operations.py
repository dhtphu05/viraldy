from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from typing import Literal
from uuid import NAMESPACE_URL, UUID, uuid5

from pydantic import BaseModel, ConfigDict, Field

from viraldy.modules.ai_gateway.prompts import (
    ADAPTATION_PROMPT_VERSION,
    CAMPAIGN_PACK_PROMPT_VERSION,
    CONCEPT_VIDEO_PREVIEW_PROMPT_VERSION,
    CREATIVE_DNA_PROMPT_VERSION,
    DECISION_SUMMARY_OUTPUT_SCHEMA_VERSION,
    DECISION_SUMMARY_PROMPT_VERSION,
    MEDIA_OBSERVATION_PROMPT_VERSION,
    PATTERN_KIT_PROMPT_VERSION,
    REVISION_MESSAGE_PROMPT_VERSION,
    STORYBOARD_IMAGE_PROMPT_VERSION,
    VIRAL_KIT_PROMPT_VERSION,
    get_prompt_package,
)
from viraldy.modules.creative_domain.schema_versions import (
    ADAPTATION_SCHEMA_VERSION,
    CAMPAIGN_PACK_SCHEMA_VERSION,
    CREATIVE_DNA_SCHEMA_VERSION,
    MEDIA_OBSERVATION_SCHEMA_VERSION,
    PATTERN_KIT_SCHEMA_VERSION,
    REVISION_MESSAGE_SCHEMA_VERSION,
    STORYBOARD_IMAGE_SCHEMA_VERSION,
    VIDEO_PREVIEW_SCHEMA_VERSION,
    VIRAL_KIT_SCHEMA_VERSION,
)
from viraldy.modules.presentations.contracts import (
    CreatorRevisionMessageV2,
    PresentationFixV1,
    SellerDecisionSummaryV1,
)


class AiOperationName(StrEnum):
    MEDIA_OBSERVATION = "media_observation"
    CREATIVE_DNA_BUILD = "creative_dna_build"
    PATTERN_KIT_EXTRACT = "pattern_kit_extract"
    VIRAL_KIT_COMPOSE = "viral_kit_compose"
    ADAPTATION_GENERATE = "adaptation_generate"
    CAMPAIGN_PACK_GENERATE = "campaign_pack_generate"
    SELLER_DECISION_SUMMARY = "seller_decision_summary"
    REVISION_MESSAGE_GENERATE = "revision_message_generate"
    STORYBOARD_IMAGE_GENERATE = "storyboard_image_generate"
    CONCEPT_VIDEO_PREVIEW_GENERATE = "concept_video_preview_generate"


class OperationContractBase(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AssetOperationInputV1(OperationContractBase):
    workspace_id: UUID
    asset_id: UUID
    asset_version_id: UUID


class MediaObservationOutputV1(OperationContractBase):
    media_artifact_ids: list[UUID] = Field(default_factory=list)
    evidence_item_ids: list[UUID] = Field(default_factory=list)


class CreativeDnaBuildInputV1(AssetOperationInputV1):
    evidence_item_ids: list[UUID] = Field(min_length=1)


class CreativeDnaBuildOutputV1(OperationContractBase):
    creative_dna_version_id: UUID


class PatternKitExtractInputV1(OperationContractBase):
    workspace_id: UUID
    creative_dna_version_ids: list[UUID] = Field(min_length=1)


class PatternKitExtractOutputV1(OperationContractBase):
    pattern_kit_id: UUID
    pattern_kit_version_id: UUID


class ViralKitComposeInputV1(OperationContractBase):
    workspace_id: UUID
    product_id: UUID
    product_context_version: int = Field(ge=1)
    pattern_kit_version_ids: list[UUID] = Field(min_length=1)


class ViralKitComposeOutputV1(OperationContractBase):
    viral_kit_id: UUID
    viral_kit_version_id: UUID
    concept_ids: list[str] = Field(min_length=3, max_length=3)


class AdaptationGenerateInputV1(OperationContractBase):
    workspace_id: UUID
    product_id: UUID
    product_context_version: int = Field(ge=1)
    creative_dna_version_id: UUID


class AdaptationGenerateOutputV1(OperationContractBase):
    adaptation_run_id: UUID


class CampaignPackGenerateInputV1(OperationContractBase):
    workspace_id: UUID
    viral_kit_version_id: UUID
    concept_id: str = Field(min_length=1, max_length=120)


class CampaignPackGenerateOutputV1(OperationContractBase):
    campaign_pack_id: UUID
    campaign_pack_version_id: UUID


class RevisionMessageGenerateInputV1(OperationContractBase):
    workspace_id: UUID
    preflight_run_id: UUID
    blocker_codes: list[str] = Field(min_length=1)
    product_name: str = "the product"
    strengths_to_preserve: list[str] = Field(
        default_factory=lambda: ["Preserve the creator's current tone and delivery."]
    )
    resubmission_request: str = (
        "Please upload the revised version for review."
    )


class RevisionMessageGenerateOutputV1(OperationContractBase):
    revision_message: str = Field(min_length=1)
    referenced_blocker_codes: list[str] = Field(min_length=1)


class SellerDecisionSummaryInputV1(OperationContractBase):
    workspace_id: UUID
    preflight_run_id: UUID
    product_name: str = Field(min_length=1)
    objective: str | None = None
    locale: Literal["en-US", "vi-VN"] = "en-US"


class GenerationOperationInputV1(OperationContractBase):
    workspace_id: UUID
    viral_kit_version_id: UUID
    concept_id: str = Field(min_length=1, max_length=120)
    source_asset_ids: list[UUID] = Field(min_length=1)


class GenerationArtifactOutputV1(OperationContractBase):
    generation_run_id: UUID
    artifact_ids: list[UUID] = Field(min_length=1)
    artifact_kind: Literal["storyboard_image", "concept_video_preview"]


@dataclass(frozen=True, slots=True)
class AiOperationDefinition:
    operation: AiOperationName
    input_contract: type[BaseModel]
    output_contract: type[BaseModel]
    prompt_name: str
    prompt_version: str
    schema_version: str
    timeout_seconds: int
    max_retries: int
    model_family: Literal["text", "vision", "image", "video"]
    mock_fixture_available: bool = True


def _definition(
    operation: AiOperationName,
    input_contract: type[BaseModel],
    output_contract: type[BaseModel],
    prompt_version: str,
    schema_version: str,
    *,
    timeout_seconds: int = 120,
    max_retries: int = 2,
    model_family: Literal["text", "vision", "image", "video"] = "text",
) -> AiOperationDefinition:
    prompt_package = get_prompt_package(operation)
    return AiOperationDefinition(
        operation=operation,
        input_contract=input_contract,
        output_contract=output_contract,
        prompt_name=prompt_package.prompt_name,
        prompt_version=prompt_version,
        schema_version=schema_version,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
        model_family=model_family,
    )


AI_OPERATION_DEFINITIONS: dict[str, AiOperationDefinition] = {
    AiOperationName.MEDIA_OBSERVATION.value: _definition(
        AiOperationName.MEDIA_OBSERVATION,
        AssetOperationInputV1,
        MediaObservationOutputV1,
        MEDIA_OBSERVATION_PROMPT_VERSION,
        MEDIA_OBSERVATION_SCHEMA_VERSION,
        model_family="vision",
    ),
    AiOperationName.CREATIVE_DNA_BUILD.value: _definition(
        AiOperationName.CREATIVE_DNA_BUILD,
        CreativeDnaBuildInputV1,
        CreativeDnaBuildOutputV1,
        CREATIVE_DNA_PROMPT_VERSION,
        CREATIVE_DNA_SCHEMA_VERSION,
    ),
    AiOperationName.PATTERN_KIT_EXTRACT.value: _definition(
        AiOperationName.PATTERN_KIT_EXTRACT,
        PatternKitExtractInputV1,
        PatternKitExtractOutputV1,
        PATTERN_KIT_PROMPT_VERSION,
        PATTERN_KIT_SCHEMA_VERSION,
    ),
    AiOperationName.VIRAL_KIT_COMPOSE.value: _definition(
        AiOperationName.VIRAL_KIT_COMPOSE,
        ViralKitComposeInputV1,
        ViralKitComposeOutputV1,
        VIRAL_KIT_PROMPT_VERSION,
        VIRAL_KIT_SCHEMA_VERSION,
    ),
    AiOperationName.ADAPTATION_GENERATE.value: _definition(
        AiOperationName.ADAPTATION_GENERATE,
        AdaptationGenerateInputV1,
        AdaptationGenerateOutputV1,
        ADAPTATION_PROMPT_VERSION,
        ADAPTATION_SCHEMA_VERSION,
    ),
    AiOperationName.CAMPAIGN_PACK_GENERATE.value: _definition(
        AiOperationName.CAMPAIGN_PACK_GENERATE,
        CampaignPackGenerateInputV1,
        CampaignPackGenerateOutputV1,
        CAMPAIGN_PACK_PROMPT_VERSION,
        CAMPAIGN_PACK_SCHEMA_VERSION,
    ),
    AiOperationName.SELLER_DECISION_SUMMARY.value: _definition(
        AiOperationName.SELLER_DECISION_SUMMARY,
        SellerDecisionSummaryInputV1,
        SellerDecisionSummaryV1,
        DECISION_SUMMARY_PROMPT_VERSION,
        DECISION_SUMMARY_OUTPUT_SCHEMA_VERSION,
    ),
    AiOperationName.REVISION_MESSAGE_GENERATE.value: _definition(
        AiOperationName.REVISION_MESSAGE_GENERATE,
        RevisionMessageGenerateInputV1,
        CreatorRevisionMessageV2,
        REVISION_MESSAGE_PROMPT_VERSION,
        REVISION_MESSAGE_SCHEMA_VERSION,
    ),
    AiOperationName.STORYBOARD_IMAGE_GENERATE.value: _definition(
        AiOperationName.STORYBOARD_IMAGE_GENERATE,
        GenerationOperationInputV1,
        GenerationArtifactOutputV1,
        STORYBOARD_IMAGE_PROMPT_VERSION,
        STORYBOARD_IMAGE_SCHEMA_VERSION,
        timeout_seconds=180,
        model_family="image",
    ),
    AiOperationName.CONCEPT_VIDEO_PREVIEW_GENERATE.value: _definition(
        AiOperationName.CONCEPT_VIDEO_PREVIEW_GENERATE,
        GenerationOperationInputV1,
        GenerationArtifactOutputV1,
        CONCEPT_VIDEO_PREVIEW_PROMPT_VERSION,
        VIDEO_PREVIEW_SCHEMA_VERSION,
        timeout_seconds=360,
        model_family="video",
    ),
}


def get_ai_operation_definition(
    operation: AiOperationName | str,
) -> AiOperationDefinition:
    return AI_OPERATION_DEFINITIONS[str(operation)]


def build_ai_operation_fixture(
    operation: AiOperationName | str,
    payload: BaseModel | dict[str, object],
) -> BaseModel:
    definition = get_ai_operation_definition(operation)
    operation_name = definition.operation
    validated_input = definition.input_contract.model_validate(payload)
    seed = json.dumps(
        validated_input.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
    )

    def fixture_id(label: str) -> UUID:
        return uuid5(NAMESPACE_URL, f"{operation_name.value}:{seed}:{label}")

    if operation_name is AiOperationName.MEDIA_OBSERVATION:
        return MediaObservationOutputV1(
            media_artifact_ids=[fixture_id("media-artifact")],
            evidence_item_ids=[fixture_id("evidence-item")],
        )
    if operation_name is AiOperationName.CREATIVE_DNA_BUILD:
        return CreativeDnaBuildOutputV1(
            creative_dna_version_id=fixture_id("creative-dna-version")
        )
    if operation_name is AiOperationName.PATTERN_KIT_EXTRACT:
        return PatternKitExtractOutputV1(
            pattern_kit_id=fixture_id("pattern-kit"),
            pattern_kit_version_id=fixture_id("pattern-kit-version"),
        )
    if operation_name is AiOperationName.VIRAL_KIT_COMPOSE:
        return ViralKitComposeOutputV1(
            viral_kit_id=fixture_id("viral-kit"),
            viral_kit_version_id=fixture_id("viral-kit-version"),
            concept_ids=["concept-1", "concept-2", "concept-3"],
        )
    if operation_name is AiOperationName.ADAPTATION_GENERATE:
        return AdaptationGenerateOutputV1(adaptation_run_id=fixture_id("adaptation-run"))
    if operation_name is AiOperationName.CAMPAIGN_PACK_GENERATE:
        return CampaignPackGenerateOutputV1(
            campaign_pack_id=fixture_id("campaign-pack"),
            campaign_pack_version_id=fixture_id("campaign-pack-version"),
        )
    if operation_name is AiOperationName.SELLER_DECISION_SUMMARY:
        summary_input = SellerDecisionSummaryInputV1.model_validate(validated_input)
        return SellerDecisionSummaryV1(
            headline=f"Revise: {summary_input.product_name}",
            one_sentence_decision=(
                f"{summary_input.product_name} needs revision before paid use."
            ),
            why_this_matters=(
                f"The persisted Preflight result for {summary_input.product_name} "
                "contains unresolved requirements."
            ),
            strengths_to_keep=[],
            blockers_to_fix=["Resolve the persisted hard requirements."],
            next_actions=["Apply the required fixes and rerun Preflight."],
            confidence_explanation=(
                "Confidence must be read from the persisted structured result."
            ),
            commercial_guardrail=(
                "Structural readiness does not guarantee virality, GMV, ROAS, "
                "conversion, policy approval, or sales."
            ),
            locale=summary_input.locale,
        )
    if operation_name is AiOperationName.REVISION_MESSAGE_GENERATE:
        revision_input = RevisionMessageGenerateInputV1.model_validate(validated_input)
        changes = [
            PresentationFixV1(
                code=code,
                instruction=f"Resolve the required change identified as {code}.",
            )
            for code in revision_input.blocker_codes
        ]
        return CreatorRevisionMessageV2(
            message=(
                "Keep the current strengths. Please apply the listed changes, "
                "then upload the revised version for review."
            ),
            strengths_to_preserve=revision_input.strengths_to_preserve,
            required_changes=changes,
            referenced_blocker_codes=revision_input.blocker_codes,
            resubmission_request=revision_input.resubmission_request,
        )
    return GenerationArtifactOutputV1(
        generation_run_id=fixture_id("generation-run"),
        artifact_ids=[fixture_id("generation-artifact")],
        artifact_kind=(
            "storyboard_image"
            if operation_name is AiOperationName.STORYBOARD_IMAGE_GENERATE
            else "concept_video_preview"
        ),
    )
