from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, status

from viraldy.api.dependencies.auth import CurrentUserDep, DbSession, require_workspace_permission
from viraldy.api.dependencies.request import get_request_id
from viraldy.api.responses.envelope import Envelope, success
from viraldy.modules.tiktok_scorer.schemas import (
    CreateTikTokScoreRequest,
    CreateTikTokScoreRevisionRequest,
    RecordTikTokFixActionRequest,
    RecordTikTokScorerEventRequest,
    RecordTikTokScorerOpenedRequest,
)
from viraldy.modules.tiktok_scorer.service import TikTokScoreService
from viraldy.platform.auth.policy import Permission
from viraldy.platform.config.settings import Settings, get_settings

router = APIRouter()
scores_router = APIRouter(
    prefix="/workspaces/{workspace_id}/tiktok-scores",
    tags=["tiktok-scores"],
)
profiles_router = APIRouter(
    prefix="/workspaces/{workspace_id}/tiktok-score-profiles",
    tags=["tiktok-scores"],
)
SettingsDep = Annotated[Settings, Depends(get_settings)]
SortOrder = Literal[
    "created_at_desc",
    "created_at_asc",
    "updated_at_desc",
    "updated_at_asc",
    "score_desc",
    "score_asc",
]


@scores_router.post("", status_code=status.HTTP_202_ACCEPTED, response_model=Envelope)
async def create_score(
    workspace_id: UUID,
    payload: CreateTikTokScoreRequest,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(
        workspace_id,
        Permission.ANALYSIS_RUN,
        current_user,
        db,
    )
    result = await TikTokScoreService(db, settings).create(
        workspace_id,
        payload,
        idempotency_key,
        current_user.id,
    )
    return success(result.model_dump(mode="json"), request_id)


@scores_router.get("", response_model=Envelope)
async def list_scores(
    workspace_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    status_filter: str | None = Query(default=None, alias="status", max_length=50),
    score_mode: str | None = Query(default=None, max_length=50),
    score_profile: str | None = Query(default=None, max_length=100),
    product_id: UUID | None = None,
    intended_use: str | None = Query(default=None, max_length=50),
    decision: str | None = Query(default=None, max_length=100),
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    search: str | None = Query(default=None, min_length=1, max_length=200),
    sort: SortOrder = "created_at_desc",
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.WORKSPACE_READ, current_user, db)
    result = await TikTokScoreService(db, settings).list(
        workspace_id,
        status=status_filter,
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
    return success(result.model_dump(mode="json"), request_id)


@scores_router.post("/events", status_code=status.HTTP_202_ACCEPTED, response_model=Envelope)
async def record_scorer_opened_event(
    workspace_id: UUID,
    payload: RecordTikTokScorerOpenedRequest,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.WORKSPACE_READ, current_user, db)
    result = await TikTokScoreService(db, settings).record_opened_event(
        workspace_id,
        payload,
        current_user.id,
    )
    return success(result.model_dump(mode="json"), request_id)


@scores_router.get("/{score_run_id}", response_model=Envelope)
async def get_score(
    workspace_id: UUID,
    score_run_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.WORKSPACE_READ, current_user, db)
    result = await TikTokScoreService(db, settings).get(workspace_id, score_run_id)
    return success(result.model_dump(mode="json"), request_id)


@scores_router.get("/{score_run_id}/fixes", response_model=Envelope)
async def list_score_fixes(
    workspace_id: UUID,
    score_run_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.WORKSPACE_READ, current_user, db)
    result = await TikTokScoreService(db, settings).list_fixes(workspace_id, score_run_id)
    return success(result.model_dump(mode="json"), request_id)


@scores_router.post(
    "/{score_run_id}/fixes/{fix_action_id}/actions",
    status_code=status.HTTP_201_CREATED,
    response_model=Envelope,
)
async def record_score_fix_action(
    workspace_id: UUID,
    score_run_id: UUID,
    fix_action_id: UUID,
    payload: RecordTikTokFixActionRequest,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(
        workspace_id,
        Permission.RECOMMENDATION_ACT,
        current_user,
        db,
    )
    result = await TikTokScoreService(db, settings).record_fix_action(
        workspace_id,
        score_run_id,
        fix_action_id,
        payload,
        current_user.id,
        idempotency_key,
    )
    return success(result.model_dump(mode="json"), request_id)


@scores_router.post(
    "/{score_run_id}/revisions",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=Envelope,
)
async def create_score_revision(
    workspace_id: UUID,
    score_run_id: UUID,
    payload: CreateTikTokScoreRevisionRequest,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(
        workspace_id,
        Permission.ANALYSIS_RUN,
        current_user,
        db,
    )
    result = await TikTokScoreService(db, settings).create_revision(
        workspace_id,
        score_run_id,
        payload,
        current_user.id,
        idempotency_key,
    )
    return success(result.model_dump(mode="json"), request_id)


@scores_router.get(
    "/{score_run_id}/comparisons/{comparison_id}",
    response_model=Envelope,
)
async def get_score_comparison(
    workspace_id: UUID,
    score_run_id: UUID,
    comparison_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.WORKSPACE_READ, current_user, db)
    result = await TikTokScoreService(db, settings).get_comparison(
        workspace_id,
        score_run_id,
        comparison_id,
    )
    return success(result.model_dump(mode="json"), request_id)


@scores_router.post(
    "/{score_run_id}/events",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=Envelope,
)
async def record_score_event(
    workspace_id: UUID,
    score_run_id: UUID,
    payload: RecordTikTokScorerEventRequest,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.WORKSPACE_READ, current_user, db)
    result = await TikTokScoreService(db, settings).record_product_event(
        workspace_id,
        score_run_id,
        payload,
        current_user.id,
    )
    return success(result.model_dump(mode="json"), request_id)


@profiles_router.get("", response_model=Envelope)
async def list_score_profiles(
    workspace_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.WORKSPACE_READ, current_user, db)
    result = await TikTokScoreService(db, settings).list_profiles(workspace_id)
    return success(result.model_dump(mode="json"), request_id)


router.include_router(scores_router)
router.include_router(profiles_router)
