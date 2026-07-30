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

Owner/admin hard deletion is workspace-scoped and audited. Resource rows and a
durable object-cleanup batch are committed in one database transaction before
object storage deletion starts. Failed object cleanup remains pending and is
retried by the maintenance worker; it does not restore already-deleted business
data or leave live rows pointing at objects deleted before a rollback.

The cascade policy removes dependent PatternKit, ViralKit, Campaign Pack,
analysis, model-run, job, feedback, event, recommendation, and generation data
when their evidence lineage is deleted. Minimal deletion audit rows have no
foreign key to the deleted workspace or user and intentionally survive
workspace deletion.

Retention deletes expired incomplete uploads, removes old unreferenced objects
under the workspace prefix, and redacts expired model input/output summaries.
See `docs/runbooks/OBJECT_STORAGE.md` for cutoff and retry behavior.

## Dependencies

Dependencies are managed through `pyproject.toml` and `uv.lock`. Security checks use `pip-audit` and Bandit in CI.

## Supported Versions

The current supported foundation version is `0.1.x`.
