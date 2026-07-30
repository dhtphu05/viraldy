from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from viraldy.modules.media_analysis.contracts import MediaObservationBundleV1
from viraldy.modules.media_analysis.evidence_bundle import (
    EvidenceBundleResponse,
    EvidenceTimelineItem,
    build_evidence_bundle,
)
from viraldy.modules.media_analysis.evidence_contracts import validate_evidence_value_v1
from viraldy.modules.media_analysis.models import EvidenceItemModel
from viraldy.modules.media_analysis.repository import MediaAnalysisRepository
from viraldy.shared.errors.base import AppError


def get_media_observation_bundle(artifacts: list[Any]) -> MediaObservationBundleV1 | None:
    for artifact in artifacts:
        artifact_type = getattr(artifact, "artifact_type", None)
        payload = getattr(artifact, "payload_json", None)
        if artifact_type == "visual_observations" and isinstance(payload, dict):
            return MediaObservationBundleV1.model_validate(payload)
    return None


def validate_evidence_refs(evidence_ids: list[UUID], allowed_evidence_ids: set[UUID]) -> None:
    unknown = [
        evidence_id for evidence_id in evidence_ids if evidence_id not in allowed_evidence_ids
    ]
    if unknown:
        raise AppError(
            "EVIDENCE_REFERENCE_INVALID",
            "Payload references evidence IDs outside the current evidence bundle.",
        )


class EvidenceQueries:
    def __init__(self, session: AsyncSession) -> None:
        self._repository = MediaAnalysisRepository(session)

    async def list_for_asset_version(
        self,
        workspace_id: UUID,
        asset_version_id: UUID,
    ) -> list[EvidenceItemModel]:
        return await self._repository.list_evidence(workspace_id, asset_version_id)


__all__ = [
    "EvidenceQueries",
    "EvidenceBundleResponse",
    "EvidenceItemModel",
    "EvidenceTimelineItem",
    "MediaObservationBundleV1",
    "build_evidence_bundle",
    "get_media_observation_bundle",
    "validate_evidence_refs",
    "validate_evidence_value_v1",
]
