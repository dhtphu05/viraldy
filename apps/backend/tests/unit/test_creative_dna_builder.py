from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, cast
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from viraldy.modules.creative_dna.contracts import CreativeDnaV1, ProductDnaV1
from viraldy.modules.creative_dna.service import _build_creative_dna, _evidence_by_type
from viraldy.modules.media_analysis.public import EvidenceItemModel


@dataclass(slots=True)
class FakeEvidence:
    evidence_type: str
    value_json: dict[str, Any]
    id: UUID = field(default_factory=uuid4)
    start_ms: int | None = None
    end_ms: int | None = None
    confidence: float | None = 0.85
    source: str = "vision"


def test_creative_dna_is_evidence_driven_without_category_leakage() -> None:
    evidence = cast(
        list[EvidenceItemModel],
        [
            FakeEvidence(
                "hook_signal",
                {
                    "hook_type": "result_first",
                    "spoken_text": "My curls looked smoother in one pass.",
                    "visual_description": "close shot of hair tool result",
                    "buyer_pain": "frizzy curls",
                    "clarity": "clear",
                    "confidence": 0.9,
                },
                start_ms=0,
                end_ms=1200,
            ),
            FakeEvidence(
                "product_visibility_summary",
                {
                    "first_appearance_ms": 800,
                    "total_visible_ms": 5000,
                    "screen_time_ratio": 0.55,
                    "clear_close_up_present": True,
                    "usage_present": True,
                },
            ),
            FakeEvidence(
                "demo_summary",
                {
                    "detected": True,
                    "demo_type": "usage",
                    "before_state_visible": True,
                    "after_state_visible": True,
                    "mechanism_clarity": "clear",
                    "continuity": "continuous",
                    "confidence": 0.88,
                },
            ),
        ],
    )

    dna = _build_creative_dna(_evidence_by_type(evidence))
    payload = dna.model_dump(mode="json")
    serialized = json.dumps(payload)

    assert payload["schema_version"] == "creative_dna_v1"
    assert payload["opening"]["primary_hook_type"]["value"] == "result_first"
    assert payload["opening"]["primary_hook_type"]["evidence_ids"]
    assert "kitchen" not in serialized
    assert "counter" not in serialized
    assert "home_organizer" not in serialized


def test_creative_dna_preserves_modal_text_and_editing_ranges() -> None:
    evidence = cast(
        list[EvidenceItemModel],
        [
            FakeEvidence(
                "cta_signal",
                {
                    "cta_type": "product_tag",
                    "text": "Check the product tag",
                    "spoken_text": "Check the product tag",
                    "overlay_text": "Product tag",
                    "product_tag_visible": True,
                    "confidence": 0.9,
                },
                start_ms=2500,
                end_ms=3200,
            ),
            FakeEvidence(
                "offer_signal",
                {
                    "offer_type": "limited_time",
                    "text": "Today only",
                    "urgency_present": True,
                    "confidence": 0.8,
                },
                start_ms=1800,
                end_ms=2200,
            ),
            FakeEvidence(
                "editing_signal",
                {
                    "cut_count": 3,
                    "average_shot_duration_ms": 900,
                    "first_three_second_cut_count": 2,
                    "pattern_interrupts": [{"start_ms": 0, "end_ms": 300}],
                    "dead_air_ranges": [{"start_ms": 4000, "end_ms": 4500}],
                    "caption_density": "medium",
                    "visual_pacing": "fast",
                    "transition_types": ["jump_cut"],
                    "confidence": 0.8,
                },
            ),
        ],
    )

    payload = _build_creative_dna(_evidence_by_type(evidence)).model_dump(mode="json")

    assert payload["cta"]["spoken_text"]["value"] == "Check the product tag"
    assert payload["cta"]["overlay_text"]["value"] == "Product tag"
    assert payload["offer"]["urgency_present"]["value"] is True
    assert payload["editing"]["pattern_interrupts"]["value"] == [{"start_ms": 0, "end_ms": 300}]
    assert payload["editing"]["dead_air_ranges"]["value"] == [{"start_ms": 4000, "end_ms": 4500}]


def test_critical_dna_fields_reject_invalid_types() -> None:
    with pytest.raises(ValidationError):
        ProductDnaV1(
            first_appearance_ms=_observed_payload("early"),
            total_visible_ms=_observed_payload(5000),
            screen_time_ratio=_observed_payload(0.5),
            close_up_present=_observed_payload(True),
            hero_shot_present=_observed_payload(False),
            usage_present=_observed_payload(True),
            product_match=_observed_payload(0.8),
            appearance_sequence=_observed_payload([]),
        )


def test_creative_dna_schema_has_no_untyped_observed_values() -> None:
    schema = CreativeDnaV1.model_json_schema()
    untyped_value_nodes = [
        definition_name
        for definition_name, definition in schema["$defs"].items()
        if isinstance(definition, dict)
        and isinstance(definition.get("properties"), dict)
        and isinstance(definition["properties"].get("value"), dict)
        and not any(
            key in definition["properties"]["value"]
            for key in ("type", "anyOf", "$ref")
        )
    ]

    assert untyped_value_nodes == []


def _observed_payload(value: object) -> dict[str, object]:
    return {"value": value, "confidence": 0.9, "evidence_ids": [], "status": "observed"}
