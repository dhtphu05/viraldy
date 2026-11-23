from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import UTC, date, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from viraldy.modules.assets.repository import AssetRepository
from viraldy.modules.assets.schemas import AssetResponse
from viraldy.modules.media_analysis.models import EvidenceItemModel
from viraldy.modules.product_events.models import ProductEventModel
from viraldy.modules.product_events.repository import ProductEventRepository
from viraldy.modules.references.repository import ReferenceRepository
from viraldy.modules.tiktok_commercial_content.family_engine import CreativeFamilyEngine
from viraldy.modules.tiktok_commercial_content.models import (
    AnalyticsAttributionModel,
    BatchReviewItemModel,
    BatchReviewModel,
    CreativeDirectionModel,
    CreativeFamilyCandidateModel,
    CreativeFamilyMemberModel,
    CreativeFamilyModel,
    CreativeSourceLinkModel,
    DecisionLogModel,
    MarketInsightSnapshotModel,
    PatternEvidenceModel,
)
from viraldy.modules.tiktok_commercial_content.workflow_schemas import (
    AnalyticsAttributionRequest,
    AnalyticsEventRequest,
    BatchReviewCreateRequest,
    PatternSummaryRequest,
    SellerResponseRequest,
    SnapshotCreateRequest,
)
from viraldy.platform.config.settings import Settings
from viraldy.shared.errors.base import AppError, NotFoundError


class MarketWorkflowService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings

    def require(self, flag: str) -> None:
        if not getattr(self._settings, flag):
            raise AppError(
                "FEATURE_UNAVAILABLE", "This market intelligence feature is not enabled.", 503
            )

    async def refresh_family_candidates(
        self,
        workspace_id: UUID,
        *,
        scope: str,
        asset_ids: list[UUID] | None = None,
    ) -> list[CreativeFamilyCandidateModel]:
        self.require("creative_family")
        family_workspace = None if scope == "MARKET" else workspace_id
        return await CreativeFamilyEngine(self._session).refresh(
            scope=scope,
            workspace_id=family_workspace,
            asset_ids=asset_ids,
        )

    async def list_family_candidates(
        self, workspace_id: UUID, *, scope: str, limit: int
    ) -> list[dict[str, object]]:
        self.require("creative_family")
        family_workspace = None if scope == "MARKET" else workspace_id
        rows = await CreativeFamilyEngine(self._session).list_candidates(
            scope=scope, workspace_id=family_workspace, limit=limit
        )
        return [_candidate_payload(row) for row in rows]

    async def list_families(
        self, workspace_id: UUID, scope: str = "MARKET"
    ) -> list[dict[str, object]]:
        self.require("creative_family")
        rows = await self._session.scalars(
            select(CreativeFamilyModel).where(
                CreativeFamilyModel.scope == scope,
                (CreativeFamilyModel.workspace_id == workspace_id)
                if scope == "WORKSPACE"
                else CreativeFamilyModel.workspace_id.is_(None),
            )
        )
        return [_family_payload(row) for row in rows]

    async def get_family(self, workspace_id: UUID, family_id: UUID) -> dict[str, object]:
        self.require("creative_family")
        family = await self._session.get(CreativeFamilyModel, family_id)
        if family is None or (
            family.scope == "WORKSPACE" and family.workspace_id != workspace_id
        ) or (family.scope == "MARKET" and family.workspace_id is not None):
            raise NotFoundError("CREATIVE_FAMILY_NOT_FOUND", "Creative family was not found.")
        members = list(
            await self._session.scalars(
                select(CreativeFamilyMemberModel).where(
                    CreativeFamilyMemberModel.creative_family_id == family_id
                )
            )
        )
        return {
            **_family_payload(family),
            "members": [
                {
                    "asset_id": member.creative_asset_id,
                    "relationship": member.relationship,
                    "similarity_score": member.similarity_score,
                    "signals": member.similarity_evidence,
                }
                for member in members
            ],
        }

    async def get_asset_intelligence(
        self, workspace_id: UUID, asset_id: UUID
    ) -> dict[str, object]:
        asset = await AssetRepository(self._session).get_for_workspace(workspace_id, asset_id)
        if asset is None:
            raise NotFoundError("ASSET_NOT_FOUND", "Creative asset was not found.")
        version = await AssetRepository(self._session).get_current_version_in_workspace(
            workspace_id, asset_id
        )
        source = await self._session.scalar(
            select(CreativeSourceLinkModel).where(
                CreativeSourceLinkModel.creative_asset_id == asset_id
            )
        )
        evidence = []
        if version is not None:
            evidence = list(
                await self._session.scalars(
                    select(EvidenceItemModel)
                    .where(
                        EvidenceItemModel.workspace_id == workspace_id,
                        EvidenceItemModel.asset_version_id == version.id,
                    )
                    .order_by(EvidenceItemModel.start_ms.asc().nulls_last())
                )
            )
        families = list(
            await self._session.scalars(
                select(CreativeFamilyModel)
                .join(
                    CreativeFamilyMemberModel,
                    CreativeFamilyMemberModel.creative_family_id == CreativeFamilyModel.id,
                )
                .where(
                    CreativeFamilyMemberModel.creative_asset_id == asset_id,
                    (CreativeFamilyModel.workspace_id == workspace_id)
                    | (
                        (CreativeFamilyModel.scope == "MARKET")
                        & CreativeFamilyModel.workspace_id.is_(None)
                    ),
                )
                .distinct()
            )
        )
        asset_response = AssetResponse.model_validate(asset)
        if asset.library_scope == "MARKET":
            reference = await ReferenceRepository(self._session).get_by_asset(
                workspace_id, asset_id
            )
            asset_response = asset_response.model_copy(
                update={"product_id": reference.product_id if reference else None}
            )
        return {
            "asset": asset_response.model_dump(mode="json"),
            "version": {
                "id": version.id,
                "validation_status": version.validation_status,
                "detected_mime_type": version.detected_mime_type,
                "duration_ms": version.duration_ms,
            }
            if version is not None
            else None,
            "source": {
                "provider": source.provider,
                "entity_type": source.provider_entity_type,
                "entity_id": source.provider_entity_id,
                "source_url": source.source_url,
                "metadata": source.source_metadata,
            }
            if source is not None
            else None,
            "analysis": {
                "status": asset.processing_status,
                "evidence_count": len(evidence),
                "evidence": [_evidence_payload(item) for item in evidence],
            },
            "families": [_family_payload(row) for row in families],
            "market_signal_only": asset.library_scope == "MARKET",
        }

    async def list_patterns(
        self,
        workspace_id: UUID,
        *,
        market: str | None = None,
        category: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, object]]:
        self.require("market_pattern_evidence")
        statement = select(PatternEvidenceModel).where(
            PatternEvidenceModel.scope == "MARKET",
            PatternEvidenceModel.workspace_id.is_(None),
        )
        if market:
            statement = statement.where(PatternEvidenceModel.market == market)
        if category:
            statement = statement.where(PatternEvidenceModel.category == category)
        rows = list(
            await self._session.scalars(
                statement.order_by(PatternEvidenceModel.created_at.desc()).limit(limit)
            )
        )
        return [
            {
                "id": row.id,
                "scope": row.scope,
                "evidence_level": row.evidence_level,
                "sample_size": row.sample_size,
                "comparable_sample_size": row.comparable_sample_size,
                "market": row.market,
                "category": row.category,
                "date_min": row.date_min,
                "date_max": row.date_max,
                "confidence": row.confidence,
                "recency": row.recency,
                "limitations": row.limitations,
                "metric_summary": row.metric_summary,
            }
            for row in rows
        ]

    async def create_pattern(
        self, workspace_id: UUID, request: PatternSummaryRequest
    ) -> PatternEvidenceModel:
        self.require("market_pattern_evidence")
        asset_count = int(
            await self._session.scalar(
                select(func.count(func.distinct(CreativeFamilyMemberModel.creative_asset_id)))
                .join(
                    CreativeFamilyModel,
                    CreativeFamilyModel.id == CreativeFamilyMemberModel.creative_family_id,
                )
                .where(CreativeFamilyModel.scope == "MARKET")
            )
            or 0
        )
        family_count = int(
            await self._session.scalar(
                select(func.count(func.distinct(CreativeFamilyModel.id))).where(
                    CreativeFamilyModel.scope == "MARKET",
                    CreativeFamilyModel.workspace_id.is_(None),
                )
            )
            or 0
        )
        if asset_count < request.min_assets or family_count < request.min_families:
            raise AppError(
                "INSUFFICIENT_MARKET_SAMPLE",
                "The market sample is below the configured threshold.",
                422,
            )
        pattern = PatternEvidenceModel(
            id=uuid4(),
            scope="MARKET",
            workspace_id=None,
            evidence_level=(
                "MARKET_PREVALENT"
                if asset_count >= request.min_assets and family_count >= request.min_families
                else "OBSERVED"
            ),
            sample_size=asset_count,
            comparable_sample_size=asset_count,
            market=request.market,
            category=request.category,
            confidence="low",
            recency="current_search_window",
            limitations=[
                "Public reach is a market distribution signal, not seller performance.",
                "This pattern cannot support workspace-proven or experiment-supported claims.",
            ],
            metric_summary={"family_count": family_count},
        )
        self._session.add(pattern)
        await self._session.flush()
        await self._session.commit()
        return pattern

    async def create_batch(
        self, workspace_id: UUID, user_id: UUID, request: BatchReviewCreateRequest
    ) -> BatchReviewModel:
        self.require("batch_creative_review")
        if len(request.asset_ids) > self._settings.tiktok_market_batch_size_limit:
            raise AppError("BATCH_LIMIT_REACHED", "The batch exceeds the rollout size limit.", 422)
        review = BatchReviewModel(
            workspace_id=workspace_id,
            product_id=request.product_id,
            objective=request.objective,
            created_by_user_id=user_id,
            status="queued",
        )
        self._session.add(review)
        await self._session.flush()
        for asset_id in dict.fromkeys(request.asset_ids):
            asset = await AssetRepository(self._session).get_for_workspace(workspace_id, asset_id)
            if asset is None:
                raise NotFoundError(
                    "ASSET_NOT_FOUND",
                    "One or more creative assets are not available in this workspace.",
                )
            self._session.add(
                BatchReviewItemModel(batch_review_id=review.id, creative_asset_id=asset_id)
            )
        await ProductEventRepository(self._session).record(
            event_type="batch_review_created",
            workspace_id=workspace_id,
            actor_user_id=user_id,
            subject_type="batch_review",
            subject_id=review.id,
            payload_json={"asset_count": len(request.asset_ids)},
        )
        await self._session.commit()
        return review

    async def get_batch(self, workspace_id: UUID, batch_id: UUID) -> dict[str, object]:
        review = await self._session.scalar(
            select(BatchReviewModel).where(
                BatchReviewModel.id == batch_id, BatchReviewModel.workspace_id == workspace_id
            )
        )
        if review is None:
            raise NotFoundError("BATCH_REVIEW_NOT_FOUND", "Batch review was not found.")
        items = list(
            await self._session.scalars(
                select(BatchReviewItemModel).where(BatchReviewItemModel.batch_review_id == batch_id)
            )
        )
        return {
            "id": review.id,
            "objective": review.objective,
            "status": review.status,
            "summary": review.summary_json,
            "items": [_item_payload(item) for item in items],
        }

    async def start_batch(
        self, workspace_id: UUID, user_id: UUID, batch_id: UUID
    ) -> dict[str, object]:
        review = await self._session.scalar(
            select(BatchReviewModel).where(
                BatchReviewModel.id == batch_id, BatchReviewModel.workspace_id == workspace_id
            )
        )
        if review is None:
            raise NotFoundError("BATCH_REVIEW_NOT_FOUND", "Batch review was not found.")
        items = list(
            await self._session.scalars(
                select(BatchReviewItemModel).where(BatchReviewItemModel.batch_review_id == batch_id)
            )
        )
        counts = {"TEST": 0, "FIX": 0, "RESHOOT": 0, "SKIP": 0, "INSUFFICIENT_EVIDENCE": 0}
        for item in items:
            decision = _recommend_batch_action(item.status)
            item.status = "ready"
            item.decision = decision
            item.recommended_action = decision
            item.priority = "high" if decision in {"FIX", "RESHOOT"} else "normal"
            item.primary_reason = _batch_reason(decision)
            counts[decision] += 1
        review.status = "completed"
        review.summary_json = {
            "file_count": len(items),
            "distinct_ideas": len(items),
            "decisions": counts,
        }
        review.completed_at = datetime.now(UTC)
        await ProductEventRepository(self._session).record(
            event_type="batch_review_completed",
            workspace_id=workspace_id,
            actor_user_id=user_id,
            subject_type="batch_review",
            subject_id=review.id,
            payload_json=review.summary_json,
        )
        await self._session.commit()
        return await self.get_batch(workspace_id, batch_id)

    async def record_response(
        self, workspace_id: UUID, user_id: UUID, item_id: UUID, request: SellerResponseRequest
    ) -> DecisionLogModel:
        item = await self._session.scalar(
            select(BatchReviewItemModel)
            .join(BatchReviewModel, BatchReviewModel.id == BatchReviewItemModel.batch_review_id)
            .where(
                BatchReviewItemModel.id == item_id, BatchReviewModel.workspace_id == workspace_id
            )
        )
        if item is None:
            raise NotFoundError("BATCH_ITEM_NOT_FOUND", "Batch review item was not found.")
        item.decision = request.action
        item.status = "reviewed"
        log = DecisionLogModel(
            workspace_id=workspace_id,
            entity_type="batch_review_item",
            entity_id=item.id,
            recommendation_type="creative_review",
            recommended_action=request.action,
            seller_response=request.response,
            seller_final_action=request.action,
            seller_feedback=request.feedback,
        )
        self._session.add(log)
        await ProductEventRepository(self._session).record(
            event_type="seller_decision_recorded",
            workspace_id=workspace_id,
            actor_user_id=user_id,
            subject_type="batch_review_item",
            subject_id=item.id,
            payload_json={"action": request.action, "response": request.response},
        )
        await self._session.commit()
        return log

    async def create_directions(
        self,
        workspace_id: UUID,
        adaptation_id: UUID,
        result: dict[str, object],
        provenance: dict[str, object],
    ) -> list[CreativeDirectionModel]:
        concepts = result.get("concepts")
        if not isinstance(concepts, list) or len(concepts) != 3:
            raise AppError(
                "DIRECTION_COUNT_INVALID", "Exactly three creative directions are required.", 422
            )
        rows: list[CreativeDirectionModel] = []
        for index, concept in enumerate(concepts, start=1):
            payload = concept if isinstance(concept, dict) else {"value": concept}
            row = CreativeDirectionModel(
                workspace_id=workspace_id,
                adaptation_run_id=adaptation_id,
                direction_number=index,
                title=str(payload.get("title") or f"Direction {index}"),
                payload_json=payload,
                provenance_json=provenance,
            )
            self._session.add(row)
            rows.append(row)
        await self._session.flush()
        return rows

    async def list_directions(
        self, workspace_id: UUID, adaptation_id: UUID
    ) -> list[CreativeDirectionModel]:
        return list(
            await self._session.scalars(
                select(CreativeDirectionModel)
                .where(
                    CreativeDirectionModel.workspace_id == workspace_id,
                    CreativeDirectionModel.adaptation_run_id == adaptation_id,
                )
                .order_by(CreativeDirectionModel.direction_number)
            )
        )

    async def select_direction(
        self, workspace_id: UUID, direction_id: UUID
    ) -> CreativeDirectionModel:
        row = await self._session.scalar(
            select(CreativeDirectionModel).where(
                CreativeDirectionModel.id == direction_id,
                CreativeDirectionModel.workspace_id == workspace_id,
            )
        )
        if row is None:
            raise NotFoundError("DIRECTION_NOT_FOUND", "Creative direction was not found.")
        row.status = "selected"
        row.selected_at = datetime.now(UTC)
        await self._session.commit()
        return row

    async def create_snapshot(
        self, workspace_id: UUID, user_id: UUID, request: SnapshotCreateRequest
    ) -> MarketInsightSnapshotModel:
        self.require("share_market_snapshot")
        _validate_public_payload(request.payload, request.date_range)
        snapshot = MarketInsightSnapshotModel(
            slug=request.slug,
            snapshot_type=request.snapshot_type,
            title=request.title,
            category=request.category,
            market=request.market,
            source_scope="MARKET",
            date_range_json=request.date_range,
            # Private ownership metadata is removed by the snapshot response serializer.
            payload_json={**request.payload, "_workspace_id": str(workspace_id)},
            created_by_user_id=user_id,
        )
        self._session.add(snapshot)
        await self._session.flush()
        await self._session.commit()
        return snapshot

    async def publish_snapshot(
        self, workspace_id: UUID, user_id: UUID, snapshot_id: UUID
    ) -> MarketInsightSnapshotModel:
        self.require("share_market_snapshot")
        snapshot = await self._session.get(MarketInsightSnapshotModel, snapshot_id)
        if (
            snapshot is None
            or snapshot.created_by_user_id != user_id
            or snapshot.payload_json.get("_workspace_id") != str(workspace_id)
            or snapshot.source_scope != "MARKET"
        ):
            raise NotFoundError("SNAPSHOT_NOT_FOUND", "Market snapshot was not found.")
        _validate_public_payload(
            {key: value for key, value in snapshot.payload_json.items() if key != "_workspace_id"},
            snapshot.date_range_json,
        )
        snapshot.published_at = datetime.now(UTC)
        await self._session.commit()
        return snapshot

    async def attribute(
        self, workspace_id: UUID | None, user_id: UUID | None, request: AnalyticsAttributionRequest
    ) -> AnalyticsAttributionModel:
        clean_utm = {
            key: value[:100]
            for key, value in request.utm.items()
            if key in {"utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term"}
        }
        attribution = AnalyticsAttributionModel(
            workspace_id=workspace_id,
            user_id=user_id,
            entry_flow=request.entry_flow,
            utm_json=clean_utm,
        )
        self._session.add(attribution)
        await self._session.commit()
        return attribution

    async def track(
        self, workspace_id: UUID | None, user_id: UUID | None, request: AnalyticsEventRequest
    ) -> ProductEventModel:
        _validate_analytics_payload(request.payload)
        if len(str(request.payload)) > 4000:
            raise AppError("ANALYTICS_PAYLOAD_TOO_LARGE", "Analytics payload is too large.", 422)
        event = ProductEventModel(
            workspace_id=workspace_id,
            actor_user_id=user_id,
            event_type=request.event_type,
            subject_type=request.subject_type,
            subject_id=request.subject_id,
            payload_json=request.payload,
            attribution_id=request.attribution_id,
            entry_flow=request.entry_flow,
            utm_json={},
        )
        self._session.add(event)
        await self._session.commit()
        return event


def _family_payload(row: CreativeFamilyModel) -> dict[str, object]:
    return {
        "id": row.id,
        "scope": row.scope,
        "name": row.name,
        "family_type": row.family_type,
        "status": row.status,
        "confidence": row.confidence,
        "representative_asset_id": row.representative_asset_id,
    }


def _item_payload(row: BatchReviewItemModel) -> dict[str, object]:
    return {
        "id": row.id,
        "asset_id": row.creative_asset_id,
        "status": row.status,
        "decision": row.decision,
        "recommended_action": row.recommended_action,
        "evidence_ids": row.evidence_ids_json,
        "priority": row.priority,
        "primary_reason": row.primary_reason,
    }


def _candidate_payload(row: CreativeFamilyCandidateModel) -> dict[str, object]:
    return {
        "id": row.id,
        "scope": row.scope,
        "workspace_id": row.workspace_id,
        "asset_a_id": row.asset_a_id,
        "asset_b_id": row.asset_b_id,
        "relationship": row.relationship,
        "candidate_score": row.candidate_score,
        "confidence": row.confidence,
        "signals": row.signals_json,
        "reason": row.reason,
        "status": row.status,
    }


def _evidence_payload(row: EvidenceItemModel) -> dict[str, object]:
    return {
        "id": row.id,
        "evidence_type": row.evidence_type,
        "source_type": row.source_type,
        "evidence_scope": row.evidence_scope,
        "value": row.normalized_value_json or row.value_json,
        "start_ms": row.start_ms,
        "end_ms": row.end_ms,
        "confidence": str(row.confidence) if row.confidence is not None else None,
        "provider": row.source_provider or row.provider,
        "observed_at": row.observed_at,
    }


def _recommend_batch_action(status: str) -> str:
    if status in {"failed", "partial"}:
        return "INSUFFICIENT_EVIDENCE"
    if status in {"metadata_only", "not_analyzed", "NOT_ANALYZED"}:
        return "FIX"
    return "TEST"


def _batch_reason(action: str) -> str:
    return {
        "TEST": "No observed blocker is available; keep this as a distinct test hypothesis.",
        "FIX": "The creative needs analysis or an execution fix before comparison.",
        "RESHOOT": "Available evidence is insufficient to verify the required product proof.",
        "SKIP": "This item adds little distinct learning value.",
        "INSUFFICIENT_EVIDENCE": "Analysis is incomplete or failed; do not infer a decision.",
    }[action]


class _PublicSnapshotPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    pattern: str | None = None
    patterns: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    observed_count: int | None = Field(default=None, ge=0)
    sample_size: int | None = Field(default=None, ge=0)
    family_count: int | None = Field(default=None, ge=0)


class _PublicSnapshotDateRange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    min: date | None = None
    max: date | None = None


def _validate_public_payload(
    payload: dict[str, object], date_range: Mapping[str, object] | None = None
) -> None:
    try:
        _PublicSnapshotPayload.model_validate(payload)
        if date_range is not None:
            _PublicSnapshotDateRange.model_validate_json(json.dumps(date_range), strict=True)
    except ValidationError as exc:
        raise AppError(
            "SNAPSHOT_PRIVACY_REJECTED",
            "The snapshot contains workspace-private or sensitive data.",
            422,
        ) from exc


def _validate_analytics_payload(payload: dict[str, object]) -> None:
    forbidden_tokens = {
        "transcript", "media", "video", "audio", "credential", "token", "secret",
        "password", "personal_data", "email", "phone", "phone_number",
    }

    def walk(value: object, key: str = "") -> None:
        normalized_key = key.lower()
        if any(token in normalized_key for token in forbidden_tokens):
            raise AppError(
                "ANALYTICS_SENSITIVE_VALUE",
                "Analytics payload contains a restricted value.",
                422,
            )
        if isinstance(value, str) and len(value) > 500:
            raise AppError("ANALYTICS_VALUE_TOO_LARGE", "Analytics values must be concise.", 422)
        if isinstance(value, dict):
            for child_key, child_value in value.items():
                walk(child_value, str(child_key))
        elif isinstance(value, list):
            for child_value in value:
                walk(child_value, key)

    walk(payload)
