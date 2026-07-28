from __future__ import annotations

from uuid import UUID

import structlog

from viraldy.modules.assets.public import SyncAssetQueries
from viraldy.modules.jobs.repository import WorkerJobRepository
from viraldy.platform.database.session import create_worker_session
from viraldy.worker.celery_app import celery_app

logger = structlog.get_logger(__name__)


@celery_app.task(bind=True, autoretry_for=(RuntimeError,), retry_backoff=True, max_retries=3)  # type: ignore[misc]
def process_asset_placeholder(self, job_id: str) -> dict[str, object]:  # type: ignore[no-untyped-def]
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
        asset_id = UUID(str(job.input_json["asset_id"]))
        asset_version_id = UUID(str(job.input_json["asset_version_id"]))
        repo.update_progress(job, 25, "loading_asset")
        session.commit()
        loaded = asset_queries.load_asset_version(asset_id, asset_version_id)
        if loaded is None:
            raise RuntimeError("asset_version_not_found")
        repo.update_progress(job, 50, "validating_metadata")
        session.commit()
        repo.update_progress(job, 75, "writing_output")
        output: dict[str, object] = {
            "processor": "foundation-placeholder",
            "asset_id": str(asset_id),
            "asset_version_id": str(asset_version_id),
            "validated": True,
            "artifacts": [],
            "message": "Asset processing foundation is operational.",
        }
        repo.mark_completed(job, output)
        session.commit()
        logger.info("processing_job_completed", job_id=job_id)
        return output
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
