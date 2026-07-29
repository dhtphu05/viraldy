from __future__ import annotations

import argparse

from sqlalchemy import select

from viraldy.modules.jobs.models import ProcessingJobEventModel, ProcessingJobModel
from viraldy.platform.database.session import SyncSessionFactory
from viraldy.worker.tasks.process_asset import process_mvp_job


def main() -> None:
    parser = argparse.ArgumentParser(description="Redispatch recoverable queued Viraldy jobs.")
    parser.add_argument("--limit", type=int, default=50)
    args = parser.parse_args()

    with SyncSessionFactory() as session:
        jobs = (
            session.execute(
                select(ProcessingJobModel)
                .where(
                    ProcessingJobModel.status.in_(("queued", "retrying")),
                    ProcessingJobModel.task_id.is_(None),
                )
                .order_by(ProcessingJobModel.created_at.asc())
                .limit(args.limit)
            )
            .scalars()
            .all()
        )
        for job in jobs:
            session.add(
                ProcessingJobEventModel(
                    workspace_id=job.workspace_id,
                    processing_job_id=job.id,
                    event_type="dispatch_requested",
                    status=job.status,
                    stage=job.stage,
                    progress=job.progress,
                    message="Redispatch requested.",
                    details_json={"source": "scripts/redispatch_jobs.py"},
                )
            )
            session.commit()
            result = process_mvp_job.delay(str(job.id))
            job.task_id = str(result.id)
            session.add(
                ProcessingJobEventModel(
                    workspace_id=job.workspace_id,
                    processing_job_id=job.id,
                    event_type="dispatch_succeeded",
                    status=job.status,
                    stage=job.stage,
                    progress=job.progress,
                    message="Redispatch succeeded.",
                    details_json={
                        "task_id": str(result.id),
                        "source": "scripts/redispatch_jobs.py",
                    },
                )
            )
            session.commit()
            print({"job_id": str(job.id), "task_id": str(result.id)})


if __name__ == "__main__":
    main()
