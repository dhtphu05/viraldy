# Viraldy Private Beta Tech Freeze Audit

Status: Backend technically frozen for supervised private beta
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
- S8 release-validation implementation SHA: `33c8780`
- S9 technical-freeze completion SHA:
  `73f7d1834378680926e796cc516dd3991d095b81`
- PR URL: `https://github.com/dhtphu05/viraldy/pull/15`
- Release tag: `v0.1.0-beta-rc1` points to the final audit commit containing
  this file.

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

### S8 Auth, Tenant, Revision, Events, And Release Validation

- `apps/backend/tests/integration/test_http_auth_tenancy.py`
- `apps/backend/src/viraldy/modules/assets/`
- `apps/backend/src/viraldy/modules/identity/public.py`
- `apps/backend/src/viraldy/modules/references/`
- `apps/backend/src/viraldy/modules/creative_dna/`
- `apps/backend/src/viraldy/modules/preflight/`
- `apps/backend/src/viraldy/modules/product_events/`
- `apps/backend/src/viraldy/modules/campaign_packs/exporter.py`
- `apps/backend/src/viraldy/modules/campaign_packs/router.py`
- `apps/backend/src/viraldy/modules/campaign_packs/schemas.py`
- `apps/backend/src/viraldy/modules/campaign_packs/service.py`
- `apps/backend/src/viraldy/worker/tasks/process_asset.py`
- `apps/backend/scripts/smoke_mvp_flow.py`
- `Makefile`
- `apps/backend/README.md`

### S8 Tests

- `apps/backend/tests/integration/test_http_auth_tenancy.py`
- `apps/backend/tests/unit/test_campaign_pack_export.py`
- `apps/backend/tests/unit/test_policies.py`
- `apps/backend/tests/contract/test_openapi.py`

### S9 Technical-Freeze Completion

- `apps/backend/src/viraldy/modules/pattern_kits/performance.py`
- `apps/backend/src/viraldy/modules/pattern_kits/contracts.py`
- `apps/backend/src/viraldy/modules/pattern_kits/provider.py`
- `apps/backend/src/viraldy/modules/pattern_kits/service.py`
- `apps/backend/src/viraldy/modules/ai_gateway/router.py`
- `apps/backend/src/viraldy/modules/ai_gateway/service.py`
- `apps/backend/src/viraldy/modules/ai_gateway/repository.py`
- `apps/backend/src/viraldy/modules/ai_gateway/schemas.py`
- `apps/backend/src/viraldy/platform/config/settings.py`
- `apps/backend/src/viraldy/api/main.py`
- `apps/backend/scripts/mock_openai_provider.py`
- `apps/backend/scripts/smoke_mvp_flow.py`
- Existing typing gaps were corrected in media analysis, Creative DNA,
  Campaign Pack, adaptations, preflight, TikTok scorer, and worker modules
  without changing their public behavior.

### S9 Tests

- `apps/backend/tests/unit/test_pattern_kits.py`
- `apps/backend/tests/unit/test_viral_kits.py`
- `apps/backend/tests/unit/test_ai_gateway.py`
- `apps/backend/tests/integration/test_http_auth_tenancy.py`
- `apps/backend/tests/contract/test_openapi.py`

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

Verified in S8 against migrated Testcontainers PostgreSQL through the ASGI HTTP
boundary:

- Missing bearer, malformed auth scheme, and invalid token return normalized
  `401 UNAUTHENTICATED` envelopes.
- Repeated provisioning returns the same user; concurrent provisioning produces
  one row, one stable UUID, and one `user_signed_up` event.
- Suspended users are denied with `403 USER_SUSPENDED`.
- Successful first authentication persists the user and does not duplicate the
  signup event on later requests.

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

S8 tenant evidence:

- The exact role/permission matrix is asserted in unit tests.
- Two real workspaces and users are created through HTTP on migrated PostgreSQL.
- Missing membership returns generic `403 FORBIDDEN` across products, assets,
  references, Creative DNA, PatternKit, ViralKit, Campaign Pack, Preflight,
  recommendations, feedback, events, and jobs.
- Actual workspace-B rows for each major resource type return workspace-scoped
  `404` when requested through a workspace-A URL.
- Viewer read access succeeds while viewer writes and member-list access fail.
- Campaign Pack export and asset revision endpoints are included in tenant
  checks.

S9 tenant evidence:

- Every PatternKit and ViralKit mutating route is exercised against a real
  foreign resource and returns a workspace-scoped `404`.
- Cross-workspace PatternKit source and ViralKit product inputs return scoped
  `404`; foreign filter IDs produce empty lists without leaking existence.
- Viewer reads succeed while PatternKit/ViralKit mutations and model-run export
  fail with `403`.
- Positive PatternKit and ViralKit hard deletion is verified.

Optional owner-grant restrictions beyond the explicit private-beta rule are
outside this release contract.

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

Completed in S9:

- `none`, `directional`, and `supported` performance labels have validated
  evidence contracts. Supported evidence enforces configurable minimum asset,
  campaign, and metric sample counts.
- Directional evidence requires a sample-size caveat. Directional and supported
  evidence require a non-causal caveat.
- Date ranges, metric names/sources/statistics, sample sizes, and percentile
  consistency are validated.
- Winner/winning labels are rejected when no performance evidence exists.
- Learned-pattern promotion requires explicit seller review or qualifying
  performance evidence.
- Multi-source disagreement is preserved in uncertainties, exact-source
  script reuse is rejected, and source taxonomy versions remain traceable.
- All mutating PatternKit routes have foreign-tenant tests.

Live provider quality qualification remains planned for the next-month
calibration phase described by the mission. Configuration key-readiness and the
OpenAI-compatible provider contract are release-gated and pass.

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

Completed in S9:

- Exactly three concepts, pairwise strategic diversity, product grounding,
  buyer/creator persona separation, hard category constraints, applicability,
  governance preservation, duplicate rejection, stale Product Context
  rejection, append-only versions, exact Campaign Pack lineage, and concept
  actions are covered by unit tests.
- User-authored versions cannot replace locked Product Context snapshots,
  PatternKit provenance, model/prompt provenance, or product governance.
- All mutating ViralKit routes have foreign-tenant tests.

Live provider quality qualification and generated-media quality qualification
remain next-month calibration work. Frontend PatternKit/ViralKit screens are
outside this backend completion goal; the existing frontend still passes lint
and production build.

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

Implemented in S8:

- `POST /api/v1/workspaces/{workspace_id}/assets/{asset_id}/versions/upload-sessions`
- `POST /api/v1/workspaces/{workspace_id}/assets/{asset_id}/versions/{asset_version_id}/complete-upload`
- `GET /api/v1/workspaces/{workspace_id}/assets/{asset_id}/versions`
- `POST /api/v1/workspaces/{workspace_id}/campaign-packs/{campaign_pack_id}/exports`

Implemented in S9:

- `GET /api/v1/workspaces/{workspace_id}/model-runs`
- `GET /api/v1/workspaces/{workspace_id}/model-runs/{model_run_id}`

Model-run reads require `data.export`, are workspace-scoped, and expose only
the safe error field rather than the internal provider error message.

S8 behavior implemented:

- UGC revisions are immutable, receive serialized version numbers, and can
  complete out of order without moving `current_version_id` backward.
- Repeated completion is idempotent and does not duplicate `ugc_uploaded` or
  `revision_uploaded` events.
- Revision creation and completion explicitly reject non-UGC assets so a
  reference source cannot be silently replaced behind existing lineage.
- Campaign Pack export supports canonical JSON and creator-readable text from
  the current immutable version, includes version/source traceability, requires
  `data.export`, and emits `campaign_pack_exported`.
- Successful reference analysis emits `reference_analyzed` in the same worker
  transaction as the DNA and reference status.
- Successful Creative DNA and Preflight reads emit `creative_dna_viewed` and
  `preflight_viewed` with actor and subject IDs.
- First user provisioning and reference creation emit `user_signed_up` and
  `reference_uploaded`.
- Required product-event writes are first-party transactional audit records,
  not best-effort external telemetry.

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
cd apps/backend && uv run pytest tests/integration/test_http_auth_tenancy.py -q --no-cov
cd apps/backend && uv run pytest
cd apps/backend && uv run ruff check <all S8 changed Python files>
cd apps/backend && uv run ruff format --check <all S8 changed Python files>
cd apps/backend && uv run mypy src
cd apps/backend && uv run bandit -q -r src && uv run pip-audit
cd apps/web && pnpm lint && pnpm build
make smoke-release-fixture
make smoke-release-mock
git diff --check
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
- The S7 full-project `mypy src` baseline had `45 errors in 13 files`. S9
  resolved those gaps; the final strict typecheck is recorded below.
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
- S8 HTTP auth/RBAC/tenant/revision integration: `2 passed` against a migrated
  Testcontainers PostgreSQL database.
- S8 full backend pytest on the final implementation state: `148 passed`,
  coverage `74.60%` against the configured 70% gate.
- S8 changed-file Ruff lint and format checks: passed.
- S8 retained the prior `45 errors in 13 files` baseline; S9 resolved the full
  set without weakening mypy configuration.
- S8 Bandit: passed. Dependency audit: no known vulnerabilities; the
  unpublished local package was skipped because it is not on PyPI.
- Frontend lint/build: passed with zero errors. ESLint reports nine existing
  Fast Refresh warnings; Vite reports an existing large-chunk warning.
- S8 fixture isolated-lifecycle E2E: passed on the final code state with four
  successful jobs, required event subjects, Campaign Pack export, immutable UGC
  revision, DB verification, storage-prefix cleanup, and deletion status
  `succeeded`.
- S8 mock OpenAI-compatible isolated-lifecycle E2E: passed on the final code
  state through ASR and vision/chat HTTP calls with the same lifecycle and
  deletion assertions.
- Independent S8 review found that revisions were initially available to
  reference assets. The implementation now rejects non-UGC revision create and
  completion; the regression is covered by the HTTP PostgreSQL test.
- The S8 migration check ran `alembic upgrade head` successfully against the
  existing local Viraldy PostgreSQL container; clean zero-to-head migration is
  also covered by Testcontainers.
- Final diff whitespace and scoped secret-pattern checks: passed.

S9 final verification on 2026-07-30:

- Full backend pytest: `167 passed`, total coverage `75.76%`; configured gate is
  70%. One existing Starlette deprecation warning remains.
- Strict full-project typecheck:
  `uv run mypy src --no-pretty --no-error-summary` passed with zero errors.
- Full backend Ruff lint: passed.
- Ruff formatting for all 26 changed Python files: passed. A full-repository
  format check still identifies 26 pre-existing files outside this change, so
  no unrelated formatting rewrite was performed.
- Clean zero-to-head migration test:
  `tests/integration/test_migrations.py -q --no-cov` passed (`1 passed`).
- Explicit no-audio regression suite passed (`2 passed`).
- Bandit source scan passed.
- `pip-audit` reported no known vulnerabilities; the unpublished local package
  was skipped.
- Frontend lint passed with zero errors and nine existing Fast Refresh
  warnings. Frontend production build passed with existing chunk-size and
  Nitro `inlineDynamicImports` warnings.
- `git diff --check` passed.
- Scoped secret scan for private keys, OpenAI/GitHub/Slack tokens, and AWS key
  IDs returned no matches.
- Live OpenAI-compatible/Seed-style configuration is key-ready when the
  required provider URL, key, and model IDs are supplied; missing-key
  configuration is explicitly not ready.
- Independent final review found three version-integrity bypasses: top-level
  ViralKit governance replacement, ViralKit Product Context/provenance
  tampering, and user-authored PatternKit performance self-certification.
  Four regression tests were added, all three code paths were fixed, and the
  reviewer confirmed the findings closed before the final gates.

## 10. CI Result

GitHub Actions are explicitly waived by the user for this milestone and were
not configured. Local gates are recorded above, but they are not represented as
GitHub CI success. This is a documented release exception, not a technical pass.

## 11. Fixture And Mock E2E Evidence

The executable runner is `apps/backend/scripts/smoke_mvp_flow.py`.
`make smoke-release-fixture` and `make smoke-release-mock` invoke it with
`--isolated-lifecycle --verify-db`. Each mode creates a workspace and detailed
Product Context, uploads reference and UGC media through presigned MinIO URLs,
executes four Celery jobs, validates exact PatternKit/ViralKit lineage, exports
the Campaign Pack, runs Preflight and the recommendation/feedback loop, uploads
an immutable UGC revision, checks required first-party event subjects, then
hard-deletes the workspace and verifies PostgreSQL audit state plus an empty
workspace object prefix.

Final fixture evidence from 2026-07-30:

- status: `ok`
- workspace: `be4b9dc0-7605-496c-b365-f05e8db0d326`
- Quick score: `5e17d088-f852-4c05-82c3-3df5790e0ecf`
- Creative DNA versions: `4311893f-d7c4-4e02-8cb8-3beb6fca3e82`,
  `62c4cce6-a873-41dd-95d5-eb416363eab9`
- PatternKit: `f1e00121-fa26-45b1-9ee1-ed6fefbd1ca6`
- ViralKit: `b2708b07-8743-42b6-8c5e-d1a30cd8155f`
- Campaign Pack: `cc520561-f45b-4a15-b957-6185d0e7ad6c`
- Campaign Pack version: `f5a42333-dd5c-4a82-8c87-dad2bec25b44`
- Preflight: `62cf1907-0061-481d-a744-7c12b7888bfb`
- Recommendation: `ce676e98-e85b-4214-a4ed-0834315768ce`
- UGC revision version: `75af991b-db5c-4944-a66a-02c13531193b`
- completed jobs: `847d2ce4-d011-4e89-92ac-9b185c9eb708`,
  `80267a04-bd14-446b-bfd1-30aa5366cba0`,
  `bd1aeda3-824f-4259-9371-57e9c55463b4`,
  `2ce07a5f-3eda-4f7a-9d77-0f9754886064`
- workspace deletion status: `succeeded`

Final mock-provider evidence from 2026-07-30:

- status: `ok`
- workspace: `433ed887-9c56-47ef-b837-e7192750c415`
- Quick score: `cf9056a6-7ddd-471e-8c0e-ddf7c6539da7`
- Creative DNA versions: `848e1fbc-961f-43cd-9e1b-80bd0131fc75`,
  `0ba1111e-9927-4ca9-86d0-dadec68d41e4`
- PatternKit: `e1104344-2143-4aaf-88c1-2a996237904c`
- ViralKit: `c6fb510f-e1ac-4a41-95b1-1ffc39f77712`
- Campaign Pack: `da2fdb5a-8543-44e7-abf7-6b6c71219edb`
- Campaign Pack version: `29874621-fcd3-4419-9336-af32112e9946`
- Preflight: `7c878680-dea3-43e5-9abd-eedf107286a6`
- Recommendation: `ee0e5cc1-1154-493d-92f6-ec132649bb46`
- UGC revision version: `bc57ac64-ae97-4285-826b-add1a94895ef`
- completed jobs: `ef0ccb04-2c9d-4394-af3c-34d8b3fbc527`,
  `2c9876a2-fb37-4817-b50d-10f5717bd554`,
  `bbf1b700-26df-4fb2-aa10-57fa16fc8b5c`,
  `6bd0ac31-82b6-4103-a69d-cb7904ceb00d`
- workspace deletion status: `succeeded`

The runs exposed and led to fixes for two real defects: the local-test identity
email was rejected by `EmailStr`, and Campaign Pack response serialization
attempted async lazy loading of an expired `updated_at`. The mock provider was
also extended to return schema-valid PatternKit and ViralKit responses through
the same OpenAI-compatible HTTP boundary.

Both final runs include model-run listing through the workspace-scoped HTTP
API, in addition to SQL verification. They also include: workspace
and Product Context creation, revision re-upload, required event verification,
workspace deletion, deletion audit/storage-batch success, database absence, and
object-prefix cleanup.

## 12. Known Limitations

- Live Dola/Seed model quality, latency, and cost qualification remains for the
  next-month data and calibration phase. Provider configuration key-readiness
  and the OpenAI-compatible contract pass; live mode never falls back silently.
- Source deletion removes dependent PatternKit/ViralKit/Campaign Pack lineage
  through the hard-deletion cascade.
- Feedback module exists for workspace-scoped field-level correction, and
  PatternKit/ViralKit both have resource-local feedback endpoints.
- Required private-beta product event producers are wired and exercised in both
  final E2E modes. Event persistence is intentionally transactional with the
  action it audits.
- Generation foundation is implemented, but live Seedream/Seedance output
  quality qualification and real generated-object storage tests remain in the
  next-month qualification scope.
- Product Context still needs expansion to the full private beta section model.
- Recommendation product snapshots and full source-version metadata remain incomplete.
- Model-run trace fields and the operation registry are present; existing
  analysis services still need complete registry-driven execution coverage.
- Health and lifecycle checks passed against local PostgreSQL, Redis, MinIO, and
  Celery; deployed-environment and live-provider qualification remain pending.
- Retention is invoked per workspace through the API; automatic per-workspace
  scheduling is not configured. Pending object-cleanup outbox retries are
  automatic every five minutes.
- Evaluation mode records whether candidates came from fixture, mock, or live
  execution. The harness evaluates captured output and intentionally does not
  call providers itself.
- Full-project strict mypy is clean.
- GitHub CI is explicitly waived for this milestone. PR 15 and release tag
  `v0.1.0-beta-rc1` identify this audited branch state.

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

## 17. Incomplete And Deferred Items

No known backend technical blocker remains for the supervised private-beta
freeze.

- GitHub Actions are explicitly waived by the user; this audit does not claim
  CI passed.
- Live Dola/Seed and Seedream/Seedance quality qualification, seller-authorized
  data collection, intelligence calibration, and small compatibility fixes are
  intentionally deferred to the next-month phase defined by the mission.
- Frontend PatternKit/ViralKit product screens are a separate frontend planning
  scope, not a requirement of this backend completion goal.
- Release tag `v0.1.0-beta-rc1` identifies the final audited commit.

Permissible completion statement:

> Viraldy backend is technically frozen for supervised private beta. Remaining
> work is live-model qualification, data collection, intelligence calibration,
> and small bug fixes.
