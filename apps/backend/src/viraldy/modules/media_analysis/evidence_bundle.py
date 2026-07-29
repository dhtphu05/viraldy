from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from viraldy.modules.media_analysis.models import EvidenceItemModel
from viraldy.shared.errors.base import AppError

ALLOWED_EVIDENCE_TYPES = {
    "transcript_segment",
    "on_screen_text",
    "product_first_appearance",
    "hook_signal",
    "demo_signal",
    "proof_signal",
    "cta_signal",
    "claim_signal",
}
ALLOWED_SOURCES = {"asr", "ocr", "vision", "derived"}
REQUIRED_COMPLETENESS_SIGNALS = {
    "visual_observations": {"product_first_appearance", "demo_signal", "proof_signal"},
    "opening": {"hook_signal"},
    "cta": {"cta_signal"},
}
OPTIONAL_COMPLETENESS_SIGNALS = {
    "transcript": {"transcript_segment"},
    "ocr": {"on_screen_text"},
}


class EvidenceTimelineItem(BaseModel):
    start_ms: int
    end_ms: int
    type: str
    label: str
    source: str
    confidence: float | None = Field(default=None, ge=0, le=1)
    evidence_id: str


class EvidenceBundleResponse(BaseModel):
    asset_version_id: UUID
    pipeline_version: str | None
    confidence: str
    completeness: dict[str, bool]
    missing_required: list[str]
    timeline: list[EvidenceTimelineItem]


@dataclass(frozen=True, slots=True)
class EvidenceValidationResult:
    confidence: float | None


def validate_evidence_payload(asset_version_id: UUID, item: Mapping[str, Any]) -> None:
    if item.get("asset_version_id") != asset_version_id:
        raise AppError("EVIDENCE_PERSIST_FAILED", "Evidence asset version mismatch.")
    evidence_type = item.get("evidence_type")
    if evidence_type not in ALLOWED_EVIDENCE_TYPES:
        raise AppError("EVIDENCE_PERSIST_FAILED", "Evidence type is not supported.")
    source = item.get("source")
    if source not in ALLOWED_SOURCES:
        raise AppError("EVIDENCE_PERSIST_FAILED", "Evidence source is not supported.")
    _validate_timestamp("start_ms", item.get("start_ms"))
    _validate_timestamp("end_ms", item.get("end_ms"))
    start_ms = item.get("start_ms")
    end_ms = item.get("end_ms")
    if isinstance(start_ms, int) and isinstance(end_ms, int) and end_ms < start_ms:
        raise AppError("EVIDENCE_PERSIST_FAILED", "Evidence timestamp range is invalid.")
    confidence = item.get("confidence")
    if confidence is not None and not (0 <= float(confidence) <= 1):
        raise AppError("EVIDENCE_PERSIST_FAILED", "Evidence confidence is outside 0..1.")
    if not item.get("identity_hash"):
        raise AppError("EVIDENCE_PERSIST_FAILED", "Evidence identity hash is required.")


def build_evidence_bundle(
    asset_version_id: UUID,
    evidence: list[EvidenceItemModel],
) -> EvidenceBundleResponse:
    evidence_types = {item.evidence_type for item in evidence}
    completeness: dict[str, bool] = {}
    missing_required: list[str] = []
    for name, required_types in REQUIRED_COMPLETENESS_SIGNALS.items():
        present = bool(evidence_types.intersection(required_types))
        completeness[name] = present
        if not present:
            missing_required.append(name)
    for name, optional_types in OPTIONAL_COMPLETENESS_SIGNALS.items():
        completeness[name] = bool(evidence_types.intersection(optional_types))
    confidence = _bundle_confidence(completeness, missing_required)
    pipeline_version = next(
        (item.pipeline_version for item in evidence if item.pipeline_version), None
    )
    return EvidenceBundleResponse(
        asset_version_id=asset_version_id,
        pipeline_version=pipeline_version,
        confidence=confidence,
        completeness=completeness,
        missing_required=missing_required,
        timeline=_timeline(evidence),
    )


def _timeline(evidence: list[EvidenceItemModel]) -> list[EvidenceTimelineItem]:
    items: list[EvidenceTimelineItem] = []
    for item in evidence:
        if item.start_ms is None:
            continue
        end_ms = item.end_ms if item.end_ms is not None else item.start_ms
        if end_ms < item.start_ms:
            continue
        items.append(
            EvidenceTimelineItem(
                start_ms=item.start_ms,
                end_ms=end_ms,
                type=item.evidence_type,
                label=_label(item),
                source=item.source,
                confidence=float(item.confidence) if item.confidence is not None else None,
                evidence_id=str(item.id),
            )
        )
    return sorted(items, key=lambda item: (item.start_ms, item.end_ms, item.type))


def _bundle_confidence(completeness: dict[str, bool], missing_required: list[str]) -> str:
    if missing_required:
        return "low"
    optional_count = sum(1 for name in OPTIONAL_COMPLETENESS_SIGNALS if completeness.get(name))
    return "high" if optional_count == len(OPTIONAL_COMPLETENESS_SIGNALS) else "medium"


def _label(item: EvidenceItemModel) -> str:
    value = item.value_json
    if "text" in value:
        return str(value["text"])
    if "value" in value:
        return str(value["value"])
    return item.evidence_type.replace("_", " ")


def _validate_timestamp(name: str, value: object) -> None:
    if value is None:
        return
    if not isinstance(value, int) or value < 0:
        raise AppError("EVIDENCE_PERSIST_FAILED", f"Evidence {name} must be non-negative.")
