from __future__ import annotations

from time import perf_counter
from typing import cast
from uuid import UUID

import structlog
from sqlalchemy.orm import Session

from viraldy.modules.assets.public import AssetVersionSnapshot, SyncAssetQueries
from viraldy.modules.campaign_packs.public import SyncCampaignPackRepository
from viraldy.modules.creative_dna.service import SyncCreativeDnaBuilder
from viraldy.modules.creative_domain.schema_versions import TIKTOK_SCORE_SCHEMA_VERSION
from viraldy.modules.jobs.models import ProcessingJobModel
from viraldy.modules.jobs.registry import JobType, normalize_job_type
from viraldy.modules.jobs.repository import WorkerJobRepository
from viraldy.modules.media_analysis.public import EvidenceItemModel
from viraldy.modules.media_analysis.service import SyncMediaEvidencePipeline
from viraldy.modules.preflight.repository import SyncPreflightRepository
from viraldy.modules.preflight.service import calculate_preflight_result
from viraldy.modules.product_events.public import SyncProductEventPublisher
from viraldy.modules.products.public import ProductContextSnapshot
from viraldy.modules.recommendations.contracts import (
    RecommendationEvidenceV2,
    RecommendationPayloadV2,
)
from viraldy.modules.recommendations.models import RecommendationModel
from viraldy.modules.references.repository import SyncReferenceRepository
from viraldy.modules.tiktok_scorer.comparison import compare_score_results
from viraldy.modules.tiktok_scorer.contracts_v2 import (
    CreativeDirectionContextV1,
    IntendedUseV1,
    ProfileSelectionV1,
    ScoreModeV2,
    TikTokScoreResultV2,
)
from viraldy.modules.tiktok_scorer.engine_v2 import (
    ScoringStageV2,
    analyze_tiktok_evidence_v2,
)
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

TIKTOK_SCORER_MODEL_VERSION = "deterministic_tiktok_diagnostic_v2"
_TIKTOK_STAGE_PROGRESS: dict[str, int] = {
    "extracting_media": 20,
    "building_evidence": 45,
    "building_scene_inventory": 55,
    "scoring": 70,
    "compiling_fixes": 78,
    "enriching_direction": 82,
    "validating_output": 86,
    "persisting": 90,
}


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
                _update_tiktok_score_failure_state(
                    job,
                    session,
                    exc.code,
                    terminal=True,
                )
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
                    _update_tiktok_score_failure_state(
                        job,
                        session,
                        "PROCESS_ASSET_FAILED",
                        terminal=True,
                    )
                    session.commit()
                else:
                    repo.mark_retrying(
                        job,
                        "PROCESS_ASSET_RETRY",
                        "Asset processing retry scheduled.",
                    )
                    _update_tiktok_score_failure_state(
                        job,
                        session,
                        "PROCESS_ASSET_RETRY",
                        terminal=False,
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
    job: ProcessingJobModel,
    repo: WorkerJobRepository,
    asset_queries: SyncAssetQueries,
    session: Session,
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
    if job_type == JobType.UGC_REVIEW.value:
        return _review_ugc_asset(job, repo, asset_queries, session)
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

        def ensure_active_attempt() -> None:
            repo.assert_claim_active(job)

        output = execute_generation_job(
            session,
            job.workspace_id,
            job.subject_id,
            job.id,
            get_settings(),
            ensure_active_attempt,
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
    job: ProcessingJobModel,
    repo: WorkerJobRepository,
    asset_queries: SyncAssetQueries,
    session: Session,
    run_type: str,
) -> tuple[AssetVersionSnapshot, list[EvidenceItemModel], UUID | None]:
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
    refreshed = asset_queries.load_asset_version(asset_id, version_id)
    if refreshed is not None:
        loaded = refreshed
    repo.update_progress(job, 60, "extracting_visual_evidence")
    session.commit()
    return loaded, pipeline_result.evidence, pipeline_result.primary_model_run_id


def _analyze_reference(
    job: ProcessingJobModel,
    repo: WorkerJobRepository,
    asset_queries: SyncAssetQueries,
    session: Session,
) -> dict[str, object]:
    loaded, evidence, _ = _process_media(job, repo, asset_queries, session, "creative_dna_build")
    reference_id = UUID(str(job.input_json["reference_id"]))
    repo.update_progress(job, 72, "building_creative_dna")
    settings = get_settings()
    dna = SyncCreativeDnaBuilder(session, settings).build(
        job.workspace_id,
        loaded.asset_version_id,
        reference_id,
        evidence,
        settings.ai_mode,
        asset_id=loaded.asset_id,
        processing_job_id=job.id,
        actor_user_id=_actor_user_id(job),
        product_id=loaded.product_id,
        media_duration_ms=_media_duration_ms(loaded.metadata_json),
        attempt_count=job.attempt_count,
    )
    reference = SyncReferenceRepository(session).get(job.workspace_id, reference_id)
    if reference is not None:
        reference.status = "analyzed"
    actor_user_id = job.input_json.get("actor_user_id")
    SyncProductEventPublisher(session).record(
        event_type="reference_analyzed",
        workspace_id=job.workspace_id,
        actor_user_id=UUID(str(actor_user_id)) if actor_user_id else None,
        subject_type="reference",
        subject_id=reference_id,
        payload_json={
            "creative_dna_version_id": str(dna.id),
            "asset_version_id": str(loaded.asset_version_id),
            "processing_job_id": str(job.id),
            "analysis_mode": dna.analysis_mode,
        },
    )
    repo.update_progress(job, 90, "persisting_results")
    session.commit()
    return {
        "reference_id": str(reference_id),
        "creative_dna_version_id": str(dna.id),
        "asset_version_id": str(loaded.asset_version_id),
        "evidence_count": len(evidence),
        "analysis_mode": dna.analysis_mode,
        "primary_model_run_id": (
            str(dna.primary_model_run_id) if dna.primary_model_run_id else None
        ),
    }


def _score_tiktok_asset(
    job: ProcessingJobModel,
    repo: WorkerJobRepository,
    asset_queries: SyncAssetQueries,
    session: Session,
) -> dict[str, object]:
    score_run_id = UUID(str(job.input_json["score_run_id"]))
    score_repository = SyncTikTokScoreRepository(session)
    run = score_repository.load_run_with_snapshots(job.workspace_id, score_run_id)
    if run is None:
        raise RuntimeError("score_run_not_found")
    if run.status == "completed":
        return _completed_tiktok_score_output(job, run)

    _update_tiktok_stage(
        job,
        run,
        repo,
        score_repository,
        session,
        "extracting_media",
    )
    asset_id = UUID(str(job.input_json["asset_id"]))
    asset_version_id = UUID(str(job.input_json["asset_version_id"]))
    loaded = asset_queries.load_asset_version(asset_id, asset_version_id)
    if loaded is None:
        raise RuntimeError("asset_version_not_found")
    _validate_tiktok_run_media(job, run, loaded)
    product_snapshot = _product_snapshot_from_run(run)

    settings = get_settings()
    pipeline_result = SyncMediaEvidencePipeline(session, settings).process_with_metadata(
        loaded,
        "tiktok_score_run",
        job.id,
        product_context_snapshot=product_snapshot,
    )
    refreshed = asset_queries.load_asset_version(asset_id, asset_version_id)
    if refreshed is not None:
        loaded = refreshed
    _validate_tiktok_run_media(job, run, loaded)
    _update_tiktok_stage(
        job,
        run,
        repo,
        score_repository,
        session,
        "building_evidence",
    )

    direction_context, direction_uncertainty = _direction_context_from_run(run)
    profile_selection = ProfileSelectionV1(
        profile_code=run.score_profile,
        selection_mode=run.profile_selection_mode,
        confidence=_profile_selection_confidence(run),
        alternative_profiles=list(run.alternative_profiles_json),
        evidence_ids=[UUID(str(value)) for value in run.profile_evidence_ids_json],
    )
    scoring_started = perf_counter()

    def record_scoring_stage(stage: ScoringStageV2) -> None:
        _update_tiktok_stage(
            job,
            run,
            repo,
            score_repository,
            session,
            stage,
        )

    result = analyze_tiktok_evidence_v2(
        pipeline_result.evidence,
        asset_version_id=loaded.asset_version_id,
        duration_ms=_media_duration_ms(loaded.metadata_json),
        score_mode=cast(ScoreModeV2, run.score_mode),
        profile_selection=profile_selection,
        intended_use=cast(IntendedUseV1, run.intended_use),
        audio_available=_media_audio_available(loaded.metadata_json),
        product_context_snapshot=product_snapshot,
        direction_context=direction_context,
        market=_optional_job_string(job, "market"),
        objective=_optional_job_string(job, "objective"),
        target_query=_optional_search_context_string(job, "target_query"),
        target_buyer_question=_optional_search_context_string(
            job,
            "target_buyer_question",
        ),
        selected_search_topic=_optional_search_context_string(
            job,
            "selected_search_topic",
        ),
        content_gap_topic=_optional_search_context_string(job, "content_gap_topic"),
        stage_callback=record_scoring_stage,
    )
    result = _append_direction_uncertainty(result, direction_uncertainty)
    _update_tiktok_stage(
        job,
        run,
        repo,
        score_repository,
        session,
        "validating_output",
    )
    validated_result = TikTokScoreResultV2.model_validate(result)
    result_payload = validated_result.model_dump(mode="json")
    _validate_tiktok_result_snapshot(run, result_payload)
    _update_tiktok_stage(
        job,
        run,
        repo,
        score_repository,
        session,
        "persisting",
    )
    score_repository.persist_v2_result(
        run,
        result_payload,
        processing_job_id=job.id,
        primary_model_run_id=pipeline_result.primary_model_run_id,
        model_version=TIKTOK_SCORER_MODEL_VERSION,
        prompt_versions=dict(run.prompt_versions_json),
        model_provider_versions=_model_provider_versions(
            run.model_provider_versions_json,
            pipeline_result.evidence,
        ),
        latency_ms=max(0, round((perf_counter() - scoring_started) * 1000)),
        token_usage={},
        cost_estimate=None,
    )
    comparison_id = _persist_tiktok_comparison_if_requested(
        job,
        run,
        score_repository,
        validated_result,
    )
    _record_tiktok_score_event(
        session,
        run,
        job,
        "tiktok_score_completed",
        {
            "structural_score": validated_result.overall_score,
            "confidence": validated_result.overall_confidence,
            "decision": validated_result.creative_structure_decision,
        },
    )
    session.commit()
    output: dict[str, object] = {
        "score_run_id": str(run.id),
        "asset_version_id": str(run.asset_version_id),
        "structural_score": validated_result.overall_score,
        "action": validated_result.creative_structure_decision,
        "confidence": validated_result.overall_confidence,
        "analysis_mode": run.analysis_mode,
        "primary_model_run_id": (
            str(pipeline_result.primary_model_run_id)
            if pipeline_result.primary_model_run_id
            else None
        ),
    }
    if comparison_id is not None:
        output["comparison_id"] = str(comparison_id)
    return output


def _run_ugc_preflight(
    job: ProcessingJobModel,
    repo: WorkerJobRepository,
    asset_queries: SyncAssetQueries,
    session: Session,
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


def _review_ugc_asset(
    job: ProcessingJobModel,
    repo: WorkerJobRepository,
    asset_queries: SyncAssetQueries,
    session: Session,
) -> dict[str, object]:
    from viraldy.modules.domain_intelligence.public import (
        SyncDomainIntelligenceQueries,
        UGCReviewContext,
        adapt_media_evidence,
        evaluate_review,
    )
    from viraldy.modules.ugc_review.public import SyncUGCReviewRepository

    loaded, evidence, primary_model_run_id = _process_media(
        job,
        repo,
        asset_queries,
        session,
        "ugc_review_v1",
    )
    if loaded.workspace_id != job.workspace_id:
        raise AppError(
            "UGC_REVIEW_WORKSPACE_MISMATCH",
            "UGC review media did not match the processing workspace.",
        )

    context_payload = job.input_json.get("request_context") or {}
    if not isinstance(context_payload, dict):
        raise AppError(
            "UGC_REVIEW_CONTEXT_INVALID",
            "UGC review context snapshot is invalid.",
        )
    context = UGCReviewContext.model_validate(context_payload)
    evidence_bundle = adapt_media_evidence(evidence)
    domain_queries = SyncDomainIntelligenceQueries(session)

    repo.update_progress(job, 68, "selecting_policies")
    session.commit()
    rules = domain_queries.select_rules(context, evidence_bundle)
    pack_status = domain_queries.status()

    repo.update_progress(job, 80, "evaluating_review")
    session.commit()
    settings = get_settings()
    result = evaluate_review(
        review_id=str(job.id),
        context=context,
        evidence=evidence_bundle,
        rules=rules,
        pack_version=pack_status.version,
        analysis_provenance={
            "analysis_mode": settings.ai_mode,
            "primary_model_run_id": (str(primary_model_run_id) if primary_model_run_id else None),
        },
    )
    result = _enrich_ugc_execution_brief(
        job=job,
        loaded=loaded,
        context=context,
        evidence_bundle=evidence_bundle,
        result=result,
        settings=settings,
        session=session,
    )

    repo.update_progress(job, 90, "persisting_results")
    session.commit()
    SyncUGCReviewRepository(session).persist_result(
        workspace_id=job.workspace_id,
        processing_job_id=job.id,
        asset_id=loaded.asset_id,
        asset_version_id=loaded.asset_version_id,
        request_context=context.model_dump(mode="json"),
        result=result,
    )
    recommendation_count = (
        len(result.fix_first) + len(result.improvements) + len(result.confirmations)
    )
    return {
        "review_id": str(job.id),
        "asset_id": str(loaded.asset_id),
        "asset_version_id": str(loaded.asset_version_id),
        "evidence_count": len(evidence),
        "recommendation_count": recommendation_count,
        "policy_pack_version": pack_status.version,
        "analysis_mode": settings.ai_mode,
        "primary_model_run_id": (str(primary_model_run_id) if primary_model_run_id else None),
    }


def _enrich_ugc_execution_brief(
    *,
    job: ProcessingJobModel,
    loaded: AssetVersionSnapshot,
    context: object,
    evidence_bundle: object,
    result: object,
    settings: object,
    session: Session,
) -> object:
    """Use OpenAI only to improve task wording after deterministic evaluation."""
    from viraldy.modules.ai_gateway.context import ViraldyOperationContextV1
    from viraldy.modules.ai_gateway.execution import execute_structured_operation
    from viraldy.modules.ai_gateway.operations import AiOperationName
    from viraldy.modules.ai_gateway.prompt_packages import get_prompt_package
    from viraldy.modules.ai_gateway.repository import SyncAiModelRunRepository
    from viraldy.modules.ai_gateway.request_identity import stable_json_hash
    from viraldy.modules.domain_intelligence.execution_brief_contracts import (
        UGCExecutionBriefSynthesisV1,
    )
    from viraldy.modules.domain_intelligence.public import apply_execution_brief_synthesis
    from viraldy.modules.domain_intelligence.schemas import (
        NormalizedEvidenceBundle,
        UGCReviewContext,
        UGCReviewResult,
    )

    typed_context = cast(UGCReviewContext, context)
    typed_evidence = cast(NormalizedEvidenceBundle, evidence_bundle)
    typed_result = cast(UGCReviewResult, result)
    if settings.ai_mode != "live":
        return typed_result
    recommendations = [
        *typed_result.fix_first,
        *typed_result.improvements,
        *typed_result.confirmations,
    ]
    if not recommendations:
        return _with_execution_brief_provenance(typed_result, {"status": "not_applicable"})

    prompt = get_prompt_package(AiOperationName.UGC_EXECUTION_BRIEF_SYNTHESIS)
    input_summary = {
        "review_id": typed_result.review_id,
        "recommendation_ids": [item.id for item in recommendations],
        "evidence_count": len(typed_evidence.items),
    }
    initial_hash = stable_json_hash(input_summary)
    model_runs = SyncAiModelRunRepository(session)
    model_run = model_runs.create_running(
        workspace_id=job.workspace_id,
        processing_job_id=job.id,
        subject_type="ugc_review",
        subject_id=job.id,
        capability="ugc_execution_brief_synthesis",
        operation=AiOperationName.UGC_EXECUTION_BRIEF_SYNTHESIS.value,
        analysis_mode=settings.ai_mode,
        provider=settings.ai_provider,
        model=settings.resolve_openai_model(AiOperationName.UGC_EXECUTION_BRIEF_SYNTHESIS.value),
        prompt_version=prompt.prompt_version,
        response_schema_version=prompt.output_schema_version,
        schema_version=prompt.output_schema_version,
        request_hash=initial_hash,
        input_hash=initial_hash,
        input_summary=input_summary,
        endpoint_family="responses" if settings.ai_provider == "openai" else "chat_completions",
        prompt_name=prompt.prompt_name,
        request_id=f"ugc-execution-brief:{job.id}",
    )
    session.commit()
    operation_context = ViraldyOperationContextV1(
        operation=AiOperationName.UGC_EXECUTION_BRIEF_SYNTHESIS,
        request_id=f"ugc-execution-brief:{model_run.id}",
        workspace_id=job.workspace_id,
        target_market=typed_context.market,
        source_artifact_ids=[loaded.asset_id],
        source_version_ids=[loaded.asset_version_id],
        seller_constraints=typed_context.model_dump(mode="json"),
        operation_payload={
            "review_id": typed_result.review_id,
            "recommendation_ids": [item.id for item in recommendations],
            "recommendations": [item.model_dump(mode="json") for item in recommendations],
            "evidence": [item.model_dump(mode="json") for item in typed_evidence.items],
        },
        schema_version=prompt.output_schema_version,
        prompt_version=prompt.prompt_version,
    )
    try:
        execution = execute_structured_operation(
            settings,
            operation_context,
            UGCExecutionBriefSynthesisV1,
        )
        synthesis = UGCExecutionBriefSynthesisV1.model_validate(execution.parsed_output)
        enriched = apply_execution_brief_synthesis(typed_result, synthesis)
        if execution.input_hash and execution.request_hash:
            model_runs.update_identity(
                model_run,
                input_hash=execution.input_hash,
                request_hash=execution.request_hash,
            )
        model_runs.complete(
            model_run,
            {
                "recommendation_patch_count": len(synthesis.recommendation_patches),
                "creator_revision_message": bool(synthesis.creator_revision_message),
            },
            execution.http_status,
            execution.provider_request_id,
            execution.latency_ms,
            usage_json=execution.usage.model_dump(mode="json"),
            repair_attempt_count=execution.repair_attempt_count,
        )
        return _with_execution_brief_provenance(
            enriched,
            {"status": "completed", "model_run_id": str(model_run.id)},
        )
    except AppError as exc:
        _fail_execution_brief_run(model_runs, model_run, exc)
        return _with_execution_brief_provenance(
            typed_result,
            {
                "status": "fallback",
                "model_run_id": str(model_run.id),
                "reason": exc.code,
            },
        )
    except Exception:
        model_runs.fail(
            model_run,
            "UGC_EXECUTION_BRIEF_INVALID",
            "Execution brief output was invalid.",
            safe_error_message="Execution brief output was invalid; deterministic review retained.",
        )
        return _with_execution_brief_provenance(
            typed_result,
            {
                "status": "fallback",
                "model_run_id": str(model_run.id),
                "reason": "invalid_output",
            },
        )


def _with_execution_brief_provenance(result: object, synthesis: dict[str, object]) -> object:
    from viraldy.modules.domain_intelligence.schemas import UGCReviewResult

    typed_result = cast(UGCReviewResult, result)
    return typed_result.model_copy(
        update={
            "analysis_provenance": {
                **typed_result.analysis_provenance,
                "execution_brief_provider": (
                    "openai" if synthesis.get("status") == "completed" else "deterministic_fallback"
                ),
                "execution_brief_synthesis": synthesis,
            }
        }
    )


def _fail_execution_brief_run(repository: object, model_run: object, error: AppError) -> None:
    details = error.details
    repository.fail(
        model_run,
        error.code,
        error.message,
        http_status=(
            details.get("http_status") if isinstance(details.get("http_status"), int) else None
        ),
        provider_request_id=(
            details.get("provider_request_id")
            if isinstance(details.get("provider_request_id"), str)
            else None
        ),
        repair_attempt_count=(
            details.get("repair_attempt_count")
            if isinstance(details.get("repair_attempt_count"), int)
            else None
        ),
        safe_error_message="Execution brief synthesis failed; deterministic review retained.",
    )


def _update_tiktok_stage(
    job: ProcessingJobModel,
    run: TikTokScoreRunModel,
    job_repository: WorkerJobRepository,
    score_repository: SyncTikTokScoreRepository,
    session: Session,
    stage: str,
) -> None:
    progress = _TIKTOK_STAGE_PROGRESS[stage]
    job_repository.update_progress(job, progress, stage)
    score_repository.update_stage(run, stage, processing_job_id=job.id)
    session.commit()


def _completed_tiktok_score_output(
    job: ProcessingJobModel,
    run: TikTokScoreRunModel,
) -> dict[str, object]:
    result = run.result_json or {}
    output: dict[str, object] = {
        "score_run_id": str(run.id),
        "asset_version_id": str(run.asset_version_id),
        "structural_score": result.get("overall_score", run.structural_score),
        "action": result.get(
            "creative_structure_decision",
            run.creative_structure_decision,
        ),
        "confidence": result.get("overall_confidence", run.confidence),
        "analysis_mode": run.analysis_mode,
        "primary_model_run_id": (
            str(run.primary_model_run_id) if run.primary_model_run_id else None
        ),
    }
    comparison_id = job.input_json.get("comparison_id")
    if comparison_id is not None:
        output["comparison_id"] = str(comparison_id)
    return output


def _update_tiktok_score_failure_state(
    job: ProcessingJobModel,
    session: Session,
    failure_code: str,
    *,
    terminal: bool,
) -> None:
    if normalize_job_type(job.job_type) != JobType.TIKTOK_SCORE_RUN.value:
        return
    score_run_id = UUID(str(job.input_json.get("score_run_id") or job.subject_id))
    score_repository = SyncTikTokScoreRepository(session)
    run = score_repository.load_run_with_snapshots(job.workspace_id, score_run_id)
    if run is None:
        logger.warning(
            "tiktok_score_failure_run_not_found",
            job_id=str(job.id),
            score_run_id=str(score_run_id),
        )
        return
    if not terminal:
        score_repository.update_stage(run, "retrying", processing_job_id=job.id)
        return
    score_repository.mark_failed(
        run,
        failure_code,
        processing_job_id=job.id,
    )
    _record_tiktok_score_event(
        session,
        run,
        job,
        "tiktok_score_failed",
        {"failure_code": failure_code},
    )


def _persist_tiktok_comparison_if_requested(
    job: ProcessingJobModel,
    run: TikTokScoreRunModel,
    score_repository: SyncTikTokScoreRepository,
    after_result: TikTokScoreResultV2,
) -> UUID | None:
    raw_comparison_id = job.input_json.get("comparison_id")
    if raw_comparison_id is None:
        return None
    comparison_id = UUID(str(raw_comparison_id))
    comparison = score_repository.load_comparison(job.workspace_id, comparison_id)
    if comparison is None:
        raise AppError(
            "TIKTOK_SCORE_COMPARISON_NOT_FOUND",
            "The pending TikTok score comparison was not found.",
        )
    if comparison.after_score_run_id != run.id:
        raise AppError(
            "TIKTOK_SCORE_COMPARISON_RUN_MISMATCH",
            "The pending comparison did not target this revision score run.",
        )
    before_payload = score_repository.load_result_payload(
        job.workspace_id,
        comparison.before_score_run_id,
    )
    if before_payload is None:
        raise AppError(
            "TIKTOK_SCORE_COMPARISON_PARENT_RESULT_MISSING",
            "The parent TikTok score result was unavailable for comparison.",
        )
    before_result = TikTokScoreResultV2.model_validate(before_payload)
    accepted_fix_action_ids = [
        UUID(str(value)) for value in comparison.accepted_fix_action_ids_json
    ]
    comparison_result = compare_score_results(
        before_result,
        after_result,
        accepted_fix_action_ids,
    )
    comparison_payload = comparison_result.model_dump(mode="json")
    score_repository.persist_comparison_result(comparison, comparison_payload)
    for verification in comparison_result.actions_verified:
        if verification.status != "verified":
            continue
        score_repository.record_verified_action_event(
            comparison,
            verification.action_id,
            actor_user_id=_actor_user_id(job),
            details_json={
                "comparison_id": str(comparison.id),
                "verification": verification.model_dump(mode="json"),
            },
        )
    return comparison.id


def _validate_tiktok_run_media(
    job: ProcessingJobModel,
    run: TikTokScoreRunModel,
    loaded: AssetVersionSnapshot,
) -> None:
    if loaded.workspace_id != job.workspace_id or loaded.workspace_id != run.workspace_id:
        raise AppError(
            "TIKTOK_SCORE_WORKSPACE_MISMATCH",
            "TikTok score media did not match the snapshotted workspace.",
        )
    if loaded.asset_version_id != run.asset_version_id:
        raise AppError(
            "TIKTOK_SCORE_ASSET_VERSION_MISMATCH",
            "TikTok score media did not match the immutable asset version.",
        )
    if run.asset_id is not None and loaded.asset_id != run.asset_id:
        raise AppError(
            "TIKTOK_SCORE_ASSET_MISMATCH",
            "TikTok score media did not match the snapshotted asset.",
        )
    if (
        run.media_checksum_sha256 is not None
        and loaded.checksum_sha256 != run.media_checksum_sha256
    ):
        raise AppError(
            "TIKTOK_SCORE_MEDIA_CHECKSUM_MISMATCH",
            "TikTok score media checksum did not match the immutable run snapshot.",
        )


def _product_snapshot_from_run(
    run: TikTokScoreRunModel,
) -> ProductContextSnapshot | None:
    if run.product_context_snapshot_json is None:
        return None
    return ProductContextSnapshot.model_validate(run.product_context_snapshot_json)


def _direction_context_from_run(
    run: TikTokScoreRunModel,
) -> tuple[CreativeDirectionContextV1 | None, str | None]:
    snapshot = run.creative_direction_context_snapshot_json
    if snapshot is None:
        uncertainty = (
            "optional creative direction unavailable"
            if run.creative_direction_lookup_error is not None
            else None
        )
        return None, uncertainty
    try:
        return CreativeDirectionContextV1.model_validate(snapshot), None
    except Exception:
        logger.warning(
            "tiktok_score_direction_snapshot_invalid",
            score_run_id=str(run.id),
            direction_context_version=run.creative_direction_context_version,
        )
        return None, "optional creative direction unavailable"


def _append_direction_uncertainty(
    result: TikTokScoreResultV2,
    uncertainty: str | None,
) -> TikTokScoreResultV2:
    if uncertainty is None or uncertainty in result.uncertainty:
        return result
    return result.model_copy(update={"uncertainty": [*result.uncertainty, uncertainty]})


def _profile_selection_confidence(run: TikTokScoreRunModel) -> float:
    if run.profile_selection_confidence is not None:
        return float(run.profile_selection_confidence)
    if run.profile_selection_mode in {"user_selected", "user_overridden", "inherited"}:
        return 1.0
    return 0.0


def _optional_job_string(job: ProcessingJobModel, key: str) -> str | None:
    value = job.input_json.get(key)
    return str(value) if value is not None and str(value).strip() else None


def _optional_search_context_string(
    job: ProcessingJobModel,
    key: str,
) -> str | None:
    search_context = job.input_json.get("search_context")
    if isinstance(search_context, dict):
        value = search_context.get(key)
        if value is not None and str(value).strip():
            return str(value)
    return _optional_job_string(job, key)


def _model_provider_versions(
    existing: dict[str, object],
    evidence: list[EvidenceItemModel],
) -> dict[str, object]:
    media_versions = {
        (
            str(item.provider) if item.provider else None,
            str(item.model_version) if item.model_version else None,
            str(item.pipeline_version) if item.pipeline_version else None,
        )
        for item in evidence
    }
    return {
        **existing,
        "scorer": {
            "provider": "deterministic",
            "model_version": TIKTOK_SCORER_MODEL_VERSION,
        },
        "media_evidence": [
            {
                "provider": provider,
                "model_version": model_version,
                "pipeline_version": pipeline_version,
            }
            for provider, model_version, pipeline_version in sorted(
                media_versions,
                key=lambda value: tuple(item or "" for item in value),
            )
        ],
    }


def _validate_tiktok_result_snapshot(
    run: TikTokScoreRunModel,
    result: dict[str, object],
) -> None:
    result_hash = result.get("product_snapshot_hash")
    if (
        run.product_context_snapshot_hash is not None
        and result_hash != run.product_context_snapshot_hash
    ):
        raise AppError(
            "TIKTOK_SCORE_PRODUCT_SNAPSHOT_MISMATCH",
            "TikTok score result did not use the immutable Product Context snapshot.",
        )


def _record_tiktok_score_event(
    session: Session,
    run: TikTokScoreRunModel,
    job: ProcessingJobModel,
    event_type: str,
    extra: dict[str, object],
) -> None:
    SyncProductEventPublisher(session).record(
        event_type=event_type,  # type: ignore[arg-type]
        workspace_id=run.workspace_id,
        actor_user_id=_actor_user_id(job),
        subject_type="tiktok_score_run",
        subject_id=run.id,
        payload_json={
            "score_run_id": str(run.id),
            "asset_version_id": str(run.asset_version_id),
            "processing_job_id": str(job.id),
            "score_mode": run.score_mode,
            "score_profile": run.score_profile,
            "intended_use": run.intended_use,
            **extra,
        },
    )


def _record_recommendation(
    session: Session,
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


def _media_audio_available(metadata_json: dict[str, object]) -> bool | None:
    media = metadata_json.get("media")
    if not isinstance(media, dict):
        return None
    audio_stream_count = media.get("audio_stream_count")
    if isinstance(audio_stream_count, int | float):
        return audio_stream_count > 0
    has_audio = media.get("has_audio")
    return has_audio if isinstance(has_audio, bool) else None


def _actor_user_id(job: ProcessingJobModel) -> UUID | None:
    actor_user_id = job.input_json.get("actor_user_id")
    return UUID(str(actor_user_id)) if actor_user_id else None


def _product_context_schema_version(product_snapshot_json: dict[str, object] | None) -> str | None:
    if not product_snapshot_json:
        return None
    schema_version = product_snapshot_json.get("schema_version")
    return str(schema_version) if schema_version else None
