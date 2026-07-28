#!/usr/bin/env sh
set -eu
exec celery -A viraldy.worker.celery_app worker --loglevel=INFO --queues=default
