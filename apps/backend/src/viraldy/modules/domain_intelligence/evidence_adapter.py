from __future__ import annotations

import re
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
        "transcript": any(item.source == "transcript" for item in normalized),
        "ocr": any(item.source == "ocr" for item in normalized),
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
    if item.evidence_type == "transcript_segment":
        value = _with_transcript_disclosure_details(value)
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
    if evidence_type == "transcript_segment" and value.get("disclosure_detected") is True:
        return "disclosure"
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


def _with_transcript_disclosure_details(value: dict[str, object]) -> dict[str, object]:
    text = _transcript_text(value)
    details = _disclosure_details(text)
    if details is None:
        return value
    return {
        **value,
        "present": True,
        "disclosure_detected": True,
        "modality": "spoken",
        **details,
    }


def _transcript_text(value: dict[str, object]) -> str:
    for field in ("text", "spoken_text", "transcript", "utterance"):
        candidate = value.get(field)
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    return ""


def _disclosure_details(text: str) -> dict[str, object] | None:
    normalized = text.casefold()
    if _contains_any(normalized, ("paid partnership", "sponsored", "gifted", "affiliate")):
        return {"language": "en"}
    if re.search(r"(?:^|[^a-z])ad(?:[^a-z]|$)", normalized):
        return {"language": "en"}
    if _contains_any(text, ("협찬", "광고", "스폰서")):
        details: dict[str, object] = {"language": "ko"}
        if "협찬" in text:
            details["translation"] = "This video was made with brand sponsorship."
        return details
    if _contains_any(
        normalized,
        (
            "tài trợ",
            "tai tro",
            "quảng cáo",
            "quang cao",
            "được tặng",
            "duoc tang",
            "liên kết tiếp thị",
            "lien ket tiep thi",
        ),
    ):
        return {"language": "vi"}
    return None


def _contains_any(value: str, needles: tuple[str, ...]) -> bool:
    return any(needle in value for needle in needles)


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
