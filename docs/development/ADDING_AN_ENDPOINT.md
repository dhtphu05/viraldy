# Adding An Endpoint

1. Add request/response schemas in `modules/<feature>/schemas.py`.
2. Add repository methods in `repository.py`. Scope business resources by `workspace_id`.
3. Add a service method in `service.py`. Put business rules and commits there.
4. Add the route in `router.py`. Keep it thin.
5. Include the router in `api/main.py` only for a new module.
6. Add or update tests.
7. Run:

```bash
cd apps/backend
uv run ruff check .
uv run mypy src
uv run pytest tests/unit tests/contract tests/architecture
uv run python scripts/export_openapi.py
```

Do not change API paths, request payloads, response payloads, status codes, or error codes unless the breaking change is documented and approved.
