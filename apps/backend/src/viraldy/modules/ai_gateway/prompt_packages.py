from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum
from types import MappingProxyType
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from viraldy.modules.ai_gateway.prompt_content import (
    ADAPTATION_DEVELOPER_PROMPT_V2,
    CAMPAIGN_PACK_DEVELOPER_PROMPT_V2,
    CONCEPT_VIDEO_PREVIEW_DEVELOPER_PROMPT_V1,
    CREATIVE_DNA_DEVELOPER_PROMPT_V2,
    DECISION_SUMMARY_DEVELOPER_PROMPT_V1,
    MEDIA_OBSERVATION_DEVELOPER_PROMPT_V2,
    PATTERN_KIT_DEVELOPER_PROMPT_V2,
    REVISION_MESSAGE_DEVELOPER_PROMPT_V2,
    STORYBOARD_IMAGE_DEVELOPER_PROMPT_V1,
    SYSTEM_PROMPT_NAME,
    SYSTEM_PROMPT_V2,
    SYSTEM_PROMPT_VERSION,
    VIRAL_KIT_DEVELOPER_PROMPT_V2,
)
from viraldy.modules.ai_gateway.prompt_content.examples import ALL_FEW_SHOT_EXAMPLE_IDS
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

MEDIA_OBSERVATION_OPERATION = "media_observation"
CREATIVE_DNA_OPERATION = "creative_dna_build"
PATTERN_KIT_OPERATION = "pattern_kit_extract"
VIRAL_KIT_OPERATION = "viral_kit_compose"
ADAPTATION_OPERATION = "adaptation_generate"
CAMPAIGN_PACK_OPERATION = "campaign_pack_generate"
REVISION_MESSAGE_OPERATION = "revision_message_generate"
STORYBOARD_IMAGE_OPERATION = "storyboard_image_generate"
CONCEPT_VIDEO_PREVIEW_OPERATION = "concept_video_preview_generate"
DECISION_SUMMARY_OPERATION = "seller_decision_summary"

type PromptOperation = Literal[
    "media_observation",
    "creative_dna_build",
    "pattern_kit_extract",
    "viral_kit_compose",
    "adaptation_generate",
    "campaign_pack_generate",
    "revision_message_generate",
    "storyboard_image_generate",
    "concept_video_preview_generate",
    "seller_decision_summary",
]
type ReasoningEffort = Literal["low", "medium", "high"]
type NonEmptyString = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
]

MEDIA_OBSERVATION_PROMPT_NAME = "media_observation"
MEDIA_OBSERVATION_PROMPT_VERSION = "media_observation_v3_bounded_few_shot_v1"
CREATIVE_DNA_PROMPT_NAME = "creative_dna_extraction"
CREATIVE_DNA_PROMPT_VERSION = (
    "creative_dna_extraction_v4_grounded_statuses_few_shot_v1"
)
PATTERN_KIT_PROMPT_NAME = "pattern_kit_extraction"
PATTERN_KIT_PROMPT_VERSION = "pattern_kit_extraction_v4_evidence_paths_few_shot_v1"
VIRAL_KIT_PROMPT_NAME = "viral_kit_composer"
VIRAL_KIT_PROMPT_VERSION = "viral_kit_composer_v2_few_shot_v1"
ADAPTATION_PROMPT_NAME = "adaptation_generation"
ADAPTATION_PROMPT_VERSION = "adaptation_generation_v2_few_shot_v1"
CAMPAIGN_PACK_PROMPT_NAME = "campaign_pack_generation"
CAMPAIGN_PACK_PROMPT_VERSION = "campaign_pack_generation_v2_few_shot_v1"
REVISION_MESSAGE_PROMPT_NAME = "revision_message"
REVISION_MESSAGE_PROMPT_VERSION = "revision_message_v2_few_shot_v1"
STORYBOARD_IMAGE_PROMPT_NAME = "storyboard_image_generation"
STORYBOARD_IMAGE_PROMPT_VERSION = "storyboard_image_generation_v1_few_shot_v1"
CONCEPT_VIDEO_PREVIEW_PROMPT_NAME = "concept_video_preview_generation"
CONCEPT_VIDEO_PREVIEW_PROMPT_VERSION = (
    "concept_video_preview_generation_v1_few_shot_v1"
)
DECISION_SUMMARY_PROMPT_NAME = "seller_decision_summary"
DECISION_SUMMARY_PROMPT_VERSION = "seller_decision_summary_v1_few_shot_v1"
DECISION_SUMMARY_OUTPUT_SCHEMA_VERSION = "seller_decision_summary_v1"


class PromptPackage(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    operation: PromptOperation
    prompt_name: NonEmptyString
    prompt_version: NonEmptyString
    system_prompt: NonEmptyString
    developer_prompt: NonEmptyString
    example_ids: tuple[NonEmptyString, ...] = Field(min_length=1)
    output_schema_version: NonEmptyString
    default_reasoning_effort: ReasoningEffort | None
    default_max_output_tokens: int | None = Field(default=None, gt=0)


_PROMPT_PACKAGES = (
    PromptPackage(
        operation=MEDIA_OBSERVATION_OPERATION,
        prompt_name=MEDIA_OBSERVATION_PROMPT_NAME,
        prompt_version=MEDIA_OBSERVATION_PROMPT_VERSION,
        system_prompt=SYSTEM_PROMPT_V2,
        developer_prompt=MEDIA_OBSERVATION_DEVELOPER_PROMPT_V2,
        example_ids=ALL_FEW_SHOT_EXAMPLE_IDS,
        output_schema_version=MEDIA_OBSERVATION_SCHEMA_VERSION,
        default_reasoning_effort="low",
        default_max_output_tokens=12_000,
    ),
    PromptPackage(
        operation=CREATIVE_DNA_OPERATION,
        prompt_name=CREATIVE_DNA_PROMPT_NAME,
        prompt_version=CREATIVE_DNA_PROMPT_VERSION,
        system_prompt=SYSTEM_PROMPT_V2,
        developer_prompt=CREATIVE_DNA_DEVELOPER_PROMPT_V2,
        example_ids=ALL_FEW_SHOT_EXAMPLE_IDS,
        output_schema_version=CREATIVE_DNA_SCHEMA_VERSION,
        default_reasoning_effort="low",
        default_max_output_tokens=12_000,
    ),
    PromptPackage(
        operation=PATTERN_KIT_OPERATION,
        prompt_name=PATTERN_KIT_PROMPT_NAME,
        prompt_version=PATTERN_KIT_PROMPT_VERSION,
        system_prompt=SYSTEM_PROMPT_V2,
        developer_prompt=PATTERN_KIT_DEVELOPER_PROMPT_V2,
        example_ids=ALL_FEW_SHOT_EXAMPLE_IDS,
        output_schema_version=PATTERN_KIT_SCHEMA_VERSION,
        default_reasoning_effort="low",
        default_max_output_tokens=12_000,
    ),
    PromptPackage(
        operation=VIRAL_KIT_OPERATION,
        prompt_name=VIRAL_KIT_PROMPT_NAME,
        prompt_version=VIRAL_KIT_PROMPT_VERSION,
        system_prompt=SYSTEM_PROMPT_V2,
        developer_prompt=VIRAL_KIT_DEVELOPER_PROMPT_V2,
        example_ids=ALL_FEW_SHOT_EXAMPLE_IDS,
        output_schema_version=VIRAL_KIT_SCHEMA_VERSION,
        default_reasoning_effort="high",
        default_max_output_tokens=10_000,
    ),
    PromptPackage(
        operation=ADAPTATION_OPERATION,
        prompt_name=ADAPTATION_PROMPT_NAME,
        prompt_version=ADAPTATION_PROMPT_VERSION,
        system_prompt=SYSTEM_PROMPT_V2,
        developer_prompt=ADAPTATION_DEVELOPER_PROMPT_V2,
        example_ids=ALL_FEW_SHOT_EXAMPLE_IDS,
        output_schema_version=ADAPTATION_SCHEMA_VERSION,
        default_reasoning_effort="high",
        default_max_output_tokens=8_000,
    ),
    PromptPackage(
        operation=CAMPAIGN_PACK_OPERATION,
        prompt_name=CAMPAIGN_PACK_PROMPT_NAME,
        prompt_version=CAMPAIGN_PACK_PROMPT_VERSION,
        system_prompt=SYSTEM_PROMPT_V2,
        developer_prompt=CAMPAIGN_PACK_DEVELOPER_PROMPT_V2,
        example_ids=ALL_FEW_SHOT_EXAMPLE_IDS,
        output_schema_version=CAMPAIGN_PACK_SCHEMA_VERSION,
        default_reasoning_effort="medium",
        default_max_output_tokens=10_000,
    ),
    PromptPackage(
        operation=REVISION_MESSAGE_OPERATION,
        prompt_name=REVISION_MESSAGE_PROMPT_NAME,
        prompt_version=REVISION_MESSAGE_PROMPT_VERSION,
        system_prompt=SYSTEM_PROMPT_V2,
        developer_prompt=REVISION_MESSAGE_DEVELOPER_PROMPT_V2,
        example_ids=ALL_FEW_SHOT_EXAMPLE_IDS,
        output_schema_version=REVISION_MESSAGE_SCHEMA_VERSION,
        default_reasoning_effort="low",
        default_max_output_tokens=2_000,
    ),
    PromptPackage(
        operation=STORYBOARD_IMAGE_OPERATION,
        prompt_name=STORYBOARD_IMAGE_PROMPT_NAME,
        prompt_version=STORYBOARD_IMAGE_PROMPT_VERSION,
        system_prompt=SYSTEM_PROMPT_V2,
        developer_prompt=STORYBOARD_IMAGE_DEVELOPER_PROMPT_V1,
        example_ids=ALL_FEW_SHOT_EXAMPLE_IDS,
        output_schema_version=STORYBOARD_IMAGE_SCHEMA_VERSION,
        default_reasoning_effort=None,
        default_max_output_tokens=None,
    ),
    PromptPackage(
        operation=CONCEPT_VIDEO_PREVIEW_OPERATION,
        prompt_name=CONCEPT_VIDEO_PREVIEW_PROMPT_NAME,
        prompt_version=CONCEPT_VIDEO_PREVIEW_PROMPT_VERSION,
        system_prompt=SYSTEM_PROMPT_V2,
        developer_prompt=CONCEPT_VIDEO_PREVIEW_DEVELOPER_PROMPT_V1,
        example_ids=ALL_FEW_SHOT_EXAMPLE_IDS,
        output_schema_version=VIDEO_PREVIEW_SCHEMA_VERSION,
        default_reasoning_effort=None,
        default_max_output_tokens=None,
    ),
    PromptPackage(
        operation=DECISION_SUMMARY_OPERATION,
        prompt_name=DECISION_SUMMARY_PROMPT_NAME,
        prompt_version=DECISION_SUMMARY_PROMPT_VERSION,
        system_prompt=SYSTEM_PROMPT_V2,
        developer_prompt=DECISION_SUMMARY_DEVELOPER_PROMPT_V1,
        example_ids=ALL_FEW_SHOT_EXAMPLE_IDS,
        output_schema_version=DECISION_SUMMARY_OUTPUT_SCHEMA_VERSION,
        default_reasoning_effort="low",
        default_max_output_tokens=2_000,
    ),
)

_prompt_package_registry: dict[str, PromptPackage] = {
    package.operation: package for package in _PROMPT_PACKAGES
}
_prompt_versions = {package.prompt_version for package in _PROMPT_PACKAGES}
if len(_prompt_package_registry) != len(_PROMPT_PACKAGES):
    raise RuntimeError("Prompt package operations must be unique.")
if len(_prompt_versions) != len(_PROMPT_PACKAGES):
    raise RuntimeError("Prompt package versions must be unique.")

PROMPT_PACKAGE_REGISTRY: Mapping[str, PromptPackage] = MappingProxyType(
    _prompt_package_registry
)
PROMPT_PACKAGES = PROMPT_PACKAGE_REGISTRY


def get_prompt_package(operation: str | StrEnum) -> PromptPackage:
    return PROMPT_PACKAGE_REGISTRY[str(operation)]


def iter_prompt_packages() -> tuple[PromptPackage, ...]:
    return _PROMPT_PACKAGES


__all__ = [
    "ADAPTATION_PROMPT_NAME",
    "ADAPTATION_PROMPT_VERSION",
    "CAMPAIGN_PACK_PROMPT_NAME",
    "CAMPAIGN_PACK_PROMPT_VERSION",
    "CONCEPT_VIDEO_PREVIEW_PROMPT_NAME",
    "CONCEPT_VIDEO_PREVIEW_PROMPT_VERSION",
    "CREATIVE_DNA_PROMPT_NAME",
    "CREATIVE_DNA_PROMPT_VERSION",
    "DECISION_SUMMARY_OPERATION",
    "DECISION_SUMMARY_OUTPUT_SCHEMA_VERSION",
    "DECISION_SUMMARY_PROMPT_NAME",
    "DECISION_SUMMARY_PROMPT_VERSION",
    "MEDIA_OBSERVATION_PROMPT_NAME",
    "MEDIA_OBSERVATION_PROMPT_VERSION",
    "PATTERN_KIT_PROMPT_NAME",
    "PATTERN_KIT_PROMPT_VERSION",
    "PROMPT_PACKAGES",
    "PROMPT_PACKAGE_REGISTRY",
    "PromptPackage",
    "REVISION_MESSAGE_PROMPT_NAME",
    "REVISION_MESSAGE_PROMPT_VERSION",
    "STORYBOARD_IMAGE_PROMPT_NAME",
    "STORYBOARD_IMAGE_PROMPT_VERSION",
    "SYSTEM_PROMPT_NAME",
    "SYSTEM_PROMPT_V2",
    "SYSTEM_PROMPT_VERSION",
    "VIRAL_KIT_PROMPT_NAME",
    "VIRAL_KIT_PROMPT_VERSION",
    "get_prompt_package",
    "iter_prompt_packages",
]
