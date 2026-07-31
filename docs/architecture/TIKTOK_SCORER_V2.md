# TikTok Scorer V2 architecture and migration note

Status: implemented and qualified  
Contract: `VIRALDY_TIKTOK_SCORER_V2_IMPLEMENTATION_PROMPT (1).md` V2.1

## Drift verified before implementation

The repository already had a useful vertical foundation: immutable asset versions, shared
ffmpeg/ASR/OCR/vision evidence, Creative DNA generation, Product Context snapshots, durable
processing jobs, deterministic TikTok dimension arithmetic, and an asset-scoring worker entry
point. Those components remain the source of truth and are reused through their public module
contracts.

The existing scorer itself was still the earlier compact implementation. It accepted an asset
rather than an immutable requested version, used one global rubric, converted missing evidence
to zero, applied universal product timing, returned performance-adjacent action labels, stored
dimensions/findings/fixes as run-level JSON only, and exposed only create/get endpoints. It had
no scene inventory, detailed edit-or-reshoot actions, immutable Product Context or selected
direction snapshot, action events, revision comparison, score history API, profile API, or
standalone frontend routes.

## Target boundaries

The V2 flow is:

```text
immutable asset version
-> shared media/evidence pipeline
-> evidence-backed scene inventory
-> selected versioned content profile
-> deterministic rules and dimensions
-> deterministic score, confidence, and decision precedence
-> detailed least-cost fix plan
-> optional compatible Creative Direction upgrade (never score-affecting)
-> immutable persisted run and product events
```

TikTok Scorer owns pre-publish structural diagnosis, fix planning, and revision verification.
It does not own media extraction, Product Context, Creative DNA, job execution, exact Campaign
Pack validation, post-launch Performance Intelligence, rights completion, or economics. Cross-
module reads use `public.py` contracts. Existing UGC Preflight continues to use the legacy
structural result contract until it is independently versioned.

## Persistence strategy

The existing `tiktok_score_runs` table is expanded additively so completed historical runs are
not rewritten or overwritten. Normalized child tables store dimension results, findings,
structured fix actions, append-only fix events, and draft comparisons. Profiles are versioned
rows seeded separately from schema DDL. Immutable product/direction snapshots, policy/rule/model
versions, media checksum, scene inventory, auxiliary signals, run cost/latency, and failure state
remain attached to the run that used them.

Asset revisions continue to use the shared asset-version upload API. A scorer revision points at
the newly completed immutable asset version, inherits auditable run settings, creates a new score
run, and links a pending comparison. Neither draft is mutated.

## Determinism and AI boundary

LLM/media providers may produce typed observations and seller-friendly wording. They do not
choose scores, severity, blocker resolution, timestamps, product facts, rights, or paid-use
readiness. Missing or weak evidence remains `unknown`, `not_applicable`, or a better-media
request. Only official, product-governance, or operational hard rules may hard-block. Optional
Creative Direction context is compatibility-gated and always has `affects_score=false`; failure
to retrieve it cannot fail core scoring.

## Compatibility

The existing create payload using `asset_id` and the legacy scorer used by UGC Preflight remain
accepted while the canonical API uses `asset_version_id`, explicit score mode, profile, intended
use, and optional direction context. New response fields and child resources are additive. The
standalone frontend consumes only real workspace-scoped APIs and job stages.

## Runtime ownership and public contracts

- `modules/tiktok_scorer` owns the V2 contracts, profiles, policy packs, deterministic engine,
  detailed Fix Planner, persistence, service, comparison, and HTTP resources.
- `modules/media_analysis.public` remains the evidence boundary. The worker supplies the run's
  immutable Product Context snapshot so evidence extraction and cache identity use the same
  context as scoring.
- `modules/assets.public` owns immutable upload/version identity and version-scoped playback.
- `modules/viral_kits.public` supplies optional Creative Direction snapshots. Invalid, stale, or
  unavailable direction data is reported as uncertainty and never changes score arithmetic.
- `modules/jobs.public` and the existing Celery task own queueing, retry, timeout, stage, and
  terminal-state behavior. The scorer's visible stages are `extracting_evidence`,
  `building_scene_inventory`, `scoring`, `compiling_fixes`, optional `enriching_direction`, and
  `comparing_revision`.
- `modules/product_events` records scorer lifecycle, seller-action, revision, and verification
  events without storing uploaded media content in analytics payloads.

The API surface is documented in `docs/api/openapi.json`. It includes list/create/detail,
profiles, fixes and fix actions, revision creation, comparison retrieval, scorer/run analytics,
and version-scoped playback. The frontend owns the four canonical `/tiktok-scorer` route shapes
and keeps server pagination/filtering in the API rather than loading an unbounded local history.

## Operations and qualification

Apply migrations with `make migrate`; `0015_tiktok_scorer_v2_persistence.py` creates the additive
schema and `0016_seed_tiktok_score_profiles.py` seeds versioned beta profiles. Run a scorer job
through the normal API/worker queues; do not invoke the deterministic engine as a separate
deployment. Failed or retried jobs retain their persisted run and expose a typed retry/failure
state to the frontend.

Qualification covers deterministic profile/scoring behavior, missing-evidence safety, all nine
dimensions, fix-plan validation, optional direction isolation, persistence and tenant scoping,
worker stages and failures, action-level comparison, migration upgrade/downgrade, API contracts,
frontend normalization/view models, and production builds. Golden-case reporting deliberately
marks real-world precision, recall, usefulness, and calibration as unmeasured until labeled beta
data exists.

## Known calibration boundary

The seeded weights, thresholds, and timing expectations are versioned beta defaults, not claims
of virality or post-launch performance. Optional live media/direction enrichment still requires
the repository's configured provider credentials. Paid-use rights, economics, and exact Campaign
Pack validation remain explicitly outside this module.
