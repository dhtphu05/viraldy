# Security

## Reporting

Report vulnerabilities privately to the Viraldy maintainers. Do not open public issues for security findings.

## Secrets

Secrets must be supplied through environment variables or a deployment secret manager. Do not commit `.env` files, API keys, tokens, passwords, private URLs, or signed object storage URLs.

## Authentication

Production deployments must use provider-neutral OIDC verification. `AUTH_MODE=local_test` and `AUTH_DISABLED=true` are blocked outside local/test environments.

## Tenant Isolation

Workspace membership and role checks are required for every business resource. UUID knowledge is never authorization.

## Media Retention

Binary media lives in private S3-compatible object storage. Lifecycle, retention, and deletion policies are documented in `docs/runbooks/OBJECT_STORAGE.md`.

## Data Deletion

Products and assets use soft deletion in the foundation. Full account and workspace deletion workflows are deferred until retention requirements are finalized.

## Dependencies

Dependencies are managed through `pyproject.toml` and `uv.lock`. Security checks use `pip-audit` and Bandit in CI.

## Supported Versions

The current supported foundation version is `0.1.x`.
