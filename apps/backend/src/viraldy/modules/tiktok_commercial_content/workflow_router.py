from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select

from viraldy.api.dependencies.auth import CurrentUserDep, DbSession, require_workspace_permission
from viraldy.api.dependencies.request import get_request_id
from viraldy.api.responses.envelope import Envelope, success
from viraldy.modules.tiktok_commercial_content.models import (
    CreativeDirectionModel,
    MarketInsightSnapshotModel,
)
from viraldy.modules.tiktok_commercial_content.workflow import (
    MarketWorkflowService,
    _validate_public_payload,
)
from viraldy.modules.tiktok_commercial_content.workflow_schemas import (
    AnalyticsAttributionRequest,
    AnalyticsEventRequest,
    BatchReviewCreateRequest,
    DirectionSelectRequest,
    FamilyRefreshRequest,
    PatternSummaryRequest,
    SellerResponseRequest,
    SnapshotCreateRequest,
)
from viraldy.platform.auth.policy import Permission
from viraldy.platform.config.settings import Settings, get_settings
from viraldy.shared.errors.base import NotFoundError

router = APIRouter(
    prefix="/workspaces/{workspace_id}/creative-library", tags=["creative-library-workflow"]
)
SettingsDep = Annotated[Settings, Depends(get_settings)]


@router.get("/families", response_model=Envelope)
async def list_families(
    workspace_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.REFERENCE_READ, current_user, db)
    result = await MarketWorkflowService(db, settings).list_families(workspace_id)
    return success(result, request_id)


@router.post("/families/refresh", response_model=Envelope, status_code=202)
async def refresh_families(
    workspace_id: UUID,
    payload: FamilyRefreshRequest,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.ANALYSIS_RUN, current_user, db)
    rows = await MarketWorkflowService(db, settings).refresh_family_candidates(
        workspace_id,
        scope=payload.scope,
        asset_ids=payload.asset_ids or None,
    )
    return success({"candidate_count": len(rows)}, request_id)


@router.get("/families/candidates", response_model=Envelope)
async def list_family_candidates(
    workspace_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    scope: Literal["MARKET", "WORKSPACE"] = Query(default="MARKET"),
    limit: int = Query(default=100, ge=1, le=200),
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.REFERENCE_READ, current_user, db)
    result = await MarketWorkflowService(db, settings).list_family_candidates(
        workspace_id, scope=scope, limit=limit
    )
    return success(result, request_id)


@router.get("/families/{family_id}", response_model=Envelope)
async def get_family(
    workspace_id: UUID,
    family_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.REFERENCE_READ, current_user, db)
    result = await MarketWorkflowService(db, settings).get_family(workspace_id, family_id)
    return success(result, request_id)


@router.post("/patterns/summary", response_model=Envelope)
async def create_pattern(
    workspace_id: UUID,
    payload: PatternSummaryRequest,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.ANALYSIS_RUN, current_user, db)
    row = await MarketWorkflowService(db, settings).create_pattern(workspace_id, payload)
    return success(
        {
            "id": row.id,
            "scope": row.scope,
            "evidence_level": row.evidence_level,
            "sample_size": row.sample_size,
            "limitations": row.limitations,
        },
        request_id,
    )


@router.get("/patterns/summary", response_model=Envelope)
async def list_patterns(
    workspace_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    market: str | None = Query(default=None, max_length=100),
    category: str | None = Query(default=None, max_length=160),
    limit: int = Query(default=50, ge=1, le=100),
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.REFERENCE_READ, current_user, db)
    result = await MarketWorkflowService(db, settings).list_patterns(
        workspace_id, market=market, category=category, limit=limit
    )
    return success(result, request_id)


@router.get("/adaptations/{adaptation_id}/directions", response_model=Envelope)
async def list_directions(
    workspace_id: UUID,
    adaptation_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.ANALYSIS_RUN, current_user, db)
    rows = await MarketWorkflowService(db, settings).list_directions(workspace_id, adaptation_id)
    return success([_direction_payload(row) for row in rows], request_id)


@router.post("/directions/{direction_id}/select", response_model=Envelope)
async def select_direction(
    workspace_id: UUID,
    direction_id: UUID,
    payload: DirectionSelectRequest,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(
        workspace_id, Permission.RECOMMENDATION_ACT, current_user, db
    )
    row = await MarketWorkflowService(db, settings).select_direction(workspace_id, direction_id)
    return success(_direction_payload(row), request_id)


@router.post("/batch-reviews", response_model=Envelope, status_code=202)
async def create_batch(
    workspace_id: UUID,
    payload: BatchReviewCreateRequest,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.ANALYSIS_RUN, current_user, db)
    row = await MarketWorkflowService(db, settings).create_batch(
        workspace_id, current_user.id, payload
    )
    return success({"id": row.id, "status": row.status}, request_id)


@router.get("/batch-reviews/{batch_id}", response_model=Envelope)
async def get_batch(
    workspace_id: UUID,
    batch_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.REFERENCE_READ, current_user, db)
    return success(
        await MarketWorkflowService(db, settings).get_batch(workspace_id, batch_id), request_id
    )


@router.post("/batch-reviews/{batch_id}/start", response_model=Envelope, status_code=202)
async def start_batch(
    workspace_id: UUID,
    batch_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.ANALYSIS_RUN, current_user, db)
    result = await MarketWorkflowService(db, settings).start_batch(
        workspace_id, current_user.id, batch_id
    )
    return success(result, request_id)


@router.post("/batch-review-items/{item_id}/response", response_model=Envelope)
async def respond_to_batch_item(
    workspace_id: UUID,
    item_id: UUID,
    payload: SellerResponseRequest,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(
        workspace_id, Permission.RECOMMENDATION_ACT, current_user, db
    )
    row = await MarketWorkflowService(db, settings).record_response(
        workspace_id, current_user.id, item_id, payload
    )
    return success(
        {"id": row.id, "action": row.seller_final_action, "response": row.seller_response},
        request_id,
    )


@router.post("/snapshots", response_model=Envelope)
async def create_snapshot(
    workspace_id: UUID,
    payload: SnapshotCreateRequest,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.DATA_EXPORT, current_user, db)
    row = await MarketWorkflowService(db, settings).create_snapshot(
        workspace_id, current_user.id, payload
    )
    return success(_snapshot_payload(row), request_id)


@router.post("/snapshots/{snapshot_id}/publish", response_model=Envelope)
async def publish_snapshot(
    workspace_id: UUID,
    snapshot_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.DATA_EXPORT, current_user, db)
    row = await MarketWorkflowService(db, settings).publish_snapshot(
        workspace_id, current_user.id, snapshot_id
    )
    return success(_snapshot_payload(row), request_id)


@router.post("/analytics/attribution", response_model=Envelope)
async def create_attribution(
    workspace_id: UUID,
    payload: AnalyticsAttributionRequest,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.WORKSPACE_READ, current_user, db)
    row = await MarketWorkflowService(db, settings).attribute(
        workspace_id, current_user.id, payload
    )
    return success({"id": row.id, "entry_flow": row.entry_flow, "utm": row.utm_json}, request_id)


@router.post("/analytics/events", response_model=Envelope)
async def track_event(
    workspace_id: UUID,
    payload: AnalyticsEventRequest,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.WORKSPACE_READ, current_user, db)
    row = await MarketWorkflowService(db, settings).track(workspace_id, current_user.id, payload)
    return success({"id": row.id, "event_type": row.event_type}, request_id)


public_router = APIRouter(prefix="/insights", tags=["public-insights"])


@public_router.get("/{slug}", response_model=Envelope)
async def public_snapshot(
    slug: str, db: DbSession, request_id: str = Depends(get_request_id)
) -> Envelope:
    row = await db.scalar(
        select(MarketInsightSnapshotModel).where(
            MarketInsightSnapshotModel.slug == slug,
            MarketInsightSnapshotModel.published_at.is_not(None),
        )
    )
    if row is None:
        raise NotFoundError("SNAPSHOT_NOT_FOUND", "Market insight snapshot was not found.")
    return success(_snapshot_payload(row), request_id)


def _direction_payload(row: CreativeDirectionModel) -> dict[str, object]:
    return {
        "id": row.id,
        "adaptation_run_id": row.adaptation_run_id,
        "direction_number": row.direction_number,
        "title": row.title,
        "payload": row.payload_json,
        "provenance": row.provenance_json,
        "status": row.status,
    }


def _snapshot_payload(row: MarketInsightSnapshotModel) -> dict[str, object]:
    if row.source_scope != "MARKET":
        raise NotFoundError("SNAPSHOT_NOT_FOUND", "Market insight snapshot was not found.")
    payload = {key: value for key, value in row.payload_json.items() if key != "_workspace_id"}
    _validate_public_payload(payload, row.date_range_json)
    return {
        "id": row.id,
        "slug": row.slug,
        "snapshot_type": row.snapshot_type,
        "title": row.title,
        "category": row.category,
        "market": row.market,
        "date_range": row.date_range_json,
        "payload": payload,
        "published_at": row.published_at,
    }
