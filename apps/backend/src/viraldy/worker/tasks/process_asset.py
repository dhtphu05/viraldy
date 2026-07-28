from __future__ import annotations

from uuid import UUID

import structlog

from viraldy.modules.assets.public import SyncAssetQueries
from viraldy.modules.campaign_packs.repository import SyncCampaignPackRepository
from viraldy.modules.creative_dna.service import SyncCreativeDnaBuilder
from viraldy.modules.jobs.repository import WorkerJobRepository
from viraldy.modules.media_analysis.service import SyncMediaEvidencePipeline
from viraldy.modules.preflight.repository import SyncPreflightRepository
from viraldy.modules.preflight.service import calculate_preflight_result
from viraldy.modules.recommendations.models import RecommendationModel
from viraldy.modules.references.repository import SyncReferenceRepository
from viraldy.modules.tiktok_scorer.models import TikTokScoreRunModel
from viraldy.modules.tiktok_scorer.repository import (
    RUBRIC_VERSION,
    RULE_VERSION,
    SyncTikTokScoreRepository,
)
from viraldy.modules.tiktok_scorer.scorer import score_tiktok_structure
from viraldy.platform.config.settings import get_settings
from viraldy.platform.database.session import create_worker_session
from viraldy.shared.errors.base import AppError
from viraldy.worker.celery_app import celery_app

logger = structlog.get_logger(__name__)


@celery_app.task(bind=True, autoretry_for=(RuntimeError,), retry_backoff=True, max_retries=3)  # type: ignore[misc]
def process_mvp_job(self, job_id: str) -> dict[str, object]:  # type: ignore[no-untyped-def]
    job_uuid = UUID(job_id)
    session = create_worker_session()
    repo = WorkerJobRepository(session)
    asset_queries = SyncAssetQueries(session)
    try:
        job = repo.load_job(job_uuid)
        if job is None:
            raise RuntimeError("job_not_found")
        logger.info("processing_job_started", job_id=job_id, workspace_id=str(job.workspace_id))
        repo.mark_running(job)
        session.commit()
        output = _execute_job(job, repo, asset_queries, session)
        repo.mark_completed(job, output)
        session.commit()
        logger.info("processing_job_completed", job_id=job_id)
        return output
    except AppError as exc:
        session.rollback()
        job = repo.load_job(job_uuid)
        if job is not None:
            repo.mark_failed(job, exc.code, exc.message)
            session.commit()
        logger.info("processing_job_failed_app_error", job_id=job_id, code=exc.code)
        return {"error_code": exc.code, "error_message": exc.message}
    except Exception as exc:
        session.rollback()
        job = repo.load_job(job_uuid)
        if job is not None and job.attempt_count >= job.max_attempts:
            repo.mark_failed(job, "PROCESS_ASSET_FAILED", "Asset processing failed.")
            session.commit()
        logger.exception("processing_job_failed", job_id=job_id)
        raise self.retry(exc=exc) from exc
    finally:
        session.close()


process_asset_placeholder = process_mvp_job


def _execute_job(
    job, repo: WorkerJobRepository, asset_queries: SyncAssetQueries, session
) -> dict[str, object]:
    if job.job_type == "process_asset":
        asset_id = UUID(str(job.input_json["asset_id"]))
        asset_version_id = UUID(str(job.input_json["asset_version_id"]))
        repo.update_progress(job, 25, "loading_asset")
        session.commit()
        loaded = asset_queries.load_asset_version(asset_id, asset_version_id)
        if loaded is None:
            raise RuntimeError("asset_version_not_found")
        repo.update_progress(job, 40, "probing_media")
        session.commit()
        evidence = SyncMediaEvidencePipeline(session, get_settings()).process(
            loaded, "process_asset"
        )
        repo.update_progress(job, 90, "persisting_results")
        session.commit()
        return {
            "processor": "media-evidence-pipeline",
            "asset_id": str(asset_id),
            "asset_version_id": str(asset_version_id),
            "evidence_count": len(evidence),
            "analysis_mode": get_settings().ai_mode,
        }
    if job.job_type == "analyze_reference":
        return _analyze_reference(job, repo, asset_queries, session)
    if job.job_type == "score_tiktok_asset":
        return _score_tiktok_asset(job, repo, asset_queries, session)
    if job.job_type == "run_ugc_preflight":
        return _run_ugc_preflight(job, repo, asset_queries, session)
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
    evidence = SyncMediaEvidencePipeline(session, get_settings()).process(loaded, run_type)
    repo.update_progress(job, 60, "extracting_visual_evidence")
    session.commit()
    return loaded, evidence


def _analyze_reference(
    job, repo: WorkerJobRepository, asset_queries: SyncAssetQueries, session
) -> dict[str, object]:
    loaded, evidence = _process_media(job, repo, asset_queries, session, "analyze_reference")
    reference_id = UUID(str(job.input_json["reference_id"]))
    repo.update_progress(job, 72, "building_creative_dna")
    dna = SyncCreativeDnaBuilder(session).build(
        job.workspace_id, loaded.asset_version_id, reference_id, evidence, get_settings().ai_mode
    )
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
    loaded, evidence = _process_media(job, repo, asset_queries, session, "score_tiktok_asset")
    score_run_id = UUID(str(job.input_json["score_run_id"]))
    repo.update_progress(job, 70, "calculating_score")
    dna = SyncCreativeDnaBuilder(session).build(
        job.workspace_id, loaded.asset_version_id, None, evidence, get_settings().ai_mode
    )
    result = score_tiktok_structure(evidence)
    run = SyncTikTokScoreRepository(session).get(job.workspace_id, score_run_id)
    if run is None:
        raise RuntimeError("score_run_not_found")
    SyncTikTokScoreRepository(session).complete(
        run, dna.id, result, "fixture_scoring_v1" if get_settings().ai_mode == "fixture" else None
    )
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
    loaded, evidence = _process_media(job, repo, asset_queries, session, "run_ugc_preflight")
    preflight_run_id = UUID(str(job.input_json["preflight_run_id"]))
    pack_version_id = UUID(str(job.input_json["campaign_pack_version_id"]))
    repo.update_progress(job, 65, "calculating_score")
    structural_result = score_tiktok_structure(evidence)
    structural_run = TikTokScoreRunModel(
        workspace_id=job.workspace_id,
        asset_version_id=loaded.asset_version_id,
        status="completed",
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
    result = calculate_preflight_result(structural_result, pack_version.brief_json)
    run = SyncPreflightRepository(session).get(job.workspace_id, preflight_run_id)
    if run is None:
        raise RuntimeError("preflight_run_not_found")
    SyncPreflightRepository(session).complete(
        run,
        result,
        structural_run.id,
        "fixture_preflight_v1" if get_settings().ai_mode == "fixture" else None,
    )
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
    session.add(
        RecommendationModel(
            workspace_id=workspace_id,
            subject_type=subject_type,
            subject_id=subject_id,
            recommendation_type=recommendation_type,
            action=str(result["action"]),
            confidence=str(result["confidence"]),
            reasoning=str(result.get("summary") or f"Action: {result['action']}"),
            evidence_json={
                "evidence_ids": result.get("evidence_ids", []),
                "blockers": result.get("blockers", []),
            },
            assumptions_json=[],
            model_version="fixture_recommendation_v1"
            if get_settings().ai_mode == "fixture"
            else None,
            rule_version=str(result["rule_version"]),
            source_run_id=subject_id,
        )
    )
