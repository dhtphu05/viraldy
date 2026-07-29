from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, cast
from uuid import UUID, uuid4

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
