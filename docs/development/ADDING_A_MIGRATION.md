# Adding A Migration

Use Alembic for schema changes. Do not edit or reset existing migration history.

Current head:

```text
0001_initial_foundation
```

Workflow:

1. Change SQLAlchemy models.
2. Create a new Alembic revision.
3. Review the migration by hand.
4. Run migration tests in an environment with PostgreSQL available.
5. Keep runtime code compatible with deployed schema during rollout when possible.

Dev commands:

```bash
cd apps/backend
uv run alembic heads
uv run alembic revision --autogenerate -m "describe change"
uv run alembic upgrade head
```

This refactor did not change database schema or migration history.
