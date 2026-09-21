from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from viraldy.api.middleware.errors import (
    app_error_handler,
    unexpected_error_handler,
    validation_error_handler,
)
from viraldy.api.middleware.request_id import RequestIdMiddleware
from viraldy.api.middleware.security_headers import SecurityHeadersMiddleware
from viraldy.api.openapi import (
    API_DESCRIPTION,
    API_SUMMARY,
    OPENAPI_TAGS,
    SWAGGER_UI_PARAMETERS,
    configure_openapi,
)
from viraldy.api.responses.envelope import Envelope, success
from viraldy.api.routers.health import router as health_router
from viraldy.api.routers.system import router as system_router
from viraldy.modules.adaptations.router import router as adaptations_router
from viraldy.modules.ai_gateway.router import router as ai_model_runs_router
from viraldy.modules.assets.router import router as assets_router
from viraldy.modules.campaign_packs.router import router as campaign_packs_router
from viraldy.modules.creative_dna.router import router as creative_dna_router
from viraldy.modules.deletion.router import router as deletion_router
from viraldy.modules.domain_intelligence.router import router as domain_intelligence_router
from viraldy.modules.feedback.router import router as feedback_router
from viraldy.modules.generation.router import router as generation_router
from viraldy.modules.identity.router import router as identity_router
from viraldy.modules.jobs.router import router as jobs_router
from viraldy.modules.media_analysis.router import router as media_analysis_router
from viraldy.modules.pattern_kits.router import router as pattern_kits_router
from viraldy.modules.preflight.router import router as preflight_router
from viraldy.modules.product_events.router import router as product_events_router
from viraldy.modules.product_import.media_router import router as product_import_media_router
from viraldy.modules.products.router import router as products_router
from viraldy.modules.recommendations.router import router as recommendations_router
from viraldy.modules.reference_boards.router import router as reference_boards_router
from viraldy.modules.references.router import router as references_router
from viraldy.modules.smart_remake.router import router as smart_remake_router
from viraldy.modules.smart_remake.runtime_paths import RENDERS_DIR
from viraldy.modules.tiktok_scorer.router import router as tiktok_scorer_router
from viraldy.modules.ugc_review.router import router as ugc_review_router
from viraldy.modules.ugc_review.video_ingestion import S3UGCVideoIngestion
from viraldy.modules.viral_kits.router import router as viral_kits_router
from viraldy.modules.workspaces.router import router as workspaces_router
from viraldy.platform.config.settings import get_settings
from viraldy.platform.observability.logging import configure_logging
from viraldy.platform.observability.sentry import configure_sentry
from viraldy.shared.errors.base import AppError


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings)
    configure_sentry(settings)

    app = FastAPI(
        title=f"{settings.app_name} API",
        summary=API_SUMMARY,
        description=API_DESCRIPTION,
        version=settings.public_version,
        openapi_tags=OPENAPI_TAGS,
        servers=[
            {"url": "/", "description": "Môi trường hiện tại đang phục vụ Swagger UI"},
            {"url": "http://localhost:8000", "description": "Backend local development"},
        ],
        swagger_ui_parameters=SWAGGER_UI_PARAMETERS,
        license_info={"name": "MIT", "identifier": "MIT"},
    )
    app.state.ugc_review_video_ingestion = S3UGCVideoIngestion(settings)
    app.mount("/outputs/renders", StaticFiles(directory=RENDERS_DIR), name="smart-remake-renders")
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(SecurityHeadersMiddleware, settings=settings)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.backend_cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-Request-ID"],
    )
    app.add_exception_handler(AppError, app_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, unexpected_error_handler)

    api_v1 = "/api/v1"
    app.include_router(health_router)
    app.include_router(product_import_media_router)
    app.include_router(system_router, prefix=api_v1)
    app.include_router(identity_router, prefix=api_v1)
    app.include_router(workspaces_router, prefix=api_v1)
    app.include_router(products_router, prefix=api_v1)
    app.include_router(assets_router, prefix=api_v1)
    app.include_router(jobs_router, prefix=api_v1)
    app.include_router(ai_model_runs_router, prefix=api_v1)
    app.include_router(recommendations_router, prefix=api_v1)
    app.include_router(product_events_router, prefix=api_v1)
    app.include_router(feedback_router, prefix=api_v1)
    app.include_router(deletion_router, prefix=api_v1)
    app.include_router(generation_router, prefix=api_v1)
    app.include_router(media_analysis_router, prefix=api_v1)
    app.include_router(domain_intelligence_router, prefix=api_v1)
    app.include_router(ugc_review_router, prefix=api_v1)
    app.include_router(reference_boards_router, prefix=api_v1)
    app.include_router(references_router, prefix=api_v1)
    app.include_router(creative_dna_router, prefix=api_v1)
    app.include_router(pattern_kits_router, prefix=api_v1)
    app.include_router(viral_kits_router, prefix=api_v1)
    app.include_router(tiktok_scorer_router, prefix=api_v1)
    app.include_router(adaptations_router, prefix=api_v1)
    app.include_router(campaign_packs_router, prefix=api_v1)
    app.include_router(preflight_router, prefix=api_v1)
    app.include_router(smart_remake_router, prefix=api_v1)

    @app.get("/health", response_model=Envelope)
    async def health(request: Request) -> Envelope:
        return success({"status": "ok"}, str(getattr(request.state, "request_id", "unknown")))

    @app.get("/ready", response_model=Envelope)
    async def root_ready(request: Request) -> Envelope:
        from viraldy.api.routers.system import readiness
        from viraldy.platform.database.session import AsyncSessionFactory

        async with AsyncSessionFactory() as db:
            checks = await readiness(db=db, settings=settings)
            status = "ok" if all(value == "ok" for value in checks.values()) else "degraded"
            return success(
                {"status": status, "checks": checks},
                str(getattr(request.state, "request_id", "unknown")),
            )

    configure_openapi(app)
    return app


app = create_app()
