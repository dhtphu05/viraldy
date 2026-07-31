from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from viraldy.modules.adaptations.contracts import AdaptationConceptV2, AdaptationOutputV2
from viraldy.modules.adaptations.public import AdaptationRepository
from viraldy.modules.ai_gateway.public import (
    CAMPAIGN_PACK_PROMPT_NAME,
    CAMPAIGN_PACK_PROMPT_VERSION,
    AiModelRunModel,
    AiModelRunRepository,
)
from viraldy.modules.campaign_packs.brief_builder import (
    build_adaptation_campaign_pack_brief,
)
from viraldy.modules.campaign_packs.contracts import CampaignPackBriefV1
from viraldy.modules.campaign_packs.exporter import build_campaign_pack_export
from viraldy.modules.campaign_packs.models import CampaignPackModel, CampaignPackVersionModel
from viraldy.modules.campaign_packs.provider import (
    CampaignPackGenerationProvider,
    CampaignPackProviderExecution,
    stable_json_hash,
)
from viraldy.modules.campaign_packs.repository import CampaignPackRepository
from viraldy.modules.campaign_packs.requirements import (
    compile_campaign_requirements,
    compiled_requirements_to_json,
)
from viraldy.modules.campaign_packs.schemas import (
    CampaignPackExportResponse,
    CampaignPackResponse,
    CampaignPackVersionResponse,
    CreateCampaignPackRequest,
    CreateCampaignPackVersionRequest,
    ExportCampaignPackRequest,
    UpdateCampaignPackRequest,
)
from viraldy.modules.creative_domain.schema_versions import (
    CAMPAIGN_PACK_SCHEMA_VERSION,
    COMPILED_REQUIREMENTS_SCHEMA_VERSION,
)
from viraldy.modules.product_events.public import ProductEventPublisher
from viraldy.modules.products.contracts import ProductContextV1
from viraldy.modules.products.public import ProductContextSnapshot, ProductQueries
from viraldy.platform.config.settings import Settings
from viraldy.shared.errors.base import AppError, NotFoundError

_brief_from_concept = build_adaptation_campaign_pack_brief


class CampaignPackService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings
        self._repository = CampaignPackRepository(session)
        self._adaptations = AdaptationRepository(session)
        self._products = ProductQueries(session)
        self._model_runs = AiModelRunRepository(session)
        self._provider = CampaignPackGenerationProvider(settings)

    async def create(
        self,
        workspace_id: UUID,
        user_id: UUID,
        data: CreateCampaignPackRequest,
    ) -> CampaignPackResponse:
        adaptation = await self._adaptations.get(workspace_id, data.adaptation_run_id)
        if adaptation is None:
            raise NotFoundError("ADAPTATION_NOT_FOUND", "Adaptation run was not found.")
        if adaptation.status != "completed":
            raise AppError(
                "ADAPTATION_NOT_COMPLETED",
                "Campaign Pack generation requires a completed adaptation.",
                status_code=409,
            )
        product = await self._load_current_product(workspace_id, adaptation.product_id)
        _validate_adaptation_product_snapshot(adaptation.product_snapshot_json, product)
        concept = _selected_adaptation_concept(adaptation.result_json, data.concept_id)
        _validate_source_concept(
            product.product_context,
            adaptation.target_buyer_json,
            concept,
        )
        deterministic_brief = _brief_from_concept(
            adaptation.objective,
            adaptation.target_market,
            adaptation.target_buyer_json,
            adaptation.product_snapshot_json,
            concept.model_dump(mode="json"),
            adaptation.id,
            data.concept_id,
        )
        input_summary: dict[str, object] = {
            "adaptation_run_id": str(adaptation.id),
            "concept_id": concept.id,
            "objective": adaptation.objective,
            "product_context_version": product.product_context_version,
            "product_id": str(product.product_id),
            "target_market": adaptation.target_market,
        }
        model_run = await self._create_model_run(
            workspace_id=workspace_id,
            adaptation_run_id=adaptation.id,
            input_summary=input_summary,
        )
        provider_execution: CampaignPackProviderExecution | None = None
        try:
            brief = deterministic_brief
            if self._settings.ai_mode != "fixture":
                provider_execution = self._provider.generate_with_metadata(
                    workspace_id=workspace_id,
                    actor_user_id=user_id,
                    model_run_id=model_run.id,
                    product_id=product.product_id,
                    product_context=product.product_context,
                    product_context_version=product.product_context_version,
                    adaptation_run_id=adaptation.id,
                    selected_concept=concept,
                    objective=adaptation.objective,
                    target_market=adaptation.target_market,
                    target_buyer=adaptation.target_buyer_json,
                    adaptation_constraints=adaptation.constraints_json,
                    deterministic_baseline=deterministic_brief,
                )
                brief = provider_execution.output
            compiled = compile_campaign_requirements(brief.model_dump(mode="json"))
            pack, version = await self._repository.create(
                workspace_id=workspace_id,
                user_id=user_id,
                product_id=adaptation.product_id,
                adaptation_run_id=adaptation.id,
                brief_json=brief.model_dump(mode="json"),
                source_model_run_id=model_run.id,
                source_prompt_version=CAMPAIGN_PACK_PROMPT_VERSION,
                source_schema_version=CAMPAIGN_PACK_SCHEMA_VERSION,
                product_snapshot_json=brief.product_snapshot.model_dump(mode="json"),
                compiled_requirements_json=compiled_requirements_to_json(compiled),
                requirements_schema_version=COMPILED_REQUIREMENTS_SCHEMA_VERSION,
            )
            await self._complete_model_run(
                model_run,
                brief,
                provider_execution,
            )
        except AppError as exc:
            await _fail_model_run(self._model_runs, model_run, exc)
            await self._session.commit()
            raise
        await self._session.commit()
        await self._session.refresh(pack)
        await self._session.refresh(version)
        return _pack_response(pack, version)

    async def _load_current_product(
        self,
        workspace_id: UUID,
        product_id: UUID,
    ) -> ProductContextSnapshot:
        product = await self._products.get_product_context_snapshot(
            workspace_id,
            product_id,
        )
        if product is None:
            raise NotFoundError("PRODUCT_NOT_FOUND", "Product was not found.")
        return product

    async def _create_model_run(
        self,
        *,
        workspace_id: UUID,
        adaptation_run_id: UUID,
        input_summary: dict[str, object],
    ) -> AiModelRunModel:
        input_hash = stable_json_hash(input_summary)
        return await self._model_runs.create_running(
            workspace_id=workspace_id,
            processing_job_id=None,
            subject_type="adaptation_concept",
            subject_id=adaptation_run_id,
            capability="campaign_pack_generate",
            operation="campaign_pack_generate",
            analysis_mode=self._settings.ai_mode,
            provider=_provider_name(self._settings),
            model=_model_name(self._settings),
            prompt_version=CAMPAIGN_PACK_PROMPT_VERSION,
            response_schema_version=CAMPAIGN_PACK_SCHEMA_VERSION,
            schema_version=CAMPAIGN_PACK_SCHEMA_VERSION,
            request_hash=input_hash,
            input_hash=input_hash,
            input_summary=input_summary,
            endpoint_family=_endpoint_family(self._settings),
            prompt_name=CAMPAIGN_PACK_PROMPT_NAME,
            attempt_count=1,
            repair_attempt_count=0,
        )

    async def _complete_model_run(
        self,
        model_run: AiModelRunModel,
        brief: CampaignPackBriefV1,
        execution: CampaignPackProviderExecution | None,
    ) -> None:
        output_summary: dict[str, object] = {
            "hook_count": len(brief.hooks),
            "must_show_count": len(brief.must_show),
            "script_beat_count": len(brief.script_beats),
            "source_adaptation_run_id": (
                str(brief.source_adaptation_run_id) if brief.source_adaptation_run_id else None
            ),
            "source_concept_id": brief.source_concept_id,
        }
        if execution is None:
            output_summary["execution_mode"] = "deterministic_fixture"
            await self._model_runs.complete(
                model_run,
                output_summary,
                http_status=None,
                provider_request_id=None,
                latency_ms=None,
                usage_json={"fixture": True},
                repair_attempt_count=0,
            )
            return
        await self._model_runs.complete(
            model_run,
            {**output_summary, "execution_mode": "provider_structured_output"},
            http_status=execution.http_status,
            provider_request_id=execution.provider_request_id,
            latency_ms=execution.latency_ms,
            usage_json=execution.usage_json,
            repair_attempt_count=execution.repair_attempt_count,
        )

    async def list_packs(self, workspace_id: UUID) -> list[CampaignPackResponse]:
        packs = await self._repository.list(workspace_id)
        responses = []
        for pack in packs:
            version = (
                await self._repository.get_version(pack.current_version_id)
                if pack.current_version_id
                else None
            )
            responses.append(_pack_response(pack, version))
        return responses

    async def get(self, workspace_id: UUID, pack_id: UUID) -> CampaignPackResponse:
        pack = await self._repository.get(workspace_id, pack_id)
        if pack is None:
            raise NotFoundError("CAMPAIGN_PACK_NOT_FOUND", "Campaign Pack was not found.")
        version = (
            await self._repository.get_version(pack.current_version_id)
            if pack.current_version_id
            else None
        )
        return _pack_response(pack, version)

    async def update(
        self,
        workspace_id: UUID,
        pack_id: UUID,
        data: UpdateCampaignPackRequest,
    ) -> CampaignPackResponse:
        pack = await self._repository.get(workspace_id, pack_id)
        if pack is None:
            raise NotFoundError("CAMPAIGN_PACK_NOT_FOUND", "Campaign Pack was not found.")
        if data.status is not None:
            pack.status = data.status
        await self._session.commit()
        await self._session.refresh(pack)
        version = (
            await self._repository.get_version(pack.current_version_id)
            if pack.current_version_id
            else None
        )
        return _pack_response(pack, version)

    async def create_version(
        self,
        workspace_id: UUID,
        pack_id: UUID,
        user_id: UUID,
        data: CreateCampaignPackVersionRequest,
    ) -> CampaignPackVersionResponse:
        pack = await self._repository.get(workspace_id, pack_id)
        if pack is None:
            raise NotFoundError("CAMPAIGN_PACK_NOT_FOUND", "Campaign Pack was not found.")
        brief = data.brief
        compiled = compile_campaign_requirements(brief.model_dump(mode="json"))
        version = await self._repository.create_version(
            pack,
            user_id,
            brief.model_dump(mode="json"),
            data.change_note,
            brief.product_snapshot.model_dump(mode="json"),
            compiled_requirements_to_json(compiled),
            COMPILED_REQUIREMENTS_SCHEMA_VERSION,
        )
        await self._session.commit()
        await self._session.refresh(version)
        return CampaignPackVersionResponse.model_validate(version)

    async def list_versions(
        self, workspace_id: UUID, pack_id: UUID
    ) -> list[CampaignPackVersionResponse]:
        pack = await self._repository.get(workspace_id, pack_id)
        if pack is None:
            raise NotFoundError("CAMPAIGN_PACK_NOT_FOUND", "Campaign Pack was not found.")
        versions = await self._repository.list_versions(pack_id)
        return [CampaignPackVersionResponse.model_validate(version) for version in versions]

    async def export(
        self,
        workspace_id: UUID,
        pack_id: UUID,
        user_id: UUID,
        data: ExportCampaignPackRequest,
    ) -> CampaignPackExportResponse:
        pack = await self._repository.get(workspace_id, pack_id)
        if pack is None:
            raise NotFoundError("CAMPAIGN_PACK_NOT_FOUND", "Campaign Pack was not found.")
        version = (
            await self._repository.get_version(pack.current_version_id)
            if pack.current_version_id
            else None
        )
        if version is None:
            raise AppError(
                "CAMPAIGN_PACK_VERSION_NOT_FOUND",
                "Campaign Pack has no current version to export.",
            )
        version_response = CampaignPackVersionResponse.model_validate(version)
        export = build_campaign_pack_export(version_response, data.format)
        await ProductEventPublisher(self._session).record(
            event_type="campaign_pack_exported",
            workspace_id=workspace_id,
            actor_user_id=user_id,
            subject_type="campaign_pack",
            subject_id=pack.id,
            payload_json={
                "campaign_pack_version_id": str(version.id),
                "version_number": version.version_number,
                "format": data.format,
                "filename": export.filename,
            },
        )
        await self._session.commit()
        return export


def _pack_response(
    pack: CampaignPackModel,
    version: CampaignPackVersionModel | None,
) -> CampaignPackResponse:
    return CampaignPackResponse.model_validate(
        {
            "id": pack.id,
            "workspace_id": pack.workspace_id,
            "product_id": pack.product_id,
            "adaptation_run_id": pack.adaptation_run_id,
            "status": pack.status,
            "current_version_id": pack.current_version_id,
            "created_at": pack.created_at,
            "updated_at": pack.updated_at,
            "current_version": CampaignPackVersionResponse.model_validate(version)
            if version
            else None,
        }
    )


def _selected_adaptation_concept(
    result_json: dict[str, object],
    concept_id: str,
) -> AdaptationConceptV2:
    try:
        output = AdaptationOutputV2.model_validate(result_json)
    except Exception as exc:
        raise AppError(
            "ADAPTATION_OUTPUT_INVALID",
            "Campaign Pack generation requires valid AdaptationOutputV2 provenance.",
        ) from exc
    for concept in output.concepts:
        if concept.id == concept_id:
            return concept
    raise NotFoundError(
        "ADAPTATION_CONCEPT_NOT_FOUND",
        "Adaptation concept was not found.",
    )


def _validate_adaptation_product_snapshot(
    product_snapshot_json: dict[str, object] | None,
    current_product: ProductContextSnapshot,
) -> None:
    if not product_snapshot_json:
        raise AppError(
            "PRODUCT_CONTEXT_SNAPSHOT_REQUIRED",
            "Campaign Pack generation requires the adaptation product snapshot.",
        )
    try:
        adaptation_snapshot = ProductContextV1.model_validate(product_snapshot_json)
    except Exception as exc:
        raise AppError(
            "PRODUCT_CONTEXT_SNAPSHOT_INVALID",
            "Campaign Pack generation requires a valid product snapshot.",
        ) from exc
    if adaptation_snapshot != current_product.product_context:
        raise AppError(
            "CAMPAIGN_PACK_PRODUCT_SNAPSHOT_STALE",
            "The product changed after adaptation. Regenerate the adaptation first.",
            status_code=409,
            details={
                "current_product_context_version": current_product.product_context_version,
            },
        )


def _validate_source_concept(
    product: ProductContextV1,
    target_buyer: dict[str, object],
    concept: AdaptationConceptV2,
) -> None:
    if concept.buyer_persona_label.casefold() == concept.creator_persona.casefold():
        raise AppError(
            "CAMPAIGN_PACK_PERSONA_COLLISION",
            "Buyer and creator personas must remain separate.",
        )
    target_persona_id = str(target_buyer.get("persona_id") or "").strip()
    if target_persona_id and concept.buyer_persona_id != target_persona_id:
        raise AppError(
            "CAMPAIGN_PACK_BUYER_MISMATCH",
            "The selected concept does not match the adaptation buyer.",
        )
    product_persona_ids = {persona.id for persona in product.personas}
    if (
        concept.buyer_persona_id
        and product_persona_ids
        and concept.buyer_persona_id not in product_persona_ids
    ):
        raise AppError(
            "CAMPAIGN_PACK_BUYER_MISMATCH",
            "The selected concept buyer is not present in Product Context.",
        )
    if product.creative.creator_personas and concept.creator_persona not in (
        product.creative.creator_personas
    ):
        raise AppError(
            "CAMPAIGN_PACK_CREATOR_MISMATCH",
            "The selected concept creator is not present in Product Context.",
        )


def _provider_name(settings: Settings) -> str:
    return "fixture" if settings.ai_mode == "fixture" else settings.ai_provider


def _model_name(settings: Settings) -> str:
    if settings.ai_mode == "fixture":
        return "fixture_campaign_pack_v1"
    if settings.ai_provider == "openai":
        return settings.resolve_openai_model("campaign_pack_generate")
    return settings.ai_text_model or "unconfigured"


def _endpoint_family(settings: Settings) -> str | None:
    if settings.ai_mode == "fixture":
        return None
    return "responses" if settings.ai_provider == "openai" else "chat_completions"


async def _fail_model_run(
    repository: AiModelRunRepository,
    model_run: AiModelRunModel,
    error: AppError,
) -> None:
    http_status = error.details.get("http_status")
    provider_request_id = error.details.get("provider_request_id")
    repair_attempt_count = error.details.get("repair_attempt_count")
    await repository.fail(
        model_run,
        error.code,
        error.message,
        http_status=http_status if isinstance(http_status, int) else None,
        safe_error_message=error.message,
        provider_request_id=(provider_request_id if isinstance(provider_request_id, str) else None),
        repair_attempt_count=(
            repair_attempt_count if isinstance(repair_attempt_count, int) else None
        ),
    )
