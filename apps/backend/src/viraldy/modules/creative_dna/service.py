from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from viraldy.modules.creative_dna.repository import CreativeDnaRepository, SyncCreativeDnaRepository
from viraldy.modules.creative_dna.schemas import CreativeDnaVersionResponse
from viraldy.modules.creative_dna.taxonomy import (
    CREATIVE_DNA_PROMPT_VERSION,
    CREATIVE_DNA_TAXONOMY_VERSION,
)
from viraldy.modules.media_analysis.public import EvidenceItemModel
from viraldy.shared.errors.base import NotFoundError


class CreativeDnaService:
    def __init__(self, session: AsyncSession) -> None:
        self._repository = CreativeDnaRepository(session)

    async def get(self, workspace_id: UUID, dna_version_id: UUID) -> CreativeDnaVersionResponse:
        dna = await self._repository.get(workspace_id, dna_version_id)
        if dna is None:
            raise NotFoundError("CREATIVE_DNA_NOT_FOUND", "Creative DNA version was not found.")
        return CreativeDnaVersionResponse.model_validate(dna)

    async def latest_for_reference(
        self, workspace_id: UUID, reference_id: UUID
    ) -> CreativeDnaVersionResponse:
        dna = await self._repository.latest_for_reference(workspace_id, reference_id)
        if dna is None:
            raise NotFoundError("CREATIVE_DNA_NOT_FOUND", "Creative DNA version was not found.")
        return CreativeDnaVersionResponse.model_validate(dna)


class SyncCreativeDnaBuilder:
    def __init__(self, session: Session) -> None:
        self._repository = SyncCreativeDnaRepository(session)

    def build(
        self,
        workspace_id: UUID,
        asset_version_id: UUID,
        reference_id: UUID | None,
        evidence: list[EvidenceItemModel],
        analysis_mode: str,
    ):
        evidence_by_type = _evidence_by_type(evidence)
        first_product = _first_value(evidence_by_type, "product_first_appearance", "value", 999999)
        hook_ids = _ids(evidence_by_type, "hook_signal")
        product_ids = _ids(evidence_by_type, "product_first_appearance")
        demo_ids = _ids(evidence_by_type, "demo_signal")
        proof_ids = _ids(evidence_by_type, "proof_signal")
        cta_ids = _ids(evidence_by_type, "cta_signal")
        claim_ids = _ids(evidence_by_type, "claim_signal")
        confidence = "high" if hook_ids and product_ids and demo_ids else "medium"
        dna_json: dict[str, Any] = {
            "opening": {
                "hook_type": "problem_first",
                "hook_text": "My counter was always a mess.",
                "opening_visual": "messy kitchen counter",
                "face_present": True,
                "evidence_ids": hook_ids,
            },
            "product": {
                "first_appearance_ms": first_product,
                "screen_time_ratio": 0.42,
                "close_up_present": first_product <= 3000,
                "demo_type": "before_after",
                "evidence_ids": product_ids + demo_ids,
            },
            "narrative": {
                "structure": "problem_solution",
                "angle": "small_space_organization",
                "buyer_emotions": ["convenience", "transformation"],
                "evidence_ids": hook_ids + demo_ids,
            },
            "proof": {
                "proof_type": "visual_result",
                "strength_label": "medium",
                "evidence_ids": proof_ids,
            },
            "offer": {"present": False, "offer_type": None, "evidence_ids": []},
            "cta": {
                "present": bool(cta_ids),
                "cta_type": "product_tag",
                "first_appearance_ms": 18200,
                "evidence_ids": cta_ids,
            },
            "creator": {
                "persona": "home_organizer",
                "delivery_style": "authentic_review",
                "evidence_ids": hook_ids,
            },
            "platform": {
                "tiktok_native_signals": ["native vertical framing", "shop CTA"],
                "shop_signals": ["product_tag"],
                "evidence_ids": cta_ids,
            },
            "risks": [
                {
                    "code": "MEDIUM_RISK_CLAIM",
                    "severity": "medium",
                    "message": "Unsupported superlative phrasing detected.",
                    "evidence_ids": claim_ids,
                }
            ]
            if claim_ids
            else [],
            "summary": {
                "what_to_keep": ["Problem-first opening", "Before/after proof", "Creator-led demo"],
                "what_to_change": ["Adapt the buyer pain and product specifics to your SKU"],
                "what_not_to_copy": ["Do not copy the exact script or unsupported claims"],
                "test_hypotheses": [
                    "Test whether a visible space-saving transformation improves saves and clicks."
                ],
            },
        }
        return self._repository.create(
            workspace_id=workspace_id,
            reference_id=reference_id,
            asset_version_id=asset_version_id,
            dna_json=dna_json,
            confidence=confidence,
            analysis_mode=analysis_mode,
            taxonomy_version=CREATIVE_DNA_TAXONOMY_VERSION,
            model_version="fixture_creative_dna_v1" if analysis_mode == "fixture" else None,
            prompt_version=CREATIVE_DNA_PROMPT_VERSION,
        )


def _evidence_by_type(evidence: list[EvidenceItemModel]) -> dict[str, list[EvidenceItemModel]]:
    grouped: dict[str, list[EvidenceItemModel]] = {}
    for item in evidence:
        grouped.setdefault(item.evidence_type, []).append(item)
    return grouped


def _ids(grouped: dict[str, list[EvidenceItemModel]], evidence_type: str) -> list[str]:
    return [str(item.id) for item in grouped.get(evidence_type, [])]


def _first_value(
    grouped: dict[str, list[EvidenceItemModel]],
    evidence_type: str,
    key: str,
    default: int,
) -> int:
    items = grouped.get(evidence_type, [])
    if not items:
        return default
    value = items[0].value_json.get(key)
    return int(value) if isinstance(value, int | float) else default
