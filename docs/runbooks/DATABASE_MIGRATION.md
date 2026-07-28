# Database Migration

Create migrations with `make migration name="..."`. Apply with `make migrate`. Production deployments run Alembic before starting API/worker containers. Do not use `create_all`.
