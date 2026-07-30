# Viraldy Backend

FastAPI API and Celery worker backend foundation.

## Commands

```bash
uv sync --all-extras --dev
uv run alembic upgrade head
uv run uvicorn viraldy.api.main:app --reload
uv run celery -A viraldy.worker.celery_app worker --loglevel=INFO --queues=default,maintenance
uv run celery -A viraldy.worker.celery_app beat --loglevel=INFO
uv run pytest
```

Local MVP fixture flow:

```bash
uv run alembic upgrade head
uv run python scripts/seed_local.py
AI_MODE=fixture uv run uvicorn viraldy.api.main:app --reload
AI_MODE=fixture uv run celery -A viraldy.worker.celery_app worker --loglevel=INFO --queues=default,maintenance
AI_MODE=fixture uv run celery -A viraldy.worker.celery_app beat --loglevel=INFO
```

`AI_MODE=fixture` only analyzes seeded demo assets with known fixture IDs. Unknown uploads
return `UNSUPPORTED_FIXTURE_ASSET`; use `AI_MODE=live` with `AI_BASE_URL`, `AI_API_KEY`,
`AI_TEXT_MODEL`, and `AI_VISION_MODEL` for live provider work.

OpenAPI export:

```bash
uv run python scripts/export_openapi.py
```
