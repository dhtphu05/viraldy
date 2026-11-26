# Smart Remake P0 — prepared pilot

## Current application flow — 2026-11-26

This file retains the historical prepared-pilot record below. Its financial authorization forms, mandatory server stage bounds and compiler versions describe that earlier bounded pilot, not requirements for the current app. Use [Local Development](LOCAL_DEVELOPMENT.md#optional-ai-and-render-providers) for current runtime setup and [the current UX recommendations](../product/smart-remake-ux-recommendations.md) for seller behavior. Existing filenames, persisted identifiers and old receipts are retained for compatibility.

The current compiler is `smart-remake-timeline-v2.3`. New app analysis uses the entire uploaded source video, keeps each analyzed logical scene and canonical prompt, and retimes the sequence into an 8/16-second output. Initial KIE generation uses fixed eight-second windows: **8 seconds = one `createTask`; 16 seconds = two**. A logical scene may have two execution fragments across the output eight-second boundary without becoming two source scenes. Source action, beat, opening-frame and transition bindings remain authoritative. Update an old plan before fresh initial generation; already-submitted or uncertain tasks only reconcile their original requests.

New intake defaults to `{"mode":"unlimited"}`. The current app removes seller USD caps, attempt grants and execution-time grants, including before analysis. Missing server price bounds do not block this flow. Legacy finite API policies remain supported, and the app explicitly upgrades an old policy before a new AI action. Ledger accounting, idempotency, rights/processing confirmation when needed, technical checks, QA and checked export remain. Unknown costs and estimates remain unknown, never an assumed zero. New worker windows are finite and derived from frozen server workload metadata; legacy jobs without that metadata retain the old 7,200-second window.

Prompt limits follow the provider contract. The [KIE Veo 3.1 schema](https://docs.kie.ai/veo3-api/generate-veo-3-video) inspected on 26 November 2026 publishes no prompt `maxLength`; the application no longer imposes an arbitrary 20,000-character KIE cap. Actual provider errors are surfaced without truncating scenes or creating extra paid video calls. Verification for this revision uses offline fixtures, including real HTTP/storage/worker/FFmpeg paths with injected providers; it does not establish paid generation quality or provider entitlement. No new paid run is authorized by this document.

## Historical prepared pilot — 2026-11-25

The sections below preserve the earlier bounded-pilot instructions and evidence. Their caps, server-price requirements, checker status and test totals must not be read as the current unlimited app's readiness gate.

The authorized task is **prepare a pilot using self-authored media; do not make paid provider calls**. Chat A's `READY_FOR_LIVE_PILOT` status is qualified as **prepared / offline; paid execution blocked**: integrated backend checks pass and an owned development package is available. Financial configuration may remain blank. Whole-P0 readiness also requires Chat B's qualification. `LIVE_VERIFIED` requires a separately authorized paid run, retained provider receipts and human assessment; offline tests do not establish model quality or account entitlement.

## Canonical generation and QA bindings — 2026-11-25

New generation requires `GenerationExpectations` v1 with its retained SHA-256 hash. OpenAI, KIE and Inspector consume canonical product facts, seller requirements and scene intent from that snapshot. Original analysis remains available only for traceability. Opening references use the verified original source, absolute24fps frame, native dimensions, layout hash and extractor version; midpoint UI thumbnails cannot satisfy this binding.

The compiler is `smart-remake-timeline-v2.1`, conditioning contract is `conditioning-p0-v2` and checker is `smart-remake-inspection-p0-v1.2` with `smart-remake-p0-rubric-v2`. An old plan must use **Cập nhật kịch bản** before new generation/repair. Incomplete source semantics return `SMART_REMAKE_SOURCE_ANALYSIS_INCOMPLETE`; unsupported source or unobserved product identity require better inputs/analysis, never a mandatory manual prompt. At most one supplemental cut analysis uses the existing ledger and project caps.

When requirements, product facts, references, opening frames or selected ranges change, recompile or compose a new preview as directed by the UI. Existing assemblies retain their old facts; stale assemblies cannot queue unusable paid QA. Old assembly QA may derive a snapshot without calling a model only from complete historical context with known unchanged requirements. Otherwise `SMART_REMAKE_ASSEMBLY_EXPECTATIONS_REQUIRED` requires preparation/compose again. Submitted or uncertain old image/video intents must reconcile their existing request; an upgrade does not authorize a replacement submission.

Conditioning opening PASS requires output, product and exact source-opening evidence. Video checks retain stable per-scene opening/presentation/action IDs and scene windows. Free-text keep/replace/forbid remains `needs_review` when only sampled frames were observed. Seller may accept semantic findings with a reason; technical validity and rights remain hard gates.

Offline regression evidence and browser captures live in `artifacts/smart-remake-p0/expectations-upgrade-20261125/`. Backend qualification: 975 tests, 92.07% aggregate coverage in the changed scope. See `final-backend.command.json` and `final-backend.summary.json`; strict mypy passes all 32 scoped source files. Full Ruff retains 140 findings on exact pre-existing lines (E501/S603); there are no findings on new or changed lines. Frontend validation passes 355 tests, typecheck, scoped ESLint and build.

## Offline configuration inventory

From the repository root:

```sh
cd apps/backend
uv run --env-file .env python ../../scripts/check-smart-remake-readiness.py --json
```

The checker reads configuration and local source profiles. It makes no HTTP, database, Redis, storage or provider request, executes no media binary and prints only fixed status/code/config names. It never prints credentials, database URLs, input paths or signed URLs. It does not load `.env` itself; `uv --env-file` supplies the selected environment.

Exit `0` means configuration inventory passed; `1` means missing/invalid configuration; `2` means invalid command arguments. `runtimeVerification: not_performed` and `pilotAuthorization: not_verified` always remain explicit. With the current offline-only preparation, `AI_MODE=fixture` and missing server cost bounds correctly produce `configuration_blocked` / `paidExecution: blocked`. That result does not prevent preparing or testing the offline package.

Before any separately authorized paid run, an operator must configure:

| Area | Configuration |
| --- | --- |
| Mode and feature | `AI_MODE=live`, `SMART_REMAKE_ENABLED=true` |
| Analysis and inspection | `GEMINI_API_KEY`; current `SMART_REMAKE_GEMINI_MODEL=gemini-2.5-flash` |
| Image | `OPENAI_API_KEY`; current code profile `gpt-image-2.6-sunburst`, `720x1280`, PNG, one image, quality `max`, complexity `high`; `SMART_REMAKE_OPENAI_IMAGE_QUALITY=max` |
| Video | `KIE_API_KEY`; current code route `veo-3-1` with input model `veo3_lite`, raw eight-second clips |
| Server exposure bounds | `SMART_REMAKE_P0_MAX_ANALYSIS_USD`, `SMART_REMAKE_P0_MAX_IMAGE_USD`, `SMART_REMAKE_P0_MAX_VIDEO_USD`, `SMART_REMAKE_P0_MAX_INSPECTION_USD` |
| Data and jobs | `DATABASE_URL` using PostgreSQL/asyncpg, `DATABASE_SYNC_URL` using PostgreSQL/psycopg, `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` |
| Private media | `S3_BUCKET`, `S3_REGION`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`; optional `S3_ENDPOINT_URL`; FFmpeg and FFprobe available through configured paths or PATH |

Each server bound is a reviewed **maximum possible USD exposure for one physical call**, not an invented list price or expected average. Values must be finite, positive, exact USD decimals with at most eight fractional digits. Token/credit counts alone do not establish an actual USD bill. Configure the same environment on API and workers. The checker confirms presence/source settings only: separately verify database migration `0024`, job delivery, private storage access, decodable media and provider account/model access before a live run. Source profile checks do not certify vendor availability.

## Generate and replay self-authored development cases

These commands use the local harness and FFmpeg/Pillow. They do not call a provider. Run from `apps/backend`; choose a fresh directory outside Git:

```sh
viraldy_p0_pilot_dir=$(mktemp -d /tmp/viraldy-p0-prepared.XXXXXX)
AI_MODE=fixture uv run python scripts/evaluate_smart_remake.py dev-corpus --output-dir "$viraldy_p0_pilot_dir"
AI_MODE=fixture uv run python scripts/evaluate_smart_remake.py validate "$viraldy_p0_pilot_dir/bundle.json"
AI_MODE=fixture uv run python scripts/evaluate_smart_remake.py replay "$viraldy_p0_pilot_dir/bundle.json" --output-dir "$viraldy_p0_pilot_dir/report"
uv run --env-file .env python ../../scripts/check-smart-remake-readiness.py --json --pilot-case "$viraldy_p0_pilot_dir/bundle.json"
```

The corpus contains original illustrated product/character assets, generated static video and synthetic audio, with hashes and authorship provenance. Its illustrated character represents no real person. Preserve the pass, needs-repair and deliberately rights-blocked cases as distinct cases; the blocked case is a policy test, not an asset approved for submission. Readability of a case JSON is not verification of its rights. Fixtures remain `fixture`; do not relabel them `live` to pass a harness gate. The official B0/B1/B2 and ablation protocol is pending and must not be invented; no batch84 is authorized.

The prepared, replay-validated development package is retained outside version control at `/Users/mac/Desktop/Viraldy/artifacts/smart-remake-p0/chat-a-prepared-20261125/bundle.json`, with its report in the adjacent `report/` directory. Its synthetic expectations and zero fixture costs are not live measurements; provider-use authorization remains false. B's separate input-only pilot package and capture instructions are documented in `evaluation/smart_remake/PILOT_RUNBOOK.md`.

Run scoped backend checks from `apps/backend` against isolated test services:

```sh
COVERAGE_FILE=/tmp/viraldy-p0-pilot-checks.coverage uv run pytest -o addopts='' tests/unit/test_smart_remake_budget_policy.py tests/unit/test_smart_remake_lifecycle_analysis.py tests/unit/test_smart_remake_lifecycle_worker.py tests/unit/test_smart_remake_readiness.py tests/integration/test_smart_remake_budget_ledger.py tests/integration/test_smart_remake_lifecycle_analysis_runtime.py
```

PostgreSQL integration tests create their own Testcontainers instances. They use mocked HTTP while preserving real reservation, tenancy and persistence logic. They also pause after reservation and submission-intent writes, revoke rights from another PostgreSQL session, and verify zero HTTP calls and a known-zero failed attempt. Use Chat B's actual browser/API/worker/FFmpeg qualification and evidence report for the full seller journey; this scoped command does not replace browser qualification. Do not migrate or clear a seller database for test isolation.

## KIE skills and local credentials

The project includes the official `kie-models` and `kie-chat-agents` skills under `.agents/skills/`, installed for Codex from `https://kie.ai`. `skills-lock.json` records the source digests. Install/update them with:

```sh
npx --yes skills@1.9.0 add https://kie.ai --agent codex --skill kie-models kie-chat-agents --yes --copy
```

The private KIE key lives in Git-ignored `apps/backend/.env`, with file mode0600. `make api`, `make worker`, `make beat` and Docker Compose already load that file. Existing processes need a restart; Compose containers need recreation to pick up changed environment. A newly installed skill is available to Codex on the next turn/chat. Installing `kie-chat-agents` does not switch this project's or Codex's model provider.

The standalone vendor CLI reads process environment, so use the existing dotenv loader when invoking it. From `apps/backend`, this command checks the account balance without creating generation tasks:

```sh
uv run --env-file .env node ../../.agents/skills/kie-models/scripts/kie-cli.mjs balance --json
```

For Smart Remake generation, use the application's owned intake and budget ledger. The standalone vendor CLI's `run` command is not a replacement for those gates. Configuring a key or installing a skill does not authorize paid submission. The current key was authenticated through the read-only credit endpoint; this does not establish model entitlement or generation quality.

## Inputs and gates before a paid run

The application must create an owned intake before analysis. Record source/product rights, processing scope, evidence notes and disclosure acknowledgement. A real-person reference additionally requires an uploaded character asset, its rights and applicable consent with evidence/scope; a name in the prompt or a synthetic fixture does not provide consent for another person. Never infer legal clearance from a checked box, a file name or the readiness script.

The user must separately supply/approve the specific submitted case and a project cap (`capUsd`), attempt limit (`maxAttempts`) and execution window (`maxDurationSeconds`). Server stage bounds remain operator-controlled. No default project cap or current provider price is supplied by this runbook. Optional checker flags `--cap-usd` and `--authorized` record declarations only; they do not grant authorization, verify rights or execute work.

Use the normal authenticated workspace application flow when a paid run is later authorized: intake → compile → generate → select/trim → private `/publish` compose preview → inspect → review findings → approve the bound assembly/report → checked export. Mutations carry the current revision and an idempotency key. Keep content approval separate from “use this range.” Exports must pass the backend rights/report/version gates and contain the burned `AI-generated` label; a preview URL is not checked export approval. Changed media, trim, constraints or relevant neighbor versions require fresh checks and approval.

## Uncertain receipts and recovery

Every physical analysis/image/video/inspection call reserves exposure before submission. A timeout, network interruption, invalid JSON, lost result cache or missing money receipt does not refund the reservation. Known usage with unknown billing remains `actualUsd: null`; show the held amount and reconciliation state. A local preflight rejection before HTTP is a known-zero failure, including rights revoked during budget preflight.

Do not create a new key/operation to retry the same uncertain intent. The ledger blocks unresolved identical request hashes across operations. If a known KIE task ID was retained, resume polling that task rather than creating another task. Keep original task/request IDs, timestamps, usage, hashes, errors and every failed attempt. Repeated receipt settlement is idempotent; conflicting known billed amounts require investigation. Only a trusted provider billing receipt may settle actual USD; credits, elapsed time, assumed free errors and absent receipts are not a monetary receipt.

There is no generic “force retry” or arbitrary client-supplied cost correction in this runbook. Reconcile retained task/request and billing evidence through the supported service path; if provider billing cannot be established, leave the reservation held. Preserve good scene hashes, immutable assemblies and the previous output while resolving failures. Retain sanitized versioned provenance with local evidence artifacts, not signed URLs or provider credentials.

Public provenance separates configured `run.serverMode` from observed execution. A physical client can record a witness only for its owned transport with negotiated, verified TLS to the fixed provider endpoint. The ledger binds that witness to the exact attempt, provider, model and request hash; a witness cannot attest a second intent. `run.mode=live` additionally requires complete physical-attempt evidence and analysis bound to the current compile operation. Injected clients/transports, missing TLS evidence, arbitrary JSON mode fields and mixed/missing proof remain unverified. Missing evidence must not be repaired by relabeling JSON. A physical-response witness proves the observed transport path, not the monetary bill or output quality: unknown costs remain null. The offline launcher records its provider injection explicitly as fixture/mock evidence when joining the case manifest.

## Stop use and deletion

Use the project's deletion operation to stop further use immediately, then inspect its recorded dependency and deletion results. Shared raw clips/cache objects, active jobs and retained inspection evidence can defer physical deletion. Do not delete a shared object by guessing its key. The backend stops issuing new preview/export links; previously issued signed links can remain usable until expiry or object deletion. Files already downloaded by an authorized person cannot be recalled.

Report what Viraldy deleted and what remains deferred/retained. Provider-side copies, logs or retention follow provider capabilities and policies; a local deletion record does not prove provider-side deletion. Revoke rights/consent or stop use as appropriate, preserve required audit evidence, and verify status before calling the request complete.

Deletion verifies the registered media inventory. An abrupt process/host termination between an object upload and its database inventory write can leave an unregistered object; this P0 does not claim a bucket-wide orphan scan. Normal caught upload failures retain uploaded keys for cleanup.
