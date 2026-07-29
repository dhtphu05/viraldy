# Viraldy MVP Product Hardening Audit

Date: 2026-07-29
Branch: `hardening/keyless-product-hardening`
Baseline commit: `8549a37`

## Executive Status

Status: completed for keyless product hardening.

The MVP now runs both required flows end to end without paid model credentials:

- Quick TikTok Scorer.
- Product -> Reference Board -> Creative DNA -> Product Adaptation -> Campaign Pack -> UGC Preflight.

Both flows passed in:

- `AI_MODE=fixture`, using seeded deterministic assets.
- `AI_MODE=mock`, using a local OpenAI-compatible provider over HTTP, uploaded MP4 media, Docker Postgres, Redis, and MinIO.

Live mode was not run against a real vendor key. It was contract-validated to fail clearly when credentials/models are missing and to require environment configuration only.

## GitHub Bot Note

Local source does not contain GitHub Actions workflows or Dependabot configuration:

- `.github/pull_request_template.md` exists.
- `.github/workflows/*` does not exist locally.
- `.github/dependabot.yml` does not exist locally.

The open Dependabot PRs visible on GitHub are therefore controlled by GitHub repository or organization Dependabot settings, not by local code in this checkout.

## Infrastructure Used

Added `docker-compose.h9.yml` for repeatable local H9 verification without colliding with existing services:

- Postgres: `127.0.0.1:55432`
- Redis: `127.0.0.1:56379`
- MinIO: `127.0.0.1:59000`
- MinIO console: `127.0.0.1:59001`

Migration and seed completed against this Docker Postgres:

- Alembic revisions `0001`, `0002`, `0003` applied.
- Seeded workspace `1e49a78e-654b-4f3b-8794-23cc7034af58`.
- Seeded product `b51ce929-ed63-4fd5-9e4e-84a924d2c86d`.
- Seeded reference board `42c1f2c5-6dc3-4898-989c-1578ffdc27de`.

## Key Fixes From Runtime Verification

- Fixed real-Postgres FK ordering for uploads: `assets` are inserted before `asset_versions`, then `assets.current_version_id` is set.
- Fixed async SQLAlchemy refresh issues in reference analyze and campaign pack create/version endpoints.
- Ensured worker model metadata is available by importing the full SQLAlchemy model registry.
- Updated fixture smoke selection to choose the seeded reference by fixture asset, not first row.
- Added `ai_model_runs` tracking for mock/live media provider calls.
- Linked media model runs to Creative DNA, TikTok score, and Preflight records through `primary_model_run_id`.

## Verification Summary

Backend:

- `PYTHONPATH=.backend_deps:src .backend_deps/bin/ruff check src scripts tests`
  - Result: pass.
- `PYTHONPATH=.backend_deps:src .backend_deps/bin/pytest tests/unit -q --no-cov`
  - Result: `30 passed, 1 warning`.

Frontend:

- `pnpm -C apps/web lint`
  - Result: pass with 11 existing Fast Refresh warnings.
- `pnpm -C apps/web build`
  - Result: pass with existing bundle/chunk-size warnings.

Readiness:

- Fixture readiness:
  - `configured=true`, `mode=fixture`, `missing=[]`.
- Mock readiness:
  - `configured=true`, `mode=mock`, text/vision/audio capabilities enabled.
- Live readiness without credentials:
  - exit code `1`, `configured=false`, missing `ASR_PROVIDER`, `AI_BASE_URL`, `AI_TEXT_MODEL`, `AI_VISION_MODEL`, `ASR_MODEL`, `AI_API_KEY`.
  - No fallback to fixture.

Smoke E2E:

- Fixture smoke passed with jobs:
  - `2854fa30-334b-45b4-8166-c0f860cb92e5`
  - `674ae315-2277-48cc-9d4f-c5a1f6033046`
  - `dcfb9c91-b635-40e8-8891-6681ad3332b8`
- Mock-provider smoke passed with jobs:
  - `bc421768-a46d-45df-adf1-985b5b9a51bf`
  - `91ebe4cd-042d-421b-948e-643ea4f67b30`
  - `ea41e1a1-c220-4cb1-9957-554f6b73ea5b`

Postgres snapshots after mock tracking:

- `ai_model_runs` completed:
  - `audio_transcription=3`
  - `visual_observations=3`
  - `generate_adaptation=2`
- Linked mock records:
  - TikTok score records with `primary_model_run_id`: `2`
  - Creative DNA records with `primary_model_run_id`: `2`
  - Preflight records with `primary_model_run_id`: `1`
- Campaign pack versions:
  - `7` versions across `4` packs after repeated fixture/mock smoke runs.

## Residual Notes

- Real vendor behavior still requires first live smoke with actual credentials.
- The frontend lint warnings are not introduced by this hardening pass and remain non-blocking.
- Docker services were used only for local verification; no deployment was performed.
