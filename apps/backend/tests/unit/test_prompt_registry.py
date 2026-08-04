from __future__ import annotations

import ast
from pathlib import Path

import pytest
from pydantic import ValidationError

from viraldy.modules.ai_gateway.context import ViraldyOperationContextV1
from viraldy.modules.ai_gateway.operations import AiOperationName
from viraldy.modules.ai_gateway.prompt_content.examples import (
    ALL_FEW_SHOT_EXAMPLE_IDS,
    MAX_RUNTIME_FEW_SHOT_EXAMPLES,
    FewShotDomain,
    match_few_shot_domain,
    render_runtime_few_shot_content,
    select_few_shot_examples,
)
from viraldy.modules.ai_gateway.prompts import (
    ADAPTATION_PROMPT_VERSION,
    CAMPAIGN_PACK_PROMPT_VERSION,
    CONCEPT_VIDEO_PREVIEW_PROMPT_VERSION,
    CREATIVE_DNA_PROMPT_VERSION,
    DECISION_SUMMARY_OPERATION,
    DECISION_SUMMARY_OUTPUT_SCHEMA_VERSION,
    DECISION_SUMMARY_PROMPT_VERSION,
    MEDIA_OBSERVATION_PROMPT_VERSION,
    PATTERN_KIT_PROMPT_VERSION,
    PROMPT_PACKAGE_REGISTRY,
    REVISION_MESSAGE_PROMPT_VERSION,
    STORYBOARD_IMAGE_PROMPT_VERSION,
    UGC_EXECUTION_BRIEF_PROMPT_VERSION,
    VIRAL_KIT_PROMPT_VERSION,
    PromptPackage,
    get_prompt_package,
    iter_prompt_packages,
)
from viraldy.modules.ai_gateway.prompts import (
    ADAPTATION_SCHEMA_VERSION as EXPORTED_ADAPTATION_SCHEMA_VERSION,
)
from viraldy.modules.creative_domain.schema_versions import (
    ADAPTATION_SCHEMA_VERSION,
    CAMPAIGN_PACK_SCHEMA_VERSION,
    CREATIVE_DNA_SCHEMA_VERSION,
    MEDIA_OBSERVATION_SCHEMA_VERSION,
    PATTERN_KIT_SCHEMA_VERSION,
    REVISION_MESSAGE_SCHEMA_VERSION,
    STORYBOARD_IMAGE_SCHEMA_VERSION,
    UGC_EXECUTION_BRIEF_SCHEMA_VERSION,
    VIDEO_PREVIEW_SCHEMA_VERSION,
    VIRAL_KIT_SCHEMA_VERSION,
)
from viraldy.modules.products.contracts import (
    PersonalizationFieldV1,
    ProductContextV1,
    ProductIdentityV1,
    ProductPersonalizationV1,
)

EXPECTED_SCHEMA_VERSIONS = {
    AiOperationName.MEDIA_OBSERVATION.value: MEDIA_OBSERVATION_SCHEMA_VERSION,
    AiOperationName.CREATIVE_DNA_BUILD.value: CREATIVE_DNA_SCHEMA_VERSION,
    AiOperationName.PATTERN_KIT_EXTRACT.value: PATTERN_KIT_SCHEMA_VERSION,
    AiOperationName.VIRAL_KIT_COMPOSE.value: VIRAL_KIT_SCHEMA_VERSION,
    AiOperationName.ADAPTATION_GENERATE.value: ADAPTATION_SCHEMA_VERSION,
    AiOperationName.CAMPAIGN_PACK_GENERATE.value: CAMPAIGN_PACK_SCHEMA_VERSION,
    AiOperationName.SELLER_DECISION_SUMMARY.value: (
        DECISION_SUMMARY_OUTPUT_SCHEMA_VERSION
    ),
    AiOperationName.REVISION_MESSAGE_GENERATE.value: REVISION_MESSAGE_SCHEMA_VERSION,
    AiOperationName.UGC_EXECUTION_BRIEF_SYNTHESIS.value: UGC_EXECUTION_BRIEF_SCHEMA_VERSION,
    AiOperationName.STORYBOARD_IMAGE_GENERATE.value: STORYBOARD_IMAGE_SCHEMA_VERSION,
    AiOperationName.CONCEPT_VIDEO_PREVIEW_GENERATE.value: VIDEO_PREVIEW_SCHEMA_VERSION,
}

EXPECTED_COMPATIBILITY_VERSIONS = {
    AiOperationName.MEDIA_OBSERVATION.value: MEDIA_OBSERVATION_PROMPT_VERSION,
    AiOperationName.CREATIVE_DNA_BUILD.value: CREATIVE_DNA_PROMPT_VERSION,
    AiOperationName.PATTERN_KIT_EXTRACT.value: PATTERN_KIT_PROMPT_VERSION,
    AiOperationName.VIRAL_KIT_COMPOSE.value: VIRAL_KIT_PROMPT_VERSION,
    AiOperationName.ADAPTATION_GENERATE.value: ADAPTATION_PROMPT_VERSION,
    AiOperationName.CAMPAIGN_PACK_GENERATE.value: CAMPAIGN_PACK_PROMPT_VERSION,
    AiOperationName.SELLER_DECISION_SUMMARY.value: DECISION_SUMMARY_PROMPT_VERSION,
    AiOperationName.REVISION_MESSAGE_GENERATE.value: REVISION_MESSAGE_PROMPT_VERSION,
    AiOperationName.UGC_EXECUTION_BRIEF_SYNTHESIS.value: UGC_EXECUTION_BRIEF_PROMPT_VERSION,
    AiOperationName.STORYBOARD_IMAGE_GENERATE.value: STORYBOARD_IMAGE_PROMPT_VERSION,
    AiOperationName.CONCEPT_VIDEO_PREVIEW_GENERATE.value: (
        CONCEPT_VIDEO_PREVIEW_PROMPT_VERSION
    ),
}


def test_every_current_operation_has_a_prompt_package() -> None:
    current_operations = {operation.value for operation in AiOperationName}

    assert current_operations <= set(PROMPT_PACKAGE_REGISTRY)
    assert DECISION_SUMMARY_OPERATION in PROMPT_PACKAGE_REGISTRY
    assert {package.operation for package in iter_prompt_packages()} == set(
        PROMPT_PACKAGE_REGISTRY
    )

    for operation in AiOperationName:
        assert get_prompt_package(operation) is PROMPT_PACKAGE_REGISTRY[operation.value]
        assert get_prompt_package(operation.value) is PROMPT_PACKAGE_REGISTRY[operation.value]


def test_prompt_packages_are_frozen_complete_and_uniquely_versioned() -> None:
    packages = iter_prompt_packages()
    versions = [package.prompt_version for package in packages]

    assert len(versions) == len(set(versions))
    assert all(version.strip() for version in versions)
    assert all(version.endswith("_few_shot_v1") for version in versions)
    assert all(package.prompt_name.strip() for package in packages)
    assert all(package.system_prompt.strip() for package in packages)
    assert all(package.developer_prompt.strip() for package in packages)
    assert all(package.output_schema_version.strip() for package in packages)
    assert all(package.example_ids for package in packages)
    assert all(
        package.default_max_output_tokens is None
        or package.default_max_output_tokens > 0
        for package in packages
    )

    package = packages[0]
    assert isinstance(package, PromptPackage)
    with pytest.raises(ValidationError):
        package.prompt_version = "mutated"  # type: ignore[misc]


def test_media_observation_prompt_is_bounded_for_complete_structured_output() -> None:
    package = get_prompt_package(AiOperationName.MEDIA_OBSERVATION)

    assert package.default_reasoning_effort == "low"
    assert package.default_max_output_tokens == 12_000
    assert "Keep the response compact" in package.developer_prompt
    assert "at most 8 product appearances" in package.developer_prompt


def test_creative_dna_prompt_is_bounded_for_complete_structured_output() -> None:
    package = get_prompt_package(AiOperationName.CREATIVE_DNA_BUILD)

    assert package.prompt_version == (
        "creative_dna_extraction_v4_grounded_statuses_few_shot_v1"
    )
    assert package.default_reasoning_effort == "low"
    assert package.default_max_output_tokens == 12_000
    assert "Keep the response compact" in package.developer_prompt
    assert "at most 5 reusable mechanisms" in package.developer_prompt
    assert "observed, inferred, or not_present" in package.developer_prompt
    assert "Unknown fields must use value=null" in package.developer_prompt


def test_pattern_kit_prompt_is_bounded_for_complete_structured_output() -> None:
    package = get_prompt_package(AiOperationName.PATTERN_KIT_EXTRACT)

    assert package.default_reasoning_effort == "low"
    assert package.default_max_output_tokens == 12_000
    assert "Keep the response compact" in package.developer_prompt
    assert "between 4 and 7 sequence beats" in package.developer_prompt
    assert "evidence_feature_paths" in package.developer_prompt


def test_canonical_system_policy_is_included_without_semantic_drift() -> None:
    system_prompt = get_prompt_package(AiOperationName.MEDIA_OBSERVATION).system_prompt
    required_clauses = (
        "You are Viraldy Creative Intelligence Engine",
        "Use only information supplied",
        "Never invent product features, price, discount, shipping time",
        "Every observed creative claim must reference supplied evidence IDs.",
        "Keep observed facts, interpretations, hypotheses and recommendations distinct.",
        "Do not infer that a creative is winning, viral, profitable or high-converting",
        "Separate buyer persona from creator persona at all times.",
        "Do not claim that a product tag exists unless evidence shows it.",
        "Distinguish mockup imagery from a filmed physical product.",
        "Do not convert an observed use case into a universal compatibility claim.",
        "Absence claims require adequate evidence coverage.",
        "Separate hard blockers, high-priority fixes and optional improvements.",
        "Extract reusable structure and mechanisms, not protected expression.",
        "Return only output matching the supplied schema.",
        "Do not include hidden reasoning or chain-of-thought.",
        "Keep machine enums stable even when seller-facing prose is localized.",
    )

    assert all(package.system_prompt == system_prompt for package in iter_prompt_packages())
    for clause in required_clauses:
        assert clause in system_prompt


def test_schema_versions_and_backwards_prompt_constants_are_stable() -> None:
    assert EXPORTED_ADAPTATION_SCHEMA_VERSION == ADAPTATION_SCHEMA_VERSION
    for operation, schema_version in EXPECTED_SCHEMA_VERSIONS.items():
        package = get_prompt_package(operation)
        assert package.output_schema_version == schema_version
        assert package.prompt_version == EXPECTED_COMPATIBILITY_VERSIONS[operation]


def test_golden_examples_are_referenced_by_id_not_embedded() -> None:
    example_ids = {
        example_id
        for package in iter_prompt_packages()
        for example_id in package.example_ids
    }

    assert example_ids == set(ALL_FEW_SHOT_EXAMPLE_IDS)
    assert all(len(package.developer_prompt) < 8_000 for package in iter_prompt_packages())
    assert all(
        "SwiftPress Mini Garment Steamer" not in package.developer_prompt
        for package in iter_prompt_packages()
    )


def _few_shot_context(
    *,
    seller_constraints: dict[str, object] | None = None,
    operation_payload: dict[str, object] | None = None,
    product_context: ProductContextV1 | None = None,
) -> ViraldyOperationContextV1:
    prompt = get_prompt_package(AiOperationName.PATTERN_KIT_EXTRACT)
    return ViraldyOperationContextV1(
        operation=AiOperationName.PATTERN_KIT_EXTRACT,
        request_id="req-few-shot",
        workspace_id="00000000-0000-0000-0000-000000000001",
        product_context=product_context,
        product_context_version=1 if product_context is not None else None,
        seller_constraints=seller_constraints or {},
        operation_payload=operation_payload or {},
        schema_version=prompt.output_schema_version,
        prompt_version=prompt.prompt_version,
    )


def test_runtime_few_shot_selection_matches_each_structured_domain_signal() -> None:
    pod_product = ProductContextV1(
        identity=ProductIdentityV1(
            name="Custom Recipe Towel",
            category="custom_home_goods",
            market="US",
        ),
        personalization=ProductPersonalizationV1(
            required=True,
            fields=[
                PersonalizationFieldV1(
                    key="family_name",
                    label="Family name",
                    expected_value="Nguyen",
                )
            ],
        ),
    )
    contexts = {
        FewShotDomain.TIKTOK_SHOP: _few_shot_context(
            seller_constraints={"target_platforms": ["TikTok Shop US"]}
        ),
        FewShotDomain.POD_PERSONALIZATION: _few_shot_context(
            product_context=pod_product
        ),
        FewShotDomain.DROPSHIPPING: _few_shot_context(
            operation_payload={"commerce_domain": "dropshipping"}
        ),
    }

    for expected_domain, context in contexts.items():
        selected = select_few_shot_examples(context)

        assert match_few_shot_domain(context) == expected_domain
        assert 1 <= len(selected) <= MAX_RUNTIME_FEW_SHOT_EXAMPLES
        assert all(example.domain == expected_domain for example in selected)
        assert all(context.operation.value in example.operations for example in selected)


def test_runtime_few_shot_content_is_bounded_and_does_not_leak_golden_outputs() -> None:
    selected = select_few_shot_examples(
        _few_shot_context(operation_payload={"domain": "pod"})
    )
    content = render_runtime_few_shot_content(selected)

    assert len(selected) == MAX_RUNTIME_FEW_SHOT_EXAMPLES
    assert "selected_example_ids" in content
    assert "SwiftPress Mini Garment Steamer" not in content
    assert "Personalized Dog Mom Crewneck" not in content
    assert "Rechargeable Mini Bag Sealer" not in content
    assert "Expected personalization: Milo" not in content
    assert "Observed personalization: Miles" not in content
    assert "makes every bag completely airtight" not in content
    assert "expected_output" not in content
    assert "http://" not in content
    assert "https://" not in content
    assert "signed_url" not in content
    assert "api_key" not in content


def test_prompt_registry_has_no_provider_code_import_dependency() -> None:
    backend_root = Path(__file__).parents[2]
    prompt_sources = [
        backend_root / "src/viraldy/modules/ai_gateway/prompt_packages.py",
        *sorted(
            (backend_root / "src/viraldy/modules/ai_gateway/prompt_content").glob("*.py")
        ),
    ]

    assert all(path.is_file() for path in prompt_sources)
    for path in prompt_sources:
        tree = ast.parse(path.read_text())
        imported_modules = {
            node.module or ""
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        }
        imported_modules.update(
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        )
        assert not any(
            "provider" in module or "openai" in module for module in imported_modules
        ), path
