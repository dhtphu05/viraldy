from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, cast
from uuid import UUID, uuid4

from viraldy.modules.campaign_packs.requirements import (
    CompiledRequirementV2,
    compiled_requirements_to_json,
)
from viraldy.modules.media_analysis.fixtures import fixture_media_contract
from viraldy.modules.media_analysis.public import EvidenceItemModel
from viraldy.modules.media_analysis.service import SyncMediaEvidencePipeline
from viraldy.modules.preflight.service import calculate_preflight_result
from viraldy.modules.tiktok_scorer.scorer import score_tiktok_structure


@dataclass(slots=True)
class FakeEvidence:
    evidence_type: str
    value_json: dict[str, Any]
    id: UUID = field(default_factory=uuid4)
    start_ms: int | None = None
    end_ms: int | None = None
    confidence: float | None = None
    source: str = "vision"


def test_semantic_category_matrix_strong_fixture_paths() -> None:
    fixture_ids = [
        "viraldy-demo-reference-v1",
        "viraldy-fixture-beauty-tool-v1",
        "viraldy-fixture-pod-gift-v1",
        "viraldy-fixture-pet-accessory-v1",
        "viraldy-fixture-fashion-accessory-v1",
    ]
    requirements = compiled_requirements_to_json(
        [
            CompiledRequirementV2(
                id="product_before_3000",
                requirement_type="product",
                source_path="semantic_matrix.product_timing",
                description="Product must appear before 3000ms.",
                severity="hard",
                matcher_type="product_visibility_timing",
                matcher_config={"before_ms": 3000},
                expected_semantics="timing",
            ),
            CompiledRequirementV2(
                id="product_tag_presence",
                requirement_type="cta",
                source_path="semantic_matrix.cta",
                description="Product tag must be visible.",
                severity="hard",
                matcher_type="product_tag_presence",
                matcher_config={},
                expected_semantics="presence",
            ),
        ]
    )

    for fixture_id in fixture_ids:
        evidence = _fixture_evidence(fixture_id)
        score = score_tiktok_structure(
            evidence,
            media_duration_ms=28000,
            product_context_present=True,
        )
        preflight = calculate_preflight_result(
            score,
            {"must_show": []},
            requirements,
            evidence,
            {"schema_version": "product_context_v1"},
            28000,
        )
        statuses = {
            item["requirement_id"]: item
            for item in preflight["brief_alignment"]["requirements"]
        }

        assert score["schema_version"] == "tiktok_score_v2"
        assert preflight["brief_alignment"]["schema_version"] == "ugc_preflight_v2"
        assert statuses["product_before_3000"]["status"] == "satisfied"
        assert statuses["product_before_3000"]["observed"]["first_appearance_ms"] <= 3000
        assert statuses["product_before_3000"]["evidence_ids"]
        assert statuses["product_tag_presence"]["status"] == "satisfied"
        assert statuses["product_tag_presence"]["evidence_ids"]


def _fixture_evidence(fixture_id: str) -> list[EvidenceItemModel]:
    contract = fixture_media_contract(fixture_id)
    rows = SyncMediaEvidencePipeline._evidence_rows(  # noqa: SLF001
        None, uuid4(), "semantic_matrix", contract
    )
    return cast(
        list[EvidenceItemModel],
        [
            FakeEvidence(
                row["evidence_type"],
                row["value_json"],
                start_ms=cast(int | None, row["start_ms"]),
                end_ms=cast(int | None, row["end_ms"]),
                confidence=cast(float | None, row["confidence"]),
                source=str(row["source"]),
            )
            for row in rows
        ],
    )
