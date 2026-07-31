from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import ValidationError

from viraldy.modules.ai_gateway.context import (
    EvidenceItemForModelV1,
    ViraldyOperationContextV1,
)
from viraldy.modules.ai_gateway.operations import AiOperationName


def _context(**overrides: object) -> ViraldyOperationContextV1:
    payload: dict[str, object] = {
        "operation": AiOperationName.PATTERN_KIT_EXTRACT,
        "request_id": "req-context-1",
        "workspace_id": uuid4(),
        "source_artifact_ids": [uuid4()],
        "source_version_ids": [uuid4()],
        "evidence_catalog": [
            EvidenceItemForModelV1(
                evidence_id=uuid4(),
                source_artifact_id=uuid4(),
                source_version_id=uuid4(),
                evidence_type="visual_observation",
                observation_id="obs-product-reveal",
                start_ms=1200,
                end_ms=2400,
                value={"description": "The product enters frame."},
                confidence=0.93,
                source="sampled_frame",
            )
        ],
        "seller_constraints": {"market": "US"},
        "operation_payload": {"selected_reference_count": 1},
        "schema_version": "pattern_kit_v1",
        "prompt_version": "pattern_kit_v2",
    }
    payload.update(overrides)
    return ViraldyOperationContextV1.model_validate(payload)


def test_operation_context_serializes_stably_without_python_repr() -> None:
    context = _context()

    first = context.stable_json()
    second = context.stable_json()

    assert first == second
    assert first.startswith('{"actor_user_id":null,')
    assert '"operation":"pattern_kit_extract"' in first
    assert "UUID(" not in first


@pytest.mark.parametrize(
    "operation_payload",
    [
        {"api_key": "sk-not-a-real-key"},
        {"frame": "data:image/png;base64,AAAA"},
        {
            "media_url": (
                "https://storage.example/media?"
                "X-Amz-Signature=not-a-real-signature"
            )
        },
    ],
)
def test_operation_context_rejects_sensitive_or_binary_material(
    operation_payload: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        _context(operation_payload=operation_payload)


def test_operation_context_rejects_invalid_evidence_ranges() -> None:
    with pytest.raises(ValidationError):
        EvidenceItemForModelV1(
            evidence_id=uuid4(),
            source_version_id=uuid4(),
            evidence_type="ocr",
            start_ms=2000,
            end_ms=1000,
            value={"text": "SwiftPress"},
            source="ocr",
        )


def test_operation_context_rejects_duplicate_evidence_ids() -> None:
    evidence_id = uuid4()
    source_version_id = uuid4()
    item = EvidenceItemForModelV1(
        evidence_id=evidence_id,
        source_version_id=source_version_id,
        evidence_type="transcript",
        value={"text": "Steam it fast."},
        source="asr",
    )

    with pytest.raises(ValidationError):
        _context(evidence_catalog=[item, item])
