from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from viraldy.modules.generation.contracts import (
    GenerationOperation,
    GenerationProviderResultV1,
)
from viraldy.modules.generation.models import GenerationArtifactModel, GenerationRunModel
from viraldy.modules.viral_kits.public import GenerationBriefV1
from viraldy.platform.clock.utc import utc_now


class GenerationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_queued(
        self,
        *,
        workspace_id: UUID,
        viral_kit_id: UUID,
        viral_kit_version_id: UUID,
        viral_kit_version: int,
        concept_id: str,
        operation: GenerationOperation,
        prompt_version: str,
        schema_version: str,
        brief: GenerationBriefV1,
        source_asset_ids: list[UUID],
        input_hash: str,
        idempotency_key: str | None,
        created_by_user_id: UUID,
    ) -> GenerationRunModel:
        run = GenerationRunModel(
            workspace_id=workspace_id,
            viral_kit_id=viral_kit_id,
            viral_kit_version_id=viral_kit_version_id,
            viral_kit_version=viral_kit_version,
            concept_id=concept_id,
            operation=operation.value,
            status="queued",
            prompt_version=prompt_version,
            schema_version=schema_version,
            generation_brief_json=brief.model_dump(mode="json"),
            source_asset_ids_json=[str(asset_id) for asset_id in source_asset_ids],
            input_hash=input_hash,
            idempotency_key=idempotency_key,
            created_by_user_id=created_by_user_id,
        )
        self._session.add(run)
        await self._session.flush()
        return run

    async def get(self, workspace_id: UUID, run_id: UUID) -> GenerationRunModel | None:
        result = await self._session.execute(
            select(GenerationRunModel).where(
                GenerationRunModel.workspace_id == workspace_id,
                GenerationRunModel.id == run_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_idempotent(
        self,
        workspace_id: UUID,
        operation: GenerationOperation,
        idempotency_key: str | None,
    ) -> GenerationRunModel | None:
        if not idempotency_key:
            return None
        result = await self._session.execute(
            select(GenerationRunModel).where(
                GenerationRunModel.workspace_id == workspace_id,
                GenerationRunModel.operation == operation.value,
                GenerationRunModel.idempotency_key == idempotency_key,
            )
        )
        return result.scalar_one_or_none()

    async def list_artifacts(
        self,
        workspace_id: UUID,
        run_id: UUID,
    ) -> list[GenerationArtifactModel]:
        result = await self._session.execute(
            select(GenerationArtifactModel)
            .where(
                GenerationArtifactModel.workspace_id == workspace_id,
                GenerationArtifactModel.generation_run_id == run_id,
            )
            .order_by(GenerationArtifactModel.created_at, GenerationArtifactModel.id)
        )
        return list(result.scalars())

    async def attach_job(self, run: GenerationRunModel, processing_job_id: UUID) -> None:
        run.processing_job_id = processing_job_id
        await self._session.flush()


class SyncGenerationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, workspace_id: UUID, run_id: UUID) -> GenerationRunModel | None:
        return self._session.execute(
            select(GenerationRunModel).where(
                GenerationRunModel.workspace_id == workspace_id,
                GenerationRunModel.id == run_id,
            )
        ).scalar_one_or_none()

    def mark_running(self, run: GenerationRunModel, model_run_id: UUID) -> None:
        run.status = "running"
        run.model_run_id = model_run_id
        run.started_at = utc_now()
        run.safe_error_code = None
        run.safe_error_message = None
        self._session.flush()

    def replace_artifacts(
        self,
        run: GenerationRunModel,
        model_run_id: UUID,
        result: GenerationProviderResultV1,
    ) -> list[GenerationArtifactModel]:
        self._session.execute(
            delete(GenerationArtifactModel).where(
                GenerationArtifactModel.generation_run_id == run.id
            )
        )
        artifacts = [
            GenerationArtifactModel(
                workspace_id=run.workspace_id,
                generation_run_id=run.id,
                model_run_id=model_run_id,
                provider_artifact_id=artifact.id,
                artifact_kind=artifact.artifact_kind,
                scene_id=artifact.scene_id,
                storage_key=artifact.storage_key,
                media_type=artifact.media_type,
                width=artifact.width,
                height=artifact.height,
                duration_ms=artifact.duration_ms,
                payload_json=artifact.payload_json,
                provider=result.provider,
                model=result.model,
                provider_request_id=result.provider_request_id,
            )
            for artifact in result.artifacts
        ]
        self._session.add_all(artifacts)
        self._session.flush()
        return artifacts

    def mark_succeeded(
        self,
        run: GenerationRunModel,
        output_json: dict[str, object],
    ) -> None:
        run.status = "succeeded"
        run.output_json = output_json
        run.completed_at = utc_now()
        self._session.flush()

    def mark_failed(self, run: GenerationRunModel, code: str, message: str) -> None:
        run.status = "failed"
        run.safe_error_code = code
        run.safe_error_message = message
        run.completed_at = utc_now()
        self._session.flush()
