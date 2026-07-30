# Viraldy Private Beta Tech Freeze Audit

Status: In progress
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
- Current S4 implementation commit SHA: pending until this audit update is committed.
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

## 3. Migration List

- `0001_initial_foundation`
- `0002_creative_intelligence_mvp`
- `0003_keyless_product_hardening`
- `0004_creative_domain_contracts`
- `0005_auth_workspace_rbac`
- `0006_feedback_events_model_runs`
- `0007_pattern_kits`
- `0008_viral_kits`

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

- Live/mock provider qualification against real Dola/Seed-compatible responses.
- Full HTTP tenant-isolation coverage for every PatternKit endpoint.
- Deletion invalidation policy when source evidence/assets are removed.
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

Pending:

- Health endpoints `/health/live`, `/health/ready`, `/health/dependencies`,
  `/health/worker`
- Generation endpoints/foundations where required

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

Local `alembic current` against the default localhost database failed because
the local Postgres credentials rejected `viraldy`; the clean migration test used
Testcontainers Postgres and passed.

## 10. CI Result

Pending. Do not claim GitHub CI success from local tests.

## 11. Fixture And Mock E2E Evidence

Pending for the full private beta flow. Existing unit tests now cover media
evidence, Creative DNA, PatternKit fixture extraction, PatternKit state
transitions, PatternKit feedback, ViralKit fixture composition, ViralKit
product-version locking, ViralKit concept actions, ViralKit-to-Campaign-Pack
lineage, TikTok scorer, campaign pack semantics, preflight requirements, and
recommendations. The full fixture/mock E2E path is not yet implemented.

## 12. Known Limitations

- PatternKit module exists, but live/mock provider qualification, full HTTP
  tenant-isolation coverage, deletion invalidation, and performance-evidence
  promotion rules remain pending.
- ViralKit module exists, but full HTTP tenant-isolation coverage, live provider
  qualification, frontend integration, and generation execution remain pending.
- Feedback module exists for workspace-scoped field-level correction, and
  PatternKit/ViralKit both have resource-local feedback endpoints.
- Product events module exists for workspace-scoped export, but not every
  required event producer is wired yet.
- Generation foundation is still absent.
- Health endpoint set is incomplete.
- Job statuses still use the pre-existing naming in parts of the codebase.
- Product Context still needs expansion to the full private beta section model.
- Recommendation product snapshots and full source-version metadata remain incomplete.
- Model-run trace fields are present, but the full Dola/Seed operation registry
  and generation run foundation remain incomplete.
- Data deletion/retention is incomplete.
- GitHub CI and release tag are pending.

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

Pending implementation. Existing AI analysis settings:

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

Required generation additions still pending:

- `IMAGE_GENERATION_ENABLED`
- `VIDEO_GENERATION_ENABLED`
- `IMAGE_GENERATION_MODEL`
- `VIDEO_GENERATION_MODEL`

## 15. Seedream/Seedance Activation Steps

Pending. Feature flags and generation run persistence have not been added yet.

## 16. Data Deletion Evidence

Pending. Existing soft deletes cover selected MVP entities, but private beta
retention cleanup, storage cleanup, workspace cascade policy, and deletion audit
records are not yet implemented.

## 17. Incomplete Items

The backend is not technically frozen yet. Remaining milestones:

- Remaining S2 job naming/progress additions beyond model-run trace fields.
- Remaining S3 hardening: PatternKit live/mock provider qualification, full
  HTTP tenant-isolation tests, deletion invalidation, and performance evidence
  promotion rules.
- S5 provider/generation/job integration.
- S6 deletion, health, evaluation harness.
- S7 full fixture/mock E2E, GitHub CI, PR, and release tag.
