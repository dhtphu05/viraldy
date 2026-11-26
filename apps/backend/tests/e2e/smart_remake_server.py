"""Child-process entry point: retain real route, storage, worker and DB behavior."""

from __future__ import annotations

import sys

from tests.e2e.smart_remake_providers import install_provider_seams


def main() -> None:
    install_provider_seams()
    if sys.argv[1] == "api":
        import uvicorn

        uvicorn.run(
            "viraldy.api.main:create_app", factory=True, host="127.0.0.1", port=int(sys.argv[2])
        )
    elif sys.argv[1] == "worker":
        from viraldy.worker.celery_app import celery_app

        # solo is a separate genuine Celery consumer, not eager task execution.
        celery_app.worker_main(
            [
                "worker",
                "--pool=solo",
                "--concurrency=1",
                "--loglevel=INFO",
                "--without-gossip",
                "--without-mingle",
                "--without-heartbeat",
            ]
        )
    else:
        raise SystemExit("Expected api or worker")


if __name__ == "__main__":
    main()
