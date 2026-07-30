from __future__ import annotations

from celery import Celery

from viraldy.platform.config.settings import get_settings

settings = get_settings()

celery_app = Celery(
    "viraldy",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["viraldy.worker.tasks.process_asset"],
)

celery_app.conf.update(
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_soft_time_limit=300,
    task_time_limit=360,
    task_track_started=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_default_queue="default",
    task_routes={
        "viraldy.worker.tasks.process_asset.recover_stale_processing_jobs": {
            "queue": "maintenance"
        },
        "viraldy.worker.tasks.process_asset.retry_pending_storage_deletions": {
            "queue": "maintenance"
        }
    },
    beat_schedule={
        "recover-stale-processing-jobs": {
            "task": "viraldy.worker.tasks.process_asset.recover_stale_processing_jobs",
            "schedule": 300.0,
        },
        "retry-pending-storage-deletions": {
            "task": "viraldy.worker.tasks.process_asset.retry_pending_storage_deletions",
            "schedule": 300.0,
        }
    },
)
