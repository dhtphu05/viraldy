from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from viraldy.modules.ai_gateway.models import AiModelRunModel
from viraldy.modules.ai_gateway.public import (
    PATTERN_KIT_PROMPT_NAME,
    PATTERN_KIT_PROMPT_VERSION,
    PATTERN_KIT_SCHEMA_VERSION,
    AiModelRunRepository,
    EvidenceItemForModelV1,
    StructuredGenerationResult,
)
from viraldy.modules.creative_dna.contracts import CreativeDnaV1
from viraldy.modules.creative_dna.public import CreativeDnaRepository
from viraldy.modules.feedback.public import FeedbackResponse, FeedbackWriter, FieldFeedbackV1
from viraldy.modules.media_analysis.public import EvidenceItemModel, EvidenceQueries
from viraldy.modules.pattern_kits.contracts import PatternEvidenceRefV1, PatternKitV1
from viraldy.modules.pattern_kits.models import PatternKitModel, PatternKitVersionModel
from viraldy.modules.pattern_kits.performance import validate_supported_performance
from viraldy.modules.pattern_kits.provider import (
    LivePatternKitProvider,
    PatternEvidenceInput,
    PatternSourceInput,
    _evidence_feature_paths,
    build_fixture_pattern_kit,
)
from viraldy.modules.pattern_kits.repository import PatternKitRepository
from viraldy.modules.pattern_kits.schemas import (
    CreatePatternKitFeedbackRequest,
    CreatePatternKitRequest,
    CreatePatternKitVersionRequest,
    PatternKitActionRequest,
    PatternKitActionResponse,
    PatternKitDetailResponse,
    PatternKitSummaryResponse,
    PatternKitVersionResponse,
)
from viraldy.modules.product_events.public import ProductEventPublisher, ProductEventType
from viraldy.platform.clock.utc import utc_now
from viraldy.platform.config.settings import Settings
from viraldy.shared.errors.base import AppError, ConflictError, NotFoundError


class PatternKitService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings
        self._repository = PatternKitRepository(session)
        self._dna = CreativeDnaRepository(session)
        self._evidence = EvidenceQueries(session)
        self._feedback = FeedbackWriter(session)
        self._events = ProductEventPublisher(session)

    async def create(
        self,
        *,
        workspace_id: UUID,
        user_id: UUID,
        data: CreatePatternKitRequest,
    ) -> PatternKitDetailResponse:
        _reject_unsupported_kind(data)
        sources = await self._load_sources(workspace_id, data.source_creative_dna_version_ids)
        pattern_kit_id = uuid4()
        created_at = utc_now()
        model_run = await self._create_model_run(
            workspace_id=workspace_id,
            pattern_kit_id=pattern_kit_id,
            input_summary=_input_summary(data, sources),
        )
        try:
            pattern, provider_result = await self._extract_pattern(
                pattern_kit_id=pattern_kit_id,
                workspace_id=workspace_id,
                version=1,
                user_id=user_id,
                created_at=created_at,
                data=data,
                sources=sources,
                model_run_id=model_run.id,
            )
            _validate_create_pattern(pattern, pattern_kit_id, workspace_id, data, sources)
            validate_supported_performance(pattern.performance_summary, self._settings)
            evidence_links = _validate_and_extract_evidence_links(pattern, sources)
            source_rows = [
                (source.creative_dna_version_id, source.asset_version_id) for source in sources
            ]
            kit, version = await self._repository.create_kit_with_version(
                workspace_id=workspace_id,
                user_id=user_id,
                pattern=pattern,
                source_rows=source_rows,
                evidence_links=evidence_links,
            )
            await self._complete_model_run(
                model_run,
                pattern,
                evidence_links,
                provider_result,
            )
            await self._events.record(
                event_type="pattern_kit_created",
                workspace_id=workspace_id,
                actor_user_id=user_id,
                subject_type="pattern_kit",
                subject_id=kit.id,
                payload_json={"version": version.version, "kind": kit.kind},
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
        kind: str | None = None,
        category: str | None = None,
        platform: str | None = None,
        market: str | None = None,
        objective: str | None = None,
        source_creative_dna_version_id: UUID | None = None,
        created_by: UUID | None = None,
        search: str | None = None,
        limit: int = 100,
    ) -> list[PatternKitSummaryResponse]:
        kits = await self._repository.list_kits(
            workspace_id=workspace_id,
            status=status,
            kind=kind,
            category=category,
            platform=platform,
            market=market,
            objective=objective,
            source_creative_dna_version_id=source_creative_dna_version_id,
            created_by=created_by,
            search=search,
            limit=limit,
        )
        return [PatternKitSummaryResponse.model_validate(kit) for kit in kits]

    async def get(self, workspace_id: UUID, pattern_kit_id: UUID) -> PatternKitDetailResponse:
        kit = await self._get_kit(workspace_id, pattern_kit_id)
        version = await self._repository.get_latest_version(workspace_id, pattern_kit_id)
        if version is None:
            raise NotFoundError(
                "PATTERN_KIT_VERSION_NOT_FOUND",
                "PatternKit version was not found.",
            )
        return _detail_response(kit, version)

    async def list_versions(
        self,
        workspace_id: UUID,
        pattern_kit_id: UUID,
    ) -> list[PatternKitVersionResponse]:
        await self._get_kit(workspace_id, pattern_kit_id)
        versions = await self._repository.list_versions(workspace_id, pattern_kit_id)
        return [_version_response(version) for version in versions]

    async def get_version(
        self,
        workspace_id: UUID,
        pattern_kit_id: UUID,
        version_number: int,
    ) -> PatternKitVersionResponse:
        await self._get_kit(workspace_id, pattern_kit_id)
        version = await self._repository.get_version(workspace_id, pattern_kit_id, version_number)
        if version is None:
            raise NotFoundError(
                "PATTERN_KIT_VERSION_NOT_FOUND",
                "PatternKit version was not found.",
            )
        return _version_response(version)

    async def create_version(
        self,
        *,
        workspace_id: UUID,
        pattern_kit_id: UUID,
        user_id: UUID,
        data: CreatePatternKitVersionRequest,
    ) -> PatternKitVersionResponse:
        kit = await self._get_kit(workspace_id, pattern_kit_id)
        if kit.status == "archived":
            raise AppError("PATTERN_KIT_ARCHIVED", "Archived PatternKits are read-only.")
        latest = await self._repository.get_latest_version(workspace_id, pattern_kit_id)
        if latest is None:
            raise NotFoundError(
                "PATTERN_KIT_VERSION_NOT_FOUND",
                "PatternKit version was not found.",
            )
        latest_pattern = _pattern_from_version(latest)
        new_version_number = kit.latest_version + 1
        model_run = None
        provider_result = None
        if data.pattern is None:
            source_ids = latest_pattern.source.creative_dna_version_ids
            sources = await self._load_sources(workspace_id, source_ids)
            pattern, model_run, provider_result = await self._regenerate_version(
                kit=kit,
                version_number=new_version_number,
                user_id=user_id,
                change_reason=data.change_reason,
                sources=sources,
                latest_pattern=latest_pattern,
            )
        else:
            sources = await self._load_sources(
                workspace_id,
                data.pattern.source.creative_dna_version_ids,
            )
            pattern = _user_version_pattern(
                data.pattern,
                kit,
                new_version_number,
                user_id,
            )
        try:
            _validate_version_pattern(pattern, kit, sources)
            if (
                data.pattern is not None
                and pattern.performance_summary != latest_pattern.performance_summary
            ):
                raise AppError(
                    "PATTERN_KIT_PERFORMANCE_IMMUTABLE",
                    "User-authored versions cannot replace verified performance evidence.",
                )
            validate_supported_performance(pattern.performance_summary, self._settings)
            evidence_links = _validate_and_extract_evidence_links(pattern, sources)
        except AppError as exc:
            if model_run is not None:
                await AiModelRunRepository(self._session).fail(
                    model_run,
                    exc.code,
                    exc.message,
                    safe_error_message=exc.message,
                )
                await self._session.commit()
            raise
        if model_run is not None:
            await self._complete_model_run(
                model_run,
                pattern,
                evidence_links,
                provider_result,
            )
        source_rows = [
            (source.creative_dna_version_id, source.asset_version_id) for source in sources
        ]
        version = await self._repository.create_version(
            kit=kit,
            user_id=user_id,
            pattern=pattern,
            parent_version=latest.version,
            change_reason=data.change_reason,
            source_rows=source_rows,
            evidence_links=evidence_links,
        )
        await self._events.record(
            event_type="pattern_kit_version_created",
            workspace_id=workspace_id,
            actor_user_id=user_id,
            subject_type="pattern_kit",
            subject_id=kit.id,
            payload_json={"version": version.version, "parent_version": latest.version},
        )
        await self._session.commit()
        return _version_response(version)

    async def record_action(
        self,
        *,
        workspace_id: UUID,
        pattern_kit_id: UUID,
        user_id: UUID,
        data: PatternKitActionRequest,
    ) -> PatternKitActionResponse:
        kit = await self._get_kit(workspace_id, pattern_kit_id)
        _validate_action_transition(kit.status, data.action, data.reason)
        if (
            kit.kind == "workspace_learned_pattern"
            and kit.status == "candidate"
            and data.action == "reviewed"
            and not data.reason
        ):
            latest = await self._repository.get_latest_version(workspace_id, pattern_kit_id)
            if (
                latest is None
                or _pattern_from_version(latest).performance_summary.evidence_status == "none"
            ):
                raise AppError(
                    "PATTERN_KIT_PROMOTION_EVIDENCE_REQUIRED",
                    "Promoting a learned PatternKit requires a documented seller action "
                    "or performance evidence.",
                )
        action = await self._repository.record_action(
            kit=kit,
            version=kit.latest_version,
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
                subject_type="pattern_kit",
                subject_id=kit.id,
                payload_json={"version": kit.latest_version, "reason": data.reason},
            )
        await self._session.commit()
        return PatternKitActionResponse.model_validate(action)

    async def create_feedback(
        self,
        *,
        workspace_id: UUID,
        pattern_kit_id: UUID,
        user_id: UUID,
        data: CreatePatternKitFeedbackRequest,
    ) -> FeedbackResponse:
        kit = await self._get_kit(workspace_id, pattern_kit_id)
        feedback = await self._feedback.record(
            workspace_id=workspace_id,
            created_by_user_id=user_id,
            feedback=FieldFeedbackV1(
                subject_type="pattern_kit",
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

    async def archive(
        self,
        *,
        workspace_id: UUID,
        pattern_kit_id: UUID,
        user_id: UUID,
    ) -> None:
        kit = await self._get_kit(workspace_id, pattern_kit_id)
        if kit.status == "archived":
            return
        await self._repository.archive(kit, user_id)
        await self._session.commit()

    async def _get_kit(self, workspace_id: UUID, pattern_kit_id: UUID) -> PatternKitModel:
        kit = await self._repository.get_kit(workspace_id, pattern_kit_id)
        if kit is None:
            raise NotFoundError("PATTERN_KIT_NOT_FOUND", "PatternKit was not found.")
        return kit

    async def _load_sources(
        self,
        workspace_id: UUID,
        creative_dna_version_ids: list[UUID],
    ) -> list[PatternSourceInput]:
        sources: list[PatternSourceInput] = []
        for creative_dna_version_id in creative_dna_version_ids:
            dna_model = await self._dna.get(workspace_id, creative_dna_version_id)
            if dna_model is None:
                raise NotFoundError(
                    "CREATIVE_DNA_NOT_FOUND",
                    "Creative DNA version was not found.",
                )
            if dna_model.status != "completed":
                raise AppError(
                    "PATTERN_KIT_SOURCE_INVALID",
                    "One or more Creative DNA versions are unavailable.",
                )
            try:
                dna = CreativeDnaV1.model_validate(dna_model.dna_json)
            except Exception as exc:
                raise AppError(
                    "PATTERN_KIT_SOURCE_INVALID",
                    "PatternKit requires CreativeDnaV1 source versions.",
                ) from exc
            evidence = await self._evidence.list_for_asset_version(
                workspace_id,
                dna_model.asset_version_id,
            )
            sources.append(
                PatternSourceInput(
                    creative_dna_version_id=dna_model.id,
                    asset_version_id=dna_model.asset_version_id,
                    taxonomy_version=dna_model.taxonomy_version,
                    dna=dna,
                    evidence_by_id=_evidence_by_id(evidence),
                )
            )
        return sources

    async def _create_model_run(
        self,
        *,
        workspace_id: UUID,
        pattern_kit_id: UUID,
        input_summary: dict[str, object],
    ) -> AiModelRunModel:
        input_hash = _hash_json(input_summary)
        return await AiModelRunRepository(self._session).create_running(
            workspace_id=workspace_id,
            processing_job_id=None,
            subject_type="pattern_kit",
            subject_id=pattern_kit_id,
            capability="pattern_kit_extract",
            operation="pattern_kit_extract",
            analysis_mode=self._settings.ai_mode,
            provider=(
                self._settings.ai_provider if self._settings.ai_mode != "fixture" else "fixture"
            ),
            model=_model_name(self._settings),
            prompt_version=PATTERN_KIT_PROMPT_VERSION,
            response_schema_version=PATTERN_KIT_SCHEMA_VERSION,
            schema_version=PATTERN_KIT_SCHEMA_VERSION,
            request_hash=input_hash,
            input_hash=input_hash,
            input_summary=input_summary,
            endpoint_family=(
                "responses"
                if self._settings.ai_mode == "live"
                and self._settings.ai_provider == "openai"
                else None
            ),
            prompt_name=PATTERN_KIT_PROMPT_NAME,
        )

    async def _extract_pattern(
        self,
        *,
        pattern_kit_id: UUID,
        workspace_id: UUID,
        version: int,
        user_id: UUID,
        created_at: datetime,
        data: CreatePatternKitRequest,
        sources: list[PatternSourceInput],
        model_run_id: UUID,
    ) -> tuple[PatternKitV1, StructuredGenerationResult | None]:
        if self._settings.ai_mode == "fixture":
            return (
                build_fixture_pattern_kit(
                    pattern_kit_id=pattern_kit_id,
                    workspace_id=workspace_id,
                    version=version,
                    created_by=user_id,
                    created_at=created_at,
                    request=data,
                    sources=sources,
                    model_run_id=model_run_id,
                ),
                None,
            )
        execution = LivePatternKitProvider(self._settings).extract_with_metadata(
            pattern_kit_id=pattern_kit_id,
            workspace_id=workspace_id,
            version=version,
            created_by=user_id,
            created_at=created_at.isoformat(),
            request=data,
            source_payloads=_source_payloads(sources),
            model_run_id=model_run_id,
            evidence_catalog=_model_evidence_catalog(sources),
            source_version_ids=list(
                dict.fromkeys(source.asset_version_id for source in sources)
            ),
        )
        return execution.output, execution.provider_result

    async def _regenerate_version(
        self,
        *,
        kit: PatternKitModel,
        version_number: int,
        user_id: UUID,
        change_reason: str,
        sources: list[PatternSourceInput],
        latest_pattern: PatternKitV1,
    ) -> tuple[
        PatternKitV1,
        AiModelRunModel,
        StructuredGenerationResult | None,
    ]:
        request = CreatePatternKitRequest(
            name=latest_pattern.name,
            kind=latest_pattern.kind,
            scope=latest_pattern.scope,
            source_creative_dna_version_ids=latest_pattern.source.creative_dna_version_ids,
            primary_category=kit.primary_category or "unknown",
            target_platforms=[str(item) for item in kit.target_platforms_json],
            target_markets=[str(item) for item in kit.target_markets_json],
            objectives=[str(item) for item in kit.objectives_json],
            extraction_mode="ai_assisted",
            review_notes=change_reason,
        )
        model_run = await self._create_model_run(
            workspace_id=kit.workspace_id,
            pattern_kit_id=kit.id,
            input_summary=_input_summary(request, sources),
        )
        try:
            pattern, provider_result = await self._extract_pattern(
                pattern_kit_id=kit.id,
                workspace_id=kit.workspace_id,
                version=version_number,
                user_id=user_id,
                created_at=utc_now(),
                data=request,
                sources=sources,
                model_run_id=model_run.id,
            )
            return pattern, model_run, provider_result
        except AppError as exc:
            await _fail_model_run(self._session, model_run, exc)
            await self._session.commit()
            raise

    async def _complete_model_run(
        self,
        model_run: AiModelRunModel,
        pattern: PatternKitV1,
        evidence_links: list[tuple[UUID, str]],
        provider_result: StructuredGenerationResult | None,
    ) -> None:
        output_summary: dict[str, object] = {
            "sequence_count": len(pattern.sequence),
            "evidence_link_count": len(evidence_links),
            "overall_confidence": pattern.overall_confidence,
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


def _validate_create_pattern(
    pattern: PatternKitV1,
    pattern_kit_id: UUID,
    workspace_id: UUID,
    data: CreatePatternKitRequest,
    sources: list[PatternSourceInput],
) -> None:
    if pattern.id != pattern_kit_id or pattern.workspace_id != workspace_id or pattern.version != 1:
        raise AppError("PATTERN_KIT_CONFLICT", "PatternKit output identity does not match request.")
    if pattern.name != data.name or pattern.kind != data.kind or pattern.scope != data.scope:
        raise AppError("PATTERN_KIT_CONFLICT", "PatternKit output metadata does not match request.")
    if pattern.status != "candidate":
        raise AppError("PATTERN_KIT_CONFLICT", "New PatternKits must start as candidate.")
    source_ids = [source.creative_dna_version_id for source in sources]
    if pattern.source.creative_dna_version_ids != source_ids:
        raise AppError("PATTERN_KIT_SOURCE_INVALID", "PatternKit source IDs changed.")
    _validate_anti_copy(pattern, sources)


def _validate_version_pattern(
    pattern: PatternKitV1,
    kit: PatternKitModel,
    sources: list[PatternSourceInput],
) -> None:
    if pattern.id != kit.id or pattern.workspace_id != kit.workspace_id:
        raise AppError("PATTERN_KIT_CONFLICT", "PatternKit version identity does not match kit.")
    if pattern.version != kit.latest_version + 1:
        raise AppError("PATTERN_KIT_CONFLICT", "PatternKit version number is invalid.")
    if pattern.status != "candidate":
        raise AppError("PATTERN_KIT_CONFLICT", "New PatternKit versions must start as candidate.")
    source_ids = [source.creative_dna_version_id for source in sources]
    if len(source_ids) != len(set(source_ids)):
        raise AppError("PATTERN_KIT_SOURCE_INVALID", "PatternKit source IDs must be unique.")
    if pattern.source.creative_dna_version_ids != source_ids:
        raise AppError("PATTERN_KIT_SOURCE_INVALID", "PatternKit source IDs are invalid.")
    _validate_anti_copy(pattern, sources)


def _validate_and_extract_evidence_links(
    pattern: PatternKitV1,
    sources: list[PatternSourceInput],
) -> list[tuple[UUID, str]]:
    source_by_dna = {source.creative_dna_version_id: source for source in sources}
    refs = _collect_evidence_refs(pattern)
    if not refs:
        raise AppError("PATTERN_KIT_EVIDENCE_INVALID", "PatternKit requires evidence refs.")
    for ref in refs:
        source = source_by_dna.get(ref.creative_dna_version_id)
        if source is None:
            raise AppError("PATTERN_KIT_EVIDENCE_INVALID", "PatternKit references unknown source.")
        if ref.evidence_id not in source.evidence_by_id:
            raise AppError(
                "PATTERN_KIT_EVIDENCE_INVALID",
                "PatternKit references evidence outside the source workspace.",
            )
        if not _field_exists(source.dna.model_dump(), ref.feature_path):
            raise AppError(
                "PATTERN_KIT_EVIDENCE_INVALID",
                "PatternKit references a missing Creative DNA field.",
            )
    return _evidence_links(pattern)


def _collect_evidence_refs(pattern: PatternKitV1) -> list[PatternEvidenceRefV1]:
    refs: list[PatternEvidenceRefV1] = []
    for item in _walk(pattern.model_dump(mode="json")):
        if isinstance(item, dict) and {"evidence_id", "feature_path"}.issubset(item.keys()):
            refs.append(PatternEvidenceRefV1.model_validate(item))
    return refs


def _evidence_links(pattern: PatternKitV1) -> list[tuple[UUID, str]]:
    links: list[tuple[UUID, str]] = []
    seen: set[tuple[UUID, str]] = set()
    for ref in _collect_evidence_refs(pattern):
        key = (ref.evidence_id, ref.feature_path)
        if key in seen:
            continue
        seen.add(key)
        links.append(key)
    return links


def _walk(value: object) -> Iterator[object]:
    if isinstance(value, dict):
        yield value
        for item in value.values():
            yield from _walk(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk(item)


def _field_exists(dna_json: dict[str, object], path: str) -> bool:
    current: object = dna_json
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return False
        current = current[part]
    return True


def _validate_anti_copy(pattern: PatternKitV1, sources: list[PatternSourceInput]) -> None:
    rendered = json.dumps(pattern.model_dump(mode="json"), sort_keys=True).lower()
    for source in sources:
        dna = source.dna.model_dump()
        for path in (
            "opening.hook_text",
            "cta.spoken_text",
            "cta.overlay_text",
        ):
            payload = _field_payload(dna, path)
            text = str(payload.get("value") or "").strip()
            if len(text.split()) >= 8 and text.lower() in rendered:
                raise AppError(
                    "PATTERN_KIT_CONFLICT",
                    "PatternKit cannot emit exact source script as reusable instruction.",
                )


def _field_payload(dna_json: dict[str, object], path: str) -> dict[str, object]:
    current: object = dna_json
    for part in path.split("."):
        if not isinstance(current, dict):
            return {}
        current = current.get(part)
    return current if isinstance(current, dict) else {}


def _validate_action_transition(
    current_status: str,
    action: str,
    reason: str | None,
) -> None:
    if action == "validated" and not reason:
        raise AppError(
            "PATTERN_KIT_VALIDATION_REASON_REQUIRED",
            "Validating a PatternKit requires an explicit human reason.",
        )
    allowed = {
        "candidate": {"reviewed", "archived"},
        "reviewed": {"validated", "deprecated", "archived"},
        "validated": {"deprecated", "archived"},
        "deprecated": {"archived", "restored"},
        "archived": {"restored"},
    }
    if action not in allowed.get(current_status, set()):
        raise ConflictError(
            "PATTERN_KIT_STATE_CONFLICT",
            "PatternKit action is not valid for the current status.",
        )


def _event_type_for_action(action: str) -> ProductEventType | None:
    if action == "reviewed":
        return "pattern_kit_reviewed"
    if action == "validated":
        return "pattern_kit_validated"
    return None


def _reject_unsupported_kind(data: CreatePatternKitRequest) -> None:
    if data.kind == "category_playbook":
        raise AppError(
            "PATTERN_KIT_SOURCE_INVALID",
            "Category playbooks are not enabled for private beta.",
        )


def _user_version_pattern(
    pattern: PatternKitV1,
    kit: PatternKitModel,
    version_number: int,
    user_id: UUID,
) -> PatternKitV1:
    return pattern.model_copy(
        update={
            "id": kit.id,
            "workspace_id": kit.workspace_id,
            "version": version_number,
            "status": "candidate",
            "created_by": user_id,
            "created_at": utc_now(),
        }
    )


def _detail_response(
    kit: PatternKitModel,
    version: PatternKitVersionModel,
) -> PatternKitDetailResponse:
    return PatternKitDetailResponse(
        kit=PatternKitSummaryResponse.model_validate(kit),
        latest_version=_version_response(version),
    )


def _version_response(version: PatternKitVersionModel) -> PatternKitVersionResponse:
    return PatternKitVersionResponse(
        id=version.id,
        pattern_kit_id=version.pattern_kit_id,
        workspace_id=version.workspace_id,
        version=version.version,
        parent_version=version.parent_version,
        change_reason=version.change_reason,
        schema_version=version.schema_version,
        pattern=_pattern_from_version(version),
        overall_confidence=version.overall_confidence,
        model_run_id=version.model_run_id,
        created_by_user_id=version.created_by_user_id,
        created_at=version.created_at,
    )


def _pattern_from_version(version: PatternKitVersionModel) -> PatternKitV1:
    return PatternKitV1.model_validate(version.pattern_json)


def _evidence_by_id(evidence: list[EvidenceItemModel]) -> dict[UUID, PatternEvidenceInput]:
    return {
        item.id: PatternEvidenceInput(
            id=item.id,
            asset_version_id=item.asset_version_id,
            evidence_type=item.evidence_type,
            source=item.source,
            start_ms=item.start_ms,
            end_ms=item.end_ms,
            value_json=item.value_json,
            confidence=float(item.confidence) if item.confidence is not None else None,
        )
        for item in evidence
    }


def _source_payloads(sources: list[PatternSourceInput]) -> list[dict[str, object]]:
    return [
        {
            "creative_dna_version_id": str(source.creative_dna_version_id),
            "asset_version_id": str(source.asset_version_id),
            "taxonomy_version": source.taxonomy_version,
            "dna": source.dna.model_dump(mode="json"),
            "evidence_feature_paths": _evidence_feature_paths(
                source.dna.model_dump(mode="json")
            ),
            "evidence": [
                {
                    "evidence_id": str(evidence.id),
                    "evidence_type": evidence.evidence_type,
                    "source": evidence.source,
                    "start_ms": evidence.start_ms,
                    "end_ms": evidence.end_ms,
                }
                for evidence in source.evidence_by_id.values()
            ],
        }
        for source in sources
    ]


def _model_evidence_catalog(
    sources: list[PatternSourceInput],
) -> list[EvidenceItemForModelV1]:
    return [
        EvidenceItemForModelV1(
            evidence_id=evidence.id,
            source_version_id=evidence.asset_version_id,
            evidence_type=evidence.evidence_type,
            start_ms=evidence.start_ms,
            end_ms=evidence.end_ms,
            value=evidence.value_json,
            confidence=evidence.confidence,
            source=evidence.source,
        )
        for source in sources
        for evidence in source.evidence_by_id.values()
    ]


def _input_summary(
    data: CreatePatternKitRequest,
    sources: list[PatternSourceInput],
) -> dict[str, object]:
    return {
        "name": data.name,
        "kind": data.kind,
        "scope": data.scope,
        "source_creative_dna_version_ids": [
            str(source.creative_dna_version_id) for source in sources
        ],
        "primary_category": data.primary_category,
        "target_platforms": data.target_platforms,
        "target_markets": data.target_markets,
        "objectives": data.objectives,
    }


def _hash_json(payload: dict[str, object]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def _model_name(settings: Settings) -> str:
    if settings.ai_mode == "fixture":
        return "fixture_pattern_kit_v1"
    if settings.ai_provider == "openai":
        return settings.resolve_openai_model("pattern_kit_extract")
    return settings.ai_text_model or "unconfigured"


async def _fail_model_run(
    session: AsyncSession,
    model_run: AiModelRunModel,
    error: AppError,
) -> None:
    http_status = error.details.get("http_status")
    provider_request_id = error.details.get("provider_request_id")
    repair_attempt_count = error.details.get("repair_attempt_count")
    await AiModelRunRepository(session).fail(
        model_run,
        error.code,
        error.message,
        http_status=http_status if isinstance(http_status, int) else None,
        safe_error_message=error.message,
        provider_request_id=(
            provider_request_id if isinstance(provider_request_id, str) else None
        ),
        repair_attempt_count=(
            repair_attempt_count if isinstance(repair_attempt_count, int) else None
        ),
    )
