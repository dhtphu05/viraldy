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
- Current S2 commit SHA: pending
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

## 3. Migration List

- `0001_initial_foundation`
- `0002_creative_intelligence_mvp`
- `0003_keyless_product_hardening`
- `0004_creative_domain_contracts`
- `0005_auth_workspace_rbac`
- `0006_feedback_events_model_runs`

`0005_auth_workspace_rbac` adds `users.last_login_at`, converts legacy
`workspace_members.role='editor'` to `member`, and adds check constraints for
valid user status and workspace roles.

`0006_feedback_events_model_runs` adds `feedback_items` and `product_events`,
adds private-beta trace fields to `ai_model_runs`, normalizes legacy
recommendation actions into the supported action set while preserving the prior
action in `metadata_json.legacy_action_type`, and adds constraints/indexes for
new append-only data.

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

Not yet implemented in this goal branch.

Required next state:

- Add `pattern_kits`, `pattern_kit_versions`, `pattern_kit_sources`,
  `pattern_kit_evidence_links`, and `pattern_kit_actions`.
- Add `PatternKitV1` strict contracts with evidence refs, temporal sequence,
  component patterns, applicability, adaptation instructions, performance
  summary, confidence, uncertainties, and provenance.
- Add API, service, repository, public boundary, fixture provider, tests, and events.

## 7. ViralKit Contract Summary

Not yet implemented in this goal branch.

Required next state:

- Add `viral_kits`, `viral_kit_versions`, `viral_kit_pattern_links`,
  `viral_kit_concept_actions`, and `viral_kit_campaign_pack_links`.
- Add `ViralKitV1` strict contracts with product snapshot, deterministic pattern
  match, adaptation plan, exactly three diverse concepts, test matrix, campaign
  pack links, preflight requirement links, generation briefs, risks, confidence,
  and provenance.
- Add API, service, repository, public boundary, fixture composer, tests, and events.

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

Pending:

- PatternKit endpoints
- ViralKit endpoints
- PatternKit/ViralKit-specific feedback convenience endpoints
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

Local `alembic current` against the default localhost database failed because
the local Postgres credentials rejected `viraldy`; the clean migration test used
Testcontainers Postgres and passed.

## 10. CI Result

Pending. Do not claim GitHub CI success from local tests.

## 11. Fixture And Mock E2E Evidence

Pending for private beta full flow. Existing unit tests cover media evidence,
Creative DNA, TikTok scorer, campaign pack semantics, preflight requirements,
and recommendations, but the full private beta E2E path is not yet implemented.

## 12. Known Limitations

- PatternKit module is still absent.
- ViralKit module is still absent.
- Feedback module exists for workspace-scoped field-level correction, but
  PatternKit/ViralKit resource-local feedback endpoints are pending.
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
- S3 PatternKit contracts, persistence, service, API, fixtures, tests.
- S4 ViralKit contracts, matcher, composer, persistence, Campaign Pack links, tests.
- S5 provider/generation/job integration.
- S6 deletion, health, evaluation harness.
- S7 full fixture/mock E2E, GitHub CI, PR, and release tag.
