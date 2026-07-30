# Viraldy Private Beta Tech Freeze Audit

Status: Backend implementation complete through S7 local gates; release freeze still blocked
Branch: `release/private-beta-tech-freeze`
Baseline commit: `6461380`
Target release: `v0.1.0-beta-rc1`

This audit is intentionally conservative. Items are marked complete only when the
current source code and verification commands prove them.

## 1. Branch And Commit SHA

- Branch: `release/private-beta-tech-freeze`
- Baseline SHA before this goal work: `6461380`
- S1 commit SHA: `1f603ba`
- S2 commit SHA: `b9ffa40`
- S3 commit SHA: `9382fcb`
- S4 commit SHA: `667e418`
- S5 implementation commit SHA: `f45b318`
- S6 implementation commit SHA: `2257ed4`
- S7 implementation commit SHA: `6de0066`
- PR URL: pending

## 2. Changed Files By Module

### S1 Auth And RBAC

- `apps/backend/src/viraldy/platform/auth/policy.py`
- `apps/backend/src/viraldy/platform/auth/oidc.py`
- `apps/backend/src/viraldy/platform/auth/current_user.py`
- `apps/backend/src/viraldy/platform/config/settings.py`
- `apps/backend/src/viraldy/api/dependencies/auth.py`
- `apps/backend/src/viraldy/modules/identity/models.py`
- `apps/backend/src/viraldy/modules/identity/public.py`
- `apps/backend/src/viraldy/modules/identity/router.py`
- `apps/backend/src/viraldy/modules/identity/schemas.py`
- `apps/backend/src/viraldy/modules/workspaces/models.py`
- `apps/backend/src/viraldy/modules/workspaces/repository.py`
- `apps/backend/src/viraldy/modules/workspaces/router.py`
- `apps/backend/src/viraldy/modules/workspaces/schemas.py`
- `apps/backend/src/viraldy/modules/workspaces/service.py`
- Existing workspace-scoped routers were updated to use domain permissions.

### Tests

- `apps/backend/tests/unit/test_config.py`
- `apps/backend/tests/unit/test_oidc_auth.py`
- `apps/backend/tests/unit/test_policies.py`
- `apps/backend/tests/unit/test_workspace_service.py`
- `apps/backend/tests/integration/test_migrations.py` exercised clean Postgres migration.

### S2 Persistence Foundations

- `apps/backend/src/viraldy/modules/feedback/`
- `apps/backend/src/viraldy/modules/product_events/`
- `apps/backend/src/viraldy/modules/ai_gateway/models.py`
- `apps/backend/src/viraldy/modules/ai_gateway/repository.py`
- `apps/backend/src/viraldy/modules/recommendations/validators.py`
- `apps/backend/src/viraldy/modules/recommendations/service.py`
- `apps/backend/src/viraldy/modules/products/service.py`
- `apps/backend/src/viraldy/modules/workspaces/service.py`
- `apps/backend/src/viraldy/api/main.py`
- `apps/backend/src/viraldy/platform/database/models.py`

### S2 Tests

- `apps/backend/tests/unit/test_feedback_service.py`
- `apps/backend/tests/unit/test_product_events.py`
- `apps/backend/tests/unit/test_recommendation_service.py`
- `apps/backend/tests/unit/test_workspace_service.py`
- `apps/backend/tests/unit/test_ai_gateway.py`
- `apps/backend/tests/integration/test_migrations.py`

### S3 PatternKit

- `apps/backend/src/viraldy/modules/pattern_kits/`
- `apps/backend/src/viraldy/modules/creative_domain/schema_versions.py`
- `apps/backend/src/viraldy/modules/ai_gateway/prompts.py`
- `apps/backend/src/viraldy/modules/ai_gateway/public.py`
- `apps/backend/src/viraldy/modules/media_analysis/public.py`
- `apps/backend/src/viraldy/modules/feedback/public.py`
- `apps/backend/src/viraldy/modules/feedback/service.py`
- `apps/backend/src/viraldy/api/main.py`
- `apps/backend/src/viraldy/platform/database/models.py`
- `apps/backend/alembic/versions/0007_pattern_kits.py`

### S3 Tests

- `apps/backend/tests/unit/test_pattern_kits.py`
- `apps/backend/tests/unit/test_feedback_service.py`
- `apps/backend/tests/integration/test_migrations.py`

### S4 ViralKit

- `apps/backend/src/viraldy/modules/viral_kits/`
- `apps/backend/src/viraldy/modules/creative_domain/schema_versions.py`
- `apps/backend/src/viraldy/modules/ai_gateway/prompts.py`
- `apps/backend/src/viraldy/modules/ai_gateway/public.py`
- `apps/backend/src/viraldy/modules/products/models.py`
- `apps/backend/src/viraldy/modules/products/public.py`
- `apps/backend/src/viraldy/modules/products/schemas.py`
- `apps/backend/src/viraldy/modules/products/service.py`
- `apps/backend/src/viraldy/modules/pattern_kits/public.py`
- `apps/backend/src/viraldy/modules/pattern_kits/repository.py`
- `apps/backend/src/viraldy/modules/campaign_packs/contracts.py`
- `apps/backend/src/viraldy/modules/campaign_packs/models.py`
- `apps/backend/src/viraldy/modules/campaign_packs/public.py`
- `apps/backend/src/viraldy/modules/campaign_packs/repository.py`
- `apps/backend/src/viraldy/modules/campaign_packs/schemas.py`
- `apps/backend/src/viraldy/api/main.py`
- `apps/backend/src/viraldy/platform/database/models.py`
- `apps/backend/alembic/versions/0008_viral_kits.py`
- `.gitignore`

### S4 Tests

- `apps/backend/tests/unit/test_viral_kits.py`
- `apps/backend/tests/integration/test_migrations.py`

### S5 AI Operations, Jobs, And Generation

- `apps/backend/src/viraldy/modules/ai_gateway/operations.py`
- `apps/backend/src/viraldy/modules/ai_gateway/prompts.py`
- `apps/backend/src/viraldy/modules/ai_gateway/public.py`
- `apps/backend/src/viraldy/modules/generation/`
- `apps/backend/src/viraldy/modules/jobs/`
- `apps/backend/src/viraldy/modules/references/service.py`
- `apps/backend/src/viraldy/modules/tiktok_scorer/service.py`
- `apps/backend/src/viraldy/modules/preflight/service.py`
- `apps/backend/src/viraldy/modules/viral_kits/public.py`
- `apps/backend/src/viraldy/platform/config/settings.py`
- `apps/backend/src/viraldy/platform/database/models.py`
- `apps/backend/src/viraldy/worker/celery_app.py`
- `apps/backend/src/viraldy/worker/tasks/process_asset.py`
- `apps/backend/src/viraldy/api/main.py`
- `apps/backend/alembic/versions/0009_generation_foundation.py`
- `apps/backend/alembic/versions/0010_job_contract_normalization.py`
- `docker-compose.yml`
- `infrastructure/docker/entrypoints/worker.sh`
- `Makefile`
- `apps/backend/README.md`

### S5 Tests

- `apps/backend/tests/unit/test_ai_gateway.py`
- `apps/backend/tests/unit/test_generation.py`
- `apps/backend/tests/unit/test_jobs.py`
- `apps/backend/tests/unit/test_job_service.py`
- `apps/backend/tests/contract/test_openapi.py`
- `apps/backend/tests/integration/test_migrations.py`

### S6 Deletion, Retention, And Storage Cleanup

- `apps/backend/src/viraldy/modules/deletion/`
- Existing workspace, product, asset, reference, Creative DNA, PatternKit,
  ViralKit, and Campaign Pack routers now use the shared hard-deletion service.
- `apps/backend/src/viraldy/platform/storage/ports.py`
- `apps/backend/src/viraldy/platform/storage/s3.py`
- `apps/backend/src/viraldy/platform/config/settings.py`
- `apps/backend/src/viraldy/platform/database/models.py`
- `apps/backend/src/viraldy/worker/tasks/process_asset.py`
- `apps/backend/src/viraldy/worker/celery_app.py`
- `apps/backend/src/viraldy/api/main.py`
- `apps/backend/alembic/versions/0011_deletion_audit.py`
- `SECURITY.md`
- `docs/runbooks/OBJECT_STORAGE.md`

### S6 Health

- `apps/backend/src/viraldy/api/routers/health.py`
- `apps/backend/src/viraldy/platform/storage/ports.py`
- `apps/backend/src/viraldy/platform/storage/s3.py`
- `apps/backend/src/viraldy/api/main.py`

### S6 Evaluation

- `apps/backend/src/viraldy/evaluation/`
- `apps/backend/scripts/run_evaluation.py`
- `evaluation/README.md`
- `apps/backend/README.md`

### S6 Tests

- `apps/backend/tests/unit/test_deletion.py`
- `apps/backend/tests/unit/test_health.py`
- `apps/backend/tests/unit/test_evaluation.py`
- `apps/backend/tests/contract/test_openapi.py`
- `apps/backend/tests/integration/test_migrations.py`

### S7 E2E And Release Hardening

- `Makefile`
- `apps/backend/scripts/smoke_mvp_flow.py`
- `apps/backend/scripts/mock_openai_provider.py`
- `apps/backend/scripts/seed_local.py`
- `apps/backend/src/viraldy/platform/auth/local_test.py`
- `apps/backend/src/viraldy/modules/campaign_packs/repository.py`
- `apps/backend/src/viraldy/modules/media_analysis/service.py`

### S7 Tests

- `apps/backend/tests/unit/test_local_test_auth.py`
- `apps/backend/tests/unit/test_campaign_pack_repository.py`

## 3. Migration List

- `0001_initial_foundation`
- `0002_creative_intelligence_mvp`
- `0003_keyless_product_hardening`
- `0004_creative_domain_contracts`
- `0005_auth_workspace_rbac`
- `0006_feedback_events_model_runs`
- `0007_pattern_kits`
- `0008_viral_kits`
- `0009_generation_foundation`
- `0010_job_contract_normalization`
- `0011_deletion_audit`

`0005_auth_workspace_rbac` adds `users.last_login_at`, converts legacy
`workspace_members.role='editor'` to `member`, and adds check constraints for
valid user status and workspace roles.

`0006_feedback_events_model_runs` adds `feedback_items` and `product_events`,
adds private-beta trace fields to `ai_model_runs`, normalizes legacy
recommendation actions into the supported action set while preserving the prior
action in `metadata_json.legacy_action_type`, and adds constraints/indexes for
new append-only data.

`0007_pattern_kits` adds `pattern_kits`, `pattern_kit_versions`,
`pattern_kit_sources`, `pattern_kit_evidence_links`, and
`pattern_kit_actions` with workspace-scoped indexes, immutable version rows,
source/evidence uniqueness constraints, lifecycle action constraints, and
`source_order >= 1` validation.

`0008_viral_kits` adds `products.product_context_version`, allows Campaign
Packs to be created without an Adaptation Run, and adds `viral_kits`,
`viral_kit_versions`, `viral_kit_pattern_links`, `viral_kit_concept_actions`,
and `viral_kit_campaign_pack_links` with workspace-scoped indexes, append-only
version uniqueness, pattern-link uniqueness, concept action constraints, and
Campaign Pack lineage links.

`0009_generation_foundation` adds workspace-scoped `generation_runs` and
`generation_artifacts`. Runs lock the exact ViralKit/version/concept,
generation brief, source asset IDs, prompt/schema version, input hash, model
run, processing job, safe failure, and idempotency metadata. Artifacts retain
provider/model provenance and storage keys or structured fixture payloads,
never signed download URLs.

`0010_job_contract_normalization` is a separate data migration. It converts
`completed` to `succeeded`, converts transient legacy `dispatching` rows to
`queued`, and safely maps legacy job type names only when doing so cannot
collide with the existing idempotency unique constraint. Application-level
aliases remain so queued legacy deliveries and collision-preserved rows are
still readable. The migration replaces job/event status constraints and has a
reverse mapping for rollback.

`0011_deletion_audit` adds minimal deletion audit records and durable
`storage_deletion_batches`. Audit and outbox rows intentionally have no foreign
key to workspace/user data so they survive workspace deletion. Status and
source constraints, workspace/status indexes, safe errors, object counts, and
row-count summaries support idempotent post-commit object cleanup and retry.

## 4. Auth And Identity

Completed in S1:

- Bearer token dependency remains the auth entry point.
- OIDC verifier now enforces configured allowed algorithms.
- OIDC decode requires issuer, audience, `exp`, `sub`, and `email`.
- `nbf` is validated by PyJWT when present.
- JWKS client uses an explicit cache lifespan for key-set refresh behavior.
- Token/provider failures are normalized to project `UnauthorizedError`.
- First authenticated request provisions a user by `external_auth_id`.
- User provisioning catches unique constraint races and reloads the existing user.
- Provider-owned email/display name are updated safely on auth.
- `last_login_at` is persisted.
- Non-active users are denied.
- `GET /api/v1/me` returns persisted user status.
- `GET /api/v1/auth/config` returns public auth mode/config without secrets.

Still pending:

- HTTP-level auth tests for missing/malformed bearer headers.
- HTTP-level suspended-user denial test.
- Explicit concurrent provisioning integration test against Postgres.

## 5. RBAC Matrix

Implemented centrally in `WorkspaceMembershipPolicy`:

| Permission | Owner | Admin | Member | Viewer |
|---|---:|---:|---:|---:|
| workspace.read | yes | yes | yes | yes |
| workspace.manage | yes | yes | no | no |
| members.read | yes | yes | yes | no |
| members.manage | yes | yes | no | no |
| product.read | yes | yes | yes | yes |
| product.write | yes | yes | yes | no |
| reference.read | yes | yes | yes | yes |
| reference.write | yes | yes | yes | no |
| analysis.run | yes | yes | yes | no |
| pattern_kit.write | yes | yes | yes | no |
| viral_kit.write | yes | yes | yes | no |
| campaign_pack.write | yes | yes | yes | no |
| preflight.run | yes | yes | yes | no |
| recommendation.act | yes | yes | yes | no |
| feedback.write | yes | yes | yes | no |
| data.export | yes | yes | no | no |
| data.delete | yes | yes | no | no |

Workspace API implemented:

- `GET /api/v1/workspaces`
- `POST /api/v1/workspaces`
- `GET /api/v1/workspaces/{workspace_id}`
- `PATCH /api/v1/workspaces/{workspace_id}`
- `DELETE /api/v1/workspaces/{workspace_id}`
- `GET /api/v1/workspaces/{workspace_id}/members`
- `POST /api/v1/workspaces/{workspace_id}/members`
- `PATCH /api/v1/workspaces/{workspace_id}/members/{member_id}`
- `DELETE /api/v1/workspaces/{workspace_id}/members/{member_id}`

Rules implemented:

- Workspace creator is inserted as owner.
- Member addition uses email.
- Viewer cannot mutate resources through the centralized permission matrix.
- Deleted workspaces are excluded from permission checks.
- The only owner cannot demote or remove themself.

Still pending:

- Full tenant-isolation HTTP tests for every major resource.
- Optional owner-grant restrictions beyond the explicit private beta rule.

## 6. PatternKit Contract Summary

Implemented in S3:

- `PatternKitV1` is a strict Pydantic contract with schema version
  `pattern_kit_v1`, immutable identity/version fields, source provenance,
  evidence refs, temporal sequence, component contracts, applicability,
  adaptation instructions, performance summary, confidence, uncertainties, and
  provenance.
- Evidence refs require exact Creative DNA version, asset version, evidence ID,
  feature path, source type, optional timing, observation summary, and
  confidence. Timing ranges reject `end_ms < start_ms`.
- Sequence validation rejects duplicate beat IDs and non-contiguous ordering;
  required beats must carry evidence.
- Fixture extraction is deterministic and input-derived. It reads observed or
  explicit inferred Creative DNA fields, resolves evidence IDs from media
  evidence, preserves unknowns, and does not emit winning/performance claims
  without performance evidence.
- Anti-copy checks reject long exact source hook/CTA strings in reusable output.
- Persistence stores kits, immutable versions, source rows, evidence links,
  actions, model-run provenance, and first-party events.
- Lifecycle actions enforce candidate -> reviewed -> validated/deprecated and
  archive/restore transitions. Validation requires an explicit human reason.
- Public boundary `PatternKitQueries` exposes exact version snapshots for later
  ViralKit integration.
- PatternKit-local feedback endpoint writes field-level correction through the
  feedback public boundary and emits `pattern_kit_corrected`.

Still pending for PatternKit:

- Live provider qualification against real Dola/Seed-compatible responses.
  Local OpenAI-compatible mock contract execution passed in S7.
- Full HTTP tenant-isolation coverage for every PatternKit endpoint.
- Performance evidence promotion rules for directional/supported labels.

## 7. ViralKit Contract Summary

Implemented in S4:

- `ViralKitV1` is a strict Pydantic contract with schema version
  `viral_kit_v1`, immutable identity/version fields, locked Product Context
  snapshot, buyer context, requested platform/objective/market, PatternKit match
  records, adaptation plan, exactly three concepts, test matrix, optional
  generation briefs, preflight requirement class links, risks, confidence,
  campaign pack lineage, and provenance.
- Concept validation rejects duplicate concept IDs, requires selected concepts
  to exist, requires every concept pair to differ on at least two strategic
  axes, requires hook variation, and requires demo/proof/narrative variation.
- Buyer persona and creator persona are explicitly separated to avoid confusing
  the target customer with the creator archetype.
- Pattern matching is deterministic and product-aware. It scores category,
  platform, market, objective, required traits, preferred traits, visual demo
  suitability, and governance context; rejected PatternKits cannot be used
  unless an explicit override reason is supplied.
- Fixture composer is product-grounded and evidence-linked. It produces three
  concepts, preserves prohibited claims and required disclosures, avoids sales
  or virality promises, adds TikTok Shop product-tag requirements when required,
  and can emit storyboard-preview generation briefs behind the request flag.
- Live composer uses the OpenAI-compatible client and validates returned JSON
  against `ViralKitV1`; it does not silently fall back to fixture mode when live
  provider configuration is missing or invalid.
- Persistence stores kits, immutable versions, pattern applicability links,
  concept decision actions, Campaign Pack links, model-run provenance, and
  first-party events.
- Product Context now has `product_context_version`; ViralKit creation rejects
  stale expected versions to prevent composing from outdated seller context.
- ViralKit-to-Campaign-Pack creation compiles exact must-show requirements and
  records source ViralKit, source ViralKit version, source concept, source
  PatternKit versions, and the created Campaign Pack version.
- ViralKit-local feedback endpoint writes field-level corrections through the
  feedback public boundary.

Still pending for ViralKit:

- HTTP tenant-isolation tests across the full endpoint set.
- Live provider qualification against real Dola/Seed-compatible responses.
- Frontend integration for ViralKit list/detail/create/select/pack creation.
- Generation provider execution for the optional generation brief payloads.

## 8. API Endpoint List

Implemented before this goal:

- Identity: `/api/v1/me`
- Workspaces: list/create/get
- Products
- Assets
- Jobs
- Recommendations
- Media analysis
- Reference boards
- References
- Creative DNA
- TikTok scorer
- Adaptations
- Campaign packs
- Preflight

Implemented in S1:

- `/api/v1/auth/config`
- workspace PATCH/DELETE
- workspace member list/add/update/delete

Implemented in S2:

- `POST /api/v1/workspaces/{workspace_id}/feedback`
- `GET /api/v1/workspaces/{workspace_id}/feedback`
- `GET /api/v1/workspaces/{workspace_id}/events`

Implemented in S3:

- `POST /api/v1/workspaces/{workspace_id}/pattern-kits`
- `GET /api/v1/workspaces/{workspace_id}/pattern-kits`
- `GET /api/v1/workspaces/{workspace_id}/pattern-kits/{pattern_kit_id}`
- `GET /api/v1/workspaces/{workspace_id}/pattern-kits/{pattern_kit_id}/versions`
- `GET /api/v1/workspaces/{workspace_id}/pattern-kits/{pattern_kit_id}/versions/{version}`
- `POST /api/v1/workspaces/{workspace_id}/pattern-kits/{pattern_kit_id}/versions`
- `POST /api/v1/workspaces/{workspace_id}/pattern-kits/{pattern_kit_id}/actions`
- `POST /api/v1/workspaces/{workspace_id}/pattern-kits/{pattern_kit_id}/feedback`
- `DELETE /api/v1/workspaces/{workspace_id}/pattern-kits/{pattern_kit_id}`

Implemented in S4:

- `POST /api/v1/workspaces/{workspace_id}/viral-kits`
- `GET /api/v1/workspaces/{workspace_id}/viral-kits`
- `GET /api/v1/workspaces/{workspace_id}/viral-kits/{viral_kit_id}`
- `GET /api/v1/workspaces/{workspace_id}/viral-kits/{viral_kit_id}/versions`
- `GET /api/v1/workspaces/{workspace_id}/viral-kits/{viral_kit_id}/versions/{version}`
- `POST /api/v1/workspaces/{workspace_id}/viral-kits/{viral_kit_id}/versions`
- `POST /api/v1/workspaces/{workspace_id}/viral-kits/{viral_kit_id}/concept-actions`
- `POST /api/v1/workspaces/{workspace_id}/viral-kits/{viral_kit_id}/concepts/{concept_id}/campaign-pack`
- `POST /api/v1/workspaces/{workspace_id}/viral-kits/{viral_kit_id}/feedback`
- `DELETE /api/v1/workspaces/{workspace_id}/viral-kits/{viral_kit_id}`

Implemented in S5:

- `POST /api/v1/workspaces/{workspace_id}/generation/storyboards`
- `POST /api/v1/workspaces/{workspace_id}/generation/concept-video-previews`
- `GET /api/v1/workspaces/{workspace_id}/generation/runs/{generation_run_id}`

Implemented in S6:

- `GET /health/live`
- `GET /health/ready`
- `GET /health/dependencies`
- `GET /health/worker`
- `DELETE /api/v1/workspaces/{workspace_id}/deletions`
- `DELETE /api/v1/workspaces/{workspace_id}/deletions/{resource_type}/{resource_id}`
- `POST /api/v1/workspaces/{workspace_id}/deletions/retention`
- Direct DELETE routes for workspace, product, asset, reference, Creative DNA
  version, PatternKit, ViralKit, and Campaign Pack use the same audited hard
  deletion path.

S2 behavior implemented:

- Field-level feedback is stored separately from AI output.
- Feedback subjects are restricted to Creative DNA, PatternKit, ViralKit,
  TikTok score, Preflight, and Recommendation.
- Feedback types are restricted to `correct`, `incorrect`, `partial`,
  `missing`, `false_positive`, `false_negative`, and `not_useful`.
- Product events are persisted first-party in PostgreSQL and exportable by
  owner/admin through `data.export`.
- Workspace creation, product creation, and accepted/rejected/applied
  recommendation actions emit product events.
- Recommendation seller actions now accept only `viewed`, `accepted`,
  `rejected`, `applied`, and `ignored`.
- `ai_model_runs` now stores `operation`, `schema_version`, `input_hash`,
  `attempt_count`, `usage_json`, `estimated_cost`, and `safe_error_message`,
  while retaining legacy fields for backward compatibility.

S3 behavior implemented:

- PatternKit creation loads exact completed Creative DNA versions through the
  Creative DNA public boundary and resolves evidence through the media analysis
  public boundary.
- PatternKit source and evidence references are workspace-scoped and persisted
  separately from the JSON artifact.
- PatternKit versions are append-only; creating a new version never mutates the
  prior version row.
- Fixture-mode PatternKit extraction creates and completes an `ai_model_runs`
  record with `operation=pattern_kit_extract`, schema/prompt version, input
  hash, and output summary.
- Failed PatternKit extraction/validation marks the model run failed with a safe
  error code/message.
- PatternKit actions and feedback emit product events where required by the
  private beta event list.

S4 behavior implemented:

- ViralKit creation loads the exact Product Context snapshot and exact
  PatternKit version snapshots through module public boundaries.
- Stale `expected_product_context_version` requests fail with
  `VIRAL_KIT_PRODUCT_VERSION_CONFLICT`.
- PatternKit applicability is stored both inside the immutable ViralKit JSON and
  separately in `viral_kit_pattern_links` for querying and audit.
- ViralKit versions are append-only; creating a new version never mutates the
  prior version row.
- Concept selection/rejection is recorded as an append-only action and emits
  `concept_selected` or `concept_rejected` where applicable.
- Campaign Pack creation from a concept records both a Campaign Pack link row
  and a `campaign_pack_created` concept action.
- Fixture-mode ViralKit composition creates and completes an `ai_model_runs`
  record with `operation=viral_kit_compose`, schema/prompt version, input hash,
  and output summary.
- Failed ViralKit validation/provider errors mark the model run failed with a
  safe error code/message.

S5 behavior implemented:

- A central typed operation registry defines all seven Dola/Seed analysis
  operations and both Seedream/Seedance generation operations. Every definition
  has typed input/output models, prompt version, schema version, timeout, retry
  policy, model family, and fixture availability.
- Job types now use the private-beta canonical names, including PatternKit,
  ViralKit, Campaign Pack, preflight, generation, and retention jobs. Legacy
  names remain aliases for already-queued deliveries and idempotent lookups.
- Job terminal success is `succeeded`. API responses expose canonical
  `progress_percent`, `current_stage`, `safe_error_code`, and
  `safe_error_message` while retaining the old fields for client compatibility.
- The Celery production task is named `run_processing_job`; placeholder aliases
  were removed. Stable UUIDs remain the only task payload.
- Stale running jobs are locked with `FOR UPDATE SKIP LOCKED`, moved to
  `retrying` or `failed` based on attempt limits, and redispatched by a
  maintenance task every five minutes. Recovery uses the persisted
  `updated_at` heartbeat and waits for the larger of the configured stale
  threshold or that job type's hard timeout plus a 120-second safety margin.
- Each claimed attempt is fenced by its persisted `attempt_count`. Every
  progress and terminal write reacquires the job row and requires both
  `status=running` and the same attempt token, so a recovered old worker cannot
  overwrite a newer attempt. Stranded old `retrying` rows are eligible for
  maintenance redispatch.
- Initial dispatch and stale-job redispatch both use the registered queue,
  soft timeout, and hard timeout for the canonical job type.
- Docker Compose includes a Celery Beat service, and the worker consumes both
  `default` and `maintenance`, so stale recovery and maintenance jobs are
  operational rather than configuration-only.
- Storyboard and concept-video requests validate workspace access, generation
  feature flags, exact ViralKit version/concept/brief, and every source asset.
  Explicit source-media rights confirmation is required where the immutable
  brief requires it. Creation stores an immutable input snapshot and queues an
  idempotent job.
- Worker execution creates an `ai_model_runs` row, validates provider output,
  atomically replaces retry artifacts, records provider/model provenance, and
  completes both generation run and processing job. Worker lookup is
  workspace-scoped and verifies the processing-job-to-generation-run binding.
- Fixture and mock modes produce deterministic structured artifacts. Live mode
  requires explicit provider URL, API key, and image/video model; it never
  falls back to fixture output. Transient timeout, rate-limit, and 5xx responses
  use the configured bounded retry policy.
- Provider artifact contracts recursively reject persisted HTTP(S) URLs.
  Signed download URLs remain request-time concerns and are not stored.

S6 behavior implemented:

- Liveness reports only API process health. Readiness checks PostgreSQL, Redis,
  and object storage required for API traffic. The full dependency endpoint
  additionally checks Celery workers and AI provider configuration; worker/AI
  outages therefore do not incorrectly remove a healthy API instance.
- Health responses contain only component status and latency. Raw dependency
  exceptions, URLs, credentials, provider errors, and bucket details are not
  returned.
- Owner/admin hard deletion is workspace-scoped and follows a dynamic
  child-first dependency plan. Evidence/source deletion promotes dependent
  PatternKit, ViralKit, and Campaign Pack artifacts so no visible artifact keeps
  invalid provenance.
- Storage keys are collected from asset versions, media artifacts, nested
  sampled-frame payloads, evidence scalar and multi-frame payloads, and
  generation artifacts. Shared `fixtures/` keys are excluded.
- Business-row deletion and a durable object-cleanup outbox batch commit in one
  PostgreSQL transaction before S3 deletion. Failed or partial object cleanup
  remains pending with a safe error and is retried every five minutes on the
  maintenance queue. S3-compatible DELETE retry is idempotent.
- Minimal deletion audit records retain initiator UUID, workspace/resource UUID,
  status, row counts, object count, safe failure, and timestamps without foreign
  keys or copied PII, so workspace deletion does not erase the audit.
- Retention removes expired `pending_upload` assets, redacts old AI model input
  and output summaries, and scans the workspace prefix for old unreferenced
  objects. Referenced, recent, fixture, and already-pending keys are protected.
- The evaluation harness accepts typed captured fixture/mock/live datasets and
  produces deterministic JSON and Markdown reports. PatternKit and ViralKit
  metrics use structured judgments, IDs, labels, compile checks, and reviewer
  scores rather than exact prose matching.

## 9. Test Commands And Results

Commands run locally:

```bash
cd apps/backend && .venv/bin/ruff check src/viraldy/platform/auth src/viraldy/modules/identity src/viraldy/modules/workspaces tests/unit/test_policies.py tests/unit/test_workspace_service.py tests/unit/test_config.py tests/unit/test_oidc_auth.py
cd apps/backend && .venv/bin/pytest tests/unit/test_policies.py tests/unit/test_workspace_service.py tests/unit/test_config.py tests/unit/test_oidc_auth.py
cd apps/backend && .venv/bin/pytest tests/unit
cd apps/backend && .venv/bin/pytest tests/integration/test_migrations.py
cd apps/backend && .venv/bin/ruff check src tests
cd apps/backend && .venv/bin/pytest tests/unit tests/architecture tests/contract tests/integration/test_migrations.py
cd apps/backend && .venv/bin/ruff check src tests alembic/versions/0006_feedback_events_model_runs.py
cd apps/backend && .venv/bin/pytest tests/unit/test_feedback_service.py tests/unit/test_product_events.py tests/unit/test_recommendation_service.py tests/unit/test_workspace_service.py tests/unit/test_ai_gateway.py
cd apps/backend && .venv/bin/pytest tests/unit tests/architecture tests/contract tests/integration/test_migrations.py
cd apps/backend && .venv/bin/ruff check src tests alembic/versions
cd apps/backend && .venv/bin/pytest tests/unit tests/architecture tests/contract tests/integration/test_migrations.py
cd apps/backend && .venv/bin/ruff check .
cd apps/backend && .venv/bin/mypy src/viraldy/modules/viral_kits src/viraldy/modules/products src/viraldy/modules/campaign_packs/public.py src/viraldy/modules/campaign_packs/contracts.py src/viraldy/modules/campaign_packs/models.py src/viraldy/modules/campaign_packs/repository.py src/viraldy/modules/pattern_kits/public.py src/viraldy/modules/pattern_kits/repository.py
cd apps/backend && .venv/bin/pytest tests/unit/test_viral_kits.py -q
cd apps/backend && .venv/bin/pytest tests/integration/test_migrations.py -q
cd apps/backend && .venv/bin/pytest -q
cd apps/backend && .venv/bin/ruff check .
cd apps/backend && .venv/bin/mypy src/viraldy/modules/generation src/viraldy/modules/ai_gateway/operations.py src/viraldy/modules/jobs src/viraldy/modules/viral_kits/public.py
cd apps/backend && .venv/bin/pytest tests/unit/test_generation.py tests/unit/test_ai_gateway.py tests/unit/test_jobs.py tests/unit/test_job_service.py -q
cd apps/backend && .venv/bin/pytest tests/integration/test_migrations.py -q
cd apps/backend && .venv/bin/pytest -q
cd apps/backend && .venv/bin/pip-audit
cd apps/backend && uv run mypy src/viraldy/modules/ai_gateway/operations.py src/viraldy/modules/ai_gateway/prompts.py src/viraldy/modules/ai_gateway/public.py src/viraldy/modules/creative_domain/schema_versions.py src/viraldy/modules/generation src/viraldy/modules/jobs/dispatcher.py src/viraldy/modules/jobs/policies.py src/viraldy/modules/jobs/public.py src/viraldy/modules/jobs/registry.py src/viraldy/modules/jobs/repository.py src/viraldy/modules/jobs/schemas.py src/viraldy/modules/jobs/service.py src/viraldy/modules/preflight/service.py src/viraldy/modules/references/service.py src/viraldy/modules/tiktok_scorer/service.py src/viraldy/modules/viral_kits/public.py src/viraldy/platform/config/settings.py src/viraldy/platform/database/models.py tests/unit/test_generation.py tests/unit/test_job_service.py tests/unit/test_jobs.py tests/contract/test_openapi.py tests/integration/test_migrations.py
cd apps/backend && uv run pytest tests/unit/test_ai_gateway.py tests/unit/test_generation.py tests/unit/test_jobs.py tests/unit/test_job_service.py tests/contract/test_openapi.py --no-cov -q
cd apps/backend && uv run pytest tests/integration/test_migrations.py -q
cd apps/backend && uv run pytest -q
docker compose -f <(sed '/env_file: \.env/d' docker-compose.yml) --project-directory "$PWD" config --quiet
cd apps/backend && uv run pytest tests/unit/test_deletion.py tests/unit/test_health.py tests/unit/test_evaluation.py tests/contract/test_openapi.py --no-cov -q
cd apps/backend && uv run mypy src/viraldy/modules/deletion src/viraldy/evaluation src/viraldy/api/routers/health.py src/viraldy/platform/storage tests/unit/test_deletion.py tests/unit/test_evaluation.py tests/unit/test_health.py scripts/run_evaluation.py
cd apps/backend && uv run ruff check .
cd apps/backend && uv run pytest tests/integration/test_migrations.py -q
cd apps/backend && uv run pytest -q
cd apps/backend && uv run pip-audit
git diff --check
cd apps/backend && uv run python scripts/smoke_mvp_flow.py --base-url http://127.0.0.1:18000/api/v1 --expect-mode fixture --verify-db --timeout-seconds 120
cd apps/backend && uv run python scripts/smoke_mvp_flow.py --base-url http://127.0.0.1:18000/api/v1 --expect-mode mock --verify-db --timeout-seconds 180
cd apps/backend && uv run pytest
cd apps/backend && uv run ruff check .
cd apps/backend && MYPYPATH=src uv run mypy scripts/smoke_mvp_flow.py scripts/mock_openai_provider.py scripts/seed_local.py src/viraldy/modules/campaign_packs/repository.py src/viraldy/platform/auth/local_test.py tests/unit/test_campaign_pack_repository.py tests/unit/test_local_test_auth.py
cd apps/backend && uv run bandit -q -r src
cd apps/backend && uv run pip-audit
```

Results:

- RBAC/auth ruff subset: passed.
- RBAC/auth unit subset: `20 passed`.
- Full backend unit suite: `71 passed`.
- Clean Postgres migration integration: `1 passed`.
- Full backend lint: passed.
- Backend unit + architecture + contract + clean migration suite: `80 passed`.
- S2 backend lint including new migration: passed.
- S2 targeted unit suite: `19 passed`.
- S2 backend unit + architecture + contract + clean migration suite:
  `86 passed`, coverage `71.90%`.
- S3 backend lint across `src`, `tests`, and all Alembic versions: passed.
- S3 backend unit + architecture + contract + clean migration suite:
  `94 passed`, coverage `72.79%`.
- S4 backend lint with `.backend_deps/` ignored: passed.
- S4 targeted mypy across ViralKit/products/Campaign Pack/PatternKit public
  boundaries: passed, `no issues found in 24 source files`.
- S4 ViralKit unit suite: `7 passed`, coverage `73.17%`.
- S4 clean Postgres migration integration: `1 passed`, coverage `98.45%`.
- S4 full backend pytest: `101 passed`, coverage `73.08%`.
- S5 full backend lint: passed.
- S5 targeted mypy: passed, `no issues found in 31 source files`.
- S5 AI/generation/job/OpenAPI targeted suite: `33 passed`. Coverage was
  intentionally disabled for this narrow run; the full suite is the coverage
  gate.
- S5 clean Postgres migration integration: `1 passed`, coverage `89.32%`.
  This also verifies canonical idempotent-job selection when canonical and
  legacy alias rows coexist.
- S5 full backend pytest: `121 passed`, coverage `72.49%`.
- S5 dependency audit: no known vulnerabilities; the local unpublished
  `viraldy-backend` package is not present on PyPI and was skipped.
- S5 Docker Compose structure validation: passed. The local `.env` file is not
  present, so validation omitted only the `env_file` entries while preserving
  all service, command, dependency, queue, and network structure.
- S6 deletion/health/evaluation/OpenAPI targeted suite: `20 passed`.
- S6 targeted mypy: passed, `no issues found in 22 source files`.
- S6 full backend lint: passed.
- S6 clean Postgres migration integration: `1 passed`, coverage `73.73%`.
  Besides zero-to-head migration, this verifies DB-first hard deletion,
  sampled-frame and multi-frame key discovery, persisted outbox state,
  failure/retry behavior, cross-workspace graph rejection, expired upload
  cleanup, orphan cleanup, and protection of referenced/recent objects.
- S6 full backend pytest: `139 passed`, coverage `73.66%`.
- S6 dependency audit: no known vulnerabilities; the local unpublished
  `viraldy-backend` package is not present on PyPI and was skipped.
- S6 diff whitespace validation: passed.
- S6 scoped secret-pattern scan: no matches.
- Independent S6 review initially found storage-before-DB ordering, incomplete
  nested frame-key discovery, readiness coupling to worker/AI, and a malformed
  cross-workspace FK cascade risk. All findings were fixed and covered by
  automated tests before commit.
- S7 fixture HTTP E2E: passed with four successful Celery jobs and DB
  verification. It exercised auth identity, seeded product/assets, two
  reference analyses, exact Creative DNA lineage, PatternKit review and
  validation, ViralKit composition, concept selection, Campaign Pack
  compilation, Preflight, recommendation acceptance, three feedback writes,
  and required product events.
- S7 mock-provider HTTP E2E: passed with four successful Celery jobs and DB
  verification. It additionally created a real MP4 with ffmpeg, uploaded four
  assets through presigned MinIO URLs, ran ASR/vision/chat through the local
  OpenAI-compatible provider, and persisted `ai_model_runs` in `mock` mode.
- S7 full backend pytest: `142 passed`, coverage `73.77%`.
- S7 full backend ruff: passed.
- S7 targeted mypy for all changed Python entrypoints/modules/tests: passed,
  `no issues found in 7 source files`.
- Full-project `mypy src` is not clean: `45 errors in 13 files`. These are
  existing typing gaps outside the S7 diff and are not represented as a passed
  release gate.
- S7 Bandit scan: passed after documenting the reviewed ffmpeg/ffprobe
  subprocess boundary; argv is used without a shell, executable paths are
  locally resolved, and calls have a timeout.
- S7 dependency audit: no known vulnerabilities; the unpublished local
  `viraldy-backend` package was skipped because it is not on PyPI.
- Independent S7 review identified three false-positive risks in the initial
  smoke assertions. Before commit, event checks were changed to exact
  event-type/subject-ID pairs, job persistence checks to a terminal event for
  every distinct run job, and model-run checks to exact
  workspace/PatternKit/ViralKit/mode/completed rows. Both captured runs passed
  the strengthened DB and event-subject checks.

Local `alembic current` against the default localhost database failed because
the local Postgres credentials rejected `viraldy`; the clean migration test used
Testcontainers Postgres and passed.

## 10. CI Result

Not configured for this milestone, per the current release instruction that
GitHub Actions are not needed. Local gates are recorded above, but they are not
reported as GitHub CI success. The original goal's `GitHub CI passes` item
therefore remains incomplete.

## 11. Fixture And Mock E2E Evidence

The executable runner is `apps/backend/scripts/smoke_mvp_flow.py`. `make smoke`,
`make smoke-fixture`, and `make smoke-mock` now invoke this runner instead of a
missing pytest file. Both modes verify the configured AI mode, `/me`, terminal
job status, typed output ranges, exact PatternKit source lineage, PatternKit
human gates, three distinct ViralKit concepts, buyer/creator persona separation,
Campaign Pack version creation, Preflight recommendation, seller action,
field-level feedback, required first-party events, processing job events, and
mock model-run persistence.

Fixture evidence from 2026-07-30:

- status: `ok`
- workspace: `181a2e7f-1afd-47ba-8ad5-54895bd6d76f`
- Quick score: `6ba27a41-aa5d-4286-a48b-d23bc3de8e92`
- Creative DNA versions: `238ad1b1-a1ad-4a78-80f7-98e535719281`,
  `9f440d2b-17d0-4c37-a6c0-2ef0846fbcea`
- PatternKit: `a4032d00-5148-41ff-8df0-57c02db80102`
- ViralKit: `1f80f5b8-5ce5-476d-808a-1ac0b326a4ee`
- Campaign Pack version: `b8d34004-f920-4168-a6e8-1d719517c33a`
- Preflight: `f758f068-699d-4333-9e60-c5fbddad15cc`
- Recommendation: `8b774911-2b89-43d5-879c-cb76a07ac0ca`
- completed jobs: 4

Mock-provider evidence from 2026-07-30:

- status: `ok`
- Quick score: `ac95d92b-facf-4c46-b23c-3be234ff8453`
- Creative DNA versions: `2a14fb31-0f48-46f4-b4d8-4d083f75ebb6`,
  `2fb93827-b7fb-4509-8bda-c19a410d9f23`
- PatternKit: `21f04292-bb63-4ceb-b715-c736c4ff3576`
- ViralKit: `31eb4f51-2f12-4804-a502-dce84c0991f7`
- Campaign Pack version: `9741c1e2-bda8-47ff-8c06-61c584e8b070`
- Preflight: `c4f3739a-be06-4934-aa9b-3abf91e282da`
- Recommendation: `f2a8d6cc-a43c-4baf-bfcf-3794aa4125a1`
- completed jobs: 4

The runs exposed and led to fixes for two real defects: the local-test identity
email was rejected by `EmailStr`, and Campaign Pack response serialization
attempted async lazy loading of an expired `updated_at`. The mock provider was
also extended to return schema-valid PatternKit and ViralKit responses through
the same OpenAI-compatible HTTP boundary.

The extended E2E sequence in the original goal is not completely consolidated
into this runner: workspace/product creation, revision re-upload, workspace
deletion, and object-cleanup confirmation are covered by separate API/service
and clean-Postgres tests, not by the same fixture/mock smoke execution.

## 12. Known Limitations

- PatternKit module exists, but live provider qualification, full HTTP
  tenant-isolation coverage, and performance-evidence promotion rules remain
  pending. Mock-provider contract execution passed. Source deletion removes
  dependent PatternKit/ViralKit/Campaign Pack lineage through the hard-deletion
  cascade.
- ViralKit module exists, but full HTTP tenant-isolation coverage, live provider
  qualification and frontend integration remain pending.
- Feedback module exists for workspace-scoped field-level correction, and
  PatternKit/ViralKit both have resource-local feedback endpoints.
- Product events module exists for workspace-scoped export, but not every
  required event producer is wired yet.
- Generation foundation is implemented, but live Seedream/Seedance provider
  qualification and real generated-object storage tests remain pending.
- Product Context still needs expansion to the full private beta section model.
- Recommendation product snapshots and full source-version metadata remain incomplete.
- Model-run trace fields and the operation registry are present; existing
  analysis services still need complete registry-driven execution coverage.
- Health checks are contract-tested but have not yet been qualified against the
  deployed private-beta PostgreSQL, Redis, S3-compatible service, Celery worker,
  and live AI provider.
- Retention is invoked per workspace through the API; automatic per-workspace
  scheduling is not configured. Pending object-cleanup outbox retries are
  automatic every five minutes.
- Evaluation mode records whether candidates came from fixture, mock, or live
  execution. The harness evaluates captured output and intentionally does not
  call providers itself.
- Full-project mypy is not clean; the changed S7 scope is clean.
- GitHub CI, PR, and release tag are pending.

## 13. OIDC Environment Variables

Required for OIDC mode:

- `AUTH_MODE=oidc`
- `OIDC_ISSUER_URL`
- `OIDC_AUDIENCE`
- `OIDC_JWKS_URL`

Optional:

- `OIDC_ALLOWED_ALGORITHMS`, default `RS256`
- `OIDC_JWKS_CACHE_SECONDS`, default `300`

Production/staging rejects:

- `AUTH_MODE=local_test`
- `AUTH_DISABLED=true`
- wildcard CORS origins
- missing OIDC issuer/audience/JWKS URL when OIDC is enabled

## 14. Dola/Seed Environment Variables

Implemented AI analysis settings:

- `AI_MODE`
- `AI_PROVIDER`
- `AI_BASE_URL`
- `AI_API_KEY`
- `AI_TEXT_MODEL`
- `AI_VISION_MODEL`
- `AI_SUPPORTS_JSON_SCHEMA`
- `AI_SUPPORTS_IMAGE_URL`
- `AI_REQUEST_TIMEOUT_SECONDS`
- `AI_MAX_RETRIES`
- `AI_MAX_OUTPUT_TOKENS`

Implemented generation settings:

- `IMAGE_GENERATION_ENABLED`
- `VIDEO_GENERATION_ENABLED`
- `IMAGE_GENERATION_MODEL`
- `VIDEO_GENERATION_MODEL`

Implemented job recovery setting:

- `JOB_STALE_AFTER_SECONDS`, default `900`

## 15. Seedream/Seedance Activation Steps

Feature flags default to off. Activation requires:

1. Deploy a qualified provider/proxy implementing
   `POST {AI_BASE_URL}/media/generations`.
2. Set `AI_MODE=live`, `AI_PROVIDER`, `AI_BASE_URL`, and `AI_API_KEY`.
3. Set `IMAGE_GENERATION_MODEL` and/or `VIDEO_GENERATION_MODEL`.
4. Run provider qualification and output-contract tests.
5. Enable `IMAGE_GENERATION_ENABLED=true` and/or
   `VIDEO_GENERATION_ENABLED=true`.

Do not enable either flag before provider qualification. Fixture and mock modes
use deterministic artifacts and do not prove visual model quality.

## 16. Data Deletion Evidence

Implemented and exercised against clean Testcontainers PostgreSQL:

- Workspace hard deletion removes the workspace, assets, versions, media
  artifacts, evidence, dependent lineage, traces, and all discovered
  non-fixture object keys.
- The test persists sampled frames inside media artifact JSON and multiple frame
  keys inside evidence JSON; all five unique source/media keys are deleted.
- A second PostgreSQL connection is opened from inside the recording storage
  adapter. It proves business rows are already absent and the pending outbox is
  committed before the first object DELETE occurs.
- Failure injection makes the first object DELETE raise. Business rows remain
  deleted, the audit reports `storage_cleanup_pending`, the outbox stays
  `pending`, and a retry succeeds idempotently and completes the audit.
- Retention deletes an expired incomplete upload, preserves an old referenced
  active object, preserves a recent unreferenced object, removes an old
  unreferenced orphan, and proves the DB-first ordering through a separate
  connection.
- Direct and generic deletion endpoints require `data.delete`; root resource
  lookup and every graph query/delete are workspace-scoped. A deliberately
  malformed workspace-B artifact pointing at a workspace-A asset is rejected
  with `DELETION_TENANT_GRAPH_CONFLICT`; neither tenant's row is deleted.

## 17. Incomplete Items

The backend implementation has completed the local S7 fixture/mock gates, but
the release is not technically frozen. Remaining items:

- Remaining S3 hardening: PatternKit live provider qualification, full
  HTTP tenant-isolation tests, and performance evidence promotion rules.
- Consolidate workspace/product creation, revision upload, workspace deletion,
  and object-cleanup verification into each E2E mode; these are currently
  proven by separate smoke and automated test paths.
- Resolve the 45 full-project mypy errors if a clean typecheck is adopted as a
  release gate.
- GitHub CI is intentionally not configured for the current milestone and
  therefore cannot be marked passed.
- PR URL and release tag `v0.1.0-beta-rc1` are pending. No tag should be created
  while the freeze statement remains false.
