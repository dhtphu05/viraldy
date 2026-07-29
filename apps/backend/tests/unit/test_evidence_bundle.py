from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, cast
from uuid import UUID, uuid4

import pytest

from viraldy.modules.media_analysis.evidence_bundle import (
    build_evidence_bundle,
    validate_evidence_payload,
)
from viraldy.modules.media_analysis.public import EvidenceItemModel
from viraldy.shared.errors.base import AppError


@dataclass(slots=True)
class FakeEvidence:
    evidence_type: str
    source: str
    start_ms: int | None
    end_ms: int | None
    value_json: dict[str, Any]
    confidence: Decimal | None = Decimal("0.8")
    id: UUID = field(default_factory=uuid4)
    pipeline_version: str | None = "media_pipeline_v1"


def test_evidence_bundle_reports_high_confidence_and_sorted_timeline() -> None:
    asset_version_id = uuid4()
    evidence = cast(
        list[EvidenceItemModel],
        [
            FakeEvidence("cta_signal", "derived", 18000, 20000, {"text": "Shop now"}),
            FakeEvidence("hook_signal", "derived", 0, 2100, {"text": "messy counter"}),
            FakeEvidence("proof_signal", "vision", 15000, 18000, {"text": "after result"}),
            FakeEvidence("demo_signal", "vision", 6500, 14000, {"text": "demo"}),
            FakeEvidence("product_first_appearance", "vision", 1200, 2200, {"value": 1200}),
            FakeEvidence("transcript_segment", "asr", 0, 2100, {"text": "my counter"}),
            FakeEvidence("on_screen_text", "ocr", 0, 2100, {"text": "tiny kitchen reset"}),
        ],
    )

    bundle = build_evidence_bundle(asset_version_id, evidence)

    assert bundle.confidence == "high"
    assert bundle.missing_required == []
    assert bundle.pipeline_version == "media_pipeline_v1"
    assert [item.type for item in bundle.timeline[:2]] == [
        "hook_signal",
        "on_screen_text",
    ]


def test_evidence_bundle_uses_low_confidence_when_required_visual_signals_are_missing() -> None:
    asset_version_id = uuid4()
    evidence = cast(
        list[EvidenceItemModel],
        [FakeEvidence("transcript_segment", "asr", 0, 2100, {"text": "spoken only"})],
    )

    bundle = build_evidence_bundle(asset_version_id, evidence)

    assert bundle.confidence == "low"
    assert bundle.missing_required == ["visual_observations", "opening", "cta"]


def test_evidence_payload_validation_rejects_bad_timestamp_and_confidence() -> None:
    asset_version_id = uuid4()
    valid = {
        "asset_version_id": asset_version_id,
        "analysis_run_type": "score",
        "evidence_type": "hook_signal",
        "identity_hash": "hash",
        "start_ms": 100,
        "end_ms": 50,
        "value_json": {"text": "bad range"},
        "confidence": 0.8,
        "source": "derived",
    }
    with pytest.raises(AppError) as exc_info:
        validate_evidence_payload(asset_version_id, valid)
    assert exc_info.value.code == "EVIDENCE_PERSIST_FAILED"

    invalid_confidence = {**valid, "end_ms": 150, "confidence": 1.5}
    with pytest.raises(AppError) as exc_info:
        validate_evidence_payload(asset_version_id, invalid_confidence)
    assert exc_info.value.code == "EVIDENCE_PERSIST_FAILED"
