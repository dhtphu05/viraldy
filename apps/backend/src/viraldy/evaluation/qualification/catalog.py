from __future__ import annotations

from viraldy.evaluation.golden.loader import GOLDEN_SCENARIO_IDS
from viraldy.modules.ai_gateway.operations import AiOperationName

CASE_ALIASES: dict[str, str] = {
    "tiktok-shop": "home_travel_steamer",
    "tiktok_shop": "home_travel_steamer",
    "home_travel_steamer": "home_travel_steamer",
    "pod": "pod_dog_mom_crewneck",
    "pod_dog_mom_crewneck": "pod_dog_mom_crewneck",
    "dropshipping": "dropshipping_bag_sealer",
    "dropshipping_bag_sealer": "dropshipping_bag_sealer",
}

OPERATION_ALIASES: dict[str, AiOperationName] = {
    "media_observation": AiOperationName.MEDIA_OBSERVATION,
    "creative_dna": AiOperationName.CREATIVE_DNA_BUILD,
    "creative_dna_build": AiOperationName.CREATIVE_DNA_BUILD,
    "pattern_kit": AiOperationName.PATTERN_KIT_EXTRACT,
    "pattern_kit_extract": AiOperationName.PATTERN_KIT_EXTRACT,
    "viral_kit": AiOperationName.VIRAL_KIT_COMPOSE,
    "viral_kit_compose": AiOperationName.VIRAL_KIT_COMPOSE,
    "adaptation": AiOperationName.ADAPTATION_GENERATE,
    "adaptation_generate": AiOperationName.ADAPTATION_GENERATE,
    "campaign_pack": AiOperationName.CAMPAIGN_PACK_GENERATE,
    "campaign_pack_generate": AiOperationName.CAMPAIGN_PACK_GENERATE,
    "seller_decision_summary": AiOperationName.SELLER_DECISION_SUMMARY,
    "revision_message": AiOperationName.REVISION_MESSAGE_GENERATE,
    "revision_message_generate": AiOperationName.REVISION_MESSAGE_GENERATE,
}

QUALIFIABLE_OPERATIONS = tuple(dict.fromkeys(OPERATION_ALIASES.values()))
FULL_FLOW_OPERATIONS = (
    AiOperationName.MEDIA_OBSERVATION,
    AiOperationName.CREATIVE_DNA_BUILD,
    AiOperationName.PATTERN_KIT_EXTRACT,
    AiOperationName.VIRAL_KIT_COMPOSE,
    AiOperationName.ADAPTATION_GENERATE,
    AiOperationName.CAMPAIGN_PACK_GENERATE,
    AiOperationName.SELLER_DECISION_SUMMARY,
    AiOperationName.REVISION_MESSAGE_GENERATE,
)


def resolve_case(case: str) -> str:
    try:
        return CASE_ALIASES[case.strip().casefold()]
    except KeyError as exc:
        allowed = ", ".join(sorted(CASE_ALIASES))
        raise ValueError(f"unknown qualification case {case!r}; choose from {allowed}") from exc


def resolve_cases(case: str | None, all_cases: bool) -> list[str]:
    if all_cases:
        return list(GOLDEN_SCENARIO_IDS)
    if case is None:
        raise ValueError("a qualification case is required")
    return [resolve_case(case)]


def resolve_operation(operation: str) -> AiOperationName:
    try:
        return OPERATION_ALIASES[operation.strip().casefold()]
    except KeyError as exc:
        allowed = ", ".join(sorted(OPERATION_ALIASES))
        raise ValueError(
            f"unknown qualification operation {operation!r}; choose from {allowed}"
        ) from exc
