# Current Architecture Audit

Date: 2026-07-11

Scope: audit before refactoring the existing Viraldy backend from deep DDD/Clean Architecture layers toward a lean modular monolith. This document is based on current source inspection, OpenAPI introspection, migration files, tests, CI workflows, and import searches.

## Current Shape

Repository-level structure is still the greenfield foundation layout:

```text
apps/backend/
  src/viraldy/
    api/
    modules/
    platform/
    shared/
    worker/
  alembic/
  tests/
apps/web/
docs/
infrastructure/
```

Backend modules currently implemented:

- `identity`
- `workspaces`
- `products`
- `assets`
- `jobs`
- `recommendations`

Future placeholder modules currently present:

- `references`
- `campaigns`
- `creative_genome`
- `preflight`
- `performance`
- `creators`
- `samples`
- `rights`
- `integrations`
- `notifications`

Each implemented module currently follows a deep shape:

```text
module/
  domain/
  application/
  infrastructure/
  presentation/
```

For the current foundation this creates too much ceremony: command objects, DTOs, repository protocols, mappers, entities, empty files, and handler classes exist even for simple CRUD.

## API Endpoints

OpenAPI currently exposes these contract paths:

- `GET /health`
- `GET /ready`
- `GET /api/v1/version`
- `GET /api/v1/me`
- `GET /api/v1/workspaces`
- `POST /api/v1/workspaces`
- `GET /api/v1/workspaces/{workspace_id}`
- `POST /api/v1/workspaces/{workspace_id}/products`
- `GET /api/v1/workspaces/{workspace_id}/products`
- `GET /api/v1/workspaces/{workspace_id}/products/{product_id}`
- `PATCH /api/v1/workspaces/{workspace_id}/products/{product_id}`
- `DELETE /api/v1/workspaces/{workspace_id}/products/{product_id}`
- `POST /api/v1/workspaces/{workspace_id}/assets/upload-sessions`
- `POST /api/v1/workspaces/{workspace_id}/assets/{asset_id}/complete-upload`
- `POST /api/v1/workspaces/{workspace_id}/assets/{asset_id}/process`
- `GET /api/v1/workspaces/{workspace_id}/assets`
- `GET /api/v1/workspaces/{workspace_id}/assets/{asset_id}`
- `GET /api/v1/workspaces/{workspace_id}/jobs`
- `GET /api/v1/workspaces/{workspace_id}/jobs/{job_id}`
- `GET /api/v1/workspaces/{workspace_id}/recommendations`
- `GET /api/v1/workspaces/{workspace_id}/recommendations/{recommendation_id}`
- `POST /api/v1/workspaces/{workspace_id}/recommendations/{recommendation_id}/actions`

These paths must not change during the refactor unless explicitly approved.

## Database And Migration History

Current Alembic history:

- `0001_initial_foundation`

Tables created:

- `users`
- `workspaces`
- `workspace_members`
- `products`
- `assets`
- `asset_versions`
- `processing_jobs`
- `recommendations`
- `recommendation_actions`

Migration history should be kept intact. The refactor should move Python code only; it should not reset Alembic or rewrite the schema.

## Celery And Worker

Current worker source:

- `worker/celery_app.py`
- `worker/main.py`
- `worker/tasks/process_asset.py`

Current task:

- `process_asset_placeholder(job_id)`

The durable job architecture is worth keeping:

- API creates `processing_jobs` record.
- API commits durable state before dispatch.
- Dispatcher enqueues Celery task with stable `job_id`.
- Worker loads job and asset/version metadata from PostgreSQL.
- Worker writes progress, output, and safe failure status back to PostgreSQL.

Current weakness:

- Worker task still contains too much processing orchestration and stage mutation.
- Job state transition logic is split across application handler, repository, worker repository, and task.

## External Adapters

Current external/provider boundaries:

- Auth: `platform/auth/token_verifier.py`, `local_test.py`, `oidc.py`
- Storage: `platform/storage/ports.py`, `s3.py`
- Queue: `modules/jobs/application/ports.py`, `modules/jobs/infrastructure/adapters.py`
- Observability: `platform/observability/logging.py`, `sentry.py`
- Model gateway: `platform/model_gateway/ports.py`, `disabled.py`

These are useful abstractions because the provider can change independently of business modules. They should move toward `integrations/` naming, not be removed.

## Auth And Workspace Permission Flow

Current auth flow:

- FastAPI dependency verifies Bearer token using `TokenVerifier`.
- Local mode accepts `Bearer local-test`.
- Missing local user is created on first authenticated request.
- Workspace permission checks query `workspace_members`.
- Role policy lives in `platform/auth/policy.py`.

Current weakness:

- `api/dependencies/auth.py` imports `UserModel` and `WorkspaceMemberModel` directly from module infrastructure. That violates the target cross-module boundary and should become a lean identity/workspace public contract or a consolidated auth integration query.

## Cross-Module Imports

Current import search found these important cross-module links:

- `assets.presentation.router` imports `jobs.api` and `products.api`.
- `worker.tasks.process_asset` imports `assets.api`.
- `api.dependencies.auth` imports `identity.infrastructure.models` and `workspaces.infrastructure.models`.

The public `api.py` files are a partial public-contract pattern, but target naming should become `public.py`. Deep imports into another module's infrastructure should be eliminated.

## Router Logic

Routers are generally thin, but they still do too much wiring:

- Routers instantiate repositories and services directly through local `handlers()` factories.
- Routers commit transactions for create/update/delete flows.
- `assets.router` builds job handlers and dispatches jobs after commit.

Target:

- Routers parse input, run auth/permission dependency, call service, and envelope the result.
- Transaction orchestration should move into service/use case level.

## Abstractions With One Implementation

Likely candidates to flatten or remove:

- `domain/entities.py` for simple modules where fields duplicate SQLAlchemy models.
- `domain/repositories.py` protocols for CRUD modules with one SQLAlchemy implementation.
- `application/commands.py` for simple CRUD input passthrough.
- `application/dto.py` where DTO duplicates response schema.
- `application/handlers.py` classes for simple CRUD.
- `infrastructure/mappers.py` for simple model-to-domain copies.
- Empty `events.py`, `policies.py`, `errors.py`, `ports.py`, `queries.py`, `adapters.py`, `dependencies.py`.

Useful abstractions to keep:

- `TokenVerifier` for auth providers.
- `StoragePort` / S3 adapter for object storage.
- `JobDispatcher` for queue boundary.
- Model gateway placeholder as provider boundary.
- Job policies/state transitions.
- Asset upload validation and storage-key generation.

## DTO And Mapper Duplication

Examples:

- `products.domain.entities.Product` duplicates `products.infrastructure.models.ProductModel`.
- `products.application.dto.ProductDto` duplicates `products.presentation.schemas.ProductResponse`.
- `products.infrastructure.mappers.to_domain()` only copies ORM fields into a near-identical dataclass.
- Similar duplication exists for workspaces, identity, assets, jobs, and recommendations.

Target:

- CRUD modules can return Pydantic response schemas from service/repository data without going through domain entity and application DTO layers.
- Complex future domains can still use explicit entities and mappers.

## Empty Or Low-Value Files

Current code has many empty or pass-through files, especially:

- `application/queries.py`
- `application/ports.py` in modules without real external boundaries
- `domain/events.py`
- `domain/errors.py`
- `domain/policies.py` for modules without policies
- `infrastructure/adapters.py`
- `presentation/dependencies.py`

Target:

- Remove empty files/folders where they do not carry a real responsibility.
- Do not keep future module placeholders under `src/viraldy/modules` unless they provide actual runtime or near-term documentation value.

## Classification

### KEEP

- Feature-based `modules/` grouping.
- Separate API and worker processes.
- PostgreSQL source of truth.
- Alembic migration history.
- Workspace-based multi-tenancy.
- Durable `processing_jobs`.
- Celery worker and Redis queue.
- Private S3-compatible storage flow.
- Provider boundaries for auth/storage/queue/model gateway/observability.
- OpenAPI response envelope contract.
- Architecture tests for import boundaries.

### FLATTEN

- `products`: Level 1 CRUD golden module.
- `workspaces`: Level 1 CRUD/membership module.
- `identity`: mostly auth/user projection; flatten heavily.
- `recommendations`: Level 1 for actions and Level 2 later for recommendation workflows.
- `assets`: Level 2 workflow module, flatten but keep validators/policies/events where meaningful.
- `jobs`: Level 2 workflow module, centralize job state transitions in service/policies.

### MERGE

- Command + handler + DTO layers for CRUD modules into `service.py`.
- Domain entity + mapper + response DTO for simple modules.
- Module `presentation/router.py` into `router.py`.
- Module `infrastructure/models.py` into `models.py`.
- Module `infrastructure/repository.py` into `repository.py`.

### RENAME

- `platform/config/settings.py` -> `core/config.py`.
- `platform/database/*` -> `db/*`.
- `platform/auth/*` -> `integrations/auth/*` or auth-specific API dependencies.
- `platform/storage/*` -> `integrations/storage/*`.
- `worker/` -> `workers/`.
- Module `api.py` public contracts -> `public.py`.

### REMOVE

- Empty future module source folders when no code uses them.
- Empty `commands.py`, `queries.py`, `events.py`, `errors.py`, `adapters.py`, `dependencies.py` files.
- Single-use repository protocols inside simple CRUD modules.
- Single-use mappers where ORM fields map directly to response schema.

### DEFER

- Deep DDD folders for future Level 3 domains: `creative_genome`, `preflight`, `performance`, creator campaigns, sample ROI, rights/Spark.
- Event outbox implementation.
- Real media/AI processing.
- Any frontend changes.
- Any microservice extraction.

## Refactor Risks

- OpenAPI schema can shift if response schemas are renamed or moved carelessly.
- Transaction boundary changes can alter commit/rollback behavior.
- Auth dependency currently deep-imports module infrastructure; changing it needs focused tests.
- Worker job flow is under-tested beyond the migration/architecture foundation.
- Docker is intentionally not part of this dev-task verification per user instruction.

## Recommended Refactor Plan

1. Baseline non-Docker verification and OpenAPI snapshot.
2. Refactor `products` as the golden Level 1 CRUD module.
3. Update imports/tests and verify OpenAPI diff.
4. Refactor `assets` as the golden Level 2 workflow module.
5. Refactor `jobs`, centralizing state transitions and worker service calls.
6. Flatten `workspaces`, `identity`, and `recommendations`.
7. Move provider boundaries from `platform/` to `integrations/`, database to `db/`, config/logging to `core/`.
8. Remove empty future module source placeholders and empty files.
9. Add junior module guides and update PR checklist.
10. Run non-Docker verification. Record Docker build as not run per current user instruction.
