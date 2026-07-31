# Viraldy OpenAI Production Intelligence Audit

Date: 2026-07-31

Branch: `release/openai-production-intelligence-showcase`

Implementation commit: `2dc48bf3428750344f6371af6ea4352cd3b2955b`

Code baseline: `origin/main@2f2e8184883a3625190137ca7b3b9a81d6a8fc0c`

## Purpose

This is the authoritative implementation and qualification handoff for the
OpenAI-native production-intelligence work. Give this file, the goal file, and
the Golden Output file to ChatGPT or another planner for the next planning
cycle.

Implementation goal:

`VIRALDY_OPENAI_NATIVE_PRODUCTION_INTELLIGENCE_SHOWCASE_GOAL.md`

Authoritative semantic source:

`VIRALDY_GOLDEN_OUTPUT_REFERENCE_AND_ACCEPTANCE_EXAMPLES_V0_9.md`

The Golden Output document is an implementation and evaluation artifact. The
complete document is never inserted into a runtime model request.

## Executive Status

| Area | Status | Evidence boundary |
| --- | --- | --- |
| OpenAI-native implementation | Implemented | Responses API, strict schemas, transcription, image generation, video preview, provenance |
| Deterministic validators | Implemented | Schema, grounding, evidence, transition, preflight, and qualification gates |
| Application E2E in mock mode | Passed | Three domain cases, API/PostgreSQL/Celery/S3 boundary |
| Real OpenAI API exercised | Partially | One bounded application case attempted; it did not qualify |
| Live qualification | **Not passed** | The required three-case real-key matrix has not passed |
| Best live output log | Empty by design | No live application case became eligible |
| Product ready | **No** | Insufficient real-model and seller evidence |
| Seller value validated | **No** | Deterministic usefulness checks exist; no seller study is complete |
| Commercial performance validated | **No** | No GMV, ROAS, sales, conversion, or virality evidence exists |

Permissible external statement:

> Implemented and mock-verified; real-key live qualification was attempted and
> failed; not live-qualified. Do not use real model outputs in customer demos
> until the all-case application qualification passes.

## What Was Implemented

### Runtime request contract

Each structured model call contains only:

1. Canonical Viraldy system prompt V2.
2. The relevant versioned operation prompt.
3. Required typed Product Context and evidence.
4. Relevant PatternKit or ViralKit context when the operation needs it.
5. At most one or two domain-matched few-shot examples.
6. The strict operation output schema.

The runtime does not inject the full Golden Output file. Few-shot selection is
bounded and grouped by:

- TikTok Shop;
- POD and personalization;
- dropshipping.

The canonical system prompt carries the global grounding,
non-hallucination, personalization, evidence, uncertainty, seller-decision,
and performance-claim policies extracted from the Golden Output.

### Versioned operation packages

| Operation | Prompt version | Output schema | Reasoning | Output cap |
| --- | --- | --- | --- | --- |
| Media Observation | `media_observation_v3_bounded_few_shot_v1` | `media_observation_v1` | low | 12,000 |
| Creative DNA | `creative_dna_extraction_v4_grounded_statuses_few_shot_v1` | `creative_dna_v1` | low | 12,000 |
| PatternKit | `pattern_kit_extraction_v4_evidence_paths_few_shot_v1` | `pattern_kit_v1` | low | 12,000 |
| ViralKit | `viral_kit_composer_v2_few_shot_v1` | `viral_kit_v1` | high | 10,000 |
| Adaptation | `adaptation_generation_v2_few_shot_v1` | `adaptation_v2` | high | 8,000 |
| Campaign Pack | `campaign_pack_generation_v2_few_shot_v1` | `campaign_pack_brief_v1` | medium | 10,000 |
| Seller Decision Summary | `seller_decision_summary_v1_few_shot_v1` | `seller_decision_summary_v1` | low | 2,000 |
| Revision Message | `revision_message_v2_few_shot_v1` | `creator_revision_message_v2` | low | 2,000 |
| Storyboard image | `storyboard_image_generation_v1_few_shot_v1` | `storyboard_image_v1` | provider operation | provider limit |
| Concept video preview | `concept_video_preview_generation_v1_few_shot_v1` | `concept_video_preview_v1` | provider operation | provider limit |
| Audio transcription | provider instruction | transcript contract | n/a | `whisper-1` default |

### OpenAI gateway

- Uses the OpenAI Python SDK and native Responses API structured parsing.
- Sends `store=false`.
- Uses Pydantic strict output contracts rather than free-form JSON parsing.
- Handles refusal, incomplete output, schema failure, provider failure, and
  guardrail failure as explicit fail-closed states.
- Uses bounded SDK retries, with a maximum of two provider retries and at most
  one structured-output repair where the operation permits repair.
- Persists operation, provider, model, prompt version, schema version,
  reasoning effort, request identity, usage, latency, status, and safe error
  metadata in model-run provenance.
- Does not expose internal cost estimates on seller-facing model-run APIs.
- Provides operator-only usage aggregation through
  `apps/backend/scripts/summarize_openai_usage.py`.

### Exact request identity and deduplication

The current implementation does not use a broad or approximate semantic cache
for paid model output.

- `input_hash` covers typed context, selected examples, bounded transcript,
  OCR, and image-content digests.
- `request_hash` covers operation, model, prompt version, schema version, and
  the exact input hash.
- Media-analysis cache identity also includes source checksum, pipeline
  version, media metadata, scene selection, frame timestamps and frame
  digests, audio digest, transcript payload, OCR payload, settings, and prompt
  identity.
- Persisted transcript and OCR artifacts can be reused only when recomputation
  proves an exact analysis request match.
- Successful and failed model runs retain the same exact identity for audit.

### Media cost and concurrency controls

- Scene-aware sampling uses FFmpeg scene detection and deterministic timeline
  fill.
- Required evidence timestamps remain pinned even when ordinary frame sampling
  reaches its configured cap.
- Images are resized with Pillow to the configured maximum long edge and are
  never upscaled.
- A Redis atomic sorted-set lease limits paid OpenAI work per workspace across
  processes.
- A named Redis claim serializes identical media-analysis requests, preventing
  duplicate paid calls from concurrent workers.
- Redis guardrail failure blocks the OpenAI call instead of silently allowing
  unbounded concurrency.
- The media pipeline commits reusable evidence before releasing the claim.
- Application qualification is sequential and worker concurrency is one.

The current media pipeline identity is:

`media_pipeline_v2_scene_cost_controls`

### Deterministic intelligence

The model proposes evidence-grounded structured judgments. It is not allowed
to be the only authority for product state transitions.

Deterministic Python/Pydantic logic owns:

- Product Context completeness and known/unknown distinctions.
- Evidence IDs, timestamp bounds, evidence paths, and source validity.
- Creative DNA field status, support, confidence, and blockers.
- PatternKit requirements, mistake codes, transitions, and activation rules.
- ViralKit concept count, diversity, product fit, and evidence lineage.
- TikTok score rubric, rule version, blockers, fixes, and final action.
- Campaign Pack required sections and immutable requirement snapshots.
- Preflight requirement-by-requirement pass, fail, warning, and blocker state.
- Revision-message issue mapping and seller/creator presentation contracts.
- Live qualification eligibility, non-generic checks, value thresholds,
  cleanup evidence, and product-readiness aggregation.

This is the main intelligence boundary: model output is constrained by
product-specific evidence and then accepted, rejected, or transitioned by
deterministic domain rules.

## Data and Workflow

The production flow is:

```text
Product Context
  -> reference upload/import
  -> media metadata, scenes, frames, audio, transcript, OCR
  -> Media Observation + typed evidence
  -> Creative DNA
  -> PatternKit
  -> ViralKit
  -> selected concept + Adaptation
  -> Campaign Pack
  -> uploaded creator asset
  -> deterministic Preflight
  -> Seller Decision Summary + creator Revision Message
```

PostgreSQL is the canonical structured-data store. S3-compatible object
storage holds media artifacts. Celery executes asynchronous jobs. Redis holds
queue state and the cross-process OpenAI request leases.

Migrations through
`apps/backend/alembic/versions/0013_media_analysis_request_cache.py` add the
exact media-analysis request identity and lookup index.

## API Surface

The generated OpenAPI document currently contains 74 paths. Main endpoint
families are:

- auth, current user, readiness, version, and dependency health;
- workspace, member, event, deletion, retention, and feedback;
- products and secure product crawl preview;
- assets, versions, upload sessions, processing, and media analysis;
- references, reference boards, analysis, and Creative DNA;
- TikTok scores;
- PatternKits, versions, actions, and feedback;
- ViralKits, versions, concept actions, feedback, and campaign handoff;
- adaptations;
- Campaign Packs, versions, and exports;
- generation runs, storyboard images, and concept-video previews;
- preflight runs and seller-facing presentation;
- recommendations and recommendation actions;
- jobs and model-run provenance.

There is intentionally no seller-facing
`/model-runs/usage-summary` endpoint. Usage/cost inspection is an operator
workflow requiring direct backend and database access.

## Frontend Integration

The guided Production Run is implemented at `/production`; `/mvp` redirects to
it. React Query connects the flow to the backend for:

- Product Context selection and import;
- reference upload and analysis;
- TikTok score and Creative DNA;
- PatternKit and ViralKit;
- adaptation generation;
- Campaign Pack generation;
- preflight and presentation;
- asynchronous job polling;
- URL search-parameter resumability.

Runtime labels distinguish mock, configured live, and qualified live states.
The UI does not equate a configured API key with successful qualification.

Known frontend boundary:

- campaign management, performance, and some UGC handoff screens still keep
  frontend/Zustand mirrors and are not fully backend-canonical;
- the Production Run desktop fixture path, product-first entry, and runtime
  status popover passed browser inspection without console errors;
- a mobile screenshot was not captured in the final audit pass.

## Self-Evaluation and Best-Output Policy

The qualification harness evaluates every final application result using:

- semantic equivalence: 30%;
- creator usefulness: 25%;
- campaign usability: 25%;
- seller action agreement: 10%;
- product/evidence specificity: 10%.

It reports a value score from 0 to 5:

- `meaningful`: at least 4;
- `limited`: at least 3 and below 4;
- below 3: not meaningful.

Best-output logging is deliberately strict. An output is eligible only when:

- the mode is real OpenAI, not fixture or mock;
- the whole application E2E case qualifies;
- model-run provenance was persisted;
- the temporary qualification workspace was deleted and cleanup was audited;
- semantic and hard gates pass;
- the output is non-generic and contains required evidence sections;
- the value score is at least 4.

No output currently satisfies all of those conditions, so the best-output log
is empty. Mock outputs are never promoted into the best-live-output store.

Product readiness requires all three real-key application cases to pass, an
average value score of at least 4, and a generic-output rate of zero.

## Qualification Evidence

### Mock application E2E

Report:

`apps/backend/evaluation/reports/openai/20260731T094649388959Z/qualification.json`

Human-readable report:

`apps/backend/evaluation/reports/openai/20260731T094649388959Z/qualification.md`

Observed result:

```text
mode: mock
qualification_state: mock_e2e_verified
cases: 3/3 passed sequentially
application boundary: API + PostgreSQL + Celery + S3
model runs per case: 26
model runs persisted: true
workspace deleted: true
value score: 5.0 for each deterministic mock case
generic output rate: 0.0
best output eligible: false
product ready: false
product-ready blocker: real_openai_app_e2e_not_run
```

This proves application wiring and deterministic qualification behavior. It
does not prove real-model quality.

### Real-key application attempt

Report:

`apps/backend/evaluation/reports/openai/20260731T080800812991Z/qualification.json`

Failure detail:

`apps/backend/evaluation/reports/openai/20260731T080800812991Z/failures/home_travel_steamer.json`

Observed result:

```text
case: home_travel_steamer
mode: live
executed boundary: application_e2e
report execution_scope metadata: contract (known pre-fix reporting defect)
state: failed
passed: false
three-case matrix run: no
automatic full-matrix retry: no
product ready: false
best outputs logged: 0
```

Several provider requests returned successfully and execution reached
adaptation, but the case later failed during slow provider/network behavior.
The report's `generic=1` and `value=0.55` are fail-closed placeholders emitted
because no final output was available. They are not evidence that the real
model output was generic.

That report was produced before commit `1483960`, which fixed preservation of
application qualification and cleanup evidence in failure reports. A database
deletion audit independently verified deletion of the temporary workspace,
37 related objects, and 8 model runs. The live case was not rerun merely to
refresh report metadata, in order to avoid unnecessary API spend.

A lower-level direct diagnostic exists at:

`apps/backend/evaluation/reports/openai/20260731T070653423281Z/qualification.json`

It is diagnostic only and cannot satisfy the application-boundary live gate.

## Verification Record

Backend:

```text
pytest: 368 passed, 1 skipped, 1 warning
coverage: 74.24%
configured project threshold: 70%
mypy: Success, no issues in 290 source files
ruff: All checks passed
pip-audit: no known vulnerabilities
git diff --check: passed
focused cost/media tests: passed
review: no remaining critical, high, or medium findings
```

The total repository coverage passes its configured gate but remains below the
broader 80% target in the engineering instructions. This is an explicit
remaining quality gap, not a hidden pass.

Frontend:

```text
Vitest: 12 files, 48 tests passed
lint: 0 errors, 9 existing Fast Refresh warnings
build: passed
pnpm audit --prod: no known vulnerabilities
```

Build warnings:

- the main client chunk is approximately 1.73 MB;
- the SSR router chunk triggers a size warning;
- Starlette TestClient uses an httpx compatibility path with a deprecation
  warning.

No additional real OpenAI requests were made for the final verification.
Mock verification used an explicit fake key and a local compatible provider.

## Security and Privacy

- No API key is committed or printed in qualification artifacts.
- Runtime secrets remain environment variables.
- Raw model prompts and full payloads are not copied into this audit.
- Workspace authorization and resource ownership are enforced at API
  boundaries.
- Model refusal and guardrail unavailability fail closed.
- Qualification workspaces are deleted and deletion evidence is part of the
  live eligibility gate.
- Rate/concurrency controls operate across workers through Redis.
- Product crawler changes currently visible in the worktree are unrelated to
  this implementation commit and were intentionally excluded.

Open privacy gap:

- media processing still needs an explicit, typed per-asset authorization and
  consent record suitable for private beta operations. Existing access checks
  do not replace that product-level consent artifact.

## Product-Value Assessment

The system is materially more than a generic prompt wrapper because it has:

- product-specific typed context;
- timestamped and source-linked media evidence;
- domain-matched bounded examples;
- versioned operation contracts;
- deterministic decision and state-transition rules;
- exact provenance and reproducible request identity;
- application-boundary qualification;
- explicit genericness and usefulness scoring;
- fail-closed claim and readiness rules.

However, that architecture is only readiness infrastructure. Current evidence
does not establish that real sellers receive enough value, that real-model
outputs consistently beat a generic assistant, or that campaigns perform
better commercially.

Current product conclusion:

```text
engineering implementation: ready for controlled continuation
deterministic/mock workflow: verified
live model quality: not qualified
private beta: blocked on live qualification and consent controls
seller value: unvalidated
commercial value: unvalidated
```

## Remaining Work, In Priority Order

1. Add typed per-asset media authorization/consent and its retention/deletion
   behavior.
2. Diagnose the single failed live case without another API call; then run one
   bounded sequential live case once.
3. Run the full three-case real-key matrix only after the single case passes.
   Keep worker concurrency at one and do not run cases in parallel.
4. Promote outputs to the best-output log only through the existing live,
   application-boundary, value, genericness, persistence, and cleanup gates.
5. Move remaining campaign, performance, and UGC handoff state from frontend
   mirrors to backend-canonical records.
6. Raise backend repository coverage from 74.24% to at least 80%, prioritizing
   model gateway failures, qualification persistence, and media authorization.
7. Perform seller beta evaluation with recorded task completion, edit burden,
   decision confidence, acceptance/rejection reasons, and qualitative value.
8. Measure commercial outcomes only after seller validation. Do not make
   virality, GMV, ROAS, conversion, or sales claims without observed evidence.
9. Reduce frontend bundle size and remove remaining lint/deprecation warnings.
10. Capture mobile Production Run browser evidence after backend
    canonicalization is complete.

## Operator Commands

Run deterministic and mock checks before spending on live calls:

```bash
cd /Users/mac/Desktop/Viraldy/apps/backend
uv run pytest
uv run mypy src
uv run ruff check .
uv run pip-audit
```

Inspect internal usage through the operator CLI:

```bash
cd /Users/mac/Desktop/Viraldy/apps/backend
uv run python scripts/summarize_openai_usage.py --help
```

Follow the bounded live procedure in:

`docs/runbooks/OPENAI_LIVE_QUALIFICATION.md`

Follow provider and cost-control operations in:

`docs/runbooks/OPENAI_PROVIDER.md`

Do not run the all-case live matrix until one application case passes. Do not
parallelize paid qualification calls.

## Repository and Delivery Notes

- GitHub Actions are intentionally disabled and are not part of this delivery.
- No pull request or release tag is created by this task.
- Local OpenAPI generation reports 74 paths; the generated artifact is ignored
  and was not committed.
- Local qualification reports remain evidence artifacts; they contain no API
  key.
- The implementation commit excludes unrelated product-import worktree
  changes and unrelated untracked goal documents.

## Planning Inputs

For the next planning pass, provide:

1. `VIRALDY_OPENAI_PRODUCTION_INTELLIGENCE_AUDIT.md` - current truth.
2. `VIRALDY_OPENAI_NATIVE_PRODUCTION_INTELLIGENCE_SHOWCASE_GOAL.md` - original
   execution contract.
3. `VIRALDY_GOLDEN_OUTPUT_REFERENCE_AND_ACCEPTANCE_EXAMPLES_V0_9.md` -
   authoritative semantic quality bar.
4. The latest mock and live qualification reports listed above.

The next plan must preserve the distinction between configured, mock-verified,
live-qualified, seller-validated, and commercially validated states.
