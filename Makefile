BACKEND_DIR=apps/backend
WEB_DIR=apps/web
SMOKE_MODE ?= fixture
SMOKE_ARGS ?=

.PHONY: setup infra-up infra-down backend-install web-install api worker beat web-dev web-build web-lint dev migrate migration downgrade seed openapi lint format typecheck test test-unit test-integration test-contract smoke smoke-fixture smoke-mock smoke-release-fixture smoke-release-mock security docker-build logs clean

setup: backend-install

infra-up:
	docker compose up -d postgres redis minio minio-init

infra-down:
	docker compose down

backend-install:
	cd $(BACKEND_DIR) && uv sync --all-extras --dev

web-install:
	cd $(WEB_DIR) && pnpm install

api:
	cd $(BACKEND_DIR) && uv run uvicorn viraldy.api.main:app --host $${API_HOST:-0.0.0.0} --port $${API_PORT:-8000} --reload

worker:
	cd $(BACKEND_DIR) && uv run celery -A viraldy.worker.celery_app worker --loglevel=INFO --queues=default,maintenance

beat:
	cd $(BACKEND_DIR) && uv run celery -A viraldy.worker.celery_app beat --loglevel=INFO

web-dev:
	cd $(WEB_DIR) && pnpm dev

web-build:
	cd $(WEB_DIR) && pnpm build

web-lint:
	cd $(WEB_DIR) && pnpm lint

dev:
	$(MAKE) infra-up
	$(MAKE) api

migrate:
	cd $(BACKEND_DIR) && uv run alembic upgrade head

migration:
	cd $(BACKEND_DIR) && uv run alembic revision --autogenerate -m "$(name)"

downgrade:
	cd $(BACKEND_DIR) && uv run alembic downgrade -1

seed:
	cd $(BACKEND_DIR) && uv run python scripts/seed_local.py

openapi:
	cd $(BACKEND_DIR) && uv run python scripts/export_openapi.py

lint:
	cd $(BACKEND_DIR) && uv run ruff check .

format:
	cd $(BACKEND_DIR) && uv run ruff format .

typecheck:
	cd $(BACKEND_DIR) && uv run mypy src

test:
	cd $(BACKEND_DIR) && uv run pytest

test-unit:
	cd $(BACKEND_DIR) && uv run pytest tests/unit

test-integration:
	cd $(BACKEND_DIR) && uv run pytest tests/integration

test-contract:
	cd $(BACKEND_DIR) && uv run pytest tests/contract

smoke:
	cd $(BACKEND_DIR) && uv run python scripts/smoke_mvp_flow.py --expect-mode $(SMOKE_MODE) $(SMOKE_ARGS)

smoke-fixture:
	$(MAKE) smoke SMOKE_MODE=fixture

smoke-mock:
	$(MAKE) smoke SMOKE_MODE=mock

smoke-release-fixture:
	$(MAKE) smoke SMOKE_MODE=fixture SMOKE_ARGS="--isolated-lifecycle --verify-db"

smoke-release-mock:
	$(MAKE) smoke SMOKE_MODE=mock SMOKE_ARGS="--isolated-lifecycle --verify-db"

security:
	cd $(BACKEND_DIR) && uv run bandit -q -r src && uv run pip-audit

docker-build:
	docker build -f infrastructure/docker/backend.Dockerfile --target runtime -t viraldy-backend:local .

logs:
	docker compose logs -f api worker

clean:
	rm -rf $(BACKEND_DIR)/.pytest_cache $(BACKEND_DIR)/.ruff_cache $(BACKEND_DIR)/.mypy_cache $(BACKEND_DIR)/htmlcov $(BACKEND_DIR)/.coverage
