from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request, status
from fastapi.responses import StreamingResponse

from viraldy.api.dependencies.auth import CurrentUserDep, DbSession, require_workspace_permission
from viraldy.api.dependencies.request import get_request_id
from viraldy.api.responses.envelope import Envelope, success
from viraldy.modules.assets.schemas import AssetResponse
from viraldy.modules.tiktok_commercial_content.media_stream import open_tiktok_media_stream
from viraldy.modules.tiktok_commercial_content.schemas import (
    AdReportRequest,
    AdSearchRequest,
    AdvertiserSearchRequest,
    AttachProductRequest,
    CommercialContentSearchRequest,
    GenerateDirectionsRequest,
    SaveReferenceRequest,
)
from viraldy.modules.tiktok_commercial_content.service import TikTokCommercialContentService
from viraldy.platform.auth.policy import Permission
from viraldy.platform.config.settings import Settings, get_settings

router = APIRouter(prefix="/workspaces/{workspace_id}/creative-library", tags=["creative-library"])
SettingsDep = Annotated[Settings, Depends(get_settings)]


def _service(db: DbSession, settings: Settings, request_id: str) -> TikTokCommercialContentService:
    return TikTokCommercialContentService(db, settings, request_id=request_id)


@router.post("/search", response_model=Envelope)
async def search_ads(
    workspace_id: UUID,
    payload: AdSearchRequest,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.REFERENCE_READ, current_user, db)
    result = await _service(db, settings, request_id).search_ads(payload)
    return success(result.model_dump(mode="json"), request_id)


@router.post("/advertisers/search", response_model=Envelope)
async def search_advertisers(
    workspace_id: UUID,
    payload: AdvertiserSearchRequest,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.REFERENCE_READ, current_user, db)
    result = await _service(db, settings, request_id).search_advertisers(payload)
    return success(result.model_dump(mode="json"), request_id)


@router.post("/commercial-content/search", response_model=Envelope)
async def search_commercial_content(
    workspace_id: UUID,
    payload: CommercialContentSearchRequest,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.REFERENCE_READ, current_user, db)
    result = await _service(db, settings, request_id).search_commercial_content(payload)
    return success(result.model_dump(mode="json"), request_id)


@router.post("/reports/ads", response_model=Envelope)
async def ad_report(
    workspace_id: UUID,
    payload: AdReportRequest,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.REFERENCE_READ, current_user, db)
    result = await _service(db, settings, request_id).get_ad_report(payload)
    return success(result, request_id)


@router.get("/sources/{source_id}", response_model=Envelope)
async def get_source(
    workspace_id: UUID,
    source_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.REFERENCE_READ, current_user, db)
    result = await _service(db, settings, request_id).get_ad_detail(source_id)
    return success(result.model_dump(mode="json"), request_id)


@router.get("/sources/{source_id}/media")
async def stream_source_media(
    workspace_id: UUID,
    source_id: UUID,
    request: Request,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
    media_index: int = Query(default=0, ge=0, le=50),
) -> StreamingResponse:
    await require_workspace_permission(workspace_id, Permission.REFERENCE_READ, current_user, db)
    if not settings.tiktok_commercial_direct_stream_allowed:
        from viraldy.shared.errors.base import AppError

        raise AppError(
            "TIKTOK_DIRECT_STREAM_DISABLED",
            "Direct TikTok streaming is disabled by compliance configuration.",
            503,
        )
    media_url, _media_type = await _service(db, settings, request_id).get_media_url(
        source_id, media_index
    )
    stream = await open_tiktok_media_stream(
        media_url,
        range_header=request.headers.get("range"),
        timeout_seconds=settings.tiktok_commercial_request_timeout_seconds,
    )
    response_headers = {**stream.headers, "X-Request-ID": request_id}
    return StreamingResponse(
        stream.body,
        status_code=stream.status_code,
        headers=response_headers,
        media_type=stream.media_type,
    )


@router.get("/assets/{asset_id}", response_model=Envelope)
async def get_asset(
    workspace_id: UUID,
    asset_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    from viraldy.modules.assets.repository import AssetRepository
    from viraldy.modules.references.repository import ReferenceRepository
    from viraldy.shared.errors.base import NotFoundError

    await require_workspace_permission(workspace_id, Permission.REFERENCE_READ, current_user, db)
    asset = await AssetRepository(db).get_for_workspace(workspace_id, asset_id)
    if asset is None:
        raise NotFoundError("ASSET_NOT_FOUND", "Creative asset was not found.")
    asset_response = AssetResponse.model_validate(asset)
    if asset.library_scope == "MARKET":
        reference = await ReferenceRepository(db).get_by_asset(workspace_id, asset_id)
        asset_response = asset_response.model_copy(
            update={"product_id": reference.product_id if reference else None}
        )
    return success(asset_response.model_dump(mode="json"), request_id)


@router.get("/assets/{asset_id}/intelligence", response_model=Envelope)
async def get_asset_intelligence(
    workspace_id: UUID,
    asset_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    from viraldy.modules.tiktok_commercial_content.workflow import MarketWorkflowService

    await require_workspace_permission(workspace_id, Permission.REFERENCE_READ, current_user, db)
    result = await MarketWorkflowService(db, settings).get_asset_intelligence(
        workspace_id, asset_id
    )
    return success(result, request_id)


@router.post(
    "/sources/{source_id}/save-reference",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=Envelope,
)
async def save_reference(
    workspace_id: UUID,
    source_id: UUID,
    payload: SaveReferenceRequest,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.REFERENCE_WRITE, current_user, db)
    result = await _service(db, settings, request_id).save_reference(
        workspace_id, current_user.id, source_id, payload
    )
    return success(result.model_dump(mode="json"), request_id)


@router.post(
    "/assets/{asset_id}/analyze", status_code=status.HTTP_202_ACCEPTED, response_model=Envelope
)
async def analyze_asset(
    workspace_id: UUID,
    asset_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    request_id: str = Depends(get_request_id),
) -> Envelope:
    from viraldy.modules.assets.repository import AssetRepository
    from viraldy.modules.products.public import ProductQueries
    from viraldy.modules.references.repository import ReferenceRepository
    from viraldy.modules.references.service import ReferenceService

    await require_workspace_permission(workspace_id, Permission.ANALYSIS_RUN, current_user, db)
    asset = await AssetRepository(db).get_for_workspace(workspace_id, asset_id)
    if asset is None or asset.current_version_id is None:
        from viraldy.shared.errors.base import NotFoundError

        raise NotFoundError("ASSET_NOT_FOUND", "Creative asset was not found.")
    version = await AssetRepository(db).get_current_version_in_workspace(workspace_id, asset_id)
    if version is None or version.validation_status == "metadata_only":
        from viraldy.shared.errors.base import AppError

        raise AppError(
            "TIKTOK_MEDIA_UNAVAILABLE",
            "This TikTok reference is metadata-only until approved media persistence is enabled.",
            409,
        )
    reference = await ReferenceRepository(db).get_by_asset(workspace_id, asset_id)
    if reference is None:
        raise NotFoundError("REFERENCE_NOT_FOUND", "This creative is not saved as a reference.")
    result = await ReferenceService(db, ProductQueries(db)).analyze(
        workspace_id, reference.id, current_user.id, idempotency_key
    )
    return success(result.model_dump(mode="json"), request_id)


@router.post("/assets/{asset_id}/attach-product", response_model=Envelope)
async def attach_product(
    workspace_id: UUID,
    asset_id: UUID,
    payload: AttachProductRequest,
    current_user: CurrentUserDep,
    db: DbSession,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    from viraldy.modules.assets.repository import AssetRepository
    from viraldy.modules.products.public import ProductQueries
    from viraldy.modules.references.repository import ReferenceRepository
    from viraldy.shared.errors.base import NotFoundError

    await require_workspace_permission(workspace_id, Permission.REFERENCE_WRITE, current_user, db)
    asset = await AssetRepository(db).get_for_workspace(workspace_id, asset_id)
    if asset is None:
        raise NotFoundError("ASSET_NOT_FOUND", "Creative asset was not found.")
    if payload.product_id and not await ProductQueries(db).exists_in_workspace(
        workspace_id, payload.product_id
    ):
        raise NotFoundError("PRODUCT_NOT_FOUND", "Product was not found.")
    if asset.library_scope == "MARKET":
        reference = await ReferenceRepository(db).get_by_asset(workspace_id, asset_id)
        if reference is None:
            raise NotFoundError("REFERENCE_NOT_FOUND", "This creative is not saved as a reference.")
        reference.product_id = payload.product_id
    else:
        asset.product_id = payload.product_id
    await db.commit()
    return success(
        {
            "asset_id": str(asset_id),
            "product_id": str(payload.product_id) if payload.product_id else None,
        },
        request_id,
    )


@router.post("/assets/{asset_id}/generate-directions", response_model=Envelope)
async def generate_directions(
    workspace_id: UUID,
    asset_id: UUID,
    payload: GenerateDirectionsRequest,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    from viraldy.modules.adaptations.schemas import CreateAdaptationRequest
    from viraldy.modules.adaptations.service import AdaptationService
    from viraldy.modules.assets.repository import AssetRepository
    from viraldy.modules.creative_dna.repository import CreativeDnaRepository
    from viraldy.modules.tiktok_commercial_content.workflow import MarketWorkflowService
    from viraldy.shared.errors.base import AppError, NotFoundError

    await require_workspace_permission(workspace_id, Permission.ANALYSIS_RUN, current_user, db)
    asset = await AssetRepository(db).get_for_workspace(workspace_id, asset_id)
    if asset is None:
        raise NotFoundError("ASSET_NOT_FOUND", "Creative asset was not found.")
    if asset.current_version_id is None:
        raise AppError("ASSET_VERSION_NOT_FOUND", "Creative asset has no current version.")
    dna = await CreativeDnaRepository(db).latest_for_asset_version(
        workspace_id, asset.current_version_id
    )
    if dna is None:
        raise AppError(
            "CREATIVE_DNA_NOT_FOUND", "Analyze the creative before generating directions."
        )
    result = await AdaptationService(db, settings).create(
        workspace_id,
        current_user.id,
        CreateAdaptationRequest(
            product_id=payload.product_id,
            creative_dna_version_id=dna.id,
            objective=payload.objective,
            target_market=payload.target_market,
            target_buyer=payload.target_buyer,
            constraints=payload.constraints,
            provenance={
                "source_asset_id": str(asset.id),
                "source_provider": asset.metadata_json.get("source_provider"),
                "source_record_id": asset.metadata_json.get("source_record_id"),
                "evidence_status": "market_signal_only",
            },
        ),
    )
    directions = await MarketWorkflowService(db, settings).create_directions(
        workspace_id,
        result.id,
        result.result_json,
        {
            **result.provenance_json,
            "adaptation_run_id": str(result.id),
            "creative_dna_version_id": str(result.creative_dna_version_id),
            "product_context_version": result.product_context_schema_version,
            "evidence_status": "market_signal_only",
        },
    )
    await db.commit()
    return success(
        {
            **result.model_dump(mode="json"),
            "directions": [
                {
                    "id": str(direction.id),
                    "direction_number": direction.direction_number,
                    "title": direction.title,
                }
                for direction in directions
            ],
        },
        request_id,
    )
