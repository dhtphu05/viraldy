from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from viraldy.modules.ai_gateway.public import (
    SyncAiModelRunRepository,
    get_ai_operation_definition,
)
from viraldy.modules.assets.public import AssetRepository
from viraldy.modules.generation.contracts import (
    GenerationOperation,
    GenerationProviderResultV1,
)
from viraldy.modules.generation.models import GenerationRunModel
from viraldy.modules.generation.provider import generation_provider
from viraldy.modules.generation.repository import (
    GenerationRepository,
    SyncGenerationRepository,
)
from viraldy.modules.generation.schemas import (
    CreateGenerationRequest,
    CreateGenerationResponse,
    GenerationArtifactResponse,
    GenerationRunResponse,
)
from viraldy.modules.jobs.public import (
    JobType,
    get_existing_idempotent_job,
    request_mvp_job,
)
from viraldy.modules.viral_kits.public import (
    GenerationBriefV1,
    ViralKitQueries,
)
from viraldy.platform.config.settings import Settings
from viraldy.shared.errors.base import AppError, NotFoundError


class GenerationService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings
        self._repository = GenerationRepository(session)
        self._assets = AssetRepository(session)
        self._viral_kits = ViralKitQueries(session)

    async def create(
        self,
        *,
        workspace_id: UUID,
        user_id: UUID,
        operation: GenerationOperation,
        data: CreateGenerationRequest,
        idempotency_key: str | None,
    ) -> CreateGenerationResponse:
        ensure_generation_enabled(self._settings, operation)
        job_type = _job_type(operation)
        existing_job = await get_existing_idempotent_job(
            self._session,
            workspace_id,
            job_type.value,
            idempotency_key,
        )
        if existing_job is not None:
            existing_run = await self._repository.get(workspace_id, existing_job.subject_id)
            if existing_run is None:
                raise AppError(
                    "IDEMPOTENT_GENERATION_RUN_NOT_FOUND",
                    "Existing idempotent generation run was not found.",
                )
            return CreateGenerationResponse(
                generation_run=await self._response(existing_run),
                job=existing_job,
            )

        snapshot = await self._viral_kits.get_version_snapshot(
            workspace_id,
            data.viral_kit_id,
            data.viral_kit_version,
        )
        if not any(concept.id == data.concept_id for concept in snapshot.viral_kit.concepts):
            raise NotFoundError("VIRAL_KIT_CONCEPT_NOT_FOUND", "ViralKit concept was not found.")
        brief = select_generation_brief(
            snapshot.viral_kit.generation_briefs,
            data.concept_id,
            operation,
        )
        ensure_generation_rights(brief, data.rights_confirmed)
        source_asset_ids = _unique_asset_ids(
            data.source_asset_ids,
            brief.product_asset_ids,
            brief.reference_asset_ids,
            [asset_id for scene in brief.scenes for asset_id in scene.reference_asset_ids],
        )
        await self._validate_assets(workspace_id, source_asset_ids)
        definition = get_ai_operation_definition(operation.value)
        input_hash = _input_hash(
            snapshot.viral_kit_version_id,
            data.concept_id,
            operation,
            brief,
            source_asset_ids,
        )
        try:
            run = await self._repository.create_queued(
                workspace_id=workspace_id,
                viral_kit_id=snapshot.viral_kit_id,
                viral_kit_version_id=snapshot.viral_kit_version_id,
                viral_kit_version=snapshot.version,
                concept_id=data.concept_id,
                operation=operation,
                prompt_version=definition.prompt_version,
                schema_version=definition.schema_version,
                brief=brief,
                source_asset_ids=source_asset_ids,
                input_hash=input_hash,
                idempotency_key=idempotency_key,
                created_by_user_id=user_id,
            )
        except IntegrityError:
            await self._session.rollback()
            return await self._resolve_concurrent_idempotent(
                workspace_id,
                operation,
                job_type,
                idempotency_key,
            )
        job = await request_mvp_job(
            self._session,
            workspace_id,
            "generation_run",
            run.id,
            job_type.value,
            {"generation_run_id": str(run.id)},
            idempotency_key,
        )
        await self._repository.attach_job(run, job.id)
        await self._session.commit()
        await self._session.refresh(run)
        return CreateGenerationResponse(
            generation_run=await self._response(run),
            job=job,
        )

    async def get(self, workspace_id: UUID, run_id: UUID) -> GenerationRunResponse:
        run = await self._repository.get(workspace_id, run_id)
        if run is None:
            raise NotFoundError("GENERATION_RUN_NOT_FOUND", "Generation run was not found.")
        return await self._response(run)

    async def _resolve_concurrent_idempotent(
        self,
        workspace_id: UUID,
        operation: GenerationOperation,
        job_type: JobType,
        idempotency_key: str | None,
    ) -> CreateGenerationResponse:
        run = await self._repository.get_idempotent(
            workspace_id,
            operation,
            idempotency_key,
        )
        job = await get_existing_idempotent_job(
            self._session,
            workspace_id,
            job_type.value,
            idempotency_key,
        )
        if run is None or job is None or job.subject_id != run.id:
            raise AppError(
                "GENERATION_IDEMPOTENCY_CONFLICT",
                "Concurrent generation request could not be resolved safely.",
                status_code=409,
            )
        return CreateGenerationResponse(
            generation_run=await self._response(run),
            job=job,
        )

    async def _validate_assets(self, workspace_id: UUID, asset_ids: list[UUID]) -> None:
        for asset_id in asset_ids:
            asset = await self._assets.get(workspace_id, asset_id)
            if asset is None:
                raise NotFoundError(
                    "GENERATION_SOURCE_ASSET_NOT_FOUND",
                    "A generation source asset was not found.",
                )
            if asset.status not in {"uploaded", "ready"}:
                raise AppError(
                    "GENERATION_SOURCE_ASSET_NOT_READY",
                    "Every generation source asset must be uploaded and ready.",
                )

    async def _response(self, run: GenerationRunModel) -> GenerationRunResponse:
        artifacts = await self._repository.list_artifacts(run.workspace_id, run.id)
        payload = GenerationRunResponse.model_validate(run)
        return payload.model_copy(
            update={
                "artifacts": [
                    GenerationArtifactResponse.model_validate(artifact) for artifact in artifacts
                ]
            }
        )


def execute_generation_job(
    session: Session,
    workspace_id: UUID,
    generation_run_id: UUID,
    processing_job_id: UUID,
    settings: Settings,
    ensure_active_attempt: Callable[[], None],
) -> dict[str, object]:
    repository = SyncGenerationRepository(session)
    run = repository.get(workspace_id, generation_run_id)
    if run is None:
        raise NotFoundError("GENERATION_RUN_NOT_FOUND", "Generation run was not found.")
    if run.processing_job_id != processing_job_id:
        raise AppError(
            "GENERATION_JOB_BINDING_INVALID",
            "Generation run is not bound to this processing job.",
            status_code=409,
        )
    if run.status == "succeeded":
        return run.output_json or {"generation_run_id": str(run.id), "artifact_count": 0}
    operation = GenerationOperation(run.operation)
    definition = get_ai_operation_definition(operation.value)
    provider = generation_provider(settings, operation)
    model_runs = SyncAiModelRunRepository(session)
    model_run = model_runs.create_running(
        workspace_id=run.workspace_id,
        processing_job_id=processing_job_id,
        subject_type="generation_run",
        subject_id=run.id,
        capability=operation.value,
        operation=operation.value,
        analysis_mode=settings.ai_mode,
        provider=provider.provider,
        model=provider.model,
        prompt_version=definition.prompt_version,
        response_schema_version=definition.schema_version,
        schema_version=definition.schema_version,
        request_hash=run.input_hash,
        input_hash=run.input_hash,
        input_summary={
            "viral_kit_version_id": str(run.viral_kit_version_id),
            "concept_id": run.concept_id,
            "source_asset_count": len(run.source_asset_ids_json),
        },
    )
    repository.mark_running(run, model_run.id)
    brief = GenerationBriefV1.model_validate(run.generation_brief_json)
    try:
        result = provider.generate(
            operation=operation,
            generation_run_id=run.id,
            brief=brief,
        )
        _validate_provider_artifact_kinds(operation, result)
        artifacts = repository.replace_artifacts(run, model_run.id, result)
        output = {
            "generation_run_id": str(run.id),
            "artifact_ids": [str(artifact.id) for artifact in artifacts],
            "artifact_count": len(artifacts),
            "operation": operation.value,
        }
        repository.mark_succeeded(run, output)
        model_run.attempt_count = result.attempt_count
        model_runs.complete(
            model_run,
            result.output_summary,
            200,
            result.provider_request_id,
            result.latency_ms,
            usage_json=result.usage_json,
        )
        return output
    except AppError as exc:
        repository.mark_failed(run, exc.code, exc.message)
        model_runs.fail(
            model_run,
            exc.code,
            exc.message,
            safe_error_message=exc.message,
        )
        ensure_active_attempt()
        session.commit()
        raise


def ensure_generation_enabled(
    settings: Settings,
    operation: GenerationOperation,
) -> None:
    if (
        operation is GenerationOperation.STORYBOARD_IMAGE_GENERATE
        and not settings.image_generation_enabled
    ):
        raise AppError(
            "IMAGE_GENERATION_DISABLED",
            "Storyboard image generation is disabled.",
            status_code=503,
        )
    if (
        operation is GenerationOperation.CONCEPT_VIDEO_PREVIEW_GENERATE
        and not settings.video_generation_enabled
    ):
        raise AppError(
            "VIDEO_GENERATION_DISABLED",
            "Concept video generation is disabled.",
            status_code=503,
        )


def select_generation_brief(
    briefs: list[GenerationBriefV1],
    concept_id: str,
    operation: GenerationOperation,
) -> GenerationBriefV1:
    purpose = (
        "storyboard_preview"
        if operation is GenerationOperation.STORYBOARD_IMAGE_GENERATE
        else "concept_video_preview"
    )
    for brief in briefs:
        if brief.concept_id == concept_id and brief.purpose == purpose:
            return brief
    raise AppError(
        "GENERATION_BRIEF_NOT_FOUND",
        "The selected ViralKit version does not contain the required generation brief.",
    )


def ensure_generation_rights(
    brief: GenerationBriefV1,
    rights_confirmed: bool,
) -> None:
    if brief.rights_confirmation_required and not rights_confirmed:
        raise AppError(
            "GENERATION_RIGHTS_CONFIRMATION_REQUIRED",
            "Source-media generation rights must be confirmed before generation.",
        )


def _validate_provider_artifact_kinds(
    operation: GenerationOperation,
    result: GenerationProviderResultV1,
) -> None:
    expected = (
        "storyboard_image"
        if operation is GenerationOperation.STORYBOARD_IMAGE_GENERATE
        else "concept_video_preview"
    )
    if any(artifact.artifact_kind != expected for artifact in result.artifacts):
        raise AppError(
            "GENERATION_OUTPUT_INVALID",
            "Generation provider returned an artifact for the wrong operation.",
            status_code=502,
        )


def _job_type(operation: GenerationOperation) -> JobType:
    if operation is GenerationOperation.STORYBOARD_IMAGE_GENERATE:
        return JobType.STORYBOARD_GENERATE
    return JobType.CONCEPT_VIDEO_GENERATE


def _unique_asset_ids(*groups: list[UUID]) -> list[UUID]:
    seen: set[UUID] = set()
    values: list[UUID] = []
    for group in groups:
        for asset_id in group:
            if asset_id not in seen:
                seen.add(asset_id)
                values.append(asset_id)
    return values


def _input_hash(
    viral_kit_version_id: UUID,
    concept_id: str,
    operation: GenerationOperation,
    brief: GenerationBriefV1,
    source_asset_ids: list[UUID],
) -> str:
    payload = {
        "viral_kit_version_id": str(viral_kit_version_id),
        "concept_id": concept_id,
        "operation": operation.value,
        "brief": brief.model_dump(mode="json"),
        "source_asset_ids": [str(asset_id) for asset_id in source_asset_ids],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()
