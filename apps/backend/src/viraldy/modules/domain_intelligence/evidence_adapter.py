from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from viraldy.modules.domain_intelligence.schemas import (
    Confidence,
    EvidenceSource,
    NormalizedEvidence,
    NormalizedEvidenceBundle,
)
from viraldy.modules.media_analysis.public import EvidenceItemModel, MediaObservationBundleV1


def adapt_media_evidence(
    items: Sequence[EvidenceItemModel],
    observation_bundle: MediaObservationBundleV1 | None = None,
) -> NormalizedEvidenceBundle:
    normalized = [_normalize_item(item) for item in items]
    evidence_types = {item.kind for item in normalized}
    coverage = {
        "transcript": "transcript_segment" in evidence_types,
        "ocr": bool({"on_screen_text", "product_identity", "personalization"} & evidence_types),
        "visual_observations": bool(
            {
                "product_appearance",
                "product_visibility_summary",
                "demo_summary",
                "proof_signal",
            }
            & evidence_types
        ),
        "opening": "hook_signal" in evidence_types,
        "cta": "cta_signal" in evidence_types,
    }
    missing_required = [
        name for name in ("visual_observations", "opening", "cta") if not coverage[name]
    ]
    strengths = _observed_strengths(normalized)
    metadata: dict[str, object] = {}
    if observation_bundle is not None:
        metadata["media_observation_schema_version"] = observation_bundle.schema_version
    model_provider_versions = list(
        dict.fromkeys(
            (item.provider, item.model_version)
            for item in items
            if item.provider or item.model_version
        )
    )
    if model_provider_versions:
        metadata["model_provider_versions"] = [
            {"provider": provider, "model_version": model_version}
            for provider, model_version in model_provider_versions
        ]
    pipeline_version = next(
        (item.pipeline_version for item in items if item.pipeline_version), None
    )
    return NormalizedEvidenceBundle(
        items=normalized,
        coverage=coverage,
        missing_required=missing_required,
        unknowns=["insufficient_evidence"] if missing_required else [],
        strengths=strengths,
        metadata=metadata,
        pipeline_version=pipeline_version,
    )


def _normalize_item(item: EvidenceItemModel) -> NormalizedEvidence:
    value = dict(item.value_json or {})
    kind = _normalized_kind(item.evidence_type, value)
    return NormalizedEvidence(
        id=str(item.id),
        kind=kind,
        source=_source(item.evidence_type),
        observed=_observed(item.evidence_type, value),
        start_ms=item.start_ms,
        end_ms=item.end_ms,
        confidence=_confidence(item.confidence),
        value=value,
    )


def _normalized_kind(evidence_type: str, value: dict[str, object]) -> str:
    if evidence_type == "on_screen_text":
        role = str(value.get("text_role") or "")
        if role == "product_identity":
            return "product_identity"
        if role == "personalization":
            return "personalization"
        if role == "disclosure":
            return "disclosure"
        if role == "offer":
            return "offer"
    if evidence_type == "claim_signal":
        return "shipping_claim" if value.get("category") == "shipping" else "claim"
    if evidence_type == "offer_signal":
        return "offer"
    return evidence_type


def _source(evidence_type: str) -> EvidenceSource:
    if evidence_type == "transcript_segment":
        return "transcript"
    if evidence_type == "on_screen_text":
        return "ocr"
    return "video"


def _observed(evidence_type: str, value: dict[str, object]) -> str:
    for field in (
        "text",
        "spoken_text",
        "overlay_text",
        "visual_description",
        "description",
        "action",
        "offer_type",
        "cta_type",
        "demo_type",
        "hook_type",
    ):
        candidate = value.get(field)
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    return evidence_type.replace("_", " ")


def _confidence(value: Decimal | float | None) -> Confidence:
    if value is None:
        return "low"
    confidence = float(value)
    if confidence >= 0.8:
        return "high"
    if confidence >= 0.5:
        return "medium"
    return "low"


def _observed_strengths(items: list[NormalizedEvidence]) -> list[str]:
    strengths: list[str] = []
    for item in items:
        if item.confidence == "low":
            continue
        if item.kind == "demo_summary" and item.value.get("detected") is True:
            strengths.append("Keep the product demonstration that is already understandable.")
        elif item.kind == "creator_signal" and item.value.get("authenticity_cues"):
            strengths.append("Keep the creator delivery and authentic moments that already work.")
        elif item.kind == "proof_signal":
            strengths.append("Keep the observable proof moment and its supporting footage.")
        elif item.kind == "hook_signal":
            strengths.append("Keep the clear opening idea while refining the product connection.")
    return list(dict.fromkeys(strengths))[:5]
