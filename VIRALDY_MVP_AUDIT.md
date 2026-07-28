# Viraldy MVP Audit

Date: 2026-07-28  
Repository: `/Users/mac/Desktop/Viraldy`  
Goal source: `VIRALDY_MVP_GOAL.md`  
Audit status: MVP fixture-mode completed and verified

## 1. Executive Summary

The Viraldy Creative Intelligence MVP has been implemented on top of the existing Lean Modular Monolith.

The implemented MVP supports the two required core flows:

1. Quick TikTok Scorer
   - Upload or select a TikTok/UGC asset.
   - Process media through the worker job path.
   - Persist artifacts and normalized evidence.
   - Calculate a deterministic TikTok Structure Score.
   - Return action label, blockers, fixes, confidence, and evidence links.

2. Full Creative Intelligence Loop
   - Create/select product.
   - Create reference board and attach reference asset.
   - Analyze reference into Creative DNA.
   - Adapt Creative DNA to a product.
   - Generate an editable, versioned Campaign Pack.
   - Run UGC Preflight against a Campaign Pack version.
   - Return final score, action, blockers, fixes, recommendation record, and creator-facing revision message.

The fixture-mode MVP has no remaining blocker. Live AI provider paths are wired and schema-validated, but were not exercised against a real provider because no credentials were supplied.

## 2. Current Runtime Status

- Goal was marked complete.
- Frontend dev server is reachable at `http://localhost:8080/mvp`.
- Backend was smoke-started with Uvicorn on `127.0.0.1:8011`; `/health` returned HTTP 200.
- Celery worker was smoke-started with memory broker; `process_mvp_job` was registered and worker became ready.
- Full docker compose stack was not started end-to-end in this shell.

## 3. Backend Scope Implemented

New backend modules were added under `apps/backend/src/viraldy/modules/`:

- `reference_boards`
- `references`
- `media_analysis`
- `creative_dna`
- `tiktok_scorer`
- `adaptations`
- `campaign_packs`
- `preflight`

Existing modules extended:

- `assets`
  - Added public asset snapshot/query contracts.
  - Exposed asset repository through `public.py` for module-boundary compliance.
- `jobs`
  - Added generic MVP job creation.
  - Added idempotent job lookup public contract.
  - Added duplicate dispatch prevention for existing idempotent jobs.
- `recommendations`
  - Reused for TikTok score and preflight decision records.

Platform changes:

- `platform/config/settings.py`
  - Added live/fixture AI settings.
  - Added ASR/OCR/provider model settings.
- `platform/storage/ports.py`
  - Added object download and file upload capabilities.
- `platform/storage/s3.py`
  - Implemented S3-compatible download/upload methods.
- `platform/database/models.py`
  - Registered new SQLAlchemy models for Alembic metadata.

## 4. Migration Scope

New migration:

- `apps/backend/alembic/versions/0002_creative_intelligence_mvp.py`

Tables added:

- `reference_boards`
- `references`
- `media_artifacts`
- `evidence_items`
- `creative_dna_versions`
- `tiktok_score_runs`
- `adaptation_runs`
- `campaign_packs`
- `campaign_pack_versions`
- `preflight_runs`

Migration verification:

- Applied successfully to a clean Postgres 16.6 testcontainer.
- Preserved existing `0001_initial_foundation`.

## 5. API Surface Added

Routers were registered in `apps/backend/src/viraldy/api/main.py`.

Added endpoint groups:

- Reference Boards
- References
- Media Analysis
- Creative DNA
- TikTok Scores
- Adaptations
- Campaign Packs
- Preflight Runs

Representative endpoints:

- `POST /api/v1/workspaces/{workspace_id}/reference-boards`
- `GET /api/v1/workspaces/{workspace_id}/reference-boards`
- `POST /api/v1/workspaces/{workspace_id}/references`
- `POST /api/v1/workspaces/{workspace_id}/references/{reference_id}/analyze`
- `GET /api/v1/workspaces/{workspace_id}/references/{reference_id}/creative-dna`
- `GET /api/v1/workspaces/{workspace_id}/assets/{asset_id}/media-analysis`
- `POST /api/v1/workspaces/{workspace_id}/tiktok-scores`
- `GET /api/v1/workspaces/{workspace_id}/tiktok-scores/{score_run_id}`
- `POST /api/v1/workspaces/{workspace_id}/adaptations`
- `GET /api/v1/workspaces/{workspace_id}/adaptations/{adaptation_id}`
- `POST /api/v1/workspaces/{workspace_id}/campaign-packs`
- `GET /api/v1/workspaces/{workspace_id}/campaign-packs`
- `GET /api/v1/workspaces/{workspace_id}/campaign-packs/{campaign_pack_id}`
- `PATCH /api/v1/workspaces/{workspace_id}/campaign-packs/{campaign_pack_id}`
- `POST /api/v1/workspaces/{workspace_id}/campaign-packs/{campaign_pack_id}/versions`
- `GET /api/v1/workspaces/{workspace_id}/campaign-packs/{campaign_pack_id}/versions`
- `POST /api/v1/workspaces/{workspace_id}/preflight-runs`
- `GET /api/v1/workspaces/{workspace_id}/preflight-runs/{preflight_run_id}`

FastAPI app smoke imported with 21 routes.

## 6. Worker And Job Processing

Main worker task:

- `viraldy.worker.tasks.process_asset.process_mvp_job`

Compatibility alias preserved:

- `process_asset_placeholder = process_mvp_job`

Supported job types:

- `process_asset`
- `analyze_reference`
- `score_tiktok_asset`
- `run_ugc_preflight`

Worker behavior:

- Loads persisted job by stable ID.
- Marks job running.
- Updates progress/stage.
- Runs media evidence pipeline.
- Persists outputs.
- Marks job completed or failed.
- Converts expected `AppError` failures into failed job rows.

Idempotency audit:

- `JobService` now dispatches only newly created jobs.
- Existing idempotent jobs are returned without duplicate enqueue.
- TikTok score and preflight creation now avoid creating orphan runs when the same idempotency key is retried.

## 7. Media Pipeline

Fixture mode:

- Supports seeded demo fixtures only.
- Rejects unknown fixture files with `UNSUPPORTED_FIXTURE_ASSET`.
- Does not fabricate results for arbitrary assets.
- Persists artifacts and evidence tied to checksums/fixture metadata.

Live mode:

- Validates required provider settings.
- Downloads source object from storage.
- Uses ffprobe for metadata.
- Uses ffmpeg for thumbnail, audio extraction, and sample frames.
- Uploads generated artifacts.
- Calls OpenAI-compatible ASR and vision/chat providers.
- Validates provider JSON through Pydantic contracts.
- Uses `TemporaryDirectory` for cleanup.

Live missing-credential behavior:

```text
AI_PROVIDER_NOT_CONFIGURED Live AI mode requires: AI_BASE_URL, AI_API_KEY, AI_TEXT_MODEL, AI_VISION_MODEL.
```

Required live env:

- `AI_MODE=live`
- `AI_BASE_URL`
- `AI_API_KEY`
- `AI_TEXT_MODEL`
- `AI_VISION_MODEL`
- `ASR_PROVIDER`
- `ASR_MODEL`
- `OCR_PROVIDER`
- `OCR_MODEL`
- `AI_REQUEST_TIMEOUT_SECONDS`
- `AI_MAX_RETRIES`

## 8. Creative Intelligence Features

Creative DNA:

- Adds taxonomy versioning.
- Stores prompt version.
- Stores fixture/live analysis mode.
- Stores confidence.
- Links conclusions to evidence IDs.
- Links DNA to reference and asset version.

TikTok Scorer:

- Deterministic scoring from evidence.
- Versioned rubric and rules.
- Dimension scores.
- Hard blockers.
- Action mapping.
- Prioritized fixes.
- Recommendation record creation.

Adaptation:

- Product + Creative DNA input.
- Fixture mode returns keep/change/avoid.
- Returns exactly three differentiated concepts.
- Live provider prompt/schema implemented.
- Results are persisted and structured.

Campaign Pack:

- Generates structured creator brief.
- Contains hooks, scripts, storyboard, must-show items, CTA, claim guardrails, and revision checklist.
- Version 1 is persisted on creation.
- Edits create new versions.
- Historical versions remain accessible.

UGC Preflight:

- Reuses media pipeline.
- Reuses TikTok structural scorer.
- Calculates brief alignment.
- Applies hard blocker action mapping.
- Calculates deterministic final preflight score.
- Returns action label, blockers, fixes, evidence, and revision message.
- Creates recommendation record.

## 9. Frontend Scope Implemented

New route:

- `/mvp`

Files added/extended:

- `apps/web/src/features/mvp-flow/routes/mvp-route.tsx`
- `apps/web/src/routes/mvp.tsx`
- `apps/web/src/shared/api/*`
- `apps/web/src/widgets/app-shell/app-sidebar.tsx`
- `apps/web/src/routeTree.gen.ts`

Implemented UI capabilities:

- Upload through presigned URL.
- Job polling.
- Quick TikTok Scorer panel.
- Reference DNA panel.
- Product adaptation flow.
- Campaign Pack editor.
- Campaign Pack version save/history.
- UGC Preflight panel.
- Copy revision message action.
- Fixture/live mode badges.
- Empty/loading/error states.
- Core navigation from app sidebar.

Frontend route status:

- `curl http://localhost:8080/mvp` returned OK.

## 10. Seed Data

Seed script updated:

- `apps/backend/scripts/seed_local.py`

Seed creates:

- Local user.
- Local workspace.
- Demo product: `CounterSpace Rack`.
- Demo reference board: `Demo Creative Research`.
- Known reference fixture: `viraldy-demo-reference-v1`.
- Known quick-score fixture: `viraldy-demo-quick-v1`.
- Known fixable UGC fixture: `viraldy-demo-ugc-fixable-v1`.
- Reference record attached to demo board/product/asset.

## 11. Verification Commands And Results

Backend formatting/lint:

```text
PYTHONPATH=.backend_deps:src python -m ruff format src scripts alembic tests
PYTHONPATH=.backend_deps:src python -m ruff check src scripts alembic tests
```

Result:

```text
All checks passed.
```

Backend tests:

```text
PYTHONPATH=.backend_deps:src python -m pytest tests -q --no-cov
```

Result:

```text
23 passed
```

Backend import:

```text
from viraldy.api.main import create_app
app = create_app()
```

Result:

```text
routes 21
```

API smoke:

```text
uvicorn viraldy.api.main:app --host 127.0.0.1 --port 8011
curl http://127.0.0.1:8011/health
```

Result:

```json
{"data":{"status":"ok"},"meta":{"request_id":"...","pagination":null},"error":null}
```

Celery smoke:

```text
CELERY_BROKER_URL=memory:// CELERY_RESULT_BACKEND=cache+memory:// celery -A viraldy.worker.celery_app worker --loglevel=INFO --pool=solo --concurrency=1
```

Result:

```text
task registered: viraldy.worker.tasks.process_asset.process_mvp_job
worker ready
```

Fixture smoke with clean Postgres testcontainer:

```text
alembic upgrade head
seed_local
process analyze_reference job
process score_tiktok_asset job
process run_ugc_preflight job
```

Result:

```text
analyze_evidence: 10
score: 78
score_action: organic_ready_or_small_test
preflight: 68
preflight_action: revise
recommendations: 2
```

Frontend lint:

```text
pnpm lint
```

Result:

```text
0 errors
11 warnings
```

Warnings are existing Fast Refresh warnings in shared/legacy UI files:

- `analysis-jobs-runner.tsx`
- `creative-toolbar.tsx`
- `filter-sheet.tsx`
- `badge.tsx`
- `button.tsx`
- `form.tsx`
- `navigation-menu.tsx`
- `sidebar.tsx`
- `toggle.tsx`

Frontend build:

```text
pnpm build
```

Result:

```text
passed
```

Build warning:

- Some chunks exceed 500 kB after minification.
- This is not a functional failure.
- Code splitting can be addressed later.

Frontend route smoke:

```text
curl http://localhost:8080/mvp
```

Result:

```text
frontend_mvp_ok
```

## 12. Current Git Status Summary

Modified tracked files:

- `.env.example`
- `apps/backend/README.md`
- `apps/backend/scripts/seed_local.py`
- `apps/backend/src/viraldy/api/main.py`
- `apps/backend/src/viraldy/modules/assets/public.py`
- `apps/backend/src/viraldy/modules/jobs/dispatcher.py`
- `apps/backend/src/viraldy/modules/jobs/public.py`
- `apps/backend/src/viraldy/modules/jobs/repository.py`
- `apps/backend/src/viraldy/modules/jobs/service.py`
- `apps/backend/src/viraldy/platform/config/settings.py`
- `apps/backend/src/viraldy/platform/database/models.py`
- `apps/backend/src/viraldy/platform/storage/ports.py`
- `apps/backend/src/viraldy/platform/storage/s3.py`
- `apps/backend/src/viraldy/worker/celery_app.py`
- `apps/backend/src/viraldy/worker/tasks/process_asset.py`
- `apps/backend/tests/unit/test_job_service.py`
- `apps/web/README.md`
- `apps/web/src/routeTree.gen.ts`
- `apps/web/src/widgets/app-shell/app-sidebar.tsx`

Untracked files/directories:

- `VIRALDY_MVP_GOAL.md`
- `VIRALDY_MVP_AUDIT.md`
- `apps/backend/alembic/versions/0002_creative_intelligence_mvp.py`
- `apps/backend/src/viraldy/modules/adaptations/`
- `apps/backend/src/viraldy/modules/campaign_packs/`
- `apps/backend/src/viraldy/modules/creative_dna/`
- `apps/backend/src/viraldy/modules/media_analysis/`
- `apps/backend/src/viraldy/modules/preflight/`
- `apps/backend/src/viraldy/modules/reference_boards/`
- `apps/backend/src/viraldy/modules/references/`
- `apps/backend/src/viraldy/modules/tiktok_scorer/`
- `apps/web/src/features/mvp-flow/`
- `apps/web/src/routes/mvp.tsx`
- `apps/web/src/shared/api/`

Generated artifacts were cleaned after verification:

- `.backend_deps`
- `.pytest_cache`
- `.ruff_cache`
- `__pycache__`
- frontend `.output`
- Nitro generated cache

## 13. Known Limitations

Fixture-mode MVP is complete. The following production/live checks remain intentionally outside this MVP verification:

- Real live AI provider call was not executed because credentials were not supplied.
- Full `docker compose up` stack was not started end-to-end in this shell.
- Redis-backed Celery worker was not smoke-tested against local Redis because Redis local was not running.
- MinIO/S3 object roundtrip was not smoke-tested through full compose.
- Browser E2E automation was not added.
- Frontend chunk-size optimization was not performed.
- Production security hardening was not performed.
- Provider cost/rate-limit behavior was not hardened.

## 14. Recommended Next Steps

1. Review the untracked new module files and tracked diffs.
2. Start full local stack with Docker Compose when Docker/Redis/MinIO are available.
3. Run:

```text
docker compose up postgres redis minio minio-init
```

4. Apply migration and seed:

```text
cd apps/backend
alembic upgrade head
python scripts/seed_local.py
```

5. Start API and worker against Redis:

```text
uvicorn viraldy.api.main:app --host 0.0.0.0 --port 8000
celery -A viraldy.worker.celery_app worker --loglevel=INFO --queues=default
```

6. Exercise `/mvp` in browser with the seeded fixtures.
7. Add real `AI_MODE=live` credentials and run a live-provider smoke with a small sample asset.
8. Add a focused E2E regression test for the two MVP flows.

## 15. Audit Verdict

The requested MVP has been implemented with clear module structure and verified end-to-end in fixture mode.

The implementation is ready for human review and full local stack validation. No fixture-mode MVP blocker remains.
