# Refactor Baseline

Date: 2026-07-11

This baseline was captured before moving the backend from the current deep DDD/Clean Architecture layout to the lean modular monolith layout.

## Commands Run

- `uv run ruff check .` from `apps/backend`: passed.
- `uv run ruff format --check .` from `apps/backend`: passed, 174 files already formatted.
- `uv run mypy src` from `apps/backend`: passed, no issues in 163 source files.
- `uv run pytest tests/unit tests/contract tests/architecture` from `apps/backend`: passed, 15 tests passed, total coverage 72.76%.
- `uv run python scripts/export_openapi.py` from `apps/backend`: exported `docs/api/openapi.json`.
- `uv run alembic heads` from `apps/backend`: `0001_initial_foundation (head)`.

Docker build and Docker-backed integration tests were intentionally not run for this baseline because the current work is in the local dev environment and the user explicitly requested no Docker build.

## API Contract Snapshot

- Snapshot: `docs/refactor/openapi-baseline.json`
- SHA-256: `d3ba68f1b7b2ec07936f0ee98133a4e2b411a95c6a6c40bfac83f2718b7a9da1`

## Migration Head

- Alembic head: `0001_initial_foundation`
- Current migration file: `apps/backend/alembic/versions/0001_initial_foundation.py`

No migration rewrite is planned for the refactor. Any schema change must be added as a new Alembic migration.
