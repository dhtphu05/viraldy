from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from viraldy.modules.creative_domain.schema_versions import EVIDENCE_SCHEMA_VERSION
from viraldy.modules.media_analysis.evidence_bundle import validate_evidence_payload
from viraldy.modules.media_analysis.models import EvidenceItemModel, MediaArtifactModel


class MediaAnalysisRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_artifacts(
        self, workspace_id: UUID, asset_version_id: UUID
    ) -> list[MediaArtifactModel]:
        result = await self._session.execute(
            select(MediaArtifactModel)
            .where(
                MediaArtifactModel.workspace_id == workspace_id,
                MediaArtifactModel.asset_version_id == asset_version_id,
            )
            .order_by(MediaArtifactModel.created_at.asc())
        )
        return list(result.scalars())

    async def list_evidence(
        self, workspace_id: UUID, asset_version_id: UUID
    ) -> list[EvidenceItemModel]:
        result = await self._session.execute(
            select(EvidenceItemModel)
            .where(
                EvidenceItemModel.workspace_id == workspace_id,
                EvidenceItemModel.asset_version_id == asset_version_id,
            )
            .order_by(
                EvidenceItemModel.start_ms.asc().nulls_last(), EvidenceItemModel.created_at.asc()
            )
        )
        return list(result.scalars())


class SyncMediaAnalysisRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_reusable_evidence(
        self,
        workspace_id: UUID,
        asset_version_id: UUID,
        provider: str,
        model_version: str | None,
        pipeline_version: str,
        analysis_request_hash: str | None = None,
    ) -> list[EvidenceItemModel]:
        filters = [
            EvidenceItemModel.workspace_id == workspace_id,
            EvidenceItemModel.asset_version_id == asset_version_id,
            EvidenceItemModel.provider == provider,
            EvidenceItemModel.model_version == model_version,
            EvidenceItemModel.pipeline_version == pipeline_version,
            EvidenceItemModel.evidence_schema_version == EVIDENCE_SCHEMA_VERSION,
        ]
        if analysis_request_hash is not None:
            filters.append(EvidenceItemModel.analysis_request_hash == analysis_request_hash)
        return list(
            self._session.execute(
                select(EvidenceItemModel)
                .where(*filters)
                .order_by(
                    EvidenceItemModel.start_ms.asc().nulls_last(),
                    EvidenceItemModel.created_at.asc(),
                )
            ).scalars()
        )

    def get_reusable_observation_inputs(
        self,
        workspace_id: UUID,
        asset_version_id: UUID,
        provider: str,
        model_version: str | None,
        pipeline_version: str,
    ) -> tuple[dict[str, object], dict[str, object]] | None:
        rows = self._session.execute(
            select(MediaArtifactModel.artifact_type, MediaArtifactModel.payload_json).where(
                MediaArtifactModel.workspace_id == workspace_id,
                MediaArtifactModel.asset_version_id == asset_version_id,
                MediaArtifactModel.provider == provider,
                MediaArtifactModel.model_version == model_version,
                MediaArtifactModel.pipeline_version == pipeline_version,
                MediaArtifactModel.artifact_type.in_(("transcript", "ocr")),
            )
        ).all()
        payloads = {
            artifact_type: payload for artifact_type, payload in rows if isinstance(payload, dict)
        }
        transcript = payloads.get("transcript")
        ocr = payloads.get("ocr")
        if transcript is None or ocr is None:
            return None
        return transcript, ocr

    def replace_artifacts_and_evidence(
        self,
        workspace_id: UUID,
        asset_version_id: UUID,
        processing_job_id: UUID | None,
        pipeline_version: str,
        artifacts: list[dict[str, Any]],
        evidence: list[dict[str, Any]],
    ) -> list[EvidenceItemModel]:
        self._session.execute(
            delete(MediaArtifactModel).where(
                MediaArtifactModel.workspace_id == workspace_id,
                MediaArtifactModel.asset_version_id == asset_version_id,
            )
        )
        self._session.execute(
            delete(EvidenceItemModel).where(
                EvidenceItemModel.workspace_id == workspace_id,
                EvidenceItemModel.asset_version_id == asset_version_id,
            )
        )
        artifact_models = [
            MediaArtifactModel(
                workspace_id=workspace_id,
                asset_version_id=asset_version_id,
                processing_job_id=processing_job_id,
                stage=item.get("stage"),
                ordinal=item.get("ordinal"),
                artifact_type=item["artifact_type"],
                storage_key=item.get("storage_key"),
                sha256=item.get("sha256"),
                payload_json=item.get("payload_json"),
                provider=item["provider"],
                model_version=item.get("model_version"),
                analysis_mode=item["analysis_mode"],
                pipeline_version=pipeline_version,
            )
            for item in artifacts
        ]
        evidence_models = [
            EvidenceItemModel(
                workspace_id=workspace_id,
                asset_version_id=asset_version_id,
                processing_job_id=processing_job_id,
                stage=item.get("stage"),
                analysis_run_type=item["analysis_run_type"],
                analysis_run_id=item.get("analysis_run_id"),
                evidence_type=item["evidence_type"],
                evidence_schema_version=item.get(
                    "evidence_schema_version", EVIDENCE_SCHEMA_VERSION
                ),
                observation_id=item.get("observation_id"),
                identity_hash=item.get("identity_hash"),
                analysis_request_hash=item.get("analysis_request_hash"),
                start_ms=item.get("start_ms"),
                end_ms=item.get("end_ms"),
                frame_storage_key=item.get("frame_storage_key"),
                value_json=item["value_json"],
                confidence=Decimal(str(item["confidence"]))
                if item.get("confidence") is not None
                else None,
                source=item["source"],
                provider=item.get("provider"),
                model_version=item.get("model_version"),
                pipeline_version=pipeline_version,
            )
            for item in _validated_evidence(asset_version_id, evidence)
        ]
        self._session.add_all([*artifact_models, *evidence_models])
        self._session.flush()
        return evidence_models

    def list_evidence(self, workspace_id: UUID, asset_version_id: UUID) -> list[EvidenceItemModel]:
        return list(
            self._session.execute(
                select(EvidenceItemModel)
                .where(
                    EvidenceItemModel.workspace_id == workspace_id,
                    EvidenceItemModel.asset_version_id == asset_version_id,
                )
                .order_by(
                    EvidenceItemModel.start_ms.asc().nulls_last(),
                    EvidenceItemModel.created_at.asc(),
                )
            ).scalars()
        )


def _validated_evidence(
    asset_version_id: UUID, evidence: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    for item in evidence:
        validate_evidence_payload(asset_version_id, item)
    return evidence
