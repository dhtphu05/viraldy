# OpenAI Provider

This runbook covers the native OpenAI intelligence path implemented in Viraldy.
It does not make the whole application production-ready by itself. PostgreSQL,
Redis, private object storage, API and Celery processes, authentication, HTTPS,
CORS, deployment secrets, retention, and deletion still have to be operated.

Use the [OpenAI live qualification runbook](OPENAI_LIVE_QUALIFICATION.md) before
making any live qualification claim. Prompt ownership and change control are in
[AI Prompts and Versioning](AI_PROMPTS_AND_VERSIONING.md).

## Status Vocabulary

Keep these states separate in release notes and customer-facing claims:

| State | Evidence required |
|---|---|
| `implemented` | Native provider and application integration exist. |
| `mock_verified` | Fixture/mock contract and application checks pass without a paid provider call. |
| `live_contract_verified` | Real OpenAI calls pass the selected contract/Golden gates. |
| `live_qualified` | Real key, application E2E boundary, persisted model runs, all three Golden cases, and verified workspace/database/object-storage cleanup all pass. |
| `seller_validated` | Human seller review has been recorded separately. |

`configured`, `not_yet_qualified`, or a successful smoke call is not
`live_qualified`.

## Provider Routing

Routing is explicit; business services must not infer a provider from a URL:

| Configuration | Route and behavior |
|---|---|
| `AI_MODE=fixture` | Deterministic fixture path; no provider call and no key required. |
| `AI_MODE=mock` | Local OpenAI-compatible path; use `AI_PROVIDER=openai_compatible`. |
| `AI_MODE=live`, `AI_PROVIDER=openai` | Official OpenAI Python SDK, Responses API, and Audio Transcriptions API. |
| `AI_MODE=live`, `AI_PROVIDER=openai_compatible` | Legacy compatible HTTP adapter using `/chat/completions` and `/audio/transcriptions`. This is not native OpenAI qualification. |

Native structured execution rejects any configuration other than
`AI_MODE=live` plus `AI_PROVIDER=openai`. A live provider error does not switch
core artifact generation to fixture or mock output. Preflight presentation is a
special case: if an OpenAI seller summary or creator message fails, the
presentation service persists a failed model run and returns an explicitly
labelled `deterministic_fallback`; this is not a silent provider success.

The native provider uses:

- Responses API parsing against the exact Pydantic output contract;
- `system`, `developer`, and `user` roles as separate input items;
- `store=false` by default;
- base64 data URLs for sampled frames;
- Audio Transcriptions with `whisper-1`, `verbose_json`, and timestamp segments
  by default;
- at most one schema/domain repair attempt;
- safe error mapping and provider request IDs;
- SDK timeout and retry configuration.

## Environment Setup

From the repository root:

```bash
cp .env.openai.example apps/backend/.env
```

Fill only `OPENAI_API_KEY` for the OpenAI settings. The infrastructure values in
the template are local defaults, not production credentials. Do not commit
`apps/backend/.env`, put the key in frontend variables, run with `set -x`, or
print the environment during diagnosis. Production should inject the key from a
secret manager.

The repository reference template is
[`.env.openai.example`](../../.env.openai.example). Settings load `.env` relative
to the backend process working directory; Docker Compose also reads
`apps/backend/.env`.

### Native OpenAI Defaults

| Variable | Current default | Current behavior |
|---|---:|---|
| `AI_MODE` | `fixture` in code | The OpenAI template sets `live`. |
| `AI_PROVIDER` | `openai_compatible` in code | The OpenAI template sets `openai`. |
| `OPENAI_API_KEY` | none | Required only for `AI_MODE=live` plus `AI_PROVIDER=openai`; stored as `SecretStr`. |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | Must be absolute and cannot contain credentials; staging/production live OpenAI requires HTTPS. |
| `OPENAI_TEXT_MODEL` | `gpt-5` | Family fallback for non-vision operations. Availability is account-specific; override when needed. |
| `OPENAI_VISION_MODEL` | `gpt-5` | Family fallback for media observation. |
| `OPENAI_TRANSCRIPTION_MODEL` | `whisper-1` | Native timed ASR model. |
| `OPENAI_REASONING_EFFORT` | `medium` | Fallback only. Current registered prompts set their own operation defaults. |
| `OPENAI_STORE_RESPONSES` | `false` | Sent to Responses API. Qualification fails when enabled. |
| `OPENAI_MAX_OUTPUT_TOKENS` | `16000` | Fallback only. Current registered prompts use operation limits from 2,000 to 10,000. |
| `OPENAI_REQUEST_TIMEOUT_SECONDS` | `180` | Used by native Responses and transcription requests. |
| `OPENAI_MAX_RETRIES` | `2` | Passed to the official SDK; allowed range is 0-10. |
| `OPENAI_IMAGE_DETAIL` | `auto` | Applied to sampled frame inputs. |
| `OPENAI_IMAGE_TRANSPORT` | `base64` | The current schema accepts only `base64`; signed URL mode is not implemented. |
| `OPENAI_TRANSCRIPTION_RESPONSE_FORMAT` | `verbose_json` | Declared in settings, but native media analysis currently hard-codes `verbose_json`. |
| `OPENAI_TRANSCRIPTION_TIMESTAMP_GRANULARITIES` | `segment` | CSV input; `segment,word` is accepted. |
| `OPENAI_MAX_FRAMES_PER_VIDEO` | `12` | Limits native media-observation frame inputs. |
| `OPENAI_MAX_FRAME_LONG_EDGE` | `1280` | Declared but not currently wired to a resize step. |
| `OPENAI_MAX_TRANSCRIPT_CHARS` | `50000` | Bounds transcript text included in media observation. |
| `OPENAI_MAX_PARALLEL_REQUESTS_PER_WORKSPACE` | `2` | Declared but no workspace semaphore currently enforces it. |

Do not describe a declared but unenforced setting as a production control.
Storyboard image and concept video generation are separate provider paths,
disabled by default, and are not part of native OpenAI qualification.

### Operation Model Overrides

Resolution order is operation override, then family model, then the code default
for that family:

| Operation | Override | Family fallback |
|---|---|---|
| `media_observation` | `OPENAI_MODEL_MEDIA_OBSERVATION` | `OPENAI_VISION_MODEL` |
| `creative_dna_build` | `OPENAI_MODEL_CREATIVE_DNA` | `OPENAI_TEXT_MODEL` |
| `pattern_kit_extract` | `OPENAI_MODEL_PATTERN_KIT` | `OPENAI_TEXT_MODEL` |
| `viral_kit_compose` | `OPENAI_MODEL_VIRAL_KIT` | `OPENAI_TEXT_MODEL` |
| `adaptation_generate` | `OPENAI_MODEL_ADAPTATION` | `OPENAI_TEXT_MODEL` |
| `campaign_pack_generate` | `OPENAI_MODEL_CAMPAIGN_PACK` | `OPENAI_TEXT_MODEL` |
| `seller_decision_summary` | `OPENAI_MODEL_DECISION_SUMMARY` | `OPENAI_TEXT_MODEL` |
| `revision_message_generate` | `OPENAI_MODEL_REVISION_MESSAGE` | `OPENAI_TEXT_MODEL` |
| audio transcription | none | `OPENAI_TRANSCRIPTION_MODEL` |

Blank operation overrides normalize to `None`. When OpenAI rejects a model, the
safe `OPENAI_MODEL_NOT_AVAILABLE` error names the operation and the applicable
override/family variable. Never assume the documented default is available to
every OpenAI project.

## Start The Application

Install dependencies once:

```bash
make backend-install
make web-install
```

Start local infrastructure and migrate:

```bash
make infra-up
make migrate
```

Run each long-lived process in a separate terminal:

```bash
make api
make worker
make beat
```

The worker must consume both `default` and `maintenance`; Beat schedules stale
job recovery and pending object-deletion retries every five minutes.

Check only safe readiness data:

```bash
curl -fsS http://localhost:8000/health/dependencies
curl -fsS http://localhost:8000/api/v1/system/ai-readiness
```

These endpoints do not call OpenAI and do not prove qualification.
`/api/v1/system/ai-readiness` currently has no durable qualification-state
lookup, so a configured live process reports `not_yet_qualified` even after a
separate report has passed.

For the browser workflow, configure `apps/web/.env.local`:

```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_LOCAL_AUTH_TOKEN=local-test
```

Then run:

```bash
make web-dev
```

Vite currently listens on `http://localhost:8080`; set
`BACKEND_CORS_ORIGINS=http://localhost:8080` for that local UI. The repository
OpenAI template still uses port 5173. The frontend token fallback is local-test
only; production must use OIDC and must not ship an OpenAI key to the browser.

## Fixture And Mock Modes

Fixture mode needs no model provider:

```env
AI_MODE=fixture
AI_PROVIDER=openai_compatible
ASR_PROVIDER=fixture
```

After restarting API and workers:

```bash
make smoke-release-fixture
```

For mock mode, start the local compatible provider from `apps/backend`:

```bash
uv run python scripts/mock_openai_provider.py
```

Configure the application:

```env
AI_MODE=mock
AI_PROVIDER=openai_compatible
AI_BASE_URL=http://127.0.0.1:8787/v1
AI_API_KEY=mock-local
AI_TEXT_MODEL=mock-text
AI_VISION_MODEL=mock-vision
ASR_PROVIDER=openai_compatible
ASR_BASE_URL=http://127.0.0.1:8787/v1
ASR_API_KEY=mock-local
ASR_MODEL=mock-asr
```

Restart API and workers, then run:

```bash
make smoke-release-mock
```

Supported mock failure switches are `malformed_json`, `missing_field`,
`timeout`, `429`, and `500` through `MOCK_AI_FAILURE`. Mock success validates
Viraldy contracts and application wiring, not OpenAI behavior or quality.

The older [AI Provider Readiness](AI_PROVIDER_READINESS.md) runbook applies to
the compatible adapter. Its `check_ai_readiness.py` health probe uses
`AI_BASE_URL`; use `qualify_openai.py --check-config` for native OpenAI.

## Model-Run Provenance

Application services persist live runs in `ai_model_runs`. Inspect through the
workspace-scoped API, which requires `data.export`:

```bash
curl -fsS \
  -H "Authorization: Bearer ${SMOKE_AUTH_TOKEN:-local-test}" \
  "http://localhost:8000/api/v1/workspaces/${WORKSPACE_ID}/model-runs?status=completed&limit=500" \
  | jq '.data[] | {
      id, operation, analysis_mode, provider, endpoint_family, model,
      prompt_name, prompt_version, schema_version,
      request_id, provider_request_id, status,
      attempt_count, repair_attempt_count, latency_ms, usage_json
    }'
```

For a live application result, verify `analysis_mode=live`, `provider=openai`,
the expected operation/model/prompt/schema, a nonempty provider request ID, and
completed usage/latency fields. Failed runs retain safe error metadata.
Input/output summaries are deliberately bounded and must not contain binary
frames, API keys, full signed URLs, or complete raw model responses.

## Data Flow And Privacy

The native media path is:

```text
seller upload
-> Viraldy private object storage
-> derived audio, sampled frames, transcript/OCR/scenes
-> OpenAI transcription and/or Responses request
-> strict typed response
-> Viraldy artifact and model-run persistence
```

Operational rules:

1. Keep `OPENAI_STORE_RESPONSES=false`.
2. Use only seller-owned or explicitly authorized qualification media.
3. Do not log prompts, raw responses, base64 frames, signed URLs, seller PII, or
   full product payloads.
4. Workspace membership and operation permissions must be checked before the
   request. UUID knowledge is not authorization.
5. Analysis permission and AI derivative-generation permission are separate.
6. Review OpenAI retention, regional processing, and enterprise data controls
   before unsupervised production use. Local deletion does not represent a
   third-party deletion request.

Current gap: the asset model and upload schema expose generic `metadata_json`
but no typed, enforced `analysis_authorization` field. The HTTP routes enforce
workspace `analysis.run`, but the code does not yet prove per-asset consent
metadata before a native request. Until that boundary is implemented and
tested, do not send private customer media in unsupervised production. Use
controlled seller-owned test media for supervised qualification.

## Retention And Deletion

Defaults are `ASSET_RETENTION_DAYS=14` and
`MODEL_OUTPUT_RETENTION_DAYS=90`.

- Workspace/resource hard deletion removes dependent artifacts, model runs,
  jobs, feedback, events, recommendations, and storage objects.
- Deletion commits business-row removal and a durable storage-deletion batch
  before deleting objects.
- A failed object cleanup remains `storage_cleanup_pending` and is retried by
  the maintenance worker.
- Retention redacts old model-run input/output summaries and errors rather than
  deleting the provenance row.
- Minimal deletion audit records intentionally survive workspace deletion.
- Shared `fixtures/` objects are not tenant-owned and are not deleted with a
  workspace.

Use the application-boundary smoke with `--isolated-lifecycle --verify-db` to
verify workspace rows, deletion audit, storage batch, and object prefix cleanup.
See [Object Storage](OBJECT_STORAGE.md) for retry and retention details.

## Common Failures

| Safe error/state | Action |
|---|---|
| Startup says `OPENAI_API_KEY` is required | Set the secret only when `AI_MODE=live` and `AI_PROVIDER=openai`; restart API and workers. |
| `OPENAI_UNAUTHORIZED` | Verify secret/project access without printing the key. |
| `OPENAI_MODEL_NOT_AVAILABLE` | Change the named operation override or family model and rerun one operation. |
| `OPENAI_RATE_LIMITED` | Reduce workload/concurrency operationally and retry after the provider window. The declared workspace parallel limit is not yet enforced. |
| `OPENAI_TIMEOUT` | Review media size and operation latency, then adjust the explicit timeout cautiously. |
| `OPENAI_REFUSED` | Treat as a failed model run; do not parse refusal text as output. |
| `OPENAI_INCOMPLETE` | Check model output limits and provider status; do not persist partial output as success. |
| `OPENAI_OUTPUT_INVALID` | The request/response failed strict parsing after at most one repair. Review schema/model compatibility. |
| `OPENAI_DOMAIN_VALIDATION_FAILED` | Evidence, prompt/schema version, or domain invariants failed; fix the boundary rather than weakening validation. |
| Health is `not_yet_qualified` after a report | Expected with the current non-durable health lookup; use the report plus application evidence, not health alone. |

## Dola/Seed Migration Boundary

Do not fork the canonical prompts for Dola/Seed and do not point
`AI_PROVIDER=openai` at a non-OpenAI URL. The reusable boundary is the frozen
`PromptPackage`, stable `ViraldyOperationContextV1`, Pydantic output contracts,
evidence validators, model-run schema, and provider protocol.

A later Dola/Seed integration must:

1. implement and register an explicit provider route/capability adapter;
2. map text, vision, ASR, image, and video models independently;
3. translate provider request/response details without changing domain prompts;
4. preserve prompt/schema/evidence provenance and safe errors;
5. add provider-specific contract tests and application E2E qualification;
6. remain labelled unqualified until real provider calls, persisted runs, and
   cleanup pass.

The current `openai_compatible` adapter is useful for mock and compatibility
testing, but it is not evidence that unverified BytePlus, Dola, Seedream, or
Seedance behavior works.
