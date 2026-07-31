from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from viraldy.modules.ai_gateway.models import AiModelRunModel
from viraldy.modules.ai_gateway.public import (
    CAMPAIGN_PACK_PROMPT_NAME,
    CAMPAIGN_PACK_PROMPT_VERSION,
    VIRAL_KIT_PROMPT_NAME,
    VIRAL_KIT_PROMPT_VERSION,
    VIRAL_KIT_SCHEMA_VERSION,
    AiModelRunRepository,
    AiOperationName,
    StructuredGenerationResult,
    ViraldyOperationContextV1,
    execute_structured_operation,
    get_prompt_package,
)
from viraldy.modules.campaign_packs.contracts import (
    CampaignAngleV1,
    CampaignAudienceV1,
    CampaignObjectiveV1,
    CampaignPackBriefV1,
    ClaimGuardrailsV1,
    CreatorDirectionV1,
    CtaDirectionV1,
    HookOptionV1,
    MustShowRequirementV1,
    RightsNoteV1,
    ScriptBeatV1,
    StoryboardSceneV1,
)
from viraldy.modules.campaign_packs.public import CampaignPackCreator
from viraldy.modules.feedback.public import FeedbackResponse, FeedbackWriter, FieldFeedbackV1
from viraldy.modules.pattern_kits.public import PatternKitQueries, PatternKitVersionSnapshot
from viraldy.modules.product_events.public import ProductEventPublisher, ProductEventType
from viraldy.modules.products.public import ProductContextSnapshot, ProductQueries
from viraldy.modules.viral_kits.contracts import (
    ViralKitConceptV1,
    ViralKitPatternMatchV1,
    ViralKitV1,
)
from viraldy.modules.viral_kits.matcher import match_patterns
from viraldy.modules.viral_kits.models import ViralKitModel, ViralKitVersionModel
from viraldy.modules.viral_kits.provider import LiveViralKitProvider, build_fixture_viral_kit
from viraldy.modules.viral_kits.repository import ViralKitRepository
from viraldy.modules.viral_kits.schemas import (
    CreateViralKitCampaignPackRequest,
    CreateViralKitFeedbackRequest,
    CreateViralKitRequest,
    CreateViralKitVersionRequest,
    ViralKitCampaignPackResponse,
    ViralKitConceptActionRequest,
    ViralKitConceptActionResponse,
    ViralKitDetailResponse,
    ViralKitSummaryResponse,
    ViralKitVersionResponse,
)
from viraldy.platform.clock.utc import utc_now
from viraldy.platform.config.settings import Settings
from viraldy.shared.errors.base import AppError, ConflictError, NotFoundError


class ViralKitService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings
        self._repository = ViralKitRepository(session)
        self._products = ProductQueries(session)
        self._patterns = PatternKitQueries(session)
        self._feedback = FeedbackWriter(session)
        self._campaign_packs = CampaignPackCreator(session)
        self._events = ProductEventPublisher(session)

    async def create(
        self,
        *,
        workspace_id: UUID,
        user_id: UUID,
        data: CreateViralKitRequest,
    ) -> ViralKitDetailResponse:
        product = await self._load_product(workspace_id, data.product_id)
        _validate_product_version(product, data.expected_product_context_version)
        patterns = await self._load_patterns(workspace_id, data.pattern_kit_version_ids)
        matches = match_patterns(
            product_context=product.product_context,
            patterns=patterns,
            request=data,
        )
        _validate_pattern_matches(matches, data.applicability_override_reason)
        viral_kit_id = uuid4()
        created_at = utc_now()
        model_run = await self._create_model_run(
            workspace_id=workspace_id,
            viral_kit_id=viral_kit_id,
            input_summary=_input_summary(data, product, matches),
        )
        try:
            viral_kit, provider_result = await self._compose(
                viral_kit_id=viral_kit_id,
                workspace_id=workspace_id,
                version=1,
                user_id=user_id,
                created_at=created_at,
                data=data,
                product=product,
                patterns=patterns,
                matches=matches,
                model_run_id=model_run.id,
            )
            _validate_create_viral_kit(viral_kit, viral_kit_id, workspace_id, data, product)
            _validate_viral_kit_business_rules(viral_kit)
            kit, version = await self._repository.create_with_version(
                workspace_id=workspace_id,
                user_id=user_id,
                viral_kit=viral_kit,
            )
            await self._complete_model_run(model_run, viral_kit, provider_result)
            await self._events.record(
                event_type="viral_kit_created",
                workspace_id=workspace_id,
                actor_user_id=user_id,
                subject_type="viral_kit",
                subject_id=kit.id,
                payload_json={
                    "version": version.version,
                    "product_id": str(kit.product_id),
                    "concept_count": len(viral_kit.concepts),
                },
            )
            await self._session.commit()
            return _detail_response(kit, version)
        except AppError as exc:
            await _fail_model_run(self._session, model_run, exc)
            await self._session.commit()
            raise

    async def list_kits(
        self,
        *,
        workspace_id: UUID,
        status: str | None = None,
        product_id: UUID | None = None,
        objective: str | None = None,
        platform: str | None = None,
        target_market: str | None = None,
        created_by: UUID | None = None,
        search: str | None = None,
        limit: int = 100,
    ) -> list[ViralKitSummaryResponse]:
        kits = await self._repository.list_kits(
            workspace_id=workspace_id,
            status=status,
            product_id=product_id,
            objective=objective,
            platform=platform,
            target_market=target_market,
            created_by=created_by,
            search=search,
            limit=limit,
        )
        return [ViralKitSummaryResponse.model_validate(kit) for kit in kits]

    async def get(self, workspace_id: UUID, viral_kit_id: UUID) -> ViralKitDetailResponse:
        kit = await self._get_kit(workspace_id, viral_kit_id)
        version = await self._repository.get_latest_version(workspace_id, viral_kit_id)
        if version is None:
            raise NotFoundError("VIRAL_KIT_VERSION_NOT_FOUND", "ViralKit version was not found.")
        return _detail_response(kit, version)

    async def list_versions(
        self,
        workspace_id: UUID,
        viral_kit_id: UUID,
    ) -> list[ViralKitVersionResponse]:
        await self._get_kit(workspace_id, viral_kit_id)
        versions = await self._repository.list_versions(workspace_id, viral_kit_id)
        return [_version_response(version) for version in versions]

    async def get_version(
        self,
        workspace_id: UUID,
        viral_kit_id: UUID,
        version_number: int,
    ) -> ViralKitVersionResponse:
        await self._get_kit(workspace_id, viral_kit_id)
        version = await self._repository.get_version(workspace_id, viral_kit_id, version_number)
        if version is None:
            raise NotFoundError("VIRAL_KIT_VERSION_NOT_FOUND", "ViralKit version was not found.")
        return _version_response(version)

    async def create_version(
        self,
        *,
        workspace_id: UUID,
        viral_kit_id: UUID,
        user_id: UUID,
        data: CreateViralKitVersionRequest,
    ) -> ViralKitVersionResponse:
        kit = await self._get_kit(workspace_id, viral_kit_id)
        if kit.status == "archived":
            raise AppError("VIRAL_KIT_ARCHIVED", "Archived ViralKits are read-only.")
        latest = await self._repository.get_latest_version(workspace_id, viral_kit_id)
        if latest is None:
            raise NotFoundError("VIRAL_KIT_VERSION_NOT_FOUND", "ViralKit version was not found.")
        latest_viral_kit = _viral_kit_from_version(latest)
        new_version_number = kit.latest_version + 1
        model_run = None
        provider_result = None
        if data.viral_kit is None:
            viral_kit, model_run, provider_result = await self._regenerate_version(
                kit=kit,
                version_number=new_version_number,
                user_id=user_id,
                change_reason=data.change_reason,
                latest_viral_kit=latest_viral_kit,
            )
        else:
            viral_kit = _user_version_viral_kit(
                data.viral_kit,
                kit,
                new_version_number,
                user_id,
            )
        try:
            _validate_version_viral_kit(
                viral_kit,
                kit,
                latest_viral_kit,
                user_supplied=data.viral_kit is not None,
            )
            _validate_viral_kit_business_rules(viral_kit)
        except AppError as exc:
            if model_run is not None:
                await _fail_model_run(
                    self._session,
                    model_run,
                    exc,
                    provider_result,
                )
                await self._session.commit()
            raise
        if model_run is not None:
            await self._complete_model_run(model_run, viral_kit, provider_result)
        version = await self._repository.create_version(
            kit=kit,
            user_id=user_id,
            viral_kit=viral_kit,
            parent_version=latest.version,
            change_reason=data.change_reason,
        )
        await self._events.record(
            event_type="viral_kit_version_created",
            workspace_id=workspace_id,
            actor_user_id=user_id,
            subject_type="viral_kit",
            subject_id=kit.id,
            payload_json={"version": version.version, "parent_version": latest.version},
        )
        await self._session.commit()
        return _version_response(version)

    async def record_concept_action(
        self,
        *,
        workspace_id: UUID,
        viral_kit_id: UUID,
        user_id: UUID,
        data: ViralKitConceptActionRequest,
    ) -> ViralKitConceptActionResponse:
        kit = await self._get_kit(workspace_id, viral_kit_id)
        latest = await self._latest_contract(workspace_id, viral_kit_id)
        _require_concept(latest, data.concept_id)
        _validate_concept_action(kit, data)
        action = await self._repository.record_concept_action(
            kit=kit,
            concept_id=data.concept_id,
            action=data.action,
            reason=data.reason,
            actor_user_id=user_id,
        )
        event_type = _event_type_for_action(data.action)
        if event_type is not None:
            await self._events.record(
                event_type=event_type,
                workspace_id=workspace_id,
                actor_user_id=user_id,
                subject_type="viral_kit",
                subject_id=kit.id,
                payload_json={
                    "version": kit.latest_version,
                    "concept_id": data.concept_id,
                    "reason": data.reason,
                },
            )
        await self._session.commit()
        return ViralKitConceptActionResponse.model_validate(action)

    async def create_campaign_pack_from_concept(
        self,
        *,
        workspace_id: UUID,
        viral_kit_id: UUID,
        user_id: UUID,
        concept_id: str,
        data: CreateViralKitCampaignPackRequest,
    ) -> ViralKitCampaignPackResponse:
        kit = await self._get_kit(workspace_id, viral_kit_id)
        latest_version = await self._repository.get_latest_version(workspace_id, viral_kit_id)
        if latest_version is None:
            raise NotFoundError("VIRAL_KIT_VERSION_NOT_FOUND", "ViralKit version was not found.")
        viral_kit = _viral_kit_from_version(latest_version)
        concept = _require_concept(viral_kit, concept_id)
        brief, model_run, provider_result = await self._build_campaign_pack_brief(
            workspace_id=workspace_id,
            user_id=user_id,
            viral_kit=viral_kit,
            viral_kit_version_id=latest_version.id,
            concept=concept,
            rights_note=data.rights_note,
        )
        try:
            pack_result = await self._campaign_packs.create_from_brief(
                workspace_id=workspace_id,
                user_id=user_id,
                product_id=kit.product_id,
                brief=brief,
                source_model_run_id=(
                    model_run.id if model_run is not None else viral_kit.provenance.model_run_id
                ),
                source_prompt_version=(
                    CAMPAIGN_PACK_PROMPT_VERSION
                    if model_run is not None
                    else viral_kit.provenance.prompt_version
                ),
                source_schema_version=brief.schema_version,
            )
        except AppError as exc:
            if model_run is not None:
                await _fail_model_run(
                    self._session,
                    model_run,
                    exc,
                    provider_result,
                )
            raise
        if model_run is not None:
            await self._complete_campaign_pack_model_run(
                model_run,
                brief,
                provider_result,
            )
        await self._repository.record_campaign_pack_link(
            workspace_id=workspace_id,
            viral_kit_version_id=latest_version.id,
            concept_id=concept.id,
            campaign_pack_id=pack_result.campaign_pack_id,
            campaign_pack_version_id=pack_result.campaign_pack_version_id,
        )
        await self._repository.record_concept_action(
            kit=kit,
            concept_id=concept.id,
            action="campaign_pack_created",
            reason="Campaign Pack created from ViralKit concept.",
            actor_user_id=user_id,
        )
        await self._events.record(
            event_type="campaign_pack_created",
            workspace_id=workspace_id,
            actor_user_id=user_id,
            subject_type="campaign_pack",
            subject_id=pack_result.campaign_pack_id,
            payload_json={
                "viral_kit_id": str(kit.id),
                "viral_kit_version": latest_version.version,
                "concept_id": concept.id,
                "pattern_kit_version_ids": [
                    str(item) for item in viral_kit.provenance.pattern_kit_version_ids
                ],
            },
        )
        await self._session.commit()
        return ViralKitCampaignPackResponse(
            concept_id=concept.id,
            campaign_pack_id=pack_result.campaign_pack_id,
            campaign_pack_version_id=pack_result.campaign_pack_version_id,
            compiled_requirements_schema_version=(pack_result.compiled_requirements_schema_version),
            campaign_pack=pack_result.response,
        )

    async def _build_campaign_pack_brief(
        self,
        *,
        workspace_id: UUID,
        user_id: UUID,
        viral_kit: ViralKitV1,
        viral_kit_version_id: UUID,
        concept: ViralKitConceptV1,
        rights_note: str | None,
    ) -> tuple[
        CampaignPackBriefV1,
        AiModelRunModel | None,
        StructuredGenerationResult | None,
    ]:
        deterministic = _campaign_pack_brief(viral_kit, concept, rights_note)
        if self._settings.ai_mode == "fixture":
            return deterministic, None, None

        prompt = get_prompt_package(AiOperationName.CAMPAIGN_PACK_GENERATE)
        input_summary: dict[str, object] = {
            "viral_kit_id": str(viral_kit.id),
            "viral_kit_version_id": str(viral_kit_version_id),
            "concept_id": concept.id,
            "product_id": str(viral_kit.product.product_id),
            "product_context_version": viral_kit.product.product_context_version,
        }
        input_hash = _hash_json(input_summary)
        model_run = await AiModelRunRepository(self._session).create_running(
            workspace_id=workspace_id,
            processing_job_id=None,
            subject_type="viral_kit_concept",
            subject_id=viral_kit.id,
            capability="campaign_pack_generate",
            operation="campaign_pack_generate",
            analysis_mode=self._settings.ai_mode,
            provider=self._settings.ai_provider,
            model=(
                self._settings.resolve_openai_model("campaign_pack_generate")
                if self._settings.ai_provider == "openai"
                else self._settings.ai_text_model or "unconfigured"
            ),
            prompt_version=CAMPAIGN_PACK_PROMPT_VERSION,
            response_schema_version=prompt.output_schema_version,
            schema_version=prompt.output_schema_version,
            request_hash=input_hash,
            input_hash=input_hash,
            input_summary=input_summary,
            endpoint_family=(
                "responses" if self._settings.ai_provider == "openai" else "chat_completions"
            ),
            prompt_name=CAMPAIGN_PACK_PROMPT_NAME,
        )
        context = ViraldyOperationContextV1(
            operation=AiOperationName.CAMPAIGN_PACK_GENERATE,
            request_id=str(model_run.id),
            workspace_id=workspace_id,
            actor_user_id=user_id,
            product_context=viral_kit.product.snapshot_json,
            product_context_version=viral_kit.product.product_context_version,
            objective=viral_kit.objective,
            target_market=viral_kit.target_market,
            source_version_ids=[viral_kit_version_id],
            seller_constraints={
                "viral_kit_constraints": viral_kit.constraints.model_dump(mode="json"),
                "rights_note": rights_note,
            },
            operation_payload={
                "viral_kit_id": str(viral_kit.id),
                "viral_kit_version": viral_kit.version,
                "selected_concept": concept.model_dump(mode="json"),
                "pattern_kit_version_ids": [
                    str(value) for value in viral_kit.provenance.pattern_kit_version_ids
                ],
                "deterministic_requirement_baseline": deterministic.model_dump(mode="json"),
            },
            schema_version=prompt.output_schema_version,
            prompt_version=prompt.prompt_version,
        )
        try:
            provider_result = execute_structured_operation(
                self._settings,
                context,
                CampaignPackBriefV1,
                output_validator=_campaign_pack_output_validator(deterministic),
            )
        except AppError as exc:
            await _fail_model_run(self._session, model_run, exc)
            await self._session.commit()
            raise
        return (
            CampaignPackBriefV1.model_validate(provider_result.parsed_output),
            model_run,
            provider_result,
        )

    async def _complete_campaign_pack_model_run(
        self,
        model_run: AiModelRunModel,
        brief: CampaignPackBriefV1,
        provider_result: StructuredGenerationResult | None,
    ) -> None:
        output_summary: dict[str, object] = {
            "hook_count": len(brief.hooks),
            "must_show_count": len(brief.must_show),
            "source_concept_id": brief.source_concept_id,
        }
        repository = AiModelRunRepository(self._session)
        if provider_result is None:
            await repository.complete(
                model_run,
                output_summary,
                http_status=None,
                provider_request_id=None,
                latency_ms=None,
            )
            return
        await repository.complete(
            model_run,
            output_summary,
            http_status=provider_result.http_status,
            provider_request_id=provider_result.provider_request_id,
            latency_ms=provider_result.latency_ms,
            usage_json=provider_result.usage.model_dump(mode="json"),
            repair_attempt_count=provider_result.repair_attempt_count,
        )

    async def create_feedback(
        self,
        *,
        workspace_id: UUID,
        viral_kit_id: UUID,
        user_id: UUID,
        data: CreateViralKitFeedbackRequest,
    ) -> FeedbackResponse:
        kit = await self._get_kit(workspace_id, viral_kit_id)
        feedback = await self._feedback.record(
            workspace_id=workspace_id,
            created_by_user_id=user_id,
            feedback=FieldFeedbackV1(
                subject_type="viral_kit",
                subject_id=kit.id,
                subject_version=data.subject_version or kit.latest_version,
                field_path=data.field_path,
                feedback_type=data.feedback_type,
                ai_value_json=data.ai_value_json,
                user_value_json=data.user_value_json,
                comment=data.comment,
                model_run_id=data.model_run_id,
            ),
        )
        await self._session.commit()
        await self._session.refresh(feedback)
        return FeedbackResponse.model_validate(feedback)

    async def archive(self, *, workspace_id: UUID, viral_kit_id: UUID) -> None:
        kit = await self._get_kit(workspace_id, viral_kit_id)
        if kit.status == "archived":
            return
        await self._repository.archive(kit)
        await self._session.commit()

    async def _get_kit(self, workspace_id: UUID, viral_kit_id: UUID) -> ViralKitModel:
        kit = await self._repository.get_kit(workspace_id, viral_kit_id)
        if kit is None:
            raise NotFoundError("VIRAL_KIT_NOT_FOUND", "ViralKit was not found.")
        return kit

    async def _latest_contract(self, workspace_id: UUID, viral_kit_id: UUID) -> ViralKitV1:
        version = await self._repository.get_latest_version(workspace_id, viral_kit_id)
        if version is None:
            raise NotFoundError("VIRAL_KIT_VERSION_NOT_FOUND", "ViralKit version was not found.")
        return _viral_kit_from_version(version)

    async def _load_product(self, workspace_id: UUID, product_id: UUID) -> ProductContextSnapshot:
        product = await self._products.get_product_context_snapshot(workspace_id, product_id)
        if product is None:
            raise NotFoundError("PRODUCT_NOT_FOUND", "Product was not found.")
        return product

    async def _load_patterns(
        self,
        workspace_id: UUID,
        pattern_kit_version_ids: list[UUID],
    ) -> list[PatternKitVersionSnapshot]:
        patterns = []
        for pattern_kit_version_id in pattern_kit_version_ids:
            snapshot = await self._patterns.get_version_snapshot_by_id(
                workspace_id,
                pattern_kit_version_id,
            )
            if snapshot.status == "archived":
                raise AppError(
                    "VIRAL_KIT_PATTERN_INAPPLICABLE",
                    "Archived PatternKit versions cannot be used for ViralKit composition.",
                )
            patterns.append(snapshot)
        return patterns

    async def _create_model_run(
        self,
        *,
        workspace_id: UUID,
        viral_kit_id: UUID,
        input_summary: dict[str, object],
    ) -> AiModelRunModel:
        input_hash = _hash_json(input_summary)
        return await AiModelRunRepository(self._session).create_running(
            workspace_id=workspace_id,
            processing_job_id=None,
            subject_type="viral_kit",
            subject_id=viral_kit_id,
            capability="viral_kit_compose",
            operation="viral_kit_compose",
            analysis_mode=self._settings.ai_mode,
            provider=(
                self._settings.ai_provider if self._settings.ai_mode != "fixture" else "fixture"
            ),
            model=_model_name(self._settings),
            prompt_version=VIRAL_KIT_PROMPT_VERSION,
            response_schema_version=VIRAL_KIT_SCHEMA_VERSION,
            schema_version=VIRAL_KIT_SCHEMA_VERSION,
            request_hash=input_hash,
            input_hash=input_hash,
            input_summary=input_summary,
            endpoint_family=(
                "responses"
                if self._settings.ai_mode == "live" and self._settings.ai_provider == "openai"
                else None
            ),
            prompt_name=VIRAL_KIT_PROMPT_NAME,
        )

    async def _compose(
        self,
        *,
        viral_kit_id: UUID,
        workspace_id: UUID,
        version: int,
        user_id: UUID,
        created_at: datetime,
        data: CreateViralKitRequest,
        product: ProductContextSnapshot,
        patterns: list[PatternKitVersionSnapshot],
        matches: list[ViralKitPatternMatchV1],
        model_run_id: UUID,
    ) -> tuple[ViralKitV1, StructuredGenerationResult | None]:
        if self._settings.ai_mode == "fixture":
            return (
                build_fixture_viral_kit(
                    viral_kit_id=viral_kit_id,
                    workspace_id=workspace_id,
                    version=version,
                    created_by=user_id,
                    created_at=created_at,
                    request=data,
                    product=product,
                    patterns=patterns,
                    pattern_matches=matches,
                    model_run_id=model_run_id,
                ),
                None,
            )
        execution = LiveViralKitProvider(self._settings).compose_with_metadata(
            viral_kit_id=viral_kit_id,
            workspace_id=workspace_id,
            version=version,
            created_by=user_id,
            created_at=created_at.isoformat(),
            request=data,
            product_snapshot=product.model_dump(mode="json"),
            pattern_payloads=_pattern_payloads(patterns),
            pattern_matches=[match.model_dump(mode="json") for match in matches],
            model_run_id=model_run_id,
        )
        return execution.output, execution.provider_result

    async def _regenerate_version(
        self,
        *,
        kit: ViralKitModel,
        version_number: int,
        user_id: UUID,
        change_reason: str,
        latest_viral_kit: ViralKitV1,
    ) -> tuple[
        ViralKitV1,
        AiModelRunModel,
        StructuredGenerationResult | None,
    ]:
        request = _request_from_viral_kit(latest_viral_kit, change_reason)
        product = ProductContextSnapshot(
            product_id=latest_viral_kit.product.product_id,
            workspace_id=kit.workspace_id,
            context_schema_version=latest_viral_kit.product.product_context_schema_version,
            product_context_version=latest_viral_kit.product.product_context_version,
            product_context=latest_viral_kit.product.snapshot_json,
        )
        patterns = await self._load_patterns(
            kit.workspace_id,
            latest_viral_kit.provenance.pattern_kit_version_ids,
        )
        matches = match_patterns(
            product_context=product.product_context,
            patterns=patterns,
            request=request,
        )
        _validate_pattern_matches(matches, request.applicability_override_reason)
        model_run = await self._create_model_run(
            workspace_id=kit.workspace_id,
            viral_kit_id=kit.id,
            input_summary=_input_summary(request, product, matches),
        )
        try:
            viral_kit, provider_result = await self._compose(
                viral_kit_id=kit.id,
                workspace_id=kit.workspace_id,
                version=version_number,
                user_id=user_id,
                created_at=utc_now(),
                data=request,
                product=product,
                patterns=patterns,
                matches=matches,
                model_run_id=model_run.id,
            )
            return viral_kit, model_run, provider_result
        except AppError as exc:
            await _fail_model_run(self._session, model_run, exc)
            await self._session.commit()
            raise

    async def _complete_model_run(
        self,
        model_run: AiModelRunModel,
        viral_kit: ViralKitV1,
        provider_result: StructuredGenerationResult | None,
    ) -> None:
        output_summary: dict[str, object] = {
            "concept_count": len(viral_kit.concepts),
            "pattern_match_count": len(viral_kit.pattern_matches),
            "overall_confidence": viral_kit.overall_confidence,
        }
        repository = AiModelRunRepository(self._session)
        if provider_result is None:
            await repository.complete(
                model_run,
                output_summary,
                http_status=None,
                provider_request_id=None,
                latency_ms=None,
            )
            return
        await repository.complete(
            model_run,
            output_summary,
            http_status=provider_result.http_status,
            provider_request_id=provider_result.provider_request_id,
            latency_ms=provider_result.latency_ms,
            usage_json=provider_result.usage.model_dump(mode="json"),
            repair_attempt_count=provider_result.repair_attempt_count,
        )


def _validate_create_viral_kit(
    viral_kit: ViralKitV1,
    viral_kit_id: UUID,
    workspace_id: UUID,
    data: CreateViralKitRequest,
    product: ProductContextSnapshot,
) -> None:
    if viral_kit.id != viral_kit_id or viral_kit.workspace_id != workspace_id:
        raise AppError("VIRAL_KIT_CONFLICT", "ViralKit output identity does not match request.")
    if viral_kit.version != 1:
        raise AppError("VIRAL_KIT_CONFLICT", "New ViralKits must start at version 1.")
    if viral_kit.product.product_id != product.product_id:
        raise AppError("VIRAL_KIT_CONFLICT", "ViralKit product snapshot changed.")
    if viral_kit.product.product_context_version != data.expected_product_context_version:
        raise ConflictError(
            "VIRAL_KIT_PRODUCT_VERSION_CONFLICT",
            "Product context version changed before ViralKit persistence.",
        )
    expected_ids = data.pattern_kit_version_ids
    if viral_kit.provenance.pattern_kit_version_ids != expected_ids:
        raise AppError("VIRAL_KIT_CONFLICT", "ViralKit PatternKit provenance changed.")
    if viral_kit.status != "ready_for_review":
        raise AppError("VIRAL_KIT_CONFLICT", "New ViralKits must be ready_for_review.")


def _validate_version_viral_kit(
    viral_kit: ViralKitV1,
    kit: ViralKitModel,
    previous: ViralKitV1,
    *,
    user_supplied: bool,
) -> None:
    if viral_kit.id != kit.id or viral_kit.workspace_id != kit.workspace_id:
        raise AppError("VIRAL_KIT_CONFLICT", "ViralKit version identity does not match kit.")
    if viral_kit.product.product_id != kit.product_id:
        raise AppError("VIRAL_KIT_CONFLICT", "ViralKit version product changed.")
    if viral_kit.version != kit.latest_version + 1:
        raise AppError("VIRAL_KIT_CONFLICT", "ViralKit version number is invalid.")
    if viral_kit.status != "ready_for_review":
        raise AppError("VIRAL_KIT_CONFLICT", "New ViralKit versions must be ready_for_review.")
    if not _same_product_snapshot(viral_kit, previous):
        raise AppError(
            "VIRAL_KIT_PRODUCT_SNAPSHOT_CONFLICT",
            "ViralKit versions cannot replace the locked Product Context snapshot.",
        )
    if viral_kit.provenance.pattern_kit_version_ids != previous.provenance.pattern_kit_version_ids:
        raise AppError(
            "VIRAL_KIT_PROVENANCE_CONFLICT",
            "ViralKit versions cannot replace source PatternKit versions.",
        )
    if user_supplied and viral_kit.provenance != previous.provenance:
        raise AppError(
            "VIRAL_KIT_PROVENANCE_CONFLICT",
            "User-authored versions cannot replace model or prompt provenance.",
        )
    if user_supplied and viral_kit.constraints.governance != previous.constraints.governance:
        raise AppError(
            "VIRAL_KIT_GOVERNANCE_CONFLICT",
            "User-authored versions cannot replace product governance.",
        )


def _validate_viral_kit_business_rules(viral_kit: ViralKitV1) -> None:
    governance = viral_kit.constraints.governance
    product_governance = viral_kit.product.snapshot_json.governance
    required_prohibited_claims = {
        claim.text for claim in product_governance.claims if claim.rule_type == "prohibited"
    }
    if not required_prohibited_claims.issubset(set(governance.prohibited_claims)):
        raise AppError(
            "VIRAL_KIT_GOVERNANCE_CONFLICT",
            "ViralKit governance does not preserve prohibited product claims.",
        )
    if not set(product_governance.required_disclosures).issubset(
        set(governance.required_disclosures)
    ):
        raise AppError(
            "VIRAL_KIT_GOVERNANCE_CONFLICT",
            "ViralKit governance does not preserve required product disclosures.",
        )
    if not set(product_governance.prohibited_content).issubset(set(governance.prohibited_content)):
        raise AppError(
            "VIRAL_KIT_GOVERNANCE_CONFLICT",
            "ViralKit governance does not preserve prohibited product content.",
        )
    if not set(product_governance.rights_notes).issubset(set(governance.rights_notes)):
        raise AppError(
            "VIRAL_KIT_GOVERNANCE_CONFLICT",
            "ViralKit governance does not preserve product rights notes.",
        )

    provenance_ids = viral_kit.provenance.pattern_kit_version_ids
    if len(provenance_ids) != len(set(provenance_ids)):
        raise AppError(
            "VIRAL_KIT_PROVENANCE_CONFLICT",
            "ViralKit source PatternKit versions must be unique.",
        )
    allowed_pattern_ids = set(provenance_ids)
    match_ids = [match.pattern_kit_version_id for match in viral_kit.pattern_matches]
    if set(match_ids) != allowed_pattern_ids or len(match_ids) != len(set(match_ids)):
        raise AppError(
            "VIRAL_KIT_PROVENANCE_CONFLICT",
            "ViralKit pattern matches do not match source provenance.",
        )
    for concept in viral_kit.concepts:
        if not set(concept.source_pattern_kit_version_ids).issubset(allowed_pattern_ids):
            raise AppError(
                "VIRAL_KIT_PROVENANCE_CONFLICT",
                "ViralKit concept references an unknown PatternKit version.",
            )
    for decision in (
        viral_kit.adaptation_plan.keep
        + viral_kit.adaptation_plan.change
        + viral_kit.adaptation_plan.avoid
    ):
        if not set(decision.source_pattern_kit_version_ids).issubset(allowed_pattern_ids):
            raise AppError(
                "VIRAL_KIT_PROVENANCE_CONFLICT",
                "ViralKit adaptation references an unknown PatternKit version.",
            )

    prohibited = set(governance.prohibited_claims + governance.prohibited_content)
    disclosures = set(governance.required_disclosures)
    for concept in viral_kit.concepts:
        if prohibited and not prohibited.issubset(set(concept.claims_to_avoid)):
            raise AppError(
                "VIRAL_KIT_GOVERNANCE_CONFLICT",
                "ViralKit concept does not preserve prohibited claims.",
            )
        if disclosures and not disclosures.issubset(set(concept.required_disclosures)):
            raise AppError(
                "VIRAL_KIT_GOVERNANCE_CONFLICT",
                "ViralKit concept does not preserve required disclosures.",
            )
        if viral_kit.constraints.commercial.product_tag_required and not any(
            requirement.requirement_type == "product_tag_presence"
            for requirement in concept.must_show
        ):
            raise AppError(
                "VIRAL_KIT_GOVERNANCE_CONFLICT",
                "TikTok Shop product-tag requirement was not preserved.",
            )


def _same_product_snapshot(current: ViralKitV1, previous: ViralKitV1) -> bool:
    return (
        current.product.product_id == previous.product.product_id
        and current.product.product_context_schema_version
        == previous.product.product_context_schema_version
        and current.product.product_context_version == previous.product.product_context_version
        and current.product.snapshot_json == previous.product.snapshot_json
    )


def _validate_product_version(product: ProductContextSnapshot, expected_version: int) -> None:
    if product.product_context_version != expected_version:
        raise ConflictError(
            "VIRAL_KIT_PRODUCT_VERSION_CONFLICT",
            "Product context version does not match the expected version.",
        )


def _validate_pattern_matches(
    matches: list[ViralKitPatternMatchV1],
    override_reason: str | None,
) -> None:
    if not matches:
        raise AppError("VIRAL_KIT_PATTERN_INAPPLICABLE", "At least one PatternKit is required.")
    if any(match.applicability_status == "rejected" for match in matches):
        raise AppError(
            "VIRAL_KIT_PATTERN_INAPPLICABLE",
            "One or more PatternKits are inapplicable without an explicit override.",
        )
    if not any(
        match.applicability_status in {"matched", "partial", "override"} for match in matches
    ):
        raise AppError("VIRAL_KIT_PATTERN_INAPPLICABLE", "No PatternKit is applicable.")
    if any(match.applicability_status == "override" for match in matches) and not override_reason:
        raise AppError(
            "VIRAL_KIT_PATTERN_INAPPLICABLE",
            "PatternKit applicability overrides require a reason.",
        )


def _validate_concept_action(
    kit: ViralKitModel,
    data: ViralKitConceptActionRequest,
) -> None:
    if kit.status == "archived":
        raise AppError("VIRAL_KIT_ARCHIVED", "Archived ViralKits are read-only.")
    if data.action == "selected" and not data.reason:
        raise AppError(
            "VIRAL_KIT_CONCEPT_REASON_REQUIRED",
            "Selecting a concept requires a seller or reviewer reason.",
        )
    if data.action == "restored" and kit.selected_concept_id != data.concept_id:
        raise ConflictError(
            "VIRAL_KIT_CONCEPT_NOT_FOUND",
            "Only the currently selected concept can be restored.",
        )


def _require_concept(viral_kit: ViralKitV1, concept_id: str) -> ViralKitConceptV1:
    for concept in viral_kit.concepts:
        if concept.id == concept_id:
            return concept
    raise NotFoundError("VIRAL_KIT_CONCEPT_NOT_FOUND", "ViralKit concept was not found.")


def _event_type_for_action(action: str) -> ProductEventType | None:
    if action == "selected":
        return "concept_selected"
    if action == "rejected":
        return "concept_rejected"
    return None


def _campaign_pack_brief(
    viral_kit: ViralKitV1,
    concept: ViralKitConceptV1,
    rights_note: str | None,
) -> CampaignPackBriefV1:
    product = viral_kit.product.snapshot_json
    return CampaignPackBriefV1(
        product_snapshot=product,
        objective=CampaignObjectiveV1(
            objective_type=viral_kit.objective,
            primary_action="create_ugc_revision",
            channel="tiktok_shop" if viral_kit.platform == "tiktok_shop" else "unknown",
        ),
        audience=CampaignAudienceV1(
            persona_id=concept.buyer_persona_id,
            persona_label=concept.buyer_persona_label,
            pain_points=[concept.buyer_pain],
            desired_outcomes=[concept.desired_outcome],
            objections=[],
            awareness_stage=concept.awareness_stage or "unknown",
        ),
        angle=CampaignAngleV1(
            name=concept.creative_angle,
            promise=concept.desired_outcome,
            mechanism=concept.demo_mechanism,
            emotional_driver=concept.buyer_pain,
        ),
        creator_direction=CreatorDirectionV1(
            persona=concept.creator_persona,
            delivery_style=concept.delivery_style,
            tone=["clear", "product-grounded"],
            avoid_tones=["overclaiming", "pressure selling"],
            authenticity_notes=["Do not copy source creator identity or exact script."],
        ),
        hooks=[
            HookOptionV1(
                id=f"{concept.id}_hook",
                spoken_text=concept.hook.spoken_text,
                overlay_text=concept.hook.overlay_text,
                opening_visual=concept.hook.opening_visual,
                hook_type=concept.hook.hook_type,
                target_time_ms=concept.hook.target_time_ms,
                mandatory=True,
            )
        ],
        script_beats=[
            ScriptBeatV1(
                id=f"{concept.id}_beat_{index}",
                sequence=index,
                beat_type=requirement.requirement_type,
                instruction=requirement.instruction,
                expected_start_ms=None,
                expected_end_ms=requirement.expected_before_ms,
                required=requirement.required,
            )
            for index, requirement in enumerate(concept.must_show, start=1)
        ],
        storyboard=[
            StoryboardSceneV1(
                id=f"{concept.id}_scene_{index}",
                sequence=index,
                instruction=requirement.instruction,
                shot_type="close_up" if "product" in requirement.requirement_type else "in_use",
                product_visibility_required="product" in requirement.requirement_type,
                overlay_text=(
                    concept.overlays[index - 1] if index <= len(concept.overlays) else None
                ),
                spoken_direction=(
                    concept.spoken_lines[index - 1] if index <= len(concept.spoken_lines) else None
                ),
                required=requirement.required,
            )
            for index, requirement in enumerate(concept.must_show, start=1)
        ],
        must_show=[
            MustShowRequirementV1(
                id=requirement.id,
                requirement_type=_campaign_requirement_type(requirement.requirement_type),
                description=requirement.instruction,
                severity=requirement.severity,
                expected_before_ms=requirement.expected_before_ms,
                source_path=f"viral_kit.concepts.{concept.id}.must_show.{requirement.id}",
            )
            for requirement in concept.must_show
        ],
        talking_points=[concept.buyer_pain, concept.desired_outcome],
        text_overlays=concept.overlays,
        proof_direction=[concept.proof_mechanism],
        offer_direction=[concept.offer_framing] if concept.offer_framing else [],
        cta=CtaDirectionV1(
            spoken=concept.cta_strategy,
            overlay=(
                "Product tag" if viral_kit.constraints.commercial.product_tag_required else None
            ),
            cta_type="product_tag"
            if viral_kit.constraints.commercial.product_tag_required
            else "soft_next_step",
            product_tag_required=viral_kit.constraints.commercial.product_tag_required,
            required_before_ms=None,
        ),
        claim_guardrails=ClaimGuardrailsV1(
            allowed=[
                rule.text for rule in product.governance.claims if rule.rule_type == "allowed"
            ],
            allowed_with_qualification=[
                rule.text
                for rule in product.governance.claims
                if rule.rule_type == "allowed_with_qualification"
            ],
            prohibited=concept.claims_to_avoid,
            required_disclosures=concept.required_disclosures,
        ),
        do=["show product clearly", "follow the concept test hypothesis"],
        dont=["copy source scripts", "add prohibited or unsupported claims"],
        rights_note=RightsNoteV1(
            raw_footage_requested=viral_kit.constraints.production.raw_footage_required,
            note=rights_note or "Rights remain pending until seller confirms creator usage.",
        ),
        revision_checklist=[
            requirement.instruction for requirement in concept.must_show if requirement.required
        ],
        source_viral_kit_id=viral_kit.id,
        source_viral_kit_version=viral_kit.version,
        source_pattern_kit_version_ids=viral_kit.provenance.pattern_kit_version_ids,
        source_concept_id=concept.id,
    )


def _campaign_requirement_type(requirement_type: str) -> str:
    lowered = requirement_type.lower()
    if "cta" in lowered or "tag" in lowered:
        return "cta"
    if "demo" in lowered or "use" in lowered:
        return "demo"
    if "proof" in lowered or "result" in lowered:
        return "proof"
    if "claim" in lowered or "disclosure" in lowered:
        return "claim"
    if "overlay" in lowered or "spoken" in lowered or "hook" in lowered:
        return "overlay"
    if "product" in lowered:
        return "product"
    return "scene"


def _detail_response(kit: ViralKitModel, version: ViralKitVersionModel) -> ViralKitDetailResponse:
    return ViralKitDetailResponse(
        kit=ViralKitSummaryResponse.model_validate(kit),
        latest_version=_version_response(version),
    )


def _version_response(version: ViralKitVersionModel) -> ViralKitVersionResponse:
    return ViralKitVersionResponse(
        id=version.id,
        viral_kit_id=version.viral_kit_id,
        workspace_id=version.workspace_id,
        version=version.version,
        parent_version=version.parent_version,
        change_reason=version.change_reason,
        schema_version=version.schema_version,
        product_context_version=version.product_context_version,
        product_snapshot_json=version.product_snapshot_json,
        viral_kit=_viral_kit_from_version(version),
        model_run_id=version.model_run_id,
        created_by_user_id=version.created_by_user_id,
        created_at=version.created_at,
    )


def _viral_kit_from_version(version: ViralKitVersionModel) -> ViralKitV1:
    return ViralKitV1.model_validate(version.viral_kit_json)


def _user_version_viral_kit(
    viral_kit: ViralKitV1,
    kit: ViralKitModel,
    version_number: int,
    user_id: UUID,
) -> ViralKitV1:
    return viral_kit.model_copy(
        update={
            "id": kit.id,
            "workspace_id": kit.workspace_id,
            "version": version_number,
            "status": "ready_for_review",
            "selected_concept_id": None,
            "created_by": user_id,
            "created_at": utc_now(),
        }
    )


def _request_from_viral_kit(viral_kit: ViralKitV1, change_reason: str) -> CreateViralKitRequest:
    return CreateViralKitRequest(
        product_id=viral_kit.product.product_id,
        expected_product_context_version=viral_kit.product.product_context_version,
        pattern_kit_version_ids=viral_kit.provenance.pattern_kit_version_ids,
        objective=viral_kit.objective,
        platform=viral_kit.platform,
        target_market=viral_kit.target_market,
        buyer_persona_id=viral_kit.buyer_context.persona_id,
        creator_constraints=viral_kit.constraints.creator,
        production_constraints=viral_kit.constraints.production,
        commercial_constraints=viral_kit.constraints.commercial,
        concept_count=3,
        notes=change_reason,
        applicability_override_reason=None,
    )


def _pattern_payloads(patterns: list[PatternKitVersionSnapshot]) -> list[dict[str, object]]:
    return [
        {
            "pattern_kit_id": str(pattern.pattern_kit_id),
            "pattern_kit_version_id": str(pattern.pattern_kit_version_id),
            "version": pattern.version,
            "status": pattern.status,
            "pattern": pattern.pattern.model_dump(mode="json"),
        }
        for pattern in patterns
    ]


def _input_summary(
    data: CreateViralKitRequest,
    product: ProductContextSnapshot,
    matches: list[ViralKitPatternMatchV1],
) -> dict[str, object]:
    return {
        "product_id": str(product.product_id),
        "expected_product_context_version": data.expected_product_context_version,
        "pattern_kit_version_ids": [str(item) for item in data.pattern_kit_version_ids],
        "objective": data.objective,
        "platform": data.platform,
        "target_market": data.target_market,
        "concept_count": data.concept_count,
        "match_statuses": [match.applicability_status for match in matches],
    }


def _campaign_pack_output_validator(
    expected: CampaignPackBriefV1,
) -> Callable[[BaseModel], None]:
    expected_requirements = {
        requirement.id: (
            requirement.requirement_type,
            requirement.severity,
            requirement.expected_before_ms,
            requirement.source_path,
        )
        for requirement in expected.must_show
    }

    def validate(output: BaseModel) -> None:
        brief = CampaignPackBriefV1.model_validate(output)
        if brief.product_snapshot != expected.product_snapshot:
            raise ValueError("Campaign Pack product snapshot changed.")
        if brief.source_concept_id != expected.source_concept_id:
            raise ValueError("Campaign Pack source concept changed.")
        if brief.source_pattern_kit_version_ids != expected.source_pattern_kit_version_ids:
            raise ValueError("Campaign Pack PatternKit source IDs changed.")
        if brief.claim_guardrails.prohibited != expected.claim_guardrails.prohibited:
            raise ValueError("Campaign Pack prohibited claims changed.")
        if (
            brief.claim_guardrails.required_disclosures
            != expected.claim_guardrails.required_disclosures
        ):
            raise ValueError("Campaign Pack required disclosures changed.")
        if (
            brief.cta.product_tag_required != expected.cta.product_tag_required
            or brief.cta.required_before_ms != expected.cta.required_before_ms
        ):
            raise ValueError("Campaign Pack CTA requirements changed.")
        observed_requirements = {
            requirement.id: (
                requirement.requirement_type,
                requirement.severity,
                requirement.expected_before_ms,
                requirement.source_path,
            )
            for requirement in brief.must_show
        }
        if observed_requirements != expected_requirements:
            raise ValueError("Campaign Pack hard requirement semantics changed.")

    return validate


def _hash_json(payload: dict[str, object]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def _model_name(settings: Settings) -> str:
    if settings.ai_mode == "fixture":
        return "fixture_viral_kit_v1"
    if settings.ai_provider == "openai":
        return settings.resolve_openai_model("viral_kit_compose")
    return settings.ai_text_model or "unconfigured"


async def _fail_model_run(
    session: AsyncSession,
    model_run: AiModelRunModel,
    error: AppError,
    provider_result: StructuredGenerationResult | None = None,
) -> None:
    http_status = error.details.get("http_status")
    provider_request_id = error.details.get("provider_request_id")
    repair_attempt_count = error.details.get("repair_attempt_count")
    await AiModelRunRepository(session).fail(
        model_run,
        error.code,
        error.message,
        http_status=(
            http_status
            if isinstance(http_status, int)
            else provider_result.http_status
            if provider_result
            else None
        ),
        safe_error_message=error.message,
        provider_request_id=(
            provider_request_id
            if isinstance(provider_request_id, str)
            else provider_result.provider_request_id
            if provider_result
            else None
        ),
        repair_attempt_count=(
            repair_attempt_count
            if isinstance(repair_attempt_count, int)
            else provider_result.repair_attempt_count
            if provider_result
            else None
        ),
    )
