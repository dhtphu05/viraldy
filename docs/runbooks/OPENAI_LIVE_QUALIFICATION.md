# OpenAI Live Qualification

This runbook separates provider contract checks from Viraldy application E2E
evidence. Read [OpenAI Provider](OPENAI_PROVIDER.md) first.

## Non-Negotiable Claim Boundary

`live_qualified` is allowed only after all of the following are true:

1. a real `OPENAI_API_KEY` was used;
2. execution crossed authenticated application/API, service, database, worker,
   and private object-storage boundaries;
3. live OpenAI model runs were persisted and queryable with correct
   provider/model/prompt/schema/request provenance;
4. all required Golden cases and hard/semantic gates passed;
5. the isolated qualification workspace, database rows, deletion audit,
   storage-deletion batch, and object prefix were cleaned up.

`--check-config`, one live operation, `live_operation_verified`, a contract-only
full flow, mock success, browser rendering, or a report with
`workspace_deleted=false` does not meet that boundary.

Current implementation limit: the default `OpenAIQualificationExecutor` calls
the native provider directly with Golden-derived contract payloads. It reports:

```text
execution_scope=contract
model_runs_persisted=false
workspace_deleted=false
```

Therefore the current CLI can produce `live_contract_verified`, but it cannot
truthfully produce `live_qualified`. The runner only emits `live_qualified` for
all three cases when an application-boundary executor supplies
`execution_scope=application_e2e`, `model_runs_persisted=true`, and
`workspace_deleted=true`. The only such executor currently in the repository is
a unit-test fake; there is no operator CLI flag for it.

The HTTP smoke runner covers real application persistence and cleanup, but it
uses a separate CounterSpace Rack scenario and does not feed its evidence back
into the three-case qualification report. Keep both evidence sets and label the
release `live_contract_verified` plus `application live smoke passed`, not
`live_qualified`, until those boundaries are connected.

## Prerequisites

Required:

- Python 3.12 and `uv`;
- backend dependencies installed;
- PostgreSQL, Redis, private S3-compatible storage, API, worker, and Beat;
- migration head, including `0012_openai_provenance`;
- `ffmpeg` or an explicit seller-owned MP4 for application smoke;
- authenticated workspace access with the required operation permissions;
- a real OpenAI key held only by the backend;
- OpenAI project access to every resolved text, vision, and transcription
  model;
- enough provider budget/rate-limit headroom for multiple structured calls;
- seller-owned, non-private test media until typed per-asset analysis consent is
  implemented.

For local supervised application smoke, `AUTH_MODE=local_test` and
`Bearer local-test` are supported. A production-like auth qualification must use
OIDC and pass a real access token through `SMOKE_AUTH_TOKEN` or `--token`;
local-test auth is blocked in staging/production.

Do not run live qualification on forks, untrusted pull requests, or ordinary
CI. Never place a real key in a command argument, frontend variable, report, or
shell trace.

## Bootstrap

From the repository root:

```bash
cp .env.openai.example apps/backend/.env
make backend-install
make infra-up
make migrate
```

Fill `OPENAI_API_KEY` in the backend secret environment without printing it.
Confirm:

```env
AI_MODE=live
AI_PROVIDER=openai
OPENAI_STORE_RESPONSES=false
```

Start separate terminals:

```bash
make api
make worker
make beat
```

Check infrastructure and safe AI configuration:

```bash
curl -fsS http://localhost:8000/health/dependencies
curl -fsS http://localhost:8000/api/v1/system/ai-readiness
```

The health response may expose only safe state/capability names. It must not
contain the key, key prefix, organization/project identifiers, credentialed
URLs, or raw provider errors.

## Qualification CLI

Run commands from `apps/backend` so `.env` and the relative report directory
resolve correctly.

### 1. Configuration Only

```bash
uv run python scripts/qualify_openai.py --check-config
```

This performs no provider call. Expected live state is
`not_yet_qualified`. It validates:

- native route is `openai`;
- a key is configured, without printing it;
- `store=false`;
- every qualified operation has model, prompt, and schema metadata.

### 2. One Real Operation

Start with a bounded text operation:

```bash
uv run python scripts/qualify_openai.py \
  --operation seller_decision_summary \
  --write-report
```

Then exercise the vision operation contract:

```bash
uv run python scripts/qualify_openai.py \
  --operation media_observation \
  --write-report
```

The qualification `media_observation` operation uses structured Golden scenario
text and does not attach a real image. Actual sampled-frame/base64 transport is
covered by provider tests and the application media path, not by this command
alone.

Successful one-operation state is `live_operation_verified`. It proves a real
native request, strict output validation, safe provider metadata, and no silent
fixture result for that operation. It does not prove persistence or cleanup.

Other accepted operation aliases are:

```text
creative_dna
pattern_kit
viral_kit
adaptation
campaign_pack
seller_decision_summary
revision_message
```

The canonical operation names such as `creative_dna_build` and
`viral_kit_compose` are also accepted.

### 3. Golden Contract Flows

Run one case while diagnosing model access or semantics:

```bash
uv run python scripts/qualify_openai.py \
  --full-flow --case tiktok-shop --write-report

uv run python scripts/qualify_openai.py \
  --full-flow --case pod --write-report

uv run python scripts/qualify_openai.py \
  --full-flow --case dropshipping --write-report
```

Final contract sweep:

```bash
uv run python scripts/qualify_openai.py \
  --full-flow --all-cases --write-report
```

This is a paid multi-call run: eight registered operations plus a bounded
semantic projection per case. It validates Pydantic output, source/evidence and
timestamp gates, native provider/request IDs, exactly three concepts, exact hard
blockers, product hallucination/disclosure/personalization gates, generic-output
rate, and deterministic usefulness/usability rubrics.

A passing current run is `live_contract_verified`, not `live_qualified`, because
its case execution scope is `contract`.

### 4. Opt-In Live Pytest

```bash
VIRALDY_RUN_OPENAI_LIVE_TESTS=1 uv run pytest -m openai_live --no-cov
```

This skips without both the opt-in and key. The current marked test exercises
only live `seller_decision_summary` operation qualification. It is useful as a
provider smoke, not an application or release qualification.

## Application E2E

The application runner crosses HTTP routes, local auth/OIDC, PostgreSQL, Redis,
Celery jobs, object storage, domain services, revision flow, model-run query,
and audited hard deletion.

From `apps/backend`, with API/worker/Beat already running:

```bash
uv run python scripts/smoke_mvp_flow.py \
  --expect-mode live \
  --isolated-lifecycle \
  --verify-db \
  --timeout-seconds 360 \
  --result-path /tmp/viraldy-openai-application-e2e.json
```

Use `--media-file /absolute/path/to/authorized-test.mp4` when a generated smoke
video is insufficient. Without it, the runner requires `ffmpeg` and generates a
small local MP4. `--verify-db` and deletion verification require
`DATABASE_SYNC_URL` in the runner environment.

For OIDC:

```bash
SMOKE_AUTH_TOKEN="$ACCESS_TOKEN" \
uv run python scripts/smoke_mvp_flow.py \
  --base-url https://staging.example.com/api/v1 \
  --expect-mode live \
  --isolated-lifecycle \
  --verify-db \
  --media-file /absolute/path/to/authorized-test.mp4 \
  --timeout-seconds 360 \
  --result-path /tmp/viraldy-openai-application-e2e.json
```

Do not use shell tracing. The runner never needs `OPENAI_API_KEY` as an HTTP
argument; the API and workers already hold it.

The runner verifies:

- authentication and workspace/product creation;
- uploads, media jobs, Creative DNA, PatternKit, ViralKit, and exactly three
  concepts;
- concept selection, Campaign Pack compile/export, UGC Preflight, seller and
  creator presentation;
- recommendation actions, feedback, product events, revision upload, second
  Preflight, and version comparison;
- completed model runs for PatternKit/ViralKit and live preflight presentation
  subjects through the API;
- terminal job events and selected model runs directly in PostgreSQL;
- workspace hard deletion, successful deletion audit and storage batch, zero
  remaining workspace/asset-version rows, and an empty object prefix.

After the run, inspect `/tmp/viraldy-openai-application-e2e.json`. Expected
cleanup evidence is:

```json
{
  "status": "ok",
  "mode": "live",
  "workspace_deletion_status": "succeeded"
}
```

The script deletes the workspace before printing the summary, so inspect model
runs through the API while debugging a non-cleanup run, or retain bounded
pre-deletion evidence in a controlled test environment. Do not weaken cleanup
to preserve a qualification workspace indefinitely.

## Inspect Model Runs

Before deleting a diagnostic workspace:

```bash
curl -fsS \
  -H "Authorization: Bearer ${SMOKE_AUTH_TOKEN:-local-test}" \
  "http://localhost:8000/api/v1/workspaces/${WORKSPACE_ID}/model-runs?limit=500" \
  | jq '.data[] | {
      id, subject_type, subject_id, operation, analysis_mode,
      provider, endpoint_family, model, prompt_name, prompt_version,
      schema_version, status, request_id, provider_request_id,
      attempt_count, repair_attempt_count, latency_ms, usage_json,
      error_code, safe_error_message
    }'
```

Required live evidence:

- `analysis_mode` is `live`;
- `provider` is `openai` for native operations;
- endpoint is `responses` or `audio_transcriptions` as applicable;
- prompt/schema/model match the resolved configuration;
- completed provider calls have provider request IDs;
- failed calls contain only safe errors;
- no key, signed URL, raw frame, complete prompt payload, or full raw response
  appears in summaries.

The endpoint requires `data.export` and is workspace-scoped.

## Reports

With the current command location, reports are written under:

```text
apps/backend/evaluation/reports/openai/<UTC timestamp>/
|- qualification.json
|- qualification.md
|- outputs/
`- failures/
```

Inspect the release fields:

```bash
jq '{
  run_id,
  mode,
  qualification_state,
  passed,
  command,
  sample_size,
  safe_config: {
    provider_route: .safe_config.provider_route,
    api_key_configured: .safe_config.api_key_configured,
    base_url_origin: .safe_config.base_url_origin,
    store_responses: .safe_config.store_responses
  },
  cases: [.case_results[] | {
    scenario_id,
    passed,
    execution_scope,
    model_runs_persisted,
    workspace_deleted
  }],
  failed_gates: [
    (.configuration_gates + .hard_gates + .semantic_gates)[]
    | select(.passed == false)
    | .gate
  ]
}' evaluation/reports/openai/<run-id>/qualification.json
```

The report writer redacts secret-shaped values and signed URLs. Reports still
contain model outputs and may contain seller/product-derived data. This
directory is not currently ignored by the repository. Do not stage or commit
live reports. Move approved evidence to access-controlled storage, record only
the safe release summary, then delete local report and `/tmp` artifacts.

Exit codes:

| Code | Meaning |
|---:|---|
| `0` | All gates applicable to that command passed. |
| `1` | A configuration, hard, or semantic gate failed. |
| `2` | CLI/settings validation failed. |

## Gate Interpretation

Hard gates require:

```text
100% Pydantic-valid final outputs
100% source/version references
100% evidence IDs
100% timestamps in range
0 silent fixture fallbacks
0 sensitive material leaks
provider request IDs for every live call
native OpenAI results for every live operation
exactly 3 ViralKit concepts
exact required hard blockers
```

All-case semantic targets include:

```text
hard-blocker recall >= 0.90
false hard-blocker rate <= 0.10
action-label agreement >= 0.80
critical product-fact hallucinations = 0
required-disclosure false satisfaction = 0
personalization mismatch misses = 0
generic-output rate <= 0.05
creator-message usefulness >= 4/5
Campaign Pack usability >= 4/5
```

These three fixtures are a small sample. A passing report is not universal
accuracy and never guarantees virality, GMV, ROAS, conversion, policy approval,
or sales.

## Failure Triage

| Symptom | Response |
|---|---|
| Config command returns `not_yet_qualified` | Expected before application qualification; continue with real calls. |
| `OPENAI_UNAUTHORIZED` | Check secret/project access without printing credentials. |
| `OPENAI_MODEL_NOT_AVAILABLE` | Set the operation-specific override named by the error, or the family model; rerun one operation first. |
| `OPENAI_RATE_LIMITED` | Wait for provider capacity and reduce operational concurrency; do not switch to fixtures. |
| `OPENAI_TIMEOUT` | Check media/operation size and explicit timeout; keep failure evidence. |
| `OPENAI_REFUSED` or `OPENAI_INCOMPLETE` | Treat as failed output; never parse refusal or partial text as success. |
| `OPENAI_OUTPUT_INVALID` | Review model/schema compatibility and the one repair result; do not loosen required fields to force a pass. |
| Semantic gate fails | Inspect `failures/`, compare with the Golden fixture, adjust prompt/model only with version control, then rerun the failed case. |
| Presentation source says `deterministic_fallback` | The OpenAI presentation run failed and was persisted as failed. Do not count it as live OpenAI presentation success. |
| Smoke leaves `storage_cleanup_pending` | Keep worker/Beat maintenance running, inspect safe deletion audit/batch status, and rerun cleanup verification. |
| Report says `live_contract_verified` | This is the current expected ceiling; application persistence and cleanup are separate evidence. |

## Cleanup And Privacy

Qualification must use isolated, authorized data. Workspace deletion removes
Viraldy rows and private object-storage objects, while minimal audit records
remain. Retention redacts old model-run summaries according to
`MODEL_OUTPUT_RETENTION_DAYS`.

`OPENAI_STORE_RESPONSES=false` is required, but local deletion is not a
third-party provider deletion request. Review OpenAI retention and regional
controls before customer media or unsupervised production use. The current
asset schema has no typed per-asset analysis authorization field; this remains a
production privacy blocker beyond controlled seller-owned qualification media.

## Fixture And Mock Baselines

Before live work, run application baselines from the repository root:

```bash
make smoke-release-fixture
make smoke-release-mock
```

The mock provider must be running and the application must be configured as
described in [OpenAI Provider](OPENAI_PROVIDER.md).

Contract-only baseline reports can be generated from `apps/backend`:

```bash
AI_MODE=fixture uv run python scripts/qualify_openai.py \
  --full-flow --all-cases --write-report

AI_MODE=mock uv run python scripts/qualify_openai.py \
  --full-flow --all-cases --write-report
```

The qualification fixture/mock executors are deterministic and do not contact
the local mock HTTP provider. Use `smoke-release-mock` for actual compatible
HTTP/application evidence.

## Release Decision

If no real-key evidence exists, use:

> Viraldy's OpenAI intelligence path is implemented and mock-verified. Live
> qualification requires a valid OpenAI API key and must be completed before
> customer demonstrations using real model output.

If live contract and separate application-smoke evidence both pass, use:

> Viraldy's OpenAI path is live-contract-verified and the application live smoke
> passed separately. The current qualification CLI does not connect Golden
> cases to persisted application runs and cleanup, so this is not
> `live_qualified`.

Only after a real application-boundary executor connects all three Golden cases,
persists their model runs, and verifies workspace cleanup may the release report
use `live_qualified`. Seller validation remains a separate state.
