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

Private-beta release smoke:

```bash
make smoke-release-fixture
make smoke-release-mock
```

Each release target creates an isolated workspace and Product Context, uploads
the reference and UGC media through presigned object-storage URLs, executes the
full PatternKit/ViralKit/Preflight learning loop, uploads an immutable UGC
revision, then hard-deletes the workspace and verifies both PostgreSQL deletion
audit state and an empty workspace object-storage prefix. Fixture mode requires
`DATABASE_SYNC_URL` so the test harness can attach a known fixture identity to
the newly uploaded asset versions; this metadata step is not exposed by the
production API.

Asset revision endpoints:

```text
POST /api/v1/workspaces/{workspace_id}/assets/{asset_id}/versions/upload-sessions
POST /api/v1/workspaces/{workspace_id}/assets/{asset_id}/versions/{asset_version_id}/complete-upload
GET  /api/v1/workspaces/{workspace_id}/assets/{asset_id}/versions
```

The initial upload must complete before a revision can be created. Completing
older revisions never moves `current_version_id` backward.

Domain Intelligence and recommendation-first UGC Review are documented in
[`docs/implementation/domain-intelligence-ugc-review-v1.md`](../../docs/implementation/domain-intelligence-ugc-review-v1.md).
After migrations, validate and activate the bundled policy pack with:

```bash
uv run python -m viraldy.scripts.import_domain_policy_pack \
  --pack resources/domain_intelligence/v1/DomainExpertPolicyPackV1.json \
  --schema resources/domain_intelligence/v1/DomainExpertPolicyPackV1.schema.json \
  --sources resources/domain_intelligence/v1/source_registry_v1.csv \
  --validate-only

uv run python -m viraldy.scripts.import_domain_policy_pack \
  --pack resources/domain_intelligence/v1/DomainExpertPolicyPackV1.json \
  --schema resources/domain_intelligence/v1/DomainExpertPolicyPackV1.schema.json \
  --sources resources/domain_intelligence/v1/source_registry_v1.csv \
  --activate-mvp
```

Campaign Pack export endpoint:

```text
POST /api/v1/workspaces/{workspace_id}/campaign-packs/{campaign_pack_id}/exports
```

The request accepts `{"format": "json"}` or `{"format": "text"}`. The response
contains a downloadable canonical snapshot of the current immutable Campaign
Pack version and records a first-party `campaign_pack_exported` event.

OpenAPI export:

```bash
uv run python scripts/export_openapi.py
```

Health probes:

```text
GET /health/live
GET /health/ready
GET /health/dependencies
GET /health/worker
```

`ready` checks API-serving dependencies only. `dependencies` also reports the
worker and AI provider configuration so their outage does not remove an
otherwise healthy API instance from service.

PatternKit/ViralKit evaluation from captured fixture, mock, or live output:

```bash
uv run python scripts/run_evaluation.py dataset.json --output-dir reports
```

The runner validates typed inputs and writes deterministic JSON and Markdown
reports. It evaluates captured outputs and does not invoke a model provider.
