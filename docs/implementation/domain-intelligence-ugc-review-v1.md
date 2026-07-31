# Domain Intelligence + UGC Review V1 implementation note

## Repository audit

Viraldy is a FastAPI/PostgreSQL modular monolith with SQLAlchemy repositories,
Alembic migrations, Celery `processing_jobs`, S3-compatible immutable asset
versions, and a React/TanStack Start frontend. UGC Review already has dedicated
routes and navigation, but the current screens use local mock scores and
flow-blocking language. This implementation replaces that feature's core path
with a durable recommendation-first review while preserving all existing route
URLs and unrelated product flows.

The implementation reuses the existing media evidence pipeline for probing,
ASR, OCR, frame sampling, visual observations, timestamps, and provenance. It
adds a global database-backed domain registry and workspace-scoped UGC review
results, action events, revisions, and comparisons.

## Implementation plan and verification

1. Place and validate the research artifacts, then add migration `0017` and an
   idempotent importer. Verify schema, source parity, exact record counts,
   content hash, active rule set, clean migration upgrade, and second-import
   behavior.
2. Add bounded domain selection and deterministic/semantic evaluation adapters.
   Verify typed unknown behavior, timing/brief distinctions, recommendation
   grouping, preserved strengths, all supplied Golden Cases, and deterministic
   fallback behavior.
3. Add workspace-scoped UGC Review APIs over `processing_jobs` and immutable
   asset versions. Verify create/status/result, persistent recommendation
   actions, inherited revision context, and finding-identity comparisons.
4. Rewire `/ugc-review` and `/ugc-review/$assetId` to the durable APIs. Verify
   upload/context submission, polling, decision-first groups, evidence seeking,
   creator-message actions, revision upload, and actual comparison rendering.
5. Export OpenAPI and run backend lint, type checking, the full backend suite,
   frontend tests, TypeScript, lint, and the frontend production build.

## Intentional repository adaptations

- Goal paths under `backend/app` map to `apps/backend/src/viraldy/modules`.
- `processing_jobs` is the existing durable job table; no parallel
  `analysis_jobs` framework is introduced.
- Business endpoints remain workspace-scoped to preserve current authorization
  and tenant isolation.
- Production persistence remains PostgreSQL/SQLAlchemy. The repository has no
  Supabase client or runtime in-memory persistence fallback, so tests use fakes
  without claiming local durability.
- Browser uploads continue through the existing presigned S3 flow. The review
  contract accepts immutable asset/version references, with multipart direct
  upload compatibility kept as an API adapter rather than duplicating media
  processing.
- The live UGC route and workspace APIs replace the legacy seeded UGC analyzer.
  Runtime hydration now discards that legacy mock state so fake scores and
  decisions cannot reappear through persisted browser storage.
- Raw research language such as `block`, `lock`, or `reject` is retained only in
  auditable registry payloads; it is never promoted to the seller-facing review
  state.

## Source-artifact status

The available pack is schema-valid and contains 58 policies, 23 creative
patterns, 20 mistake definitions, 15 uncertainties, 66 sources, and three
Golden Cases. `semantic_regression_tests_v1.jsonl` is now present in the backend
fixture directory with 35 records and SHA-256
`13bd9e28850599c63f9d849b89ddb9167a49eb6c99235ebfed61de12950ee0c1`.
The loader reports missing or malformed fixture artifacts explicitly.

## Database and importer

Migration `0017_domain_ugc_review` adds seven global registry tables for policy
packs, sources, rules, rule/source links, patterns, mistakes, and uncertainties.
It also adds five workspace-owned tables for review results, findings,
recommendation action events, revision relations, and comparisons. Review IDs
are existing `processing_jobs.id` values, and every review row retains its
immutable asset/version provenance.

From `apps/backend`:

```bash
uv run alembic upgrade head

uv run python -m viraldy.scripts.import_domain_policy_pack \
  --pack resources/domain_intelligence/v1/DomainExpertPolicyPackV1.json \
  --schema resources/domain_intelligence/v1/DomainExpertPolicyPackV1.schema.json \
  --sources resources/domain_intelligence/v1/source_registry_v1.csv \
  --validate-only

uv run python -m viraldy.scripts.import_domain_policy_pack \
  --pack resources/domain_intelligence/v1/DomainExpertPolicyPackV1.json \
  --schema resources/domain_intelligence/v1/DomainExpertPolicyPackV1.schema.json \
  --sources resources/domain_intelligence/v1/source_registry_v1.csv \
  --activate-mvp
```

The import verifies the supplied JSON Schema, exact record counts, embedded/CSV
source parity, source references, duplicate identifiers, content hash, and the
exact 16-code MVP rule set. Repeating the same import is a no-op.

## Runtime flow and API contracts

The API remains workspace-scoped:

```text
POST /api/v1/workspaces/{workspace_id}/ugc-reviews
GET  /api/v1/workspaces/{workspace_id}/ugc-reviews/{review_id}/status
GET  /api/v1/workspaces/{workspace_id}/ugc-reviews/{review_id}
POST /api/v1/workspaces/{workspace_id}/ugc-reviews/{review_id}/recommendations/{recommendation_id}/actions
POST /api/v1/workspaces/{workspace_id}/ugc-reviews/{review_id}/revisions
GET  /api/v1/workspaces/{workspace_id}/ugc-reviews/{review_id}/comparisons/latest
GET  /api/v1/domain-intelligence/status
```

The browser uses the existing presigned asset upload and sends `asset_id` plus
`asset_version_id` as flat multipart fields. For integration clients, create and
revision endpoints also accept `video_file`; the compatibility adapter streams
the file to a bounded temporary spool, creates the same immutable S3-backed
asset/version, and then uses the identical review path. Optional review context
never prevents starting a review.

Create and revision requests accept `Idempotency-Key`. Repeating a direct-file
request returns the originally persisted asset/version without uploading the
file again. Reusing a key with different asset, context, or parent input returns
`409 UGC_REVIEW_IDEMPOTENCY_CONFLICT` rather than binding the old review ID to
new input.

The Celery worker reuses `SyncMediaEvidencePipeline`, normalizes its persisted
evidence, selects active database rules for the supplied context, evaluates
deterministic facts before bounded semantic candidates, persists the result and
findings, and completes the existing processing job. Provider or evidence gaps
produce typed confirmations and a useful partial result rather than a creative
failure. Draft 2 inherits Draft 1 context and comparisons use stable finding
identities and actual evidence; no synthetic score is calculated. Persisted
provenance includes the media pipeline version, primary model-run identity, and
provider/model versions when available. The normalized-evidence evaluator maps
all required MVP mistake codes, including demo clarity, proof, urgency, creator
delivery, revision scope, and dropshipping compatibility.

## Environment and persistence

Use the repository's existing environment variables. The feature specifically
depends on `DATABASE_URL`, `DATABASE_SYNC_URL`, `REDIS_URL`, the `S3_*` values,
and the existing `AI_MODE`/provider variables used by media analysis. Local UI
development also uses `AUTH_MODE=local_test`; production keeps OIDC enabled.
The maximum direct or presigned declaration is controlled by
`MAX_DECLARED_UPLOAD_MB` (250 MB by default).

PostgreSQL is the durable source of truth. The small in-memory UGC repository is
an explicit unit-test double only: it is not selected at runtime and must not be
described as durable. There is no Supabase runtime in this repository.

## Recommendation-first product behavior

The result always preserves useful footage first, then presents only three
groups: **Fix first**, **Improve**, and **Confirm**. Seller actions are persisted
as append-only events. Missing rights, seller facts, publish metadata, or weak
media remain unknown/confirmation states; they never become a global block,
lock, rejection, or failed asset. Views and research pattern labels are evidence
only, so the feature never promises virality, GMV, ROAS, sales, or score lift.

## Local run and verification

Start the processes from the repository root:

```bash
make infra-up
make migrate
make api
make worker
make web-dev
```

Quality gates:

```bash
cd apps/backend
uv run ruff check .
uv run mypy src
uv run pytest
uv run python scripts/export_openapi.py

cd ../web
pnpm test
pnpm exec tsc --noEmit
pnpm lint
pnpm build
```

Reproducible manual flow:

1. Apply migration `0017_domain_ugc_review` and run the activating importer.
2. Start PostgreSQL, Redis, S3/MinIO, API, worker, and frontend.
3. Sign in, select a workspace, and open **UGC Review**.
4. Upload an MP4/MOV draft, optionally expand context, and submit.
5. Watch async progress, then inspect Keep/Fix first/Improve/Confirm and seek a
   timestamped evidence item in the video.
6. Apply or send a recommendation and confirm the action request succeeds.
7. Copy the creator message, mark it sent, upload Draft 2, and wait for its child
   review.
8. Inspect the persisted resolved/still-open/new comparison and strengths kept.

## Current limitation

The supplied media-analysis provider already creates semantic visual
observations. UGC Review additionally exposes a strict bounded semantic
evaluator port and deterministic fallback; deployments can attach a provider
without allowing it to alter rule sources, invent timestamps, or turn unknown
into pass. The exact 35-case semantic regression fixture is exercised by the
domain golden pytest contract.
