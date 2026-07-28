# Viraldy Backend

FastAPI API and Celery worker backend foundation.

## Commands

```bash
uv sync --all-extras --dev
uv run alembic upgrade head
uv run uvicorn viraldy.api.main:app --reload
uv run celery -A viraldy.worker.celery_app worker --loglevel=INFO --queues=default
uv run pytest
```

OpenAPI export:

```bash
uv run python scripts/export_openapi.py
```
