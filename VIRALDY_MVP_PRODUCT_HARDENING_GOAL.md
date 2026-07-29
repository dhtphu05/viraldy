# VIRALDY MVP PRODUCT HARDENING GOAL
## Codex Goal-Mode Execution Contract — Keyless Product Hardening

> **Repository:** local Viraldy source containing the completed fixture-mode MVP  
> **Audit source:** `VIRALDY_MVP_AUDIT.md`  
> **Primary objective:** harden data integrity, workflows, jobs, media processing, AI provider contracts, scoring, and frontend so all MVP features work end to end without model credentials and real models require environment configuration only  
> **Out of scope:** cloud deployment, Kubernetes, autoscaling, billing, non-MVP features, and broad production optimization

---

# 0. EXECUTION DIRECTIVE

Read the current repository and `VIRALDY_MVP_AUDIT.md` before changing code.

The existing MVP already supports:

```text
Quick TikTok Scorer
```

and:

```text
Product
→ Reference Board
→ Creative DNA
→ Product Adaptation
→ Campaign Pack
→ UGC Preflight
```

Do not rebuild these features from zero. Do not run another architecture refactor. Do not stop after planning, migrations, interfaces, or placeholders.

The hardened system must satisfy:

1. Fixture mode remains deterministic.
2. Mock-provider mode exercises the same HTTP/provider path as live mode without a paid key.
3. Live mode uses the same contracts and requires environment configuration only.
4. Every output is workspace-scoped, persisted, versioned, traceable, and linked to its exact inputs.
5. Jobs are idempotent, retry-safe, recoverable, and stage-aware.
6. Scores are deterministic and evidence-backed; LLMs never own final numeric scores.
7. Frontend core MVP routes use backend state, survive refresh, and expose progress/errors/mode.
8. Failures never silently fall back from live to fixture.
9. The final report states what was contract-verified and what still awaits real credentials.

---

# 1. CURRENT BASELINE TO CONFIRM

Expected runtime modules:

```text
identity
workspaces
products
assets
jobs
recommendations
reference_boards
references
media_analysis
creative_dna
tiktok_scorer
adaptations
campaign_packs
preflight
```

Expected tables:

```text
users
workspaces
workspace_members
products
assets
asset_versions
processing_jobs
recommendations
recommendation_actions
reference_boards
references
media_artifacts
evidence_items
creative_dna_versions
tiktok_score_runs
adaptation_runs
campaign_packs
campaign_pack_versions
preflight_runs
```

Expected job types:

```text
process_asset
analyze_reference
score_tiktok_asset
run_ugc_preflight
```

Expected status:

- Fixture-mode MVP completed.
- Unknown fixture files rejected.
- Live OpenAI-compatible paths wired but untested with credentials.
- Quick scorer deterministic.
- Adaptation returns three concepts.
- Campaign Pack structured and versioned.
- Preflight creates recommendation.
- `/mvp` exists.
- Many MVP files may still be untracked locally.

## Source-control safety

Before hardening:

- Record current branch, commit, and `git status`.
- Preserve all untracked MVP modules.
- Create a checkpoint commit or hardening branch when possible.
- Do not reset to public GitHub `main` if it does not contain the local MVP.
- Add baseline details to the Execution Log.

---

# 2. THREE ANALYSIS MODES

## 2.1 Fixture

- Known fixtures only.
- `analysis_mode = fixture` on every analytical record.
- Visible frontend badge.
- Unknown fixture → `UNSUPPORTED_FIXTURE_ASSET`.
- Same Pydantic contracts, scorer, rules, persistence, and recommendations as other modes.
- No frontend-only fake results.

## 2.2 Mock provider

Purpose: exercise the real HTTP client and provider adapter without a vendor key.

- Local OpenAI-compatible server.
- Same live adapter, request construction, auth header, timeout, retry, multipart ASR, multimodal payload, structured parsing, and error mapping.
- `analysis_mode = mock`.
- Visible frontend badge.
- Failure switches: malformed JSON, timeout, 429, 500, missing field.
- Feature services must not import mock result objects directly.

## 2.3 Live

- Missing settings fail clearly.
- No silent fallback.
- Provider readiness endpoint exposes missing capability names, never secrets.
- Same schemas/workflows as mock mode.
- Provider/model/prompt/schema versions persisted.
- Adding credentials/models requires environment changes only.

---

# 3. NON-GOALS

Do not implement:

- Cloud deployment or Kubernetes.
- Autoscaling or multi-region architecture.
- Billing/credits.
- Creator Fit, Sample ROI, full Rights/Spark, Performance CSV, Fatigue.
- PatternKit/ViralKit.
- Competitor crawler or browser extension.
- Shopify/TikTok/Meta integrations.
- Fine-tuning or proprietary performance prediction.
- Full video editor.
- Agent/MCP.
- Microservices.
- Replacing FastAPI/Postgres/Redis/Celery/S3.
- Full UI redesign.
- Coverage expansion for its own sake.

Targeted verification required by this goal is expected.

---

# 4. ARCHITECTURE RULES

Preserve the Lean Modular Monolith.

Typical feature module:

```text
modules/<feature>/
├── models.py
├── schemas.py
├── repository.py
├── service.py
├── router.py
├── public.py
├── rules.py
├── scorer.py
├── prompts.py
├── tasks.py
├── validators.py
└── exceptions.py
```

Keep only files with real responsibilities.

Rules:

- Router → service → repository/integration.
- Worker task is thin and receives stable IDs.
- Every business lookup includes `workspace_id`.
- Cross-module calls use `public.py`.
- Binary media remains in object storage.
- Structured analytical data remains in PostgreSQL.
- Old analytical versions are immutable.
- Existing migrations are never rewritten.
- No generic repository, command bus, event sourcing, Kafka, or deep DDD ceremony.
- No giant global `ai_service.py`.
- Feature prompts live with their feature.
- ASR/OCR/visual evidence is persisted once and reused by DNA/scorer/preflight.

---

# 5. KEY-READY DATA MODEL

Create a new migration after the MVP migration. Do not modify prior revisions.

## 5.1 `processing_job_events`

```text
id UUID PK
workspace_id UUID FK
processing_job_id UUID FK
event_type varchar
status varchar
stage varchar nullable
progress integer nullable
message varchar nullable
details_json JSONB default {}
created_at timestamptz
```

Events:

```text
job_created
dispatch_requested
dispatch_succeeded
dispatch_failed
job_claimed
stage_started
stage_completed
retry_scheduled
job_completed
job_failed
job_cancelled
```

## 5.2 `ai_model_runs`

```text
id UUID PK
workspace_id UUID FK
processing_job_id UUID nullable
subject_type varchar
subject_id UUID
capability varchar
analysis_mode varchar
provider varchar
model varchar
prompt_version varchar nullable
response_schema_version varchar
status varchar
attempt integer
request_hash varchar
input_summary_json JSONB default {}
output_summary_json JSONB default {}
latency_ms integer nullable
http_status integer nullable
provider_request_id varchar nullable
error_code varchar nullable
error_message text nullable
started_at timestamptz
completed_at timestamptz nullable
created_at timestamptz
```

Never store keys, auth headers, presigned URLs, binary/base64 frames, or raw private payloads.

## 5.3 Link analytical records

Add where missing:

```text
processing_job_id
primary_model_run_id nullable
pipeline_version
```

to:

```text
creative_dna_versions
tiktok_score_runs
adaptation_runs
preflight_runs
```

Campaign Pack versions should retain source adaptation/model provenance.

## 5.4 Current-version integrity

Add safe foreign keys where practical:

```text
assets.current_version_id → asset_versions.id
campaign_packs.current_version_id → campaign_pack_versions.id
```

Do not cascade-delete immutable history.

## 5.5 State constraints

Processing jobs:

```text
queued
dispatching
running
retrying
completed
failed
cancelled
```

Analytical runs:

```text
pending
queued
processing
completed
failed
cancelled
```

References:

```text
draft
ready
analyzing
analyzed
failed
archived
```

Campaign Packs:

```text
draft
ready
sent
archived
```

Add DB checks for core states and progress 0–100.

## 5.6 Uniqueness and idempotency

Review/add:

- Unique job idempotency per workspace/job type/key.
- Unique analytical-run idempotency when exposed.
- Unique DNA version per asset version/version number.
- Unique Campaign Pack version number per pack.
- Artifact identity unique per job/stage/type/ordinal.
- Evidence dedupe per job/stage/evidence identity.

Handle concurrent idempotency races by catching `IntegrityError`, rolling back, and returning the existing run/job.

## 5.7 Workspace consistency

Services verify all linked records share the same workspace:

```text
board
reference
product
asset
asset_version
creative_dna
adaptation
campaign_pack
preflight
```


---

# 6. JOB-ORCHESTRATION HARDENING

## 6.1 Typed job registry

Centralize job definitions:

```text
PROCESS_ASSET
ANALYZE_REFERENCE
SCORE_TIKTOK_ASSET
RUN_UGC_PREFLIGHT
```

Each definition declares:

```text
queue
max_attempts
soft_timeout
hard_timeout
required_stages
optional_stages
result_subject_type
```

No scattered magic strings.

## 6.2 Atomic claim

Worker atomically transitions:

```text
queued/retrying → running
```

Only one worker may claim an attempt. If already running/completed/failed/cancelled, return safely without duplicating work.

## 6.3 Retry semantics

Use one source of truth.

Recommended definition:

```text
max_attempts = total executions including the first attempt
```

Align DB attempt count and Celery retry behavior. Never mark failed and then schedule another retry.

## 6.4 Dispatch recovery

Flow:

```text
create job
→ commit
→ persist dispatch request
→ enqueue
→ persist task ID/dispatch success
```

On enqueue failure:

- Persist `dispatch_failed` event.
- Keep the job recoverable.
- Add `scripts/redispatch_jobs.py` or equivalent.
- Do not add Kafka/outbox infrastructure in this goal.

## 6.5 Idempotency races

Two simultaneous requests using the same idempotency key must return the same run/job, not HTTP 500.

Use the DB unique constraint as final authority.

## 6.6 Stage contract

Each stage has:

```text
name
input schema
output schema
required/optional
timeout
idempotency identity
```

Worker orchestration calls stage services. Domain logic does not live in the Celery task.

## 6.7 Resume and reuse

On retry:

- Reuse completed artifacts if input hash, pipeline version, provider/model version match.
- Skip completed idempotent stages.
- Run only missing/failed stages.
- Prevent duplicate artifacts/evidence.

## 6.8 Error taxonomy

Use stable codes:

```text
MEDIA_DOWNLOAD_FAILED
MEDIA_UNREADABLE
FFPROBE_FAILED
FFMPEG_FAILED
ASR_PROVIDER_FAILED
OCR_PROVIDER_FAILED
VISION_PROVIDER_FAILED
MODEL_RESPONSE_INVALID
AI_PROVIDER_RATE_LIMITED
AI_PROVIDER_TIMEOUT
AI_PROVIDER_NOT_CONFIGURED
ARTIFACT_PERSIST_FAILED
EVIDENCE_PERSIST_FAILED
SCORING_FAILED
BRIEF_ALIGNMENT_FAILED
```

Frontend receives safe messages; logs may retain stack traces but never secrets.

## 6.9 Progress

- Progress is monotonic within an attempt.
- Job events preserve attempt/stage history.
- Frontend shows retrying state and current stage.

---

# 7. MEDIA-PIPELINE HARDENING

Define:

```text
MEDIA_PIPELINE_VERSION = media_pipeline_v1
```

Persist it with analytical runs/artifacts.

## 7.1 Isolated processing directory

Use a unique temporary directory per attempt:

```text
viraldy-<job_id>-<attempt>
```

Rules:

- Controlled generated filenames only.
- Clean on success/failure.
- Persist only intended artifacts.
- Never execute user-controlled shell strings.

## 7.2 Source download

- Download once per attempt.
- Verify object exists and is non-empty.
- Verify object key belongs to workspace/asset/version.
- Compare size/checksum when available.
- User request may not provide an arbitrary storage key.

## 7.3 ffprobe validation

Extract:

```text
duration_ms
container
video_codec
audio_codec
width
height
fps
video_stream_count
audio_stream_count
```

Validate:

- Video stream exists.
- Duration > 0 and <= configured MVP maximum.
- Container is supported.
- Dimensions and FPS are sensible.
- Detected format is stored separately from declared MIME.

## 7.4 Safe subprocess helper

One helper must provide:

- Argument arrays.
- No `shell=True`.
- Timeout.
- Captured/truncated stderr.
- Stable error mapping.
- Safe logging.

## 7.5 Deterministic frame sampling

Use:

- Dense opening frames in first 3 seconds.
- Regular interval frames.
- Scene-boundary frames.
- Maximum frame count.
- Timestamp on each frame.
- Duplicate timestamp removal.

Same input + pipeline version → same sampling plan.

## 7.6 ASR normalization

Contract:

```json
{
  "language": "en",
  "segments": [
    {"start_ms": 0, "end_ms": 2100, "text": "..."}
  ],
  "full_text": "..."
}
```

Validate monotonic timestamps inside video duration. No speech is a valid degraded case.

## 7.7 OCR normalization

- Trim/normalize whitespace.
- Remove empty segments.
- Merge repeated adjacent overlays.
- Preserve start/end timestamps, confidence, and frame references.
- Do not create duplicate evidence for the same persistent overlay.

## 7.8 Scene normalization

- Ordered indexes starting at zero.
- No negative durations.
- End does not exceed video duration.
- Merge tiny adjacent scenes with a documented threshold when useful.

## 7.9 Visual observations

Visual provider returns observations, never final scores.

Validate:

- Enum values.
- Timestamps.
- Frame references.
- Product-first appearance.
- Claim candidate structure.
- Unknown rather than unsupported certainty.

## 7.10 Required/optional stages

Required:

```text
source download
ffprobe
frame sampling
artifact manifest
visual observations for live scoring/DNA
```

Optional with degraded confidence:

```text
ASR when no speech/audio
OCR when no text
scene detection when no cuts
```

If live visual analysis is unavailable, fail the analytical job. Do not substitute transcript for visual proof.

## 7.11 Artifact manifest

Persist:

```json
{
  "pipeline_version": "media_pipeline_v1",
  "asset_version_id": "...",
  "input_checksum": "...",
  "artifacts": [
    {
      "type": "thumbnail",
      "storage_key": "...",
      "sha256": "...",
      "stage": "creating_thumbnail"
    }
  ]
}
```

---

# 8. AI PROVIDER GATEWAY

## 8.1 Capability-specific interface

Expose typed methods:

```python
transcribe_audio(...)
extract_visual_observations(...)
build_creative_dna(...)
generate_adaptation(...)
generate_campaign_pack(...)
write_revision_message(...)
```

Every method returns a Pydantic model.

## 8.2 Capability model

Represent:

```text
audio_transcription
text_chat
vision_chat
json_schema
image_url
base64_image
```

Readiness checks required capabilities for configured models.

## 8.3 Environment contract

```text
AI_MODE=fixture|mock|live
AI_PROVIDER=openai_compatible

AI_BASE_URL=
AI_API_KEY=
AI_TEXT_MODEL=
AI_VISION_MODEL=

ASR_PROVIDER=openai_compatible
ASR_BASE_URL=
ASR_API_KEY=
ASR_MODEL=

AI_SUPPORTS_JSON_SCHEMA=true
AI_SUPPORTS_IMAGE_URL=true
AI_REQUEST_TIMEOUT_SECONDS=120
AI_MAX_RETRIES=2
AI_MAX_OUTPUT_TOKENS=
```

Document any fallback from ASR credentials to AI credentials explicitly.

## 8.4 Readiness endpoint and CLI

Add:

```http
GET /api/v1/system/ai-readiness
```

Example:

```json
{
  "mode": "live",
  "provider": "openai_compatible",
  "configured": false,
  "capabilities": {
    "text_chat": true,
    "vision_chat": false,
    "audio_transcription": false,
    "json_schema": true
  },
  "missing": ["AI_API_KEY", "AI_VISION_MODEL", "ASR_MODEL"]
}
```

Add:

```text
python scripts/check_ai_readiness.py
```

Exit codes:

```text
0 configured
1 missing configuration
2 provider contract error
```

No secrets in output.

## 8.5 HTTP client

Use one `httpx` client layer with:

- Pooling.
- Configured timeout.
- Correlation/request ID.
- Retry of safe transient failures only.
- `Retry-After` support.
- Provider request-ID capture.
- Latency tracking.
- Stable mapping for 401/403/429/5xx.

## 8.6 Structured output

Preferred:

```text
JSON schema response format
```

Fallback:

```text
strict JSON instruction → parse one JSON object → Pydantic validation
```

Rules:

- Malformed output → `MODEL_RESPONSE_INVALID`.
- Small repair retry allowed.
- Failed `ai_model_run` persists.
- Feature service never receives unvalidated JSON.

## 8.7 Multimodal input bundle

Send a bounded bundle:

```text
thumbnail
dense opening frames
representative scene frames
frame timestamps
transcript summary
OCR summary
product context
```

Do not send every frame. Persist only hashes/safe summaries of requests.

## 8.8 Prompt registry

Every feature prompt defines:

```text
PROMPT_NAME
PROMPT_VERSION
RESPONSE_SCHEMA_VERSION
```

Initial versions:

```text
creative_dna_extraction_v1
adaptation_generation_v1
campaign_pack_generation_v1
revision_message_v1
```

Prompt rules:

- Use only supplied evidence.
- Return unknown when insufficient.
- Do not output final scores.
- Do not claim viral/GMV performance.
- Do not infer rights.
- Respect media duration and evidence IDs.
- Follow schema exactly.

## 8.9 Mock OpenAI-compatible provider

Add a local server with:

```text
POST /v1/chat/completions
POST /v1/audio/transcriptions
GET /health
```

It must:

- Return valid deterministic DNA/adaptation/pack/revision/ASR responses.
- Inspect request shape.
- Support multimodal messages.
- Support multipart transcription.
- Simulate invalid JSON, timeout, 429, 500, missing fields.
- Be called over HTTP by the live adapter.

## 8.10 Model-run lifecycle

```text
create ai_model_run
→ call provider
→ validate
→ mark completed/failed
→ link feature result
```

Persist capability/provider/model/prompt/schema/latency/status/safe error.

---

# 9. EVIDENCE AND CREATIVE DNA

## 9.1 Ownership

- `media_analysis` owns normalized raw evidence.
- `creative_dna`, `tiktok_scorer`, and `preflight` reference evidence IDs.
- Preflight may add brief-alignment evidence.
- Do not copy raw transcript/OCR into every feature table.

## 9.2 Evidence invariants

Every evidence item:

- Matches workspace and asset version.
- Has valid timestamp range when applicable.
- Has confidence in allowed range.
- Has stable type/source/provider/model.
- Is immutable.

## 9.3 Confidence

Calculate from evidence completeness:

```text
metadata
visual observations
opening frames
transcript
OCR
scenes
product context
schema validation
```

Expose low/medium/high. Do not use only an LLM confidence value.

## 9.4 DNA versioning

Create a new version when pipeline/model/prompt/taxonomy changes or user requests reanalysis. Never overwrite `dna_json`.

## 9.5 Taxonomy

- Central, versioned enums.
- `unknown` is valid.
- No uncontrolled free-form labels where enums exist.
- Optional custom tags live separately.

## 9.6 Timeline projection

Expose frontend-ready timeline:

```json
[
  {
    "start_ms": 0,
    "end_ms": 2100,
    "type": "hook_signal",
    "label": "problem-first opening",
    "source": "vision",
    "confidence": 0.89
  }
]
```


---

# 10. SCORER AND DECISION ENGINE

## 10.1 Rubric registry

Create versioned rubric objects instead of scattered constants.

```python
TikTokStructureRubric(
    version="tiktok_structure_rubric_v1",
    weights={...},
    thresholds={...},
)
```

Persist rubric and rule versions on every score run.

## 10.2 Dimension calculators

Use deterministic calculators:

```text
HookClarityCalculator
ProductVisibilityCalculator
DemoClarityCalculator
ProofStrengthCalculator
CreatorAuthenticityCalculator
OfferClarityCalculator
CtaReadinessCalculator
TikTokNativeFitCalculator
ClaimSafetyCalculator
```

Return:

```text
score
confidence
reason
signals
evidence_ids
```

## 10.3 Missing evidence

Do not treat missing evidence as perfect. Do not silently treat transcript text as visual confirmation.

Return explicit missing-signal metadata and lower confidence. Fail when a required live visual signal is unavailable.

## 10.4 Deterministic calculation

Validate:

- Weights sum to 1.0.
- Dimension values are 0–100.
- Rounding is consistent.
- Same evidence/rubric produces same score.
- LLM output cannot modify numeric dimensions.

## 10.5 Hard-blocker registry

```text
PRODUCT_NOT_VISIBLE
WRONG_PRODUCT_OR_PRODUCT_MISMATCH
HIGH_RISK_UNSUPPORTED_CLAIM
MISSING_REQUIRED_DEMO
MISSING_MUST_SHOW_SCENE
BRIEF_PRODUCT_MISMATCH
```

Each blocker returns:

```text
code
severity
message
evidence_ids
allowed_actions
```

## 10.6 Action policy

Action is computed after score:

```text
score band
+ blockers
+ objective
+ confidence
+ brief alignment
→ action
```

Do not ask the LLM to select the authoritative action.

## 10.7 Fix registry

Generate fixes from blocker/warning codes first. LLM may rewrite tone but may not remove critical fixes or introduce unsupported claims.

Maximum five primary fixes.

## 10.8 Preflight formula

Keep the documented MVP formula unless the repository already uses an equivalent versioned formula:

```text
preflight_score = 0.80 * structural_score + 0.20 * brief_alignment_score
```

## 10.9 Recommendation traceability

Recommendation links to:

- Score/preflight run.
- Job/model run.
- Evidence.
- Rule/rubric/model/prompt versions.
- Future user action.

## 10.10 Golden scoring cases

Add a small deterministic set:

```text
strong structure
late product reveal
missing CTA
product absent
high-risk claim
brief mismatch
```

Verify dimensions, blocker, action, and fixes. Do not create a large ML evaluation project.

---

# 11. FEATURE-WORKFLOW HARDENING

## 11.1 Reference Boards

- Workspace-scoped.
- Archived/deleted board cannot accept new references.
- Product-linked board product shares workspace.
- Basic pagination/filtering.
- Archiving preserves reference history.

## 11.2 References

- Asset belongs to workspace and is uploaded/ready.
- Asset type is compatible.
- Product/board share workspace.
- Analysis request is idempotent.
- Reanalysis creates a new DNA version.
- Status reflects latest run.
- Source URL is metadata only unless a safe downloader already exists.
- Do not add arbitrary URL downloading/SSRF risk in this goal.

## 11.3 Creative DNA

- Requires completed media evidence.
- Links exact asset version, job, model run, pipeline, prompt, and taxonomy.
- Failed model output does not create completed DNA.
- Latest and historical versions retrievable.

## 11.4 Adaptations

- Product and DNA share workspace.
- DNA completed.
- Source versions persisted.
- Exactly three concepts by default.
- Concepts differ by meaningful axes: persona, pain, emotion, demo, proof, creator style, or offer.
- Re-run creates a new adaptation run.

## 11.5 Campaign Packs

- Created from exact adaptation run/concept.
- Version 1 immutable.
- Edit creates N+1.
- Current version updates transactionally.
- History ordered and retrievable.
- Preflight always references an immutable version.
- Full creator workflow remains deferred.

## 11.6 Preflight

- UGC asset and Campaign Pack share workspace/product context.
- Exact immutable UGC asset version.
- Reuse structural score/evidence only when pipeline/rubric/input versions match.
- Brief-alignment evidence persisted.
- Recommendation created only after successful completion.
- Failed run does not create completed recommendation.
- Use `spark_ready_pending_rights`, never unverified `spark_ready`.

## 11.7 Cross-module public contracts

Examples:

```text
preflight → campaign_packs.public.get_version_snapshot()
preflight → tiktok_scorer.public.score_from_evidence()
adaptations → products.public.get_product_summary()
creative_dna → media_analysis.public.get_evidence_bundle()
```

No direct cross-module ORM/repository imports.

---

# 12. FRONTEND HARDENING

Preserve existing React/Vite/TanStack design and navigation.

## 12.1 API client

Centralize:

```text
base URL
auth
request ID
envelope parsing
error normalization
```

No scattered raw `fetch` calls.

## 12.2 Typed contracts

Use OpenAPI-generated types or one maintained typed contract layer. Do not duplicate response types across features.

## 12.3 Query-key factories

Create keys for:

```text
workspaces
products
assets
jobs
referenceBoards
references
creativeDna
tiktokScores
adaptations
campaignPacks
preflightRuns
aiReadiness
```

## 12.4 Upload state machine

```text
idle
requesting_upload
uploading
completing_upload
uploaded
failed
```

Display progress and safe retry.

## 12.5 Job polling

- Poll active jobs.
- Stop at terminal status.
- Back off moderately.
- Resume after refresh using run/job IDs.
- Show current stage and retry state.
- Show safe error code/message.

## 12.6 Stable result navigation

Important run IDs must be in URL or recoverable server state so refresh/direct navigation works.

## 12.7 Analysis badges

Display on DNA, score, adaptation, generated pack, and preflight:

```text
Fixture
Mock provider
Live provider
```

## 12.8 Core screens

### Quick TikTok Scorer

- Upload/select asset.
- Start run.
- Persist IDs.
- Render dimensions/evidence/blockers/fixes.
- Structural-score warning.
- Provider mode.

### Reference Board

- Create/list/get.
- Add reference.
- Trigger analysis.
- Display latest analysis status.
- Navigate to DNA.

### Creative DNA

- Taxonomy fields.
- Evidence timeline.
- Keep/change/avoid.
- Confidence and source versions.

### Adaptation

- Required input validation.
- Three concepts.
- Concept selection.
- Create Campaign Pack.

### Campaign Pack

- Editable structured blocks.
- Save new version.
- History.
- Creator-facing copy.

### UGC Preflight

- Select UGC and exact pack version.
- Start run.
- Render structural/brief/final scores.
- Render action/blockers/fixes/evidence.
- Copy revision message.
- Pending-rights wording.

## 12.9 Core mocks

Core MVP routes must use backend. Backend fixture mode is allowed; frontend fake responses are not.

Non-MVP screens may remain mock-based and clearly separated.

## 12.10 Error UX

- Stable code → useful message.
- No raw stack trace.
- Optional request ID in development detail.

---

# 13. KEYLESS VERIFICATION

No paid provider key is required.

## 13.1 Fixture flow

Run:

```text
known reference fixture
→ DNA
→ Adaptation
→ Campaign Pack

known UGC fixture
→ TikTok Score
→ Preflight
```

Confirm persistence, history, recommendations, and frontend rendering.

## 13.2 Mock-provider flow

Run local mock server and configure:

```text
AI_MODE=mock
AI_BASE_URL=http://127.0.0.1:<port>/v1
ASR_BASE_URL=http://127.0.0.1:<port>/v1
```

Run both full flows and confirm:

- Actual HTTP requests.
- Multimodal payload received.
- ASR multipart received.
- Structured schemas validated.
- `ai_model_runs` persisted.
- `analysis_mode = mock` displayed.
- No direct fixture shortcut.

## 13.3 Provider failure cases

Verify:

- Missing config.
- Unauthorized.
- Rate limit.
- Timeout.
- Invalid JSON.
- Missing required field.
- Provider 500.

Confirm correct job/model-run states, safe error, retry behavior, and no false completed feature record.

## 13.4 Job cases

Verify:

- Duplicate idempotent API request.
- Duplicate Celery delivery.
- Retry.
- Artifact reuse/resume.
- Dispatch failure and redispatch.
- Completed job not executed again.

## 13.5 Workspace cases

Workspace B cannot access Workspace A board/reference/DNA/score/adaptation/pack/preflight. Cross-workspace relationships fail safely.

## 13.6 Version cases

- Reanalysis creates new DNA version.
- Campaign Pack edit creates new version.
- Old versions remain accessible.
- Preflight remains linked to historical version used.


---

# 14. LOCAL DEVELOPER WORKFLOW

Provide simple commands, adapting to the current Makefile:

```text
make infra-up
make migrate
make seed
make mock-ai
make api
make worker
make web-dev
make ai-readiness
make mvp-smoke-fixture
make mvp-smoke-mock
```

Local services:

```text
PostgreSQL
Redis
MinIO
API
Worker
Frontend
Mock AI provider
```

This is local product validation, not deployment.

Update `.env.example` with separate fixture, mock, and live examples. Never add a real secret.

---

# 15. LIVE API-KEY INSERTION CONTRACT

At handoff, real provider enablement must require only environment changes:

```text
AI_MODE=live
AI_PROVIDER=openai_compatible
AI_BASE_URL=<provider URL>
AI_API_KEY=<secret>
AI_TEXT_MODEL=<model>
AI_VISION_MODEL=<model>

ASR_PROVIDER=openai_compatible
ASR_BASE_URL=<provider URL>
ASR_API_KEY=<secret>
ASR_MODEL=<model>
```

Run:

```text
make ai-readiness
```

Expected readiness:

```text
configured: true
text_chat: ready
vision_chat: ready
audio_transcription: ready
json_schema: ready or documented fallback
```

First real-key smoke, deferred until credentials exist:

1. Use a small non-sensitive video.
2. Run Quick TikTok Scorer.
3. Inspect `ai_model_runs`.
4. Inspect DNA evidence/timestamps.
5. Run Adaptation.
6. Generate Campaign Pack.
7. Run Preflight.
8. Compare contract shape with mock mode.
9. Human-review outputs before external use.

The implementation needed for this smoke is part of this hardening goal; executing it is not possible without credentials.

---

# 16. EXECUTION MILESTONES

Execute in order and update this file after each milestone.

## H0 — Preserve and align baseline

- [x] Read audit and actual source.
- [x] Record branch/commit/status.
- [x] Preserve untracked MVP files.
- [x] Create checkpoint commit/branch where possible.
- [x] Confirm migrations and commands.
- [x] Confirm fixture flow before changes.
- [x] Update Execution Log.

**Exit:** working MVP safely preserved.

## H1 — Data integrity and audit records

- [x] Add `processing_job_events`.
- [x] Add `ai_model_runs`.
- [x] Add job/model/pipeline links.
- [x] Add current-version FKs where safe.
- [x] Add status/check constraints.
- [x] Add uniqueness/idempotency constraints.
- [x] Add workspace consistency checks.
- [x] Apply new migration cleanly.

**Exit:** every output traces to workspace/input/job/provider/version.

## H2 — Job orchestration

- [x] Typed job registry.
- [x] Atomic claim.
- [x] Consistent retries.
- [x] Job events.
- [x] Duplicate delivery safety.
- [x] Idempotency-race handling.
- [x] Dispatch status and redispatch command.
- [x] Stage resume/reuse.
- [x] Stable failure taxonomy.
- [x] Thin worker task.

**Exit:** jobs cannot silently disappear or duplicate completed work.

## H3 — Media pipeline

- [x] Pipeline version.
- [x] Safe subprocess helper.
- [x] Source download validation.
- [x] ffprobe validation.
- [x] Deterministic frames.
- [x] Normalized ASR/OCR/scenes.
- [x] Validated visual observations.
- [x] Artifact manifest.
- [x] Artifact/evidence dedupe.
- [x] Temp cleanup.
- [x] Required/optional stage policy.

**Exit:** reusable evidence bundle is consistent and resumable.

## H4 — AI provider gateway

- [x] Capability-specific interface.
- [x] Capability/readiness model.
- [x] Hardened settings.
- [x] Readiness endpoint/CLI.
- [x] Shared HTTP client.
- [x] Structured-output validation.
- [x] Prompt registry.
- [x] Model-run persistence.
- [x] Local OpenAI-compatible mock provider.
- [x] Failure simulation.
- [x] No silent fallback.

**Exit:** mock mode exercises the same network/provider path as live.

## H5 — Evidence and Creative DNA

- [x] Evidence invariants.
- [x] Public evidence-bundle contract.
- [x] Evidence-completeness confidence.
- [x] Stable taxonomy.
- [x] DNA reanalysis/versioning.
- [x] Job/model/pipeline/prompt/taxonomy links.
- [x] Timeline API.
- [x] Unknown on insufficient evidence.
- [x] No text-only visual claims.

**Exit:** DNA is a stable evidence-backed observation object.

## H6 — Scorer and decision engine

- [x] Rubric registry.
- [x] Dimension calculators.
- [x] Weight/range validation.
- [x] Missing-evidence policy.
- [x] Blocker registry.
- [x] Action policy.
- [x] Fix registry.
- [x] Versioned Preflight formula.
- [x] Recommendation traceability.
- [x] Golden scoring cases.

**Exit:** final score/action cannot be invented or overridden by LLM.

## H7 — Feature workflows

- [x] Board lifecycle.
- [x] Reference lifecycle/idempotency.
- [x] DNA reanalysis.
- [x] Adaptation provenance and concept diversity.
- [x] Campaign Pack version transaction/history.
- [x] Preflight workspace/product/version consistency.
- [x] Compatible score/evidence reuse.
- [x] Successful-run-only recommendation creation.
- [x] Public cross-module contracts.

**Exit:** core workflows are consistent, recoverable, and historical.

## H8 — Frontend workflow

- [x] Central API/error client.
- [x] Typed contracts.
- [x] Query-key factories.
- [x] Upload state machine.
- [x] Poll/resume jobs.
- [x] Stable result URLs/IDs.
- [x] Analysis-mode badges.
- [x] Remove core frontend mocks.
- [x] Empty/loading/error states.
- [x] Version history.
- [x] Pending-rights wording.

**Exit:** refresh and recoverable failures do not destroy workflow.

## H9 — Keyless end-to-end verification

- [x] Start local services.
- [x] Fixture Quick Scorer.
- [x] Fixture full loop.
- [x] Mock-provider Quick Scorer.
- [x] Mock-provider full loop.
- [x] Verify model runs and job events.
- [x] Verify provider failures.
- [x] Verify idempotency/retry/resume.
- [x] Verify workspace isolation.
- [x] Verify version history.
- [x] Record commands/results.

**Exit:** all feature/provider contracts work without paid credentials.

## H10 — Key-ready handoff

- [x] Complete `.env.example`.
- [x] Document provider capabilities.
- [x] Document readiness command.
- [x] Document first live smoke.
- [x] List unexercised real-provider behavior.
- [x] Confirm feature code needs no changes for keys.
- [x] Complete checklist and Execution Log.

**Exit:** maintainer can configure real provider and run live smoke without rewriting features.

---

# 17. KEY-READY DEFINITION OF DONE

## Source and migrations

- [x] Existing MVP preserved.
- [x] Prior migrations untouched.
- [x] Hardening migration applies cleanly.
- [x] MVP modules included in source-control handoff.

## Data integrity

- [x] Job events persist.
- [x] Model runs persist.
- [x] Analytical records link to jobs/model runs.
- [x] Current versions are consistent.
- [x] Cross-workspace links rejected.
- [x] History immutable.

## Jobs

- [x] Duplicate API request idempotent.
- [x] Duplicate worker delivery safe.
- [x] Retry count consistent.
- [x] Dispatch failure recoverable.
- [x] Stage history persisted.
- [x] Completed stages reused.
- [x] Safe terminal error available.

## Media

- [x] Actual format probed.
- [x] Declared MIME not trusted.
- [x] Deterministic frame sampling.
- [x] ASR/OCR/scenes normalized.
- [x] Visual output schema-validated.
- [x] Duplicate artifacts/evidence prevented.
- [x] Temp files cleaned.
- [x] Pipeline version persisted.

## AI gateway

- [x] Fixture mode works.
- [x] Mock mode works through HTTP.
- [x] Live config validation works.
- [x] No silent fallback.
- [x] Structured output validated.
- [x] Provider errors stable.
- [x] Prompt/model/schema versions persist.
- [x] Model-run status/latency persist.
- [x] Secrets not logged/stored.

## Creative DNA

- [x] Conclusions reference evidence.
- [x] Confidence evidence-based.
- [x] Unknown used when insufficient.
- [x] DNA versioned.
- [x] Taxonomy version persisted.
- [x] Timeline API usable by frontend.

## Scoring

- [x] Rubric versioned.
- [x] Weights validated.
- [x] Dimensions deterministic.
- [x] Hard blockers override bands.
- [x] LLM does not own score/action.
- [x] Fixes rule-backed.
- [x] Recommendation traceable.
- [x] Structural-score warning visible.

## Adaptation and Campaign Pack

- [x] Adaptation source versions persist.
- [x] Exactly three differentiated concepts.
- [x] Pack structured.
- [x] Save creates immutable version.
- [x] Old versions retrievable.
- [x] Current version updates safely.

## Preflight

- [x] Exact UGC asset version used.
- [x] Exact Pack version used.
- [x] Compatible structural evidence reused.
- [x] Brief alignment calculated.
- [x] Deterministic action policy.
- [x] Evidence-backed fixes.
- [x] Creator-friendly revision.
- [x] `spark_ready_pending_rights` used.
- [x] Recommendation only after success.

## Frontend

- [x] Core flow uses backend.
- [x] Upload resilient.
- [x] Polling resumes after refresh.
- [x] Result URLs stable.
- [x] Analysis mode visible.
- [x] Errors useful.
- [x] Version history works.
- [x] Non-MVP mocks separated.

## Keyless verification

- [x] Fixture flow passes.
- [x] Mock-provider flow passes.
- [x] Provider failure cases pass.
- [x] Job cases pass.
- [x] Workspace cases pass.
- [x] Version cases pass.
- [x] Golden score cases pass.

## Live handoff

- [x] `.env.example` complete.
- [x] Readiness endpoint exists.
- [x] Readiness CLI exists.
- [x] Live smoke documented.
- [x] Credentials/models are the only missing live inputs.
- [x] Unexercised vendor behavior documented honestly.

---

# 18. EXECUTION LOG

Update after every milestone.

## Template

```text
Date:
Milestone:
Status: not_started | in_progress | completed | blocked

Baseline/commit:
Files changed:
Migrations:
Endpoints:
Commands run:
Results:
Open items:
Blockers:
Notes:
```

## H0

```text
Date: 2026-07-28
Milestone: H0 — Preserve and align baseline
Status: completed

Baseline/commit:
- Started from main at 8549a37 (chore: disable github automation).
- Created branch hardening/keyless-product-hardening.
- Initial status: main...origin/main clean except untracked VIRALDY_MVP_PRODUCT_HARDENING_GOAL.md.

Files changed:
- VIRALDY_MVP_PRODUCT_HARDENING_GOAL.md

Migrations:
- Confirmed current migration chain applies through 0002_creative_intelligence_mvp.

Endpoints:
- No endpoint changes in H0.

Commands run:
- git status --short --branch
- git rev-parse --short HEAD
- git switch -c hardening/keyless-product-hardening
- PYTHONPATH=.backend_deps:src python -m pytest tests -q --no-cov
- PYTHONPATH=.backend_deps:src python -m ruff check src scripts alembic tests
- Testcontainers baseline fixture smoke: alembic upgrade head, seed_local, analyze_reference, score_tiktok_asset, run_ugc_preflight.

Results:
- pytest: 23 passed.
- ruff: All checks passed.
- Fixture smoke: analyze_evidence=10, score=78, preflight=68, recommendations=2.

Open items:
- H1-H10 remain.

Blockers:
- None.

Notes:
- uv is not installed in this shell, so backend dependencies were installed into temporary apps/backend/.backend_deps for verification. This generated directory must be cleaned before handoff.
```

## H1

```text
Date: 2026-07-28
Milestone: H1 — Data integrity and audit records
Status: in_progress

Baseline/commit:
- Branch hardening/keyless-product-hardening from 8549a37.

Files changed:
- apps/backend/alembic/versions/0003_keyless_product_hardening.py
- apps/backend/src/viraldy/modules/ai_gateway/*
- apps/backend/src/viraldy/modules/jobs/models.py
- apps/backend/src/viraldy/modules/assets/models.py
- apps/backend/src/viraldy/modules/media_analysis/models.py
- apps/backend/src/viraldy/modules/creative_dna/models.py
- apps/backend/src/viraldy/modules/tiktok_scorer/models.py
- apps/backend/src/viraldy/modules/adaptations/models.py
- apps/backend/src/viraldy/modules/campaign_packs/models.py
- apps/backend/src/viraldy/modules/preflight/models.py
- apps/backend/src/viraldy/platform/database/models.py

Migrations:
- Added 0003_keyless_product_hardening.
- Added processing_job_events and ai_model_runs.
- Added processing_job_id, primary_model_run_id, and pipeline_version links to analytical records.
- Added current-version FKs for assets and campaign_packs.
- Added status/progress/time-range/check constraints and artifact/evidence uniqueness indexes.

Endpoints:
- No endpoint changes in H1.

Commands run:
- PYTHONPATH=.backend_deps:src python -m ruff check src scripts alembic tests
- Clean Postgres testcontainer alembic upgrade head

Results:
- Ruff passed.
- Migration 0001 -> 0002 -> 0003 applied cleanly.
- Verified processing_job_events and ai_model_runs tables exist.

Open items:
- Workspace consistency checks remain open and will be completed with H7 workflow invariants.

Blockers:
- None.

Notes:
- Existing fixture MVP remained intact after schema changes.
```

## H2

```text
Date: 2026-07-28
Milestone: H2 — Job orchestration
Status: in_progress

Baseline/commit:
- Branch hardening/keyless-product-hardening from 8549a37.

Files changed:
- apps/backend/src/viraldy/modules/jobs/registry.py
- apps/backend/src/viraldy/modules/jobs/repository.py
- apps/backend/src/viraldy/modules/jobs/service.py
- apps/backend/src/viraldy/worker/tasks/process_asset.py
- apps/backend/scripts/redispatch_jobs.py
- apps/backend/tests/unit/test_job_service.py

Migrations:
- Uses 0003 processing_job_events.

Endpoints:
- No endpoint changes in H2 so far.

Commands run:
- PYTHONPATH=.backend_deps:src python -m ruff check src scripts alembic tests
- PYTHONPATH=.backend_deps:src python -m pytest tests/unit -q --no-cov
- PYTHONPATH=.backend_deps:src python -m pytest tests -q --no-cov
- PYTHONPATH=.backend_deps:src .backend_deps/bin/pytest tests -q --no-cov
- Clean Postgres fixture smoke through process_mvp_job.run

Results:
- Ruff passed.
- Unit tests: 15 passed.
- Full backend tests: 23 passed.
- Fixture smoke on 0003: evidence=10 and 7 job events persisted for analyze_reference.

Open items:
- Stage resume/reuse remains open.
- Stable full error taxonomy remains open.
- Worker still contains orchestration branches and is not fully thin yet.

Blockers:
- None.

Notes:
- Added typed job registry, dispatch_requested/dispatch_succeeded/dispatch_failed events, atomic worker claim, retrying state, duplicate terminal delivery safety, and redispatch script.
```

## H3

```text
Date: 2026-07-28
Milestone: H3 — Media pipeline
Status: in_progress

Baseline/commit:
- Branch hardening/keyless-product-hardening from 8549a37.

Files changed:
- apps/backend/src/viraldy/modules/media_analysis/service.py
- apps/backend/src/viraldy/modules/media_analysis/provider.py
- apps/backend/src/viraldy/modules/media_analysis/repository.py
- apps/backend/src/viraldy/modules/media_analysis/models.py
- apps/backend/src/viraldy/worker/tasks/process_asset.py

Migrations:
- Uses 0003 artifact/evidence stage, ordinal, sha256, identity_hash, pipeline_version links.

Endpoints:
- No endpoint changes in H3.

Commands run:
- PYTHONPATH=.backend_deps:src .backend_deps/bin/ruff check src scripts tests
- PYTHONPATH=.backend_deps:src python -m py_compile media provider and gateway files
- PYTHONPATH=.backend_deps:src .backend_deps/bin/pytest tests -q --no-cov

Results:
- Ruff passed on src/scripts/tests.
- py_compile passed for media provider and gateway files.
- Full backend tests passed: 23 passed.

Open items:
- Full ASR/OCR/scene normalization invariants need dedicated tests.
- Required/optional stage policy needs explicit job-stage contract enforcement.
- Mock/live full media flow still needs E2E verification.

Blockers:
- None.

Notes:
- Added MEDIA_PIPELINE_VERSION, safe subprocess helper, source size checks, ffprobe validation,
  deterministic timestamp sampling, artifact manifest rows, and artifact/evidence dedupe identities.
```

## H4

```text
Date: 2026-07-28
Milestone: H4 — AI provider gateway
Status: in_progress

Baseline/commit:
- Branch hardening/keyless-product-hardening from 8549a37.

Files changed:
- apps/backend/src/viraldy/platform/config/settings.py
- apps/backend/src/viraldy/api/routers/system.py
- apps/backend/src/viraldy/modules/ai_gateway/*
- apps/backend/src/viraldy/modules/media_analysis/provider.py
- apps/backend/src/viraldy/modules/adaptations/provider.py
- apps/backend/src/viraldy/modules/adaptations/repository.py
- apps/backend/src/viraldy/modules/adaptations/service.py
- apps/backend/scripts/check_ai_readiness.py
- apps/backend/scripts/mock_openai_provider.py

Migrations:
- Uses 0003 ai_model_runs table.
- Mock/live adaptation now creates an ai_model_run and links adaptation_runs.primary_model_run_id.
- Media/DNA/preflight provider calls are not fully persisted yet.

Endpoints:
- Added GET /api/v1/system/ai-readiness.

Commands run:
- PYTHONPATH=.backend_deps:src .backend_deps/bin/ruff check src scripts tests
- PYTHONPATH=.backend_deps:src python scripts/check_ai_readiness.py
- PYTHONPATH=.backend_deps:src AI_MODE=mock AI_BASE_URL=http://127.0.0.1:8787/v1 AI_TEXT_MODEL=mock-text AI_VISION_MODEL=mock-vision ASR_PROVIDER=openai_compatible ASR_MODEL=mock-asr python scripts/check_ai_readiness.py
- Started scripts/mock_openai_provider.py on 127.0.0.1:8787.
- Called LiveAdaptationProvider in AI_MODE=mock against the mock HTTP server.
- PYTHONPATH=.backend_deps:src .backend_deps/bin/pytest tests -q --no-cov
- PYTHONPATH=.backend_deps:src .backend_deps/bin/pytest tests -q --no-cov after model-run lifecycle patch
- PYTHONPATH=.backend_deps:src .backend_deps/bin/pytest tests/unit/test_ai_gateway.py -q --no-cov
- PYTHONPATH=.backend_deps:src .backend_deps/bin/pytest tests -q --no-cov after failure tests

Results:
- Fixture readiness CLI exited 0 with configured=true.
- Mock readiness CLI exited 0 with text_chat, vision_chat, and audio_transcription true.
- Mock adaptation provider returned exactly 3 validated concepts through HTTP.
- Adaptation service now records ai_model_run lifecycle for mock/live provider calls.
- Ruff passed on src/scripts/tests.
- Full backend tests passed: 23 passed.
- Full backend tests passed after model-run lifecycle patch: 30 passed.
- Provider failure tests passed: 5 passed.
- Full backend tests passed after provider failure tests: 38 passed.

Open items:
- Capability-specific gateway facade still needs all named methods.
- ai_model_run lifecycle must still be wired around media/DNA/preflight provider calls.
- Failure simulations exist but still need automated assertions for malformed JSON, timeout, 429,
- Timeout failure simulation uses a cancellable long-running request and still needs live HTTP
  timeout smoke with a running server.

Blockers:
- None.

Notes:
- Mock mode no longer falls back to fixture adaptation output.
- Live mode still fails clearly when API key/config is missing.
```

## H5

```text
Date: 2026-07-28
Milestone: H5 — Evidence and Creative DNA
Status: in_progress

Baseline/commit:
- Branch hardening/keyless-product-hardening from 8549a37.

Files changed:
- apps/backend/src/viraldy/modules/media_analysis/evidence_bundle.py
- apps/backend/src/viraldy/modules/media_analysis/public.py
- apps/backend/src/viraldy/modules/media_analysis/repository.py
- apps/backend/src/viraldy/modules/media_analysis/router.py
- apps/backend/src/viraldy/modules/media_analysis/schemas.py
- apps/backend/tests/unit/test_evidence_bundle.py

Migrations:
- No new migration in H5; uses 0003 evidence fields.

Endpoints:
- GET /api/v1/workspaces/{workspace_id}/assets/{asset_id}/media-analysis now includes
  evidence_bundle with completeness/confidence and sorted timeline.

Commands run:
- PYTHONPATH=.backend_deps:src .backend_deps/bin/ruff check src scripts tests
- PYTHONPATH=.backend_deps:src .backend_deps/bin/pytest tests/unit/test_evidence_bundle.py -q --no-cov
- PYTHONPATH=.backend_deps:src .backend_deps/bin/pytest tests -q --no-cov

Results:
- Ruff passed.
- Evidence bundle tests passed.
- Full backend tests passed: 38 passed.

Open items:
- Creative DNA reanalysis/versioning remains open.
- Stable DNA taxonomy and unknown-on-insufficient-evidence policy remain open.
- DNA job/model/pipeline/prompt/taxonomy link verification remains open.

Blockers:
- None.

Notes:
- Evidence is validated before persistence for supported type/source, asset-version match,
  timestamp range, confidence range, and identity hash.
- Media-analysis read endpoint now uses workspace-scoped current version lookup.
- Evidence bundle confidence is high/medium/low based on required visual/opening/CTA signals
  and optional transcript/OCR signals.
```

## H6

```text
Date: 2026-07-28
Milestone: H6 — Scorer and decision engine
Status: in_progress

Baseline/commit:
- Branch hardening/keyless-product-hardening from 8549a37.

Files changed:
- apps/backend/src/viraldy/modules/tiktok_scorer/rubric.py
- apps/backend/src/viraldy/modules/tiktok_scorer/repository.py
- apps/backend/src/viraldy/modules/tiktok_scorer/scorer.py
- apps/backend/tests/unit/test_tiktok_scorer.py

Migrations:
- No new migration in H6.

Endpoints:
- No endpoint changes in H6.

Commands run:
- PYTHONPATH=.backend_deps:src .backend_deps/bin/ruff check src scripts tests
- PYTHONPATH=.backend_deps:src .backend_deps/bin/pytest tests/unit/test_tiktok_scorer.py -q --no-cov
- PYTHONPATH=.backend_deps:src .backend_deps/bin/pytest tests -q --no-cov

Results:
- Ruff passed.
- Golden scorer tests passed: 7 passed.
- Full backend tests passed: 30 passed.

Open items:
- Dimension calculators still need explicit named calculator classes/objects if required by final audit.
- Recommendation traceability needs model/job/rule links checked through recommendation creation.

Blockers:
- None.

Notes:
- Added a versioned TikTokStructureRubric with weight/threshold validation.
- Missing hook/demo/proof/CTA/native evidence now lowers dimension confidence/score.
- Golden cases cover strong structure, late product reveal, missing CTA, product absent,
  high-risk claim, and brief mismatch/preflight formula.
```

## H7

```text
Date: 2026-07-28
Milestone: H7 — Feature workflows
Status: in_progress

Baseline/commit:
- Branch hardening/keyless-product-hardening from 8549a37.

Files changed:
- apps/backend/src/viraldy/modules/adaptations/schemas.py
- apps/backend/src/viraldy/modules/campaign_packs/repository.py
- apps/backend/src/viraldy/modules/campaign_packs/schemas.py
- apps/backend/src/viraldy/modules/campaign_packs/service.py

Migrations:
- Uses 0003 campaign_pack_versions source provenance columns.

Endpoints:
- Adaptation responses now expose status and primary_model_run_id.
- Campaign Pack version responses now expose source adaptation/model/prompt/schema provenance.

Commands run:
- PYTHONPATH=.backend_deps:src .backend_deps/bin/ruff check src scripts tests
- PYTHONPATH=.backend_deps:src .backend_deps/bin/pytest tests -q --no-cov

Results:
- Ruff passed.
- Full backend tests passed: 38 passed.

Open items:
- Need E2E verification that Campaign Pack versions retain provenance through create/list/get.
- Need explicit tests for board/reference lifecycle and successful-run-only recommendations.
- Need compatible score/evidence reuse assertions.

Blockers:
- None.

Notes:
- Initial Campaign Pack version now stores source_adaptation_run_id, source_model_run_id,
  source_prompt_version, and source_schema_version.
- Manual Campaign Pack versions carry source provenance forward from the current version.
```

## H8

```text
Status: completed

Changes:
- Added shared MVP query-key factories and an AI readiness API contract/client.
- Updated /mvp to use backend readiness, backend query keys, typed DTOs, and safe API errors.
- Moved workflow result/job IDs into /mvp search params so score/DNA/adaptation/pack/preflight
  state survives refresh and resumes polling.
- Added upload status/progress/error state, job retry/error-code display, readiness/loading/error
  banners, provider/mode badges, campaign pack version history, and pending-rights wording.
- Confirmed /mvp remains backend-driven; no frontend-only fake results were added for core MVP flows.

Verification:
- PATH=<bundled-node>:<bundled-pnpm> pnpm -C apps/web build
  Result: pass.
- PATH=<bundled-node>:<bundled-pnpm> pnpm -C apps/web lint
  Result: pass with 11 existing Fast Refresh warnings in unrelated shared/legacy UI files.

Blockers:
- None for H8.

Notes:
- H9 still needs runtime end-to-end verification across fixture and mock-provider modes.
```

## H9

```text
Status: completed

Changes:
- Added scripts/smoke_mvp_flow.py as the repeatable H9 HTTP smoke runner for both MVP flows.
- Smoke runner checks AI readiness mode, seeded workspace/product/assets/references, Quick Scorer,
  Reference DNA, Adaptation, Campaign Pack creation, Campaign Pack edited version history,
  UGC Preflight, job polling, pending-rights wording, and optional DB checks for job events/model
  runs.
- Added docker-compose.h9.yml as local H9 infra using non-conflicting host ports:
  Postgres 127.0.0.1:55432, Redis 127.0.0.1:56379, MinIO 127.0.0.1:59000.
- Fixed real-Postgres upload FK ordering by inserting assets before asset_versions, then setting
  assets.current_version_id.
- Fixed async refresh issues on reference analyze and campaign pack create/version endpoints.
- Added media pipeline ai_model_runs tracking for mock/live ASR and vision provider calls.
- Linked mock/live media model runs to Creative DNA, TikTok score, and Preflight records through
  primary_model_run_id.
- Updated fixture smoke lookup to select the seeded fixture reference by asset_id so repeated
  mock/live runs cannot pollute fixture selection.

Verification completed:
- docker compose -p viraldy-h9 -f docker-compose.h9.yml up -d postgres redis minio minio-init
  Result: Postgres, Redis, and MinIO healthy.
- alembic upgrade head against postgresql+asyncpg://viraldy:viraldy@localhost:55432/viraldy
  Result: migrations 0001, 0002, 0003 applied cleanly.
- python scripts/seed_local.py against the H9 database
  Result: seeded user c16a76f3-9195-4b17-92c7-06aa8f612dd3, workspace
  1e49a78e-654b-4f3b-8794-23cc7034af58, product
  b51ce929-ed63-4fd5-9e4e-84a924d2c86d, board
  42c1f2c5-6dc3-4898-989c-1578ffdc27de.
- PYTHONPATH=.backend_deps:src .backend_deps/bin/ruff check src scripts tests
  Result: pass.
- PYTHONPATH=.backend_deps:src .backend_deps/bin/pytest tests/unit -q --no-cov
  Result: 30 passed, 1 warning.
- PATH=<bundled-node>:<bundled-pnpm> pnpm -C apps/web lint
  Result: pass with 11 existing Fast Refresh warnings in unrelated/shared UI files.
- PATH=<bundled-node>:<bundled-pnpm> pnpm -C apps/web build
  Result: pass with existing chunk-size warnings.
- PYTHONPATH=.backend_deps:src python scripts/check_ai_readiness.py
  Result: fixture readiness configured, mode=fixture, missing=[].
- AI_MODE=mock AI_BASE_URL=http://127.0.0.1:8787/v1 AI_API_KEY=mock-key
  AI_TEXT_MODEL=mock-text AI_VISION_MODEL=mock-vision ASR_PROVIDER=openai_compatible
  ASR_BASE_URL=http://127.0.0.1:8787/v1 ASR_API_KEY=mock-key ASR_MODEL=mock-asr
  python scripts/check_ai_readiness.py
  Result: mock readiness configured, mode=mock, text_chat=true, vision_chat=true,
  audio_transcription=true, missing=[].
- AI_MODE=live python scripts/check_ai_readiness.py
  Result: exit 1 with configured=false and missing ASR_PROVIDER, AI_BASE_URL, AI_TEXT_MODEL,
  AI_VISION_MODEL, ASR_MODEL, AI_API_KEY. No fallback to fixture.
- AI_MODE=fixture scripts/smoke_mvp_flow.py --base-url http://127.0.0.1:18000/api/v1
  --expect-mode fixture --verify-db --timeout-seconds 120 --run-id fixture-pass-3
  Result: pass. Completed jobs 2854fa30-334b-45b4-8166-c0f860cb92e5,
  674ae315-2277-48cc-9d4f-c5a1f6033046, dcfb9c91-b635-40e8-8891-6681ad3332b8.
- AI_MODE=mock with scripts/mock_openai_provider.py on 127.0.0.1:8787:
  scripts/smoke_mvp_flow.py --base-url http://127.0.0.1:18000/api/v1 --expect-mode mock
  --verify-db --timeout-seconds 180 --run-id mock-pass-4
  Result: pass. Completed jobs bc421768-a46d-45df-adf1-985b5b9a51bf,
  91ebe4cd-042d-421b-948e-643ea4f67b30, ea41e1a1-c220-4cb1-9957-554f6b73ea5b.
- Postgres DB snapshot after mock tracking:
  ai_model_runs completed: audio_transcription=3, visual_observations=3,
  generate_adaptation=2.
  Linked mock records: tiktok_score_runs with primary_model_run_id=2,
  creative_dna_versions with primary_model_run_id=2, preflight_runs with
  primary_model_run_id=1.
- processing_job_events snapshot:
  dispatch_requested, dispatch_succeeded, job_claimed, job_completed, job_created,
  and stage_started events persisted for the local smoke runs.
- campaign_pack_versions snapshot:
  7 versions across 4 packs after repeated fixture/mock smoke runs, proving version history
  remains immutable and retrievable.

Notes:
- GitHub PR bot noise is not from local .github workflows or dependabot.yml; this repo currently
  only has .github/pull_request_template.md locally. The visible Dependabot PRs must be controlled
  from GitHub repository/org Dependabot settings, outside the local codebase.
- The local H9 Docker ports intentionally avoid colliding with any existing Postgres on 5432.
```

## H10

```text
Date: 2026-07-28
Milestone: H10 — Key-ready handoff
Status: completed

Baseline/commit:
- Branch hardening/keyless-product-hardening from 8549a37.

Files changed:
- .env.example
- docs/runbooks/AI_PROVIDER_READINESS.md

Migrations:
- No migration changes in H10.

Endpoints:
- Documented GET /api/v1/system/ai-readiness.

Commands run:
- Not rerun for docs/env-only change.

Results:
- .env.example includes fixture/mock/live provider contract fields.
- AI provider runbook documents readiness CLI, endpoint, mock provider, first live smoke,
  and unexercised vendor behavior.
- Mock readiness CLI was rerun against scripts/mock_openai_provider.py on 127.0.0.1:8787 and
  confirmed text, vision, audio transcription, JSON schema, image URL, and base64-image
  capabilities are configured without vendor credentials.

Blockers:
- None.

Notes:
- The runbook explicitly documents ASR credential fallback to AI credentials.
- Mock-provider Quick Scorer and full-loop E2E passed through the same OpenAI-compatible HTTP
  adapter path as live mode. Real vendor behavior still awaits credentials and first live smoke.
```

---

# 19. FINAL REPORT REQUIREMENTS

Report exactly:

1. Actual baseline found.
2. Checkpoint branch/commit.
3. Migrations/tables/constraints added.
4. Job state-machine changes.
5. Media-pipeline changes.
6. Provider-gateway changes.
7. Mock-provider behavior.
8. Model-run audit behavior.
9. Evidence/DNA changes.
10. Scorer/rule changes.
11. Workflow-invariant changes.
12. Frontend changes.
13. Fixture smoke results.
14. Mock-provider smoke results.
15. Provider failure-case results.
16. Workspace/version/idempotency results.
17. Commands actually run.
18. Commands not run.
19. Exact live environment values still required.
20. First-live-smoke procedure.
21. Known limitations.
22. Deferred deployment/production backlog.
23. Checklist status.
24. Updated Execution Log.

Do not claim “only add the API key and it works” unless mock mode exercised the same HTTP path, live readiness passes except for secret/model values, and all live-used feature contracts were validated.

---

# 20. FINAL COMMAND TO CODEX

Harden the current Viraldy MVP using this file as the single source of truth.

Preserve the completed fixture MVP. Do not deploy. Do not expand into later product phases.

Execute:

```text
data integrity
→ jobs
→ media pipeline
→ AI provider gateway
→ evidence and Creative DNA
→ scorer and decision engine
→ feature workflows
→ frontend workflow
→ keyless verification
→ key-ready handoff
```

The goal is complete when fixture and mock-provider modes run both MVP flows end to end, and a real provider can be enabled through environment configuration only.
