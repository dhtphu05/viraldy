from __future__ import annotations

import hashlib
import json
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from viraldy.modules.assets.public import AssetQueries, AssetRepository, AssetVersionReference
from viraldy.modules.jobs.public import (
    get_existing_idempotent_job,
    get_processing_job,
    request_mvp_job,
)
from viraldy.modules.media_analysis.public import EvidenceItemModel, EvidenceQueries
from viraldy.modules.product_events.public import ProductEventPublisher
from viraldy.modules.products.public import ProductContextSnapshot, ProductQueries
from viraldy.modules.tiktok_scorer.models import TikTokScoreProfileModel, TikTokScoreRunModel
from viraldy.modules.tiktok_scorer.repository import (
    TikTokScoreListFilters,
    TikTokScoreRepository,
)
from viraldy.modules.tiktok_scorer.schemas import (
    CreateTikTokScoreRequest,
    CreateTikTokScoreResponse,
    CreateTikTokScoreRevisionRequest,
    CreateTikTokScoreRevisionResponse,
    RecordTikTokFixActionRequest,
    RecordTikTokFixActionResponse,
    RecordTikTokScorerEventRequest,
    RecordTikTokScorerEventResponse,
    RecordTikTokScorerOpenedRequest,
    TikTokEvidencePreviewResponse,
    TikTokFixActionEventResponse,
    TikTokFixActionListResponse,
    TikTokFixActionResponse,
    TikTokScoreComparisonResponse,
    TikTokScoreDetailResponse,
    TikTokScoreDimensionResponse,
    TikTokScoreFindingResponse,
    TikTokScoreListItemResponse,
    TikTokScoreListResponse,
    TikTokScoreProfileListResponse,
    TikTokScoreProfileResponse,
    TikTokScoreRunResponse,
)
from viraldy.modules.viral_kits.public import ViralKitQueries, ViralKitVersionSnapshot
from viraldy.platform.config.settings import Settings
from viraldy.shared.errors.base import AppError, ConflictError, NotFoundError

_FIX_PRODUCT_EVENTS = {
    "accepted": "tiktok_fix_accepted",
    "rejected": "tiktok_fix_rejected",
    "sent_to_creator": "tiktok_fix_sent_to_creator",
    "sent_to_editor": "tiktok_fix_sent_to_editor",
    "marked_completed": "tiktok_fix_marked_completed",
    "verified_after_revision": "tiktok_action_verified_after_revision",
}


class TikTokScoreService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings
        self._repository = TikTokScoreRepository(session)
        self._assets = AssetRepository(session)
        self._asset_queries = AssetQueries(session)
        self._products = ProductQueries(session)
        self._directions = ViralKitQueries(session)
        self._evidence = EvidenceQueries(session)

    async def create(
        self,
        workspace_id: UUID,
        data: CreateTikTokScoreRequest,
        idempotency_key: str | None,
        actor_user_id: UUID | None = None,
    ) -> CreateTikTokScoreResponse:
        effective_key = idempotency_key or data.idempotency_key
        existing = await self._existing_create_response(workspace_id, effective_key)
        if existing is not None:
            return existing

        asset = await self._resolve_asset_version(workspace_id, data)
        profile = await self._require_profile(workspace_id, data.score_profile)
        product = await self._load_product_snapshot(workspace_id, data.product_id)
        (
            direction_snapshot,
            direction_version,
            direction_error,
        ) = await self._load_direction_snapshot(
            workspace_id,
            data.creative_direction_context_id,
        )
        product_json, product_hash = _product_snapshot_payload(product)
        try:
            run = await self._repository.create_pending(
                workspace_id=workspace_id,
                asset_id=asset.asset_id,
                asset_version_id=asset.asset_version_id,
                analysis_mode=self._settings.ai_mode,
                product_id=data.product_id,
                score_mode=data.score_mode,
                intended_use=data.intended_use,
                score_profile=profile.code,
                score_profile_version=profile.profile_version,
                score_profile_id=profile.id,
                profile_selection_mode=data.profile_selection_mode,
                profile_selection_confidence=data.profile_selection_confidence,
                alternative_profiles=data.alternative_profiles,
                profile_evidence_ids=data.profile_evidence_ids,
                product_context_snapshot=product_json,
                product_context_snapshot_hash=product_hash,
                product_context_schema_version=(
                    product.context_schema_version if product is not None else None
                ),
                product_context_version=(
                    product.product_context_version if product is not None else None
                ),
                media_checksum_sha256=asset.checksum_sha256,
                creative_direction_context_id=data.creative_direction_context_id,
                creative_direction_context_snapshot=direction_snapshot,
                creative_direction_context_version=direction_version,
                creative_direction_lookup_error=direction_error,
                idempotency_key=effective_key,
            )
        except IntegrityError:
            await self._session.rollback()
            existing = await self._existing_create_response(workspace_id, effective_key)
            if existing is not None:
                return existing
            raise

        job = await request_mvp_job(
            self._session,
            workspace_id,
            "tiktok_score_run",
            run.id,
            "tiktok_score_run",
            _job_input(run, data.objective, actor_user_id, data),
            effective_key,
        )
        if job.subject_id != run.id:
            run = await self._require_run(workspace_id, job.subject_id)
        await self._repository.attach_job(run, job.id, job.stage)
        await self._session.commit()
        await self._session.refresh(run)
        await self._record_event_best_effort(
            event_type="tiktok_score_started",
            run=run,
            actor_user_id=actor_user_id,
            extra={"processing_job_id": str(job.id)},
        )
        return _create_response(run, job)

    async def list(
        self,
        workspace_id: UUID,
        *,
        status: str | None = None,
        score_mode: str | None = None,
        score_profile: str | None = None,
        product_id: UUID | None = None,
        intended_use: str | None = None,
        decision: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        search: str | None = None,
        sort: str = "created_at_desc",
        limit: int = 50,
        offset: int = 0,
    ) -> TikTokScoreListResponse:
        filters = TikTokScoreListFilters(
            status=status,
            score_mode=score_mode,
            score_profile=score_profile,
            product_id=product_id,
            intended_use=intended_use,
            decision=decision,
            created_from=created_from,
            created_to=created_to,
            search=search,
            sort=sort,
            limit=limit,
            offset=offset,
        )
        rows, total = await self._repository.list_runs(workspace_id, filters)
        items = [
            TikTokScoreListItemResponse(
                **TikTokScoreRunResponse.model_validate(row.run).model_dump(),
                asset_filename=row.asset_filename,
                asset_name=row.asset_filename,
                product_name=_product_name(row.run.product_context_snapshot_json),
                revision_count=row.revision_count,
                last_updated_at=row.run.updated_at,
            )
            for row in rows
        ]
        return TikTokScoreListResponse(items=items, total=total, limit=limit, offset=offset)

    async def get(self, workspace_id: UUID, score_run_id: UUID) -> TikTokScoreDetailResponse:
        run = await self._require_run(workspace_id, score_run_id)
        asset = await self._asset_queries.get_version_reference(
            workspace_id,
            run.asset_version_id,
        )
        if asset is None:
            raise NotFoundError("ASSET_VERSION_NOT_FOUND", "Asset version was not found.")
        lineage = await self._repository.get_lineage_metadata(workspace_id, score_run_id)
        dimensions = await self._repository.list_dimensions(workspace_id, score_run_id)
        findings = await self._repository.list_findings(workspace_id, score_run_id)
        fixes = await self._repository.list_fix_actions(workspace_id, score_run_id)
        evidence = await self._evidence.list_for_asset_version(
            workspace_id,
            run.asset_version_id,
        )
        job = (
            await get_processing_job(self._session, workspace_id, run.processing_job_id)
            if run.processing_job_id is not None
            else None
        )
        return TikTokScoreDetailResponse(
            score_run=TikTokScoreRunResponse.model_validate(run),
            job=job,
            dimensions=[TikTokScoreDimensionResponse.model_validate(item) for item in dimensions],
            findings=[TikTokScoreFindingResponse.model_validate(item) for item in findings],
            fix_actions=[TikTokFixActionResponse.model_validate(item) for item in fixes],
            evidence=[_evidence_preview(item) for item in evidence],
            asset_filename=asset.original_filename,
            asset_name=asset.original_filename,
            product_name=_product_name(run.product_context_snapshot_json),
            revision_count=lineage.revision_count,
            comparison_ids=lineage.comparison_ids,
        )

    async def list_fixes(
        self,
        workspace_id: UUID,
        score_run_id: UUID,
    ) -> TikTokFixActionListResponse:
        await self._require_run(workspace_id, score_run_id)
        fixes = await self._repository.list_fix_actions(workspace_id, score_run_id)
        return TikTokFixActionListResponse(
            score_run_id=score_run_id,
            items=[TikTokFixActionResponse.model_validate(item) for item in fixes],
        )

    async def record_fix_action(
        self,
        workspace_id: UUID,
        score_run_id: UUID,
        fix_action_id: UUID,
        data: RecordTikTokFixActionRequest,
        actor_user_id: UUID,
        idempotency_key: str | None,
    ) -> RecordTikTokFixActionResponse:
        run = await self._require_run(workspace_id, score_run_id)
        fix = await self._repository.get_fix_action(workspace_id, score_run_id, fix_action_id)
        if fix is None:
            raise NotFoundError("TIKTOK_FIX_ACTION_NOT_FOUND", "Fix action was not found.")
        event = await self._repository.record_fix_action_event(
            fix_action=fix,
            actor_user_id=actor_user_id,
            event_type=data.event_type,
            details_json=data.details_json,
            idempotency_key=idempotency_key or data.idempotency_key,
        )
        await self._session.commit()
        await self._session.refresh(fix)
        await self._session.refresh(event)
        analytics_type = _FIX_PRODUCT_EVENTS.get(data.event_type)
        if analytics_type is not None:
            await self._record_event_best_effort(
                event_type=analytics_type,
                run=run,
                actor_user_id=actor_user_id,
                extra={"fix_action_id": str(fix.id)},
            )
        return RecordTikTokFixActionResponse(
            fix_action=TikTokFixActionResponse.model_validate(fix),
            event=TikTokFixActionEventResponse.model_validate(event),
        )

    async def create_revision(
        self,
        workspace_id: UUID,
        score_run_id: UUID,
        data: CreateTikTokScoreRevisionRequest,
        actor_user_id: UUID,
        idempotency_key: str | None,
    ) -> CreateTikTokScoreRevisionResponse:
        parent = await self._require_run(workspace_id, score_run_id)
        if parent.status != "completed":
            raise ConflictError(
                "TIKTOK_SCORE_REVISION_NOT_READY",
                "A revision can be scored after the parent score run completes.",
            )
        asset = await self._asset_queries.get_version_reference(
            workspace_id,
            data.asset_version_id,
        )
        if asset is None:
            raise NotFoundError("ASSET_VERSION_NOT_FOUND", "Asset version was not found.")
        if parent.asset_id is not None and asset.asset_id != parent.asset_id:
            raise AppError(
                "TIKTOK_REVISION_ASSET_MISMATCH",
                "Revision asset version must belong to the parent score asset.",
            )
        if asset.asset_version_id == parent.asset_version_id:
            raise ConflictError(
                "TIKTOK_REVISION_VERSION_UNCHANGED",
                "Revision must use a new immutable asset version.",
            )
        if len(set(data.accepted_fix_action_ids)) != len(data.accepted_fix_action_ids):
            raise AppError(
                "TIKTOK_REVISION_FIX_IDS_DUPLICATED",
                "Accepted fix action IDs must be unique.",
            )
        matched_fixes = await self._repository.count_fix_actions(
            workspace_id,
            parent.id,
            data.accepted_fix_action_ids,
        )
        if matched_fixes != len(data.accepted_fix_action_ids):
            raise AppError(
                "TIKTOK_REVISION_FIX_IDS_INVALID",
                "Accepted fix actions must belong to the parent score run.",
            )

        effective_key = idempotency_key or data.idempotency_key
        existing_job = await get_existing_idempotent_job(
            self._session,
            workspace_id,
            "tiktok_score_run",
            effective_key,
        )
        if existing_job is not None:
            child = await self._require_run(workspace_id, existing_job.subject_id)
            if child.parent_score_run_id != parent.id:
                raise ConflictError(
                    "IDEMPOTENCY_KEY_REUSED",
                    "Idempotency key was already used for a different score run.",
                )
            comparison = await self._repository.get_comparison_for_pair(
                workspace_id,
                parent.id,
                child.id,
            )
            if comparison is None:
                raise AppError(
                    "IDEMPOTENT_COMPARISON_NOT_FOUND",
                    "Existing revision comparison was not found.",
                )
            return _revision_response(child, existing_job, comparison)

        profile_code = data.score_profile or parent.score_profile
        profile = await self._require_profile(workspace_id, profile_code)
        profile_overridden = profile.code != parent.score_profile
        try:
            child = await self._repository.create_pending(
                workspace_id=workspace_id,
                asset_id=asset.asset_id,
                asset_version_id=asset.asset_version_id,
                analysis_mode=parent.analysis_mode,
                product_id=parent.product_id,
                score_mode=parent.score_mode,
                intended_use=parent.intended_use,
                score_profile=profile.code,
                score_profile_version=profile.profile_version,
                score_profile_id=profile.id,
                profile_selection_mode="user_overridden" if profile_overridden else "inherited",
                profile_selection_confidence=None,
                alternative_profiles=[],
                profile_evidence_ids=[],
                product_context_snapshot=parent.product_context_snapshot_json,
                product_context_snapshot_hash=parent.product_context_snapshot_hash,
                product_context_schema_version=parent.product_context_schema_version,
                product_context_version=parent.product_context_version,
                media_checksum_sha256=asset.checksum_sha256,
                creative_direction_context_id=parent.creative_direction_context_id,
                creative_direction_context_snapshot=(
                    parent.creative_direction_context_snapshot_json
                ),
                creative_direction_context_version=parent.creative_direction_context_version,
                creative_direction_lookup_error=parent.creative_direction_lookup_error,
                idempotency_key=effective_key,
                parent_score_run_id=parent.id,
                profile_override_reason=(
                    data.profile_override_reason
                    if profile_overridden
                    else "Inherited from parent score run."
                ),
                policy_pack_versions=parent.policy_pack_versions_json,
                rule_versions=parent.rule_versions_json,
                prompt_versions=parent.prompt_versions_json,
                model_provider_versions=parent.model_provider_versions_json,
            )
            comparison = await self._repository.create_pending_comparison(
                workspace_id=workspace_id,
                before_score_run_id=parent.id,
                after_score_run_id=child.id,
                accepted_fix_action_ids=data.accepted_fix_action_ids,
            )
        except IntegrityError as exc:
            await self._session.rollback()
            existing_job = await get_existing_idempotent_job(
                self._session,
                workspace_id,
                "tiktok_score_run",
                effective_key,
            )
            if existing_job is None:
                raise
            child = await self._require_run(workspace_id, existing_job.subject_id)
            comparison = await self._repository.get_comparison_for_pair(
                workspace_id,
                parent.id,
                child.id,
            )
            if comparison is None:
                raise AppError(
                    "IDEMPOTENT_COMPARISON_NOT_FOUND",
                    "Existing revision comparison was not found.",
                ) from exc
            return _revision_response(child, existing_job, comparison)

        job = await request_mvp_job(
            self._session,
            workspace_id,
            "tiktok_score_run",
            child.id,
            "tiktok_score_run",
            {
                "score_run_id": str(child.id),
                "parent_score_run_id": str(parent.id),
                "comparison_id": str(comparison.id),
                "asset_id": str(asset.asset_id),
                "asset_version_id": str(asset.asset_version_id),
                "product_id": str(parent.product_id) if parent.product_id else None,
                "score_mode": parent.score_mode,
                "score_profile": profile.code,
                "score_profile_version": profile.profile_version,
                "intended_use": parent.intended_use,
                "actor_user_id": str(actor_user_id),
                "accepted_fix_action_ids": [str(value) for value in data.accepted_fix_action_ids],
            },
            effective_key,
        )
        await self._repository.attach_job(child, job.id, job.stage)
        await self._session.commit()
        await self._session.refresh(child)
        await self._record_event_best_effort(
            event_type="tiktok_revision_uploaded",
            run=child,
            actor_user_id=actor_user_id,
            extra={
                "parent_score_run_id": str(parent.id),
                "comparison_id": str(comparison.id),
            },
        )
        return _revision_response(child, job, comparison)

    async def get_comparison(
        self,
        workspace_id: UUID,
        score_run_id: UUID,
        comparison_id: UUID,
    ) -> TikTokScoreComparisonResponse:
        await self._require_run(workspace_id, score_run_id)
        comparison = await self._repository.get_comparison(
            workspace_id,
            score_run_id,
            comparison_id,
        )
        if comparison is None:
            raise NotFoundError(
                "TIKTOK_SCORE_COMPARISON_NOT_FOUND",
                "TikTok score comparison was not found.",
            )
        before_run = await self._require_run(workspace_id, comparison.before_score_run_id)
        after_run = await self._require_run(workspace_id, comparison.after_score_run_id)
        before_asset = await self._asset_queries.get_version_reference(
            workspace_id,
            before_run.asset_version_id,
        )
        after_asset = await self._asset_queries.get_version_reference(
            workspace_id,
            after_run.asset_version_id,
        )
        if before_asset is None or after_asset is None:
            raise NotFoundError("ASSET_VERSION_NOT_FOUND", "Asset version was not found.")
        return TikTokScoreComparisonResponse.model_validate(comparison).model_copy(
            update={
                "before_asset_version_id": before_run.asset_version_id,
                "after_asset_version_id": after_run.asset_version_id,
                "before_asset_filename": before_asset.original_filename,
                "after_asset_filename": after_asset.original_filename,
                "before_product_name": _product_name(
                    before_run.product_context_snapshot_json
                ),
                "after_product_name": _product_name(after_run.product_context_snapshot_json),
            }
        )

    async def list_profiles(self, workspace_id: UUID) -> TikTokScoreProfileListResponse:
        profiles = await self._repository.list_profiles(workspace_id)
        unique_profiles: dict[str, TikTokScoreProfileModel] = {}
        for profile in profiles:
            unique_profiles.setdefault(profile.code, profile)
        return TikTokScoreProfileListResponse(
            items=[
                TikTokScoreProfileResponse.model_validate(profile)
                for profile in unique_profiles.values()
            ]
        )

    async def record_product_event(
        self,
        workspace_id: UUID,
        score_run_id: UUID,
        data: RecordTikTokScorerEventRequest,
        actor_user_id: UUID,
    ) -> RecordTikTokScorerEventResponse:
        run = await self._require_run(workspace_id, score_run_id)
        if data.asset_version_id is not None and data.asset_version_id != run.asset_version_id:
            raise AppError(
                "TIKTOK_EVENT_ASSET_VERSION_INVALID",
                "Event asset version must match the score run.",
            )
        if data.fix_action_id is not None:
            fix = await self._repository.get_fix_action(
                workspace_id,
                score_run_id,
                data.fix_action_id,
            )
            if fix is None:
                raise NotFoundError("TIKTOK_FIX_ACTION_NOT_FOUND", "Fix action was not found.")
        if data.finding_id is not None:
            finding_ids = {
                finding.id
                for finding in await self._repository.list_findings(workspace_id, score_run_id)
            }
            if data.finding_id not in finding_ids:
                raise NotFoundError("TIKTOK_FINDING_NOT_FOUND", "Finding was not found.")
        if data.evidence_id is not None:
            evidence_ids = {
                evidence.id
                for evidence in await self._evidence.list_for_asset_version(
                    workspace_id,
                    run.asset_version_id,
                )
            }
            if data.evidence_id not in evidence_ids:
                raise NotFoundError("TIKTOK_EVIDENCE_NOT_FOUND", "Evidence was not found.")
        if data.comparison_id is not None:
            comparison = await self._repository.get_comparison(
                workspace_id,
                score_run_id,
                data.comparison_id,
            )
            if comparison is None:
                raise NotFoundError(
                    "TIKTOK_SCORE_COMPARISON_NOT_FOUND",
                    "TikTok score comparison was not found.",
                )
        return await self._record_event_best_effort(
            event_type=data.event_type,
            run=run,
            actor_user_id=actor_user_id,
            extra={
                key: str(value)
                for key, value in {
                    "fix_action_id": data.fix_action_id,
                    "finding_id": data.finding_id,
                    "evidence_id": data.evidence_id,
                    "comparison_id": data.comparison_id,
                }.items()
                if value is not None
            },
        )

    async def record_opened_event(
        self,
        workspace_id: UUID,
        data: RecordTikTokScorerOpenedRequest,
        actor_user_id: UUID,
    ) -> RecordTikTokScorerEventResponse:
        payload: dict[str, object] = {
            key: value
            for key, value in {
                "score_mode": data.score_mode,
                "score_profile": data.score_profile,
                "intended_use": data.intended_use,
            }.items()
            if value is not None
        }
        try:
            event = await ProductEventPublisher(self._session).record(
                event_type=data.event_type,
                workspace_id=workspace_id,
                actor_user_id=actor_user_id,
                subject_type="workspace",
                subject_id=workspace_id,
                payload_json=payload,
            )
            await self._session.commit()
        except Exception:
            await self._session.rollback()
            return RecordTikTokScorerEventResponse(recorded=False)
        return RecordTikTokScorerEventResponse(recorded=True, event_id=event.id)

    async def _resolve_asset_version(
        self,
        workspace_id: UUID,
        data: CreateTikTokScoreRequest,
    ) -> AssetVersionReference:
        if data.asset_version_id is not None:
            asset = await self._asset_queries.get_version_reference(
                workspace_id,
                data.asset_version_id,
            )
            if asset is None:
                raise NotFoundError("ASSET_VERSION_NOT_FOUND", "Asset version was not found.")
            if data.asset_id is not None and data.asset_id != asset.asset_id:
                raise AppError(
                    "ASSET_VERSION_MISMATCH",
                    "Asset version does not belong to the provided asset.",
                )
        else:
            if data.asset_id is None:
                raise AppError(
                    "ASSET_REFERENCE_REQUIRED",
                    "An asset version or legacy asset is required.",
                )
            model = await self._assets.get(workspace_id, data.asset_id)
            if model is None:
                raise NotFoundError("ASSET_NOT_FOUND", "Asset was not found.")
            version = await self._assets.get_current_version_in_workspace(
                workspace_id,
                data.asset_id,
            )
            if version is None:
                raise AppError("ASSET_VERSION_NOT_FOUND", "Asset version was not found.")
            asset = AssetVersionReference(
                asset_id=model.id,
                asset_version_id=version.id,
                workspace_id=model.workspace_id,
                product_id=model.product_id,
                original_filename=version.original_filename,
                checksum_sha256=version.checksum_sha256,
                validation_status=version.validation_status,
            )
        if asset.validation_status not in {"uploaded", "valid", "processed"}:
            raise AppError("ASSET_VERSION_NOT_READY", "Asset version is not ready for scoring.")
        return asset

    async def _require_profile(
        self,
        workspace_id: UUID,
        code: str,
    ) -> TikTokScoreProfileModel:
        profile = await self._repository.get_profile(workspace_id, code)
        if profile is None:
            raise NotFoundError("TIKTOK_SCORE_PROFILE_NOT_FOUND", "Score profile was not found.")
        return profile

    async def _load_product_snapshot(
        self,
        workspace_id: UUID,
        product_id: UUID | None,
    ) -> ProductContextSnapshot | None:
        if product_id is None:
            return None
        product = await self._products.get_product_context_snapshot(workspace_id, product_id)
        if product is None:
            raise NotFoundError("PRODUCT_NOT_FOUND", "Product was not found.")
        return product

    async def _load_direction_snapshot(
        self,
        workspace_id: UUID,
        direction_id: UUID | None,
    ) -> tuple[dict[str, object] | None, int | None, str | None]:
        if direction_id is None:
            return None, None, None
        try:
            try:
                snapshot = await self._directions.get_version_snapshot_by_id(
                    workspace_id,
                    direction_id,
                )
            except NotFoundError:
                snapshot = await self._directions.get_version_snapshot(
                    workspace_id,
                    direction_id,
                )
            context = _direction_context(snapshot)
            if context is None:
                return None, snapshot.version, "DIRECTION_NOT_SELECTED"
            return context, snapshot.version, None
        except Exception:
            return None, None, "DIRECTION_LOOKUP_FAILED"

    async def _existing_create_response(
        self,
        workspace_id: UUID,
        idempotency_key: str | None,
    ) -> CreateTikTokScoreResponse | None:
        existing_job = await get_existing_idempotent_job(
            self._session,
            workspace_id,
            "tiktok_score_run",
            idempotency_key,
        )
        if existing_job is None:
            return None
        run = await self._require_run(workspace_id, existing_job.subject_id)
        if run.processing_job_id is None:
            await self._repository.attach_job(run, existing_job.id, existing_job.stage)
            await self._session.commit()
            await self._session.refresh(run)
        return _create_response(run, existing_job)

    async def _require_run(
        self,
        workspace_id: UUID,
        score_run_id: UUID,
    ) -> TikTokScoreRunModel:
        run = await self._repository.get(workspace_id, score_run_id)
        if run is None:
            raise NotFoundError(
                "TIKTOK_SCORE_RUN_NOT_FOUND",
                "TikTok score run was not found.",
            )
        return run

    async def _record_event_best_effort(
        self,
        *,
        event_type: str,
        run: TikTokScoreRunModel,
        actor_user_id: UUID | None,
        extra: dict[str, object] | None = None,
    ) -> RecordTikTokScorerEventResponse:
        payload: dict[str, object] = {
            "score_run_id": str(run.id),
            "asset_version_id": str(run.asset_version_id),
            "score_mode": run.score_mode,
            "score_profile": run.score_profile,
            "intended_use": run.intended_use,
            **(extra or {}),
        }
        try:
            event = await ProductEventPublisher(self._session).record(
                event_type=event_type,  # type: ignore[arg-type]
                workspace_id=run.workspace_id,
                actor_user_id=actor_user_id,
                subject_type="tiktok_score_run",
                subject_id=run.id,
                payload_json=payload,
            )
            await self._session.commit()
        except Exception:
            await self._session.rollback()
            return RecordTikTokScorerEventResponse(recorded=False)
        return RecordTikTokScorerEventResponse(recorded=True, event_id=event.id)


def _product_snapshot_payload(
    snapshot: ProductContextSnapshot | None,
) -> tuple[dict[str, object] | None, str | None]:
    if snapshot is None:
        return None, None
    payload = snapshot.model_dump(mode="json")
    context_payload = snapshot.product_context.model_dump(mode="json")
    return payload, _canonical_hash(context_payload)


def _canonical_hash(payload: dict[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _product_name(snapshot: dict[str, object] | None) -> str | None:
    if snapshot is None:
        return None
    product_context = snapshot.get("product_context")
    if not isinstance(product_context, dict):
        return None
    identity = product_context.get("identity")
    if not isinstance(identity, dict):
        return None
    name = identity.get("name")
    return name if isinstance(name, str) and name.strip() else None


def _direction_context(snapshot: ViralKitVersionSnapshot) -> dict[str, object] | None:
    kit = snapshot.viral_kit
    if kit.selected_concept_id is None:
        return None
    concept = next(
        (candidate for candidate in kit.concepts if candidate.id == kit.selected_concept_id),
        None,
    )
    if concept is None:
        return None
    product_context = kit.product.snapshot_json.model_dump(mode="json")
    governance = kit.product.snapshot_json.governance
    allowed_claims = [
        claim.text
        for claim in governance.claims
        if claim.rule_type in {"allowed", "allowed_with_qualification"}
    ]
    return {
        "source_type": "viral_kit",
        "source_id": str(snapshot.viral_kit_id),
        "source_version": snapshot.version,
        "source_status": snapshot.status,
        "concept_id": concept.id,
        "product_snapshot_hash": _canonical_hash(product_context),
        "objective": kit.objective,
        "market": kit.target_market,
        "buyer_context": kit.buyer_context.model_dump(mode="json"),
        "message_angle": concept.creative_angle,
        "hook_mechanism": concept.hook.hook_type,
        "narrative_sequence": [concept.narrative_structure],
        "demo_mechanism": concept.demo_mechanism,
        "proof_mechanism": concept.proof_mechanism,
        "cta_strategy": concept.cta_strategy,
        "keep": [decision.element_path for decision in kit.adaptation_plan.keep],
        "change": [decision.element_path for decision in kit.adaptation_plan.change],
        "avoid": [decision.element_path for decision in kit.adaptation_plan.avoid],
        "allowed_claims": allowed_claims,
        "prohibited_claims": [
            *kit.constraints.governance.prohibited_claims,
            *concept.claims_to_avoid,
        ],
        "required_disclosures": [
            *kit.constraints.governance.required_disclosures,
            *concept.required_disclosures,
        ],
        "expected_learning": concept.expected_learning,
    }


def _job_input(
    run: TikTokScoreRunModel,
    objective: str,
    actor_user_id: UUID | None,
    request: CreateTikTokScoreRequest,
) -> dict[str, object]:
    return {
        "score_run_id": str(run.id),
        "asset_id": str(run.asset_id),
        "asset_version_id": str(run.asset_version_id),
        "product_id": str(run.product_id) if run.product_id else None,
        "score_mode": run.score_mode,
        "score_profile": run.score_profile,
        "score_profile_version": run.score_profile_version,
        "intended_use": run.intended_use,
        "objective": objective,
        "creative_direction_context_id": (
            str(run.creative_direction_context_id) if run.creative_direction_context_id else None
        ),
        "actor_user_id": str(actor_user_id) if actor_user_id else None,
        "target_query": request.target_query,
        "target_buyer_question": request.target_buyer_question,
        "selected_search_topic": request.selected_search_topic,
        "content_gap_topic": request.content_gap_topic,
        "search_context": {
            "target_query": request.target_query,
            "target_buyer_question": request.target_buyer_question,
            "selected_search_topic": request.selected_search_topic,
            "content_gap_topic": request.content_gap_topic,
        },
    }


def _create_response(run: TikTokScoreRunModel, job: Any) -> CreateTikTokScoreResponse:
    return CreateTikTokScoreResponse(
        score_run=TikTokScoreRunResponse.model_validate(run),
        job=job,
        run_id=run.id,
        job_id=job.id,
        status=job.status,
        current_stage=job.stage,
    )


def _revision_response(
    run: TikTokScoreRunModel,
    job: Any,
    comparison: Any,
) -> CreateTikTokScoreRevisionResponse:
    return CreateTikTokScoreRevisionResponse(
        score_run=TikTokScoreRunResponse.model_validate(run),
        job=job,
        comparison=TikTokScoreComparisonResponse.model_validate(comparison),
        run_id=run.id,
        job_id=job.id,
        comparison_id=comparison.id,
        status=job.status,
        current_stage=job.stage,
    )


def _evidence_preview(evidence: EvidenceItemModel) -> TikTokEvidencePreviewResponse:
    return TikTokEvidencePreviewResponse(
        id=evidence.id,
        evidence_type=evidence.evidence_type,
        source=evidence.source,
        start_ms=evidence.start_ms,
        end_ms=evidence.end_ms,
        value_summary_json=_safe_summary(evidence.value_json),
        confidence=(float(evidence.confidence) if evidence.confidence is not None else None),
        frame_available=evidence.frame_storage_key is not None,
    )


def _safe_summary(value: dict[str, object]) -> dict[str, object]:
    return {
        key: _safe_value(item)
        for key, item in value.items()
        if not any(token in key.lower() for token in ("storage_key", "url", "path"))
    }


def _safe_value(value: object) -> object:
    if isinstance(value, str):
        return value[:2000]
    if isinstance(value, list):
        return [_safe_value(item) for item in value[:20]]
    if isinstance(value, dict):
        return _safe_summary(value)
    if isinstance(value, bool | int | float | Decimal) or value is None:
        return value
    return str(value)[:500]
