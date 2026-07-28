# Module Guide

Modules live under `apps/backend/src/viraldy/modules/<feature>/`.

## Minimum CRUD Module

Use `products` as the current golden CRUD example:

- `models.py`: SQLAlchemy tables.
- `schemas.py`: Pydantic request and response schemas.
- `repository.py`: workspace-scoped queries and persistence.
- `service.py`: business rules and commits.
- `router.py`: FastAPI routes and response envelope.
- `public.py`: small stable contracts for other modules.

Flow:

```text
router -> service -> repository -> PostgreSQL
```

## Workspace Scope

Every business resource query must accept `workspace_id`.

Good:

```python
await ProductRepository(session).get_product(workspace_id, product_id)
```

Bad:

```python
await ProductRepository(session).get_product(product_id)
```

## Transactions

Repositories call `flush()` when they create or update models. Services call `commit()` after a complete use case.

## Cross-Module Calls

Only import another module through `public.py`.

Good:

```python
from viraldy.modules.products.public import ProductQueries
```

Bad:

```python
from viraldy.modules.products.repository import ProductRepository
from viraldy.modules.products.models import ProductModel
```

## Background Work

Use `assets` and `jobs` as the workflow examples:

```text
asset router -> AssetService.request_processing()
AssetService -> jobs.public.request_process_asset()
JobService -> commit processing_jobs -> JobDispatcher -> Celery
Celery task -> sync repositories -> PostgreSQL progress/result
```

Do not use FastAPI `BackgroundTasks`, daemon threads, or in-memory queues for business processing.
