from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping, Sequence
from enum import StrEnum
from types import MappingProxyType
from typing import TYPE_CHECKING, Final, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

if TYPE_CHECKING:
    from viraldy.modules.ai_gateway.context import ViraldyOperationContextV1

type FewShotOperation = Literal[
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

MAX_RUNTIME_FEW_SHOT_EXAMPLES: Final = 2
RUNTIME_FEW_SHOT_SCHEMA_VERSION: Final = "runtime_few_shot_v1"
_RUNTIME_INSTRUCTION: Final = (
    "Use these compact examples only as behavior guidance. Ground the response in the "
    "current operation context and never copy or infer facts from an example."
)
_FORBIDDEN_RUNTIME_MARKERS: Final = (
    "swiftpress mini garment steamer",
    "personalized dog mom crewneck",
    "rechargeable mini bag sealer",
    "expected personalization: milo",
    "observed personalization: miles",
    "makes every bag completely airtight",
    "expected_output",
    "api_key",
    "signed_url",
    "http://",
    "https://",
)


class FewShotDomain(StrEnum):
    TIKTOK_SHOP = "tiktok_shop"
    POD_PERSONALIZATION = "pod_personalization"
    DROPSHIPPING = "dropshipping"


class FewShotExampleV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    example_id: str = Field(
        min_length=1,
        max_length=160,
        pattern=r"^golden-v0\.9:[a-z0-9-]+:compact-[a-z0-9-]+-v1$",
    )
    authority: Literal["golden_v0_9"] = "golden_v0_9"
    domain: FewShotDomain
    operations: tuple[FewShotOperation, ...] = Field(min_length=1)
    scenario: str = Field(min_length=1, max_length=500)
    supplied_signals: tuple[str, ...] = Field(min_length=1, max_length=4)
    demonstrated_behavior: tuple[str, ...] = Field(min_length=1, max_length=4)

    @model_validator(mode="after")
    def reject_forbidden_runtime_material(self) -> FewShotExampleV1:
        content = " ".join(
            (
                self.scenario,
                *self.supplied_signals,
                *self.demonstrated_behavior,
            )
        ).casefold()
        for marker in _FORBIDDEN_RUNTIME_MARKERS:
            if marker in content:
                raise ValueError(f"few-shot content contains forbidden marker: {marker}")
        return self


class RuntimeFewShotContentV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["runtime_few_shot_examples"] = "runtime_few_shot_examples"
    schema_version: Literal["runtime_few_shot_v1"] = RUNTIME_FEW_SHOT_SCHEMA_VERSION
    instruction: Literal[
        "Use these compact examples only as behavior guidance. Ground the response in the "
        "current operation context and never copy or infer facts from an example."
    ] = _RUNTIME_INSTRUCTION
    selected_example_ids: tuple[str, ...] = Field(
        min_length=1,
        max_length=MAX_RUNTIME_FEW_SHOT_EXAMPLES,
    )
    examples: tuple[FewShotExampleV1, ...] = Field(
        min_length=1,
        max_length=MAX_RUNTIME_FEW_SHOT_EXAMPLES,
    )

    @model_validator(mode="after")
    def validate_selected_ids(self) -> RuntimeFewShotContentV1:
        example_ids = tuple(example.example_id for example in self.examples)
        if self.selected_example_ids != example_ids:
            raise ValueError("selected_example_ids must match examples in order")
        return self


_EVIDENCE_OPERATIONS: tuple[FewShotOperation, ...] = (
    "media_observation",
    "creative_dna_build",
    "pattern_kit_extract",
    "revision_message_generate",
    "seller_decision_summary",
)
_STRATEGY_OPERATIONS: tuple[FewShotOperation, ...] = (
    "pattern_kit_extract",
    "viral_kit_compose",
    "adaptation_generate",
    "campaign_pack_generate",
    "storyboard_image_generate",
    "concept_video_preview_generate",
)

TIKTOK_SHOP_EXAMPLES: Final = (
    FewShotExampleV1(
        example_id="golden-v0.9:tiktok-shop-us:compact-evidence-v1",
        domain=FewShotDomain.TIKTOK_SHOP,
        operations=_EVIDENCE_OPERATIONS,
        scenario=(
            "A TikTok Shop draft has an early-reveal requirement, a visual demo, a "
            "required disclosure, and a separately evidenced product-tag cue."
        ),
        supplied_signals=(
            "Required reveal is by 2,000 ms; first clear appearance is at 4,100 ms.",
            "The mechanism is visible, but the required same-item result is not supplied.",
            "The tag cue and conversational delivery are both evidenced.",
        ),
        demonstrated_behavior=(
            "Report reveal timing as expected versus observed.",
            "Do not promote mechanism visibility to result proof.",
            "Keep the disclosure unresolved and preserve the evidenced strengths.",
        ),
    ),
    FewShotExampleV1(
        example_id="golden-v0.9:tiktok-shop-us:compact-strategy-v1",
        domain=FewShotDomain.TIKTOK_SHOP,
        operations=_STRATEGY_OPERATIONS,
        scenario=(
            "A clip-on reading light needs product-specific short-form concepts for a "
            "TikTok Shop test."
        ),
        supplied_signals=(
            "The supplied mechanism is a flexible neck with three authorized brightness modes.",
            "The supplied buyer contexts are dorm reading and late-night travel.",
            "A product-tag CTA is required; no discount or shipping promise is supplied.",
        ),
        demonstrated_behavior=(
            "Vary buyer context, hook, demo, and proof rather than wording alone.",
            "Show the supplied mechanism and product-tag requirement in each usable direction.",
            "Do not invent an offer, shipping speed, or performance guarantee.",
        ),
    ),
)

POD_PERSONALIZATION_EXAMPLES: Final = (
    FewShotExampleV1(
        example_id="golden-v0.9:pod-personalization:compact-evidence-v1",
        domain=FewShotDomain.POD_PERSONALIZATION,
        operations=_EVIDENCE_OPERATIONS,
        scenario=(
            "A custom recipe towel requires exact family-name personalization and a filmed "
            "physical sample."
        ),
        supplied_signals=(
            "Approved family name is 'Lena'; visible text reads 'Lina'.",
            "The physical sample is visible and the creator reaction is evidenced.",
            "No authorized arrival-date promise is supplied.",
        ),
        demonstrated_behavior=(
            "Treat the exact personalization mismatch as a hard execution blocker.",
            "Preserve the physical-product reveal and creator reaction as strengths.",
            "Do not add production or delivery promises.",
        ),
    ),
    FewShotExampleV1(
        example_id="golden-v0.9:pod-personalization:compact-strategy-v1",
        domain=FewShotDomain.POD_PERSONALIZATION,
        operations=_STRATEGY_OPERATIONS,
        scenario=(
            "A personalized neighborhood map print needs distinct self-purchase, gifting, "
            "and ordering-clarity concepts."
        ),
        supplied_signals=(
            "The supplied fields are street label, date, and frame variant.",
            "A physical product reveal is required; a digital mockup alone is insufficient.",
            "Production timing is unknown.",
        ),
        demonstrated_behavior=(
            "Preserve exact personalization fields and variant details.",
            "Separate identity, gifting, and ordering-clarity directions by meaningful axes.",
            "Distinguish the physical item from a mockup and keep timing unknown.",
        ),
    ),
)

DROPSHIPPING_EXAMPLES: Final = (
    FewShotExampleV1(
        example_id="golden-v0.9:dropshipping:compact-evidence-v1",
        domain=FewShotDomain.DROPSHIPPING,
        operations=_EVIDENCE_OPERATIONS,
        scenario=(
            "A sourced cable organizer is demonstrated with one supported cable size and "
            "an unsupported universal compatibility claim."
        ),
        supplied_signals=(
            "The organizer is visibly installed on one supplied cable size.",
            "The spoken claim says it works with every cable and never slips.",
            "No broader compatibility test or shipping promise is supplied.",
        ),
        demonstrated_behavior=(
            "Keep the visible installation as observed mechanism evidence.",
            "Block the universal compatibility and permanent-result claim.",
            "Recommend only the demonstrated use case and do not invent shipping language.",
        ),
    ),
    FewShotExampleV1(
        example_id="golden-v0.9:dropshipping:compact-strategy-v1",
        domain=FewShotDomain.DROPSHIPPING,
        operations=_STRATEGY_OPERATIONS,
        scenario=(
            "A foldable desk light needs product-specific concepts without unsupported "
            "compatibility or fulfillment claims."
        ),
        supplied_signals=(
            "The supplied mechanism is a folding hinge with two verified desk positions.",
            "The supplied contexts are a study desk, shared workspace, and travel setup.",
            "Compatibility beyond the supplied power source and shipping speed are unknown.",
        ),
        demonstrated_behavior=(
            "Use a visible mechanism and observable setup proof in every direction.",
            "Differentiate contexts, creator delivery, and proof setup.",
            "Keep compatibility and shipping boundaries explicit.",
        ),
    ),
)

FEW_SHOT_EXAMPLES_BY_DOMAIN: Mapping[
    FewShotDomain, tuple[FewShotExampleV1, ...]
] = MappingProxyType(
    {
        FewShotDomain.TIKTOK_SHOP: TIKTOK_SHOP_EXAMPLES,
        FewShotDomain.POD_PERSONALIZATION: POD_PERSONALIZATION_EXAMPLES,
        FewShotDomain.DROPSHIPPING: DROPSHIPPING_EXAMPLES,
    }
)
ALL_FEW_SHOT_EXAMPLES: Final = tuple(
    example
    for domain in FewShotDomain
    for example in FEW_SHOT_EXAMPLES_BY_DOMAIN[domain]
)
ALL_FEW_SHOT_EXAMPLE_IDS: Final = tuple(
    example.example_id for example in ALL_FEW_SHOT_EXAMPLES
)

_PRIMARY_DOMAIN_KEYS: Final = frozenset(
    {
        "business_model",
        "commerce_domain",
        "commerce_model",
        "domain",
        "seller_model",
    }
)
_DOMAIN_ALIASES: Mapping[FewShotDomain, tuple[str, ...]] = MappingProxyType(
    {
        FewShotDomain.POD_PERSONALIZATION: (
            "pod",
            "print on demand",
            "personalization",
            "personalized",
            "customized",
        ),
        FewShotDomain.DROPSHIPPING: (
            "dropship",
            "dropshipping",
            "drop shipping",
        ),
        FewShotDomain.TIKTOK_SHOP: (
            "tiktok",
            "tiktok shop",
            "tiktok shop us",
            "tiktok affiliate",
        ),
    }
)
_DOMAIN_MATCH_ORDER: Final = (
    FewShotDomain.POD_PERSONALIZATION,
    FewShotDomain.DROPSHIPPING,
    FewShotDomain.TIKTOK_SHOP,
)


def match_few_shot_domain(
    context: ViraldyOperationContextV1,
) -> FewShotDomain | None:
    explicit_domain = _match_domain(
        _values_for_keys(
            (context.seller_constraints, context.operation_payload),
            _PRIMARY_DOMAIN_KEYS,
        )
    )
    if explicit_domain is not None:
        return explicit_domain

    product_context = context.product_context
    if product_context is not None and (
        product_context.personalization.required
        or product_context.personalization.fields
    ):
        return FewShotDomain.POD_PERSONALIZATION

    values: tuple[object, ...] = (
        context.objective,
        context.target_market,
        context.seller_constraints,
        context.operation_payload,
    )
    if product_context is not None:
        values = (
            *values,
            product_context.model_dump(mode="json"),
        )
    return _match_domain(_text_values(values))


def select_few_shot_examples(
    context: ViraldyOperationContextV1,
) -> tuple[FewShotExampleV1, ...]:
    domain = match_few_shot_domain(context)
    if domain is None:
        return ()
    operation = str(context.operation)
    matching = (
        example
        for example in FEW_SHOT_EXAMPLES_BY_DOMAIN[domain]
        if operation in example.operations
    )
    return tuple(matching)[:MAX_RUNTIME_FEW_SHOT_EXAMPLES]


def render_runtime_few_shot_content(
    examples: Sequence[FewShotExampleV1],
) -> str:
    selected = tuple(examples)
    content = RuntimeFewShotContentV1(
        selected_example_ids=tuple(example.example_id for example in selected),
        examples=selected,
    )
    return json.dumps(
        content.model_dump(mode="json"),
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def _match_domain(values: Iterable[str]) -> FewShotDomain | None:
    normalized = " ".join(_normalize(value) for value in values)
    if not normalized:
        return None
    padded = f" {normalized} "
    for domain in _DOMAIN_MATCH_ORDER:
        aliases = _DOMAIN_ALIASES[domain]
        if any(f" {_normalize(alias)} " in padded for alias in aliases):
            return domain
    return None


def _values_for_keys(values: object, keys: frozenset[str]) -> tuple[str, ...]:
    if isinstance(values, Mapping):
        selected = tuple(
            text
            for raw_key, nested in values.items()
            if _normalize_key(str(raw_key)) in keys
            for text in _text_values(nested)
        )
        nested_selected = tuple(
            text
            for nested in values.values()
            for text in _values_for_keys(nested, keys)
        )
        return (*selected, *nested_selected)
    if isinstance(values, Sequence) and not isinstance(
        values, str | bytes | bytearray
    ):
        return tuple(
            text
            for nested in values
            for text in _values_for_keys(nested, keys)
        )
    return ()


def _text_values(value: object) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,)
    if isinstance(value, Mapping):
        return tuple(
            text
            for raw_key, nested in value.items()
            for text in (str(raw_key), *_text_values(nested))
        )
    if isinstance(value, Sequence) and not isinstance(
        value, str | bytes | bytearray
    ):
        return tuple(text for nested in value for text in _text_values(nested))
    return ()


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def _normalize_key(value: str) -> str:
    return "_".join(_normalize(value).split())


__all__ = [
    "ALL_FEW_SHOT_EXAMPLE_IDS",
    "ALL_FEW_SHOT_EXAMPLES",
    "DROPSHIPPING_EXAMPLES",
    "FEW_SHOT_EXAMPLES_BY_DOMAIN",
    "MAX_RUNTIME_FEW_SHOT_EXAMPLES",
    "POD_PERSONALIZATION_EXAMPLES",
    "RUNTIME_FEW_SHOT_SCHEMA_VERSION",
    "TIKTOK_SHOP_EXAMPLES",
    "FewShotDomain",
    "FewShotExampleV1",
    "RuntimeFewShotContentV1",
    "match_few_shot_domain",
    "render_runtime_few_shot_content",
    "select_few_shot_examples",
]
