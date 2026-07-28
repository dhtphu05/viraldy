from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

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

    def replace_artifacts_and_evidence(
        self,
        workspace_id: UUID,
        asset_version_id: UUID,
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
                artifact_type=item["artifact_type"],
                storage_key=item.get("storage_key"),
                payload_json=item.get("payload_json"),
                provider=item["provider"],
                model_version=item.get("model_version"),
                analysis_mode=item["analysis_mode"],
            )
            for item in artifacts
        ]
        evidence_models = [
            EvidenceItemModel(
                workspace_id=workspace_id,
                asset_version_id=asset_version_id,
                analysis_run_type=item["analysis_run_type"],
                analysis_run_id=item.get("analysis_run_id"),
                evidence_type=item["evidence_type"],
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
            )
            for item in evidence
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
