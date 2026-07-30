from __future__ import annotations

from uuid import UUID

import structlog

from viraldy.modules.assets.public import SyncAssetQueries
from viraldy.modules.campaign_packs.public import SyncCampaignPackRepository
from viraldy.modules.creative_dna.service import SyncCreativeDnaBuilder
from viraldy.modules.creative_domain.schema_versions import TIKTOK_SCORE_SCHEMA_VERSION
from viraldy.modules.jobs.registry import JobType, normalize_job_type
from viraldy.modules.jobs.repository import WorkerJobRepository
from viraldy.modules.media_analysis.service import SyncMediaEvidencePipeline
from viraldy.modules.preflight.repository import SyncPreflightRepository
from viraldy.modules.preflight.service import calculate_preflight_result
from viraldy.modules.recommendations.contracts import (
    RecommendationEvidenceV2,
    RecommendationPayloadV2,
)
from viraldy.modules.recommendations.models import RecommendationModel
from viraldy.modules.references.repository import SyncReferenceRepository
from viraldy.modules.tiktok_scorer.models import TikTokScoreRunModel
from viraldy.modules.tiktok_scorer.repository import (
    RUBRIC_VERSION,
    RULE_VERSION,
    SyncTikTokScoreRepository,
)
from viraldy.modules.tiktok_scorer.scorer import score_tiktok_structure
from viraldy.platform.clock.utc import utc_now
from viraldy.platform.config.settings import get_settings
from viraldy.platform.database.session import create_worker_session
from viraldy.shared.errors.base import AppError
from viraldy.worker.celery_app import celery_app

logger = structlog.get_logger(__name__)


@celery_app.task(bind=True, autoretry_for=(RuntimeError,), retry_backoff=True, max_retries=2)  # type: ignore[misc]
def run_processing_job(self, job_id: str) -> dict[str, object]:  # type: ignore[no-untyped-def]
    job_uuid = UUID(job_id)
    session = create_worker_session()
    repo = WorkerJobRepository(session)
    asset_queries = SyncAssetQueries(session)
    try:
        job = repo.claim_job(job_uuid)
        if job is None:
            session.commit()
            return {"ignored": True, "reason": "job_not_claimable"}
        logger.info("processing_job_started", job_id=job_id, workspace_id=str(job.workspace_id))
        session.commit()
        output = _execute_job(job, repo, asset_queries, session)
        repo.mark_succeeded(job, output)
        session.commit()
        logger.info("processing_job_completed", job_id=job_id)
        return output
    except AppError as exc:
        session.rollback()
        job = repo.load_job(job_uuid)
        if job is not None:
            try:
                repo.mark_failed(job, exc.code, exc.message)
            except AppError as fence_error:
                session.rollback()
                if fence_error.code == "JOB_ATTEMPT_SUPERSEDED":
                    logger.info("processing_job_attempt_superseded", job_id=job_id)
                    return {"ignored": True, "reason": "job_attempt_superseded"}
                raise
            session.commit()
        logger.info("processing_job_failed_app_error", job_id=job_id, code=exc.code)
        return {"error_code": exc.code, "error_message": exc.message}
    except Exception as exc:
        session.rollback()
        job = repo.load_job(job_uuid)
        if job is not None:
            try:
                if job.attempt_count >= job.max_attempts:
                    repo.mark_failed(job, "PROCESS_ASSET_FAILED", "Asset processing failed.")
                    session.commit()
                else:
                    repo.mark_retrying(
                        job,
                        "PROCESS_ASSET_RETRY",
                        "Asset processing retry scheduled.",
                    )
                    session.commit()
            except AppError as fence_error:
                session.rollback()
                if fence_error.code == "JOB_ATTEMPT_SUPERSEDED":
                    logger.info("processing_job_attempt_superseded", job_id=job_id)
                    return {"ignored": True, "reason": "job_attempt_superseded"}
                raise
        logger.exception("processing_job_failed", job_id=job_id)
        raise self.retry(exc=exc) from exc
    finally:
        session.close()


@celery_app.task  # type: ignore[misc]
def recover_stale_processing_jobs() -> dict[str, object]:
    from viraldy.modules.jobs.dispatcher import CeleryJobDispatcher

    settings = get_settings()
    session = create_worker_session()
    dispatcher = CeleryJobDispatcher()
    try:
        retry_ids = WorkerJobRepository(session).recover_stale_jobs(
            utc_now(),
            settings.job_stale_after_seconds,
        )
        session.commit()
        for job_id in retry_ids:
            job = WorkerJobRepository(session).load_job(job_id)
            if job is None:
                continue
            dispatcher.dispatch_job(job.id, job.job_type)
        return {"recovered_job_ids": [str(job_id) for job_id in retry_ids]}
    finally:
        session.close()


@celery_app.task  # type: ignore[misc]
def retry_pending_storage_deletions() -> dict[str, int]:
    from viraldy.modules.deletion.storage_cleanup import (
        process_pending_storage_deletions,
    )
    from viraldy.platform.storage.s3 import S3StorageAdapter

    settings = get_settings()
    session = create_worker_session()
    try:
        return process_pending_storage_deletions(
            session,
            S3StorageAdapter(settings),
        )
    finally:
        session.close()


def _execute_job(
    job, repo: WorkerJobRepository, asset_queries: SyncAssetQueries, session
) -> dict[str, object]:
    job_type = normalize_job_type(job.job_type)
    if job_type == JobType.MEDIA_ANALYSIS.value:
        asset_id = UUID(str(job.input_json["asset_id"]))
        asset_version_id = UUID(str(job.input_json["asset_version_id"]))
        repo.update_progress(job, 25, "loading_asset")
        session.commit()
        loaded = asset_queries.load_asset_version(asset_id, asset_version_id)
        if loaded is None:
            raise RuntimeError("asset_version_not_found")
        repo.update_progress(job, 40, "probing_media")
        session.commit()
        pipeline_result = SyncMediaEvidencePipeline(session, get_settings()).process_with_metadata(
            loaded, "media_analysis", job.id
        )
        repo.update_progress(job, 90, "persisting_results")
        session.commit()
        return {
            "processor": "media-evidence-pipeline",
            "asset_id": str(asset_id),
            "asset_version_id": str(asset_version_id),
            "evidence_count": len(pipeline_result.evidence),
            "primary_model_run_id": str(pipeline_result.primary_model_run_id)
            if pipeline_result.primary_model_run_id
            else None,
            "analysis_mode": get_settings().ai_mode,
        }
    if job_type == JobType.CREATIVE_DNA_BUILD.value:
        return _analyze_reference(job, repo, asset_queries, session)
    if job_type == JobType.TIKTOK_SCORE_RUN.value:
        return _score_tiktok_asset(job, repo, asset_queries, session)
    if job_type == JobType.PREFLIGHT_RUN.value:
        return _run_ugc_preflight(job, repo, asset_queries, session)
    if job_type in {
        JobType.STORYBOARD_GENERATE.value,
        JobType.CONCEPT_VIDEO_GENERATE.value,
    }:
        from viraldy.modules.generation.public import execute_generation_job

        if job.subject_type != "generation_run":
            raise AppError(
                "GENERATION_JOB_SUBJECT_INVALID",
                "Generation jobs must target a generation run.",
            )
        repo.update_progress(job, 30, "loading_generation_brief")
        session.commit()
        output = execute_generation_job(
            session,
            job.workspace_id,
            job.subject_id,
            job.id,
            get_settings(),
            lambda: repo.assert_claim_active(job),
        )
        repo.update_progress(job, 90, "persisting_results")
        return output
    if job_type == JobType.RETENTION_CLEANUP.value:
        from viraldy.modules.deletion.retention import execute_retention_cleanup
        from viraldy.platform.storage.s3 import S3StorageAdapter

        if job.subject_type != "workspace" or job.subject_id != job.workspace_id:
            raise AppError(
                "RETENTION_JOB_SUBJECT_INVALID",
                "Retention jobs must target their own workspace.",
            )
        repo.update_progress(job, 30, "selecting_expired_records")
        session.commit()
        output = execute_retention_cleanup(
            session,
            job.workspace_id,
            get_settings(),
            S3StorageAdapter(get_settings()),
        )
        repo.update_progress(job, 90, "persisting_results")
        return output
    raise RuntimeError(f"unsupported_job_type:{job.job_type}")


def _process_media(
    job, repo: WorkerJobRepository, asset_queries: SyncAssetQueries, session, run_type: str
):
    asset_id = UUID(str(job.input_json.get("asset_id") or job.input_json.get("ugc_asset_id")))
    version_id = UUID(
        str(job.input_json.get("asset_version_id") or job.input_json.get("ugc_asset_version_id"))
    )
    repo.update_progress(job, 20, "loading_asset")
    session.commit()
    loaded = asset_queries.load_asset_version(asset_id, version_id)
    if loaded is None:
        raise RuntimeError("asset_version_not_found")
    repo.update_progress(job, 35, "probing_media")
    session.commit()
    pipeline_result = SyncMediaEvidencePipeline(session, get_settings()).process_with_metadata(
        loaded, run_type, job.id
    )
    repo.update_progress(job, 60, "extracting_visual_evidence")
    session.commit()
    return loaded, pipeline_result.evidence, pipeline_result.primary_model_run_id


def _analyze_reference(
    job, repo: WorkerJobRepository, asset_queries: SyncAssetQueries, session
) -> dict[str, object]:
    loaded, evidence, primary_model_run_id = _process_media(
        job, repo, asset_queries, session, "creative_dna_build"
    )
    reference_id = UUID(str(job.input_json["reference_id"]))
    repo.update_progress(job, 72, "building_creative_dna")
    dna = SyncCreativeDnaBuilder(session).build(
        job.workspace_id, loaded.asset_version_id, reference_id, evidence, get_settings().ai_mode
    )
    dna.processing_job_id = job.id
    dna.primary_model_run_id = primary_model_run_id
    reference = SyncReferenceRepository(session).get(job.workspace_id, reference_id)
    if reference is not None:
        reference.status = "analyzed"
    repo.update_progress(job, 90, "persisting_results")
    session.commit()
    return {
        "reference_id": str(reference_id),
        "creative_dna_version_id": str(dna.id),
        "asset_version_id": str(loaded.asset_version_id),
        "evidence_count": len(evidence),
        "analysis_mode": dna.analysis_mode,
    }


def _score_tiktok_asset(
    job, repo: WorkerJobRepository, asset_queries: SyncAssetQueries, session
) -> dict[str, object]:
    loaded, evidence, primary_model_run_id = _process_media(
        job, repo, asset_queries, session, "tiktok_score_run"
    )
    score_run_id = UUID(str(job.input_json["score_run_id"]))
    repo.update_progress(job, 70, "calculating_score")
    dna = SyncCreativeDnaBuilder(session).build(
        job.workspace_id, loaded.asset_version_id, None, evidence, get_settings().ai_mode
    )
    result = score_tiktok_structure(
        evidence,
        media_duration_ms=_media_duration_ms(loaded.metadata_json),
        product_context_present=loaded.product_id is not None,
    )
    run = SyncTikTokScoreRepository(session).get(job.workspace_id, score_run_id)
    if run is None:
        raise RuntimeError("score_run_not_found")
    SyncTikTokScoreRepository(session).complete(
        run, dna.id, result, "fixture_scoring_v1" if get_settings().ai_mode == "fixture" else None
    )
    run.processing_job_id = job.id
    run.primary_model_run_id = primary_model_run_id
    dna.primary_model_run_id = primary_model_run_id
    _record_recommendation(
        session,
        job.workspace_id,
        "tiktok_score_run",
        run.id,
        "tiktok_structure_decision",
        result,
    )
    repo.update_progress(job, 90, "persisting_results")
    session.commit()
    return {
        "score_run_id": str(run.id),
        "creative_dna_version_id": str(dna.id),
        "structural_score": result["structural_score"],
        "action": result["action"],
        "analysis_mode": run.analysis_mode,
    }


def _run_ugc_preflight(
    job, repo: WorkerJobRepository, asset_queries: SyncAssetQueries, session
) -> dict[str, object]:
    loaded, evidence, primary_model_run_id = _process_media(
        job, repo, asset_queries, session, "preflight_run"
    )
    preflight_run_id = UUID(str(job.input_json["preflight_run_id"]))
    pack_version_id = UUID(str(job.input_json["campaign_pack_version_id"]))
    repo.update_progress(job, 65, "calculating_score")
    structural_result = score_tiktok_structure(
        evidence,
        media_duration_ms=_media_duration_ms(loaded.metadata_json),
        product_context_present=True,
    )
    structural_run = TikTokScoreRunModel(
        workspace_id=job.workspace_id,
        asset_version_id=loaded.asset_version_id,
        status="completed",
        schema_version=TIKTOK_SCORE_SCHEMA_VERSION,
        structural_score=structural_result["structural_score"],
        confidence=structural_result["confidence"],
        action_label=structural_result["action"],
        dimension_scores_json=structural_result["dimensions"],
        strengths_json=structural_result["strengths"],
        blockers_json=structural_result["blockers"],
        fixes_json=structural_result["fixes"],
        evidence_ids_json=structural_result["evidence_ids"],
        analysis_mode=get_settings().ai_mode,
        rubric_version=RUBRIC_VERSION,
        rule_version=RULE_VERSION,
        model_version="fixture_scoring_v1" if get_settings().ai_mode == "fixture" else None,
        processing_job_id=job.id,
        primary_model_run_id=primary_model_run_id,
        pipeline_version="media_pipeline_v1",
    )
    session.add(structural_run)
    session.flush()
    repo.update_progress(job, 76, "checking_brief_alignment")
    pack_row = SyncCampaignPackRepository(session).get_version_with_pack(
        job.workspace_id, pack_version_id
    )
    if pack_row is None:
        raise RuntimeError("campaign_pack_version_not_found")
    pack_version, _ = pack_row
    result = calculate_preflight_result(
        structural_result,
        pack_version.brief_json,
        pack_version.compiled_requirements_json,
        evidence,
        pack_version.product_snapshot_json,
        _media_duration_ms(loaded.metadata_json),
    )
    run = SyncPreflightRepository(session).get(job.workspace_id, preflight_run_id)
    if run is None:
        raise RuntimeError("preflight_run_not_found")
    SyncPreflightRepository(session).complete(
        run,
        result,
        structural_run.id,
        "fixture_preflight_v1" if get_settings().ai_mode == "fixture" else None,
        pack_version.product_snapshot_json,
        _product_context_schema_version(pack_version.product_snapshot_json),
        pack_version.compiled_requirements_json,
    )
    run.processing_job_id = job.id
    run.primary_model_run_id = primary_model_run_id
    _record_recommendation(
        session,
        job.workspace_id,
        "preflight_run",
        run.id,
        "ugc_preflight_decision",
        result,
    )
    repo.update_progress(job, 90, "persisting_results")
    session.commit()
    return {
        "preflight_run_id": str(run.id),
        "structural_score_run_id": str(structural_run.id),
        "preflight_score": result["preflight_score"],
        "action": result["action"],
        "analysis_mode": run.analysis_mode,
    }


def _record_recommendation(
    session,
    workspace_id: UUID,
    subject_type: str,
    subject_id: UUID,
    recommendation_type: str,
    result: dict[str, object],
) -> None:
    payload = RecommendationPayloadV2(
        subject_type=subject_type,
        subject_id=subject_id,
        recommendation_type=recommendation_type,
        action=str(result["action"]),
        confidence=str(result["confidence"]),
        reasoning=str(result.get("summary") or f"Action: {result['action']}"),
        evidence=RecommendationEvidenceV2(
            evidence_ids=result.get("evidence_ids", []),
            blockers=result.get("blockers", []),
            fixes=result.get("fixes", []),
        ),
        rule_version=str(result["rule_version"]),
        source_run_id=subject_id,
    )

    session.add(
        RecommendationModel(
            workspace_id=workspace_id,
            subject_type=payload.subject_type,
            subject_id=payload.subject_id,
            recommendation_type=payload.recommendation_type,
            action=payload.action,
            confidence=payload.confidence,
            reasoning=payload.reasoning,
            evidence_json=payload.evidence.model_dump(mode="json"),
            assumptions_json=payload.assumptions,
            model_version="fixture_recommendation_v1"
            if get_settings().ai_mode == "fixture"
            else None,
            rule_version=payload.rule_version,
            payload_schema_version=payload.schema_version,
            source_run_id=payload.source_run_id,
        )
    )


def _media_duration_ms(metadata_json: dict[str, object]) -> int | None:
    media = metadata_json.get("media")
    if not isinstance(media, dict):
        return None
    duration = media.get("duration_ms")
    return int(duration) if isinstance(duration, int | float) else None


def _product_context_schema_version(product_snapshot_json: dict[str, object] | None) -> str | None:
    if not product_snapshot_json:
        return None
    schema_version = product_snapshot_json.get("schema_version")
    return str(schema_version) if schema_version else None
